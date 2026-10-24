# api_backend/backend_app/routes/cash_closure/cash_closure_endpoints.py
"""Routeurs /cash-closure (cloture de caisse) et /payment-modes.

Garde de role PAR ROUTE. Comptage a l'aveugle : GET /status ne contient aucun total ; la
periode ouverte n'a pas d'id ; les montants ne sont lisibles qu'une fois la cloture validee.
Aucune route PUT/PATCH/DELETE sur une cloture (immuable) ; un mode de paiement n'est jamais
supprime. Les chemins fixes (/status, /start, /catchup, /corrections) sont declares AVANT
/{closure_id}.
Erreurs du controleur : CashClosureNotFoundError -> 404, CashClosureConflictError -> 409,
PermissionError -> 403, ValueError -> 422. Montants renvoyes en chaines (jamais de float).
"""
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.cash_closure_controller import (
    CashClosureConflictError, CashClosureController, CashClosureNotFoundError,
    get_cash_closure_controller,
)

from .cash_closure_schemas import (
    CloseBody, CorrectionCreate, DecideBody, ModeUpdate, StartBody,
)

router = APIRouter(prefix="/cash-closure", tags=["Cloture de caisse"])
modes_router = APIRouter(prefix="/payment-modes", tags=["Cloture de caisse"])

# ---- matrice des roles (codes role_required) ----
READERS = ("secretaire", "promoteur", "admin")      # statut, lecture, rattrapage, modes (lecture)
CLOSERS = ("secretaire",)                            # cloture manuelle
ADMINS = ("admin",)                                  # depart, ecriture des modes
CORRECTION_REQUESTERS = ("secretaire",)
CORRECTION_DECIDERS = ("promoteur", "admin")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_clock():
    """Horloge du controleur : None = horloge reelle. Surchargee par les tests."""
    return None


def get_ctrl(current_user: Any = Depends(get_current_user),
             db: Session = Depends(get_db), clock=Depends(get_clock)) -> CashClosureController:
    # fabrique de la tache 4 : depots d'audit ET de notifications reellement injectes
    return get_cash_closure_controller(db, current_user, clock=clock)


# identifiants int4 : hors bornes -> 422 (et non 500 sur depassement)
PathId = Annotated[int, Path(ge=1, le=2**31 - 1)]


@contextmanager
def _errors():
    try:
        yield
    except CashClosureNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CashClosureConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


def _out(v):
    """Decimal -> chaine, recursivement (FastAPI convertirait en float)."""
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, dict):
        return {k: _out(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_out(x) for x in v]
    return v


# ---------------- chemins fixes (avant /{closure_id}) ----------------
@router.get("/status", dependencies=[Depends(role_required(*READERS))])
def get_status(ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.status())


@router.post("/start", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required(*ADMINS))])
def set_start(payload: StartBody, ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.set_start(payload.opening_cash))


@router.post("/catchup", dependencies=[Depends(role_required(*READERS))])
def catchup(ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.catch_up())


@router.get("/corrections", dependencies=[Depends(role_required(*CORRECTION_DECIDERS))])
def list_corrections(status_filter: Optional[str] = Query(None, alias="status"),
                     ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.list_corrections({"status": status_filter}))


@router.post("/corrections/{correction_id}/decide",
             dependencies=[Depends(role_required(*CORRECTION_DECIDERS))])
def decide_correction(correction_id: PathId, payload: DecideBody,
                      ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.decide_correction(correction_id, payload.approve))


# ---------------- clotures ----------------
@router.get("", dependencies=[Depends(role_required(*READERS))])
def list_closures(date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None),
                  kind: Optional[str] = Query(None), limit: int = Query(50), offset: int = Query(0),
                  ctrl: CashClosureController = Depends(get_ctrl)):
    # seules des clotures validees existent en base : la periode ouverte n'y figure jamais
    with _errors():
        return _out(ctrl.list({"date_from": date_from, "date_to": date_to, "kind": kind,
                               "limit": limit, "offset": offset}))


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required(*CLOSERS))])
def submit_closure(payload: CloseBody, ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.submit([c.model_dump() for c in payload.counts],
                                last_closed_at=payload.last_closed_at))


@router.get("/{closure_id}", dependencies=[Depends(role_required(*READERS))])
def get_closure(closure_id: PathId, ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.get(closure_id))


@router.post("/{closure_id}/corrections", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required(*CORRECTION_REQUESTERS))])
def request_correction(closure_id: PathId, payload: CorrectionCreate,
                       ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.request_correction(closure_id, payload.model_dump()))


# ---------------- modes de paiement ----------------
@modes_router.get("", dependencies=[Depends(role_required(*READERS))])
def list_modes(ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.list_modes())


# Pas de creation de mode : la liste officielle est fixe (renommer, activer/desactiver, ordonner).
@modes_router.put("/{code}", dependencies=[Depends(role_required(*ADMINS))])
def update_mode(code: str, payload: ModeUpdate, ctrl: CashClosureController = Depends(get_ctrl)):
    with _errors():
        return _out(ctrl.update_mode(code, payload.model_dump(exclude_unset=True)))
