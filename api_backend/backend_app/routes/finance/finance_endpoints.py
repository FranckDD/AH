from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import role_required
from repositories.finance_ledger_repo import FinanceLedgerRepository

router = APIRouter(prefix="/finance", tags=["Finance"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_ledger_repo(db: Session = Depends(get_db)) -> FinanceLedgerRepository:
    return FinanceLedgerRepository(db)


@router.get(
    "/mouvements",
    response_model=Any,
    dependencies=[Depends(role_required("admin", "secretaire", "manager"))],
)
def list_mouvements(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sens: Optional[str] = Query(None, pattern="^(INCOME|EXPENSE)$"),
    status: Optional[str] = Query(None),
    repo: FinanceLedgerRepository = Depends(get_ledger_repo),
):
    """Journal financier unifie : recettes et depenses en un seul flux,
    trie et pagine en base."""
    return repo.list_mouvements(
        page=page, per_page=per_page, date_from=date_from, date_to=date_to,
        category=category, search=search, sens=sens, status=status,
    )


@router.get(
    "/totaux",
    response_model=Any,
    dependencies=[Depends(role_required("admin", "secretaire", "manager"))],
)
def get_totaux(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sens: Optional[str] = Query(None, pattern="^(INCOME|EXPENSE)$"),
    status: Optional[str] = Query(None),
    repo: FinanceLedgerRepository = Depends(get_ledger_repo),
):
    """Totaux recettes/depenses filtres exactement comme /finance/mouvements -
    ce que le module Finance affiche dans ses cartes KPI reflete toujours les
    memes filtres que la liste juste en dessous."""
    return repo.get_totals(
        date_from=date_from, date_to=date_to, category=category,
        search=search, sens=sens, status=status,
    )


@router.get(
    "/categories",
    response_model=Any,
    dependencies=[Depends(role_required("admin", "secretaire", "manager"))],
)
def list_categories(repo: FinanceLedgerRepository = Depends(get_ledger_repo)):
    """Categories reellement presentes dans le journal financier."""
    return repo.list_categories()
