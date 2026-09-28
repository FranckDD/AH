# Notifications + validation des réductions caisse — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer la validation papier des réductions caisse (falsifiable, source de vol avéré) par un workflow numérique tracé : la secrétaire demande, un manager (`admin`/`promoteur`) choisi nommément décide avec reconfirmation par mot de passe, la décision est journalisée dans l'audit existant.

**Architecture:** Deux nouvelles tables (`notifications`, `discount_requests`), un nouvel état `caisse.status = 'pending_approval'` qui verrouille la facture pendant l'attente, un store Pinia à polling léger (30s) pour les notifications, réutilisation intégrale des primitives existantes (`User.check_password`, `AuditRepository.log_user_action`, `CaisseRepository.create_transaction`).

**Tech Stack:** FastAPI + SQLAlchemy (backend), Vue 3 + Pinia (frontend), Postgres.

**Spec:** `docs/superpowers/specs/2026-09-25-notifications-reduction-caisse-design.md`

## Global Constraints

- Aucun commit git sans accord explicite à chaque fois — ce dépôt ne committe jamais en session, snapshots + `diff -u` pour toute revue au lieu de `git diff`.
- Travail direct sur le répertoire principal — pas de worktree.
- Migration réelle contre la base de données uniquement après accord explicite de l'utilisateur via question directe.
- `refuse: true` est exclusif avec `decision_percent`/`decision_echelonne_deadline` (422 sinon).
- `status` final d'une décision : `'refused'` seulement si `refuse: true` ; `'approved'` dès qu'au moins un des deux (pourcentage > 0 et/ou échéance) est accordé — un échéancier seul, sans pourcentage, compte comme approuvé.
- `caisse.amount` recalculé uniquement si un pourcentage a été accordé ; inchangé si échéancier seul.
- `caisse.status` repasse à `'active'` dans tous les cas (approuvé ou refusé), jamais laissé sur `'pending_approval'`.
- Une seule ligne `discount_requests.status = 'pending'` par `transaction_id` à la fois.
- Rôles : `secretaire` crée/annule ses propres demandes ; `admin`/`promoteur` décident celles qui leur sont adressées ; aucun autre rôle concerné.

---

## File Structure

Backend :
- `alembic/versions/013_notifications_discount_requests.py` (nouveau) — 2 tables.
- `models/notification.py` (nouveau) — modèle `Notification`.
- `models/discount_request.py` (nouveau) — modèle `DiscountRequest`.
- `repositories/notification_repo.py` (nouveau) — CRUD notifications.
- `repositories/discount_request_repo.py` (nouveau) — CRUD + logique de décision.
- `repositories/caisse_repo.py` — `create_transaction` gagne un paramètre `initial_status`.
- `repositories/user_repo.py` — `get_users_by_role_names(role_names: list[str])`.
- `controller/caisse_controller.py` — `update_transaction`/`cancel_transaction`/`add_installment_payment` refusent si `status == 'pending_approval'`.
- `controller/discount_request_controller.py` (nouveau) — logique métier (création, annulation, décision + mot de passe + audit).
- `controller/notification_controller.py` (nouveau) — lecture/marquage lu.
- `api_backend/backend_app/routes/discount/discount_endpoints.py` (nouveau) — 4 routes.
- `api_backend/backend_app/routes/discount/discount_schemas.py` (nouveau) — Pydantic.
- `api_backend/backend_app/routes/notifications/notification_endpoints.py` (nouveau) — 2 routes.
- `api_backend/backend_app/routes/admin/users_endpoint.py` — nouvelle route `GET /users/managers`.
- `api_backend/backend_app/main.py` — enregistrement des 2 nouveaux routers.
- `tests/test_discount_requests.py`, `tests/test_notifications.py` (nouveaux).

Frontend :
- `ah2-admin-web/src/services/NotificationGateway.js` (nouveau).
- `ah2-admin-web/src/services/DiscountRequestGateway.js` (nouveau).
- `ah2-admin-web/src/stores/notificationStore.js` (nouveau) — polling 30s, popup une fois par notification.
- `ah2-admin-web/src/components/notifications/NotificationBell.vue` (nouveau) — pastille + popup, monté dans les layouts concernés.
- `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue` — bouton "Demander une réduction", sélecteur de destinataire, affichage de l'état d'attente.
- `ah2-admin-web/src/views/modules/caisse/DiscountReview.vue` (nouveau) — écran de réception manager.
- `ah2-admin-web/src/components/layout/MainLayout.vue`, `ah2-admin-web/src/components/layout/SecretaireLayout.vue` — montage de `NotificationBell`.
- `ah2-admin-web/src/router/index.js` — route `discount-review`.

---

### Task 1: Migration — `notifications` + `discount_requests`

**Files:**
- Create: `alembic/versions/013_notifications_discount_requests.py`

**Interfaces:**
- Produces: tables `notifications` (`id, recipient_user_id, type, payload, status, created_at, read_at`) et `discount_requests` (`id, transaction_id, requested_by, requested_to, original_amount, status, decision_percent, decision_echelonne_deadline, decided_by, decided_at, created_at`).

- [ ] **Step 1: Écrire la migration**

Vérifier d'abord la révision actuelle (`alembic current`) pour le `down_revision` exact — ne pas supposer `'012_lab_results_uuid'`, le confirmer par `grep -rn "down_revision" alembic/versions/*.py` (le head est la révision jamais référencée comme `down_revision` d'une autre).

```python
"""notifications + discount_requests

Revision ID: 013_notif_discount
Revises: <TETE_ACTUELLE_VERIFIEE>
Create Date: 2026-09-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '013_notif_discount'
down_revision = '<TETE_ACTUELLE_VERIFIEE>'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            recipient_user_id INTEGER NOT NULL REFERENCES users(user_id),
            type VARCHAR(50) NOT NULL,
            payload JSONB,
            status VARCHAR(20) NOT NULL DEFAULT 'unread',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            read_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_notifications_recipient_status
            ON notifications (recipient_user_id, status);

        CREATE TABLE IF NOT EXISTS discount_requests (
            id SERIAL PRIMARY KEY,
            transaction_id INTEGER NOT NULL REFERENCES caisse(transaction_id),
            requested_by INTEGER NOT NULL REFERENCES users(user_id),
            requested_to INTEGER NOT NULL REFERENCES users(user_id),
            original_amount NUMERIC(10,2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            decision_percent INTEGER,
            decision_echelonne_deadline DATE,
            decided_by INTEGER REFERENCES users(user_id),
            decided_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_discount_requests_transaction
            ON discount_requests (transaction_id);
        CREATE INDEX IF NOT EXISTS ix_discount_requests_requested_to_status
            ON discount_requests (requested_to, status);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS discount_requests;
        DROP TABLE IF EXISTS notifications;
    """)
```

Note : raw SQL avec `IF NOT EXISTS`/`IF EXISTS` partout, même motif que la migration 012 de ce projet (idempotence en cas de retry après échec partiel) — pas de dance nullable→backfill→NOT NULL ici, ces deux tables sont neuves, aucune ligne existante à migrer.

- [ ] **Step 2: Vérifier la longueur de l'id de révision**

Run: `python -c "print(len('013_notif_discount'))"`
Expected: ≤ 32 (piège déjà rencontré sur ce projet — `alembic_version.version_num` est `varchar(32)`).

- [ ] **Step 3: NE PAS appliquer la migration**

Fichier seulement, comme convenu — application différée à la dernière tâche, après accord explicite de l'utilisateur.

---

### Task 2: Backend — modèles SQLAlchemy

