import datetime
import logging
from ...security.role_map import normalize_role_name, normalize_roles_list
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from jose import ExpiredSignatureError, jwt as jose_jwt ,JWTError
from ...database import SessionLocal
from ...config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from ...rate_limit import limiter
from ...exceptions import translate_integrity_error
from controller.auth_controller import AuthController
from controller.user_controller import UserController
from repositories.user_repo import UserRepository
from repositories.role_repo import RoleRepository
from .schemas import Token
from .schemas import UserPasswordUpdate
from .schemas import SelfProfileUpdate
from typing import Any
import uuid

logger = logging.getLogger(__name__)

JWT_ISSUER = "ah2-api"
JWT_AUDIENCE = "ah2-web"

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/auth/login", response_model=Token, tags=["Authentication"])
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    auth_ctrl = AuthController(db_session=db)
    user = auth_ctrl.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")

    # s'assurer que la relation application_role est chargée (sécurité)
    try:
        if user.application_role is None:
            db.refresh(user, ['application_role'])
    except Exception:
        pass

    # récupérer le/les rôles canoniques (si présents)
    role_list = []
    app_role = getattr(user, "application_role", None)
    if app_role:
        role_name_db = getattr(app_role, "role_name", None)
        if role_name_db:
            canon = normalize_role_name(str(role_name_db))
            if canon:
                role_list = [canon]

    # construire le token (sub + roles + exp + hygiene JWT : ver/jti/iss/aud/iat)
    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.user_id),
        "roles": role_list,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "ver": getattr(user, "token_version", 0) or 0,
        "jti": uuid.uuid4().hex,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }

    token = jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM, headers={"kid": "ah2-hs256-1"})  # pyright: ignore[reportArgumentType]
    return {"access_token": token, "token_type": "bearer"}


# Exemple de dependency pour obtenir l'utilisateur courant

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Any:
    """
    Décode et vérifie le JWT, retourne l'objet utilisateur.
    Lève HTTPException(401) si le token est invalide/expiré ou si l'utilisateur n'existe pas.
    """

    # --- Guard checks pour satisfaire Pylance / sécurité ---
    if not isinstance(JWT_SECRET, str) or JWT_SECRET == "":
        raise RuntimeError("JWT_SECRET must be set and be a string.")
    if not isinstance(JWT_ALGORITHM, str) or JWT_ALGORITHM == "":
        raise RuntimeError("JWT_ALGORITHM must be set and be a string.")

    # --- Décodage unique du token ---
    try:
        payload = jose_jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER, audience=JWT_AUDIENCE,
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expiré")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré")

    # --- Récupération et validation de la claim 'sub' ---
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    if not isinstance(sub, str):
        try:
            sub = str(sub)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    try:
        user_id_int = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    # --- Récupérer l'utilisateur depuis le repository ---
    auth_ctrl = AuthController(db_session=db)
    user = auth_ctrl.user_repo.get_user_by_id(user_id_int)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur non trouvé")

    # --- Révocation : le token doit correspondre à la version courante ---
    token_ver = payload.get("ver")
    if token_ver != (getattr(user, "token_version", 0) or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalidée, veuillez vous reconnecter")

    # Charger explicitement la relation application_role si besoin (sécurise l'accès aux attributs)
    try:
        if user.application_role is None:
            db.refresh(user, ['application_role'])
    except Exception:
        # Ne pas échouer la requête juste pour un refresh ; on continuera avec ce qu'on a.
        pass

    # --- GESTION DES RÔLES (CORRIGÉE) ---
    
    canonical_roles: list[str] = []
    
    # 1. Priorité absolue : Le rôle défini en Base de Données
    app_role = getattr(user, "application_role", None)
    
    if app_role:
        # On récupère soit le code, soit le nom (ex: "Psychologist")
        raw_role_name = getattr(app_role, "role_code", None) or getattr(app_role, "role_name", None)
        
        if raw_role_name:
            raw_role_str = str(raw_role_name)
            
            # A. On tente de normaliser via ta fonction utilitaire
            canon = normalize_role_name(raw_role_str)
            
            if canon:
                canonical_roles = [canon]
            else:
                # 🟢 B. FALLBACK (CORRECTION CRITIQUE)
                # Si normalize_role_name renvoie None (car "Psychologist" n'est pas dans la liste),
                # on utilise le rôle brut en minuscule pour ne pas bloquer l'utilisateur.
                canonical_roles = [raw_role_str.strip().lower()]

    # 2. Fallback secondaire : Les rôles stockés dans le Token (si la DB a échoué)
    if not canonical_roles:
        roles_from_token = payload.get("roles")
        if isinstance(roles_from_token, list):
             # On nettoie aussi les rôles du token
             canonical_roles = [str(r).strip().lower() for r in roles_from_token if r]
        elif isinstance(roles_from_token, str):
             canonical_roles = [roles_from_token.strip().lower()]

    # 3. Assignation finale
    # On s'assure que user.roles existe pour la suite (role_required)
    user.roles = canonical_roles or []

    # Debug (Décommente si tu as encore des soucis pour voir ce qui sort)
    # print(f"DEBUG AUTH: User={user.username}, Roles={user.roles}")

    return user

@router.get("/auth/me", tags=["Authentication"])
def get_me(current_user=Depends(get_current_user)):
    """
    Retourne les infos du user courant basé sur le JWT.
    """
    return {
        "id": current_user.user_id,
        "username": getattr(current_user, "username", None),
        "full_name": getattr(current_user, "full_name", None),
        "email": getattr(current_user, "email", None),
        "contact": getattr(current_user, "contact", None),
        "application_role": {
            "id": getattr(current_user.application_role, "id", None),
            "role_name": getattr(current_user.application_role, "role_name", None),
        }
    }



def role_required(*allowed_roles: str):
    """
    Factory: Depends(role_required("admin", "secretaire"))
    allowed_roles peut être un alias (fr/en) ou un canonical (ex: "admin", "medecin").
    """
    # normaliser la liste autorisée en codes canoniques (lowercase)
    allowed_canon = set()
    for r in allowed_roles:
        if not r:
            continue
        c = normalize_role_name(r)
        if c:
            allowed_canon.add(c)

    def wrapper(user = Depends(get_current_user)):
        user_roles = set([r.strip().lower() for r in getattr(user, "roles", []) if r])
        if not (user_roles & allowed_canon):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : rôle utilisateur insuffisant"
            )
        return user
    return wrapper

