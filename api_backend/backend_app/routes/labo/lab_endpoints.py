# app/routes/labo/lab_endpoints.py
import io
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from typing import Any, List, Dict, Optional

# --- IMPORTS SCHEMAS ---
from .labo_schemas import (
    LabResultCreate, 
    LabResultOut, 
    ExamenCreate, 
    ExamenUpdate, 
    ExamenOut, 
    BatchResultCreate, 
    LabStatsOut,
    PaginatedLabHistoryOut
)

# --- IMPORTS BACKEND ---
from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from api_backend.backend_app.utils.pdf_generator import build_medical_pdf
from api_backend.backend_app.utils.patient_resolution import resolve_lab_result_id_from_path
from fastapi.responses import StreamingResponse
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository
from repositories.lab_repo import LabRepository
from controller.lab_controller import LabController

logger = logging.getLogger(__name__)

# --- CONFIGURATION ROUTER ---
# NOTE: On retire la dépendance globale ici pour permettre l'accès sélectif aux médecins/infirmiers
router = APIRouter(
    prefix="/labo",
    tags=["labo"]
)

# ====================================================================
# DÉPENDANCES
# ====================================================================

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

# ====================================================================
# 1. CONFIGURATION EXAMENS & PARAMÈTRES
# ====================================================================

@router.get("/exams", response_model=List[Dict])
def list_examens(
    ctrl: LabController = Depends(get_lab_controller),
    # ✅ ACCÈS ÉLARGI : Permet au personnel de soins de voir la liste pour prescrire.
    # "secretaire" ajoutee ici (chantier dette technique 2026-09-22) : la
    # facturation d'un examen en caisse a besoin du catalogue avec prix.
    _ = Depends(role_required("laborantin", "admin", "ToxicoManager", "medecin", "nurse", "secretaire"))
):
    """Liste tous les examens (accessible au labo et personnel médical)."""
    return ctrl.list_examens()

@router.post("/exams", response_model=Dict, status_code=status.HTTP_201_CREATED, 
             dependencies=[Depends(role_required("laborantin", "admin"))])
def create_examen(payload: ExamenCreate, ctrl: LabController = Depends(get_lab_controller)):
    """Crée un nouvel examen (Admin/Labo uniquement)."""
    try:
        return ctrl.create_examen(payload.model_dump())
    except IntegrityError:
        raise HTTPException(status_code=400, detail=f"Le code '{payload.code}' existe déjà.")

@router.put("/exams/{examen_id}", response_model=Dict, 
            dependencies=[Depends(role_required("laborantin", "admin"))])
def update_examen(examen_id: int, payload: ExamenUpdate, ctrl: LabController = Depends(get_lab_controller)):
    """Met à jour un examen."""
    out = ctrl.update_examen(examen_id, payload.model_dump(exclude_unset=True))
    if not out:
        raise HTTPException(status_code=404, detail="Examen introuvable.")
    return out

@router.delete("/exams/{examen_id}", status_code=status.HTTP_204_NO_CONTENT, 
               dependencies=[Depends(role_required("admin"))])
def delete_examen(examen_id: int, ctrl: LabController = Depends(get_lab_controller)):
    """Supprime un examen (Admin uniquement)."""
    if not ctrl.delete_examen(examen_id):
        raise HTTPException(404, "Examen introuvable.")

# ====================================================================
# 2. WORKFLOW LABORATOIRE (Réservé au Staff Labo/Admin)
# ====================================================================

