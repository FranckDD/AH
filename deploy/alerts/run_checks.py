"""Controles d'alerte AH2, lances toutes les 10 minutes par le planificateur :
    python -m deploy.alerts.run_checks [--dry-run] [--test-mail]

Une alerte n'est envoyee qu'une fois par changement d'etat (rappel apres 24 h tant
qu'elle dure, un seul message "retabli" ensuite). Plusieurs alertes simultanees
partent dans un seul message. Un echec SMTP est journalise et l'etat n'est pas mis a
jour : l'envoi est retente au passage suivant. Code de sortie 0 sauf plantage imprevu.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional

from deploy.alerts import checks
from deploy.alerts.sender import AlertSendError, SmtpSettings, load_recipients, send_alert

log = logging.getLogger("ah2.alerts")

DEFAULT_CONFIG_DIR = "/run/alerts"
DOC = "docs/exploitation/alertes-et-acces.md"
BACKUP_DOC = "docs/exploitation/sauvegardes.md"


def parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k.strip()] = v
    return out


def build_env(environ: Mapping[str, str]) -> dict[str, str]:
    """alerts.env (monte en lecture seule) sous l'environnement du conteneur."""
    cfg = Path(environ.get("ALERT_CONFIG_DIR", DEFAULT_CONFIG_DIR))
    merged = parse_env_file(cfg / "alerts.env")
    merged.update(environ)
    merged.setdefault("ALERT_CONFIG_DIR", str(cfg))
    return merged


def smtp_settings(env: Mapping[str, str]) -> Optional[SmtpSettings]:
    host = env.get("SMTP_HOST", "").strip()
    if not host:
        return None
    user = env.get("SMTP_USER", "").strip()
    try:
        port = int(env.get("SMTP_PORT", "587"))
    except ValueError:
        port = 587
    security = env.get("SMTP_SECURITY", "ssl" if port == 465 else "starttls").strip().lower()
    return SmtpSettings(host=host, port=port, user=user, password=env.get("SMTP_PASSWORD", ""),
                        sender=env.get("SMTP_FROM", "").strip() or user, security=security)


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        return int(env.get(key, default))
    except (TypeError, ValueError):
        return default


def collect(env: Mapping[str, str], now: datetime, first_run: Optional[datetime]) -> dict[str, str]:
    """Execute tous les controles ; renvoie {cle d'alerte: message}."""
    found: dict[str, str] = {}

    def add(key: str, msg: Optional[str]) -> None:
        if msg:
            found[key] = msg

    pct = _int(env, "ALERT_DISK_PCT", 80)
    paths = [p.strip() for p in env.get("ALERT_DISK_PATHS", "/,/watch/pgdata,/watch/uploads,/watch/ps_storage,/watch/backups").split(",") if p.strip()]
    for p in paths:
        if not os.path.exists(p):
            continue  # volume non monte dans ce deploiement
        add("disk:" + p, checks.check_disk(p, pct))

    status = Path(env.get("ALERT_STATUS_DIR", "/var/lib/ah2-status"))
    jobs = [("hourly", _int(env, "ALERT_HOURLY_MAX_H", 3)), ("nightly", _int(env, "ALERT_NIGHTLY_MAX_H", 30))]
    if env.get("ALERT_CHECK_OFFSITE", "1") != "0":
        jobs.append(("offsite", _int(env, "ALERT_OFFSITE_MAX_H", 9 * 24)))
    for job, max_h in jobs:
        add("backup-fresh:" + job, checks.check_backup_fresh(status / ("last_success_" + job), max_h, now, first_run))
        add("backup-fail:" + job, checks.check_backup_failure(status, job))

    api = env.get("ALERT_PROBE_API", "http://api:8000/health")
    add("probe:api", checks.check_probe("api", api, expect_json_key="success"))
    ps = env.get("ALERT_PROBE_POWERSYNC", "")
    if ps:
        add("probe:powersync", checks.check_probe("powersync", ps))
    redis_url = env.get("REDIS_URL", "")
    if redis_url:
        add("probe:redis", checks.check_redis(redis_url))

    domain = env.get("DOMAIN", "").strip()
    if domain and env.get("ALERT_CHECK_CERT", "1") != "0":
        add("cert", checks.check_cert_expiry(env.get("ALERT_CERT_HOST", "caddy"), _int(env, "ALERT_CERT_PORT", 443),
                                             _int(env, "ALERT_CERT_DAYS", 14), server_name=domain, now=now))
    return found


HINTS = {
    "disk": "Que faire : liberer de la place ou agrandir le disque (" + DOC + ", section Disque).",
    "backup-fresh": "Que faire : verifier le conteneur backup et son journal (" + BACKUP_DOC + ").",
    "backup-fail": "Que faire : lire le motif ci-dessus puis " + BACKUP_DOC + ".",
    "probe": "Que faire : voir l'etat des conteneurs, docker compose ps (" + DOC + ", section Services).",
    "cert": "Que faire : verifier Caddy et le DNS du domaine (" + DOC + ", section Certificat HTTPS).",
}


def _hint_for(key: str) -> str:
    return HINTS.get(key.split(":", 1)[0], "")


