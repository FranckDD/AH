from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .pharmacy_schemas import PharmacyCreate, PharmacyUpdate, PharmacyResponse
from ...database import SessionLocal
from repositories.pharmacy_repo import PharmacyRepository
from repositories.audit_repo import AuditRepository
from controller.pharmacy_controller import PharmacyController
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user,role_required
from .mapping import normalize_pharmacy_data
from .pharmacy_schemas import PharmacyCreate, PharmacyUpdate, PharmacyResponse, CriticalStockCount # <--- Importer CriticalStockCount
from .pharmacy_schemas import  ExpiringProductCount, TotalStockValue,StockDashboardStats,CategoryCount # Importer les nouveaux schémas

logger = logging.getLogger(__name__)
#router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])
router = APIRouter(
    prefix="/pharmacy",
    tags=["pharmacy"],
    dependencies=[Depends(role_required("secretaire","admin","manager"))]
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
    
    # Création des Repositories nécessaires
    repo = PharmacyRepository(session=db)
    audit_repo = AuditRepository(db) 
    
    return PharmacyController(
        repo=repo, 
        current_user=current_user,
        audit_repo=audit_repo 
    )


@router.get("/", response_model=dict)
def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    term: Optional[str] = Query(None),
    type_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    critical: bool = Query(False),
    expiring: Optional[int] = Query(None),
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        # --- Cas 1: Critical (Critique) ---
        if critical:
            result = ctrl.repo.get_critical_or_empty()
            products = result if isinstance(result, list) else result["data"]
            total = len(products)
            
            # 🟢 NOUVEAU: Calcul de la valeur filtrée pour le stock critique
            # Si 'products' contient les entités avec price et quantity, on calcule la somme
            filtered_value = sum(p.quantity * p.price for p in products)
            
            return {
                "data": [normalize_pharmacy_data(p) for p in products],
                "total": total,
                "filtered_value": float(filtered_value), # 👈 Ajout
                "page": 1,
                "per_page": total,
                "total_pages": 1
            }
            
        # --- Cas 2: Expiring (Périmés) ---
        elif expiring is not None:
            result = ctrl.repo.get_expiring_soon(days=expiring)
            products = result if isinstance(result, list) else result["data"]
            total = len(products)
            
            # 🟢 NOUVEAU: Calcul de la valeur filtrée pour le stock périmé
            filtered_value = sum(p.quantity * p.price for p in products)
            
            return {
                "data": [normalize_pharmacy_data(p) for p in products],
                "total": total,
                "filtered_value": float(filtered_value), # 👈 Ajout
                "page": 1,
                "per_page": total,
                "total_pages": 1
            }
            
        # --- Cas 3: Search normal (avec filtres de type/statut/terme) ---
        else:
            # Assurez-vous que cette méthode de repo renvoie la clé "filtered_value"
            result = ctrl.repo.search(
                term=term,
                type_filter=type_filter,
                status_filter=status_filter,
                page=page,
                per_page=per_page
            )
            return {
                "data": [normalize_pharmacy_data(p) for p in result["data"]],
                "total": result["total"],
                "filtered_value": result.get("filtered_value", 0.0), # 👈 Ajout/Récupération
                "page": result["page"],
                "per_page": result["per_page"],
                "total_pages": result["total_pages"]
            }
            
    except Exception as e:
        logger.exception("Error listing pharmacy products")
        raise HTTPException(500, "Internal server error")

@router.get("/{medication_id}", response_model=PharmacyResponse)
def get_product(
    medication_id: int,
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    try:
        # SUPPRIME include_relations=True → il n'existe pas !
        product = ctrl.repo.get_by_id(medication_id)
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
    
@router.get(
    "/kpi/critical_stock_count",
    response_model=CriticalStockCount,
    status_code=status.HTTP_200_OK,
    summary="Récupère le nombre total de produits en stock critique ou épuisé (KPI Dashboard)"
)
def get_kpi_critical_stock_count(
    ctrl: PharmacyController = Depends(get_pharmacy_controller)
):
    """
    Retourne le nombre d'articles en alerte de stock (critique ou épuisé).
    """
    try:
        count = ctrl.get_critical_stock_count_kpi()
        return {"stock_alerts_count": count}
    except Exception as e:
        logger.exception("Error fetching critical stock KPI")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du KPI: {str(e)}"
        )  

@router.get(
    "/kpi/expiring_product_count",
    response_model=ExpiringProductCount, 
    status_code=status.HTTP_200_OK,
    summary="Récupère le nombre total de produits expirant dans les 30 prochains jours (KPI Dashboard)"
)
def get_kpi_expiring_product_count(
    days: int = Query(30, gt=0, description="Jours dans le futur à considérer pour l'expiration"),
    ctrl: PharmacyController = Depends(get_pharmacy_controller) 
):
    """
    Retourne le nombre d'articles expirant bientôt.
    """
    try:
        count = ctrl.get_expiring_product_count_kpi(days=days)
        return {"expiring_alerts_count": count}
    except Exception as e:
        logger.exception("Erreur lors de la récupération du KPI de produits expirant")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du KPI: {str(e)}"
        )


