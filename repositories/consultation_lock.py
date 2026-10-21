# repositories/consultation_lock.py
"""Regle metier « consultation passee = lecture seule » (2026-10-21).

Une consultation (table medical_records) est la PLUS RECENTE de son patient
si aucune autre consultation du meme patient n'a une date de consultation
posterieure. Ordre total utilise partout (meme ordre que l'affichage) :
    consultation_date DESC NULLS LAST, record_id DESC
(une date NULL compte comme la plus ancienne ; a date egale, le plus grand
record_id gagne). Il n'existe ni statut ni suppression logique sur
medical_records : toute ligne presente compte. Une consultation supprimee
(DELETE physique) ne compte donc plus, et la precedente redevient la plus
recente.

Des qu'une consultation plus recente existe, l'ancienne devient en LECTURE
SEULE : plus de modification/suppression de la consultation, plus de
prescription rattachee (creation, modification, suppression, changement de
statut). Une prescription sans consultation (medical_record_id NULL) n'est
pas concernee.

Point unique : toutes les ecritures passent par assert_consultation_writable()
(controllers medical/prescription), qui leve ConsultationLockedError
(traduite en HTTP 409 par les endpoints, convention du projet pour un
conflit de regle metier - cf. /medical_records/{id}/claim).
"""
from typing import Dict, Iterable, Optional

import uuid as _uuid

from sqlalchemy import text

LOCKED_MESSAGE = (
    "Cette consultation n'est plus modifiable : une consultation plus "
    "récente existe pour ce patient."
)


def _is_postgres(session) -> bool:
    # Le client desktop hors ligne (retire) partage ces controllers avec une
    # base SQLite : DISTINCT ON / FOR UPDATE / ANY n'y existent pas.
    try:
        return session.get_bind().dialect.name == "postgresql"
    except Exception:
        return True


class ConsultationLockedError(Exception):
    """Ecriture refusee sur une consultation qui n'est plus la plus recente."""

    def __init__(self, message: str = LOCKED_MESSAGE):
        super().__init__(message)


def lock_patients(session, patient_ids: Iterable[Optional[int]]) -> None:
    """Verrou ligne sur le(s) patient(s), pris dans l'ordre CROISSANT des
    patient_id (pas d'interblocage quand une prescription change de patient).
    Serialise une creation de consultation et une ecriture sur l'ancienne
    consultation du meme patient (sinon : verification OK, creation
    concurrente commitee, puis ecriture sur une consultation devenue
    ancienne). Mode FOR NO KEY UPDATE : deux preneurs se bloquent entre eux,
    mais les INSERT qui referencent le patient (cle etrangere = FOR KEY
    SHARE : prescriptions, rendez-vous, factures...) ne sont PAS bloques.
    Relache au commit de l'ecriture (les repositories commitent). Pas de
    verrou sous SQLite (desktop hors ligne, mono-utilisateur)."""
    ids = sorted({int(p) for p in patient_ids if p is not None})
    if not ids or not _is_postgres(session):
        return
    for p in ids:
        session.execute(
            text("SELECT 1 FROM patients WHERE patient_id = :p FOR NO KEY UPDATE"),
            {"p": p},
        )


def lock_patient_consultations(session, patient_id: Optional[int]) -> None:
    lock_patients(session, [patient_id])


def latest_record_ids(session, patient_ids: Iterable[int]) -> Dict[int, int]:
    """{patient_id: record_id de sa consultation la plus recente} en UNE requete."""
    ids = sorted({int(p) for p in patient_ids if p is not None})
    if not ids:
        return {}
    if not _is_postgres(session):
        out = {}
        for p in ids:
            r = session.execute(
                text(
                    "SELECT record_id FROM medical_records WHERE patient_id = :p "
                    "ORDER BY (consultation_date IS NULL), consultation_date DESC, record_id DESC LIMIT 1"
                ),
                {"p": p},
            ).fetchone()
            if r:
                out[p] = int(r[0])
        return out
    rows = session.execute(
        text(
            "SELECT DISTINCT ON (patient_id) patient_id, record_id "
            "FROM medical_records WHERE patient_id = ANY(:ids) "
            "ORDER BY patient_id, consultation_date DESC NULLS LAST, record_id DESC"
        ),
        {"ids": ids},
    ).fetchall()
    return {int(r[0]): int(r[1]) for r in rows}


