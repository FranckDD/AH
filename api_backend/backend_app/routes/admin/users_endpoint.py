# api_backend/app/routes/users/users_endpoints.py
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

from api_backend.backend_app.database import SessionLocal
from controller.user_controller import UserController
from repositories.user_repo import UserRepository
from repositories.role_repo import RoleRepository
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from api_backend.backend_app.exceptions import translate_integrity_error
from .users_schemas import RoleOut, SpecialtyOut, UserCreate, UserUpdate, UserOut
from .mapping import normalize_user_data

logger = logging.getLogger(__name__)

# 🟢 MODIFICATION 1 : J'ai retiré le verrou global "dependencies=[...]"
# Maintenant, on peut entrer dans ce fichier simplement en étant connecté.
router = APIRouter(prefix="/users", tags=["Users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_controller(
    current_user=Depends(get_current_user), # Vérifie l'authenticité du Token
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


# =========================================================================
#  ZONE LECTURE (GET) - Accessible à tout utilisateur connecté
# =========================================================================

@router.get("/roles", response_model=List[RoleOut])
def list_roles(controller: UserController = Depends(get_user_controller)):
    try:
        return controller.get_all_roles()
    except SQLAlchemyError:
        logger.exception("Erreur DB list_roles")
        raise HTTPException(status_code=500, detail="Erreur serveur lecture rôles")

@router.get("/specialties", response_model=List[SpecialtyOut])
def list_specialties(controller: UserController = Depends(get_user_controller)):
    try:
        return controller.get_all_specialties()
    except SQLAlchemyError:
        logger.exception("Erreur DB list_specialties")
        raise HTTPException(status_code=500, detail="Erreur serveur lecture spécialités")


@router.get("/", response_model=List[UserOut], dependencies=[Depends(role_required("admin", "manager"))])
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    user_ctrl: UserController = Depends(get_user_controller),
):
    """Liste tous les utilisateurs ou recherche par terme."""
    if search:
        raws = user_ctrl.search_users(search)
        results = [_safe_validate_user(u) for u in raws]
    else:
        raws = user_ctrl.list_users(page=page, per_page=per_page) 
        results = [_safe_validate_user(u) for u in raws]
    return results


@router.get("/search", response_model=List[UserOut], dependencies=[Depends(role_required("admin", "manager"))])
def search_users(q: str = Query(..., min_length=1), user_ctrl: UserController = Depends(get_user_controller)):
    results = user_ctrl.search_users(q)
    return [_safe_validate_user(u) for u in results]


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(role_required("admin", "manager"))])
def get_user(user_id: int, user_ctrl: UserController = Depends(get_user_controller)):
    try:
        u = user_ctrl.get_user_by_id(user_id)
        return _safe_validate_user(u)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


# =========================================================================
#  ZONE ÉCRITURE (POST, PUT, DELETE) - Restreinte Admin / Manager
# =========================================================================

# 🟢 MODIFICATION 2 : On applique la sécurité stricte ici
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required("admin", "manager"))])
def create_user(data: UserCreate, user_ctrl: UserController = Depends(get_user_controller)):
    try:
        payload = data.model_dump()
        user = user_ctrl.create_user(payload)
        return _safe_validate_user(user)
    except IntegrityError as ie:
        try:
            user_ctrl.user_repo.session.rollback()
        except: pass
        raise translate_integrity_error(ie)
    except SQLAlchemyError as se:
        try:
            user_ctrl.user_repo.session.rollback()
        except: pass
        logger.exception("SQLAlchemyError creating user: %s", se)
        raise HTTPException(status_code=500, detail="Erreur serveur création")
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))


@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(role_required("admin", "manager"))])
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
        except: pass
        raise translate_integrity_error(ie)
    except SQLAlchemyError as se:
        try:
            user_ctrl.user_repo.session.rollback()
        except: pass
        logger.exception("SQLAlchemyError updating user: %s", se)
        raise HTTPException(status_code=500, detail="Erreur serveur maj")
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(role_required("admin", "manager"))])
def delete_user(user_id: int, user_ctrl: UserController = Depends(get_user_controller)):
    try:
        ok = user_ctrl.delete_user(user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        return None
    except SQLAlchemyError as se:
        try:
            user_ctrl.user_repo.session.rollback()
        except: pass
        logger.exception("SQLAlchemyError deleting user: %s", se)
        raise HTTPException(status_code=500, detail="Erreur serveur suppression")