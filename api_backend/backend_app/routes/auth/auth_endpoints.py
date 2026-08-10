import datetime
from ...security.role_map import normalize_role_name, normalize_roles_list
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import ExpiredSignatureError, jwt as jose_jwt ,JWTError
from ...database import SessionLocal
from ...config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from ...rate_limit import limiter
from controller.auth_controller import AuthController
from .schemas import Token
from typing import Any
import uuid

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

    # construire le token (sub + roles + exp + hygiene JWT : ver/jti/iss/aud)
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.user_id),
        "roles": role_list,
        "exp": int(expire.timestamp()),
        "ver": getattr(user, "token_version", 0) or 0,
        "jti": uuid.uuid4().hex,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }

    token = jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)  # pyright: ignore[reportArgumentType]
    return {"access_token": token, "token_type": "bearer"}


# Exemple de dependency pour obtenir l'utilisateur courant

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Any:
    """
    Décode et vérifie le JWT, retourne l'objet utilisateur.
    Lève HTTPException(401) si le token est invalide/expiré ou si l'utilisateur n'existe pas."""

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

    # --- Normalisation des rôles en codes canoniques ---
    roles_from_token = payload.get("roles")
    if isinstance(roles_from_token, str):
        roles_from_token = [roles_from_token]
    

    canonical_roles: list[str] = []

    # préférer la source DB (role_code ou role_name) si disponible
    app_role = getattr(user, "application_role", None)
    if app_role:
        # essayer role_code (si tu as ajouté role_code en base)
        role_code_db = getattr(app_role, "role_code", None)
        if role_code_db:
            canon = normalize_role_name(str(role_code_db))
            if canon:
                canonical_roles = [canon]

        if not canonical_roles:
            role_name_db = getattr(app_role, "role_name", None)
            if role_name_db:
                canon = normalize_role_name(str(role_name_db))
                if canon:
                    canonical_roles = [canon]

    # 3) fallback vers les rôles fournis par le token si aucune info utile en DB
    if not canonical_roles and roles_from_token:
        canonical_roles = normalize_roles_list(list(roles_from_token))

    # 4) dernier fallback -> liste vide
    user.roles = canonical_roles or []

    return user

@router.get("/auth/me", tags=["Authentication"])
def get_me(current_user=Depends(get_current_user)):
    """
    Retourne les infos du user courant basé sur le JWT.
    """
    return {
        "id": current_user.user_id,
        "username": getattr(current_user, "username", None),
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
