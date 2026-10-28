"""Alertes e-mail du chantier 8 (tache 10) : deploy/alerts/*. Aucun reseau externe."""
import email
import json
import logging
import os
import shutil
import socket
import socketserver
import ssl
import subprocess
import threading
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from email import policy
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from deploy.alerts import checks, run_checks
from deploy.alerts.sender import AlertSendError, SmtpSettings, load_recipients, send_alert

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
Usage = namedtuple("Usage", "total used free")


# ---------------------------------------------------------------- disque
def test_check_disk_ok(monkeypatch):
    monkeypatch.setattr(checks.shutil, "disk_usage", lambda p: Usage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3))
    assert checks.check_disk("/watch/pgdata", 80) is None


def test_check_disk_over_threshold_exact_message(monkeypatch):
    monkeypatch.setattr(checks.shutil, "disk_usage", lambda p: Usage(100 * 1024**3, 85 * 1024**3, 15 * 1024**3))
    assert checks.check_disk("/watch/pgdata", 80) == (
        "Disque /watch/pgdata : 85 % utilise (seuil 80 %), 15.0 Go libres sur 100.0 Go")


def test_check_disk_unreadable():
    assert checks.check_disk("/chemin/inexistant/xyz") == "Disque /chemin/inexistant/xyz : lecture impossible (FileNotFoundError)"


# ---------------------------------------------------------------- sauvegardes
def _marker(tmp_path, name, when):
    f = tmp_path / name
    f.write_text(str(int(when.timestamp())))
    return f


def test_backup_fresh_ok(tmp_path):
    m = _marker(tmp_path, "last_success_hourly", NOW - timedelta(hours=2))
    assert checks.check_backup_fresh(m, 3, NOW) is None


def test_backup_stale_exact_message(tmp_path):
    m = _marker(tmp_path, "last_success_nightly", NOW - timedelta(hours=40))
    assert checks.check_backup_fresh(m, 30, NOW) == (
        "Sauvegarde de nuit trop ancienne : derniere reussite le 2026-10-26 20:00 (il y a 40.0 h, maximum 30 h)")


def test_backup_marker_missing_and_grace(tmp_path):
    m = tmp_path / "last_success_offsite"
    assert checks.check_backup_fresh(m, 216, NOW) == "Sauvegarde hors site (Hostinger) : aucune reussite enregistree (maximum 216 h)"
    assert checks.check_backup_fresh(m, 216, NOW, grace_since=NOW - timedelta(hours=5)) is None
    assert checks.check_backup_fresh(m, 216, NOW, grace_since=NOW - timedelta(days=10)) is not None


def test_backup_failure_marker_newer_than_success(tmp_path):
    _marker(tmp_path, "last_success_hourly", NOW - timedelta(hours=2))
    assert checks.check_backup_failure(tmp_path, "hourly") is None
    _marker(tmp_path, "last_failure_hourly", NOW - timedelta(hours=1))
    (tmp_path / "last_error_hourly").write_text("pg_dump: connexion refusee\n")
    assert checks.check_backup_failure(tmp_path, "hourly") == "Sauvegarde horaire en echec : pg_dump: connexion refusee"
    _marker(tmp_path, "last_success_hourly", NOW - timedelta(minutes=5))  # reussite plus recente
    assert checks.check_backup_failure(tmp_path, "hourly") is None


# ---------------------------------------------------------------- sondes
class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        code, body = {"/ok": (200, b'{"success": true}'), "/ko": (200, b'{"success": false}'),
                      "/err": (503, b"{}"), "/junk": (200, b"pas du json")}.get(self.path, (404, b""))
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture
def http_base():
    srv = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()


def test_probe_ok(http_base):
    assert checks.check_probe("api", http_base + "/ok", expect_json_key="success") is None
    assert checks.check_probe("powersync", http_base + "/ok") is None


def test_probe_failures_exact_messages(http_base):
    assert checks.check_probe("api", http_base + "/ko", expect_json_key="success") == (
        'Service api degrade : "success" n\'est pas vrai dans la reponse de %s/ko' % http_base)
    assert checks.check_probe("api", http_base + "/junk", expect_json_key="success") == (
        "Service api : reponse illisible sur %s/junk" % http_base)