# NOUVEL ENDPOINT KPI 3 : Valeur Monétaire Totale du Stock
@router.get(
    "/kpi/total_stock_value",
    response_model=TotalStockValue, 
    status_code=status.HTTP_200_OK,
    summary="Récupère la valeur monétaire totale du stock disponible (KPI Dashboard)"
)
def get_kpi_total_stock_value(
    ctrl: PharmacyController = Depends(get_pharmacy_controller) 
):
    """
    Retourne la valeur monétaire totale du stock (somme de quantity * price).
    """
    try:
        value = ctrl.get_total_stock_value_kpi()
        return {"total_stock_value": value}
    except Exception as e:
        logger.exception("Erreur lors de la récupération du KPI de valeur de stock")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du KPI: {str(e)}"
        )      
    
## 🎯 Nouveaux Endpoints KPI pour Catégories

@router.get(
    "/kpi/pharmaceutique_count",
    response_model=CategoryCount, 
    status_code=status.HTTP_200_OK,
    summary="Récupère le nombre total de produits 'pharmaceutique' (KPI Dashboard)"
)
def get_kpi_pharmaceutique_count(
    ctrl: PharmacyController = Depends(get_pharmacy_controller) 
):
    """
    Retourne le nombre d'articles de type 'pharmaceutique'.
    """
    try:
        # Appelle la méthode dans le Controller qui utilise la catégorie 'pharmaceutique'
        count = ctrl.get_pharma_count_kpi()
        return {"category_count": count}
    except Exception as e:
        logger.exception("Erreur lors de la récupération du KPI 'pharmaceutique'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du KPI: {str(e)}"
        )

@router.get(
    "/kpi/naturel_count",
    response_model=CategoryCount, 
    status_code=status.HTTP_200_OK,
    summary="Récupère le nombre total de produits 'Naturel' (KPI Dashboard)"
)
def get_kpi_naturel_count(
    ctrl: PharmacyController = Depends(get_pharmacy_controller) 
):
    """
    Retourne le nombre d'articles de type 'Naturel'.
    """
    try:
        # Appelle la méthode dans le Controller qui utilise la catégorie 'Naturel'
        count = ctrl.get_natural_count_kpi()
        return {"category_count": count}
    except Exception as e:
        logger.exception("Erreur lors de la récupération du KPI 'Naturel'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du KPI: {str(e)}"
        )

## 📊 Nouvel Endpoint KPI Global Dashboard

@router.get(
    "/kpi/dashboard_stats",
    response_model=StockDashboardStats, # Assurez-vous que ce schéma Pydantic existe
    status_code=status.HTTP_200_OK,
    summary="Récupère toutes les statistiques du tableau de bord en un seul appel"
)
def get_dashboard_stats(
    ctrl: PharmacyController = Depends(get_pharmacy_controller) 
):
    """
    Retourne l'ensemble des indicateurs du tableau de bord (Valeur totale, alertes, comptes par catégorie).
    """
    try:
        # Appelle la méthode agrégée du Controller
        stats = ctrl.get_stock_dashboard_stats()
        return stats
    except Exception as e:
        logger.exception("Erreur lors de la récupération des statistiques du tableau de bord")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}"
        )    
    