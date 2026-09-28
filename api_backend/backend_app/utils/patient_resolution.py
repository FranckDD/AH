import uuid as uuid_lib
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session


def resolve_patient_id(session: Session, patient_id: Optional[int], patient_uuid: Optional[str]) -> int:
    """patient_id a utiliser pour une creation de consultation/prescription.

    Chantier 4 sous-projet 4 : un patient cree hors ligne n'a pas encore
    d'identifiant serveur cote client - ses consultations/prescriptions
    hors ligne portent seulement son uuid. La file PowerSync etant ordonnee,
    le patient est toujours cree cote serveur avant elles : on le retrouve
    ici par son uuid (index unique patients_uuid_key, migration 010).
    """
    if patient_id is not None:
        return patient_id
    if not patient_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id ou patient_uuid est requis")
    try:
        normalized = str(uuid_lib.UUID(str(patient_uuid)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="patient_uuid invalide")
    row = session.execute(
        text("SELECT patient_id FROM patients WHERE uuid = CAST(:u AS uuid) AND is_deleted = false"),
        {"u": normalized},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Patient introuvable pour ce patient_uuid")
    return int(row[0])


def resolve_medical_record_id(session: Session, medical_record_id: Optional[int], medical_record_uuid: Optional[str]) -> Optional[int]:
    """medical_record_id a utiliser pour une prescription liee a une
    consultation - meme motif que resolve_patient_id ci-dessus. Contrairement
    au patient, le lien est optionnel : si ni l'un ni l'autre n'est fourni,
    la prescription n'est simplement liee a aucune consultation (retour
    None), ce n'est pas une erreur."""
    if medical_record_id is not None:
        return medical_record_id
    if not medical_record_uuid:
        return None
    try:
        normalized = str(uuid_lib.UUID(str(medical_record_uuid)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="medical_record_uuid invalide")
    row = session.execute(
        text("SELECT record_id FROM medical_records WHERE uuid = CAST(:u AS uuid)"),
        {"u": normalized},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Consultation introuvable pour ce medical_record_uuid")
    return int(row[0])


def resolve_lab_result_id(session: Session, result_id: Optional[int], result_uuid: Optional[str]) -> int:
    """result_id a utiliser pour une saisie de valeurs labo - meme motif que
    resolve_patient_id/resolve_medical_record_id. Contrairement a la
    consultation, le lien est obligatoire ici : on ne peut pas saisir des
    valeurs sans savoir a quel dossier elles appartiennent."""
    if result_id is not None:
        return result_id
    if not result_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="result_id ou result_uuid est requis")
    try:
        normalized = str(uuid_lib.UUID(str(result_uuid)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="result_uuid invalide")
    row = session.execute(
        text("SELECT result_id FROM lab_results WHERE uuid = CAST(:u AS uuid)"),
        {"u": normalized},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dossier labo introuvable pour ce result_uuid")
    return int(row[0])


def resolve_lab_result_id_from_path(session: Session, raw_id: str) -> int:
    """result_id a partir d'un segment d'URL qui peut etre soit l'entier
    server_id (dossier deja synchronise), soit l'uuid local d'un dossier
    cree hors ligne pas encore confirme - saisie de valeurs sur un dossier
    lui-meme cree hors ligne dans le meme geste (enchainement complet,
    decision utilisateur 2026-09-24)."""
    try:
        return int(raw_id)
    except ValueError:
        return resolve_lab_result_id(session, None, raw_id)
