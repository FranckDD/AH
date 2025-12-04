from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging
from datetime import datetime
from math import ceil

from api_backend.backend_app.database import SessionLocal
from controller.caisse_retrait_controller import CaisseRetraitController
from repositories.caisse_retrait_repo import CaisseRetraitRepository
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from api_backend.backend_app.exceptions import translate_integrity_error
from .mapping import normalize_retrait_data

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/retrait",
    tags=["Caisse Retrait"],
    dependencies=[Depends(role_required("secretaire", "admin"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_retrait_controller(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    retrait_repo = CaisseRetraitRepository(session=db)
    return CaisseRetraitController(repo=retrait_repo, current_user=current_user)

# ==========================================
# 1. ROUTES STATIQUES (EN PREMIER)
# ==========================================

@router.get("/total", response_model=float)
def get_total_retraits(
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    retrait_ctrl: CaisseRetraitController = Depends(get_retrait_controller),
):
    """
    Calcule la somme des retraits selon les filtres.
    Doit être placé AVANT /{retrait_id}.
    """
    # Assure-toi que ton CaisseRetraitController a bien cette méthode 'get_total_retraits'
    return retrait_ctrl.get_total_retraits(status=status, date_from=date_from, date_to=date_to)

@router.get("/", response_model=Any) # response_model changé en Any pour permettre la pagination {data, total} si besoin
def list_retraits(
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    retrait_ctrl: CaisseRetraitController = Depends(get_retrait_controller),
):
    # Note: Idéalement, ton controller devrait aussi renvoyer un tuple (items, count) pour la pagination réelle
    # Ici, on garde ta logique actuelle mais on pourrait l'adapter comme pour Caisse
    raws = retrait_ctrl.list_retraits(status=status, date_from=date_from, date_to=date_to)
    
    # Pagination en Python (si pas faite en SQL dans le repo)
    total_count = len(raws)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = raws[start:end]
    
    data = [normalize_retrait_data(x) for x in page_items]
    
    # On renvoie une structure paginée pour uniformiser avec Caisse
    return {
        "data": data,
        "total": total_count,
        "page": page,
        "per_page": per_page
    }

@router.get("/search", response_model=Any)
def search_retraits_paginated(
    term: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    retrait_ctrl: CaisseRetraitController = Depends(get_retrait_controller),
):
    """
    Route dédiée au module Finance (Pagination SQL).
    """
    result = retrait_ctrl.search_retraits(
        page=page,
        per_page=per_page,
        status=status,
        date_from=date_from,
        date_to=date_to,
        term=term
    )
    
    # Mapping des données
    data = [normalize_retrait_data(item) for item in result["items"]]
    
    return {
        "data": data,
        "total": result["total"],
        "page": result["page"],
        "per_page": result["per_page"]
    }

# ==========================================
# 2. ROUTES DYNAMIQUES (EN DERNIER)
# ==========================================

@router.get("/{retrait_id}", response_model=Any)
def get_retrait(retrait_id: int, retrait_ctrl: CaisseRetraitController = Depends(get_retrait_controller)):
    try:
        retrait = retrait_ctrl.get_retrait(retrait_id)
        return normalize_retrait_data(retrait)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/", response_model=Any, status_code=status.HTTP_201_CREATED)
def create_retrait(
    amount: float = Body(..., gt=0),
    justification: str = Body(...),
    # 🟢 Récupération des nouveaux champs (Optionnels)
    category: Optional[str] = Body(None),
    payment_method: Optional[str] = Body(None),
    retrait_ctrl: CaisseRetraitController = Depends(get_retrait_controller),
):
    try:
        # On passe tout au contrôleur
        retrait = retrait_ctrl.effectuer_retrait(
            amount=amount, 
            justification=justification,
            category=category,
            payment_method=payment_method
        )
        return normalize_retrait_data(retrait)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except IntegrityError as ie:
        try:
            retrait_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try:
            retrait_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@router.post("/{retrait_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_retrait(
    retrait_id: int,
    cancel_justification: str = Body(..., embed=True), # embed=True permet d'attendre {"cancel_justification": "..."}
    retrait_ctrl: CaisseRetraitController = Depends(get_retrait_controller),
):
    try:
        retrait_ctrl.annuler_retrait(retrait_id=retrait_id, cancel_justification=cancel_justification)
        return {"detail": "Retrait annulé avec succès"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))