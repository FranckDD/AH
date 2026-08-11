# Chantier 2d-1 — Tests d'intégration auth + RBAC — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Couvrir par des tests d'intégration réels (vraie base `AH2`, vraies requêtes HTTP via `TestClient`) le chemin d'authentification complet (`POST /auth/login`, `GET /auth/me`, `POST /auth/logout`) et le contrôle d'accès par rôle (`role_required()`), en s'appuyant sur l'infrastructure `db_session`/`override_get_db` livrée au chantier 2d-0.

**Architecture:** Une factory `create_test_user()` et une fixture `autouse` de réinitialisation du rate limiter, ajoutées à `tests/conftest.py` (infrastructure partagée, réutilisable par 2d-2 à 2d-4). Trois fichiers de tests, un par responsabilité : login, cycle de vie du token, RBAC.

**Tech Stack:** pytest, SQLAlchemy 2.0, FastAPI `TestClient`, `python-jose`, PostgreSQL (base `AH2` locale réelle).

## Global Constraints

- Comptes de test **éphémères uniquement** — jamais de dépendance aux comptes seedés existants (`admin_test`, etc.) ni à leurs mots de passe.
- `create_test_user()` utilise `session.flush()`, jamais `session.commit()` — la ligne doit rester dans la transaction annulée par `db_session`.
- Le message d'échec de login reste volontairement générique dans les 3 cas (mauvais mot de passe, compte inactif, utilisateur inconnu) : 401 "Identifiants invalides" — comportement existant, ne pas le faire varier.
- `GET /users/` (pas `/admin/users/` — `users_endpoint.py` a `prefix="/users"` et n'a aucun préfixe supplémentaire dans `main.py`) nécessite de surcharger **deux** `get_db()` distincts : celui d'`auth_endpoints` (via `role_required` → `get_current_user`) et celui d'`users_endpoint` (via `get_user_controller`).
- Ne pas tester la limite de débit elle-même (5/minute) — seulement neutraliser son effet de bord entre tests via `limiter.reset()`.

---

## Task 1: Infrastructure partagée — factory de compte + reset du rate limiter

**Files:**
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: `db_session` fixture, `override_get_db()` (chantier 2d-0, déjà dans ce fichier)
- Produces: `create_test_user(session, username, role_name, password="TestPass123!", is_active=True) -> User`, fixture `autouse` `reset_rate_limiter` (aucune interface exposée, agit en arrière-plan sur toute la suite)

- [ ] **Step 1: Ajouter les imports nécessaires en tête de `tests/conftest.py`**

Après les imports existants (`sys`, `os`, `pytest`, `event`, `Session`, `engine`), ajouter :

```python
from models.user import User, pwd_context
from models.application_role import ApplicationRole
from api_backend.backend_app.rate_limit import limiter
```

- [ ] **Step 2: Ajouter `create_test_user()` à la fin de `tests/conftest.py`**

```python
def create_test_user(session, username, role_name, password="TestPass123!", is_active=True):
    """
    Cree un utilisateur ephemere dans la transaction de test (flush, jamais
    commit) rattache a un role deja seede en base (ex: 'admin', 'secretaire').
    Reutilisable par les sous-chantiers 2d-2 a 2d-4.
    """
    role = session.query(ApplicationRole).filter_by(role_name=role_name).one()
    user = User(
        username=username,
        password_hash=pwd_context.hash(password),
        full_name=f"Test {username}",
        role_id=role.role_id,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user
```

- [ ] **Step 3: Ajouter la fixture de reset du rate limiter à la fin de `tests/conftest.py`**

```python
@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Evite que les tests successifs de /auth/login ne se bloquent entre eux :
    TestClient envoie toutes ses requetes avec la meme adresse cliente
    ('testclient'), slowapi la traiterait sinon comme un seul appelant
    cumulant les appels de tous les tests (limite : 5/minute, SEC-05).
    """
    limiter.reset()
    yield
```

- [ ] **Step 4: Vérifier que le fichier s'importe sans erreur**

```bash
python -c "from tests.conftest import db_session, override_get_db, create_test_user, reset_rate_limiter; print('ok')"
```

Attendu : `ok`, pas d'exception.

- [ ] **Step 5: Vérifier manuellement que la factory fonctionne (test jetable, non committé)**

Créer temporairement `tests/test_scratch_factory.py` :

```python
from tests.conftest import create_test_user


def test_create_test_user_works(db_session):
    user = create_test_user(db_session, "scratch_admin", "admin")
    assert user.user_id is not None
    assert user.username == "scratch_admin"
```

Lancer :

```bash
pytest tests/test_scratch_factory.py -v
```

Attendu : `PASS`. Puis supprimer ce fichier (il ne fait pas partie du plan, sert uniquement à valider la factory avant de l'utiliser dans les tests réels) :

```bash
rm tests/test_scratch_factory.py
```

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py
git commit -m "test: factory create_test_user + reset du rate limiter (chantier 2d-1)

create_test_user() : insere un utilisateur ephemere (flush, jamais
commit) rattache a un role deja seede (admin/secretaire), reutilisable
par les sous-chantiers 2d-2 a 2d-4.

reset_rate_limiter (autouse) : evite que TestClient (adresse cliente
unique 'testclient') ne declenche la limite 5/minute de /auth/login
(SEC-05) en enchainant les tests.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Tests de login (`tests/test_auth_login.py`)

**Files:**
- Create: `tests/test_auth_login.py`

**Interfaces:**
- Consumes: `db_session`, `override_get_db()`, `create_test_user()` (Task 1)
- Produces: rien — fichier de test terminal

- [ ] **Step 1: Écrire les 4 tests**

```python
# tests/test_auth_login.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jose import jwt as jose_jwt
from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.config import JWT_SECRET, JWT_ALGORITHM
from tests.conftest import override_get_db, create_test_user


def _login(client, username, password):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )


def test_login_success_returns_token_with_correct_role(db_session):
    create_test_user(db_session, "test_login_admin", "admin", password="Correct123!")
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = _login(client, "test_login_admin", "Correct123!")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    token = resp.json()["access_token"]
    payload = jose_jwt.decode(
        token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
        issuer="ah2-api", audience="ah2-web",
    )
    assert payload["roles"] == ["admin"]


def test_login_wrong_password_returns_401(db_session):
    create_test_user(db_session, "test_login_wrongpass", "admin", password="Correct123!")
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = _login(client, "test_login_wrongpass", "WrongPassword!")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"


def test_login_inactive_account_returns_401(db_session):
    create_test_user(db_session, "test_login_inactive", "admin", password="Correct123!", is_active=False)
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = _login(client, "test_login_inactive", "Correct123!")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"


def test_login_unknown_username_returns_401(db_session):
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = _login(client, "does_not_exist_at_all", "Whatever123!")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_auth_login.py -v
```

Attendu : 4 `PASS`.

- [ ] **Step 3: Si un test échoue**

Le cas le plus probable : `role_id`/`role_name` introuvable si le rôle `"admin"` n'est plus seedé en base sous ce nom exact — vérifier avec `python -c "from api_backend.backend_app.database import engine; from sqlalchemy import text; print(engine.connect().execute(text(\"SELECT role_name FROM application_roles\")).fetchall())"`. Ne pas modifier la factory pour contourner — la base `AH2` locale doit avoir ce rôle seedé (confirmé pendant le cadrage : `admin`, `secretaire`, `medecin`, `nurse`, `laborantin`, `Psychologist`, `Assistant`).

- [ ] **Step 4: Commit**

```bash
git add tests/test_auth_login.py
git commit -m "test: couverture POST /auth/login (chantier 2d-1)

Succes (role correctement encode dans le token), mot de passe errone,
compte inactif, utilisateur inconnu - les 3 derniers partagent le meme
message generique 401 'Identifiants invalides' (comportement existant,
pas de fuite d'info sur l'existence d'un compte).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Tests du cycle de vie du token (`tests/test_auth_token_lifecycle.py`)

**Files:**
- Create: `tests/test_auth_token_lifecycle.py`

**Interfaces:**
- Consumes: `db_session`, `override_get_db()`, `create_test_user()` (Task 1)
- Produces: rien — fichier de test terminal

- [ ] **Step 1: Écrire les 4 tests**

```python
# tests/test_auth_token_lifecycle.py
import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jose import jwt as jose_jwt
from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.config import JWT_SECRET, JWT_ALGORITHM
from tests.conftest import override_get_db, create_test_user

JWT_ISSUER = "ah2-api"
JWT_AUDIENCE = "ah2-web"


def _login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


def test_valid_token_allows_access_to_me_endpoint(db_session):
    create_test_user(db_session, "test_token_valid", "admin", password="Correct123!")
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        token = _login(client, "test_token_valid", "Correct123!").json()["access_token"]
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["application_role"]["role_name"] == "admin"


def test_expired_token_returns_401(db_session):
    user = create_test_user(db_session, "test_token_expired", "admin", password="Correct123!")
    expired_payload = {
        "sub": str(user.user_id),
        "roles": ["admin"],
        "exp": int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).timestamp()),
        "ver": 0,
        "jti": "test-expired-jti",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    token = jose_jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token expiré"


def test_tampered_signature_returns_401(db_session):
    user = create_test_user(db_session, "test_token_tampered", "admin", password="Correct123!")
    payload = {
        "sub": str(user.user_id),
        "roles": ["admin"],
        "exp": int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).timestamp()),
        "ver": 0,
        "jti": "test-tampered-jti",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    token = jose_jwt.encode(payload, "wrong-secret-not-the-real-one", algorithm=JWT_ALGORITHM)

    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token invalide ou expiré"


