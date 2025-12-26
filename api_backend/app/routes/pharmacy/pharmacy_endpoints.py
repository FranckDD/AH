from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

from .pharmacy_schemas import PharmacyCreate, PharmacyUpdate, PharmacyResponse
from app.database import SessionLocal
from repositories.pharmacy_repo import PharmacyRepository
from controller.pharmacy_controller import PharmacyController
from app.routes.auth.auth_endpoints import get_current_user,role_required
from .mapping import normalize_pharmacy_data

logger = logging.getLogger(__name__)
#router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])
router = APIRouter(
    prefix="/pharmacy",
    tags=["pharmacy"],
    dependencies=[Depends(role_required("secretaire"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_pharmacy_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PharmacyController:
    repo = PharmacyRepository(session=db)
    return PharmacyController(repo=repo, current_user=current_user)


@router.get("/", response_model=list[PharmacyResponse])
def list_products(
    term: str = Query(None),
    type_filter: str = Query(None),
    status_filter: str = Query(None),
    critical: bool = Query(False, description="Filtrer les produits critiques"),
    expiring: int = Query(None, description="Jours avant expiration"),
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        # Gestion des filtres combinés
        if critical and expiring:
            raise HTTPException(400, "Utilisez un seul filtre à la fois")
        
        if critical:
            products = ctrl.repo.get_critical_or_empty()
        elif expiring is not None:
            products = ctrl.repo.get_expiring_soon(days=expiring)
        else:
            products = ctrl.repo.search(
                term=term, 
                type_filter=type_filter, 
                status_filter=status_filter
            )
        
        return [normalize_pharmacy_data(p) for p in products]
    except Exception as e:
        logger.exception("Error listing pharmacy products")
        raise HTTPException(500, "Internal server error")

@router.get("/{medication_id}", response_model=PharmacyResponse)
def get_product(
    medication_id: int,
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        product = ctrl.repo.get_by_id(medication_id, include_relations=True)
        if not product:
            raise HTTPException(404, "Product not found")
        return normalize_pharmacy_data(product)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting product {medication_id}")
        raise HTTPException(500, "Internal server error")

@router.post("/", response_model=PharmacyResponse, status_code=201)
def create_product(
    data: PharmacyCreate,
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        product = ctrl.create_product(data.model_dump())
        return normalize_pharmacy_data(product)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except IntegrityError:
        raise HTTPException(400, "Database integrity error")
    except Exception as e:
        logger.exception("Error creating pharmacy product")
        raise HTTPException(500, "Internal server error")

@router.put("/{medication_id}", response_model=PharmacyResponse)
def update_product(
    medication_id: int,
    data: PharmacyUpdate,
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        product = ctrl.update_product(medication_id, data.model_dump(exclude_unset=True))
        return normalize_pharmacy_data(product)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except IntegrityError:
        raise HTTPException(400, "Database integrity error")
    except Exception as e:
        logger.exception(f"Error updating product {medication_id}")
        raise HTTPException(500, "Internal server error")

@router.delete("/{medication_id}", status_code=204)
def delete_product(
    medication_id: int,
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        ctrl.delete_product(medication_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.exception(f"Error deleting product {medication_id}")
        raise HTTPException(500, "Internal server error")

@router.post("/{medication_id}/renew", response_model=PharmacyResponse)
def renew_stock(
    medication_id: int,
    added_quantity: int = Query(..., gt=0, description="Quantité à ajouter"),
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        product = ctrl.renew_stock(medication_id, added_quantity)
        return normalize_pharmacy_data(product)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception(f"Error renewing stock for {medication_id}")
        raise HTTPException(500, "Internal server error")

@router.get("/alerts/critical", response_model=list[PharmacyResponse])
def list_critical_products(
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        products = ctrl.list_critical_or_empty()
        return [normalize_pharmacy_data(p) for p in products]
    except Exception as e:
        logger.exception("Error listing critical products")
        raise HTTPException(500, "Internal server error")

@router.get("/alerts/expiring", response_model=list[PharmacyResponse])
def list_expiring_products(
    days: int = Query(30, description="Jours avant expiration"),
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        products = ctrl.repo.get_expiring_soon(days)
        return [normalize_pharmacy_data(p) for p in products]
    except Exception as e:
        logger.exception("Error listing expiring products")
        raise HTTPException(500, "Internal server error")