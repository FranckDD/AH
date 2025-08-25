# api_backend/app/routes/users/users_endpoints.py
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

from app.database import SessionLocal
from controller.user_controller import UserController
from repositories.user_repo import UserRepository
from repositories.role_repo import RoleRepository
from app.routes.auth.auth_endpoints import get_current_user, role_required
from app.exceptions import translate_integrity_error

from .users_schemas import UserCreate, UserUpdate, UserOut
from .mapping import normalize_user_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(role_required("admin"))])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserController:
    user_repo = UserRepository(session=db)
    role_repo = RoleRepository(session=db)
    return UserController(user_repo=user_repo, role_repo=role_repo)


def _safe_validate_user(raw: Any) -> UserOut:
    data = normalize_user_data(raw)
    try:
        return UserOut.model_validate(data)
    except Exception as e:
        logger.exception("Error validating user response data: %s", e)
        raise HTTPException(status_code=500, detail="Erreur interne : données utilisateur invalides")


@router.get("/", response_model=List[UserOut])
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    user_ctrl: UserController = Depends(get_user_controller),
):
    raws = user_ctrl.list_users()
    start = (page - 1) * per_page
    end = start + per_page
    page_items = raws[start:end]
    return [_safe_validate_user(u) for u in page_items]


@router.get("/search", response_model=List[UserOut])
def search_users(q: str = Query(..., min_length=1), user_ctrl: UserController = Depends(get_user_controller)):
    results = user_ctrl.search_users(q)
    return [_safe_validate_user(u) for u in results]


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, user_ctrl: UserController = Depends(get_user_controller)):
    try:
        u = user_ctrl.get_user_by_id(user_id)
        return _safe_validate_user(u)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, user_ctrl: UserController = Depends(get_user_controller)):
    try:
        payload = data.model_dump()
        user = user_ctrl.create_user(payload)
        return _safe_validate_user(user)
    except IntegrityError as ie:
        try:
            user_ctrl.user_repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as se:
        try:
            user_ctrl.user_repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError creating user: %s", se)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création de l'utilisateur")
    except RuntimeError as re:
        # Controller raises RuntimeError on repo-level failure
        raise HTTPException(status_code=500, detail=str(re))


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, user_ctrl: UserController = Depends(get_user_controller)):
    try:
        payload = data.model_dump(exclude_unset=True)
        updated = user_ctrl.update_user(user_id, payload)
        return _safe_validate_user(updated)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except IntegrityError as ie:
        try:
            user_ctrl.user_repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as se:
        try:
            user_ctrl.user_repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError updating user: %s", se)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour de l'utilisateur")
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, user_ctrl: UserController = Depends(get_user_controller)):
    try:
        ok = user_ctrl.delete_user(user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        return None
    except SQLAlchemyError as se:
        try:
            user_ctrl.user_repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError deleting user: %s", se)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la suppression de l'utilisateur")