def test_probe_http_error_message(http_base):
    # urllib leve HTTPError pour 5xx : le message le dit
    assert checks.check_probe("api", http_base + "/err") == (
        "Service api ne repond pas (HTTPError) : %s/err" % http_base)


def test_probe_unreachable():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    url = "http://127.0.0.1:%d/x" % port
    assert checks.check_probe("api", url, timeout=1) == "Service api ne repond pas (URLError) : " + url


def test_check_redis_ok_and_down():
    got = []

    class R(socketserver.BaseRequestHandler):
        def handle(self):
            while True:
                d = self.request.recv(256)
                if not d:
                    return
                got.append(d)
                self.request.sendall(b"+OK\r\n" if b"AUTH" in d else b"+PONG\r\n")

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), R)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    assert checks.check_redis("redis://:s3cret@127.0.0.1:%d/0" % port) is None
    assert any(b"s3cret" in g for g in got)
    srv.shutdown()
    srv.server_close()
    msg = checks.check_redis("redis://:s3cret@127.0.0.1:%d/0" % port, timeout=1)
    # Linux : ConnectionRefusedError ; Windows : TimeoutError (le nom depend de l'OS)
    assert msg.startswith("Service redis ne repond pas (") and msg.endswith(") : 127.0.0.1:%d" % port)
    assert "s3cret" not in msg


# ---------------------------------------------------------------- certificat
def _make_cert(tmp_path, days, cn="ah2.test"):
    key, crt = tmp_path / "k.pem", tmp_path / "c.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(crt),
                    "-days", str(days), "-subj", "/CN=" + cn], check=True, capture_output=True)
    return crt, key


def _serve_tls(crt, key):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(crt), str(key))
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)

    def loop():
        while True:
            try:
                c, _ = srv.accept()
            except OSError:
                return
            try:
                ctx.wrap_socket(c, server_side=True).close()
            except Exception:
                pass

    threading.Thread(target=loop, daemon=True).start()
    return srv


@pytest.mark.skipif(shutil.which("openssl") is None, reason="la commande openssl est absente")
def test_cert_expiry(tmp_path):
    crt, key = _make_cert(tmp_path, 5)
    srv = _serve_tls(crt, key)
    port = srv.getsockname()[1]
    # auto-signe : la chaine n'est pas verifiee, seule la date est lue
    msg = checks.check_cert_expiry("127.0.0.1", port, 14, server_name="ah2.test")
    assert msg is not None and msg.startswith("Certificat HTTPS de ah2.test : expire dans 4 jours (le ")
    assert msg.endswith(", minimum 14 jours)")
    assert checks.check_cert_expiry("127.0.0.1", port, 3, server_name="ah2.test") is None
    far = datetime.now(timezone.utc) + timedelta(days=30)
    assert checks.check_cert_expiry("127.0.0.1", port, 3, server_name="ah2.test", now=far).startswith(
        "Certificat HTTPS de ah2.test : EXPIRE depuis le ")
    srv.close()
    down = checks.check_cert_expiry("127.0.0.1", port, 14, server_name="ah2.test")
    assert down.startswith("Certificat HTTPS de ah2.test : connexion impossible a 127.0.0.1:%d (" % port)


