"""Envoi des alertes par SMTP (bibliotheque standard). Le mot de passe n'est jamais journalise."""
from __future__ import annotations

import logging
import re
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

log = logging.getLogger("ah2.alerts")
_ADDR = re.compile(r"^[^\s@<>,;]+@[^\s@<>,;]+\.[^\s@<>,;]+$")


class AlertSendError(RuntimeError):
    """Echec d'envoi SMTP (message sans secret)."""


@dataclass
class SmtpSettings:
    host: str
    port: int
    user: str
    password: str = field(repr=False)
    sender: str = ""
    security: str = "starttls"  # "starttls" (587), "ssl" (465) ou "none" (tests)
    timeout: float = 20.0

    def __repr__(self) -> str:  # le mot de passe n'apparait jamais
        return "SmtpSettings(host=%r, port=%r, user=%r, sender=%r, security=%r)" % (
            self.host, self.port, self.user, self.sender, self.security)


def load_recipients(path: Path) -> list[str]:
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        log.warning("fichier des destinataires illisible (%s) : %s", exc.__class__.__name__, path)
        return []
    out: list[str] = []
    seen: set[str] = set()
    for n, raw in enumerate(lines, 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if not _ADDR.match(line):
            log.warning("adresse invalide ignoree (ligne %d de %s) : %r", n, Path(path).name, line)
            continue
        key = line.lower()
        if key not in seen:
            seen.add(key)
            out.append(line)
    return out


def send_alert(subject: str, body: str, recipients: list[str], smtp: SmtpSettings) -> None:
    if not recipients:
        raise AlertSendError("aucun destinataire")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp.sender
    msg["To"] = ", ".join(recipients)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=smtp.sender.split("@")[-1] or None)
    msg.set_content(body, charset="utf-8")
    try:
        if smtp.security == "ssl":
            server = smtplib.SMTP_SSL(smtp.host, smtp.port, timeout=smtp.timeout,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(smtp.host, smtp.port, timeout=smtp.timeout)
        with server:
            server.ehlo()
            if smtp.security == "starttls":
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if smtp.user:
                server.login(smtp.user, smtp.password)
            server.send_message(msg, from_addr=smtp.sender, to_addrs=recipients)
    except Exception as exc:  # noqa: BLE001
        text = str(exc)
        if smtp.password:
            text = text.replace(smtp.password, "***")
        raise AlertSendError("envoi SMTP impossible vers %s:%s (%s : %s)" % (
            smtp.host, smtp.port, exc.__class__.__name__, text[:200])) from None
