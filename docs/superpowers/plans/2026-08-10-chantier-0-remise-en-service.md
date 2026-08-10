# Chantier 0 — Remise en service + P0 sécurité — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fermer les vulnérabilités critiques identifiées par l'audit (secrets exposés, endpoints non protégés, upload arbitraire, identifiants en dur, absence de limitation de débit) et les deux bugs bloquants du front web, sans toucher à l'architecture des rôles ni au portage web.

**Architecture:** Corrections ciblées sur le backend FastAPI existant (`api_backend/backend_app/`), le noyau métier partagé (`controller/`, `models/`), les scripts d'import, et la console web Vue (`ah2-admin-web/`). Aucune nouvelle couche introduite ; les correctifs suivent les patterns déjà en place (`role_required`, `Depends`, structure des routers).

**Tech Stack:** FastAPI, SQLAlchemy, Pillow (déjà en dépendance), slowapi (nouvelle dépendance), git-filter-repo (outil, pas une dépendance du projet), Vue 3 / Vite.

## Global Constraints

- Le dépôt `github.com/FranckDD/AH` est **public** — tout secret présent dans l'historique est considéré compromis, indépendamment de la purge.
- Aucune valeur de secret ne doit apparaître dans le code, les commits, ou les sorties de commande de ce plan. Toute commande qui manipulerait un secret en clair doit être exécutée sans l'imprimer.
- `SEC-06` (repli permissif des rôles) est **hors périmètre** de ce chantier — n'y touchez pas, même si vous le croisez dans `auth_endpoints.py`.
- `GET /config/structure` reste **public** (décision utilisateur explicite) — seul `POST /config/structure` est protégé.
- Le dépôt contient 89 fichiers modifiés et 9 entrées non suivies, non liés à ce chantier (travail antérieur en cours). Ils ne doivent être ni committés, ni perdus — uniquement mis de côté (`git stash`) puis restaurés à l'identique autour de l'opération d'historique Git.
- Limitation de débit : implémentée par IP uniquement (`slowapi` + `get_remote_address`), pas par IP+utilisateur. Le `key_func` de slowapi est synchrone et ne peut pas lire le corps de la requête (asynchrone) de façon fiable sans plomberie supplémentaire non vérifiée ; l'IP seule est le choix sûr et documenté pour ce chantier. Voir Tâche 7.
- Seuil de limitation : `5/minute` (syntaxe `limits`/`slowapi` vérifiée), au lieu du `5/5 minutes` évoqué en spec — plus strict, syntaxe garantie fonctionnelle.

---

## Task 1: Rotation des secrets actifs

**Files:**
- Modify: `.env` (racine du projet, jamais commité)

**Interfaces:**
- Consumes: rien (première tâche)
- Produces: nouveau mot de passe PostgreSQL pour l'utilisateur `postgres`, nouveau `JWT_SECRET`, nouveau mot de passe pour le compte applicatif `admin_test`. Les tâches suivantes qui redémarrent l'API dépendent de ces nouvelles valeurs étant dans `.env`.

- [ ] **Step 1: Générer un nouveau `JWT_SECRET`**

Depuis la racine du projet :

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copier la valeur affichée (ne pas la coller dans un message de commit ou une sortie de log partagée).

- [ ] **Step 2: Mettre à jour `.env`**

Ouvrir `.env` et remplacer la ligne `JWT_SECRET=...` par la nouvelle valeur générée à l'étape 1. Choisir également un nouveau mot de passe PostgreSQL (chaîne aléatoire, 20+ caractères) et mettre à jour la ligne `DATABASE_URL=postgresql://postgres:<NOUVEAU_MDP>@localhost:5432/AH2`.

- [ ] **Step 3: Appliquer le nouveau mot de passe PostgreSQL**

```bash
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d postgres -c "ALTER USER postgres WITH PASSWORD '<NOUVEAU_MDP>';"
```

(remplacer `<NOUVEAU_MDP>` par la valeur choisie à l'étape 2 — utilise l'ancien mot de passe `Admin_2025` pour cette seule connexion, c'est la dernière fois qu'il sert).

- [ ] **Step 4: Vérifier la nouvelle connexion**

```bash
$env:PGPASSWORD='<NOUVEAU_MDP>'; & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d AH2 -c "SELECT 1;"
```

Doit retourner une ligne `1`. Si erreur d'authentification, refaire l'étape 3.

- [ ] **Step 5: Générer un nouveau mot de passe pour `admin_test` et l'appliquer**

```bash
python -c "
from passlib.context import CryptContext
import getpass
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
new_password = input('Nouveau mot de passe pour admin_test (ne sera pas affiche ensuite) : ')
print(pwd_context.hash(new_password))
"
```

Copier le hash affiché, puis :

