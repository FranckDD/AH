"""Verifications d'alerte. Chaque check_* renvoie None si tout va bien, sinon le message.

Bibliotheque standard uniquement. Messages en francais sans accents (ASCII).
Aucun secret n'apparait jamais dans un message.
"""
from __future__ import annotations

import json
import shutil
import socket
import ssl
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

BACKUP_LABELS = {"hourly": "horaire", "nightly": "de nuit", "offsite": "hors site (Hostinger)"}


def check_disk(path: str, threshold_pct: int = 80) -> Optional[str]:
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        return "Disque %s : lecture impossible (%s)" % (path, exc.__class__.__name__)
    pct = usage.used * 100 / usage.total if usage.total else 100.0
    if pct > threshold_pct:
        return "Disque %s : %.0f %% utilise (seuil %d %%), %.1f Go libres sur %.1f Go" % (
            path, pct, threshold_pct, usage.free / 1024**3, usage.total / 1024**3)
    return None


def _label(marker: Path) -> str:
    return BACKUP_LABELS.get(marker.name.replace("last_success_", ""), marker.name)


def _read_ts(path: Path) -> Optional[int]:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def check_backup_fresh(marker: Path, max_age_hours: int, now: datetime,
                       grace_since: Optional[datetime] = None) -> Optional[str]:
    """marker = fichier last_success_<job> (secondes Unix). grace_since : si le marqueur
    n'existe pas encore, pas d'alerte avant max_age_hours apres cette date (premier demarrage)."""
    label = _label(marker)
    ts = _read_ts(marker)
    if ts is None:
        if grace_since is not None and now - grace_since < timedelta(hours=max_age_hours):
            return None
        return "Sauvegarde %s : aucune reussite enregistree (maximum %d h)" % (label, max_age_hours)
    last = datetime.fromtimestamp(ts, tz=now.tzinfo or timezone.utc)
    age = now - last
    if age > timedelta(hours=max_age_hours):
        return "Sauvegarde %s trop ancienne : derniere reussite le %s (il y a %.1f h, maximum %d h)" % (
            label, last.strftime("%Y-%m-%d %H:%M"), age.total_seconds() / 3600, max_age_hours)
    return None


def check_backup_failure(status_dir: Path, job: str) -> Optional[str]:
    """Echec plus recent que la derniere reussite (lib.sh efface last_failure_* a la reussite)."""
    fail = _read_ts(status_dir / ("last_failure_" + job))
    if fail is None:
        return None
    ok = _read_ts(status_dir / ("last_success_" + job))
    if ok is not None and ok >= fail:
        return None
    try:
        err = (status_dir / ("last_error_" + job)).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        err = ""
    err = " ".join(err.split())[:300] or "motif inconnu"
    return "Sauvegarde %s en echec : %s" % (BACKUP_LABELS.get(job, job), err)


def check_probe(name: str, url: str, expect_json_key: Optional[str] = None,
                timeout: float = 5.0) -> Optional[str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (URL interne)
            status = resp.status
            body = resp.read(65536)
    except Exception as exc:  # noqa: BLE001
        return "Service %s ne repond pas (%s) : %s" % (name, exc.__class__.__name__, url)
    if not 200 <= status < 300:
        return "Service %s en erreur : HTTP %d sur %s" % (name, status, url)
    if expect_json_key is not None:
        try:
            ok = json.loads(body).get(expect_json_key) is True
        except (ValueError, AttributeError):
            return "Service %s : reponse illisible sur %s" % (name, url)
        if not ok:
            return "Service %s degrade : \"%s\" n'est pas vrai dans la reponse de %s" % (
                name, expect_json_key, url)
    return None


def check_redis(redis_url: str, timeout: float = 5.0) -> Optional[str]:
    """PING Redis (protocole RESP a la main, avec AUTH si l'URL contient un mot de passe)."""
    parts = urlsplit(redis_url)
    host, port = parts.hostname or "redis", parts.port or 6379
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            if parts.password:
                pw = unquote(parts.password).encode()
                s.sendall(b"*2\r\n$4\r\nAUTH\r\n$%d\r\n%s\r\n" % (len(pw), pw))
                if not s.recv(256).startswith(b"+OK"):
                    return "Service redis refuse l'authentification (%s:%d)" % (host, port)
            s.sendall(b"*1\r\n$4\r\nPING\r\n")
            if not s.recv(256).startswith(b"+PONG"):
                return "Service redis : reponse inattendue au PING (%s:%d)" % (host, port)
    except OSError as exc:
        return "Service redis ne repond pas (%s) : %s:%d" % (exc.__class__.__name__, host, port)
    return None


def check_cert_expiry(host: str, port: int, min_days: int = 14,
                      server_name: Optional[str] = None, now: Optional[datetime] = None) -> Optional[str]:
    """Lit la date d'expiration du certificat servi sur host:port (SNI = server_name).
    La verification de la chaine est desactivee : seule la date est lue (autorite locale
    ou de test possible en repetition)."""
    sni = server_name or host
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, port), timeout=8) as raw:
            with ctx.wrap_socket(raw, server_hostname=sni) as tls:
                der = tls.getpeercert(binary_form=True)
    except (OSError, ssl.SSLError) as exc:
        return "Certificat HTTPS de %s : connexion impossible a %s:%d (%s)" % (
            sni, host, port, exc.__class__.__name__)
    try:
        # getpeercert() est vide quand la chaine n'est pas verifiee : decoder le DER en PEM.
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as tmp:
            tmp.write(ssl.DER_cert_to_PEM_cert(der))
        try:
            info = ssl._ssl._test_decode_cert(tmp.name)  # type: ignore[attr-defined]
        finally:
            Path(tmp.name).unlink(missing_ok=True)
        expires = datetime.fromtimestamp(ssl.cert_time_to_seconds(info["notAfter"]), tz=timezone.utc)
    except Exception as exc:  # noqa: BLE001
        return "Certificat HTTPS de %s : date d'expiration illisible (%s)" % (sni, exc.__class__.__name__)
    now = now or datetime.now(timezone.utc)
    days = (expires - now).total_seconds() / 86400
    if days < 0:
        return "Certificat HTTPS de %s : EXPIRE depuis le %s" % (sni, expires.strftime("%Y-%m-%d"))
    if days < min_days:
        return "Certificat HTTPS de %s : expire dans %d jours (le %s, minimum %d jours)" % (
            sni, int(days), expires.strftime("%Y-%m-%d"), min_days)
    return None
