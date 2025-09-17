from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import logging
from typing import List, Optional
from datetime import date

from fastapi.responses import JSONResponse

from .mapping import normalize_medical_record_data
from .schemas import MedicalRecordCreate, MedicalRecordUpdate, MedicalRecordResponse,PaginatedResponse
from app.database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from controller.medical_controller import MedicalRecordController
from app.routes.auth.auth_endpoints import get_current_user, role_required
from app.routes.patients.patients_schemas import PatientResponse

logger = logging.getLogger(__name__)

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
    patient_ctrl = PatientController(repo=auth_ctrl.patient_repo, current_user=current_user)
    return MedicalRecordController(repo=auth_ctrl.medical_repo, patient_controller=patient_ctrl, current_user=current_user)


# endpoints/medical_records.py
@router.get("/", response_model=PaginatedResponse[MedicalRecordResponse])
def list_records(
    patient_id: Optional[int] = Query(None, description="Filtrer par patient_id"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=30000),
    date_from: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    motif_code: Optional[str] = Query(None, description="Filtrer par code motif"),
    severity: Optional[str] = Query(None, description="Filtrer par gravité (low, medium, high)"),
    search: Optional[str] = Query(None, description="Recherche texte (code patient, nom)"),
    medical_ctrl: MedicalRecordController = Depends(get_medical_controller)
):
    try:
        # Conversion des valeurs de gravité pour l'API
        severity_map = {"Faible": "low", "Moyen": "medium", "Élevé": "high"}
        if severity in severity_map:
            severity = severity_map[severity]
            
        logger.info(f"API Params - page: {page}, per_page: {per_page}, severity: {severity}")
        
        # Appeler le contrôleur avec tous les filtres
        result = medical_ctrl.list_records(
            patient_id=patient_id,
            page=page,
            per_page=per_page,
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to) if date_to else None,
            motif_code=motif_code,
            severity=severity,
            search=search
        )
        
        logger.info(f"API Result - total: {result.get('total')}, data: {len(result.get('data', []))}")
        
        # Normaliser et valider les données
        normalized = [normalize_medical_record_data(r) for r in result["data"]]
        validated_data = [MedicalRecordResponse.model_validate(r) for r in normalized]
        
        return PaginatedResponse(
            data=validated_data,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"]
        )
        
    except ValidationError:
        logger.exception("Response validation failed in list_records")
        raise HTTPException(status_code=500, detail="Erreur interne : données dossiers médicaux invalides")
    except Exception as e:
        logger.exception("Error in list_records: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des dossiers")
    
    # Dans votre endpoint FastAPI
@router.get("/motifs", response_model=List[dict])
def list_motifs(medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        return medical_ctrl.list_motifs()
    except SQLAlchemyError:
        logger.exception("Erreur DB list_motifs")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des motifs")



@router.post("/", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(data: MedicalRecordCreate, medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        if data.patient_id is None:
            raise HTTPException(status_code=400, detail="patient_id est requis")

        created = medical_ctrl.create_record(data.model_dump())
        # tenter de retourner le dernier dossier du patient (fallback si create ne renvoie pas l'objet)
        last = medical_ctrl.get_last_for_patient(data.patient_id)
        if not last:
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={"detail": "Dossier créé (lecture non disponible)"})
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


# ---- Endpoints supplémentaires / KPI / recherche ----

"""@router.get("/find_patient", response_model=MedicalRecordResponse)
def find_patient(q: str = Query(..., description="id numérique ou code_patient"), medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        p = medical_ctrl.find_patient(q)
        if not p:
            raise HTTPException(status_code=404, detail="Patient non trouvé")
        # retourne l'objet patient (normalisation si nécessaire) — ici on réutilise la logique du patient controller si besoin
        return p
    except SQLAlchemyError:
        logger.exception("Erreur DB find_patient")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la recherche du patient")"""
@router.get("/find_patient", response_model=PatientResponse)
def find_patient(q: str = Query(..., description="id numérique ou code_patient"),
                 medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        p = medical_ctrl.find_patient(q)
        if not p:
            raise HTTPException(status_code=404, detail="Patient non trouvé")
        return p
    except SQLAlchemyError:
        logger.exception("Erreur DB find_patient")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la recherche du patient")
    except Exception as e:
        logger.exception("Erreur inattendue find_patient: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur inattendue lors de la recherche du patient")

@router.get("/last_for_patient/{patient_id}", response_model=MedicalRecordResponse)
def last_for_patient(patient_id: int, medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        r = medical_ctrl.get_last_for_patient(patient_id)
        if not r:
            raise HTTPException(status_code=404, detail="Aucun dossier trouvé pour le patient")
        resp = normalize_medical_record_data(r)
        return MedicalRecordResponse.model_validate(resp)
    except SQLAlchemyError:
        logger.exception("Erreur DB last_for_patient")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture du dernier dossier")

@router.get("/kpi/count_records")
def kpi_count_records(doctor_id: Optional[int] = Query(None), start: Optional[date] = Query(None), end: Optional[date] = Query(None), medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        cnt = medical_ctrl.count_records_for_doctor(doctor_id=doctor_id, start=start, end=end)
        return {"count": cnt}
    except SQLAlchemyError:
        logger.exception("Erreur DB kpi_count_records")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI")

@router.get("/kpi/consultation_distribution")
def kpi_consultation_distribution(doctor_id: Optional[int] = Query(None), start: Optional[date] = Query(None), end: Optional[date] = Query(None), medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        data = medical_ctrl.consultation_type_distribution(doctor_id=doctor_id, start=start, end=end)
        return data
    except SQLAlchemyError:
        logger.exception("Erreur DB kpi_consultation_distribution")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI")

@router.get("/kpi/count_preconsultations")
def kpi_count_preconsultations(period: str = Query("day", regex="^(day|week)$"), medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        cnt = medical_ctrl.count_preconsultations(period=period)
        return {"count": cnt}
    except SQLAlchemyError:
        logger.exception("Erreur DB kpi_count_preconsultations")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI")

@router.get("/kpi/count_consultations")
def kpi_count_consultations(period: str = Query("day", regex="^(day|week)$"), medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        cnt = medical_ctrl.count_consultations(period=period)
        return {"count": cnt}
    except SQLAlchemyError:
        logger.exception("Erreur DB kpi_count_consultations")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI")
    

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
