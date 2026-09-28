# Imprimante thermique POS — ticket de caisse — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** À chaque facture caisse enregistrée (statut `active`), imprimer automatiquement un ticket thermique POS via un service pont local, y compris le bloc "réduction validée" quand une `DiscountRequest` approuvée existe pour la transaction.

**Architecture:** Le backend FastAPI construit le contenu structuré du ticket (JSON, en réutilisant `get_transaction_details_for_invoice()` déjà existant) via un nouvel endpoint `GET /caisse/{id}/ticket`. Un nouveau service Python autonome (`printer_bridge/`), qui tourne sur le poste secrétariat, reçoit ce JSON en HTTP local, le met en page en ESC/POS via `python-escpos`, et l'envoie à l'imprimante (connexion configurable : `Win32Raw` pour l'émulateur Windows en dev, `Usb` pour la vraie imprimante plus tard). Le frontend déclenche l'appel dans deux cas : juste après la création réussie d'une facture normale, et quand la secrétaire est notifiée qu'une facture en attente de réduction vient d'être décidée.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend, existant), Vue 3 + Pinia (frontend, existant), Python autonome + `python-escpos` + `pywin32` (nouveau service pont), pytest (`escpos.printer.Dummy` pour tester le rendu sans matériel).

**Spec:** `docs/superpowers/specs/2026-09-28-imprimante-pos-ticket-design.md`

## Global Constraints

- Aucune impression ne doit jamais bloquer ou faire échouer l'enregistrement d'une facture — toujours best-effort, échec = bandeau d'erreur, jamais une exception qui remonte au flux de création.
- Le jeton d'impression ne doit **jamais** apparaître dans la réponse de `GET /config/structure` (endpoint public, sans authentification, utilisé par l'écran de login) — il a son propre endpoint protégé.
- Pas de TVA, pas de "montant reçu/monnaie rendue", pas de QR/code-barres — hors périmètre explicite de la spec.
- Le bloc réduction sur le ticket ne doit apparaître QUE si le statut de la `DiscountRequest` liée est `approved` — jamais pour `pending`, `refused`, ou `cancelled`.
- Générer un ticket pour une transaction `pending_approval` doit être refusé (même garde que `generate_invoice_pdf`).
- Le service pont (`printer_bridge/`) est un projet Python autonome, séparé du backend FastAPI principal — pas de nouvelle dépendance ajoutée à `requirements-api.txt`.

## Review Focus

- Un ticket demandé pour une transaction `pending_approval` doit être refusé, jamais généré avec des montants provisoires — couvert par les tests de la Tâche 5.
- Une `DiscountRequest` `refused` ou encore `pending` sur la transaction ne doit jamais produire de bloc réduction sur le ticket — couvert par les tests de la Tâche 4 et 5.
- Le jeton d'impression ne doit jamais apparaître dans la réponse JSON de `GET /config/structure` — couvert par un test dédié dans la Tâche 3.
- Une désignation d'article trop longue pour la largeur papier (80mm ≈ 42 caractères en police normale) ne doit jamais faire planter le rendu ni déborder de façon illisible — couvert par un test avec un nom d'article volontairement long dans la Tâche 12.
- Le pont local injoignable (mauvais port, service pas démarré) ne doit jamais faire planter l'écran caisse ni empêcher la facture de rester enregistrée — couvert par un test frontend dans la Tâche 9.

---

## Task 1 : Migration — colonnes `ticket_logo_url` et `ticket_print_token`

**Files:**
- Create: `alembic/versions/014_ticket_logo_token.py`
- Modify: `models/organization_config.py`

**Interfaces:**
- Produces: `OrganizationConfig.ticket_logo_url` (str, nullable), `OrganizationConfig.ticket_print_token` (str, nullable) — consommés par les Tâches 2 et 3.

- [ ] **Step 1: Écrire la migration**

```python
# alembic/versions/014_ticket_logo_token.py
"""organization_config ticket_logo_url + ticket_print_token

Revision ID: 014_ticket_logo_token
Revises: 013_notif_discount
Create Date: 2026-09-28

"""
from alembic import op

revision = '014_ticket_logo_token'
down_revision = '013_notif_discount'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.organization_config
            ADD COLUMN IF NOT EXISTS ticket_logo_url varchar,
            ADD COLUMN IF NOT EXISTS ticket_print_token varchar;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.organization_config
            DROP COLUMN IF EXISTS ticket_print_token,
            DROP COLUMN IF EXISTS ticket_logo_url;
    """)
```

- [ ] **Step 2: Ajouter les colonnes au modèle SQLAlchemy**

Dans `models/organization_config.py`, après la ligne `logo_url = Column(String, nullable=True) # Chemin relatif ou URL complète` :

```python
    ticket_logo_url = Column(String, nullable=True)  # Logo monochrome dedie au ticket thermique, distinct du logo couleur
    ticket_print_token = Column(String, nullable=True)  # Jeton partage requis par le service pont local (jamais expose via GET /config/structure)
```

- [ ] **Step 3: Appliquer la migration en base réelle**

Run: `alembic upgrade head`
Expected: pas d'erreur, `ticket_logo_url`/`ticket_print_token` visibles dans `\d organization_config` via psql.

- [ ] **Step 4: Régénérer `ci/schema_only.sql`**