def is_latest_consultation(session, record_id: int) -> Optional[bool]:
    """True/False, ou None si la consultation n'existe pas."""
    row = session.execute(
        text("SELECT patient_id FROM medical_records WHERE record_id = :r"),
        {"r": record_id},
    ).fetchone()
    if not row:
        return None
    latest = latest_record_ids(session, [row[0]])
    return latest.get(int(row[0])) == int(record_id)


def assert_consultations_writable(session, record_ids: Iterable[Optional[int]], lock: bool = True) -> None:
    """Leve ConsultationLockedError si l'une des consultations n'est plus la
    plus recente de son patient. Ids None ou inexistants ignores (l'appelant
    garde son propre 404 / cas « sans consultation »). Tous les patients
    concernes sont verrouilles (ordre croissant) AVANT toute verification."""
    rids = sorted({int(r) for r in record_ids if r is not None})
    if not rids:
        return
    from models.medical_record import MedicalRecord  # import local : evite un cycle au chargement
    owners = {
        int(r[0]): int(r[1])
        for r in session.query(MedicalRecord.record_id, MedicalRecord.patient_id)
        .filter(MedicalRecord.record_id.in_(rids)).all()
    }
    if not owners:
        return
    if lock:
        lock_patients(session, owners.values())
    latest = latest_record_ids(session, owners.values())
    for rid, pid in owners.items():
        if latest.get(pid) != rid:
            raise ConsultationLockedError()


def assert_consultation_writable(session, record_id: Optional[int], lock: bool = True) -> None:
    assert_consultations_writable(session, [record_id], lock=lock)


def _same(a, b) -> bool:
    if a is None or a == "":
        return b is None or b == ""
    if isinstance(a, (int, float)) or isinstance(b, (int, float)) or type(a).__name__ == "Decimal" or type(b).__name__ == "Decimal":
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return False
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        return list(a or []) == list(b or [])
    return str(a) == str(b)


def is_noop_update(obj, data: dict, ignore: Iterable[str] = ()) -> bool:
    """True si appliquer `data` a `obj` ne change rien (rejeu d'une
    modification deja commitee, ex. file PowerSync rejouee apres une coupure
    reseau survenue apres le commit). Un tel rejeu est accepte sans
    verification de la regle (sinon : 409 sur une ecriture deja appliquee,
    devenue « ancienne » entre-temps)."""
    if obj is None:
        return False
    ignored = set(ignore)
    for k, v in (data or {}).items():
        if k in ignored or not hasattr(obj, k):
            continue
        if not _same(v, getattr(obj, k)):
            return False
    return True


def annotate_records(session, records) -> None:
    """Pose l'attribut d'instance is_editable sur des MedicalRecord ORM (lu par
    jsonable_encoder/_to_dict/from_attributes). Une seule requete."""
    records = [r for r in (records or []) if r is not None and not isinstance(r, dict)]
    if not records:
        return
    latest = latest_record_ids(session, [getattr(r, "patient_id", None) for r in records])
    for r in records:
        r.is_editable = latest.get(getattr(r, "patient_id", None)) == getattr(r, "record_id", None)


def annotate_prescriptions(session, prescriptions) -> None:
    """is_editable sur des Prescription ORM : True si sans consultation, sinon
    True ssi sa consultation est la plus recente du patient."""
    items = [p for p in (prescriptions or []) if p is not None and not isinstance(p, dict)]
    if not items:
        return
    linked = [p for p in items if getattr(p, "medical_record_id", None) is not None]
    owners = {}
    if linked:
        from models.medical_record import MedicalRecord  # import local : evite un cycle au chargement
        rows = (
            session.query(MedicalRecord.record_id, MedicalRecord.patient_id)
            .filter(MedicalRecord.record_id.in_(sorted({int(p.medical_record_id) for p in linked})))
            .all()
        )
        owners = {int(r[0]): int(r[1]) for r in rows}
    latest = latest_record_ids(session, owners.values())
    for p in items:
        rid = getattr(p, "medical_record_id", None)
        if rid is None:
            p.is_editable = True
        else:
            pid = owners.get(int(rid))
            p.is_editable = pid is not None and latest.get(pid) == int(rid)


def as_uuid(value):
    """uuid.UUID ou None si la valeur n'est pas un uuid valide (aucune ligne
    ne correspondra alors, la creation suit son chemin normal)."""
    try:
        return value if isinstance(value, _uuid.UUID) else _uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None
