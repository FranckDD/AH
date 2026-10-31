# utils/lab_dossier.py
"""Numero de dossier du laboratoire : `NNN/NN du JJ/MM/AAAA` (ex. `289/02 du 08/10/2026`).

- Premier nombre : compteur annuel qui avance d'un cran au PREMIER dossier de chaque nouvelle
  journee d'activite (tous les patients du meme jour le partagent), remis a 1 le 1er janvier ;
  un jour sans enregistrement ne le fait pas avancer.
- Second nombre : rang du patient dans la journee, partage par tous ses examens du jour.
- Attribue par le SERVEUR, jamais par le client, sous verrou consultatif PostgreSQL
  (pg_advisory_xact_lock : relache a la fin de la transaction).

La fonction `assign_dossier` est l'unique endroit qui decide du calcul.
"""
import hashlib
import logging
import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, NamedTuple, Optional

from sqlalchemy import text

# Cle du verrou consultatif (constante arbitraire, propre au numero de dossier du laboratoire).
DOSSIER_LOCK_KEY = 7_306_241_001


class DossierNumber(NamedTuple):
    year: int
    counter: int
    rank: int


class DossierNotAssignedError(ValueError):
    """Le resultat n'a pas encore de numero de dossier officiel (reception hors ligne non synchronisee)."""


def _norm(value: Any) -> str:
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def build_patient_key(patient_id: Optional[int] = None, external_info: Optional[Dict[str, Any]] = None,
                      batch_id: Any = None) -> str:
    """Cle stable d'un patient pour partager le rang du jour entre ses examens.

    Interne : `p:<patient_id>`. Externe : `x:` + sha1 de (nom + prenom, age, sexe, telephone) normalises.
    Externe SANS telephone (cas du formulaire de reception) : `batch_id` (identifiant serveur du lot) est ajoute a
    la cle, pour que deux personnes differentes de meme nom/age/sexe le meme jour n'aient pas le meme rang ; tous
    les examens d'une meme reception (meme lot) gardent le meme rang. Une meme personne recue deux fois le meme
    jour (deux lots) obtient donc deux rangs : comportement accepte."""
    if patient_id:
        return f"p:{int(patient_id)}"
    if not external_info:
        raise ValueError("Patient interne ou informations du patient externe requis.")
    name = _norm(f"{external_info.get('nom') or ''} {external_info.get('prenom') or ''}")
    if not name:
        raise ValueError("Nom du patient externe requis.")
    if external_info.get("age_days") not in (None, ""):
        age = f"d{external_info.get('age_days')}"
    else:
        age = f"{_norm(external_info.get('age'))}{_norm(external_info.get('age_unit'))}"
    sex = _norm(external_info.get("sexe"))
    phone = re.sub(r"\D", "", str(external_info.get("telephone") or ""))
    parts = [name, age, sex, phone]
    if not phone and batch_id:
        parts.append(f"b:{batch_id}")
    raw = "|".join(parts)
    return "x:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()


def format_dossier(number: DossierNumber, day: date) -> str:
    """`289/02 du 08/10/2026` : compteur sur 3 chiffres, rang sur 2, date jj/mm/aaaa."""
    return f"{number.counter:03d}/{number.rank:02d} du {day.strftime('%d/%m/%Y')}"


def assign_dossier(session, patient_key: str, day: date) -> DossierNumber:
    """Numero de dossier du patient `patient_key` pour le jour `day` (idempotent par patient et jour).

    Sous verrou consultatif de transaction : deux receptions simultanees n'obtiennent jamais le meme
    numero. Les lignes inserees (lab_dossier_days / lab_dossier_ranks) sont validees avec la
    transaction de l'appelant ; un rollback n'en laisse aucune (pas de numero perdu)."""
    if not patient_key:
        raise ValueError("patient_key requis")
    year = day.year
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": DOSSIER_LOCK_KEY})

    row = session.execute(
        text("SELECT counter, rank FROM lab_dossier_ranks WHERE year = :y AND day = :d AND patient_key = :k"),
        {"y": year, "d": day, "k": patient_key},
    ).first()
    if row:
        return DossierNumber(year, row.counter, row.rank)

    counter = session.execute(
        text("SELECT counter FROM lab_dossier_days WHERE year = :y AND day = :d"), {"y": year, "d": day}
    ).scalar()
    if counter is None:
        counter = session.execute(
            text("SELECT COALESCE(MAX(counter), 0) + 1 FROM lab_dossier_days WHERE year = :y"), {"y": year}
        ).scalar()
        session.execute(
            text("INSERT INTO lab_dossier_days (year, day, counter) VALUES (:y, :d, :c)"),
            {"y": year, "d": day, "c": counter},
        )
    rank = session.execute(
        text("SELECT COALESCE(MAX(rank), 0) + 1 FROM lab_dossier_ranks WHERE year = :y AND counter = :c"),
        {"y": year, "c": counter},
    ).scalar()
    session.execute(
        text("INSERT INTO lab_dossier_ranks (year, counter, rank, patient_key, day) "
             "VALUES (:y, :c, :r, :k, :d)"),
        {"y": year, "c": counter, "r": rank, "k": patient_key, "d": day},
    )
    return DossierNumber(year, counter, rank)


