# api_backend/backend_app/routes/labo/lab_catalogue_endpoints.py
"""Catalogue du laboratoire : lecture (labo, admin, promoteur) et ecriture (admin ou cheffe du laboratoire).

Le prix n'est jamais ecrit ici (route existante PUT /labo/exams/{id}, admin).
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.lab_catalogue_controller import CatalogueError, LabCatalogueController
from repositories.lab_catalogue_repo import LabCatalogueRepository
from utils.lab_catalogue_access import can_edit_lab_catalogue

from ...database import SessionLocal
from .lab_catalogue_schemas import (
    ExamCatalogueCreate,
    ExamCataloguePut,
    IdsIn,
    ParameterCreate,
    ParameterPut,
    PositionIn,
    RangeCreate,
    RangePut,
)

router = APIRouter(prefix="/labo/catalogue", tags=["labo-catalogue"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_catalogue_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> LabCatalogueController:
    return LabCatalogueController(LabCatalogueRepository(db), current_user)


def require_catalogue_editor(current_user: Any = Depends(get_current_user)):
    if not can_edit_lab_catalogue(current_user):
        raise HTTPException(status_code=403, detail="Acces refuse : edition du catalogue reservee a l'administrateur et a la cheffe du laboratoire.")
    return current_user


def _run(fn, *args):
    try:
        return fn(*args)
    except CatalogueError as e:
        raise HTTPException(status_code=e.status, detail=e.detail())


# ------------------------------------------------------------------ lecture
@router.get("/exams", response_model=List[Dict[str, Any]],
            dependencies=[Depends(role_required("laborantin", "admin", "promoteur"))])
def list_catalogue(include_inactive: bool = Query(False), ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    """Examens (ordre sort_order puis nom) avec parametres et plages ; actifs seulement par defaut."""
    return ctrl.list_exams(include_inactive)


# ------------------------------------------------------------------ examens
@router.post("/exams", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_catalogue_editor)])
def create_exam(payload: ExamCatalogueCreate, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    return _run(ctrl.create_exam, payload.model_dump())


@router.put("/exams/order", dependencies=[Depends(require_catalogue_editor)])
def order_exams(payload: IdsIn, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    """Ordre complet des examens listes (les autres suivent) : sort_order = 1..n."""
    return _run(ctrl.order_exams, payload.ids)


@router.put("/exams/{examen_id}", dependencies=[Depends(require_catalogue_editor)])
def update_exam(examen_id: int, payload: ExamCataloguePut, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    return _run(ctrl.update_exam, examen_id, payload.model_dump(exclude_unset=True))


@router.put("/exams/{examen_id}/order", dependencies=[Depends(require_catalogue_editor)])
def move_exam(examen_id: int, payload: PositionIn, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    """Deplace l'examen a la position donnee (1 = premier) ; les autres sont renumerotes."""
    return _run(ctrl.move_exam, examen_id, payload.position)


@router.put("/exams/{examen_id}/parameters/order", dependencies=[Depends(require_catalogue_editor)])
def order_parameters(examen_id: int, payload: IdsIn, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    """Ordre complet des parametres de l'examen (exactement tous, une fois chacun)."""
    return _run(ctrl.order_parameters, examen_id, payload.ids)


@router.delete("/exams/{examen_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_catalogue_editor)])
def delete_exam(examen_id: int, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    _run(ctrl.delete_exam, examen_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------- parametres
@router.post("/parameters", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_catalogue_editor)])
def create_parameter(payload: ParameterCreate, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    return _run(ctrl.create_parameter, payload.model_dump())


@router.put("/parameters/{param_id}", dependencies=[Depends(require_catalogue_editor)])
def update_parameter(param_id: int, payload: ParameterPut, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    return _run(ctrl.update_parameter, param_id, payload.model_dump(exclude_unset=True))


@router.put("/parameters/{param_id}/order", dependencies=[Depends(require_catalogue_editor)])
def move_parameter(param_id: int, payload: PositionIn, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    return _run(ctrl.move_parameter, param_id, payload.position)


@router.delete("/parameters/{param_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_catalogue_editor)])
def delete_parameter(param_id: int, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    _run(ctrl.delete_parameter, param_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------- plages
@router.post("/ranges", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_catalogue_editor)])
def create_range(payload: RangeCreate, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    return _run(ctrl.create_range, payload.model_dump())


@router.put("/ranges/{range_id}", dependencies=[Depends(require_catalogue_editor)])
def update_range(range_id: int, payload: RangePut, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    return _run(ctrl.update_range, range_id, payload.model_dump())


@router.delete("/ranges/{range_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_catalogue_editor)])
def delete_range(range_id: int, ctrl: LabCatalogueController = Depends(get_catalogue_controller)):
    _run(ctrl.delete_range, range_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