def format_alert(domain: str, items: list[tuple[str, str]], reminder: set[str]) -> tuple[str, str]:
    n = len(items)
    subject = "[AH2 ALERTE] %s : %s" % (domain, items[0][1][:80] if n == 1 else "%d problemes" % n)
    lines = ["Alerte automatique du serveur AH2 (%s)." % domain, ""]
    for i, (key, msg) in enumerate(items, 1):
        lines.append("%d. %s%s" % (i, msg, " [RAPPEL, toujours en cours]" if key in reminder else ""))
        hint = _hint_for(key)
        if hint:
            lines.append("   " + hint)
        lines.append("")
    lines.append("Vous recevrez un seul message \"retabli\" quand tout sera revenu a la normale.")
    return subject, "\n".join(lines) + "\n"


def format_recovery(domain: str, items: list[tuple[str, str]]) -> tuple[str, str]:
    n = len(items)
    subject = "[AH2 RETABLI] %s : %s" % (domain, "1 probleme resolu" if n == 1 else "%d problemes resolus" % n)
    lines = ["Retour a la normale sur le serveur AH2 (%s)." % domain, "", "Problemes resolus :"]
    lines += ["- " + msg for _, msg in items]
    return subject, "\n".join(lines) + "\n"


def _load_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("alerts"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"first_run": None, "alerts": {}}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def run_once(env: Mapping[str, str], now: Optional[datetime] = None, dry_run: bool = False,
             sender: Callable[..., None] = send_alert,
             collector: Optional[Callable[[Mapping[str, str], datetime, Optional[datetime]], dict[str, str]]] = None
             ) -> None:
    now = now or datetime.now(timezone.utc).astimezone()
    domain = env.get("DOMAIN", "").strip() or "AH2"
    state_path = Path(env.get("ALERT_STATE_FILE", "/var/lib/ah2-alerts/state.json"))
    state = _load_state(state_path)
    if not state.get("first_run"):
        state["first_run"] = now.timestamp()
    first_run = datetime.fromtimestamp(state["first_run"], tz=now.tzinfo or timezone.utc)

    current = (collector or collect)(env, now, first_run)
    known: dict = state["alerts"]
    reminder_s = _int(env, "ALERT_REMINDER_H", 24) * 3600

    to_send = [(k, m) for k, m in sorted(current.items())
               if k not in known or now.timestamp() - known[k].get("last_sent", 0) >= reminder_s]
    reminders = {k for k, _ in to_send if k in known}
    recovered = [(k, known[k].get("message", k)) for k in sorted(known) if k not in current]
    # Le message d'une alerte connue suit la valeur courante (sans nouvel envoi).
    for k, m in current.items():
        if k in known:
            known[k]["message"] = m

    recipients = load_recipients(Path(env.get("ALERT_CONFIG_DIR", DEFAULT_CONFIG_DIR)) / "recipients.txt") \
        if (to_send or recovered) else []
    smtp = smtp_settings(env)
    can_send = dry_run or (smtp is not None and bool(recipients))
    if (to_send or recovered) and not can_send:
        log.error("alertes en attente mais SMTP_HOST ou destinataires non configures (%s)", DOC)
    for key, msg in current.items():
        if (key, msg) not in to_send:
            log.info("alerte deja signalee : %s", msg)

    def deliver(subject: str, body: str) -> bool:
        if dry_run:
            print("--- DRY-RUN : message non envoye ---\nA : %s\nObjet : %s\n\n%s" % (", ".join(recipients) or "(aucun)", subject, body))
            return True
        try:
            sender(subject, body, recipients, smtp)
            return True
        except AlertSendError as exc:
            log.error("echec d'envoi de l'alerte, nouvel essai au prochain passage : %s", exc)
            return False

    if to_send and can_send:
        subject, body = format_alert(domain, to_send, reminders)
        if deliver(subject, body) and not dry_run:
            for k, m in to_send:
                known[k] = {"message": m, "since": known.get(k, {}).get("since", now.isoformat()),
                            "last_sent": now.timestamp()}
    if recovered and can_send:
        subject, body = format_recovery(domain, recovered)
        if deliver(subject, body) and not dry_run:
            for k, _ in recovered:
                known.pop(k, None)
    if not dry_run:
        try:
            _save_state(state_path, state)
        except OSError as exc:
            log.error("etat des alertes non enregistre (%s) : %s", exc.__class__.__name__, state_path)


def send_test_mail(env: Mapping[str, str]) -> int:
    smtp = smtp_settings(env)
    recipients = load_recipients(Path(env.get("ALERT_CONFIG_DIR", DEFAULT_CONFIG_DIR)) / "recipients.txt")
    if smtp is None or not recipients:
        print("ECHEC : SMTP_HOST (alerts.env) ou destinataires (recipients.txt) non configures.", file=sys.stderr)
        return 1
    domain = env.get("DOMAIN", "").strip() or "AH2"
    try:
        send_alert("[AH2 TEST] %s : message de test des alertes" % domain,
                   "Ceci est un message de test du systeme d'alertes AH2 (%s).\n"
                   "Si vous le lisez, l'envoi fonctionne. Aucune action n'est demandee.\n" % domain,
                   recipients, smtp)
    except AlertSendError as exc:
        print("ECHEC : %s" % exc, file=sys.stderr)
        return 1
    print("Message de test envoye a : %s" % ", ".join(recipients))
    return 0


def main(argv: Optional[list[str]] = None, environ: Optional[Mapping[str, str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="run_checks", description="Controles et alertes e-mail AH2")
    ap.add_argument("--dry-run", action="store_true", help="afficher les messages au lieu de les envoyer")
    ap.add_argument("--test-mail", action="store_true", help="envoyer un message de test a chaque destinataire")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s alerts: %(message)s")
    env = build_env(environ if environ is not None else os.environ)
    if args.test_mail:
        return send_test_mail(env)
    run_once(env, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