@router.post("/auth/logout", status_code=status.HTTP_200_OK, tags=["Authentication"])
def logout(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Révoque tous les tokens actuellement émis pour l'utilisateur courant."""
    current_user.token_version = (getattr(current_user, "token_version", 0) or 0) + 1
    db.add(current_user)
    db.commit()
    return {"message": "Déconnexion effectuée"}

@router.put("/auth/password", status_code=status.HTTP_200_OK)
def update_password(
    password_data: UserPasswordUpdate, # Validation Pydantic
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user) # On a besoin de l'utilisateur connecté
):
    """Permet à l'utilisateur connecté de changer son mot de passe."""
    
    # On instancie le contrôleur avec la session DB
    auth_ctrl = AuthController(db_session=db)
    
    auth_ctrl.change_user_password(
        user_id=current_user.user_id, # L'ID vient du token décodé
        old_pass=password_data.old_password,
        new_pass=password_data.new_password
    )

    return {"message": "Mot de passe mis à jour avec succès"}


def get_self_user_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserController:
    # Factory locale : ne PAS importer users_endpoint.py::get_user_controller
    # ici, ce module y est deja importe (get_current_user/role_required) -
    # un import dans l'autre sens creerait un cycle.
    user_repo = UserRepository(session=db)
    role_repo = RoleRepository(session=db)
    return UserController(user_repo=user_repo, role_repo=role_repo)


@router.put("/auth/profile", tags=["Authentication"])
def update_my_profile(
    data: SelfProfileUpdate,
    user_ctrl: UserController = Depends(get_self_user_controller),
    current_user = Depends(get_current_user),
):
    """
    Permet à l'utilisateur connecté de modifier son propre profil
    (full_name/email/contact uniquement - jamais username/password/role_id/
    is_active/specialty_id, absents de SelfProfileUpdate). user_id vient
    exclusivement du JWT décodé (current_user), jamais du corps de la
    requête.
    """
    try:
        payload = data.model_dump(exclude_unset=True)
        updated = user_ctrl.update_user(current_user.user_id, payload)
        return {
            "id": updated.user_id,
            "username": updated.username,
            "full_name": updated.full_name,
            "email": updated.email,
            "contact": updated.contact,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except IntegrityError as ie:
        try:
            user_ctrl.user_repo.session.rollback()
        except Exception:
            pass
        raise translate_integrity_error(ie)
    except SQLAlchemyError as se:
        try:
            user_ctrl.user_repo.session.rollback()
        except Exception:
            pass
        logger.exception("SQLAlchemyError updating own profile: %s", se)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour du profil")
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))