Suivre la procédure déjà établie sur ce projet (dump + diff-check avant d'écraser) : régénérer le fichier et vérifier que le diff ne contient QUE les 2 nouvelles colonnes.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/014_ticket_logo_token.py models/organization_config.py ci/schema_only.sql
git commit -m "feat: add ticket_logo_url and ticket_print_token to organization_config"
```

---

## Task 2 : Backend — helper partagé de résolution de logo + contexte ticket

**Files:**
- Modify: `api_backend/backend_app/utils/pdf_header.py`
- Test: `tests/test_pdf_header.py` (nouveau fichier)

**Interfaces:**
- Consumes: `OrganizationConfig` (Task 1, champ `ticket_logo_url`).
- Produces: `resolve_local_asset_path(url: Optional[str]) -> Optional[Path]`, `get_ticket_header_context(config_ctrl) -> dict` avec clés `structure`, `ticket_logo_path` (str ou None, chemin fichier plat, PAS un `file://` URI) — consommé par la Tâche 5.

- [ ] **Step 1: Écrire le test de la fonction partagée**

```python
# tests/test_pdf_header.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock
from api_backend.backend_app.utils.pdf_header import resolve_local_asset_path, get_ticket_header_context


def test_resolve_local_asset_path_returns_none_for_empty_url():
    assert resolve_local_asset_path(None) is None
    assert resolve_local_asset_path("") is None


def test_resolve_local_asset_path_returns_none_for_missing_file():
    assert resolve_local_asset_path("/static/uploads/logos/does-not-exist.png") is None


def test_resolve_local_asset_path_resolves_existing_relative_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("static/uploads/logos", exist_ok=True)
    with open("static/uploads/logos/real.png", "wb") as f:
        f.write(b"fake-png-bytes")
    result = resolve_local_asset_path("/static/uploads/logos/real.png")
    assert result is not None
    assert result.name == "real.png"


def test_get_ticket_header_context_no_logo_when_field_empty():
    structure = MagicMock(ticket_logo_url=None)
    config_ctrl = MagicMock()
    config_ctrl.get_structure_info.return_value = structure
    ctx = get_ticket_header_context(config_ctrl)
    assert ctx["structure"] is structure
    assert ctx["ticket_logo_path"] is None
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python -m pytest tests/test_pdf_header.py -v`
Expected: FAIL (`ImportError: cannot import name 'resolve_local_asset_path'`)

- [ ] **Step 3: Refactoriser `pdf_header.py` — extraire le helper partagé et ajouter `get_ticket_header_context`**

```python
# api_backend/backend_app/utils/pdf_header.py
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def resolve_local_asset_path(url: Optional[str]) -> Optional[Path]:
    """Resout un champ *_url (relatif type /static/... ou absolu legacy) en
    chemin fichier local reel. Retourne None si le champ est vide ou si le
    fichier n'existe pas sur disque - jamais d'exception, un logo manquant
    ne doit jamais faire echouer la generation d'un document."""
    if not url:
        return None
    relative_path = urlparse(url).path
    local_path = Path(relative_path.lstrip("/")).resolve()
    return local_path if local_path.is_file() else None


def get_pdf_header_context(config_ctrl: Any) -> Dict[str, Any]:
    """
    Resout une seule fois les infos d'etablissement (nom, adresse, logo)
    pour tout generateur PDF de ce projet - source unique, evite la
    derive deja constatee (facture caisse ignorait completement
    OrganizationConfig avant ce chantier, nom/logo codes en dur).
    """
    structure = config_ctrl.get_structure_info()
    local_logo = resolve_local_asset_path(structure.logo_url) if structure else None
    return {"structure": structure, "logo_path": local_logo.as_uri() if local_logo else None}


def get_ticket_header_context(config_ctrl: Any) -> Dict[str, Any]:
    """Meme resolution que get_pdf_header_context, mais pour le logo
    monochrome dedie au ticket thermique (ticket_logo_url) - fichier
    distinct du logo couleur, deja optimise pour un rendu bitmap ESC/POS.
    ticket_logo_path est un chemin plat (pas un file:// URI comme
    logo_path) : python-escpos.printer.image() attend un chemin fichier
    normal ou une image PIL, jamais une URI."""
    structure = config_ctrl.get_structure_info()
    ticket_logo_url = getattr(structure, "ticket_logo_url", None) if structure else None
    local_logo = resolve_local_asset_path(ticket_logo_url)
    return {"structure": structure, "ticket_logo_path": str(local_logo) if local_logo else None}
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `python -m pytest tests/test_pdf_header.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Vérifier l'absence de régression sur les exports existants**

Run: `python -m pytest tests/ -k "pdf or export or invoice or labo" -q`
Expected: mêmes résultats qu'avant (aucun nouveau FAILED) — `get_pdf_header_context` garde exactement le même comportement, seule son implémentation interne a changé.

- [ ] **Step 6: Commit**

```bash
git add api_backend/backend_app/utils/pdf_header.py tests/test_pdf_header.py
git commit -m "refactor: extract resolve_local_asset_path, add get_ticket_header_context"
```

---

## Task 3 : Backend — upload du logo ticket + endpoint dédié pour le jeton d'impression

**Files:**
- Modify: `controller/config_controller.py`
- Modify: `api_backend/backend_app/routes/admin/config_endpoints.py`
- Test: `tests/test_config_controller.py`
- Test: `tests/test_config_endpoints.py` (nouveau fichier)

**Interfaces:**
- Consumes: `_generate_safe_filename`, `_validate_image_content`, `MAX_UPLOAD_SIZE_BYTES` (déjà existants dans `config_controller.py`).
- Produces: `ConfigController._save_uploaded_image(file, upload_dir) -> str` (chemin relatif) ; `ConfigController.generate_ticket_print_token() -> str` ; endpoints `GET /config/ticket-print-token` (role `secretaire`/`admin`/`promoteur`) et `POST /config/generate-ticket-token` (role `admin`) — consommés par la Tâche 6 (frontend).

- [ ] **Step 1: Écrire le test du helper d'upload extrait**

```python
# tests/test_config_controller.py (ajout en fin de fichier)

def test_save_uploaded_image_rejects_oversized_file(tmp_path, monkeypatch):
    from controller.config_controller import ConfigController, MAX_UPLOAD_SIZE_BYTES
    import io

    class FakeUploadFile:
        filename = "big.png"
        def __init__(self, data):
            self.file = io.BytesIO(data)

    monkeypatch.chdir(tmp_path)
    ctrl = ConfigController(repo=None)
    oversized = FakeUploadFile(b"0" * (MAX_UPLOAD_SIZE_BYTES + 1))
    with pytest.raises(ValueError, match="taille maximale"):
        ctrl._save_uploaded_image(oversized, "static/uploads/ticket_logos")


def test_generate_ticket_print_token_returns_url_safe_random_string():
    from controller.config_controller import ConfigController
    ctrl = ConfigController(repo=None)
    token = ctrl.generate_ticket_print_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    # genere deux fois -> jamais le meme jeton (evite un token constant par accident)
    assert token != ctrl.generate_ticket_print_token()
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python -m pytest tests/test_config_controller.py -k "uploaded_image or ticket_print_token" -v`
Expected: FAIL (`AttributeError: 'ConfigController' object has no attribute '_save_uploaded_image'`)

- [ ] **Step 3: Extraire le helper d'upload et ajouter la génération de jeton dans `config_controller.py`**

Remplacer le corps de `update_structure_info` pour réutiliser un helper, et ajouter deux méthodes. Le fichier devient :

```python
import io
import os
import secrets
import shutil
import uuid
from fastapi import UploadFile
from PIL import Image
from repositories.config_repo import ConfigRepository
from models.organization_config import OrganizationConfig

UPLOAD_DIR = "static/uploads/logos"
TICKET_LOGO_UPLOAD_DIR = "static/uploads/ticket_logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TICKET_LOGO_UPLOAD_DIR, exist_ok=True)

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

    def _save_uploaded_image(self, image_file: UploadFile, upload_dir: str) -> str:
        """Valide et sauvegarde une image uploadee, retourne son chemin
        relatif servi par /static. Factorise entre le logo couleur (factures
        PDF) et le logo monochrome (ticket thermique) - meme validation,
        seul le repertoire de destination change."""
        raw_bytes = image_file.file.read()
        if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError("Le fichier depasse la taille maximale autorisee (5 Mo)")

        buffer = io.BytesIO(raw_bytes)
        _validate_image_content(buffer)

        filename = _generate_safe_filename(image_file.filename or "")
        file_path = os.path.join(upload_dir, filename)

        buffer.seek(0)
        with open(file_path, "wb") as out:
            shutil.copyfileobj(buffer, out)

        return f"/{upload_dir}/{filename}"

    def update_structure_info(
        self,
        data_dict: dict,
        logo_file: UploadFile = None,  # type: ignore
        ticket_logo_file: UploadFile = None,  # type: ignore
    ) -> OrganizationConfig:
        if logo_file:
            data_dict["logo_url"] = self._save_uploaded_image(logo_file, UPLOAD_DIR)
        if ticket_logo_file:
            data_dict["ticket_logo_url"] = self._save_uploaded_image(ticket_logo_file, TICKET_LOGO_UPLOAD_DIR)
        return self.repo.save_config(data_dict)

    def get_ticket_print_token(self) -> str | None:
        config = self.get_structure_info()
        return getattr(config, "ticket_print_token", None)

    def generate_ticket_print_token(self) -> str:
        """Genere un nouveau jeton partage (32 octets urlsafe -> 43
        caracteres) requis par le service pont local pour accepter une
        demande d'impression - empeche un site tiers ouvert dans un autre
        onglet du meme navigateur d'imprimer silencieusement sur
        http://localhost:PORT."""
        token = secrets.token_urlsafe(32)
        if self.repo:
            self.repo.save_config({"ticket_print_token": token})
        return token
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `python -m pytest tests/test_config_controller.py -v`
Expected: PASS (tous les tests existants + les 2 nouveaux)

- [ ] **Step 5: Écrire le test backend confirmant que le jeton ne fuite jamais sur l'endpoint public**

```python
# tests/test_config_endpoints.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.admin import config_endpoints
from api_backend.backend_app.routes.auth import auth_endpoints
from conftest import create_test_user, auth_headers

TEST_PASSWORD = "TestPass123!"


def test_structure_endpoint_never_exposes_ticket_print_token(api_client, db_session):
    """GET /config/structure est PUBLIC (aucune authentification, utilise
    par l'ecran de login) - le jeton d'impression ne doit donc jamais s'y
    trouver, meme s'il est deja renseigne en base."""
    from repositories.config_repo import ConfigRepository
    repo = ConfigRepository(db_session)
    repo.save_config({"name": "Clinique Test", "ticket_print_token": "SECRET_NE_DOIT_JAMAIS_FUITER"})

    client = api_client(config_endpoints)
    r = client.get("/config/structure")
    assert r.status_code == 200
    assert "ticket_print_token" not in r.json()
    assert "SECRET_NE_DOIT_JAMAIS_FUITER" not in str(r.json())


def test_ticket_print_token_endpoint_requires_auth(api_client, db_session):
    client = api_client(config_endpoints)
    r = client.get("/config/ticket-print-token")
    assert r.status_code == 401


def test_ticket_print_token_endpoint_forbidden_for_medecin(api_client, db_session):
    client = api_client(auth_endpoints, config_endpoints)
    create_test_user(db_session, "cfg_medecin1", "medecin", password=TEST_PASSWORD)
    headers = auth_headers(client, "cfg_medecin1", TEST_PASSWORD)
    r = client.get("/config/ticket-print-token", headers=headers)
    assert r.status_code == 403


def test_generate_ticket_token_endpoint_admin_only(api_client, db_session):
    client = api_client(auth_endpoints, config_endpoints)
    create_test_user(db_session, "cfg_secretaire1", "secretaire", password=TEST_PASSWORD)
    headers = auth_headers(client, "cfg_secretaire1", TEST_PASSWORD)
    r = client.post("/config/generate-ticket-token", headers=headers)
    assert r.status_code == 403


def test_generate_then_fetch_ticket_token_roundtrip(api_client, db_session):
    client = api_client(auth_endpoints, config_endpoints)
    create_test_user(db_session, "cfg_admin1", "admin", password=TEST_PASSWORD)
    headers = auth_headers(client, "cfg_admin1", TEST_PASSWORD)

    r = client.post("/config/generate-ticket-token", headers=headers)
    assert r.status_code == 200
    token = r.json()["token"]
    assert len(token) >= 32

    r = client.get("/config/ticket-print-token", headers=headers)
    assert r.status_code == 200
    assert r.json()["token"] == token
```

- [ ] **Step 6: Lancer les tests pour vérifier qu'ils échouent**

Run: `python -m pytest tests/test_config_endpoints.py -v`
Expected: FAIL (404, la route `/config/ticket-print-token` n'existe pas encore)

- [ ] **Step 7: Ajouter les routes et étendre `update_structure_info` dans `config_endpoints.py`**

```python
# api_backend/backend_app/routes/admin/config_endpoints.py (ajouts)
```

Modifier la signature de `update_structure_info` pour ajouter le paramètre optionnel :

```python
    ticket_logo: Optional[UploadFile] = File(None),
    ctrl: ConfigController = Depends(get_config_controller)
):
    ...
    try:
        updated_config = ctrl.update_structure_info(
            data_dict=data,
            logo_file=logo,  # type: ignore
            ticket_logo_file=ticket_logo,  # type: ignore
        )
