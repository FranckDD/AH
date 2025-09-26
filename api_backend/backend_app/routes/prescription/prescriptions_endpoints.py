from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from typing import List, Optional, Any, Dict
from fastapi import Query
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from api_backend.backend_app.database import SessionLocal
from repositories.prescription_repo import PrescriptionRepository
from controller.prescription_controller import PrescriptionController
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from .mapping import normalize_prescription_data
from .prescriptions_schemas import PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse


logger = logging.getLogger(__name__)

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
    repo = PrescriptionRepository(db)
    return PrescriptionController(repo=repo, patient_controller=None, current_user=current_user)

def _validate_and_normalize_single(obj: Any) -> PrescriptionResponse:
    try:
        # Si c'est un ORM / objet, convertis en dict (jsonable_encoder gère datetimes, relations simples)
        if hasattr(obj, "__dict__") and not isinstance(obj, dict):
            data = jsonable_encoder(obj)
        else:
            # si déjà dict-like, utilise la normalisation spécifique
            data = normalize_prescription_data(obj)

        # validate with pydantic from dict
        return PrescriptionResponse.model_validate(data)

    except ValidationError as ve:
        logger.exception("Response validation failed for prescription: %s", ve)
        raise HTTPException(status_code=500, detail="Erreur interne : données prescription invalides")
    except Exception as e:
        logger.exception("Unexpected error validating prescription response: %s", e)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la validation de la prescription")



@router.get("/", response_model=Dict[str, Any])
def list_prescriptions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    patient_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description="Recherche par code patient ou médicament"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)
) -> Dict[str, Any]:
    try:
        res = prescription_ctrl.list_prescriptions(
            page=page, per_page=per_page,
            date_from=date_from, date_to=date_to,
            patient_id=patient_id, search=search
        )
    except Exception as e:
        logger.exception("Erreur lors de l'appel controller.list_prescriptions: %s", e)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {e}")

    items = res.get("data") or []
    results = []
    invalid = []  # contiendra dicts {index, error, raw_preview}
    for idx, it in enumerate(items):
        try:
            normalized = _validate_and_normalize_single(it)
            results.append(normalized)
        except HTTPException as he:
            # garde l'erreur mais ne stoppe pas toute la requête
            try:
                raw_preview = str(it)[:200]
            except Exception:
                raw_preview = "<unprintable object>"
            logger.warning("Prescription invalide index=%s error=%s raw=%s", idx, he.detail, raw_preview)
            invalid.append({"index": idx, "error": (he.detail if isinstance(he.detail, str) else str(he.detail)), "raw_preview": raw_preview})
        except Exception as e:
            # erreur inattendue lors de la normalisation
            try:
                raw_preview = str(it)[:200]
            except Exception:
                raw_preview = "<unprintable object>"
            logger.exception("Erreur inattendue lors de la validation d'une prescription index=%s: %s", idx, e)
            invalid.append({"index": idx, "error": str(e), "raw_preview": raw_preview})

    response = {
        "data": results,
        "total": res.get("total", len(results)),
        "page": res.get("page", page),
        "per_page": res.get("per_page", per_page)
    }
    if invalid:
        # ajoute la clé invalid pour debug; le client peut l'afficher dans console/log
        response["invalid"] = invalid
        # on choisit de renvoyer 200 pour que l'UI ait quelque chose d'affichable
        # si tu préfères conserver le 500, tu peux lever HTTPException ici en incluant invalid[0]
    return response




@router.post("/", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(
    data: PrescriptionCreate,
    prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)
):
    payload = data.model_dump()

    # Vérification logique côté API avant envoi au repo
    if payload.get("end_date") and payload.get("start_date") and payload["start_date"] > payload["end_date"]:
        raise HTTPException(
            status_code=400,
            detail="start_date doit être antérieure ou égale à end_date"
        )

    # 1) Création : attrape les erreurs SQL/Integrity ici pour renvoyer des HTTP appropriés
    try:
        created = prescription_ctrl.create_prescription(payload)
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
    except Exception as e:
        # Erreur inattendue
        logger.exception("Unexpected error creating prescription: %s", e)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création : {str(e)}")

    # 2) Interpréter le retour du repo (procédure => True)
    obj = None

    # (cas général si repo évoluerait un jour pour renvoyer un id ou un objet)
    if isinstance(created, int):
        try:
            obj = prescription_ctrl.get_prescription(created)
        except Exception:
            logger.exception("Failed to fetch newly created prescription by id")
            obj = None
    elif hasattr(created, "__dict__") or isinstance(created, dict):
        obj = created
    elif created is True or created is None:
        # La procédure a réussi (True). Tenter de retrouver la prescription la plus récente du patient
        patient_id = payload.get("patient_id")
        if patient_id:
            try:
                recent = prescription_ctrl.list_prescriptions(patient_id=patient_id, page=1, per_page=1)
                obj = recent[0] if recent else None # type: ignore
            except Exception:
                logger.exception("Failed to fetch recent prescription after create")
                obj = None

    # 3) Si on n'a pas pu retrouver l'objet, renvoyer 201 sans body détaillé (évite 500)
    if obj is None:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"detail": "Prescription créée (lecture non disponible)"}
        )

    # 4) Normaliser/valider et retourner l'objet
    return _validate_and_normalize_single(obj)



@router.put("/{prescription_id}", response_model=PrescriptionResponse)
def update_prescription(prescription_id: int, data: PrescriptionUpdate, prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)):
    payload = data.model_dump()
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
    
@router.get("/renewals", response_model=List[PrescriptionResponse])
def prescription_renewals(
    within_days: int = Query(14, ge=1, le=60, description="Nombre de jours pour chercher les renouvellements"),
    prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)
):
    try:
        items = prescription_ctrl.renewals_for_doctor(within_days=within_days)
        return [_validate_and_normalize_single(it) for it in items]
    except Exception as e:
        logger.exception("Erreur prescription_renewals")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des renouvellements")

    
@router.get("/kpi/count")
def kpi_count_prescriptions(period: str = Query("day", regex="^(day|week)$"), prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)):
    try:
        cnt = prescription_ctrl.count_prescriptions(period=period)
        return {"count": cnt}
    except SQLAlchemyError:
        logger.exception("Erreur DB count_prescriptions")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI")
    

@router.get("/{prescription_id}", response_model=PrescriptionResponse)
def get_prescription(prescription_id: int, prescription_ctrl: PrescriptionController = Depends(get_prescription_controller)):
    p = prescription_ctrl.get_prescription(prescription_id)
    if not p:
        raise HTTPException(status_code=404, detail="Prescription non trouvée")
    return _validate_and_normalize_single(p)


