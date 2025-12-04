from fastapi.responses import FileResponse, Response
from starlette.background import BackgroundTasks
import os
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging
from datetime import date, datetime
from math import ceil

from api_backend.backend_app.database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from controller.caisse_controller import CaisseController
from repositories.caisse_repo import CaisseRepository
from repositories.audit_repo import AuditRepository
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from api_backend.backend_app.exceptions import translate_integrity_error
from .mapping import normalize_caisse_data
from ..caisse.caisse_schemas import (
    FinancialKpiSchema, 
    UnpaidTransactionSchema, 
    PaymentDistributionSchema, 
    PaymentDistributionItem,
    InstallmentPaymentIn
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/caisse",
    tags=["Caisse"],
    dependencies=[Depends(role_required("secretaire", "admin"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_caisse_controller(
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
) -> CaisseController:
    # 1. Créer les repos
    caisse_repo = CaisseRepository(session=db)
    audit_repo = AuditRepository(db)
    
    # 2. Créer le controller avec injection
    return CaisseController(
        repo=caisse_repo, 
        current_user=current_user,
        audit_repo=audit_repo
    )

# =================================================================
# 1. ROUTES STATIQUES & TABLEAUX DE BORD (Doivent être en premier)
# =================================================================

@router.get("/daily_total", response_model=float)
def daily_total(for_date: date = Query(...), caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    return caisse_ctrl.get_daily_total(for_date)

@router.get("/total", response_model=float)
def total_transactions(
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    return caisse_ctrl.get_total_transactions(status=status, date_from=date_from, date_to=date_to)

@router.get("/total_payments", response_model=float)
def total_payments(
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    """
    Retourne la somme des encaissements réels (advance_amount/total payé).
    """
    return caisse_ctrl.get_total_payments(status=status, date_from=date_from, date_to=date_to) 

@router.get("/total_remaining_due", response_model=float)
def total_remaining_due(
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    """
    Retourne la somme totale des montants restant dûs sur les transactions actives.
    """
    return caisse_ctrl.get_total_remaining_due(status=status, date_from=date_from, date_to=date_to)

@router.get("/patient/{patient_id}", response_model=List[Any])
def list_for_patient(patient_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    items = caisse_ctrl.list_for_patient(patient_id)
    return [normalize_caisse_data(x) for x in items]

# --- DASHBOARD KPIs ---

@router.get("/dashboard/caisse/kpis", response_model=FinancialKpiSchema, tags=["Dashboard", "Caisse"])
def get_caisse_financial_kpis(
    date_from: date = Query(..., description="Date de début"),
    date_to: date = Query(..., description="Date de fin"),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        return caisse_ctrl.get_financial_kpis(date_from, date_to)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des KPIs financiers.")

@router.get("/dashboard/caisse/unpaid", response_model=List[UnpaidTransactionSchema], tags=["Dashboard", "Caisse"])
def get_caisse_unpaid_list(
    date_from: date = Query(..., description="Date de début"),
    date_to: date = Query(..., description="Date de fin"),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        return caisse_ctrl.get_unpaid_action_list(date_from, date_to)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la liste d'impayés.")

@router.get("/dashboard/caisse/payment_distribution", response_model=PaymentDistributionSchema, tags=["Dashboard", "Caisse"])
def get_caisse_payment_distribution(
    date_from: date = Query(..., description="Date de début"),
    date_to: date = Query(..., description="Date de fin"),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    """
    Récupère la répartition du total encaissé par mode de paiement.
    """
    try:
        distribution_dict = caisse_ctrl.get_payment_distribution_kpi(date_from, date_to)
        
        distribution_list = [
            PaymentDistributionItem(method=method, total=total) 
            for method, total in distribution_dict.items()
        ]
        
        return PaymentDistributionSchema(distribution=distribution_list)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Erreur lors de la récupération de la distribution des paiements.")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la distribution des paiements.")

# ==========================================
# 2. LISTE GÉNÉRALE (SEARCH)
# ==========================================

@router.get("/", response_model=Any)
def list_transactions(
    term: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    result = caisse_ctrl.search_transactions(
        term=term,
        payment_method=payment_method,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page
    )

    items_models = result["items"]
    total_count = result["total"]
    data = [normalize_caisse_data(x) for x in items_models]
    total_pages = ceil(total_count / per_page) if per_page > 0 else 1

    return {
        "data": data,
        "total": total_count,
        "page": page,
        "per_page": per_page
    }

# ==========================================
# 3. CRÉATION (POST /)
# ==========================================

@router.post("/", response_model=Any, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: dict = Body(...),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        tx = caisse_ctrl.create_transaction(data)
        return normalize_caisse_data(tx)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except IntegrityError as ie:
        try: caisse_ctrl.repo.session.rollback()
        except: pass
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try: caisse_ctrl.repo.session.rollback()
        except: pass
        logger.exception("SQLAlchemyError creating transaction: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création de la transaction")

# ==========================================
# 4. ACTIONS SPÉCIFIQUES SUR ID (POST)
#    (Placées AVANT les routes génériques {id})
# ==========================================

@router.post("/{transaction_id}/payment", status_code=status.HTTP_201_CREATED)
def add_payment(
    transaction_id: int, 
    payment_data: InstallmentPaymentIn,
    caisse_ctrl: CaisseController = Depends(get_caisse_controller)
):
    """
    Ajoute un paiement échelonné (versement) à une transaction.
    """
    try:
        return caisse_ctrl.add_installment_payment(transaction_id, payment_data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur serveur add_payment TX {transaction_id}")
        raise HTTPException(status_code=500, detail="Erreur interne lors du paiement.")

@router.post("/{transaction_id}/settle", response_model=Any)
def settle_transaction(
    transaction_id: int,
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    """
    Solde entièrement une transaction (Obsolète, préférer /payment).
    """
    try:
        tx = caisse_ctrl.settle_transaction(transaction_id)
        return normalize_caisse_data(tx)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/{transaction_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        caisse_ctrl.cancel_transaction(transaction_id)
        return {"detail": "Annulé"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/{transaction_id}/invoice/download", tags=["Caisse"])
def download_invoice_pdf(
    transaction_id: int,
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        pdf_content_bytes = caisse_ctrl.generate_invoice_pdf(transaction_id)
        
        if not pdf_content_bytes:
             raise HTTPException(status_code=404, detail="Facture non trouvée ou vide")

        return Response(
            content=pdf_content_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=facture_{transaction_id}.pdf"
            }
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.exception(f"Erreur lors de la génération du PDF pour TX {transaction_id}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la génération du PDF")

# ==========================================
# 5. ROUTES DYNAMIQUES GÉNÉRIQUES (GET/PUT/DELETE {id})
# ==========================================

@router.get("/{transaction_id}", response_model=Any)
def get_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        tx = caisse_ctrl.get_transaction(transaction_id)
        return normalize_caisse_data(tx)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.put("/{transaction_id}", response_model=Any)
def update_transaction(
    transaction_id: int,
    data: dict = Body(...),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        tx = caisse_ctrl.update_transaction(transaction_id, data)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction non trouvée après mise à jour")
        return normalize_caisse_data(tx)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except IntegrityError as ie:
        try: caisse_ctrl.repo.session.rollback()
        except: pass
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try: caisse_ctrl.repo.session.rollback()
        except: pass
        logger.exception("SQLAlchemyError updating transaction: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour de la transaction")

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        caisse_ctrl.delete_transaction(transaction_id)
        return None
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))