**Files:**
- Create: `models/notification.py`
- Create: `models/discount_request.py`
- Modify: `api_backend/backend_app/database.py` (ou l'endroit où les modèles sont importés pour qu'Alembic/SQLAlchemy les découvre — chercher comment `models/lab.py` ou `models/caisse.py` sont déjà importés/enregistrés et suivre exactement le même point d'entrée)

**Interfaces:**
- Consumes: `models.database.Base`, `models.caisse.Caisse`, `models.user.User`.
- Produces: `Notification` (colonnes : `id, recipient_user_id, type, payload, status, created_at, read_at`), `DiscountRequest` (colonnes : `id, transaction_id, requested_by, requested_to, original_amount, status, decision_percent, decision_echelonne_deadline, decided_by, decided_at, created_at`).

- [ ] **Step 1: `models/notification.py`**

```python
# models/notification.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, default="unread")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, recipient={self.recipient_user_id})>"
```

- [ ] **Step 2: `models/discount_request.py`**

```python
# models/discount_request.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey
from .database import Base


class DiscountRequest(Base):
    __tablename__ = "discount_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("caisse.transaction_id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    requested_to = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    original_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    decision_percent = Column(Integer, nullable=True)
    decision_echelonne_deadline = Column(Date, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<DiscountRequest(id={self.id}, transaction={self.transaction_id}, status={self.status})>"
```

- [ ] **Step 3: Enregistrer les modèles**

Lire d'abord comment un modèle récent (ex. `models/lab.py`) est rendu visible à SQLAlchemy/Alembic dans ce projet — chercher un fichier central (`models/__init__.py`, ou l'import list dans `api_backend/backend_app/database.py`/`alembic/env.py`) qui importe tous les modèles pour que `Base.metadata` les connaisse. Ajouter les deux nouveaux imports au même endroit, dans le même style que les imports existants.

- [ ] **Step 4: Test — import sans erreur**

```python
# tests/test_notifications.py (début du fichier, sera complété en Task 3)
def test_models_import_cleanly():
    from models.notification import Notification
    from models.discount_request import DiscountRequest
    assert Notification.__tablename__ == "notifications"
    assert DiscountRequest.__tablename__ == "discount_requests"
```

Run: `pytest tests/test_notifications.py::test_models_import_cleanly -v`
Expected: PASS

---

### Task 3: Backend — dépôt et contrôleur notifications

**Files:**
- Create: `repositories/notification_repo.py`
- Create: `controller/notification_controller.py`
- Test: `tests/test_notifications.py` (complété)

**Interfaces:**
- Consumes: `models.notification.Notification`.
- Produces: `NotificationRepository.create(recipient_user_id, type, payload) -> Notification`, `NotificationRepository.list_unread(recipient_user_id) -> list[Notification]`, `NotificationRepository.mark_read(notification_id, recipient_user_id) -> Notification`. `NotificationController` expose les mêmes opérations côté métier, appelées par les endpoints de la Task 8.

- [ ] **Step 1: `repositories/notification_repo.py`**

```python
# repositories/notification_repo.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from models.notification import Notification


class NotificationRepository:
    def __init__(self, session):
        self.session = session

    def create(self, recipient_user_id: int, type: str, payload: Optional[Dict[str, Any]] = None) -> Notification:
        notif = Notification(recipient_user_id=recipient_user_id, type=type, payload=payload)
        self.session.add(notif)
        self.session.flush()
        return notif

    def list_unread(self, recipient_user_id: int) -> List[Notification]:
        return (
            self.session.query(Notification)
            .filter(Notification.recipient_user_id == recipient_user_id, Notification.status == "unread")
            .order_by(Notification.created_at.desc())
            .all()
        )

    def mark_read(self, notification_id: int, recipient_user_id: int) -> Optional[Notification]:
        notif = (
            self.session.query(Notification)
            .filter(Notification.id == notification_id, Notification.recipient_user_id == recipient_user_id)
            .first()
        )
        if not notif:
            return None
        notif.status = "read"
        notif.read_at = datetime.utcnow()
        return notif
```

Note : `recipient_user_id` filtré systématiquement dans `mark_read` — sans ça, un utilisateur pourrait marquer comme lue la notification de quelqu'un d'autre en devinant son id.

- [ ] **Step 2: `controller/notification_controller.py`**

```python
# controller/notification_controller.py
from typing import List
from repositories.notification_repo import NotificationRepository
from models.notification import Notification


class NotificationController:
    def __init__(self, repo: NotificationRepository, current_user):
        self.repo = repo
        self.user = current_user

    def list_unread(self) -> List[Notification]:
        return self.repo.list_unread(self.user.user_id)

    def mark_read(self, notification_id: int) -> Notification:
        notif = self.repo.mark_read(notification_id, self.user.user_id)
        if not notif:
            raise ValueError("Notification introuvable.")
        self.repo.session.commit()
        return notif
```

- [ ] **Step 3: Tests**

```python
# tests/test_notifications.py (ajouter)
from repositories.notification_repo import NotificationRepository
from controller.notification_controller import NotificationController


def test_create_and_list_unread(db_session):
    repo = NotificationRepository(db_session)
    repo.create(recipient_user_id=1, type="discount_request", payload={"amount": 5000})
    db_session.commit()
    unread = repo.list_unread(1)
    assert len(unread) == 1
    assert unread[0].type == "discount_request"


def test_mark_read_scoped_to_recipient(db_session):
    repo = NotificationRepository(db_session)
    notif = repo.create(recipient_user_id=1, type="discount_request")
    db_session.commit()
    # Un autre destinataire ne peut pas la marquer lue
    result = repo.mark_read(notif.id, recipient_user_id=2)
    assert result is None
    # Le bon destinataire peut
    result = repo.mark_read(notif.id, recipient_user_id=1)
    assert result is not None
    assert result.status == "read"
```