@router.get("/worklist", response_model=List[Dict], 
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager"))])
def get_worklist(ctrl: LabController = Depends(get_lab_controller)):
    """📋 LISTE D'ATTENTE - Uniquement pour le personnel du labo."""
    return ctrl.get_worklist()

@router.get("/paillasse", response_model=List[Dict],
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager"))])
def get_paillasse_list(ctrl: LabController = Depends(get_lab_controller)):
    """
    🧪 LISTE TECHNIQUE : Affiche les dossiers créés en attente de résultats.
    Utilisé par le technicien pour savoir quoi analyser.
    """
    # Assure-toi d'avoir ajouté get_paillasse_list dans ton Controller comme vu précédemment
    return ctrl.get_paillasse_list()

@router.get("/exams/{examen_id}/params", response_model=List[Dict])
def list_parametres(examen_id: int, ctrl: LabController = Depends(get_lab_controller)):
    """Liste les paramètres configurés pour un examen."""
    return ctrl.list_parametres(examen_id)

@router.post("/exams/{examen_id}/params", status_code=status.HTTP_201_CREATED, 
             dependencies=[Depends(role_required("laborantin", "admin"))])
def add_parametre(examen_id: int, payload: Dict[str, Any] = Body(...), ctrl: LabController = Depends(get_lab_controller)):
    try:
        return ctrl.add_parametre(examen_id, payload)
    except Exception as e:
        logger.error(f"Erreur ajout paramètre: {e}")
        raise HTTPException(status_code=500, detail="Impossible d'ajouter le paramètre.")

@router.delete("/params/{param_id}", status_code=status.HTTP_204_NO_CONTENT, 
               dependencies=[Depends(role_required("admin"))])
def delete_parametre(param_id: int, ctrl: LabController = Depends(get_lab_controller)):
    if not ctrl.delete_parametre(param_id):
        raise HTTPException(404, "Paramètre introuvable.")

# ====================================================================
# 3. GESTION DES RÉSULTATS
# ====================================================================

@router.get("/history/paginated", response_model=PaginatedLabHistoryOut, 
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager", "medecin", "nurse"))])
def get_paginated_history(
    page: int = Query(1, ge=1, description="Numéro de la page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments par page"),
    search: Optional[str] = Query(None, description="Recherche par nom ou code"),
    status: Optional[str] = Query(None, description="Filtre par statut (pending, completed, etc.)"),
    ctrl: LabController = Depends(get_lab_controller)
):
    """
    📚 HISTORIQUE PAGINÉ : Récupère la liste globale des résultats avec pagination et filtres.
    Idéal pour le tableau principal du frontend.
    """
    return ctrl.get_paginated_results(page=page, limit=limit, search=search, status=status)

# Lecture de donnees d'analyses : soignants + admin uniquement, meme jeu de
# roles que les autres routes de lecture de ce module (lignes 66 et 141).
# Le secretariat en est volontairement exclu - ce n'est pas un oubli : ces
# routes etaient ouvertes a tout compte authentifie, ce qui laissait la
# secretaire lire n'importe quel resultat d'examen.
@router.get("/search", response_model=List[Dict],
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager", "medecin", "nurse"))])
def search_lab_files(q: str = Query(..., min_length=2), ctrl: LabController = Depends(get_lab_controller)):
    return ctrl.search_lab_files(q)

@router.get("/search-internal", response_model=List[Dict],
            # medecin/nurse retires : cet endpoint sert le workflow "creer
            # un nouveau resultat", deja hors de leur portee (POST
            # /labo/results les exclut). Aucun ecran medical ne l'appelle
            # (seul LabReception.vue, jamais monte sous /medical/*).
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager"))])
def search_internal_patients(q: str = Query(""), ctrl: LabController = Depends(get_lab_controller)):
    return ctrl.search_internal_with_prescriptions(q)

@router.get("/batch/{batch_id}", response_model=List[LabResultOut],
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager", "medecin", "nurse"))])
def get_results_by_batch(batch_id: str, ctrl: LabController = Depends(get_lab_controller)):
    return ctrl.get_results_by_batch_id(batch_id)    

@router.post("/results", status_code=status.HTTP_201_CREATED, 
             dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager"))])
def create_single_result(payload: LabResultCreate, ctrl: LabController = Depends(get_lab_controller)):
    try:
        details_list = [d.model_dump() for d in payload.details] if payload.details else []
        return ctrl.create_result(
            examen_id=payload.examen_id,
            details=details_list, # type: ignore
            patient_id=payload.patient_id,
            external_patient_info=payload.external_patient_info,
            origin_prescription_id=payload.origin_prescription_id
        )
    except Exception as e:
        logger.exception("Erreur création résultat")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{result_id}", response_model=Dict,
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager", "medecin", "nurse"))])
def get_result_detail(result_id: int, ctrl: LabController = Depends(get_lab_controller)):
    try:
        res = ctrl.get_result_detail(result_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not res:
        raise HTTPException(status_code=404, detail="Dossier introuvable.")
    return res

@router.put("/results/{result_id}/values",
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager"))])
def update_result_values(result_id: str, payload: Dict[str, Any] = Body(...), ctrl: LabController = Depends(get_lab_controller)):
    try:
        resolved_id = resolve_lab_result_id_from_path(ctrl.repo.session, result_id)
        values = payload.get("values", {})
        completed = payload.get("completed", False)
        global_note = payload.get("note", None)
        return ctrl.submit_values(resolved_id, values, completed, global_note)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur sauvegarde valeurs {result_id}")
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde.")

@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT, 
               dependencies=[Depends(role_required("admin"))])
def delete_result(result_id: int, ctrl: LabController = Depends(get_lab_controller)):
    if not ctrl.delete_result(result_id):
        raise HTTPException(status_code=404, detail="Dossier introuvable.")

@router.post("/results/batch", status_code=status.HTTP_201_CREATED, 
             dependencies=[Depends(role_required("laborantin", "admin"))])
def create_batch_results(
    payload: BatchResultCreate, 
    ctrl: LabController = Depends(get_lab_controller),
    current_user = Depends(get_current_user)  # <-- 1. AJOUT ICI
):
    try:
        # 2. On passe payload ET current_user au contrôleur
        return ctrl.create_batch_results(payload.model_dump(), current_user)
    except HTTPException:
        # 4xx metier (patient_uuid irresoluble, examen supprime...) : doit
        # rester un 4xx pour que DossierConnector.isFatalUploadError() mette
        # l'operation en quarantaine au lieu de la rejouer indefiniment.
        raise
    except Exception as e:
        logger.exception("Erreur batch")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patient/{patient_id}/history", response_model=List[Dict],
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager", "medecin", "nurse"))])
def get_patient_history(patient_id: int, ctrl: LabController = Depends(get_lab_controller)):
    return ctrl.get_patient_lab_history(patient_id)

# ====================================================================
# 4. STATISTIQUES (Admin / Manager uniquement)
# ====================================================================

@router.get("/stats", response_model=LabStatsOut, 
            dependencies=[Depends(role_required("admin", "ToxicoManager","laborantin"))])
def get_lab_stats(
    period: str = "month", # <-- AJOUT DU PARAMÈTRE ICI
    ctrl: LabController = Depends(get_lab_controller)
):
    return ctrl.get_dashboard_stats(period) 

@router.get("/results/{result_id}/pdf", tags=["Labo PDF"],
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager", "medecin", "nurse"))])
def download_result_pdf(
    result_id: int,
    db: Session = Depends(get_db),
    lab_ctrl: LabController = Depends(get_lab_controller) # <-- CORRECTION ERREUR 3
):
    """
    Génère et retourne le PDF des résultats d'un examen de laboratoire.
    """
    # 1. Initialisation propre du ConfigController via son Repo
    config_repo = ConfigRepository(db)
    config_ctrl = ConfigController(repo=config_repo)

    # 2. Récupérer TOUTES les données pré-formatées pour l'impression
    try:
        print_data = lab_ctrl.get_print_data(result_id, config_ctrl)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not print_data:
        raise HTTPException(status_code=404, detail=f"Résultat {result_id} introuvable")

    # 3. Génération du PDF 
    try:
        # Pylance râle ici pour le moment, c'est normal !
        pdf_bytes = build_medical_pdf(print_data)
    except Exception as e:
        logger.exception(f"Erreur lors de la génération du PDF pour le résultat {result_id}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création du document PDF")

    # 4. Renvoyer le fichier au frontend
    filename = f"Resultat_{print_data['examen']['code']}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes), 
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )