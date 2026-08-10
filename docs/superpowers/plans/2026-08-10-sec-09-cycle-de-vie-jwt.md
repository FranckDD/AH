# SEC-09 — Cycle de vie JWT et en-têtes de sécurité — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le JWT réellement révocable (déconnexion serveur, pas seulement client), ajouter `jti`/`iss`/`aud`, poser des en-têtes de sécurité HTTP de base, et câbler `IS_PROD`.

**Architecture:** Colonne `token_version` sur `users` (migration SQL directe, pas d'Alembic), comparée à chaque requête dans `get_current_user()`. Nouvelle route `POST /auth/logout` qui incrémente cette version, invalidant tous les jetons déjà émis pour le compte. Middleware Starlette pour les en-têtes de sécurité.

**Tech Stack:** FastAPI, python-jose, SQLAlchemy, PostgreSQL, Vue/Pinia.

## Global Constraints

- Token reste en `localStorage`, aucun refresh token — décisions déjà validées (voir spec).
- `PUT /auth/password` / `change_user_password()` **n'existe pas sur `HEAD`** (travail en cours non commité) — ne pas y toucher, ne pas ajouter de révocation à cette fonctionnalité dans ce chantier.
- `login()`, le bloc de décodage du token, et la récupération de l'utilisateur dans `get_current_user()` sont **identiques entre `HEAD` et la copie de travail** — éditables et isolables directement. Le bloc de résolution des rôles dans `get_current_user()` (repli permissif local) et la route `/auth/password` sont uniquement dans la copie de travail — **ne pas y toucher, ne pas les committer**.
- CSP explicitement hors périmètre (voir spec).

---

## Task 1: Colonne `token_version` sur `users`

**Files:**
- Modify: `models/user.py` (fichier propre)
- Migration: SQL direct (pas de fichier de migration, pas d'Alembic pour l'instant)

**Interfaces:**
- Produces: `User.token_version` (int, défaut 0), consommé par Task 2 (backend) et lu par toute requête authentifiée.

- [ ] **Step 1: Appliquer la migration SQL**

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0;"
```

Attendu : `ALTER TABLE`.

- [ ] **Step 2: Vérifier**

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "SELECT username, token_version FROM users LIMIT 3;"
```

Attendu : la colonne apparaît, valeur `0` pour toutes les lignes existantes.

- [ ] **Step 3: Ajouter le champ au modèle SQLAlchemy**

Dans `models/user.py`, remplacer :

```python
    role_id = Column(Integer, ForeignKey('application_roles.role_id'))
    email = Column(String(150), unique=True, nullable=True)
    contact = Column(String(50), nullable=True)
```

par :

```python
    role_id = Column(Integer, ForeignKey('application_roles.role_id'))
    email = Column(String(150), unique=True, nullable=True)
    contact = Column(String(50), nullable=True)
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
```

- [ ] **Step 4: Vérifier que le modèle se charge sans erreur**

```bash
python -c "from models.user import User; print(User.token_version)"
```

Attendu : pas d'exception, affiche une représentation de colonne SQLAlchemy.

- [ ] **Step 5: Commit**

```bash
git add models/user.py
git commit -m "feat(security): ajouter token_version pour la revocation JWT (SEC-09)

Colonne SQL ajoutee directement (ALTER TABLE), pas d'Alembic pour
l'instant. Utilisee par get_current_user() (Task 2) pour comparer
la version du token a la version courante en base et invalider les
tokens deja emis apres une deconnexion.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Émission et vérification du token (`ver`, `jti`, `iss`, `aud`)

**Files:**
- Modify: `api_backend/backend_app/routes/auth/auth_endpoints.py` (isolation requise — voir Global Constraints)
- Test: `tests/test_jwt_lifecycle.py` (nouveau)

**Interfaces:**
- Consumes: `User.token_version` (Task 1)
- Produces: le payload du JWT gagne les claims `ver`, `jti`, `iss`, `aud`, consommés uniquement par `get_current_user()` dans ce même fichier.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/test_jwt_lifecycle.py` :

```python
# tests/test_jwt_lifecycle.py
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock, patch
from jose import jwt as jose_jwt
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from api_backend.backend_app.config import JWT_SECRET, JWT_ALGORITHM
from api_backend.backend_app.routes.auth import auth_endpoints as auth_mod


def make_fake_user(user_id=1, token_version=0):
    user = MagicMock()
    user.user_id = user_id
    user.token_version = token_version
    user.application_role = None
    return user


def build_app_with_fake_user(fake_user):
    app = FastAPI()

    @app.get("/protected")
    def protected(current_user=Depends(auth_mod.get_current_user)):
        return {"user_id": current_user.user_id}

    fake_ctrl = MagicMock()
    fake_ctrl.user_repo.get_user_by_id.return_value = fake_user

    patcher = patch.object(auth_mod, "AuthController", return_value=fake_ctrl)
    patcher.start()
    return app, patcher


def make_token(sub, ver, iss="ah2-api", aud="ah2-web", exp_delta=600):
    payload = {"sub": str(sub), "roles": [], "exp": int(time.time()) + exp_delta}
    if ver is not None:
        payload["ver"] = ver
    if iss is not None:
        payload["iss"] = iss
    if aud is not None:
        payload["aud"] = aud
    return jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_matching_token_version_is_accepted():
    fake_user = make_fake_user(user_id=1, token_version=2)
    app, patcher = build_app_with_fake_user(fake_user)
    try:
        token = make_token(sub=1, ver=2)
        client = TestClient(app)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
    finally:
        patcher.stop()


def test_stale_token_version_is_rejected():
    fake_user = make_fake_user(user_id=1, token_version=3)
    app, patcher = build_app_with_fake_user(fake_user)
    try:
        token = make_token(sub=1, ver=2)  # ancien token, version depassee (logout entre-temps)
        client = TestClient(app)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    finally:
        patcher.stop()


def test_wrong_audience_is_rejected():
    fake_user = make_fake_user(user_id=1, token_version=0)
    app, patcher = build_app_with_fake_user(fake_user)
    try:
        token = make_token(sub=1, ver=0, aud="autre-app")
        client = TestClient(app)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    finally:
        patcher.stop()


def test_wrong_issuer_is_rejected():
    fake_user = make_fake_user(user_id=1, token_version=0)
    app, patcher = build_app_with_fake_user(fake_user)
    try:
        token = make_token(sub=1, ver=0, iss="autre-service")
        client = TestClient(app)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    finally:
        patcher.stop()
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

```bash
pytest tests/test_jwt_lifecycle.py -v
```

Attendu : `test_stale_token_version_is_rejected`, `test_wrong_audience_is_rejected`, `test_wrong_issuer_is_rejected` échouent (reçoivent `200` au lieu de `401` — rien ne vérifie encore `ver`/`iss`/`aud`). `test_matching_token_version_is_accepted` passe déjà.

- [ ] **Step 3: Ajouter les constantes et l'import `uuid`**

Dans `api_backend/backend_app/routes/auth/auth_endpoints.py`, remplacer :

```python
from ...rate_limit import limiter
from controller.auth_controller import AuthController
from .schemas import Token
from typing import Any

router = APIRouter()
```

par :

```python
from ...rate_limit import limiter
from controller.auth_controller import AuthController
from .schemas import Token
from typing import Any
import uuid

JWT_ISSUER = "ah2-api"
JWT_AUDIENCE = "ah2-web"

router = APIRouter()
```

- [ ] **Step 4: Enrichir le payload dans `login()`**

Remplacer :

```python
    # construire le token (sub + roles + exp)
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user.user_id), "roles": role_list, "exp": int(expire.timestamp())}

    token = jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)  # pyright: ignore[reportArgumentType]
    return {"access_token": token, "token_type": "bearer"}
```

par :

```python
    # construire le token (sub + roles + exp + hygiene JWT : ver/jti/iss/aud)
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
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
```

- [ ] **Step 5: Valider `iss`/`aud` au décodage dans `get_current_user()`**

Remplacer :

```python
    # --- Décodage unique du token ---
    try:
        payload = jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expiré")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré")
```

par :

```python
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
```

- [ ] **Step 6: Vérifier `ver` après récupération de l'utilisateur**

Remplacer :

```python
    # --- Récupérer l'utilisateur depuis le repository ---
    auth_ctrl = AuthController(db_session=db)
    user = auth_ctrl.user_repo.get_user_by_id(user_id_int)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur non trouvé")

    # Charger explicitement la relation application_role si besoin (sécurise l'accès aux attributs)
```

par :

```python
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
```

- [ ] **Step 7: Ajouter la route `POST /auth/logout`**

Ajouter à la toute fin du fichier (après `return wrapper` qui clôt `role_required`) :

```python

@router.post("/auth/logout", status_code=status.HTTP_200_OK, tags=["Authentication"])
def logout(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Révoque tous les tokens actuellement émis pour l'utilisateur courant."""
    current_user.token_version = (getattr(current_user, "token_version", 0) or 0) + 1
    db.add(current_user)
    db.commit()
    return {"message": "Déconnexion effectuée"}
```

- [ ] **Step 8: Lancer les tests pour vérifier qu'ils passent**

```bash
pytest tests/test_jwt_lifecycle.py -v
```

Attendu : 4 tests `PASS`.

- [ ] **Step 9: Isoler et stager le correctif (le fichier porte du travail en cours ailleurs)**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:api_backend/backend_app/routes/auth/auth_endpoints.py > "$SCRATCH/auth_endpoints_base_sec09.py"
python - <<PYEOF
path = r"$SCRATCH/auth_endpoints_base_sec09.py"
content = open(path, encoding="utf-8").read()

replacements = [
    (
        '''from ...rate_limit import limiter
from controller.auth_controller import AuthController
from .schemas import Token
from typing import Any

router = APIRouter()''',
        '''from ...rate_limit import limiter
from controller.auth_controller import AuthController
from .schemas import Token
from typing import Any
import uuid

JWT_ISSUER = "ah2-api"
JWT_AUDIENCE = "ah2-web"

router = APIRouter()'''
    ),
    (
        '''    # construire le token (sub + roles + exp)
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user.user_id), "roles": role_list, "exp": int(expire.timestamp())}

    token = jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)  # pyright: ignore[reportArgumentType]
    return {"access_token": token, "token_type": "bearer"}''',
        '''    # construire le token (sub + roles + exp + hygiene JWT : ver/jti/iss/aud)
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
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
    return {"access_token": token, "token_type": "bearer"}'''
    ),
    (
        '''    # --- Décodage unique du token ---
    try:
        payload = jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expiré")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré")''',
        '''    # --- Décodage unique du token ---
    try:
        payload = jose_jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER, audience=JWT_AUDIENCE,
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expiré")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré")'''
    ),
    (
        '''    user = auth_ctrl.user_repo.get_user_by_id(user_id_int)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur non trouvé")

    # Charger explicitement la relation application_role si besoin (sécurise l'accès aux attributs)''',
        '''    user = auth_ctrl.user_repo.get_user_by_id(user_id_int)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur non trouvé")

    # --- Révocation : le token doit correspondre à la version courante ---
    token_ver = payload.get("ver")
    if token_ver != (getattr(user, "token_version", 0) or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalidée, veuillez vous reconnecter")

    # Charger explicitement la relation application_role si besoin (sécurise l'accès aux attributs)'''
    ),
]

for old, new in replacements:
    assert old in content, f"pattern introuvable: {old[:60]}"
    content = content.replace(old, new)

content = content.rstrip("\n") + '''

@router.post("/auth/logout", status_code=status.HTTP_200_OK, tags=["Authentication"])
def logout(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Révoque tous les tokens actuellement émis pour l'utilisateur courant."""
    current_user.token_version = (getattr(current_user, "token_version", 0) or 0) + 1
    db.add(current_user)
    db.commit()
    return {"message": "Déconnexion effectuée"}
'''

open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/auth_endpoints_base_sec09.py")
git update-index --cacheinfo 100644,$BLOB,api_backend/backend_app/routes/auth/auth_endpoints.py
git diff --cached -- api_backend/backend_app/routes/auth/auth_endpoints.py
```

Vérifier que le diff affiché ne contient que : les constantes/import, `login()`, le décodage, le check `ver`, et la nouvelle route `/auth/logout` — rien sur le bloc de résolution des rôles ni sur `/auth/password`.

- [ ] **Step 10: Commit**

```bash
git add tests/test_jwt_lifecycle.py
git commit -m "feat(security): revocation JWT via token_version, jti/iss/aud (SEC-09)

login() emet desormais ver (token_version courant), jti, iss, aud.
get_current_user() valide iss/aud au decodage et rejette tout token
dont ver ne correspond plus a la version courante en base.

Nouvelle route POST /auth/logout : incremente token_version de
l'utilisateur courant, invalidant tous les tokens deja emis pour ce
compte (deconnexion serveur reelle, pas seulement client).

auth_endpoints.py porte du travail en cours non lie a ce chantier
(repli permissif local sur la resolution des roles, route
/auth/password entiere absente de HEAD) : seuls les hunks lies a
SEC-09 sont inclus dans ce commit (injection directe dans l'index).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Front — déconnexion appelle réellement le serveur

**Files:**
- Modify: `ah2-admin-web/src/stores/auth.js` (fichier propre)

**Interfaces:**
- Consumes: `POST /auth/logout` (Task 2)
- Produces: rien consommé par une tâche suivante

- [ ] **Step 1: Modifier `logout()`**

Remplacer :

```javascript
    logout() {
      // 1. Nettoyer l'état Pinia
      this.token = null;
      this.user = null;
      
      // 2. Nettoyer le LocalStorage
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // 3. 🟢 Redirection forcée via le router Vue
      router.push('/login');
    }
```

par :

```javascript
    async logout() {
      // 0. Revoquer le token cote serveur (best-effort : si l'appel echoue,
      //    on nettoie quand meme localement pour ne jamais bloquer l'utilisateur)
      try {
        await api.post('/auth/logout');
      } catch (error) {
        console.warn("Echec de la revocation serveur du token :", error);
      }

      // 1. Nettoyer l'état Pinia
      this.token = null;
      this.user = null;

      // 2. Nettoyer le LocalStorage
      localStorage.removeItem('token');
      localStorage.removeItem('user');

      // 3. 🟢 Redirection forcée via le router Vue
      router.push('/login');
    }
```

**Note :** cette action appelle `api.post('/auth/logout')` **avant** de nettoyer `localStorage`, pour que l'intercepteur de requête (`services/api.js`) ait encore le token courant à joindre à l'en-tête `Authorization`. `api` est déjà importé en haut du fichier depuis le chantier 0 (`import api from '@/services/api';`).

- [ ] **Step 2: Vérifier le build**

```bash
cd ah2-admin-web
npm run build
cd -
```

Attendu : succès.

- [ ] **Step 3: Commit**

```bash
git add ah2-admin-web/src/stores/auth.js
git commit -m "fix(security): la deconnexion revoque reellement le token (SEC-09)

logout() appelle POST /auth/logout avant de nettoyer le localStorage,
en best-effort. Sans cet appel, se deconnecter n'oubliait le token
que localement : un attaquant en possession du jeton pouvait
continuer a l'utiliser jusqu'a son expiration naturelle.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: En-têtes de sécurité HTTP + `IS_PROD`

**Files:**
- Modify: `api_backend/backend_app/config.py` (fichier propre)
- Modify: `api_backend/backend_app/main.py` (isolation requise — voir Global Constraints)
- Test: manuel (voir Step 4)

**Interfaces:**
- Produces: `IS_PROD: bool` exporté depuis `config.py`, consommé uniquement par le middleware ajouté dans `main.py`

- [ ] **Step 1: Exposer `IS_PROD` dans `config.py`**

Remplacer :

```python
IS_CLIENT = os.getenv("IS_CLIENT", "false").lower() == "true"
```

par :

```python
IS_CLIENT = os.getenv("IS_CLIENT", "false").lower() == "true"
IS_PROD = os.getenv("IS_PROD", "false").lower() == "true"
```

- [ ] **Step 2: Ajouter le middleware d'en-têtes dans `main.py`**

Remplacer :

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .rate_limit import limiter

app = FastAPI(title="AH2 API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

par :

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .rate_limit import limiter
from .config import IS_PROD

app = FastAPI(title="AH2 API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response
```

(`Request` est déjà importé plus haut dans le fichier, ligne `from fastapi import Request`.)

- [ ] **Step 3: Isoler et stager (le fichier porte du travail en cours ailleurs — CORS)**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:api_backend/backend_app/main.py > "$SCRATCH/main_base_sec09.py"
python - <<PYEOF
old = '''from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .rate_limit import limiter

app = FastAPI(title="AH2 API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)'''
new = '''from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .rate_limit import limiter
from .config import IS_PROD

app = FastAPI(title="AH2 API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response'''
path = r"$SCRATCH/main_base_sec09.py"
content = open(path, encoding="utf-8").read()
assert old in content, "pattern introuvable"
content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/main_base_sec09.py")
git update-index --cacheinfo 100644,$BLOB,api_backend/backend_app/main.py
git diff --cached -- api_backend/backend_app/main.py
```

Vérifier que le diff ne contient que l'ajout du middleware, rien sur la section CORS plus bas dans le fichier.

- [ ] **Step 4: Test manuel**

```bash
PYTHONIOENCODING=utf-8 uvicorn api_backend.backend_app.main:app --port 8000 &
sleep 5
curl -sI http://127.0.0.1:8000/health | grep -i "x-content-type-options\|x-frame-options\|referrer-policy\|strict-transport"
```

Attendu : `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` présents. `Strict-Transport-Security` **absent** (`IS_PROD` non positionné à `true` dans `.env` local).

- [ ] **Step 5: Commit**

```bash
git add api_backend/backend_app/config.py
git commit -m "feat(security): en-tetes de securite HTTP + cablage IS_PROD (SEC-09)

X-Content-Type-Options, X-Frame-Options, Referrer-Policy sur toute
reponse. Strict-Transport-Security ajoute uniquement si IS_PROD est
vrai (n'a pas de sens en HTTP local). IS_PROD etait defini dans .env
depuis le debut mais jamais lu par le code.

CSP volontairement exclu : necessite un audit des origines de
ressources de la console Vue avant calibration, pour ne pas casser
l'application silencieusement (voir spec).

main.py porte du travail en cours non lie a ce chantier (config
CORS) : seul le middleware est inclus dans ce commit (injection
directe dans l'index).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Vérification finale de bout en bout

**Files:** aucun (vérification uniquement)

- [ ] **Step 1: Suite de tests complète**

```bash
pytest tests/ -v
```

Attendu : tous les tests passent, y compris les 4 nouveaux de Task 2. Les échecs pré-existants et non liés (chantier 0 : `test_patient_repo.py` ; chantier 1 : flakiness d'ordre sur `test_prescription_repo.py`) restent présents et sans lien avec ce chantier.

- [ ] **Step 2: Vérification manuelle — cycle de vie complet**

```bash
# 1. Connexion
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login -d "username=admin_test&password=<mot_de_passe>" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Le token fonctionne
curl -s -o /dev/null -w "avant logout: %{http_code}\n" http://127.0.0.1:8000/auth/me -H "Authorization: Bearer $TOKEN"

# 3. Déconnexion
curl -s -X POST http://127.0.0.1:8000/auth/logout -H "Authorization: Bearer $TOKEN" -w "\nHTTP:%{http_code}\n"

# 4. Le même token ne fonctionne plus
curl -s -o /dev/null -w "apres logout: %{http_code}\n" http://127.0.0.1:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

Attendu : `avant logout: 200`, logout renvoie `200`, `apres logout: 401`.

- [ ] **Step 3: Récapitulatif**

Confirmer un par un :
- [ ] `token_version` existe en base, défaut `0`
- [ ] `login()` émet `ver`/`jti`/`iss`/`aud`
- [ ] `get_current_user()` rejette un `ver` périmé et un `iss`/`aud` incorrect, 4 tests passent
- [ ] `POST /auth/logout` révoque réellement le token (vérifié en Step 2)
- [ ] Le front appelle `/auth/logout` avant de nettoyer le stockage local
- [ ] En-têtes de sécurité présents, `Strict-Transport-Security` absent en dev
- [ ] Le bloc de résolution des rôles et `/auth/password` dans la copie de travail n'ont subi aucune modification par ce chantier