```

Et ajouter en fin de fichier `normalize_config_data` la clé `ticket_logo_url` (JAMAIS `ticket_print_token`) :

```python
        "legal_info": config.legal_info,
        "ticket_logo_url": config.ticket_logo_url,
    }
```

Puis ajouter les 2 nouvelles routes après `update_structure_info` :

```python
@router.get("/ticket-print-token", dependencies=[Depends(role_required("secretaire", "admin", "promoteur"))])
def get_ticket_print_token(ctrl: ConfigController = Depends(get_config_controller)):
    """Endpoint dedie, distinct de GET /structure (public) - c'est ici et
    UNIQUEMENT ici que le jeton d'impression est expose, aux seuls roles qui
    declenchent une impression."""
    return {"token": ctrl.get_ticket_print_token()}


@router.post("/generate-ticket-token", dependencies=[Depends(role_required("admin"))])
def generate_ticket_print_token(ctrl: ConfigController = Depends(get_config_controller)):
    return {"token": ctrl.generate_ticket_print_token()}
```

- [ ] **Step 8: Lancer les tests pour vérifier qu'ils passent**

Run: `python -m pytest tests/test_config_endpoints.py tests/test_config_controller.py -v`
Expected: PASS (tous)

- [ ] **Step 9: Suite complète pour vérifier l'absence de régression**

Run: `python -m pytest tests/ -q`
Expected: mêmes échecs pré-existants qu'avant cette tâche (aucun nouveau FAILED)

- [ ] **Step 10: Commit**

```bash
git add controller/config_controller.py api_backend/backend_app/routes/admin/config_endpoints.py tests/test_config_controller.py tests/test_config_endpoints.py
git commit -m "feat: ticket logo upload + dedicated ticket-print-token endpoint"
```

---

## Task 4 : Backend — `DiscountRequestRepository.get_approved_for_transaction()`

**Files:**
- Modify: `repositories/discount_request_repo.py`
- Test: `tests/test_discount_requests.py`

**Interfaces:**
- Produces: `DiscountRequestRepository.get_approved_for_transaction(transaction_id: int) -> Optional[DiscountRequest]` (charge `.decider` en eager) — consommé par la Tâche 5.

- [ ] **Step 1: Écrire le test**

```python
# tests/test_discount_requests.py (ajout en fin de fichier)

