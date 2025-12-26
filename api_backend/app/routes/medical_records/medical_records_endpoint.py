from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from typing import List, Optional

from .mapping import normalize_medical_record_data
from .schemas import MedicalRecordCreate, MedicalRecordUpdate, MedicalRecordResponse
from app.database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from controller.medical_controller import MedicalRecordController
from app.routes.auth.auth_endpoints import get_current_user,role_required

logger = logging.getLogger(__name__)

#router = APIRouter(prefix="/medical_records", tags=["Dossiers médicaux"], dependencies=[Depends(get_current_user)])
router = APIRouter(
    prefix="/medical_records",
    tags=["Dossier Medical"],
    dependencies=[Depends(role_required("medecin", "nurse"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_medical_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MedicalRecordController:
    auth_ctrl = AuthController(db_session=db)
    # Construire un PatientController léger si on a besoin de rechercher des patients depuis le controller médical
    patient_ctrl = PatientController(repo=auth_ctrl.patient_repo, current_user=current_user)
    return MedicalRecordController(repo=auth_ctrl.medical_repo, patient_controller=patient_ctrl, current_user=current_user)


@router.get("/", response_model=List[MedicalRecordResponse])
def list_records(
    patient_id: Optional[int] = Query(None, description="Filtrer par patient_id"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    medical_ctrl: MedicalRecordController = Depends(get_medical_controller)
):
    records = medical_ctrl.list_records(patient_id=patient_id, page=page, per_page=per_page)
    # Normaliser chaque enregistrement avant la validation de la réponse
    normalized = [normalize_medical_record_data(r) for r in records]
    try:
        return [MedicalRecordResponse.model_validate(r) for r in normalized]
    except ValidationError as ve:
        logger.exception("Response validation failed in list_records")
        raise HTTPException(status_code=500, detail="Erreur interne : données dossiers médicaux invalides")


@router.get("/{record_id}", response_model=MedicalRecordResponse)
def get_record(record_id: int, medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    r = medical_ctrl.get_record(record_id)
    if not r:
        raise HTTPException(status_code=404, detail="Dossier médical non trouvé")
    data = normalize_medical_record_data(r)
    try:
        return MedicalRecordResponse.model_validate(data)
    except ValidationError:
        logger.exception("Response validation failed for single record")
        raise HTTPException(status_code=500, detail="Erreur interne : données dossier médical invalides")


@router.post("/", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(data: MedicalRecordCreate, medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    # Pydantic validera la requête d'entrée automatiquement
    try:
        # Optionnel : vérifier que le patient existe (controller.patient_ctrl gère cela)
        if data.patient_id is None:
            raise HTTPException(status_code=400, detail="patient_id est requis")

        pid = medical_ctrl.create_record(data.model_dump())
        # create_record renvoie True dans ton repo ; on récupère alors le dernier enregistrement éventuellement
        # Ici on tente de récupérer le dernier dossier pour le patient (ou utiliser l'id si la proc retourne l'id)
        last = medical_ctrl.get_last_for_patient(data.patient_id)
        if not last:
            raise HTTPException(status_code=500, detail="Dossier créé mais impossible à lire")
        resp_data = normalize_medical_record_data(last)
        return MedicalRecordResponse.model_validate(resp_data)

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    except IntegrityError as ie:
        try:
            medical_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        orig = str(ie.orig).lower() if ie.orig is not None else str(ie).lower()
        # Exemple de détection : contrainte sur motif, patient etc.
        if "foreign key" in orig and "patient" in orig:
            raise HTTPException(status_code=400, detail="Patient référencé introuvable")
        logger.exception("IntegrityError creating medical record: %s", ie)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflit en base de données")

    except SQLAlchemyError as e:
        try:
            medical_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError creating medical record: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création du dossier médical")


@router.put("/{record_id}", response_model=MedicalRecordResponse)
def update_record(record_id: int, data: MedicalRecordUpdate, medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        medical_ctrl.update_record(record_id, data.model_dump(exclude_unset=True))
        r = medical_ctrl.get_record(record_id)
        if not r:
            raise HTTPException(status_code=404, detail="Dossier médical introuvable après mise à jour")
        resp = normalize_medical_record_data(r)
        return MedicalRecordResponse.model_validate(resp)

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

    except IntegrityError as ie:
        try:
            medical_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        logger.exception("IntegrityError updating medical record: %s", ie)
        raise HTTPException(status_code=409, detail="Conflit en base de données")

    except SQLAlchemyError as e:
        try:
            medical_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError updating medical record: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour du dossier médical")


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        success = medical_ctrl.delete_record(record_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dossier médical non trouvé")
    except SQLAlchemyError:
        logger.exception("SQLAlchemyError deleting medical record")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la suppression du dossier médical")