def test_logout_revokes_current_token(db_session):
    create_test_user(db_session, "test_token_logout", "admin", password="Correct123!")
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        token = _login(client, "test_token_logout", "Correct123!").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        logout_resp = client.post("/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        reuse_resp = client.get("/auth/me", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["detail"] == "Session invalidée, veuillez vous reconnecter"
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_auth_token_lifecycle.py -v
```

Attendu : 4 `PASS`.

- [ ] **Step 3: Si `test_expired_token_returns_401` ou `test_tampered_signature_returns_401` échouent avec une erreur `python-jose` inattendue plutôt qu'un 401 propre**

Rappel du chantier SEC-09 : `jose_jwt.decode()` exige `audience=` dès qu'un token contient une claim `aud` — déjà géré côté route (`auth_endpoints.get_current_user` passe `issuer=`/`audience=`). Si l'erreur persiste, vérifier que le payload forgé dans le test contient bien `iss`/`aud` identiques à `JWT_ISSUER`/`JWT_AUDIENCE` définis dans `auth_endpoints.py`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_auth_token_lifecycle.py
git commit -m "test: cycle de vie du token JWT (chantier 2d-1, SEC-09)

Token valide, token expire, signature invalide (forges directement),
et sequence complete login -> logout -> reutilisation de l'ancien
token -> 401 (verifie la revocation effective via token_version).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Tests RBAC (`tests/test_rbac.py`)

**Files:**
- Create: `tests/test_rbac.py`

**Interfaces:**
- Consumes: `db_session`, `override_get_db()`, `create_test_user()` (Task 1)
- Produces: rien — fichier de test terminal

- [ ] **Step 1: Écrire les 3 tests**

```python
# tests/test_rbac.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from tests.conftest import override_get_db, create_test_user


def _login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


def _override_both(session):
    override_get_db(app, auth_endpoints, session)
    override_get_db(app, users_endpoint, session)


def test_admin_role_can_list_users(db_session):
    create_test_user(db_session, "test_rbac_admin", "admin", password="Correct123!")
    _override_both(db_session)
    try:
        client = TestClient(app)
        token = _login(client, "test_rbac_admin", "Correct123!").json()["access_token"]
        resp = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200


def test_secretaire_role_forbidden_from_admin_route(db_session):
    create_test_user(db_session, "test_rbac_secretaire", "secretaire", password="Correct123!")
    _override_both(db_session)
    try:
        client = TestClient(app)
        token = _login(client, "test_rbac_secretaire", "Correct123!").json()["access_token"]
        resp = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_unauthenticated_request_returns_401(db_session):
    _override_both(db_session)
    try:
        client = TestClient(app)
        resp = client.get("/users/")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_rbac.py -v
```

Attendu : 3 `PASS`.

- [ ] **Step 3: Si `test_admin_role_can_list_users` échoue avec une erreur 500 liée à `UserOut`/validation Pydantic**

Cause probable : un des comptes seedés déjà présents en base (non liés à ce test) a des données incompatibles avec `UserOut` (ex. `full_name` vide). Ne pas modifier la route pour contourner — signaler l'anomalie plutôt que la masquer ; c'est un signal utile sur l'état réel des données de `AH2`, pas un défaut du test.

- [ ] **Step 4: Commit**

```bash
git add tests/test_rbac.py
git commit -m "test: RBAC via role_required() sur GET /users/ (chantier 2d-1)

Role admin autorise, role secretaire refuse (403), non authentifie
(401). Necessite un double override_get_db (auth_endpoints +
users_endpoint) - confirme concretement le besoin ARC-05.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Vérification finale

**Files:** aucun (vérification uniquement)

- [ ] **Step 1: Suite de tests complète**

```bash
pytest tests/ -v
```

Attendu : tous les tests passent, y compris les 11 nouveaux de ce chantier (Task 2 : 4, Task 3 : 4, Task 4 : 3). Les 4 échecs pré-existants et non liés (`test_patient_repo.py` x2, `test_prescription_repo.py` x2) restent identiques.

- [ ] **Step 2: Confirmer l'absence de donnée résiduelle**

```bash
python -c "
from api_backend.backend_app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    rows = conn.execute(text(\"SELECT username FROM users WHERE username LIKE 'test_%'\")).fetchall()
    print(rows)
"
```

Attendu : `[]`.

- [ ] **Step 3: Mettre à jour `docs/superpowers/SUIVI-AVANCEMENT.md`**

Marquer 2d-1 comme terminé dans le tableau de la feuille de route (commits de Task 1 à 4), ajouter un résumé dans la section détail (nouveaux fichiers de test, factory `create_test_user` réutilisable pour 2d-2 à 2d-4, confirmation concrète du besoin `ARC-05`).

- [ ] **Step 4: Commit de la mise à jour du suivi**

```bash
git add docs/superpowers/SUIVI-AVANCEMENT.md
git commit -m "docs: cloture du chantier 2d-1 dans le suivi d'avancement

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git push origin AH2_V3-1
```

- [ ] **Step 5: Récapitulatif**

Confirmer un par un :
- [ ] Login : succès, mauvais mot de passe, compte inactif, utilisateur inconnu — tous couverts
- [ ] Cycle de vie du token : valide, expiré, signature invalide, révocation via logout — tous couverts
- [ ] RBAC : rôle autorisé, rôle refusé, non authentifié — tous couverts sur une vraie route
- [ ] Aucune donnée résiduelle dans `AH2`
- [ ] Prêt pour 2d-2 (tests patients)