def test_get_approved_for_transaction_returns_none_when_no_decision(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    repo = DiscountRequestRepository(db_session)
    assert repo.get_approved_for_transaction(req.transaction_id) is None


def test_get_approved_for_transaction_returns_none_when_refused(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=True)

    repo = DiscountRequestRepository(db_session)
    assert repo.get_approved_for_transaction(req.transaction_id) is None


def test_get_approved_for_transaction_returns_decision_with_decider_name(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=20)

    repo = DiscountRequestRepository(db_session)
    approved = repo.get_approved_for_transaction(req.transaction_id)
    assert approved is not None
    assert approved.decision_percent == 20
    assert approved.decider is not None
    assert approved.decider.user_id == manager_user.user_id
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python -m pytest tests/test_discount_requests.py -k get_approved_for_transaction -v`
Expected: FAIL (`AttributeError: 'DiscountRequestRepository' object has no attribute 'get_approved_for_transaction'`)

- [ ] **Step 3: Implémenter la méthode**

Dans `repositories/discount_request_repo.py`, après `get_pending_for_transaction` :

```python
    def get_approved_for_transaction(self, transaction_id: int) -> Optional[DiscountRequest]:
        """Au plus une demande approuvee par transaction en pratique (le
        workflow ne permet pas de re-demander sur une facture deja active),
        mais order_by+first() reste defensif si ce jour cette hypothese
        change un jour."""
        return (
            self.session.query(DiscountRequest)
            .options(joinedload(DiscountRequest.decider))
            .filter(DiscountRequest.transaction_id == transaction_id, DiscountRequest.status == "approved")
            .order_by(DiscountRequest.decided_at.desc())
            .first()
        )
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `python -m pytest tests/test_discount_requests.py -v`
Expected: PASS (tous, y compris les 3 nouveaux)

- [ ] **Step 5: Commit**

```bash
git add repositories/discount_request_repo.py tests/test_discount_requests.py
git commit -m "feat: add DiscountRequestRepository.get_approved_for_transaction"
```

---

## Task 5 : Backend — `CaisseController.build_ticket_data()` + `GET /caisse/{id}/ticket`

**Files:**
- Modify: `controller/caisse_controller.py`
- Modify: `api_backend/backend_app/routes/caisse/caisse_endpoints.py`
- Test: `tests/test_discount_requests.py`
- Test: `tests/test_caisse.py`

**Interfaces:**
- Consumes: `CaisseRepository.get_transaction_details_for_invoice()` (existant), `DiscountRequestRepository.get_approved_for_transaction()` (Task 4), `get_ticket_header_context()` (Task 2).
- Produces: `CaisseController.build_ticket_data(transaction_id: int) -> dict` avec clés `transaction_id`, `patient_name`, `user_name`, `amount`, `advance_amount`, `remaining`, `payment_method`, `paid_at`, `items` (liste de `{item_name, quantity, unit_price, line_total}`), `discount` (`None` ou `{decision_percent, decided_by_name}`), `header` (`{structure_name, address, phone, niu, rccm, legal_info, ticket_logo_path}`). Endpoint JSON `GET /caisse/{transaction_id}/ticket` — consommé par la Tâche 9 (frontend).

- [ ] **Step 1: Écrire les tests du controller**

```python
# tests/test_discount_requests.py (ajout en fin de fichier)

def test_build_ticket_data_blocked_when_pending_approval():
    ctrl, repo = _make_controller_with_pending_tx()
    ctrl.discount_repo = MagicMock()
    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.build_ticket_data(1)


def test_build_ticket_data_includes_discount_block_when_approved(db_session, secretaire_user, manager_user, caisse_repo_factory):
    from controller.caisse_controller import CaisseController
    from repositories.audit_repo import AuditRepository

    req, discount_ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    discount_ctrl.user = manager_user
    discount_ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=20)

    caisse_repo = caisse_repo_factory()
    caisse_ctrl = CaisseController(repo=caisse_repo, current_user=manager_user, discount_repo=DiscountRequestRepository(db_session))
    ticket = caisse_ctrl.build_ticket_data(req.transaction_id)

    assert ticket["discount"] is not None
    assert ticket["discount"]["decision_percent"] == 20
    assert ticket["discount"]["decided_by_name"]


def test_build_ticket_data_no_discount_block_for_plain_transaction(db_session, secretaire_user, caisse_repo_factory):
    """Une transaction active qui n'a JAMAIS eu de demande de reduction
    (le cas normal, immensement majoritaire) ne doit jamais chercher ni
    afficher de bloc reduction."""
    from controller.caisse_controller import CaisseController
    from tests.conftest import create_test_transaction

    caisse_repo = caisse_repo_factory()
    tx = create_test_transaction(db_session, secretaire_user)
    assert tx.status == "active"

    caisse_ctrl = CaisseController(repo=caisse_repo, current_user=secretaire_user, discount_repo=DiscountRequestRepository(db_session))
    ticket = caisse_ctrl.build_ticket_data(tx.transaction_id)
    assert ticket["discount"] is None
```

```python
# tests/test_caisse.py (ajout en fin de fichier)

def test_ticket_endpoint_returns_404_for_unknown_transaction(api_client, db_session):
    client = api_client(auth_endpoints, caisse_endpoints)
    create_test_user(db_session, "tk_sec1", "secretaire", password=TEST_PASSWORD)
    headers = auth_headers(client, "tk_sec1", TEST_PASSWORD)
    r = client.get("/caisse/999999/ticket", headers=headers)
    assert r.status_code == 404
```

(Vérifier au préalable les imports déjà présents en tête de `tests/test_caisse.py` : `auth_endpoints`, `caisse_endpoints`, `create_test_user`, `auth_headers`, `TEST_PASSWORD` — réutiliser exactement les mêmes noms déjà importés dans ce fichier, ne pas les réimporter en double.)

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python -m pytest tests/test_discount_requests.py -k build_ticket_data -v tests/test_caisse.py -k ticket_endpoint -v`
Expected: FAIL (`AttributeError: 'CaisseController' object has no attribute 'build_ticket_data'` / 404 générique car la route n'existe pas)

- [ ] **Step 3: Étendre `CaisseController.__init__` et ajouter `build_ticket_data`**

Dans `controller/caisse_controller.py`, modifier le constructeur (paramètre optionnel, ne casse aucun appelant existant) :

```python
    def __init__(self, repo: CaisseRepository, current_user, audit_repo: Optional[AuditRepository] = None,
                 discount_repo=None):
        """
        - repo         : instance de CaisseRepository
        - current_user : instance de User (doit avoir l'attribut 'user_id' et 'username')
        - discount_repo : instance de DiscountRequestRepository, optionnel -
          seule build_ticket_data() en a besoin (recherche d'une reduction
          approuvee). None -> aucun bloc reduction n'est jamais recherche
          (comportement degrade, jamais une exception).
        """
```

Puis ajouter, après `generate_invoice_pdf` :

```python
    def build_ticket_data(self, transaction_id: int) -> dict:
        """Contenu structure du ticket thermique - reutilise integralement
        get_transaction_details_for_invoice() (meme source que la facture
        PDF, memes noms d'articles deja resolus via item.note). Le rendu
        ESC/POS lui-meme est la responsabilite du service pont local, pas
        de ce controller."""
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")

        data = self.repo.get_transaction_details_for_invoice(transaction_id)
        if not data:
            raise ValueError(f"Transaction ID {transaction_id} non trouvée.")

        data["remaining"] = data["amount"] - data["advance_amount"]
        data["payment_method"] = getattr(tx, "payment_method", None)

        data["discount"] = None
        if self.discount_repo:
            approved = self.discount_repo.get_approved_for_transaction(transaction_id)
            if approved:
                data["discount"] = {
                    "decision_percent": approved.decision_percent,
                    "decided_by_name": (approved.decider.full_name or approved.decider.username) if approved.decider else None,
                }

        return data
```

- [ ] **Step 4: Ajouter l'endpoint dans `caisse_endpoints.py`**

Modifier `get_caisse_controller` pour injecter `discount_repo` :

```python
from repositories.discount_request_repo import DiscountRequestRepository
from api_backend.backend_app.utils.pdf_header import get_ticket_header_context
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository

def get_caisse_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CaisseController:
    caisse_repo = CaisseRepository(session=db)
    audit_repo = AuditRepository(db)
    return CaisseController(
        repo=caisse_repo,
        current_user=current_user,
        audit_repo=audit_repo,
        discount_repo=DiscountRequestRepository(db),
    )
```

Puis, après `download_invoice_pdf` :

```python
@router.get("/{transaction_id}/ticket", tags=["Caisse"])
def get_invoice_ticket_data(
    transaction_id: int,
    db: Session = Depends(get_db),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        ticket = caisse_ctrl.build_ticket_data(transaction_id)
        config_ctrl = ConfigController(repo=ConfigRepository(db))
        header_ctx = get_ticket_header_context(config_ctrl)
        structure = header_ctx["structure"]
        ticket["header"] = {
            "structure_name": getattr(structure, "name", None),
            "address": getattr(structure, "address", None),
            "phone": getattr(structure, "phone", None),
            "niu": getattr(structure, "niu", None),
            "rccm": getattr(structure, "rccm", None),
            "legal_info": getattr(structure, "legal_info", None),
            "ticket_logo_path": header_ctx["ticket_logo_path"],
        }
        return ticket
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
```

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

Run: `python -m pytest tests/test_discount_requests.py tests/test_caisse.py -v`
Expected: PASS (tous)

- [ ] **Step 6: Suite complète pour vérifier l'absence de régression**

Run: `python -m pytest tests/ -q`
Expected: mêmes échecs pré-existants qu'avant cette tâche (aucun nouveau FAILED) — attention particulière à `test_update_transaction_blocked_when_pending_approval` et les 4 autres tests du même fichier qui utilisent `_make_controller_with_pending_tx()` : vérifier qu'ils passent toujours tel quel malgré le nouveau paramètre `discount_repo` optionnel.

- [ ] **Step 7: Commit**

```bash
git add controller/caisse_controller.py api_backend/backend_app/routes/caisse/caisse_endpoints.py tests/test_discount_requests.py tests/test_caisse.py
git commit -m "feat: add CaisseController.build_ticket_data + GET /caisse/{id}/ticket"
```

---

## Task 6 : Frontend — jeton d'impression dans `configStore.js` + upload logo ticket dans `SystemConfig.vue`

**Files:**
- Modify: `ah2-admin-web/src/stores/configStore.js`
- Modify: `ah2-admin-web/src/views/SystemConfig.vue`

**Interfaces:**
- Produces: `configStore.ticketPrintToken` (ref), `configStore.fetchTicketPrintToken()`, `configStore.regenerateTicketPrintToken()` — consommés par la Tâche 8 (`PrinterBridgeGateway`).

- [ ] **Step 1: Étendre `configStore.js`**

Ajouter dans le `setup()` de `useConfigStore`, après `structureError` :

```javascript
    const ticketPrintToken = ref(null);

    async function fetchTicketPrintToken() {
        try {
            const response = await api.get('/config/ticket-print-token');
            ticketPrintToken.value = response.data?.token || null;
        } catch (err) {
            console.error('Echec du chargement du jeton d\'impression:', err);
        }
    }

    async function regenerateTicketPrintToken() {
        const response = await api.post('/config/generate-ticket-token');
        ticketPrintToken.value = response.data.token;
        return ticketPrintToken.value;
    }
```

Et les exposer dans le `return` final :

```javascript
    return {
        // State
        examens,
        prayerBookTypes,
        structureInfo,
        isLoading,
        error,
        structureError,
        ticketPrintToken,

        // Actions
        fetchExamens,
        saveExamen,
        deleteExamen,
        fetchPrayerBooks,
        fetchStructureInfo,
        saveStructureInfo,
        fetchTicketPrintToken,
        regenerateTicketPrintToken
    };
```

- [ ] **Step 2: Ajouter le champ d'upload logo ticket dans `SystemConfig.vue`**

Dans le template, juste après le bloc `<div class="md:col-span-4 ...">` du logo couleur (autour de la ligne 53) :

```html
                <div class="md:col-span-4 flex flex-col items-center justify-start p-4 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50 hover:bg-gray-100 transition">
                    <label class="block text-sm font-medium text-gray-700 mb-4">Logo Ticket (monochrome)</label>

                    <div class="relative group cursor-pointer w-40 h-40 mb-4">
                        <img
                            :src="previewTicketLogo || resolveAssetUrl(configStore.structureInfo.ticket_logo_url) || '/placeholder-logo.png'"
                            class="w-full h-full object-contain rounded-lg bg-white shadow-sm border p-2"
                            alt="Aperçu Logo Ticket"
                        />
                        <div class="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <PhotoIcon class="h-8 w-8 text-white" />
                        </div>
                        <input type="file" accept="image/*" @change="handleTicketLogoUpload" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                    </div>

                    <p class="text-xs text-gray-500 text-center">Fichier déjà converti en monochrome, dédié à l'impression thermique.</p>
                </div>

                <div class="md:col-span-12 bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-700">Jeton d'impression ticket</p>
                        <p class="text-xs text-gray-500 font-mono mt-1">{{ configStore.ticketPrintToken || 'Non généré' }}</p>
                    </div>
                    <button type="button" @click="handleRegenerateToken" class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium">
                        Régénérer
                    </button>
                </div>
```

Dans le `<script setup>`, après `const previewLogo = ref(null);` :

```javascript
const ticketLogoFile = ref(null);
const previewTicketLogo = ref(null);

const handleTicketLogoUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
        ticketLogoFile.value = file;
        previewTicketLogo.value = URL.createObjectURL(file);
    }
};

