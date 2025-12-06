# app/routes/labo/lab_endpoints.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging
from typing import Any, List

# 🔑 IMPORTATION CORRIGÉE ET SIMPLIFIÉE
# Assurez-vous que le fichier 'labo_schemas.py' existe à côté de ce fichier
# et contient toutes les classes Pydantic nécessaires.
from .labo_schemas import (
    LabResultCreate, LabResultOut, 
    ExamenCreate, ExamenUpdate, ExamenOut 
)

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user,role_required
from repositories.lab_repo import LabRepository
from controller.lab_controller import LabController


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/labo",
    tags=["labo"],
    dependencies=[Depends(role_required("laborantin","secretaire","admin","manager"))]
)

# --- Dépendances ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_lab_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> LabController:
    repo = LabRepository(db)
    return LabController(repo=repo, current_user=current_user)

def _safe_return_lab_result(lr) -> LabResultOut:
    """
    Retourne un LabResultOut validé.
    """
    try:
        return LabResultOut.model_validate(lr)
    except Exception as e:
        logger.error(f"Erreur de validation LabResultOut: {e}")
        raise HTTPException(status_code=500, detail="Erreur de validation du modèle de retour.")


# ====================================================================
# EXAMENS (CRUD pour la Configuration)
# ====================================================================

@router.post("/exams", response_model=ExamenOut, status_code=status.HTTP_201_CREATED)
def create_examen(
    payload: ExamenCreate,
    ctrl: LabController = Depends(get_lab_controller),
):
    """Crée un nouvel examen avec son prix."""
    try:
        data = payload.model_dump()
        out = ctrl.create_examen(data)
        return out
    except IntegrityError as e:
        # Utilisez 'e.orig' uniquement si e est un IntegrityError, sinon str(e)
        detail_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        raise HTTPException(
            status_code=400, 
            detail=f"Le code d'examen '{payload.code}' existe déjà ou contrainte violée: {detail_msg}"
        )
    except Exception as e:
        logger.exception("Erreur lors de la création d'examen")
        raise HTTPException(status_code=500, detail=f"Erreur interne : {e}")

@router.put("/exams/{examen_id}", response_model=ExamenOut)
def update_examen(
    examen_id: int,
    payload: ExamenUpdate,
    ctrl: LabController = Depends(get_lab_controller),
):
    """Met à jour les détails d'un examen (nom, catégorie, prix...)."""
    try:
        # N'envoyer que les champs définis (évite d'envoyer 'None' non désiré)
        data = payload.model_dump(exclude_unset=True) 
        if not data:
            raise HTTPException(status_code=400, detail="Aucune donnée fournie pour la mise à jour.")
            
        out = ctrl.update_examen(examen_id, data)
        if not out:
             raise HTTPException(status_code=404, detail=f"Examen (ID={examen_id}) non trouvé.")
        return out
    except IntegrityError as e:
        detail_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        raise HTTPException(status_code=400, detail=f"Contrainte violée: {detail_msg}")
    except Exception as e:
        logger.exception("Erreur lors de la mise à jour d'examen")
        raise HTTPException(status_code=500, detail="Erreur interne.")
        
@router.delete("/exams/{examen_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_examen(
    examen_id: int,
    ctrl: LabController = Depends(get_lab_controller),
):
    """Supprime un examen par son ID."""
    if not ctrl.delete_examen(examen_id):
        raise HTTPException(status_code=404, detail=f"Examen (ID={examen_id}) non trouvé.")
    return None 

# ====================================================================
# EXAMENS (Lecture)
# ====================================================================

@router.get("/", response_model=List[ExamenOut]) # 🔑 Retourne le modèle ExamenOut complet
def list_examens(ctrl: LabController = Depends(get_lab_controller)):
    """
    Retourne tous les examens disponibles, incluant le prix.
    """
    examens = ctrl.list_examens()
    # Pydantic va convertir la liste d'objets ORM en liste d'ExamenOut,
    # y compris la conversion Decimal en format JSON (float/string)
    return examens 

# ====================================================================
# RÉSULTATS (Création & Historique)
# ====================================================================

@router.post("/results", response_model=LabResultOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(get_current_user)])
def create_lab_result(
    payload: LabResultCreate,
    ctrl: LabController = Depends(get_lab_controller),
):
    """
    Crée un résultat labo (atomique: résultat + détails). Gère Patient Interne/Externe.
    """
    try:
        details_list: List[dict] = [d.model_dump() for d in payload.details] if payload.details else []
        
        # Le contrôleur doit accepter patient_id et external_patient_info
        out = ctrl.create_result(
            examen_id=payload.examen_id, 
            details=details_list, 
            patient_id=payload.patient_id,
            external_patient_info=payload.external_patient_info
        )

        result_id = out.get("result_id")
        if result_id is None:
            raise HTTPException(status_code=500, detail="Création échouée: pas d'identifiant retourné")

        lr = ctrl.repo.get_full_lab_result(result_id)
        if not lr:
            raise HTTPException(status_code=500, detail="Impossible de récupérer le résultat créé")

        return _safe_return_lab_result(lr)

    except IntegrityError as e:
        try:
            ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        detail_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        logger.exception("DB Integrity error: %s", detail_msg)
        raise HTTPException(status_code=400, detail=f"Erreur de contrainte DB : {detail_msg}")

    except SQLAlchemyError as e:
        try:
            ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        # 🔑 CORRECTION PYLANCE: SQLAlchemyError n'a pas toujours 'orig', utilisez str(e)
        detail_msg = str(e) 
        logger.exception("SQL error creating lab result: %s", detail_msg)
        raise HTTPException(status_code=500, detail=f"Erreur serveur DB : {detail_msg}")

    except ValueError as ve:
        # Erreur de validation Pydantic/modèle métier
        raise HTTPException(status_code=400, detail=str(ve))
    
    except Exception as e:
        try:
            ctrl.repo.session.rollback()
        except Exception:
            pass
        logger.exception("Unexpected error creating lab result")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/patient/{patient_id}/history", response_model=List[dict])
def get_patient_lab_history(
    patient_id: int,
    ctrl: LabController = Depends(get_lab_controller)
):
    """
    Récupère l'historique des résultats de laboratoire pour un patient donné.
    """
    try:
        history = ctrl.get_patient_lab_history(patient_id)
        return history
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération de l'historique labo pour le patient {patient_id}")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la récupération de l'historique labo")