Adapter le nom de la fixture `db_session` à ce qui existe réellement dans `tests/conftest.py` (vérifier avant d'écrire, ne pas supposer).

- [ ] **Step 4: Exécuter les tests**

Run: `pytest tests/test_notifications.py -v`
Expected: PASS

---

### Task 4: Backend — endpoints notifications

**Files:**
- Create: `api_backend/backend_app/routes/notifications/notification_endpoints.py`
- Modify: `api_backend/backend_app/main.py` (enregistrement du router)

**Interfaces:**
- Consumes: `NotificationController` (Task 3), `get_current_user` (`api_backend.backend_app.routes.auth.auth_endpoints`).
- Produces: `GET /notifications?status=unread` (tout rôle authentifié), `POST /notifications/{id}/read`.

- [ ] **Step 1: Écrire les endpoints**

Lire d'abord un fichier d'endpoints existant simple (ex. `api_backend/backend_app/routes/labo/lab_endpoints.py`, lignes 1-60) pour le style exact `get_db`/dependency-injection déjà établi, puis suivre le même moule :

```python
# api_backend/backend_app/routes/notifications/notification_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user
from repositories.notification_repo import NotificationRepository
from controller.notification_controller import NotificationController

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_notification_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> NotificationController:
    repo = NotificationRepository(db)
    return NotificationController(repo=repo, current_user=current_user)


@router.get("", response_model=List[Dict])
def list_notifications(
    status: Optional[str] = Query(None),
    ctrl: NotificationController = Depends(get_notification_controller),
):
    notifs = ctrl.list_unread() if status == "unread" or status is None else []
    return [
        {
            "id": n.id,
            "type": n.type,
            "payload": n.payload,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.post("/{notification_id}/read")
def mark_notification_read(notification_id: int, ctrl: NotificationController = Depends(get_notification_controller)):
    try:
        ctrl.mark_read(notification_id)
        return {"detail": "Notification marquée lue."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
```

Note : `status=None` traité comme `'unread'` (seul cas d'usage réel prévu par la spec — un historique complet n'est pas demandé) ; tout autre valeur renvoie une liste vide plutôt qu'une erreur, pour rester permissif côté client sans avoir à gérer un cas d'erreur inutile.

- [ ] **Step 2: Enregistrer le router**

Lire `api_backend/backend_app/main.py`, trouver où les routers existants (`labo`, `caisse`, etc.) sont inclus via `app.include_router(...)`, ajouter la même ligne pour ce nouveau router, dans le même bloc/ordre logique.

- [ ] **Step 3: Test d'intégration minimal**

```python
# tests/test_notifications.py (ajouter)
def test_list_notifications_endpoint_scoped_to_current_user(client, secretaire_token):
    r = client.get("/notifications?status=unread", headers={"Authorization": f"Bearer {secretaire_token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

Adapter `client`/`secretaire_token` aux fixtures réelles de `tests/conftest.py` (vérifier avant d'écrire).

- [ ] **Step 4: Exécuter les tests**

Run: `pytest tests/test_notifications.py -v`
Expected: PASS

---

### Task 5: Backend — verrouillage des factures `pending_approval`

**Files:**
- Modify: `controller/caisse_controller.py:249-273` (`update_transaction`, `cancel_transaction`), et `add_installment_payment` (lignes 217-247)
- Test: `tests/test_discount_requests.py` (nouveau, démarré ici)

**Interfaces:**
- Produces: les 3 méthodes lèvent `ValueError("Facture en attente de validation d'une réduction - action impossible.")` si `tx.status == 'pending_approval'` — converti en 400 par les endpoints existants (déjà le cas pour tout `ValueError` sur ces 3 routes, vérifié en Task de préparation du plan).

- [ ] **Step 1: Garde dans `update_transaction`**

Dans `controller/caisse_controller.py`, au début de `update_transaction` (juste après la vérification `if tx.status == "cancelled":`) :

```python
    def update_transaction(self, transaction_id: int, data: dict) -> Caisse:
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        if tx.status == "cancelled":
            raise ValueError("Impossible de modifier une transaction annulée.")
        if tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
```

(le reste de la méthode ne change pas.)

- [ ] **Step 2: Garde dans `cancel_transaction`**

```python
    def cancel_transaction(self, transaction_id: int, justification: str) -> Caisse:
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
        tx = self.repo.cancel_transaction(transaction_id, self.user, justification)
```

Note : `self.repo.cancel_transaction(...)` est appelé une seconde fois volontairement dans le code existant (c'est déjà la méthode qui fait le travail réel) — la garde ajoutée ici relit `get_by_id` explicitement AVANT, puisque la version actuelle de `cancel_transaction` n'a pas de lecture préalable à exploiter.

- [ ] **Step 3: Garde dans `add_installment_payment`**

```python
    def add_installment_payment(self, transaction_id: int, data: dict):
        tx = self.repo.get_by_id(transaction_id)
        if not tx: raise ValueError("Transaction introuvable")
        if tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
```

(le reste de la méthode, à partir de `remaining = float(tx.amount) - float(tx.advance_amount)`, ne change pas.)

- [ ] **Step 4: Tests**

```python
# tests/test_discount_requests.py
import pytest
from models.caisse import Caisse


def test_update_transaction_blocked_when_pending_approval(db_session, caisse_controller_factory):
    ctrl = caisse_controller_factory()
    tx = Caisse(patient_id=None, amount=1000, advance_amount=0, created_by_name="t", handled_by=1,
                payment_method="Espèces", transaction_type="Consultation", status="pending_approval")
    db_session.add(tx)
    db_session.commit()
    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.update_transaction(tx.transaction_id, {"note": "test"})


def test_cancel_transaction_blocked_when_pending_approval(db_session, caisse_controller_factory):
    ctrl = caisse_controller_factory()
    tx = Caisse(patient_id=None, amount=1000, advance_amount=0, created_by_name="t", handled_by=1,
                payment_method="Espèces", transaction_type="Consultation", status="pending_approval")
    db_session.add(tx)
    db_session.commit()
    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.cancel_transaction(tx.transaction_id, "test annulation")


def test_add_installment_payment_blocked_when_pending_approval(db_session, caisse_controller_factory):
    ctrl = caisse_controller_factory()
    tx = Caisse(patient_id=None, amount=1000, advance_amount=0, created_by_name="t", handled_by=1,
                payment_method="Espèces", transaction_type="Consultation", status="pending_approval")
    db_session.add(tx)
    db_session.commit()
    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.add_installment_payment(tx.transaction_id, {"paid_amount": 100, "payment_method": "Espèces", "payment_type": "VERSEMENT_ECHEANCE"})
```

`caisse_controller_factory` est une fixture à créer si elle n'existe pas déjà — vérifier `tests/conftest.py` pour un motif équivalent déjà utilisé par les tests caisse existants (`tests/test_caisse.py`) et le réutiliser plutôt que d'en inventer un nouveau.

- [ ] **Step 5: Exécuter les tests**

Run: `pytest tests/test_discount_requests.py -v`
Expected: PASS (3/3)

---

### Task 6: Backend — création/annulation de demande de réduction

**Files:**
- Modify: `repositories/caisse_repo.py:187` (`create_transaction` gagne `initial_status`)
- Modify: `repositories/user_repo.py` (nouvelle méthode `get_users_by_role_names`)
- Create: `repositories/discount_request_repo.py`
- Create: `controller/discount_request_controller.py`
- Test: `tests/test_discount_requests.py` (complété)

**Interfaces:**
- Consumes: `CaisseRepository.create_transaction`, `NotificationRepository.create` (Task 3).
- Produces: `DiscountRequestController.create_request(invoice_data: dict, requested_to: int) -> DiscountRequest`, `DiscountRequestController.cancel_request(request_id: int) -> DiscountRequest`, `UserRepository.get_users_by_role_names(role_names: list[str]) -> list[User]`.

- [ ] **Step 1: `initial_status` sur `create_transaction`**

Dans `repositories/caisse_repo.py`, modifier la signature et le seul endroit où `status` est fixé :

```python
    def create_transaction(self, data: dict, current_user, initial_status: str = 'active') -> Caisse:
        """
        Crée une transaction complète : ...
        """
        # --- 1. Création de l'en-tête (Facture) ---
        tx = Caisse(
            patient_id       = data.get("patient_id"),
            patient_label    = data.get("patient_label"),
            amount           = data["amount"],
            advance_amount   = 0.0,
            paid_at          = data.get("paid_at", datetime.now()),
            created_by_name  = current_user.username,
            handled_by       = current_user.user_id,
            payment_method   = data["payment_method"],
            transaction_type = data["transaction_type"],
            note             = data.get("note"),
            status           = initial_status
        )
```

(le reste de la méthode, traitement des lignes/stock/avance, ne change pas — le paramètre par défaut `'active'` garantit qu'aucun appelant existant n'est affecté.)

- [ ] **Step 2: `get_users_by_role_names` sur `UserRepository`**

Dans `repositories/user_repo.py`, ajouter juste après `get_users_by_role_name` :

```python
    def get_users_by_role_names(self, role_names: list[str]) -> list[User]:
        """Comme get_users_by_role_name, mais correspondance exacte sur
        plusieurs roles a la fois (ex: ['admin', 'promoteur']) - utilise
        .in_() plutot que .ilike() car on veut une liste fermee de roles
        precis, pas un motif partiel."""
        return (
            self.session.query(User)
            .join(ApplicationRole)
            .filter(ApplicationRole.role_name.in_(role_names))
            .filter(User.is_active == True)
            .all()
        )
```

Vérifier l'import de `ApplicationRole` déjà présent en haut du fichier (utilisé par `get_users_by_role_name` juste au-dessus) — le réutiliser, ne pas le réimporter.

- [ ] **Step 3: `repositories/discount_request_repo.py`**

```python
# repositories/discount_request_repo.py
from datetime import datetime
from decimal import Decimal
from typing import Optional
from models.discount_request import DiscountRequest
from models.caisse import Caisse


class DiscountRequestRepository:
    def __init__(self, session):
        self.session = session

    def get_pending_for_transaction(self, transaction_id: int) -> Optional[DiscountRequest]:
        return (
            self.session.query(DiscountRequest)
            .filter(DiscountRequest.transaction_id == transaction_id, DiscountRequest.status == "pending")
            .first()
        )

    def create(self, transaction_id: int, requested_by: int, requested_to: int, original_amount: Decimal) -> DiscountRequest:
        req = DiscountRequest(
            transaction_id=transaction_id,
            requested_by=requested_by,
            requested_to=requested_to,
            original_amount=original_amount,
            status="pending",
        )
        self.session.add(req)
        self.session.flush()
        return req

    def get_by_id(self, request_id: int) -> Optional[DiscountRequest]:
        return self.session.query(DiscountRequest).filter(DiscountRequest.id == request_id).first()

    def list_pending_for_recipient(self, requested_to: int) -> list[DiscountRequest]:
        return (
            self.session.query(DiscountRequest)
            .filter(DiscountRequest.requested_to == requested_to, DiscountRequest.status == "pending")
            .order_by(DiscountRequest.created_at.asc())
            .all()
        )

    def cancel(self, request: DiscountRequest) -> DiscountRequest:
        request.status = "cancelled"
        return request

    def decide(self, request: DiscountRequest, decided_by: int, refuse: bool,
               decision_percent: Optional[int], decision_echelonne_deadline) -> DiscountRequest:
        request.decided_by = decided_by
        request.decided_at = datetime.utcnow()
        if refuse:
            request.status = "refused"
        else:
            request.decision_percent = decision_percent
            request.decision_echelonne_deadline = decision_echelonne_deadline
            request.status = "approved"
        return request
```

- [ ] **Step 4: `controller/discount_request_controller.py` — création et annulation seulement (la décision est Task 7)**

```python
# controller/discount_request_controller.py
from decimal import Decimal
from typing import Dict, Any
from repositories.discount_request_repo import DiscountRequestRepository
from repositories.caisse_repo import CaisseRepository
from repositories.notification_repo import NotificationRepository
from models.discount_request import DiscountRequest


class DiscountRequestController:
    def __init__(self, repo: DiscountRequestRepository, caisse_repo: CaisseRepository,
                 notification_repo: NotificationRepository, current_user):
        self.repo = repo
        self.caisse_repo = caisse_repo
        self.notification_repo = notification_repo
        self.user = current_user

    def create_request(self, invoice_data: Dict[str, Any], requested_to: int) -> DiscountRequest:
        """Cree la facture (status='pending_approval' des la creation,
        decision utilisateur n2) ET la demande dans le meme geste."""
        required_keys = ["payment_method", "transaction_type", "amount", "items", "advance_amount"]
        for key in required_keys:
            if key not in invoice_data:
                raise ValueError(f"Champ manquant : {key}")
        if not invoice_data["items"] and invoice_data.get("advance_amount", 0) == 0:
            raise ValueError("La transaction doit contenir au moins une ligne ou indiquer une avance.")
        total_calc = sum(line["line_total"] for line in invoice_data["items"])
        if total_calc != invoice_data["amount"]:
            raise ValueError(f"Incohérence montant: Lignes({total_calc}) != Total({invoice_data['amount']}).")

        tx = self.caisse_repo.create_transaction(invoice_data, self.user, initial_status="pending_approval")

        req = self.repo.create(
            transaction_id=tx.transaction_id,
            requested_by=self.user.user_id,
            requested_to=requested_to,
            original_amount=Decimal(str(invoice_data["amount"])),
        )

        self.notification_repo.create(
            recipient_user_id=requested_to,
            type="discount_request",
            payload={
                "discount_request_id": req.id,
                "transaction_id": tx.transaction_id,
                "patient_label": tx.patient_label,
                "amount": float(req.original_amount),
                "requested_by_name": getattr(self.user, "full_name", self.user.username),
            },
        )
        self.repo.session.commit()
        return req

    def cancel_and_reassign(self, request_id: int, new_requested_to: int) -> DiscountRequest:
        old_req = self.repo.get_by_id(request_id)
        if not old_req:
            raise ValueError("Demande introuvable.")
        if old_req.requested_by != self.user.user_id:
            raise PermissionError("Seul l'auteur de la demande peut l'annuler.")
        if old_req.status != "pending":
            raise ValueError("Cette demande n'est plus en attente.")

        self.repo.cancel(old_req)

        new_req = self.repo.create(
            transaction_id=old_req.transaction_id,
            requested_by=self.user.user_id,
            requested_to=new_requested_to,
            original_amount=old_req.original_amount,
        )
        self.notification_repo.create(
            recipient_user_id=new_requested_to,
            type="discount_request",
            payload={
                "discount_request_id": new_req.id,
                "transaction_id": new_req.transaction_id,
                "amount": float(new_req.original_amount),
                "requested_by_name": getattr(self.user, "full_name", self.user.username),
            },
        )
        self.repo.session.commit()
        return new_req
```

Note : `create_request` réplique volontairement les 3 premières validations de `CaisseController.create_transaction` (champs requis, coherence du montant) — la ligne stock/pharmacie de `create_transaction` original ne change pas de comportement, elle reste dans `CaisseRepository.create_transaction`, seul le `status` initial diffère. Pas de duplication du traitement des lignes, seulement de sa pré-validation.

- [ ] **Step 5: Tests**

```python
# tests/test_discount_requests.py (ajouter)
from controller.discount_request_controller import DiscountRequestController
from repositories.discount_request_repo import DiscountRequestRepository
from repositories.notification_repo import NotificationRepository


def test_create_request_locks_transaction(db_session, secretaire_user, manager_user, caisse_repo_factory):
    caisse_repo = caisse_repo_factory()
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session),
        caisse_repo=caisse_repo,
        notification_repo=NotificationRepository(db_session),
        current_user=secretaire_user,
    )
    invoice_data = {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 5000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 5000, "quantity": 1, "line_total": 5000}],
    }
    req = ctrl.create_request(invoice_data, requested_to=manager_user.user_id)
    tx = caisse_repo.get_by_id(req.transaction_id)
    assert tx.status == "pending_approval"
    assert req.status == "pending"
    assert req.original_amount == 5000