const handleRegenerateToken = async () => {
    if (!confirm("Régénérer le jeton invalidera l'ancien pour tous les services pont locaux déjà configurés. Continuer ?")) return;
    await configStore.regenerateTicketPrintToken();
};
```

Modifier `saveStructureConfig` pour ajouter le fichier au `FormData` :

```javascript
        if (logoFile.value) {
            formData.append('logo', logoFile.value);
        }
        if (ticketLogoFile.value) {
            formData.append('ticket_logo', ticketLogoFile.value);
        }
```

Dans `onMounted`, ajouter :

```javascript
onMounted(async () => {
    await configStore.fetchStructureInfo();
    await configStore.fetchTicketPrintToken();
    configStore.fetchExamens();
    configStore.fetchPrayerBooks();
});
```

- [ ] **Step 3: Vérification manuelle (aucun test automatisé de composant Vue sur ce projet)**

Lancer `npm run dev` (ou `vite`), se connecter en admin, ouvrir Configuration Système, vérifier que le nouveau bloc "Logo Ticket" et "Jeton d'impression ticket" s'affichent, que "Régénérer" change bien la valeur affichée après confirmation.

- [ ] **Step 4: Build de production**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: succès, aucune erreur de compilation.

- [ ] **Step 5: Commit**

```bash
git add ah2-admin-web/src/stores/configStore.js ah2-admin-web/src/views/SystemConfig.vue
git commit -m "feat: ticket logo upload + print token management in SystemConfig"
```

---

## Task 7 : Frontend — `CaisseGateway.getTicket()`

**Files:**
- Modify: `ah2-admin-web/src/services/CaisseGateway.js`

**Interfaces:**
- Produces: `CaisseGateway.getTicket(transactionId) -> Promise<AxiosResponse>` — consommé par la Tâche 9.

- [ ] **Step 1: Ajouter la méthode**

Dans `ah2-admin-web/src/services/CaisseGateway.js`, après `fetchKpis` :

```javascript
    async getTicket(transactionId) {
        return api.get(`/caisse/${transactionId}/ticket`);
    },
