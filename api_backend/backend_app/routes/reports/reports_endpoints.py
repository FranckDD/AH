# api_backend/backend_app/routes/reports/reports_endpoints.py
"""Routeur /reports : Rapports et controle quotidien (lecture promoteur/admin).

Garde de role PAR ROUTE : lecture READERS (promoteur, admin), reglages SETTINGS_WRITERS
(admin seul). Tout autre role : 403 ; non authentifie : 401.
Erreurs du controleur : PermissionError -> 403, ValueError -> 422 (message francais),
toute autre erreur -> 500 avec un message generique (jamais la trace).
Uniquement des chemins fixes : aucun chemin parametre ne doit venir les masquer.
Le controle du soir (run_daily_control, catch_up) n'est PAS expose en HTTP.
"""
import logging
from contextlib import contextmanager
from datetime import date
from typing import Any, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ...database import SessionLocal
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from api_backend.backend_app.utils.reports_pdf import MAX_ROWS, render_reports_pdf
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.reports_controller import ReportsController, get_reports_controller
from utils.report_rules import parse_period

from .reports_schemas import SettingsBody

log = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Rapports"])

READERS = ("promoteur", "admin")
SETTINGS_WRITERS = ("admin",)
GENERIC_ERROR = "Erreur interne lors du calcul du rapport."


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_controller(current_user: Any = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> ReportsController:
    return get_reports_controller(db, current_user)


@contextmanager
def _errors():
    try:
        yield
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        log.exception("Erreur inattendue dans /reports")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR)


def _period(ctrl: ReportsController, date_from: Optional[date],
            date_to: Optional[date]) -> Tuple[date, date]:
    # meme horloge que le controleur (get_control separe aujourd'hui des jours passes avec
    # ctrl.today()) : la periode est fixee ICI une fois et transmise telle quelle
    return parse_period(date_from, date_to, ctrl.today())


@router.get("/overview", dependencies=[Depends(role_required(*READERS))])
def overview(date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None),
             ctrl: ReportsController = Depends(get_controller)):
    with _errors():
        d0, d1 = _period(ctrl, date_from, date_to)
        return {"period": {"from": d0.isoformat(), "to": d1.isoformat()},
                "money": ctrl.money(d0, d1),
                "products": ctrl.products(d0, d1),
                "production": ctrl.production(d0, d1),
                "growth": ctrl.growth(d0, d1),
                "control": ctrl.get_control(d0, d1)}


@router.get("/daily-control", dependencies=[Depends(role_required(*READERS))])
def daily_control(date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None),
                  ctrl: ReportsController = Depends(get_controller)):
    with _errors():
        d0, d1 = _period(ctrl, date_from, date_to)
        return ctrl.get_control(d0, d1)


@router.get("/products-sold", dependencies=[Depends(role_required(*READERS))])
def products_sold(date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None),
                  q: Optional[str] = Query(None, max_length=100),
                  item_type: str = Query("Medicament", max_length=40),
                  category: Optional[str] = Query(None, max_length=100),
                  sort: str = Query("amount_desc", max_length=40),
                  limit: int = Query(50, ge=1, le=200),
                  offset: int = Query(0, ge=0, le=2**31 - 1),
                  ctrl: ReportsController = Depends(get_controller)):
    with _errors():
        d0, d1 = _period(ctrl, date_from, date_to)
        return ctrl.sold_by_product(d0, d1, q=q, item_type=item_type, category=category,
                                    sort=sort, limit=limit, offset=offset)


@router.get("/export.pdf", dependencies=[Depends(role_required(*READERS))])
def export_pdf(date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None),
               ctrl: ReportsController = Depends(get_controller), db: Session = Depends(get_db)):
    """PDF francais de la page Rapports (chiffres seulement, pas de courbes). Tableau des
    produits : Medicament, montant decroissant, au plus MAX_ROWS lignes (pages de 200)."""
    with _errors():
        d0, d1 = _period(ctrl, date_from, date_to)
        items, total, basis = [], 0, None
        while len(items) < MAX_ROWS:
            page = ctrl.sold_by_product(d0, d1, item_type="Medicament", sort="amount_desc",
                                        limit=min(200, MAX_ROWS - len(items)), offset=len(items))
            items += page["items"]
            total, basis = page["total"], page["amount_basis"]
            if not page["items"] or len(items) >= total:
                break
        data = {"period": {"from": d0.isoformat(), "to": d1.isoformat()},
                "money": ctrl.money(d0, d1), "products": ctrl.products(d0, d1),
                "production": ctrl.production(d0, d1), "growth": ctrl.growth(d0, d1),
                "control": ctrl.get_control(d0, d1),
                "sold": {"items": items, "total": total, "amount_basis": basis}}
        header = get_pdf_header_context(ConfigController(repo=ConfigRepository(db)))
        pdf = render_reports_pdf(header, data)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="rapports_{d0.isoformat()}_{d1.isoformat()}.pdf"'})


@router.get("/settings", dependencies=[Depends(role_required(*READERS))])
def get_settings(ctrl: ReportsController = Depends(get_controller)):
    with _errors():
        return ctrl.get_settings()


@router.put("/settings", dependencies=[Depends(role_required(*SETTINGS_WRITERS))])
def set_settings(payload: SettingsBody, ctrl: ReportsController = Depends(get_controller)):
    with _errors():
        return ctrl.set_settings(payload.cancelled_sales_threshold, payload.adjustment_pending_days)