def test_cancel_and_reassign_keeps_history(db_session, secretaire_user, manager_user, manager2_user, caisse_repo_factory):
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session),
        caisse_repo=caisse_repo_factory(),
        notification_repo=NotificationRepository(db_session),
        current_user=secretaire_user,
    )
    invoice_data = {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 3000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 3000, "quantity": 1, "line_total": 3000}],
    }
    first = ctrl.create_request(invoice_data, requested_to=manager_user.user_id)
    second = ctrl.cancel_and_reassign(first.id, manager2_user.user_id)

    db_session.refresh(first)
    assert first.status == "cancelled"
    assert second.status == "pending"
    assert second.requested_to == manager2_user.user_id
    assert second.transaction_id == first.transaction_id
```

Fixtures `secretaire_user`/`manager_user`/`manager2_user`/`caisse_repo_factory` à créer si absentes — vérifier d'abord `tests/conftest.py`/`tests/test_caisse.py` pour des équivalents déjà utilisés (`create_test_user`, etc.) et les réutiliser directement plutôt que d'en écrire de nouvelles versions.

- [ ] **Step 6: Exécuter les tests**

Run: `pytest tests/test_discount_requests.py -v`
Expected: PASS (5/5 en comptant la Task 5)

---

### Task 7: Backend — décision avec reconfirmation par mot de passe + audit

**Files:**
- Modify: `controller/discount_request_controller.py` (ajout de `decide_request`)
- Test: `tests/test_discount_requests.py` (complété)

**Interfaces:**
- Consumes: `User.check_password(password: str) -> bool` (déjà existant, `models/user.py:60`), `AuditRepository.log_user_action(current_user, resource_type, action_performed, resource_id, new_values)` (déjà existant, `repositories/audit_repo.py:146`).
- Produces: `DiscountRequestController.decide_request(request_id, password, refuse, decision_percent, decision_echelonne_deadline) -> DiscountRequest`.

- [ ] **Step 1: `decide_request` sur le contrôleur**

**Important** : ne PAS utiliser `AuthController.authenticate()` pour la reconfirmation — cette méthode a un effet de bord (elle écrit un log `LOGIN_SUCCESS` dans l'audit et instancie une dizaine de sous-contrôleurs inutiles ici). Utiliser directement `User.check_password(password)`, une méthode d'instance déjà existante et sans effet de bord (`models/user.py:60-61`).

Dans `controller/discount_request_controller.py`, ajouter le paramètre `audit_repo` au constructeur et la méthode :

```python
class DiscountRequestController:
    def __init__(self, repo: DiscountRequestRepository, caisse_repo: CaisseRepository,
                 notification_repo: NotificationRepository, current_user, audit_repo=None):
        self.repo = repo
        self.caisse_repo = caisse_repo
        self.notification_repo = notification_repo
        self.audit_repo = audit_repo
        self.user = current_user

    # ... create_request, cancel_and_reassign inchanges ...

    def decide_request(self, request_id: int, password: str, refuse: bool,
                        decision_percent: int = None, decision_echelonne_deadline=None) -> DiscountRequest:
        if not self.user.check_password(password):
            raise PermissionError("Mot de passe incorrect.")

        req = self.repo.get_by_id(request_id)
        if not req:
            raise ValueError("Demande introuvable.")
        if req.requested_to != self.user.user_id:
            raise PermissionError("Cette demande ne vous est pas adressée.")
        if req.status != "pending":
            raise ValueError("Cette demande n'est plus en attente.")
        if refuse and (decision_percent or decision_echelonne_deadline):
            raise ValueError("Un refus ne peut pas être accompagné d'un pourcentage ou d'une échéance.")

        self.repo.decide(req, self.user.user_id, refuse, decision_percent, decision_echelonne_deadline)

        tx = self.caisse_repo.get_by_id(req.transaction_id)
        if not refuse and decision_percent:
            tx.amount = float(req.original_amount) * (1 - decision_percent / 100)
        tx.status = "active"

        if self.audit_repo:
            self.audit_repo.log_user_action(
                current_user=self.user,
                resource_type="DiscountRequest",
                action_performed="REFUSE" if refuse else "APPROVE",
                resource_id=req.id,
                new_values={
                    "transaction_id": req.transaction_id,
                    "decision_percent": decision_percent,
                    "decision_echelonne_deadline": str(decision_echelonne_deadline) if decision_echelonne_deadline else None,
                    "original_amount": float(req.original_amount),
                    "final_amount": float(tx.amount),
                },
            )

        self.notification_repo.create(
            recipient_user_id=req.requested_by,
            type="discount_decided",
            payload={
                "discount_request_id": req.id,
                "transaction_id": req.transaction_id,
                "status": req.status,
                "decision_percent": decision_percent,
                "decision_echelonne_deadline": str(decision_echelonne_deadline) if decision_echelonne_deadline else None,
            },
        )
        self.repo.session.commit()
        return req