```

- [ ] **Step 2: Vérification manuelle**

Depuis la console du navigateur (connecté en secretaire), sur une facture déjà active :
```javascript
await CaisseGateway.getTicket(<un transaction_id réel>)
```
Expected: réponse JSON avec les clés `items`, `amount`, `discount`, `header`.

- [ ] **Step 3: Commit**

```bash
git add ah2-admin-web/src/services/CaisseGateway.js
git commit -m "feat: add CaisseGateway.getTicket"
```

---

## Task 8 : Service pont local — scaffold + rendu ESC/POS pur (`escpos.printer.Dummy`)

**Files:**
- Create: `printer_bridge/config.py`
- Create: `printer_bridge/config.example.json`
- Create: `printer_bridge/ticket_renderer.py`
- Create: `printer_bridge/requirements.txt`
- Create: `printer_bridge/tests/test_ticket_renderer.py`
- Create: `printer_bridge/README.md`

**Interfaces:**
- Produces: `render_ticket(printer, ticket_data: dict) -> None` (fonction pure, prend n'importe quelle instance `escpos.printer.*` — `Dummy` en test, `Win32Raw`/`Usb` en réel) ; `load_config(path: str) -> dict` avec clés `connection_type` (`"win32raw"` ou `"usb"`), `printer_name` (si win32raw), `vendor_id`/`product_id` (si usb), `token`, `port` — consommé par la Tâche 10.

- [ ] **Step 1: Créer `requirements.txt` du pont**

```
fastapi>=0.110
uvicorn[standard]>=0.29
python-escpos>=3.1
pillow>=10.0
pywin32>=306; sys_platform == 'win32'
```

- [ ] **Step 2: Créer `config.example.json`**

```json
{
  "connection_type": "win32raw",
  "printer_name": "POS Printer Emulator",
  "vendor_id": null,
  "product_id": null,
  "token": "CHANGE_ME_avec_le_jeton_genere_dans_Configuration_Systeme",
  "port": 9123
}
```

- [ ] **Step 3: Créer `config.py`**

```python
# printer_bridge/config.py
import json
import os

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Charge la config du pont depuis un fichier JSON local (jamais commite
    en clair - config.json est dans .gitignore, seul config.example.json
    est versionne). Leve FileNotFoundError explicitement si absent, plutot
    que de demarrer silencieusement avec des valeurs par defaut dangereuses
    (ex. token vide qui accepterait n'importe quelle requete)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Fichier de configuration introuvable : {path}. "
            f"Copiez config.example.json vers config.json et renseignez-le."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 4: Écrire les tests du rendu de ticket (avec `escpos.printer.Dummy`)**

```python
# printer_bridge/tests/test_ticket_renderer.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from escpos.printer import Dummy
from ticket_renderer import render_ticket


def _sample_ticket(**overrides):
    base = {
        "transaction_id": 42,
        "patient_name": "Jean Dupont",
        "user_name": "secretaire1",
        "paid_at": "2026-09-28T10:30:00",
        "amount": 10000.0,
        "advance_amount": 10000.0,
        "remaining": 0.0,
        "payment_method": "Espèces",
        "items": [
            {"item_name": "Consultation générale", "quantity": 1, "unit_price": 10000.0, "line_total": 10000.0},
        ],
        "discount": None,
        "header": {
            "structure_name": "Clinique AH2",
            "address": "Douala",
            "phone": "699000000",
            "niu": "M012345678",
            "rccm": "RC/DLA/2020/B/1234",
            "legal_info": None,
            "ticket_logo_path": None,
        },
    }
    base.update(overrides)
    return base


def test_render_ticket_includes_structure_name_and_transaction_id():
    printer = Dummy()
    render_ticket(printer, _sample_ticket())
    output = printer.output.decode("latin-1", errors="ignore")
    assert "Clinique AH2" in output
    assert "42" in output


def test_render_ticket_includes_item_line_with_quantity_and_price():
    printer = Dummy()
    render_ticket(printer, _sample_ticket())
    output = printer.output.decode("latin-1", errors="ignore")
    assert "Consultation générale" in output
    assert "10000" in output


def test_render_ticket_shows_discount_block_when_present():
    printer = Dummy()
    ticket = _sample_ticket(discount={"decision_percent": 20, "decided_by_name": "Dr Manager"})
    render_ticket(printer, ticket)
    output = printer.output.decode("latin-1", errors="ignore")
    assert "20" in output
    assert "Dr Manager" in output


def test_render_ticket_omits_discount_block_when_none():
    printer = Dummy()
    render_ticket(printer, _sample_ticket(discount=None))
    output = printer.output.decode("latin-1", errors="ignore")
    assert "Réduction" not in output


def test_render_ticket_truncates_long_item_name_without_crashing():
    """Review Focus : une designation trop longue pour du papier 80mm
    (~42 caracteres en police normale) ne doit jamais faire planter le
    rendu ni deborder de facon illisible."""
    printer = Dummy()
    long_name = "Consultation spécialisée en médecine interne avec suivi prolongé et bilan complet"
    render_ticket(printer, _sample_ticket(items=[
        {"item_name": long_name, "quantity": 1, "unit_price": 5000.0, "line_total": 5000.0},
    ]))
    output = printer.output.decode("latin-1", errors="ignore")
    lines = [l for l in output.split("\n") if long_name[:20] in l]
    assert len(lines) >= 1
    # aucune ligne de la sortie ne doit depasser une largeur raisonnable
    # (marge large : 48 caracteres, au-dela du 42 usuel du 80mm, pour
    # tolerer les codes ESC/POS eux-memes dans le buffer brut)
    for line in output.split("\n"):
        printable = "".join(ch for ch in line if ch.isprintable())
        assert len(printable) <= 48
```

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd printer_bridge && python -m pip install -r requirements.txt && python -m pytest tests/test_ticket_renderer.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'ticket_renderer'`)

- [ ] **Step 6: Implémenter `ticket_renderer.py`**

```python
# printer_bridge/ticket_renderer.py
"""Rendu ESC/POS pur du ticket de caisse - ne connait rien au reseau ni a
la config, prend n'importe quelle instance escpos.printer.* (Dummy en test,
Win32Raw/Usb en reel). Toute la logique metier (calcul du montant reduit,
recherche de la reduction approuvee) vit deja cote backend
(CaisseController.build_ticket_data) - cette fonction ne fait QUE mettre en
page ce qui lui est fourni."""

PAPER_WIDTH_CHARS = 42  # 80mm, police normale - marge de securite volontaire


def _truncate(text: str, max_len: int = PAPER_WIDTH_CHARS) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _line_item(name: str, quantity, unit_price, line_total) -> str:
    designation = _truncate(f"{quantity}x {name}", PAPER_WIDTH_CHARS - 12)
    return f"{designation}\n   P.U: {unit_price:.0f}   Total: {line_total:.0f}"


def render_ticket(printer, ticket_data: dict) -> None:
    header = ticket_data.get("header", {}) or {}

    printer.set(align="center")
    ticket_logo_path = header.get("ticket_logo_path")
    if ticket_logo_path:
        try:
            printer.image(ticket_logo_path)
        except Exception:
            pass  # logo illisible/corrompu -> le ticket continue sans, jamais bloquant

    printer.set(align="center", bold=True, double_height=True)
    printer.text(f"{header.get('structure_name') or ''}\n")
    printer.set(align="center", bold=False, double_height=False)
    if header.get("address"):
        printer.text(f"{header['address']}\n")
    if header.get("phone"):
        printer.text(f"Tel: {header['phone']}\n")
    if header.get("niu") or header.get("rccm"):
        printer.text(f"NIU: {header.get('niu') or ''}  RCCM: {header.get('rccm') or ''}\n")

    printer.text("-" * PAPER_WIDTH_CHARS + "\n")
    printer.set(align="left")
    printer.text(f"Facture N: {ticket_data.get('transaction_id')}\n")
    printer.text(f"Date: {ticket_data.get('paid_at') or ''}\n")
    printer.text(f"Caissier: {ticket_data.get('user_name') or ''}\n")
    printer.text(f"Patient: {ticket_data.get('patient_name') or ''}\n")
    printer.text("-" * PAPER_WIDTH_CHARS + "\n")

    for item in ticket_data.get("items", []):
        printer.text(_line_item(
            item.get("item_name") or "Article",
            item.get("quantity"),
            float(item.get("unit_price") or 0),
            float(item.get("line_total") or 0),
        ) + "\n")

    printer.text("-" * PAPER_WIDTH_CHARS + "\n")
    printer.set(align="right")
    printer.text(f"TOTAL: {float(ticket_data.get('amount') or 0):.0f}\n")

    discount = ticket_data.get("discount")
    if discount:
        printer.set(align="left")
        printer.text(
            f"Réduction validée par {discount.get('decided_by_name') or '?'} "
            f"- {discount.get('decision_percent')}%\n"
        )
        printer.set(align="right")

    printer.text(f"Paye: {float(ticket_data.get('advance_amount') or 0):.0f}\n")
    remaining = float(ticket_data.get("remaining") or 0)
    if remaining > 0:
        printer.text(f"Reste a payer: {remaining:.0f}\n")
    printer.set(align="left")
    if ticket_data.get("payment_method"):
        printer.text(f"Mode: {ticket_data['payment_method']}\n")

    printer.text("-" * PAPER_WIDTH_CHARS + "\n")
    printer.set(align="center")
    printer.text("Merci de votre visite !\n")
    if header.get("legal_info"):
        printer.text(f"{header['legal_info']}\n")
    printer.cut()
```

- [ ] **Step 7: Lancer les tests pour vérifier qu'ils passent**

Run: `cd printer_bridge && python -m pytest tests/test_ticket_renderer.py -v`
Expected: PASS (6 tests)

- [ ] **Step 8: Créer `README.md` du pont**

```markdown
# Service pont impression POS

Service Python autonome qui tourne sur le poste secrétariat (pas sur le serveur backend). Reçoit le contenu JSON d'un ticket depuis le frontend et l'imprime via ESC/POS.

## Installation (développement, avec l'émulateur POS Windows)

1. `pip install -r requirements.txt`
2. Installer/lancer "POS Printer Emulator for Windows" — il s'enregistre comme une imprimante Windows classique.
3. Copier `config.example.json` vers `config.json`, renseigner `printer_name` avec le nom exact affiché dans les imprimantes Windows, et `token` avec la valeur générée dans Configuration Système > Régénérer.
4. `python server.py`

## Bascule vers une vraie imprimante USB

Dans `config.json`, changer `connection_type` à `"usb"` et renseigner `vendor_id`/`product_id` (visibles dans le Gestionnaire de périphériques Windows) — aucun changement de code nécessaire.

## Tests

`python -m pytest tests/ -v` — utilise `escpos.printer.Dummy`, aucune imprimante ni émulateur nécessaire.
```

- [ ] **Step 9: Commit**

```bash
git add printer_bridge/
git commit -m "feat: printer bridge scaffold + pure ESC/POS ticket renderer"
```

---

## Task 9 : Service pont local — serveur HTTP (`server.py`) avec authentification par jeton

**Files:**
- Create: `printer_bridge/server.py`
- Create: `printer_bridge/tests/test_server.py`
- Modify: `printer_bridge/README.md`

**Interfaces:**
- Consumes: `load_config` (Task 8), `render_ticket` (Task 8).
- Produces: application FastAPI exposant `GET /health` (public) et `POST /print` (protégé par en-tête `X-Print-Token`) — consommé par la Tâche 10 (`PrinterBridgeGateway.js`).

- [ ] **Step 1: Écrire les tests du serveur**

```python
# printer_bridge/tests/test_server.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

FAKE_CONFIG = {
    "connection_type": "win32raw",
    "printer_name": "POS Printer Emulator",
    "vendor_id": None,
    "product_id": None,
    "token": "test-token-123",
    "port": 9123,
}


@pytest.fixture
def client():
    with patch("server.load_config", return_value=FAKE_CONFIG):
        import server
        importlib_reload_needed = server
        return TestClient(server.app)


def test_health_endpoint_is_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_print_endpoint_rejects_missing_token(client):
    r = client.post("/print", json={"transaction_id": 1})
    assert r.status_code == 401


def test_print_endpoint_rejects_wrong_token(client):
    r = client.post("/print", json={"transaction_id": 1}, headers={"X-Print-Token": "wrong"})
    assert r.status_code == 401


def test_print_endpoint_accepts_correct_token_and_calls_render(client):
    with patch("server.get_active_printer") as mock_get_printer, \
         patch("server.render_ticket") as mock_render:
        mock_get_printer.return_value = MagicMock()
        r = client.post(
            "/print",
            json={"transaction_id": 1, "header": {}, "items": []},
            headers={"X-Print-Token": "test-token-123"},
        )
        assert r.status_code == 200
        mock_render.assert_called_once()


def test_print_endpoint_returns_503_when_printer_unreachable(client):
    with patch("server.get_active_printer", side_effect=Exception("printer offline")):
        r = client.post(
            "/print",
            json={"transaction_id": 1, "header": {}, "items": []},
            headers={"X-Print-Token": "test-token-123"},
        )
        assert r.status_code == 503
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd printer_bridge && python -m pytest tests/test_server.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'server'`)

- [ ] **Step 3: Implémenter `server.py`**

```python
# printer_bridge/server.py
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Header
from escpos.printer import Win32Raw, Usb

from config import load_config
from ticket_renderer import render_ticket

logger = logging.getLogger("printer_bridge")

app = FastAPI(title="AH2 Printer Bridge")


def get_active_printer():
    """Instancie la connexion imprimante reelle a chaque appel (pas de
    connexion persistante gardee ouverte entre deux tickets - plus simple,
    et une imprimante thermique USB/Win32Raw supporte tres bien une
    ouverture/fermeture par ticket sur le volume d'une secretariat)."""
    config = load_config()
    if config["connection_type"] == "win32raw":
        return Win32Raw(config["printer_name"])
    if config["connection_type"] == "usb":
        return Usb(config["vendor_id"], config["product_id"])
    raise ValueError(f"connection_type inconnu: {config['connection_type']}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/print")
def print_ticket(ticket_data: Dict[str, Any], x_print_token: str = Header(None)):
    config = load_config()
    if not x_print_token or x_print_token != config.get("token"):
        raise HTTPException(status_code=401, detail="Jeton invalide ou manquant")

    try:
        printer = get_active_printer()
    except Exception as e:
        logger.exception("Imprimante injoignable")
        raise HTTPException(status_code=503, detail=f"Imprimante indisponible: {e}")

    try:
        render_ticket(printer, ticket_data)
    except Exception as e:
        logger.exception("Echec du rendu/envoi du ticket")
        raise HTTPException(status_code=500, detail=f"Erreur d'impression: {e}")

    return {"status": "printed"}


if __name__ == "__main__":
    import uvicorn
    config = load_config()
    uvicorn.run(app, host="127.0.0.1", port=config.get("port", 9123))
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd printer_bridge && python -m pytest tests/ -v`
Expected: PASS (tous, y compris les 6 de la Tâche 8)

- [ ] **Step 5: Vérification manuelle contre l'émulateur**

Avec l'émulateur POS Windows installé et `config.json` renseigné (nom d'imprimante exact, jeton copié depuis Configuration Système) :
```bash
cd printer_bridge && python server.py
```
Dans un autre terminal :
```bash
curl -X POST http://localhost:9123/print -H "X-Print-Token: <le jeton>" -H "Content-Type: application/json" -d @tests/sample_ticket.json
```
(Créer `printer_bridge/tests/sample_ticket.json` avec le contenu de `_sample_ticket()` de la Tâche 8, en JSON.)
Expected : la fenêtre de l'émulateur affiche le ticket rendu, mise en page conforme à la spec (en-tête, articles, totaux, bloc réduction si testé avec `discount` renseigné).

- [ ] **Step 6: Commit**

```bash
git add printer_bridge/server.py printer_bridge/tests/test_server.py printer_bridge/tests/sample_ticket.json printer_bridge/README.md
git commit -m "feat: printer bridge HTTP server with token auth"
```

---

## Task 10 : Frontend — `PrinterBridgeGateway.js`

**Files:**
- Create: `ah2-admin-web/src/services/PrinterBridgeGateway.js`

**Interfaces:**
- Consumes: `configStore.ticketPrintToken` (Task 6).
- Produces: `PrinterBridgeGateway.printTicket(ticketData) -> Promise<void>` (lève une erreur explicite en cas d'échec, jamais silencieuse) — consommé par les Tâches 11 et 12.

- [ ] **Step 1: Créer le fichier**

```javascript
// src/services/PrinterBridgeGateway.js
import { useConfigStore } from '@/stores/configStore';

const BRIDGE_URL = import.meta.env.VITE_PRINT_BRIDGE_URL || 'http://localhost:9123';

export const PrinterBridgeGateway = {
    /**
     * Envoie le JSON d'un ticket au service pont local pour impression.
     * Toujours best-effort du point de vue de l'appelant : cette fonction
     * leve une erreur explicite en cas d'echec (pont injoignable, jeton
     * manquant, imprimante hors ligne) - c'est a l'appelant de l'attraper
     * et de ne jamais bloquer le flux metier (creation de facture) dessus.
     */
    async printTicket(ticketData) {
        const configStore = useConfigStore();
        const token = configStore.ticketPrintToken;
        if (!token) {
            throw new Error("Jeton d'impression non configuré.");
        }
        const response = await fetch(`${BRIDGE_URL}/print`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Print-Token': token,
            },
            body: JSON.stringify(ticketData),
        });
        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            throw new Error(body.detail || `Impression échouée (${response.status})`);
        }
    },
};
```

- [ ] **Step 2: Vérification manuelle**

Avec le pont local lancé (Tâche 9) et un jeton configuré côté `configStore` (déjà chargé au montage de l'app), depuis la console navigateur :
```javascript
await PrinterBridgeGateway.printTicket({ transaction_id: 1, header: {}, items: [] })
```
Expected: pas d'erreur, le ticket s'imprime sur l'émulateur.

- [ ] **Step 3: Commit**

```bash
git add ah2-admin-web/src/services/PrinterBridgeGateway.js
git commit -m "feat: add PrinterBridgeGateway"
```

---

## Task 11 : Frontend — impression automatique + bouton Réimprimer dans `CaisseList.vue`

**Files:**
- Modify: `ah2-admin-web/src/views/modules/finance/CaisseList.vue`

**Interfaces:**
- Consumes: `CaisseGateway.getTicket` (Task 7), `PrinterBridgeGateway.printTicket` (Task 10).

- [ ] **Step 1: Localiser `handleCreateInvoice` et ajouter le déclenchement d'impression**

Chercher la fonction `handleCreateInvoice` dans `CaisseList.vue` (celle appelée par `@save="handleCreateInvoice"` sur `<CaisseInvoiceModal>`). Après l'appel réussi à `caisseStore.createInvoice(...)` qui ferme la modale, ajouter :

```javascript
import { PrinterBridgeGateway } from '@/services/PrinterBridgeGateway';