```bash
$env:PGPASSWORD='<NOUVEAU_MDP>'; & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d AH2 -c "UPDATE users SET password_hash = '<HASH_COPIE>' WHERE username = 'admin_test';"
```

- [ ] **Step 6: Vérifier la connexion applicative avec le nouveau mot de passe**

Ce test se fait après la Tâche 4 (backend démarré) — noter cette étape et y revenir : `POST /auth/login` avec `admin_test` / nouveau mot de passe doit retourner un token.

- [ ] **Step 7: Confirmer que `.env` n'est pas suivi**

```bash
git status --porcelain .env
```

Doit retourner **aucune ligne** (fichier ignoré). Si une ligne apparaît, ne pas continuer — le `.gitignore` a un problème à corriger avant de poursuivre.

---

## Task 2: Purge de `.env` de l'historique Git

**Files:**
- N/A (opération Git, pas de fichier de code)

**Interfaces:**
- Consumes: rien
- Produces: historique Git réécrit sur `origin`, sans aucune trace de `.env`. Les tâches suivantes (code) ne dépendent pas de celle-ci — elle peut être faite en parallèle, mais est placée tôt pour limiter la fenêtre d'exposition.

- [ ] **Step 1: Sauvegarde miroir locale (hors du dossier de travail)**

```bash
git clone --mirror . "C:\Users\DD\Desktop\ah2-backup-avant-purge.git"
```

- [ ] **Step 2: Mettre de côté le travail en cours (89 modifiés + 9 non suivis)**

```bash
git stash push -u -m "chantier-0-avant-purge-historique"
git status --porcelain
```

La deuxième commande doit retourner **aucune ligne** — arbre de travail propre, condition requise par `git filter-repo`.

- [ ] **Step 3: Installer `git-filter-repo`**

```bash
pip install git-filter-repo
```

- [ ] **Step 4: Purger `.env` de tout l'historique, toutes branches**

```bash
git filter-repo --path .env --invert-paths --force
```

