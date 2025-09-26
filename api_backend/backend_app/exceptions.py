# app/exceptions.py
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

def translate_integrity_error(ie: IntegrityError) -> HTTPException:
    """
    Retourne une HTTPException appropriée pour une IntegrityError donnée.
    Ne fait pas de rollback ici (handler caller doit rollback si nécessaire).
    """
    orig = getattr(ie, "orig", None)
    msg = str(orig).lower() if orig is not None else str(ie).lower()

    # doublon national_id (Postgres message observed)
    if "national_id" in msg or "patients_national_id_key" in msg or "patients_national_id" in msg:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un patient avec le même national_id existe déjà."
        )

    # autres contraintes uniques (générique)
    if "unique" in msg or "duplicate" in msg or "unique constraint" in msg:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflit d'intégrité en base de données (valeur dupliquée)."
        )

    # fallback
    logger.exception("IntegrityError not specifically handled: %s", msg)
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflit d'intégrité en base de données.")
