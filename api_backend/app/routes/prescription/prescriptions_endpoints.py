# app/routes/prescriptions/prescriptions_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from typing import List

from app.database import SessionLocal
from repositories.prescription_repo import PrescriptionRepository
from controller.prescription_controller import PrescriptionController
from app.routes.auth.auth_endpoints import get_current_user,role_required
from .mapping import normalize_prescription_data
from .prescriptions_schemas import PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse

logger = logging.getLogger(__name__)
#router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"], dependencies=[Depends(get_current_user)])
router = APIRouter(
    prefix="/prescriptions",
    tags=["Prescriptions"],
    dependencies=[Depends(role_required("medecin", "nurse"))]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_prescription_controller(current_user=Depends(get_current_user),
                               db: Session = Depends(get_db)) -> PrescriptionController:
    # ton PrescriptionController accepte repo=None -> il créera le repo si tu veux
    # pour clarté on l'injecte explicitement
    repo = PrescriptionRepository(db)
    return PrescriptionController(repo=repo, patient_controller=None, current_user=current_user)

def _validate_and_normalize_single(obj):
    data = normalize_prescription_data(obj)
    try:
        return PrescriptionResponse.model_validate(data)
    except ValidationError as e:
        logger.exception("Response validation failed for prescription")
        raise HTTPException(status_code=500, detail="Erreur interne : données prescription invalides")

@router.get("/", response_model=List[PrescriptionResponse])
def list_prescriptions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    patient_id: int | None = Query(None),
    prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)
):
    items = prescription_ctrl.list_prescriptions(patient_id=patient_id, page=page, per_page=per_page)
    # items = list d'ORM objects -> normaliser chacun
    results = []
    errors = []
    for idx, it in enumerate(items):
        try:
            results.append(_validate_and_normalize_single(it))
        except HTTPException:
            errors.append(idx)
    if errors:
        raise HTTPException(status_code=500, detail="Erreur interne : certaines prescriptions en base sont invalides")
    return results

@router.get("/{prescription_id}", response_model=PrescriptionResponse)
def get_prescription(prescription_id: int, prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)):
    p = prescription_ctrl.get_prescription(prescription_id)
    if not p:
        raise HTTPException(status_code=404, detail="Prescription non trouvée")
    return _validate_and_normalize_single(p)

@router.post("/", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(data: PrescriptionCreate, prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)):
    payload = data.model_dump()
    # contrôles business rapides
    if payload.get("end_date") and payload.get("start_date") and payload["start_date"] > payload["end_date"]:
        raise HTTPException(status_code=400, detail="start_date doit être antérieure ou égale à end_date")
    try:
        prescription_ctrl.create_prescription(payload)
        # repo.create retourne True dans ton code ; récupérer l'objet créé via une requete si tu veux:
        # ici on cherche la dernière prescription pour le patient+medicament (optionnel)
        # pour simplicité, renvoyons la ressource via un get après création s'il existe un identifiant retourné par ton repo
        # comme repo.create() renvoie True, on revient à une lecture par recherche (complexe)
        # Alternative simple: demander au repo de renvoyer l'objet créé (à améliorer côté repo)
        raise HTTPException(status_code=201, detail="Prescription créée (vérifier lecture si nécessaire)")
    except IntegrityError as ie:
        try:
            prescription_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        logger.exception("IntegrityError creating prescription: %s", ie)
        raise HTTPException(status_code=409, detail="Conflit en base de données")
    except SQLAlchemyError as e:
        try:
            prescription_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError creating prescription: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création de la prescription")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.put("/{prescription_id}", response_model=PrescriptionResponse)
def update_prescription(prescription_id: int, data: PrescriptionUpdate, prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)):
    # IMPORTANT: n'utilise pas exclude_unset=True si ta proc stockée attend tous les bind params.
    payload = data.model_dump()  # si tu veux envoyer toutes les clefs, même si None
    # ensure patient_id present (repo.update remplit s'il manque)
    try:
        prescription_ctrl.update_prescription(prescription_id, payload)
        updated = prescription_ctrl.get_prescription(prescription_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Prescription introuvable après mise à jour")
        return _validate_and_normalize_single(updated)
    except IntegrityError as ie:
        try:
            prescription_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        logger.exception("IntegrityError updating prescription: %s", ie)
        raise HTTPException(status_code=409, detail="Conflit en base de données")
    except SQLAlchemyError as e:
        try:
            prescription_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError updating prescription: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour de la prescription")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(prescription_id: int, prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)):
    try:
        ok = prescription_ctrl.delete_prescription(prescription_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Prescription non trouvée")
        return None
    except SQLAlchemyError:
        try:
            prescription_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError deleting prescription")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la suppression")