(`--force` est nécessaire car ce n'est pas un clone fraîchement cloné pour le seul usage de filter-repo — c'est attendu et sûr ici, la sauvegarde miroir de l'étape 1 couvre le risque.)

- [ ] **Step 5: Vérifier que `.env` a disparu de l'historique**

```bash
git log --all --oneline -- .env
```

Doit retourner **aucune ligne**.

- [ ] **Step 6: Reconfigurer le remote (filter-repo le retire par sécurité)**

```bash
git remote add origin https://github.com/FranckDD/AH.git
```

- [ ] **Step 7: Forcer la mise à jour d'origin sur les 4 branches**

```bash
git push --force origin AH2_V2 AH2_V3-1 dash_Ah2 master
```

- [ ] **Step 8: Restaurer le travail en cours**

```bash
git stash pop
git status --porcelain
```

Doit à nouveau afficher les 89 fichiers modifiés + 9 non suivis d'origine, appliqués sur l'historique réécrit.

- [ ] **Step 9: Commit**

Rien à committer à cette étape (opération d'historique pure, pas de nouveau fichier de code). Passer à la tâche suivante.

---

## Task 3: Retirer les fichiers suivis à tort du suivi Git

**Files:**
- Modify: `.gitignore` (racine)
- Untrack: `offline.db`, `onehandhumanity.sqlite`, `auth.log`, tous les `*.pyc` suivis, `view/`, `view_pyqt6/`, `build/`, `dist/`, `htmlcov/`

**Interfaces:**
- Consumes: arbre de travail propre après la Tâche 2 (mais peut aussi s'exécuter avant/après indépendamment — pas de dépendance stricte de code)
- Produces: dépôt allégé, futurs commits n'incluent plus ces chemins

- [ ] **Step 1: Untrack les fichiers binaires et logs**

```bash
git rm --cached offline.db onehandhumanity.sqlite auth.log
git rm --cached $(git ls-files '*.pyc')
```

- [ ] **Step 2: Untrack les répertoires déjà dans `.gitignore` mais suivis**

```bash
git rm -r --cached view view_pyqt6 build dist htmlcov
```

- [ ] **Step 3: Vérifier qu'aucun de ces chemins n'est plus suivi**

```bash
git ls-files | grep -E "^(offline\.db|onehandhumanity\.sqlite|auth\.log|view/|view_pyqt6/|build/|dist/|htmlcov/)|\.pyc$"
```

Doit retourner **aucune ligne**.

- [ ] **Step 4: Commit**

```bash
git add -A -- offline.db onehandhumanity.sqlite auth.log view view_pyqt6 build dist htmlcov "*.pyc"
git commit -m "chore: retirer du suivi git les fichiers deja ignores (SEC-10)

offline.db, onehandhumanity.sqlite, auth.log, les .pyc et les
repertoires view/, view_pyqt6/, build/, dist/, htmlcov/ etaient
suivis malgre leur presence dans .gitignore (suivis avant son ajout).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Protéger `POST /config/structure` (SEC-02)

**Files:**
- Modify: `api_backend/backend_app/routes/admin/config_endpoints.py:63`
- Test: manuel (voir Step 4)

**Interfaces:**
- Consumes: `role_required` importé depuis `api_backend.backend_app.routes.auth.auth_endpoints` (déjà utilisé ailleurs dans le projet, ex. `api_backend/backend_app/routes/admin/users_endpoint.py:12`)
- Produces: rien consommé par une tâche suivante

- [ ] **Step 1: Ajouter l'import**

Dans `api_backend/backend_app/routes/admin/config_endpoints.py`, après la ligne `from models.organization_config import OrganizationConfig` (ligne 6), ajouter :

```python
from api_backend.backend_app.routes.auth.auth_endpoints import role_required
```

- [ ] **Step 2: Protéger uniquement la route POST**

Remplacer :

```python
@router.post("/structure", response_model=Any)
async def update_structure_info(
```

par :

```python
@router.post("/structure", response_model=Any, dependencies=[Depends(role_required("admin"))])
async def update_structure_info(
```

Ne pas toucher au décorateur de `get_structure_info` (`GET /structure` reste public — décision explicite).

- [ ] **Step 3: Démarrer l'API et vérifier manuellement**

```bash
cd "c:/Users/DD/Desktop/Project Stage/ah2_v2/AH2"
uvicorn api_backend.backend_app.main:app --reload
```

Dans un autre terminal :

```bash
curl -X POST http://127.0.0.1:8000/config/structure -F "name=Test"
```

Attendu : `401 Unauthorized` (pas de token).

```bash
curl http://127.0.0.1:8000/config/structure
```

Attendu : `200 OK` (GET toujours public).

- [ ] **Step 4: Commit**

```bash
git add api_backend/backend_app/routes/admin/config_endpoints.py
git commit -m "fix(security): proteger POST /config/structure (SEC-02)

Seul POST exige desormais le role admin. GET reste public par
decision explicite (affichage de la marque sur l'ecran de connexion).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Assainir l'upload de logo (SEC-03)

**Files:**
- Modify: `controller/config_controller.py`
- Test: `tests/test_config_controller.py` (nouveau)

**Interfaces:**
- Consumes: `PIL.Image` (Pillow, déjà en dépendance — `requirements.txt`)
- Produces: fonction `_generate_safe_filename(original_filename: str) -> str` et `_validate_image_content(file_obj) -> None` (lève `ValueError` si invalide), utilisées uniquement dans ce fichier

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_config_controller.py` :

```python
# tests/test_config_controller.py
import sys
import os
import io
import pytest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from controller.config_controller import _generate_safe_filename, _validate_image_content


def test_generate_safe_filename_strips_path_traversal():
    result = _generate_safe_filename("../../etc/passwd.png")
    assert "/" not in result
    assert ".." not in result
    assert result.endswith(".png")


def test_generate_safe_filename_rejects_disallowed_extension():
    with pytest.raises(ValueError):
        _generate_safe_filename("script.svg")


def test_generate_safe_filename_rejects_double_extension_trick():
    with pytest.raises(ValueError):
        _generate_safe_filename("logo.png.exe")


def test_validate_image_content_accepts_real_png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="PNG")
    buf.seek(0)
    _validate_image_content(buf)  # ne doit pas lever


def test_validate_image_content_rejects_non_image_bytes():
    buf = io.BytesIO(b"ceci n'est pas une image")
    with pytest.raises(ValueError):
        _validate_image_content(buf)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_config_controller.py -v
```

Attendu : `ImportError` ou `ModuleNotFoundError` — `_generate_safe_filename` et `_validate_image_content` n'existent pas encore.

- [ ] **Step 3: Réécrire `controller/config_controller.py`**

Remplacer tout le contenu du fichier par :

```python
import os
import shutil
import uuid
from fastapi import UploadFile
from PIL import Image
from repositories.config_repo import ConfigRepository
from models.organization_config import OrganizationConfig

UPLOAD_DIR = "static/uploads/logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 Mo


def _generate_safe_filename(original_filename: str) -> str:
    """Genere un nom de fichier aleatoire a partir d'une extension validee.
    Le nom fourni par le client n'est jamais reutilise tel quel (SEC-03)."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension de fichier non autorisee : {ext or '(aucune)'}")
    return f"{uuid.uuid4().hex}.{ext}"


def _validate_image_content(file_obj) -> None:
    """Verifie que le contenu est reellement une image, pas seulement l'extension."""
    try:
        position = file_obj.tell()
    except (AttributeError, OSError):
        position = None
    try:
        Image.open(file_obj).verify()
    except Exception as e:
        raise ValueError(f"Le fichier envoye n'est pas une image valide : {e}")
    finally:
        if position is not None:
            file_obj.seek(position)


class ConfigController:
    def __init__(self, repo: ConfigRepository):
        self.repo = repo

    def get_structure_info(self) -> OrganizationConfig:
        config = self.repo.get_config()
        if not config:
            return OrganizationConfig()
        return config

    def update_structure_info(
        self,
        data_dict: dict,
        logo_file: UploadFile = None,  # type: ignore
        base_url: str = ""
    ) -> OrganizationConfig:

        if logo_file:
            raw_bytes = logo_file.file.read()
            if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
                raise ValueError("Le fichier depasse la taille maximale autorisee (5 Mo)")

            import io
            buffer = io.BytesIO(raw_bytes)
            _validate_image_content(buffer)

            filename = _generate_safe_filename(logo_file.filename or "")
            file_path = os.path.join(UPLOAD_DIR, filename)

            buffer.seek(0)
            with open(file_path, "wb") as out:
                shutil.copyfileobj(buffer, out)

            data_dict["logo_url"] = f"{base_url}/static/uploads/logos/{filename}"

        return self.repo.save_config(data_dict)
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_config_controller.py -v
```

Attendu : 5 tests `PASS`.

- [ ] **Step 5: Test manuel bout-en-bout**

Avec l'API démarrée (Task 4, Step 3) et un token admin valide :

```bash
curl -X POST http://127.0.0.1:8000/config/structure \
  -H "Authorization: Bearer <TOKEN>" \
  -F "name=Test Hopital" \
  -F "logo=@chemin/vers/une/vraie/image.png"
```

Vérifier dans la réponse que `logo_url` contient un nom généré (UUID), pas `logo_<nom original>`.

- [ ] **Step 6: Commit**

```bash
git add controller/config_controller.py tests/test_config_controller.py
git commit -m "fix(security): assainir l'upload de logo (SEC-03)

Nom de fichier regenere cote serveur (uuid4), liste blanche
d'extensions, et validation du contenu reel via Pillow au lieu de
faire confiance a l'extension ou au Content-Type declare.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Retirer les identifiants en dur (SEC-04)

**Files:**
- Modify: `README.md`
- Modify: `controller/auth_controller.py:38-42`
- Modify: `main.py:9-16` (racine)
- Modify: `controller/controller_offline/auth_controller_factory.py:27-29`
- Modify: `import_medical_specialities.py:15,62-67`
- Modify: `migrations/import_users_pg_to_sqlite.py:15-19`

**Interfaces:**
- Consumes: `DATABASE_URL` déjà importé depuis `api_backend.backend_app.config` dans `auth_controller.py`
- Produces: rien consommé par une tâche suivante

- [ ] **Step 1: `README.md`**

Remplacer tout le contenu par :

```markdown
# AH2
git pour le projet de systeme de gestion hospitalier
```

- [ ] **Step 2: `controller/auth_controller.py`**

Remplacer :

```python
        if db_session:
            self.session = db_session
        else:
            db_url = DATABASE_URL or "postgresql://postgres:Admin_2025@localhost/AH2"
            self.db = DatabaseManager(db_url)
            self.session = self.db.get_session()
```

par :

```python
        if db_session:
            self.session = db_session
        else:
            if not DATABASE_URL:
                raise RuntimeError(
                    "DATABASE_URL doit etre defini (variable d'environnement ou .env) "
                    "pour instancier AuthController sans session existante."
                )
            self.db = DatabaseManager(DATABASE_URL)
            self.session = self.db.get_session()
```

- [ ] **Step 3: `main.py` (racine, point d'entrée du client Tkinter)**

Remplacer :

```python
from models.database import DatabaseManager
from view.auth_view import AuthView
from controller.auth_controller import AuthController
import sys
import models

from controller.controller_offline.auth_controller_factory import get_auth_controller
import sys

def main():
    # --- Récupère le controller selon la dispo du backend ---
    auth_controller, backend = get_auth_controller(
        mode="auto",  # auto = online si possible, offline sinon
        pg_conn_string="postgresql://postgres:Admin_2025@localhost/AH2",
        sqlite_path="offline.db"
    )
```

par :

```python
from models.database import DatabaseManager
from view.auth_view import AuthView
from controller.auth_controller import AuthController
import os
import sys
import models

from controller.controller_offline.auth_controller_factory import get_auth_controller

def main():
    pg_conn_string = os.environ.get("DATABASE_URL")
    if not pg_conn_string:
        print("Erreur: la variable d'environnement DATABASE_URL doit etre definie.", file=sys.stderr)
        sys.exit(1)

    # --- Récupère le controller selon la dispo du backend ---
    auth_controller, backend = get_auth_controller(
        mode="auto",  # auto = online si possible, offline sinon
        pg_conn_string=pg_conn_string,
        sqlite_path="offline.db"
    )
```

- [ ] **Step 4: `controller/controller_offline/auth_controller_factory.py`**

Remplacer :

```python
    # Définir une chaîne de connexion par défaut si aucune n'est fournie
    if pg_conn_string is None:
        pg_conn_string = os.environ.get("DATABASE_URL", "postgresql://postgres:Admin_2025@localhost/A")
        logger.info(f"Utilisation de la chaîne de connexion PostgreSQL: {pg_conn_string}")
```

par :

```python
    # Définir une chaîne de connexion par défaut si aucune n'est fournie
    if pg_conn_string is None:
        pg_conn_string = os.environ.get("DATABASE_URL")
        logger.info(
            "Chaine de connexion PostgreSQL: %s",
            "definie" if pg_conn_string else "absente - bascule offline attendue"
        )
```

(Aucune valeur par défaut codée en dur ; si `DATABASE_URL` est absent, `pg_conn_string` reste `None` et le mécanisme de bascule offline existant, plus bas dans la fonction, prend le relais — comportement déjà géré par le `try/except` autour de `get_user_repo_backend`.)

- [ ] **Step 5: `import_medical_specialities.py`**

Remplacer :

```python
DEFAULT_PG = "postgresql://postgres:Admin_2025@localhost/AH2"
DEFAULT_SQLITE = "sqlite:///offline.db"
```

par :

```python
import os

DEFAULT_PG = os.environ.get("DATABASE_URL")
DEFAULT_SQLITE = "sqlite:///offline.db"
```

Puis remplacer :

```python
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pg", default=DEFAULT_PG, help="Postgres connection string")
    p.add_argument("--sqlite", default=DEFAULT_SQLITE, help="SQLite connection string (SQLAlchemy style)")
    args = p.parse_args()
    main(args.pg, args.sqlite)
```

par :

```python
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pg", default=DEFAULT_PG, help="Postgres connection string (ou variable d'environnement DATABASE_URL)")
    p.add_argument("--sqlite", default=DEFAULT_SQLITE, help="SQLite connection string (SQLAlchemy style)")
    args = p.parse_args()
    if not args.pg:
        p.error("--pg est requis (ou definissez DATABASE_URL dans l'environnement)")
    main(args.pg, args.sqlite)
```

- [ ] **Step 6: `migrations/import_users_pg_to_sqlite.py`**

Remplacer :

```python
# Remplace par ta chaîne Postgres
PG_CONN = "postgresql://postgres:Admin_2025@localhost/AH2"

def import_users(pg_conn=PG_CONN, sqlite_path="offline.db"):
    # Postgres session
    pg_engine = create_engine(pg_conn)
```

par :

```python
import os

PG_CONN = os.environ.get("DATABASE_URL")

def import_users(pg_conn=PG_CONN, sqlite_path="offline.db"):
    if not pg_conn:
        raise RuntimeError(
            "DATABASE_URL doit etre defini dans l'environnement pour executer cette migration."
        )
    # Postgres session
    pg_engine = create_engine(pg_conn)
```

- [ ] **Step 7: Vérifier qu'aucun mot de passe en dur ne subsiste**

```bash
grep -rn "Admin_2025" --include="*.py" --include="*.md" .
```

Attendu : **aucune ligne** (hormis d'éventuels fichiers de sauvegarde ou dumps `.sql`, hors périmètre de ce chantier — vérifier que le résultat ne contient que des fichiers `.sql`/binaires, pas de `.py` ni `.md`).

- [ ] **Step 8: Commit**

```bash
git add README.md controller/auth_controller.py main.py controller/controller_offline/auth_controller_factory.py import_medical_specialities.py migrations/import_users_pg_to_sqlite.py
git commit -m "fix(security): retirer les identifiants postgres codes en dur (SEC-04)

Les 5 fallbacks vers postgresql://postgres:Admin_2025@localhost/AH2
sont remplaces par une lecture stricte de DATABASE_URL, avec echec
explicite plutot qu'un identifiant par defaut silencieux. Ligne
d'identifiants retiree du README.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Limitation de débit sur `/auth/login` (SEC-05)

**Files:**
- Create: `api_backend/backend_app/rate_limit.py`
- Modify: `api_backend/backend_app/main.py`
- Modify: `api_backend/backend_app/routes/auth/auth_endpoints.py`
- Modify: `requirements.txt`
- Test: `tests/test_rate_limit.py` (nouveau)

**Interfaces:**
- Consumes: rien
- Produces: objet `limiter` (instance `slowapi.Limiter`) exporté depuis `api_backend/backend_app/rate_limit.py`, importé à la fois par `main.py` (pour l'enregistrement global) et `auth_endpoints.py` (pour décorer la route de login) — évite l'import circulaire entre les deux.

- [ ] **Step 1: Ajouter `slowapi` aux dépendances**

Dans `requirements.txt`, ajouter une ligne (ordre alphabétique, après `six==1.17.0`) :

```
slowapi==0.1.9
```

Puis :

```bash
pip install slowapi==0.1.9
```

- [ ] **Step 2: Écrire le test qui échoue**

Créer `tests/test_rate_limit.py` :

```python
# tests/test_rate_limit.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.rate_limit import limiter


def test_limiter_is_configured_with_ip_key_func():
    from slowapi.util import get_remote_address
    assert limiter._key_func is get_remote_address


def test_limiter_has_no_default_limits():
    # Les limites sont appliquees par route via le decorateur, pas globalement
    assert limiter._default_limits == []
```

- [ ] **Step 3: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_rate_limit.py -v
```

Attendu : `ModuleNotFoundError: No module named 'api_backend.backend_app.rate_limit'`

- [ ] **Step 4: Créer `api_backend/backend_app/rate_limit.py`**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

- [ ] **Step 5: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_rate_limit.py -v
```

Attendu : 2 tests `PASS`.

- [ ] **Step 6: Enregistrer le limiteur dans `main.py`**

Ajouter après les imports existants (après la ligne `import json`) :

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .rate_limit import limiter
```

Ajouter juste après `app = FastAPI(title="AH2 API")` :

```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

- [ ] **Step 7: Décorer la route de login**

Dans `api_backend/backend_app/routes/auth/auth_endpoints.py`, ajouter l'import :

```python
from fastapi import Request
from ...rate_limit import limiter
```

Remplacer :

```python
@router.post("/auth/login", response_model=Token, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
```

par :

```python
@router.post("/auth/login", response_model=Token, tags=["Authentication"])
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
```

- [ ] **Step 8: Test manuel bout-en-bout**

Avec l'API démarrée :

```bash
for i in 1 2 3 4 5 6; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/auth/login -d "username=admin_test&password=mauvais_mdp"; done
```

Attendu : les 5 premières lignes affichent `401` (identifiants invalides, mais requête traitée), la 6e affiche `429` (limite atteinte).

- [ ] **Step 9: Commit**

```bash
git add api_backend/backend_app/rate_limit.py api_backend/backend_app/main.py api_backend/backend_app/routes/auth/auth_endpoints.py requirements.txt tests/test_rate_limit.py
git commit -m "fix(security): limiter le debit sur /auth/login (SEC-05)

5 tentatives par minute par adresse IP via slowapi, stockage en
memoire. Limite par IP seule (pas IP+utilisateur) car le key_func
de slowapi est synchrone et ne peut pas lire le corps de la requete
de maniere fiable sans plomberie supplementaire non verifiee.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: Restreindre la lecture de l'annuaire des comptes (SEC-07)

**Files:**
- Modify: `api_backend/backend_app/routes/admin/users_endpoint.py:71-102`

**Interfaces:**
- Consumes: `role_required` déjà importé (ligne 12 du fichier)
- Produces: rien consommé par une tâche suivante

- [ ] **Step 1: Protéger `list_users`**

Remplacer :

```python
@router.get("/", response_model=List[UserOut])
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    user_ctrl: UserController = Depends(get_user_controller),
):
```

par :

```python
@router.get("/", response_model=List[UserOut], dependencies=[Depends(role_required("admin", "manager"))])
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    user_ctrl: UserController = Depends(get_user_controller),
):
```

- [ ] **Step 2: Protéger `search_users`**

Remplacer :

```python
@router.get("/search", response_model=List[UserOut])
def search_users(q: str = Query(..., min_length=1), user_ctrl: UserController = Depends(get_user_controller)):
```

par :

```python
@router.get("/search", response_model=List[UserOut], dependencies=[Depends(role_required("admin", "manager"))])
def search_users(q: str = Query(..., min_length=1), user_ctrl: UserController = Depends(get_user_controller)):
```

- [ ] **Step 3: Protéger `get_user`**

Remplacer :

```python
@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, user_ctrl: UserController = Depends(get_user_controller)):
```

par :

```python
@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(role_required("admin", "manager"))])
def get_user(user_id: int, user_ctrl: UserController = Depends(get_user_controller)):
```

**Ne pas toucher** à `list_doctors` (ligne 88) : reste ouvert au personnel soignant connecté, besoin métier légitime.

- [ ] **Step 4: Test manuel**

Avec un token appartenant à `nurse_test` (rôle `nurse`, non-admin) :

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/users/ -H "Authorization: Bearer <TOKEN_NURSE>"
```

Attendu : `403`.

Avec un token `admin_test` :

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/users/ -H "Authorization: Bearer <TOKEN_ADMIN>"
```

Attendu : `200`.

- [ ] **Step 5: Commit**

```bash
git add api_backend/backend_app/routes/admin/users_endpoint.py
git commit -m "fix(security): restreindre la lecture de l'annuaire des comptes (SEC-07)

GET /users/, /users/search et /users/{id} exigent desormais un role
admin ou manager, aligne sur les mutations deja protegees.
/users/doctors reste ouvert au personnel soignant (besoin legitime).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 9: Ne plus journaliser les payloads de validation (SEC-08)

**Files:**
- Modify: `api_backend/backend_app/main.py`

**Interfaces:**
- Consumes: rien
- Produces: rien

- [ ] **Step 1: Retirer l'impression de la valeur reçue**

Remplacer :

```python
    for i, error in enumerate(error_details):
        loc = " -> ".join(str(l) for l in error['loc'])
        msg = error['msg']
        print(f"❌ Erreur #{i+1}:")
        print(f"   📍 Emplacement : {loc}")
        print(f"   ⚠️ Message     : {msg}")
        # Affiche la valeur reçue si disponible dans le contexte (dépend version Pydantic)
        if 'input' in error:
             print(f"   📥 Valeur reçue: {error['input']}")
```

par :

```python
    for i, error in enumerate(error_details):
        loc = " -> ".join(str(l) for l in error['loc'])
        msg = error['msg']
        print(f"❌ Erreur #{i+1}:")
        print(f"   📍 Emplacement : {loc}")
        print(f"   ⚠️ Message     : {msg}")
```

- [ ] **Step 2: Vérifier**

```bash
grep -n "Valeur reçue\|error\['input'\]" api_backend/backend_app/main.py
```

Attendu : **aucune ligne**.

- [ ] **Step 3: Commit**

```bash
git add api_backend/backend_app/main.py
git commit -m "fix(security): ne plus journaliser les payloads recus en erreur 422 (SEC-08)

Le handler de validation n'imprime plus la valeur soumise par le
client, qui pouvait contenir des donnees patient nominatives.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 10: Corrections front web (WEB-01, WEB-02, WEB-03)

**Files:**
- Rename: `ah2-admin-web/src/views/errors/forbidden.vue` → `ah2-admin-web/src/views/errors/Forbidden.vue`
- Modify: `ah2-admin-web/src/services/api.js`
- Modify: `ah2-admin-web/src/stores/auth.js`
- Modify: `ah2-admin-web/src/components/toxico/ToxicoPatientDetailsModal.vue:245`
- Create: `ah2-admin-web/.env.example`
- Modify: `ah2-admin-web/.gitignore`

**Interfaces:**
- Consumes: rien
- Produces: `API_URL` exporté depuis `services/api.js` (nommé export `API_URL`), consommé par `stores/auth.js`

- [ ] **Step 1: Renommer le fichier (casse)**

```bash
cd ah2-admin-web/src/views/errors
git mv forbidden.vue Forbidden.vue.tmp
git mv Forbidden.vue.tmp Forbidden.vue
cd -
```

(le double renommage est nécessaire sur un système de fichiers insensible à la casse pour que Git enregistre le changement de casse)

- [ ] **Step 2: Ajouter `.env` au `.gitignore` du front**

Dans `ah2-admin-web/.gitignore`, ajouter en fin de fichier :

```
.env
.env.local
```

- [ ] **Step 3: Créer `ah2-admin-web/.env.example`**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 4: Créer `ah2-admin-web/.env` (local, non suivi)**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 5: Centraliser `API_URL` dans `services/api.js`**

Remplacer :

```javascript
// URL de base de votre API FastAPI
const API_URL = 'http://localhost:8000'; 
```

par :

```javascript
// URL de base de votre API FastAPI
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

- [ ] **Step 6: Faire consommer `stores/auth.js` la même source et l'instance `api` partagée**

Remplacer :

```javascript
// src/stores/auth.js
import { defineStore } from 'pinia';
import axios from 'axios';
import router from '@/router'; // 🟢 1. Importer le router pour la redirection

const API_URL = 'http://localhost:8000';
```

par :

```javascript
// src/stores/auth.js
import { defineStore } from 'pinia';
import api from '@/services/api';
import router from '@/router'; // 🟢 1. Importer le router pour la redirection
```

Puis, dans l'action `login`, remplacer :

```javascript
        const response = await axios.post(`${API_URL}/auth/login`, formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });

        this.token = response.data.access_token;
        
        // 🟢 Stockage avec la clé 'token' (Doit être identique dans api.js)
        localStorage.setItem('token', this.token);

        const meResponse = await axios.get(`${API_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${this.token}` }
        });
```

par :

```javascript
        const response = await api.post('/auth/login', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });

        this.token = response.data.access_token;
        
        // 🟢 Stockage avec la clé 'token' (Doit être identique dans api.js)
        localStorage.setItem('token', this.token);

        const meResponse = await api.get('/auth/me', {
            headers: { Authorization: `Bearer ${this.token}` }
        });
```

(L'instance `api` injecte déjà le token via son intercepteur pour les requêtes suivantes ; le passage explicite du header sur `/auth/me` reste nécessaire ici car `this.token` vient tout juste d'être défini et n'est pas encore dans `localStorage` au moment de l'appel — l'intercepteur lit `localStorage`, pas `this.token`.)

- [ ] **Step 7: Corriger la 3e occurrence isolée**

Dans `ah2-admin-web/src/components/toxico/ToxicoPatientDetailsModal.vue`, remplacer :

```javascript
const API_BASE_URL = 'http://localhost:8000'; // À remplacer par import.meta.env.VITE_API_URL en prod
```

par :

```javascript
import { API_URL as API_BASE_URL } from '@/services/api';
```

(retirer cette ligne de son emplacement d'origine dans le `<script setup>` et l'ajouter avec les autres imports en tête de bloc `<script setup>`)

- [ ] **Step 8: Vérifier qu'aucune autre occurrence codée en dur ne subsiste**

```bash
grep -rn "localhost:8000" ah2-admin-web/src
```

Attendu : **aucune ligne**.

- [ ] **Step 9: Build de vérification**

```bash
cd ah2-admin-web
npm run build
cd -
```

Attendu : build réussi, aucune erreur de résolution de module sur `Forbidden.vue`.

- [ ] **Step 10: Commit**

```bash
git add ah2-admin-web/src/views/errors/Forbidden.vue ah2-admin-web/src/services/api.js ah2-admin-web/src/stores/auth.js ah2-admin-web/src/components/toxico/ToxicoPatientDetailsModal.vue ah2-admin-web/.env.example ah2-admin-web/.gitignore
git commit -m "fix(web): corriger la casse Forbidden.vue et centraliser API_URL (WEB-01, WEB-02, WEB-03)

- forbidden.vue renomme en Forbidden.vue (bloquait le build sur systeme sensible a la casse)
- API_URL n'a plus qu'une seule definition (services/api.js), lue depuis VITE_API_URL
- stores/auth.js utilise l'instance api partagee au lieu d'axios brut, ce qui le fait
  beneficier des intercepteurs de gestion des 401 (corrige WEB-03 au passage)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 11: Vérification finale de bout en bout

**Files:** aucun (vérification uniquement)

**Interfaces:**
- Consumes: résultat de toutes les tâches précédentes
- Produces: confirmation que le chantier est complet

- [ ] **Step 1: Lancer toute la suite de tests**

```bash
cd "c:/Users/DD/Desktop/Project Stage/ah2_v2/AH2"
pytest tests/ -v
```

Attendu : tous les tests passent (existants + les nouveaux des tâches 5 et 7).

- [ ] **Step 2: Revérifier Task 1, Step 6 (login avec le nouveau mot de passe admin_test)**

```bash
curl -X POST http://127.0.0.1:8000/auth/login -d "username=admin_test&password=<NOUVEAU_MDP_ADMIN_TEST>"
```

Attendu : `200` avec un `access_token`.

- [ ] **Step 3: Vérifier l'historique Git distant**

```bash
git clone https://github.com/FranckDD/AH.git /tmp-verif-clone 2>&1 | tail -5
git -C /tmp-verif-clone log --all --oneline -- .env
```

Attendu : **aucune ligne** — confirme que la purge a bien été poussée.

- [ ] **Step 4: Vérifier que le travail en cours (89 modifiés + 9 non suivis) est toujours présent**

```bash
git status --porcelain | wc -l
```

Attendu : `98` (ou proche — quelques fichiers ont pu être légitimement touchés par les tâches ci-dessus, comme `main.py`, `users_endpoint.py`, `router/index.js`-adjacent files ; vérifier qu'aucun fichier n'a disparu de la liste, seulement que certains ont été committés intentionnellement).

- [ ] **Step 5: Récapitulatif**

Confirmer un par un, en cochant :
- [ ] `SEC-01` — secrets rotés, historique purgé et poussé
- [ ] `SEC-02` — `POST /config/structure` protégé, `GET` public
- [ ] `SEC-03` — upload assaini (nom régénéré, extension validée, contenu vérifié)
- [ ] `SEC-04` — plus aucun identifiant en dur dans le code
- [ ] `SEC-05` — limitation de débit active sur `/auth/login`
- [ ] `SEC-07` — lecture de l'annuaire restreinte
- [ ] `SEC-08` — logs ne contiennent plus de payload patient
- [ ] `SEC-10` — fichiers indésirables retirés du suivi
- [ ] `WEB-01` — `Forbidden.vue` corrigé, build passe
- [ ] `WEB-02` / `WEB-03` — `API_URL` centralisé, `auth.js` utilise l'instance partagée