def result_dossier(result) -> Optional[DossierNumber]:
    """Numero officiel d'un LabResult, ou None tant qu'il n'est pas attribue."""
    y = getattr(result, "dossier_year", None)
    c = getattr(result, "dossier_counter", None)
    r = getattr(result, "dossier_rank", None)
    if y is None or c is None or r is None:
        return None
    return DossierNumber(y, c, r)


def dossier_labels(session, results) -> Dict[int, str]:
    """{result_id: "289/02 du 08/10/2026"} pour les resultats qui ont un numero (une requete)."""
    triples = {result_dossier(r) for r in results if result_dossier(r)}
    if not triples:
        return {}
    days = {(r.year, r.counter, r.rank): r.day for r in session.execute(
        text("SELECT year, counter, rank, day FROM lab_dossier_ranks "
             "WHERE year = ANY(:ys) AND counter = ANY(:cs)"),
        {"ys": list({t.year for t in triples}), "cs": list({t.counter for t in triples})},
    )}
    out: Dict[int, str] = {}
    for r in results:
        n = result_dossier(r)
        if n and (n.year, n.counter, n.rank) in days:
            out[r.result_id] = format_dossier(n, days[(n.year, n.counter, n.rank)])
    return out


def dossier_day(session, number: DossierNumber) -> Optional[date]:
    """Jour (date de reception) d'un numero deja attribue, ou None s'il est introuvable."""
    return session.execute(
        text("SELECT day FROM lab_dossier_ranks WHERE year = :y AND counter = :c AND rank = :r"),
        {"y": number.year, "c": number.counter, "r": number.rank},
    ).scalar()


def patient_key_for(patient_id: Optional[int], external_info: Optional[Dict[str, Any]], token: Any) -> str:
    """Cle de patient pour TOUT resultat, sans jamais lever : interne `p:<id>`, externe (voir build_patient_key, `token`
    = identifiant de la reception : batch_id, ou uuid d'un resultat isole), sinon `r:<token>` (resultat sans
    identite : une cle propre a sa reception, jamais NULL)."""
    if patient_id or external_info:
        try:
            return build_patient_key(patient_id, external_info, batch_id=token)
        except ValueError:
            pass
    return f"r:{token}"


def _result_day(session, result) -> date:
    """Jour de reception d'un resultat sans numero : plus ancien test_date du lot (heure de Douala, naive), sinon le
    sien, sinon aujourd'hui."""
    from utils.business_time import business_today
    batch_id = getattr(result, "batch_id", None)
    when = None
    if batch_id:
        when = session.execute(text("SELECT MIN(test_date) FROM lab_results WHERE batch_id = :b"),
                               {"b": batch_id}).scalar()
    if when is None:
        when = getattr(result, "test_date", None)
    if isinstance(when, datetime):
        return when.date()
    return when if isinstance(when, date) else business_today()


def assign_missing_dossier(session, result) -> DossierNumber:
    """Attribue (sous le verrou consultatif) le numero manquant d'un resultat ET de tous les examens de son lot
    (batch_id) : un lot = un seul numero. Reutilise celui d'un frere s'il en a deja un. Ne commit pas."""
    from models.lab import LabResult
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": DOSSIER_LOCK_KEY})
    batch_id = getattr(result, "batch_id", None)
    where, params = ("batch_id = :b", {"b": batch_id}) if batch_id else ("result_id = :r", {"r": result.result_id})

    row = session.execute(
        text(f"SELECT dossier_year, dossier_counter, dossier_rank, patient_key FROM lab_results "
             f"WHERE {where} AND dossier_year IS NOT NULL ORDER BY result_id LIMIT 1"), params).first()
    if row:
        number, key = DossierNumber(row.dossier_year, row.dossier_counter, row.dossier_rank), row.patient_key
    else:
        token = batch_id or getattr(result, "uuid", None) or result.result_id
        key = getattr(result, "patient_key", None) or patient_key_for(
            getattr(result, "patient_id", None), getattr(result, "external_patient_info", None), token)
        number = assign_dossier(session, key, _result_day(session, result))

    if batch_id:
        targets = session.query(LabResult).filter(LabResult.batch_id == batch_id).all()
    else:
        targets = []
    if result not in targets:
        targets.append(result)
    for t in targets:
        if result_dossier(t) is None:
            t.dossier_year, t.dossier_counter, t.dossier_rank = number.year, number.counter, number.rank
            if not t.patient_key:
                t.patient_key = key
    session.flush()
    return number


def ensure_dossier_assigned(result, commit: bool = False) -> DossierNumber:
    """Numero officiel du resultat ; s'il manque (ancien resultat, reception jamais numerotee) il est ATTRIBUE ici,
    jamais refuse : l'impression n'est jamais bloquee. `commit` : valider la transaction apres l'attribution
    (routes d'impression). Leve DossierNotAssignedError seulement si l'attribution elle-meme echoue de facon
    inattendue ; l'appelant imprime alors avec le code de reference."""
    n = result_dossier(result)
    if n is not None:
        return n
    from sqlalchemy.orm import object_session
    session = object_session(result)
    if session is None:
        raise DossierNotAssignedError("Numero de dossier non attribue et resultat hors session.")
    try:
        with session.begin_nested():
            n = assign_missing_dossier(session, result)
        if commit:
            session.commit()
    except Exception as e:
        if commit:
            session.rollback()
        logging.getLogger(__name__).warning("Attribution du numero de dossier impossible (resultat %s) : %s",
                                            getattr(result, "result_id", None), e)
        raise DossierNotAssignedError("Numero de dossier non attribue.") from e
    return n