// ... dans handleCreateInvoice, juste après la fermeture reussie de la modale
// (showInvoiceModal.value = false), uniquement si la facture est
// immediatement active (pas de reduction demandee - une facture
// pending_approval n'a pas encore de statut final, voir Task 5) :
if (result && result.status !== 'pending_approval' && result.transaction_id) {
    printTicketForTransaction(result.transaction_id);
}
```

- [ ] **Step 2: Ajouter la fonction partagée `printTicketForTransaction` + l'état d'erreur d'impression**

```javascript
const printError = ref('');

const printTicketForTransaction = async (transactionId) => {
    printError.value = '';
    try {
        const resp = await CaisseGateway.getTicket(transactionId);
        await PrinterBridgeGateway.printTicket(resp.data);
    } catch (err) {
        printError.value = "Ticket non imprimé — imprimante indisponible. Utilisez le bouton Réimprimer pour réessayer.";
        console.error('Erreur impression ticket:', err);
    }
};
```

Et dans le template, un bandeau dédié (distinct de `actionError` déjà existant, pour ne pas mélanger les deux causes d'erreur) :

```html
    <div v-if="printError" class="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-xl">
      <p class="text-sm text-amber-700">{{ printError }}</p>
    </div>
```

- [ ] **Step 3: Ajouter le bouton "Réimprimer" dans la table**

Dans la colonne actions (`<div class="flex items-center justify-end gap-1.5">`), après le bouton de téléchargement PDF :

```html
                  <button v-if="tx.status === 'active'" @click="printTicketForTransaction(tx.transaction_id)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-100 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.reprint_ticket') : 'En attente de synchronisation'">
                    <PrinterIcon class="h-4 w-4" />
                  </button>