```

- [ ] **Step 2: Tests**

```python
# tests/test_discount_requests.py (ajouter)
import pytest
from datetime import date


def _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory, notification_repo=None):
    from repositories.audit_repo import AuditRepository
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session),
        caisse_repo=caisse_repo_factory(),
        notification_repo=notification_repo or NotificationRepository(db_session),
        current_user=secretaire_user,
        audit_repo=AuditRepository(db_session),
    )
    invoice_data = {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 10000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 10000, "quantity": 1, "line_total": 10000}],
    }
    return ctrl.create_request(invoice_data, requested_to=manager_user.user_id), ctrl


def test_decide_wrong_password_rejected(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    with pytest.raises(PermissionError, match="Mot de passe incorrect"):
        ctrl.decide_request(req.id, password="mauvais_mdp", refuse=False, decision_percent=20)
    db_session.refresh(req)
    assert req.status == "pending"


def test_decide_approve_percent_updates_amount_and_audit(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=20)

    db_session.refresh(req)
    assert req.status == "approved"
    assert req.decision_percent == 20

    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert tx.status == "active"
    assert float(tx.amount) == 8000.0  # 10000 * (1 - 0.20)


def test_decide_echelonne_only_does_not_change_amount(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False,
                         decision_echelonne_deadline=date(2026, 12, 31))

    db_session.refresh(req)
    assert req.status == "approved"
    assert req.decision_echelonne_deadline == date(2026, 12, 31)
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert float(tx.amount) == 10000.0  # inchangé, pas de pourcentage


def test_decide_refuse_rejects_combined_percent(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    with pytest.raises(ValueError, match="refus ne peut pas"):
        ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=True, decision_percent=10)
```

`manager_user.PLAIN_PASSWORD` suppose que la fixture `manager_user` (Task 6) expose le mot de passe en clair utilisé pour le hasher — si la fixture existante du projet (`create_test_user`) ne le fait pas déjà, l'ajuster pour le stocker en attribut de test (ex: `user.PLAIN_PASSWORD = TEST_PASSWORD` juste après création), suivre le motif déjà utilisé par `tests/test_lab_endpoints.py` ou équivalent pour un compte de test avec mot de passe connu.

- [ ] **Step 3: Exécuter les tests**

Run: `pytest tests/test_discount_requests.py -v`
Expected: PASS (9/9)

---

### Task 8: Backend — endpoints discount-requests + route managers

**Files:**
- Create: `api_backend/backend_app/routes/discount/discount_schemas.py`
- Create: `api_backend/backend_app/routes/discount/discount_endpoints.py`
- Modify: `api_backend/backend_app/routes/admin/users_endpoint.py` (nouvelle route `GET /users/managers`)
- Modify: `api_backend/backend_app/main.py` (enregistrement du router)

**Interfaces:**
- Consumes: `DiscountRequestController` (Tasks 6-7), `UserRepository.get_users_by_role_names` (Task 6).
- Produces: `POST /discount-requests`, `POST /discount-requests/{id}/cancel`, `POST /discount-requests/{id}/decide`, `GET /discount-requests/pending` (pour l'écran de réception manager), `GET /users/managers`.

- [ ] **Step 1: Schémas Pydantic**

```python
# api_backend/backend_app/routes/discount/discount_schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import date


class DiscountRequestCreate(BaseModel):
    invoice_data: Dict[str, Any]
    requested_to: int


class DiscountRequestCancel(BaseModel):
    new_requested_to: int


class DiscountRequestDecide(BaseModel):
    password: str
    refuse: bool = False
    decision_percent: Optional[int] = None
    decision_echelonne_deadline: Optional[date] = None
```

- [ ] **Step 2: Endpoints**

```python
# api_backend/backend_app/routes/discount/discount_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Dict

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from repositories.discount_request_repo import DiscountRequestRepository
from repositories.caisse_repo import CaisseRepository
from repositories.notification_repo import NotificationRepository
from repositories.audit_repo import AuditRepository
from controller.discount_request_controller import DiscountRequestController
from .discount_schemas import DiscountRequestCreate, DiscountRequestCancel, DiscountRequestDecide

router = APIRouter(prefix="/discount-requests", tags=["discount-requests"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_discount_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> DiscountRequestController:
    return DiscountRequestController(
        repo=DiscountRequestRepository(db),
        caisse_repo=CaisseRepository(db),
        notification_repo=NotificationRepository(db),
        audit_repo=AuditRepository(db),
        current_user=current_user,
    )


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required("secretaire"))])
def create_discount_request(payload: DiscountRequestCreate, ctrl: DiscountRequestController = Depends(get_discount_controller)):
    try:
        req = ctrl.create_request(payload.invoice_data, payload.requested_to)
        return {"id": req.id, "transaction_id": req.transaction_id, "status": req.status}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/{request_id}/cancel", dependencies=[Depends(role_required("secretaire"))])
def cancel_discount_request(request_id: int, payload: DiscountRequestCancel, ctrl: DiscountRequestController = Depends(get_discount_controller)):
    try:
        req = ctrl.cancel_and_reassign(request_id, payload.new_requested_to)
        return {"id": req.id, "status": req.status}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))