# ---------------------------------------------------------------- destinataires
def test_recipients_ignores_comments_and_blank_lines(tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("# en-tete\n\n  a@x.test  # promoteur\n\nb@x.test\n", encoding="utf-8")
    assert load_recipients(f) == ["a@x.test", "b@x.test"]


def test_recipients_invalid_skipped_with_warning(tmp_path, caplog):
    f = tmp_path / "r.txt"
    f.write_text("pas une adresse\na@x.test\nbad@@x\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="ah2.alerts"):
        assert load_recipients(f) == ["a@x.test"]
    assert caplog.text.count("adresse invalide ignoree") == 2


def test_recipients_duplicates_removed(tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("a@x.test\nA@X.test\nb@x.test\na@x.test\n", encoding="utf-8")
    assert load_recipients(f) == ["a@x.test", "b@x.test"]


# ---------------------------------------------------------------- run_checks
@pytest.fixture
def env(tmp_path):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "recipients.txt").write_text("promoteur@x.test\nadmin@x.test\n")
    return {"DOMAIN": "ah2.test", "ALERT_CONFIG_DIR": str(cfg), "ALERT_STATE_FILE": str(tmp_path / "state" / "state.json"),
            "SMTP_HOST": "smtp.invalid", "SMTP_PORT": "587", "SMTP_USER": "u@x.test", "SMTP_PASSWORD": "PaSsW0rd-secret",
            "SMTP_FROM": "alertes@x.test"}


class Outbox:
    def __init__(self):
        self.sent = []

    def __call__(self, subject, body, recipients, smtp):
        self.sent.append((subject, body, list(recipients)))


def _collector(box):
    return lambda env, now, first_run: dict(box)


def test_same_alert_sent_once_until_resolved(env):
    out, cur = Outbox(), {"disk:/": "Disque / : 91 % utilise (seuil 80 %)"}
    for i in range(3):
        run_checks.run_once(env, NOW + timedelta(minutes=10 * i), sender=out, collector=_collector(cur))
    assert len(out.sent) == 1
    assert out.sent[0][0].startswith("[AH2 ALERTE] ah2.test : ")
    assert "Disque / : 91 % utilise" in out.sent[0][1]
    assert out.sent[0][2] == ["promoteur@x.test", "admin@x.test"]


def test_reminder_after_24h(env):
    out, cur = Outbox(), {"cert": "Certificat HTTPS de ah2.test : expire dans 3 jours"}
    run_checks.run_once(env, NOW, sender=out, collector=_collector(cur))
    run_checks.run_once(env, NOW + timedelta(hours=23, minutes=50), sender=out, collector=_collector(cur))
    assert len(out.sent) == 1
    run_checks.run_once(env, NOW + timedelta(hours=24, minutes=1), sender=out, collector=_collector(cur))
    assert len(out.sent) == 2
    assert "RAPPEL" in out.sent[1][1]


def test_recovery_mail_sent_once(env):
    out, cur = Outbox(), {"probe:api": "Service api ne repond pas (URLError) : http://api:8000/health"}
    run_checks.run_once(env, NOW, sender=out, collector=_collector(cur))
    cur.clear()
    run_checks.run_once(env, NOW + timedelta(minutes=10), sender=out, collector=_collector(cur))
    run_checks.run_once(env, NOW + timedelta(minutes=20), sender=out, collector=_collector(cur))
    assert len(out.sent) == 2
    assert out.sent[1][0] == "[AH2 RETABLI] ah2.test : 1 probleme resolu"
    assert "Service api ne repond pas" in out.sent[1][1]
    # une nouvelle panne apres retablissement est de nouveau signalee
    cur["probe:api"] = "Service api ne repond pas (URLError) : http://api:8000/health"
    run_checks.run_once(env, NOW + timedelta(minutes=30), sender=out, collector=_collector(cur))
    assert len(out.sent) == 3


def test_several_alerts_one_mail(env):
    out = Outbox()
    cur = {"disk:/": "Disque / : 91 %", "probe:redis": "Service redis ne repond pas", "cert": "Certificat bientot expire"}
    run_checks.run_once(env, NOW, sender=out, collector=_collector(cur))
    assert len(out.sent) == 1
    subject, body, _ = out.sent[0]
    assert subject == "[AH2 ALERTE] ah2.test : 3 problemes"
    for m in cur.values():
        assert m in body
    # une alerte de plus plus tard : un mail ne portant que la nouvelle
    cur["probe:api"] = "Service api ne repond pas"
    run_checks.run_once(env, NOW + timedelta(minutes=10), sender=out, collector=_collector(cur))
    assert len(out.sent) == 2 and "Service api ne repond pas" in out.sent[1][1] and "Disque / : 91" not in out.sent[1][1]


def test_smtp_failure_is_logged_not_raised_and_retried_next_run(env, caplog):
    cur = {"disk:/": "Disque / : 91 %"}
    state = Path(env["ALERT_STATE_FILE"])

    def boom(*a, **k):
        raise AlertSendError("envoi SMTP impossible vers smtp.invalid:587 (OSError : down)")

    with caplog.at_level(logging.ERROR, logger="ah2.alerts"):
        run_checks.run_once(env, NOW, sender=boom, collector=_collector(cur))  # ne leve pas
    assert "nouvel essai au prochain passage" in caplog.text
    assert json.loads(state.read_text())["alerts"] == {}  # etat inchange : l'alerte reste a envoyer
    out = Outbox()
    run_checks.run_once(env, NOW + timedelta(minutes=10), sender=out, collector=_collector(cur))
    assert len(out.sent) == 1


def test_no_password_in_log_output(env, caplog, capsys):
    secret = env["SMTP_PASSWORD"]
    cur = {"disk:/": "Disque / : 91 %"}

    def boom(subject, body, recipients, smtp):
        raise AlertSendError("envoi SMTP impossible (%r)" % (smtp,))

    with caplog.at_level(logging.DEBUG):
        run_checks.run_once(env, NOW, sender=boom, collector=_collector(cur))
        run_checks.run_once(env, NOW, dry_run=True, collector=_collector(cur))
    assert secret not in caplog.text
    cap = capsys.readouterr()
    assert secret not in cap.out and secret not in cap.err
    assert secret not in repr(run_checks.smtp_settings(env))


def test_sender_masks_password_in_error(monkeypatch):
    import smtplib

    class Bad:
        def __init__(self, *a, **k):
            raise smtplib.SMTPAuthenticationError(535, b"mauvais mot de passe PaSsW0rd-secret")

    monkeypatch.setattr(smtplib, "SMTP", Bad)
    s = SmtpSettings("smtp.invalid", 587, "u@x.test", "PaSsW0rd-secret", "a@x.test", "starttls")
    with pytest.raises(AlertSendError) as ei:
        send_alert("s", "b", ["d@x.test"], s)
    assert "PaSsW0rd-secret" not in str(ei.value)


def test_dry_run_sends_nothing(env, capsys):
    out = Outbox()
    run_checks.run_once(env, NOW, dry_run=True, sender=out, collector=_collector({"disk:/": "Disque / : 91 %"}))
    assert out.sent == []
    printed = capsys.readouterr().out
    assert "DRY-RUN" in printed and "[AH2 ALERTE] ah2.test" in printed
    assert not Path(env["ALERT_STATE_FILE"]).exists()


def test_unconfigured_smtp_keeps_alert_pending(env, caplog):
    env["SMTP_HOST"] = ""
    with caplog.at_level(logging.ERROR, logger="ah2.alerts"):
        run_checks.run_once(env, NOW, sender=Outbox(), collector=_collector({"cert": "x"}))
    assert "non configures" in caplog.text
    assert json.loads(Path(env["ALERT_STATE_FILE"]).read_text())["alerts"] == {}


def test_collect_end_to_end_with_status_dir(tmp_path, http_base):
    status = tmp_path / "status"
    status.mkdir()
    _marker(status, "last_success_hourly", NOW - timedelta(hours=5))
    _marker(status, "last_success_nightly", NOW - timedelta(hours=1))
    e = {"ALERT_STATUS_DIR": str(status), "ALERT_DISK_PATHS": "/chemin/absent", "ALERT_CHECK_OFFSITE": "0",
         "ALERT_PROBE_API": http_base + "/ok"}
    found = run_checks.collect(e, NOW, NOW - timedelta(days=1))
    assert list(found) == ["backup-fresh:hourly"]
    assert found["backup-fresh:hourly"].startswith("Sauvegarde horaire trop ancienne")


# ---------------------------------------------------------------- SMTP de bout en bout
class _Smtp(socketserver.StreamRequestHandler):
    def handle(self):
        w = lambda s: self.wfile.write((s + "\r\n").encode())
        w("220 fake ESMTP")
        rcpt, data, mail_from = [], None, None
        while True:
            line = self.rfile.readline().decode(errors="replace").strip()
            cmd = line.upper()
            if cmd.startswith("EHLO") or cmd.startswith("HELO"):
                w("250 fake")
            elif cmd.startswith("MAIL FROM"):
                mail_from = line.split(":", 1)[1].strip()
                w("250 ok")
            elif cmd.startswith("RCPT TO"):
                rcpt.append(line.split(":", 1)[1].strip().strip("<>"))
                w("250 ok")
            elif cmd == "DATA":
                w("354 go")
                buf = []
                while True:
                    l = self.rfile.readline()
                    if l in (b".\r\n", b""):
                        break
                    buf.append(l)
                data = b"".join(buf)
                w("250 queued")
            elif cmd == "QUIT":
                w("221 bye")
                break
            else:
                w("250 ok")
        self.server.captured.append({"from": mail_from, "rcpt": rcpt, "data": data})


def test_smtp_end_to_end_french_body_and_recipients(env):
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Smtp)
    srv.daemon_threads = True
    srv.captured = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env.update(SMTP_HOST="127.0.0.1", SMTP_PORT=str(srv.server_address[1]), SMTP_SECURITY="none", SMTP_USER="")
    cur = {"backup-fresh:hourly": "Sauvegarde horaire trop ancienne : derniere reussite le 2026-10-28 06:00 (il y a 6.0 h, maximum 3 h)"}
    run_checks.run_once(env, NOW, collector=_collector(cur))
    srv.shutdown()
    assert len(srv.captured) == 1
    got = srv.captured[0]
    assert got["rcpt"] == ["promoteur@x.test", "admin@x.test"]
    msg = email.message_from_bytes(got["data"], policy=policy.default)
    assert msg["Subject"].startswith("[AH2 ALERTE] ah2.test : Sauvegarde horaire trop ancienne")
    assert msg["From"] == "alertes@x.test"
    body = msg.get_content()
    assert "Alerte automatique du serveur AH2 (ah2.test)." in body
    assert "il y a 6.0 h, maximum 3 h" in body
    assert "Que faire :" in body and "docs/exploitation/sauvegardes.md" in body
    assert "PaSsW0rd" not in got["data"].decode()


def test_test_mail_option(env, capsys):
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Smtp)
    srv.daemon_threads = True
    srv.captured = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env.update(SMTP_HOST="127.0.0.1", SMTP_PORT=str(srv.server_address[1]), SMTP_SECURITY="none", SMTP_USER="")
    assert run_checks.main(["--test-mail"], environ=env) == 0
    srv.shutdown()
    msg = email.message_from_bytes(srv.captured[0]["data"], policy=policy.default)
    assert msg["Subject"] == "[AH2 TEST] ah2.test : message de test des alertes"
    assert srv.captured[0]["rcpt"] == ["promoteur@x.test", "admin@x.test"]
    assert "Message de test envoye" in capsys.readouterr().out


def test_test_mail_without_config_fails_cleanly(env, capsys):
    env["SMTP_HOST"] = ""
    assert run_checks.main(["--test-mail"], environ=env) == 1
    assert "ECHEC" in capsys.readouterr().err


def test_build_env_reads_alerts_env_file(tmp_path):
    cfg = tmp_path / "c"
    cfg.mkdir()
    (cfg / "alerts.env").write_text('# c\nSMTP_HOST=smtp.h.test\nSMTP_PASSWORD="p w"\nALERT_DISK_PCT=70\n')
    e = run_checks.build_env({"ALERT_CONFIG_DIR": str(cfg), "ALERT_DISK_PCT": "90"})
    assert e["SMTP_HOST"] == "smtp.h.test" and e["SMTP_PASSWORD"] == "p w"
    assert e["ALERT_DISK_PCT"] == "90"  # l'environnement du conteneur l'emporte
    s = run_checks.smtp_settings({"SMTP_HOST": "h", "SMTP_PORT": "465", "SMTP_USER": "u@h"})
    assert s.security == "ssl" and s.sender == "u@h"