```

Ajouter `PrinterIcon` à l'import `@heroicons/vue/24/outline` déjà présent en tête du `<script setup>`.

- [ ] **Step 4: Ajouter les clés i18n**

Dans `ah2-admin-web/src/i18n.js`, section `caisse.actions` (fr, ligne ~460) :
```javascript
        reprint_ticket: "Réimprimer le ticket",
```
Et section équivalente en (en) :
```javascript
        reprint_ticket: "Reprint ticket",
```

- [ ] **Step 5: Build de production**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: succès.

- [ ] **Step 6: Vérification manuelle**

Avec le backend, le pont local et l'émulateur tous lancés : créer une facture normale en secretaire → vérifier l'impression automatique. Cliquer "Réimprimer" sur une facture existante → vérifier une deuxième impression. Arrêter le pont local puis réessayer → vérifier le bandeau d'erreur, la facture reste bien dans la liste.

- [ ] **Step 7: Commit**

```bash
git add ah2-admin-web/src/views/modules/finance/CaisseList.vue ah2-admin-web/src/i18n.js
git commit -m "feat: auto-print ticket on invoice creation + reprint button"
```

---

## Task 12 : Frontend — impression automatique après décision de réduction (`NotificationBell.vue`)

**Files:**
- Modify: `ah2-admin-web/src/components/notifications/NotificationBell.vue`

**Interfaces:**
- Consumes: `CaisseGateway.getTicket` (Task 7), `PrinterBridgeGateway.printTicket` (Task 10), `authStore.hasRole` (existant).

- [ ] **Step 1: Ajouter le déclenchement dans le cycle de polling existant**

`NotificationBell.vue` a déjà un `popupCheckTimer` (`setInterval`, toutes les 1s) qui appelle `notificationStore.popNextPopup()`. Ajouter la logique d'impression dans `onMounted`, en réagissant aux nouvelles notifications récupérées par `notificationStore.startPolling()` :

```javascript
import { useAuthStore } from '@/stores/auth';
import { CaisseGateway } from '@/services/CaisseGateway';
import { PrinterBridgeGateway } from '@/services/PrinterBridgeGateway';

const authStore = useAuthStore();
const printedDecisionIds = new Set(); // evite une double impression si la meme notification est relue

const maybePrintApprovedDiscountTicket = async (n) => {
    if (!authStore.hasRole(['secretaire'])) return;
    if (n.type !== 'discount_decided') return;
    if (n.payload?.status !== 'approved') return;
    if (printedDecisionIds.has(n.id)) return;
    printedDecisionIds.add(n.id);

    try {
        const resp = await CaisseGateway.getTicket(n.payload.transaction_id);
        await PrinterBridgeGateway.printTicket(resp.data);
    } catch (err) {
        console.error('Impression automatique post-décision échouée:', err);
        // Pas de bandeau ici (composant global monté partout) - l'utilisateur
        // peut toujours reimprimer manuellement depuis CaisseList.vue (Task 11).
    }
};
```

- [ ] **Step 2: Brancher ce déclenchement sur l'arrivée de nouvelles notifications**

Modifier `onMounted` pour surveiller les nouvelles notifications (pas seulement les popups) :

```javascript
onMounted(() => {
  notificationStore.startPolling();
  popupCheckTimer = setInterval(() => {
    if (!activePopup.value) {
      const next = notificationStore.popNextPopup();
      if (next) activePopup.value = next;
    }
    // Verifie aussi les decisions de reduction fraichement recues,
    // independamment du popup (qui ne se declenche que pour discount_request,
    // jamais discount_decided - voir labelFor)
    notificationStore.notifications.forEach(maybePrintApprovedDiscountTicket);
  }, 1000);
});
```

- [ ] **Step 3: Vérification manuelle du scénario complet**

Deux sessions navigateur : secrétaire (avec pont local + émulateur lancés) crée une facture avec demande de réduction ; manager (autre session, autre machine simulée par un autre profil navigateur) approuve la demande. Vérifier que le ticket s'imprime automatiquement côté secrétaire dans la minute (délai du polling), avec le bloc réduction visible sur le ticket rendu par l'émulateur.

- [ ] **Step 4: Build de production**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: succès.

- [ ] **Step 5: Commit**

```bash
git add ah2-admin-web/src/components/notifications/NotificationBell.vue
git commit -m "feat: auto-print ticket after discount decision notification"
```

---

## Task 13 : Vérification finale — suite complète + non-régression

- [ ] **Step 1: Suite backend complète**

Run: `python -m pytest tests/ -q`
Expected: uniquement les échecs pré-existants déjà documentés (caisse/prescriptions WIP, sans rapport avec ce chantier) — aucun nouveau FAILED.

- [ ] **Step 2: Suite du pont local**

Run: `cd printer_bridge && python -m pytest tests/ -v`
Expected: PASS (tous).

- [ ] **Step 3: Build frontend production**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: succès.

- [ ] **Step 4: Protocole de test manuel de bout en bout (avec l'émulateur)**

Dans l'ordre :
1. Facture normale (sans réduction) → impression automatique immédiate.
2. Facture avec demande de réduction, approuvée par le manager → impression automatique côté secrétaire dans la minute qui suit la décision, bloc réduction visible.
3. Facture avec demande de réduction, refusée → aucune impression automatique tant que la secrétaire n'a pas ré-essayé manuellement ; ticket réimprimé manuellement ne doit PAS afficher de bloc réduction (statut refusé).
4. Pont local arrêté pendant la création d'une facture → bandeau d'erreur affiché, facture bien enregistrée, "Réimprimer" fonctionne une fois le pont relancé.
5. Nom d'article très long → vérifier visuellement sur l'émulateur que la troncature reste lisible.
6. Non-régression : téléchargement de la facture PDF classique toujours fonctionnel, exports patients/dossiers toujours fonctionnels (aucun changement de `get_pdf_header_context` côté comportement).

- [ ] **Step 5: Mettre à jour `SUIVI-AVANCEMENT.md` et la mémoire du projet**

Ajouter une section "Imprimante thermique POS — ticket de caisse" décrivant ce qui a été livré, les résultats de vérification, et tout résidu trouvé pendant l'exécution (pattern déjà établi sur ce projet pour chaque chantier fermé).