@router.get("/pending", dependencies=[Depends(role_required("admin", "promoteur"))])
def list_pending_discount_requests(ctrl: DiscountRequestController = Depends(get_discount_controller)):
    pending = ctrl.repo.list_pending_for_recipient(ctrl.user.user_id)
    return [
        {
            "id": r.id, "transaction_id": r.transaction_id, "original_amount": float(r.original_amount),
            "requested_by": r.requested_by, "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in pending
    ]


@router.post("/{request_id}/decide", dependencies=[Depends(role_required("admin", "promoteur"))])
def decide_discount_request(request_id: int, payload: DiscountRequestDecide, ctrl: DiscountRequestController = Depends(get_discount_controller)):
    try:
        req = ctrl.decide_request(
            request_id, payload.password, payload.refuse,
            payload.decision_percent, payload.decision_echelonne_deadline,
        )
        return {"id": req.id, "status": req.status}
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
```

- [ ] **Step 3: `GET /users/managers`**

Dans `api_backend/backend_app/routes/admin/users_endpoint.py`, ajouter juste après `list_doctors` (suivre exactement le même moule — pas de restriction de rôle supplémentaire, `secretaire` doit pouvoir l'appeler pour peupler son sélecteur de destinataire) :

```python
@router.get("/managers", response_model=List[UserOut])
def list_managers(user_ctrl: UserController = Depends(get_user_controller)):
    """Récupère les comptes admin/promoteur actifs pour le sélecteur de
    destinataire d'une demande de réduction (chantier notifications)."""
    try:
        raws = user_ctrl.user_repo.get_users_by_role_names(["admin", "promoteur"])
        return [_safe_validate_user(u) for u in raws]
    except Exception as e:
        logger.exception("Erreur lors de la récupération des managers")
        raise HTTPException(status_code=500, detail=str(e))
```

Vérifier que `UserController` expose bien `self.user_repo` (lire la classe rapidement) — sinon utiliser le chemin d'accès réel à `UserRepository` depuis `UserController`.

- [ ] **Step 4: Enregistrer le router**

Même procédure que Task 4/Step 2 pour `discount_endpoints.router` dans `main.py`.

- [ ] **Step 5: Tests d'intégration**

```python
# tests/test_discount_requests.py (ajouter)
def test_create_request_endpoint_forbidden_for_admin(client, admin_token):
    r = client.post("/discount-requests", json={"invoice_data": {}, "requested_to": 1},
                     headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 403


def test_list_pending_endpoint_forbidden_for_secretaire(client, secretaire_token):
    r = client.get("/discount-requests/pending", headers={"Authorization": f"Bearer {secretaire_token}"})
    assert r.status_code == 403
```

- [ ] **Step 6: Exécuter les tests**

Run: `pytest tests/test_discount_requests.py -v`
Expected: PASS (11/11)

---

### Task 9: Frontend — store de notifications + pastille/popup

**Files:**
- Create: `ah2-admin-web/src/services/NotificationGateway.js`
- Create: `ah2-admin-web/src/stores/notificationStore.js`
- Create: `ah2-admin-web/src/components/notifications/NotificationBell.vue`

**Interfaces:**
- Consumes: `GET /notifications?status=unread`, `POST /notifications/{id}/read`, `useAuthStore().hasRole([...])` (déjà existant).
- Produces: `useNotificationStore()` exposant `unreadCount`, `unreadNotifications`, `startPolling()`, `stopPolling()`, `markRead(id)`. `<NotificationBell />` composant monté par la Task 11.

- [ ] **Step 1: `NotificationGateway.js`**

```javascript
// src/services/NotificationGateway.js
import api from './api';

export const NotificationGateway = {
    async listUnread() {
        return api.get('/notifications', { params: { status: 'unread' } });
    },
    async markRead(id) {
        return api.post(`/notifications/${id}/read`);
    },
};
```

- [ ] **Step 2: `notificationStore.js`**

```javascript
// src/stores/notificationStore.js
import { defineStore } from 'pinia';
import { NotificationGateway } from '@/services/NotificationGateway';

const POLL_INTERVAL_MS = 30000;

export const useNotificationStore = defineStore('notification', {
    state: () => ({
        notifications: [],
        seenIds: new Set(),
        pollTimer: null,
        popupQueue: [],
    }),

    getters: {
        unreadCount: (state) => state.notifications.length,
    },

    actions: {
        async fetchUnread() {
            try {
                const res = await NotificationGateway.listUnread();
                const fresh = res.data || [];
                // Nouvelle notification = jamais vue depuis le demarrage du store
                // (pas juste "pas dans la derniere liste recue", pour ne jamais
                // re-declencher un popup deja affiche une fois).
                const newlySeen = fresh.filter((n) => !this.seenIds.has(n.id));
                newlySeen.forEach((n) => {
                    this.seenIds.add(n.id);
                    this.popupQueue.push(n);
                });
                this.notifications = fresh;
            } catch (err) {
                console.error('Erreur chargement notifications:', err);
            }
        },

        startPolling() {
            if (this.pollTimer) return;
            this.fetchUnread();
            this.pollTimer = setInterval(() => this.fetchUnread(), POLL_INTERVAL_MS);
        },

        stopPolling() {
            if (this.pollTimer) {
                clearInterval(this.pollTimer);
                this.pollTimer = null;
            }
        },

        async markRead(id) {
            try {
                await NotificationGateway.markRead(id);
                this.notifications = this.notifications.filter((n) => n.id !== id);
            } catch (err) {
                console.error('Erreur marquage notification lue:', err);
            }
        },

        popNextPopup() {
            return this.popupQueue.shift() || null;
        },
    },
});
```

Note : `seenIds` (un `Set`, jamais vidé pendant la session) garantit qu'une notification ne déclenche son popup qu'une seule fois — même si elle reste dans la réponse `unread` de plusieurs polls consécutifs tant qu'elle n'est pas marquée lue.

- [ ] **Step 3: `NotificationBell.vue`**

Lire d'abord `ah2-admin-web/src/components/layout/MainLayout.vue` (déjà lu, structure du `<header>` autour de la ligne 92-98, bouton `UserCircleIcon`) pour matcher le style visuel exact (classes Tailwind, taille d'icône).

```vue
<!-- src/components/notifications/NotificationBell.vue -->
<template>
  <div class="relative">
    <button
      @click="toggleOpen"
      class="relative flex items-center text-gray-600 hover:text-gray-900 transition"
      :title="$t('notifications.title')"
    >
      <BellIcon class="h-6 w-6" />
      <span
        v-if="notificationStore.unreadCount > 0"
        class="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold rounded-full h-4 w-4 flex items-center justify-center"
      >
        {{ notificationStore.unreadCount > 9 ? '9+' : notificationStore.unreadCount }}
      </span>
    </button>

    <div v-if="open" class="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-96 overflow-y-auto">
      <div v-if="notificationStore.notifications.length === 0" class="p-4 text-sm text-gray-400 text-center">
        {{ $t('notifications.empty') }}
      </div>
      <div
        v-for="n in notificationStore.notifications"
        :key="n.id"
        class="p-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer text-sm"
        @click="handleClick(n)"
      >
        <div class="font-medium text-gray-800">{{ labelFor(n) }}</div>
        <div class="text-xs text-gray-400 mt-1">{{ formatDate(n.created_at) }}</div>
      </div>
    </div>

    <!-- Popup bloquant pour une nouvelle demande de reduction -->
    <div v-if="activePopup" class="fixed inset-0 bg-black/30 flex items-center justify-center z-[100]" @click.self="dismissPopup">
      <div class="bg-white rounded-xl shadow-2xl p-6 max-w-sm w-full">
        <h3 class="font-bold text-gray-800 mb-2">{{ labelFor(activePopup) }}</h3>
        <button @click="dismissPopup" class="mt-4 w-full bg-indigo-600 text-white rounded-lg py-2 font-medium hover:bg-indigo-700">
          {{ $t('common.ok') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { BellIcon } from '@heroicons/vue/24/outline';
import { useNotificationStore } from '@/stores/notificationStore';
import router from '@/router';

const notificationStore = useNotificationStore();
const open = ref(false);
const activePopup = ref(null);
let popupCheckTimer = null;

const toggleOpen = () => { open.value = !open.value; };

const labelFor = (n) => {
  if (n.type === 'discount_request') {
    return `${n.payload?.requested_by_name || '?'} demande une réduction (${n.payload?.amount ?? '?'} FCFA)`;
  }
  if (n.type === 'discount_decided') {
    return n.payload?.status === 'refused' ? 'Demande de réduction refusée' : 'Demande de réduction traitée';
  }
  return n.type;
};

const formatDate = (iso) => iso ? new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '';

const handleClick = async (n) => {
  await notificationStore.markRead(n.id);
  open.value = false;
  if (n.type === 'discount_request') {
    router.push({ name: 'discount-review' });
  }
};

const dismissPopup = () => { activePopup.value = null; };

onMounted(() => {
  notificationStore.startPolling();
  popupCheckTimer = setInterval(() => {
    if (!activePopup.value) {
      const next = notificationStore.popNextPopup();
      if (next) activePopup.value = next;
    }
  }, 1000);
});

onUnmounted(() => {
  notificationStore.stopPolling();
  if (popupCheckTimer) clearInterval(popupCheckTimer);
});
</script>
```

Note : le popup vérifie la file toutes les secondes plutôt que de réagir directement à `fetchUnread()`, pour éviter d'afficher 2 popups simultanément si plusieurs notifications arrivent au même poll — un seul à la fois, à la file.

- [ ] **Step 4: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert (peut échouer si les clés i18n `notifications.title`/`notifications.empty`/`common.ok` n'existent pas encore — les ajouter à `src/i18n.js` dans les mêmes blocs `fr`/`en` que les clés voisines si absentes, suivre le style déjà en place).

---

### Task 10: Frontend — bouton "Demander une réduction" dans `CaisseInvoiceModal.vue`

**Files:**
- Modify: `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue`
- Create: `ah2-admin-web/src/services/DiscountRequestGateway.js`

**Interfaces:**
- Consumes: `POST /discount-requests`, `GET /users/managers`, `authStore.hasRole(['secretaire'])`.
- Produces: `$emit('request-discount', {invoice_data, requested_to})` géré par le composant parent (l'écran caisse qui monte cette modale) — Task 11 ne le couvre pas, cette tâche s'arrête à l'émission de l'événement et à l'appel réseau direct, cohérent avec le fait que `handleSubmit` actuel fait déjà l'appel réseau lui-même plutôt que de faire remonter les données brutes (vérifier ce point précisément en lisant `handleSubmit` avant d'écrire, et suivre le même choix pour rester cohérent avec le fichier).

- [ ] **Step 1: `DiscountRequestGateway.js`**

```javascript
// src/services/DiscountRequestGateway.js
import api from './api';

export const DiscountRequestGateway = {
    async listManagers() {
        return api.get('/users/managers');
    },
    async create(invoiceData, requestedTo) {
        return api.post('/discount-requests', { invoice_data: invoiceData, requested_to: requestedTo });
    },
    async cancel(requestId, newRequestedTo) {
        return api.post(`/discount-requests/${requestId}/cancel`, { new_requested_to: newRequestedTo });
    },
};
```

- [ ] **Step 2: Lire `handleSubmit` actuel**

Lire `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue` en entier (le fichier fait ~260 lignes, déjà partiellement lu jusqu'à la ligne 320) pour voir précisément comment `handleSubmit` construit `invoiceData` à partir de `lines`/`selectedPatient`/`note`/etc., et comment il gère `isSaving`/`errorMessage` (props reçues du parent, donc l'appel réseau réel vit probablement dans le parent, pas dans la modale elle-même — à confirmer en lisant, pas à supposer).

- [ ] **Step 3: Ajouter le sélecteur de destinataire et le bouton**

Dans le template, juste avant le bloc des boutons existants (après la ligne du `<div v-if="errorMessage">`) :

```vue
        <div v-if="authStore.hasRole(['secretaire']) && !pendingDiscountRequest" class="border-t pt-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('caisse.invoice_modal.discount_recipient') }}</label>
          <select v-model="selectedManagerId" class="block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option :value="null">{{ t('caisse.invoice_modal.discount_select_placeholder') }}</option>
            <option v-for="m in managers" :key="m.user_id" :value="m.user_id">{{ m.full_name || m.username }}</option>
          </select>
        </div>

        <div v-if="pendingDiscountRequest" class="bg-amber-50 border-l-4 border-amber-500 p-3 rounded text-sm text-amber-800 flex items-center justify-between">
          <span>{{ t('caisse.invoice_modal.pending_approval', { name: pendingDiscountRequest.managerName }) }}</span>
          <button type="button" @click="cancelAndReassign" class="text-xs underline text-amber-900">
            {{ t('caisse.invoice_modal.cancel_reassign') }}
          </button>
        </div>
```

Dans le bloc des boutons existants (après le bouton "Enregistrer" actuel) :

```vue
        <button
          v-if="authStore.hasRole(['secretaire']) && !pendingDiscountRequest"
          type="button"
          @click="handleRequestDiscount"
          :disabled="isSaving || !isFormValid || !selectedManagerId"
          class="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 font-medium shadow-md transition disabled:opacity-50"
        >
          {{ t('caisse.invoice_modal.request_discount') }}
        </button>
```

- [ ] **Step 4: Script**

```javascript
import { useAuthStore } from '@/stores/auth';
import { DiscountRequestGateway } from '@/services/DiscountRequestGateway';

const authStore = useAuthStore();
const managers = ref([]);
const selectedManagerId = ref(null);
const pendingDiscountRequest = ref(null);

onMounted(async () => {
  if (authStore.hasRole(['secretaire'])) {
    try {
      const res = await DiscountRequestGateway.listManagers();
      managers.value = res.data || [];
    } catch (err) {
      console.error('Chargement des managers échoué :', err);
    }
  }
});

const buildInvoiceData = () => ({
  payment_method: paymentMethod.value,
  transaction_type: transactionType.value,
  amount: totalAmount.value,
  advance_amount: advanceAmount.value || 0,
  patient_id: selectedPatient.value?.id || null,
  patient_label: patientLabel.value || selectedPatient.value?.label || null,
  note: note.value,
  items: lines.value.map((l) => ({
    item_type: l.itemType, item_ref_id: l.refId, unit_price: l.unitPrice,
    quantity: l.quantity, line_total: l.unitPrice * l.quantity,
  })),
});

const handleRequestDiscount = async () => {
  try {
    const res = await DiscountRequestGateway.create(buildInvoiceData(), selectedManagerId.value);
    const manager = managers.value.find((m) => m.user_id === selectedManagerId.value);
    pendingDiscountRequest.value = { id: res.data.id, managerName: manager?.full_name || manager?.username };
  } catch (err) {
    console.error('Erreur demande de réduction:', err);
  }
};

const cancelAndReassign = async () => {
  if (!selectedManagerId.value) return;
  await DiscountRequestGateway.cancel(pendingDiscountRequest.value.id, selectedManagerId.value);
  pendingDiscountRequest.value = null;
};
```

Adapter les noms de variables (`paymentMethod`, `transactionType`, `totalAmount`, `advanceAmount`, `patientLabel`) aux vrais noms déjà utilisés dans le fichier (lus en Step 2) — ce sont des noms plausibles déduits du template déjà vu, pas garantis exacts, à vérifier ligne par ligne avant d'écrire `buildInvoiceData`.

- [ ] **Step 5: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert. Ajouter les clés i18n manquantes (`caisse.invoice_modal.discount_recipient`, `discount_select_placeholder`, `pending_approval`, `cancel_reassign`, `request_discount`) dans `src/i18n.js`, blocs `fr`/`en`, si absentes.

---

### Task 11: Frontend — écran de réception manager + montage des layouts + route

**Files:**
- Create: `ah2-admin-web/src/views/modules/caisse/DiscountReview.vue`
- Modify: `ah2-admin-web/src/components/layout/MainLayout.vue`
- Modify: `ah2-admin-web/src/components/layout/SecretaireLayout.vue`
- Modify: `ah2-admin-web/src/router/index.js`

**Interfaces:**
- Consumes: `GET /discount-requests/pending`, `POST /discount-requests/{id}/decide`, `<NotificationBell />` (Task 9).
- Produces: route `discount-review`, référencée par `NotificationBell.vue` (déjà écrit en Task 9 avec `router.push({ name: 'discount-review' })`).

- [ ] **Step 1: `DiscountReview.vue`**

```vue
<!-- src/views/modules/caisse/DiscountReview.vue -->
<template>
  <div class="max-w-3xl mx-auto p-6">
    <h2 class="text-xl font-bold text-gray-800 mb-4">{{ $t('discount_review.title') }}</h2>

    <div v-if="pending.length === 0" class="text-center text-gray-400 py-12">
      {{ $t('discount_review.empty') }}
    </div>

    <div v-for="req in pending" :key="req.id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-4">
      <div class="flex justify-between items-center mb-3">
        <span class="font-bold text-gray-800">{{ formatCurrency(req.original_amount) }}</span>
        <span class="text-xs text-gray-400">{{ formatDate(req.created_at) }}</span>
      </div>

      <div class="grid grid-cols-3 gap-2 mb-3">
        <button
          v-for="pct in [10, 20, 50, 100]"
          :key="pct"
          @click="selectedPercent[req.id] = pct"
          :class="selectedPercent[req.id] === pct ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700'"
          class="py-2 rounded-lg text-sm font-medium"
        >{{ pct }}%</button>
      </div>

      <div class="mb-3">
        <label class="block text-xs text-gray-500 mb-1">{{ $t('discount_review.echelonne_deadline') }}</label>
        <input type="date" v-model="selectedDeadline[req.id]" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
      </div>

      <div class="mb-3">
        <label class="block text-xs text-gray-500 mb-1">{{ $t('discount_review.password_confirm') }}</label>
        <input type="password" v-model="passwordInput[req.id]" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-full" />
      </div>

      <div v-if="errorFor[req.id]" class="text-xs text-red-600 mb-2">{{ errorFor[req.id] }}</div>

      <div class="flex gap-2">
        <button @click="submitDecision(req, false)" class="flex-1 bg-green-600 text-white rounded-lg py-2 font-medium hover:bg-green-700">
          {{ $t('discount_review.approve') }}
        </button>
        <button @click="submitDecision(req, true)" class="flex-1 bg-red-500 text-white rounded-lg py-2 font-medium hover:bg-red-600">
          {{ $t('discount_review.refuse') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '@/services/api';

const pending = ref([]);
const selectedPercent = reactive({});
const selectedDeadline = reactive({});
const passwordInput = reactive({});
const errorFor = reactive({});

const formatCurrency = (v) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(v || 0).replace('XOF', 'FCFA');
const formatDate = (iso) => iso ? new Date(iso).toLocaleString('fr-FR') : '';

const fetchPending = async () => {
  const res = await api.get('/discount-requests/pending');
  pending.value = res.data || [];
};

const submitDecision = async (req, refuse) => {
  errorFor[req.id] = '';
  try {
    await api.post(`/discount-requests/${req.id}/decide`, {
      password: passwordInput[req.id] || '',
      refuse,
      decision_percent: refuse ? null : (selectedPercent[req.id] || null),
      decision_echelonne_deadline: refuse ? null : (selectedDeadline[req.id] || null),
    });
    pending.value = pending.value.filter((r) => r.id !== req.id);
  } catch (err) {
    errorFor[req.id] = err.response?.data?.detail || 'Erreur lors de la décision.';
  }
};

onMounted(fetchPending);
</script>
```

- [ ] **Step 2: Route**

Dans `ah2-admin-web/src/router/index.js`, ajouter une route de haut niveau (pas nécessairement sous `/dashboard/labo` ou un module existant — lire la structure des routes de premier niveau autour de la ligne 29 `/dashboard` pour choisir un emplacement cohérent, probablement un enfant direct de `/dashboard` comme les autres écrans caisse) :

```javascript
{
  path: 'discount-review',
  name: 'discount-review',
  component: () => import('@/views/modules/caisse/DiscountReview.vue'),
  meta: { requiresAuth: true, roles: [ROLES.ADMIN, ROLES.PROMOTEUR] }
},
```

- [ ] **Step 3: Monter `NotificationBell` dans les 2 layouts**

Dans `ah2-admin-web/src/components/layout/MainLayout.vue`, dans le `<header>`, juste avant le bouton `UserCircleIcon` (ligne ~92) :

```vue
          <NotificationBell v-if="authStore.hasRole(['admin', 'promoteur', 'secretaire'])" />
```

Ajouter l'import correspondant dans le `<script setup>` de ce fichier :

```javascript
import NotificationBell from '@/components/notifications/NotificationBell.vue';
```

Répéter la même chose dans `ah2-admin-web/src/components/layout/SecretaireLayout.vue` — lire d'abord ce fichier pour situer son `<header>` (probablement une structure similaire mais pas identique, ne pas supposer les mêmes numéros de ligne) et suivre le même motif d'insertion.

- [ ] **Step 4: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert. Ajouter les clés i18n manquantes (`discount_review.*`) si absentes.

---

### Task 12: Vérification finale — migration réelle (accord requis), non-régression

**Files:**
- Aucun fichier de code — tâche de vérification et de clôture.
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md` (clôture du chantier)

**Interfaces:**
- Consumes: l'ensemble des tâches 1-11.

- [ ] **Step 1: Demander l'accord explicite pour appliquer la migration réelle**

Via `AskUserQuestion` (règle projet immuable) : "Appliquer la migration 013 (`notifications` + `discount_requests`) contre la base AH2 locale ?"

- [ ] **Step 2: Appliquer la migration (uniquement après accord)**

Run: `alembic upgrade head`
Expected: `alembic current` affiche `013_notif_discount`.

- [ ] **Step 3: Tests backend complets**

Run: `pytest tests/ -v -k "notification or discount"`
Expected: tous les tests des Tasks 3-8 PASS.

Run: `pytest tests/ -q`
Expected: aucune régression sur la suite existante (même nombre d'échecs pré-existants documentés qu'avant ce chantier).

- [ ] **Step 4: Test manuel — cycle complet**

Se connecter en `secretaire`. Remplir une facture, cliquer "Demander une réduction", choisir un manager précis. Vérifier que la facture est verrouillée (modification/annulation refusées). Se connecter en `admin`/`promoteur` dans un autre onglet/navigateur. Vérifier la pastille + le popup dans les 30 secondes. Approuver avec 20% + une échéance, avec le bon mot de passe. Vérifier côté secrétaire que la notification retour arrive, que le montant de la facture a bien baissé de 20%, et que l'action apparaît dans le journal d'audit (`SystemLogs.vue` ou équivalent).

- [ ] **Step 5: Test manuel — annuler et réassigner**

Créer une demande vers un manager, l'annuler côté secrétaire, la réassigner à un second manager. Vérifier que le premier manager ne la voit plus dans son écran de réception, et que le second la voit.

- [ ] **Step 6: Test manuel — mot de passe incorrect**

Tenter de valider une décision avec un mauvais mot de passe. Vérifier que rien n'est enregistré (la demande reste `pending`, la facture reste verrouillée).

- [ ] **Step 7: Clôture**

Mettre à jour `docs/superpowers/SUIVI-AVANCEMENT.md` avec un résumé du chantier (nouvelles tables, workflow, garde-fous anti-fraude). Mettre à jour la mémoire auto-générée si pertinent.
