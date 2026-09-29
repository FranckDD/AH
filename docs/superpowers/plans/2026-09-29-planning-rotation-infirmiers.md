# Planning de rotation des infirmiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let médecin (always) and any nurse flagged `is_head_nurse` assign nurses to fixed daily shifts (MATIN/APRES_MIDI/NUIT), with the full team's schedule visible to every médecin/nurse.

**Architecture:** One new boolean column on `users` (`is_head_nurse`, no new role — this project is single-role-per-user, a genuine new role would silently strip existing `nurse` permissions everywhere unless every existing role check were updated) and one new table (`nurse_shifts`, a plain assignment row per date+slot+nurse, DB-unique to prevent an exact duplicate, no cap on how many nurses share a slot). A new backend module (model → repository → controller → FastAPI router) mirrors the existing `hospitalizations` module exactly. `UserUpdate`/`UserCreate`/`UserOut` and `UserModal.vue` gain the new flag as an ordinary field, following the same whitelist pattern every other user field already uses. Frontend: a new Pinia store + gateway, and a month-grid calendar screen built the same way as `AppointmentsCalendar.vue` (2026-09-28) — médecin/nurse only, no offline/PowerSync support.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic (raw-SQL migrations), pytest with real HTTP (`TestClient`) + real Postgres transactions, Vue 3 `<script setup>`, Pinia, vue-i18n, Tailwind, dayjs.

**Spec:** `docs/superpowers/specs/2026-09-29-planning-rotation-infirmiers-design.md`

## Global Constraints

- Pas de nouveau rôle : `users.is_head_nurse` (booléen) est l'unique mécanisme. Le rôle `nurse` de la personne reste inchangé, avec tous ses droits habituels.
- Créneaux fixes, exactement 3 valeurs : `MATIN`, `APRES_MIDI`, `NUIT`.
- Plusieurs infirmiers possibles sur un même (date, créneau) — jamais de limite à un seul.
- Lecture (`GET /nurse-shifts`, `GET /nurse-shifts/nurses`) : `medecin` + `nurse`, tout le monde.
- Écriture (`POST`/`DELETE /nurse-shifts`) : `medecin` toujours ; `nurse` seulement si `is_head_nurse == True` — vérifié par le controller (garde applicative), pas seulement la garde de rôle du routeur.
- Aucun effet sur une garde de rôle existante ailleurs dans le projet — ce chantier n'ajoute une condition qu'à l'intérieur de son propre module.
- Pas de motif récurrent, pas de mode hors ligne pour ce chantier.
- Aucun test automatisé de composant Vue dans ce projet — le frontend se vérifie par build de production + lecture du code.

## Review Focus

- Un infirmier sans `is_head_nurse` qui tente `POST`/`DELETE /nurse-shifts` doit recevoir un refus clair (403), jamais une erreur générique ni un succès silencieux. Testé en Task 5.
- Affecter deux fois le même infirmier au même (date, créneau) doit être refusé (409), jamais un doublon silencieux. Testé en Task 2 et Task 5.
- `shift_type` hors des 3 valeurs autorisées doit être refusé (422). `nurse_id` inexistant ou correspondant à un compte inactif/non-infirmier doit être refusé (404), jamais une violation de contrainte étrangère brute qui fuite en surface. Testé en Task 2 et Task 5.
- Le nouveau champ `is_head_nurse` doit voyager de bout en bout (`UserUpdate` → `UserController.update_user()` → `UserOut` → `UserModal.vue`) sans casser aucun champ déjà whitelisté (`is_active`, `role_id`, etc.) — un test HTTP existant (`tests/test_users_update.py`, motif déjà établi) montre la convention à suivre. Testé en Task 6.
- La case à cocher "Chef infirmier/infirmière" dans `UserModal.vue` doit être invisible et réinitialisée à `false` pour tout rôle autre que `nurse` — un admin qui bascule le rôle d'un compte en cours d'édition ne doit jamais soumettre silencieusement `is_head_nurse: true` sur un compte non-infirmier. Pas de test automatisé possible côté frontend — vérifié par une relecture explicite du garde en Task 9.

---

## Task 1: Migration + modèles SQLAlchemy

**Files:**
- Create: `alembic/versions/016_nurse_shifts.py`
- Create: `models/nurse_shift.py`
- Modify: `models/__init__.py`
- Modify: `models/user.py`
- Modify: `ci/schema_only.sql` (régénéré, pas édité à la main)
- Test: `tests/test_nurse_shift_schema.py`

**Interfaces:**
- Produces: colonne `users.is_head_nurse` (Boolean, `NOT NULL DEFAULT false`) ; table `nurse_shifts` (`id`, `shift_date`, `shift_type`, `nurse_id`, `created_by`, `created_at`) ; index unique partiel-libre `ux_nurse_shifts_no_duplicate` sur `(shift_date, shift_type, nurse_id)`. Modèle SQLAlchemy `NurseShift` (`models/nurse_shift.py`), constante `SHIFT_TYPES` — consommés par Task 2.

- [ ] **Step 1: Écrire la migration Alembic**

```python
# alembic/versions/016_nurse_shifts.py
"""users.is_head_nurse + nurse_shifts

Revision ID: 016_nurse_shifts
Revises: 015_hospitalizations
Create Date: 2026-09-29

"""
from alembic import op

revision = '016_nurse_shifts'
down_revision = '015_hospitalizations'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.users
            ADD COLUMN IF NOT EXISTS is_head_nurse boolean NOT NULL DEFAULT false;

        CREATE TABLE IF NOT EXISTS nurse_shifts (
            id SERIAL PRIMARY KEY,
            shift_date DATE NOT NULL,
            shift_type VARCHAR(20) NOT NULL
                CHECK (shift_type IN ('MATIN', 'APRES_MIDI', 'NUIT')),
            nurse_id INTEGER NOT NULL REFERENCES users(user_id),
            created_by INTEGER NOT NULL REFERENCES users(user_id),
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_nurse_shifts_no_duplicate
            ON nurse_shifts (shift_date, shift_type, nurse_id);
        CREATE INDEX IF NOT EXISTS ix_nurse_shifts_date
            ON nurse_shifts (shift_date);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS nurse_shifts;
        ALTER TABLE public.users DROP COLUMN IF EXISTS is_head_nurse;
    """)
```

- [ ] **Step 2: Appliquer la migration contre la base locale réelle**

```bash
alembic upgrade head
```

Vérifier que `alembic current` affiche bien `016_nurse_shifts (head)`.

- [ ] **Step 3: Écrire le modèle SQLAlchemy**

```python
# models/nurse_shift.py
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

SHIFT_TYPES = ("MATIN", "APRES_MIDI", "NUIT")


class NurseShift(Base):
    __tablename__ = 'nurse_shifts'

    id = Column(Integer, primary_key=True)
    shift_date = Column(Date, nullable=False)
    shift_type = Column(String(20), nullable=False)
    nurse_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    nurse = relationship("User", foreign_keys=[nurse_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
```

- [ ] **Step 4: Enregistrer le modèle dans `models/__init__.py`**

Ajouter, à côté de `from .hospitalization import Hospitalization, HospitalizationStatusUpdate` :

```python
from .nurse_shift import NurseShift
```

- [ ] **Step 5: Ajouter la colonne au modèle `User` existant**

Dans `models/user.py`, ajouter la colonne (à côté de `token_version`) :

```python
    is_head_nurse = Column(Boolean, nullable=False, default=False, server_default="false")
```

`Boolean` est déjà importé dans ce fichier (`from sqlalchemy import Column, Integer, String, Boolean, ForeignKey`) — ne pas ajouter d'import.

- [ ] **Step 6: Écrire un test qui vérifie le schéma réel**

```python
# tests/test_nurse_shift_schema.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import text
from tests.conftest import create_test_user


def test_nurse_shifts_table_has_unique_index(db_session):
    row = db_session.execute(text("""
        SELECT indexdef FROM pg_indexes
        WHERE indexname = 'ux_nurse_shifts_no_duplicate'
    """)).fetchone()
    assert row is not None
    assert "shift_date" in row[0] and "shift_type" in row[0] and "nurse_id" in row[0]


def test_nurse_shifts_shift_type_check_constraint(db_session):
    """La contrainte CHECK sur shift_type doit exister reellement en base,
    pas seulement etre validee cote Pydantic - un vrai infirmier est cree
    d'abord pour que l'echec attendu soit bien celui du CHECK et non une
    violation de cle etrangere sans rapport."""
    nurse = create_test_user(db_session, "schema_test_nurse", "nurse")
    admin = create_test_user(db_session, "schema_test_admin_nsh", "admin")

    with pytest.raises(Exception):
        db_session.execute(text("""
            INSERT INTO nurse_shifts (shift_date, shift_type, nurse_id, created_by)
            VALUES (CURRENT_DATE, 'VALEUR_INVALIDE', :nurse_id, :created_by)
        """), {"nurse_id": nurse.user_id, "created_by": admin.user_id})
        db_session.flush()
    db_session.rollback()


def test_users_is_head_nurse_defaults_false(db_session):
    nurse = create_test_user(db_session, "schema_test_nurse2", "nurse")
    assert nurse.is_head_nurse is False
```

- [ ] **Step 7: Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_nurse_shift_schema.py -v
```

Attendu : 3 passed.

- [ ] **Step 8: Régénérer `ci/schema_only.sql`**

```bash
pg_dump --schema-only --no-owner --no-privileges "$DATABASE_URL" > ci/schema_only.sql
```

Vérifier avec `git diff ci/schema_only.sql` que le diff contient la nouvelle table, le nouvel index, et la nouvelle colonne sur `users` — rien d'inattendu.

- [ ] **Step 9: Commit**

```bash
git add alembic/versions/016_nurse_shifts.py models/nurse_shift.py models/__init__.py models/user.py ci/schema_only.sql tests/test_nurse_shift_schema.py
git commit -m "feat: nurse_shifts schema + users.is_head_nurse flag"
```

---

## Task 2: Repository

**Files:**
- Create: `repositories/nurse_shift_repo.py`
- Test: `tests/test_nurse_shift_repo.py`

**Interfaces:**
- Consumes: `models.nurse_shift.NurseShift`, `SHIFT_TYPES` (Task 1), `models.user.User`, `models.application_role.ApplicationRole` (déjà existants).
- Produces: `NurseShiftRepository(session)` avec `assign(shift_date, shift_type: str, nurse_id: int, created_by_id: int) -> NurseShift`, `remove(shift_id: int) -> None`, `list_for_range(start_date, end_date) -> list[NurseShift]`. Toutes lèvent `ValueError` (jamais une exception SQLAlchemy brute) sur une règle métier violée — consommé par Task 3.

- [ ] **Step 1: Écrire les tests du repository (avant l'implémentation)**

```python
# tests/test_nurse_shift_repo.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
import pytest
from repositories.nurse_shift_repo import NurseShiftRepository
from tests.conftest import create_test_user


def test_assign_creates_shift(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin1", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse1", "nurse")
    repo = NurseShiftRepository(db_session)

    shift = repo.assign(date(2026, 10, 3), "MATIN", nurse.user_id, medecin.user_id)

    assert shift.id is not None
    assert shift.shift_type == "MATIN"
    assert shift.nurse_id == nurse.user_id
    assert shift.created_by == medecin.user_id


def test_assign_allows_multiple_nurses_same_slot(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin2", "medecin")
    nurse1 = create_test_user(db_session, "nsh_repo_nurse2a", "nurse")
    nurse2 = create_test_user(db_session, "nsh_repo_nurse2b", "nurse")
    repo = NurseShiftRepository(db_session)

    repo.assign(date(2026, 10, 4), "NUIT", nurse1.user_id, medecin.user_id)
    repo.assign(date(2026, 10, 4), "NUIT", nurse2.user_id, medecin.user_id)

    shifts = repo.list_for_range(date(2026, 10, 4), date(2026, 10, 4))
    assert len(shifts) == 2


def test_assign_refuses_exact_duplicate(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin3", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse3", "nurse")
    repo = NurseShiftRepository(db_session)
    repo.assign(date(2026, 10, 5), "APRES_MIDI", nurse.user_id, medecin.user_id)

    with pytest.raises(ValueError, match="déjà"):
        repo.assign(date(2026, 10, 5), "APRES_MIDI", nurse.user_id, medecin.user_id)


def test_assign_refuses_invalid_shift_type(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin4", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse4", "nurse")
    repo = NurseShiftRepository(db_session)

    with pytest.raises(ValueError, match="invalide"):
        repo.assign(date(2026, 10, 6), "SOIREE", nurse.user_id, medecin.user_id)


def test_assign_refuses_unknown_nurse(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin5", "medecin")
    repo = NurseShiftRepository(db_session)

    with pytest.raises(ValueError, match="introuvable"):
        repo.assign(date(2026, 10, 7), "MATIN", 999999999, medecin.user_id)


def test_assign_refuses_non_nurse_user(db_session):
    """Un medecin (ou tout autre role) ne peut pas etre affecte comme
    infirmier a un creneau, meme si son user_id est valide."""
    medecin = create_test_user(db_session, "nsh_repo_medecin6", "medecin")
    other_medecin = create_test_user(db_session, "nsh_repo_medecin6b", "medecin")
    repo = NurseShiftRepository(db_session)

    with pytest.raises(ValueError, match="introuvable"):
        repo.assign(date(2026, 10, 8), "MATIN", other_medecin.user_id, medecin.user_id)


def test_remove_deletes_shift(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin7", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse7", "nurse")
    repo = NurseShiftRepository(db_session)
    shift = repo.assign(date(2026, 10, 9), "NUIT", nurse.user_id, medecin.user_id)

    repo.remove(shift.id)

    assert repo.list_for_range(date(2026, 10, 9), date(2026, 10, 9)) == []


def test_remove_refuses_unknown_id(db_session):
    repo = NurseShiftRepository(db_session)
    with pytest.raises(ValueError, match="Aucune affectation"):
        repo.remove(999999999)


def test_list_for_range_filters_by_date(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin8", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse8", "nurse")
    repo = NurseShiftRepository(db_session)
    repo.assign(date(2026, 11, 1), "MATIN", nurse.user_id, medecin.user_id)
    repo.assign(date(2026, 12, 1), "MATIN", nurse.user_id, medecin.user_id)

    november_only = repo.list_for_range(date(2026, 11, 1), date(2026, 11, 30))
    assert len(november_only) == 1
    assert november_only[0].shift_date == date(2026, 11, 1)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

```bash
python -m pytest tests/test_nurse_shift_repo.py -v
```

Attendu : ÉCHEC avec `ModuleNotFoundError: No module named 'repositories.nurse_shift_repo'`.

- [ ] **Step 3: Écrire le repository**

```python
# repositories/nurse_shift_repo.py
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from models.nurse_shift import NurseShift, SHIFT_TYPES
from models.user import User
from models.application_role import ApplicationRole


class NurseShiftRepository:
    def __init__(self, session: Session):
        self.session = session

    def _get_active_nurse(self, nurse_id: int) -> Optional[User]:
        return (
            self.session.query(User)
            .join(ApplicationRole)
            .filter(
                User.user_id == nurse_id,
                ApplicationRole.role_name == "nurse",
                User.is_active == True,
            )
            .first()
        )

    def assign(self, shift_date, shift_type: str, nurse_id: int, created_by_id: int) -> NurseShift:
        if shift_type not in SHIFT_TYPES:
            raise ValueError(f"Créneau invalide : {shift_type}")

        nurse = self._get_active_nurse(nurse_id)
        if nurse is None:
            raise ValueError(f"Infirmier introuvable ou inactif (ID={nurse_id}).")

        existing = (
            self.session.query(NurseShift)
            .filter(
                NurseShift.shift_date == shift_date,
                NurseShift.shift_type == shift_type,
                NurseShift.nurse_id == nurse_id,
            )
            .one_or_none()
        )
        if existing is not None:
            raise ValueError("Cet infirmier est déjà affecté à ce créneau.")

        shift = NurseShift(
            shift_date=shift_date,
            shift_type=shift_type,
            nurse_id=nurse_id,
            created_by=created_by_id,
        )
        self.session.add(shift)
        self.session.commit()
        self.session.refresh(shift)
        return shift

    def remove(self, shift_id: int) -> None:
        shift = self.session.get(NurseShift, shift_id)
        if shift is None:
            raise ValueError(f"Aucune affectation trouvée pour l'ID={shift_id}")
        self.session.delete(shift)
        self.session.commit()

    def list_for_range(self, start_date, end_date) -> List[NurseShift]:
        return (
            self.session.query(NurseShift)
            .options(joinedload(NurseShift.nurse), joinedload(NurseShift.created_by_user))
            .filter(NurseShift.shift_date >= start_date, NurseShift.shift_date <= end_date)
            .order_by(NurseShift.shift_date.asc(), NurseShift.shift_type.asc())
            .all()
        )
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_nurse_shift_repo.py -v
```

Attendu : 9 passed.

- [ ] **Step 5: Commit**

```bash
git add repositories/nurse_shift_repo.py tests/test_nurse_shift_repo.py
git commit -m "feat: NurseShiftRepository (assign/remove/list_for_range)"
```

---

## Task 3: Controller (garde d'accès + audit)

**Files:**
- Create: `controller/nurse_shift_controller.py`
- Test: `tests/test_nurse_shift_controller.py`

**Interfaces:**
- Consumes: `repositories.nurse_shift_repo.NurseShiftRepository` (Task 2), `repositories.user_repo.UserRepository::get_users_by_role_names(role_names: list[str]) -> list[User]` (déjà existant), `repositories.audit_repo.AuditRepository` (déjà existant).
- Produces: `NurseShiftController(repo, user_repo, current_user, audit_repo=None)` avec `assign_shift(shift_date, shift_type, nurse_id) -> NurseShift`, `remove_shift(shift_id) -> None`, `list_shifts(start_date, end_date) -> list[NurseShift]`, `list_active_nurses() -> list[User]` — consommé par Task 4. `assign_shift`/`remove_shift` lèvent `PermissionError` (jamais `ValueError`) si l'appelant n'a pas le droit d'écrire.

- [ ] **Step 1: Écrire les tests du controller (avant l'implémentation)**

```python
# tests/test_nurse_shift_controller.py
import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock
from controller.nurse_shift_controller import NurseShiftController


def _make_user(roles, is_head_nurse=False, user_id=7):
    user = MagicMock(user_id=user_id, is_head_nurse=is_head_nurse)
    user.roles = roles
    return user


def test_medecin_can_assign_shift():
    repo = MagicMock()
    shift = MagicMock(id=1)
    repo.assign.return_value = shift
    user = _make_user(["medecin"])

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user, audit_repo=MagicMock())
    result = ctrl.assign_shift("2026-10-03", "MATIN", 5)

    assert result is shift
    repo.assign.assert_called_once_with("2026-10-03", "MATIN", 5, 7)


def test_head_nurse_can_assign_shift():
    repo = MagicMock()
    repo.assign.return_value = MagicMock(id=1)
    user = _make_user(["nurse"], is_head_nurse=True)

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user)
    ctrl.assign_shift("2026-10-03", "MATIN", 5)

    repo.assign.assert_called_once()


def test_plain_nurse_cannot_assign_shift():
    repo = MagicMock()
    user = _make_user(["nurse"], is_head_nurse=False)

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user)

    with pytest.raises(PermissionError):
        ctrl.assign_shift("2026-10-03", "MATIN", 5)
    repo.assign.assert_not_called()


def test_plain_nurse_cannot_remove_shift():
    repo = MagicMock()
    user = _make_user(["nurse"], is_head_nurse=False)

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user)

    with pytest.raises(PermissionError):
        ctrl.remove_shift(42)
    repo.remove.assert_not_called()


def test_assign_shift_logs_audit_entry():
    repo = MagicMock()
    repo.assign.return_value = MagicMock(id=42)
    user = _make_user(["medecin"])
    audit_repo = MagicMock()

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user, audit_repo=audit_repo)
    ctrl.assign_shift("2026-10-03", "MATIN", 5)

    audit_repo.log_user_action.assert_called_once()
    kwargs = audit_repo.log_user_action.call_args.kwargs
    assert kwargs["resource_type"] == "NurseShift"
    assert kwargs["action_performed"] == "ASSIGN"


def test_controller_logs_when_audit_fails(caplog):
    repo = MagicMock()
    repo.assign.return_value = MagicMock(id=1)
    user = _make_user(["medecin"])
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.assign_shift("2026-10-03", "MATIN", 5)

    assert result is not None
    assert any("audit" in r.message.lower() for r in caplog.records)


def test_list_shifts_delegates_to_repo():
    repo = MagicMock()
    repo.list_for_range.return_value = ["a", "b"]
    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=_make_user(["nurse"]))

    assert ctrl.list_shifts("2026-10-01", "2026-10-31") == ["a", "b"]
    repo.list_for_range.assert_called_once_with("2026-10-01", "2026-10-31")


def test_list_active_nurses_delegates_to_user_repo():
    user_repo = MagicMock()
    user_repo.get_users_by_role_names.return_value = ["nurse1", "nurse2"]
    ctrl = NurseShiftController(repo=MagicMock(), user_repo=user_repo, current_user=_make_user(["medecin"]))

    assert ctrl.list_active_nurses() == ["nurse1", "nurse2"]
    user_repo.get_users_by_role_names.assert_called_once_with(["nurse"])
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

```bash
python -m pytest tests/test_nurse_shift_controller.py -v
```

Attendu : ÉCHEC avec `ModuleNotFoundError: No module named 'controller.nurse_shift_controller'`.

- [ ] **Step 3: Écrire le controller**

```python
# controller/nurse_shift_controller.py
import logging
from typing import Optional, List

from repositories.nurse_shift_repo import NurseShiftRepository
from repositories.user_repo import UserRepository
from repositories.audit_repo import AuditRepository


class NurseShiftController:
    def __init__(
        self,
        repo: NurseShiftRepository,
        user_repo: UserRepository,
        current_user,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.repo = repo
        self.user_repo = user_repo
        self.user = current_user
        self.audit_repo = audit_repo
        self.logger = logging.getLogger(__name__)

    def _ensure_can_manage_schedule(self):
        roles = getattr(self.user, "roles", []) or []
        if "medecin" in roles:
            return
        if "nurse" in roles and getattr(self.user, "is_head_nurse", False):
            return
        raise PermissionError(
            "Seuls le médecin ou le chef infirmier/infirmière peuvent modifier le planning."
        )

    def _log_audit(self, action_performed: str, resource_id: int, details: Optional[str] = None):
        if not (self.audit_repo and self.user):
            return
        try:
            self.audit_repo.log_user_action(
                current_user=self.user,
                resource_type="NurseShift",
                action_performed=action_performed,
                resource_id=resource_id,
                details=details,
            )
        except Exception:
            self.logger.exception("Échec de l'écriture d'audit")

    def assign_shift(self, shift_date, shift_type: str, nurse_id: int):
        self._ensure_can_manage_schedule()
        shift = self.repo.assign(shift_date, shift_type, nurse_id, self.user.user_id)
        self._log_audit("ASSIGN", shift.id, details=f"{shift_type} {shift_date} -> nurse {nurse_id}")
        return shift

    def remove_shift(self, shift_id: int):
        self._ensure_can_manage_schedule()
        self.repo.remove(shift_id)
        self._log_audit("REMOVE", shift_id)

    def list_shifts(self, start_date, end_date) -> List:
        return self.repo.list_for_range(start_date, end_date)

    def list_active_nurses(self) -> List:
        return self.user_repo.get_users_by_role_names(["nurse"])
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_nurse_shift_controller.py -v
```

Attendu : 8 passed.

- [ ] **Step 5: Commit**

```bash
git add controller/nurse_shift_controller.py tests/test_nurse_shift_controller.py
git commit -m "feat: NurseShiftController (permission gate + audit logging)"
```

---

## Task 4: Schémas Pydantic + routeur FastAPI + enregistrement

**Files:**
- Create: `api_backend/backend_app/routes/nurse_shifts/__init__.py`
- Create: `api_backend/backend_app/routes/nurse_shifts/schemas.py`
- Create: `api_backend/backend_app/routes/nurse_shifts/nurse_shift_endpoint.py`
- Modify: `api_backend/backend_app/main.py`

**Interfaces:**
- Consumes: `controller.nurse_shift_controller.NurseShiftController` (Task 3).
- Produces: routeur monté sur `/nurse-shifts`, endpoints `POST /`, `DELETE /{shift_id}`, `GET /`, `GET /nurses` — consommé par Task 5 (tests HTTP) et le frontend (Task 7).

- [ ] **Step 1: Créer le fichier vide de package**

```python
# api_backend/backend_app/routes/nurse_shifts/__init__.py
```

- [ ] **Step 2: Écrire les schémas Pydantic**

```python
# api_backend/backend_app/routes/nurse_shifts/schemas.py
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field


class NurseShiftCreate(BaseModel):
    shift_date: date
    shift_type: str = Field(..., description="MATIN | APRES_MIDI | NUIT")
    nurse_id: int


class NurseShiftOut(BaseModel):
    id: int
    shift_date: date
    shift_type: str
    nurse_id: int
    nurse_name: Optional[str] = None
    created_by: int
    created_by_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActiveNurseOut(BaseModel):
    user_id: int
    full_name: str
    is_head_nurse: bool
```

- [ ] **Step 3: Écrire le routeur**

```python
# api_backend/backend_app/routes/nurse_shifts/nurse_shift_endpoint.py
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .schemas import NurseShiftCreate, NurseShiftOut, ActiveNurseOut
from ...database import SessionLocal
from controller.nurse_shift_controller import NurseShiftController
from repositories.nurse_shift_repo import NurseShiftRepository
from repositories.user_repo import UserRepository
from repositories.audit_repo import AuditRepository
from models.nurse_shift import SHIFT_TYPES
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nurse-shifts", tags=["Planning infirmiers"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_nurse_shift_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NurseShiftController:
    repo = NurseShiftRepository(db)
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    return NurseShiftController(repo=repo, user_repo=user_repo, current_user=current_user, audit_repo=audit_repo)


def _user_name(user) -> str:
    if not user:
        return "Inconnu"
    return getattr(user, "full_name", None) or getattr(user, "username", None) or "Inconnu"


def _to_out(shift) -> NurseShiftOut:
    return NurseShiftOut(
        id=shift.id,
        shift_date=shift.shift_date,
        shift_type=shift.shift_type,
        nurse_id=shift.nurse_id,
        nurse_name=_user_name(getattr(shift, "nurse", None)),
        created_by=shift.created_by,
        created_by_name=_user_name(getattr(shift, "created_by_user", None)),
        created_at=shift.created_at,
    )


@router.post(
    "/",
    response_model=NurseShiftOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def create_shift(data: NurseShiftCreate, ctrl: NurseShiftController = Depends(get_nurse_shift_controller)):
    if data.shift_type not in SHIFT_TYPES:
        raise HTTPException(status_code=422, detail="Créneau invalide.")
    try:
        shift = ctrl.assign_shift(data.shift_date, data.shift_type, data.nurse_id)
        return _to_out(shift)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        if "introuvable" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=409, detail=str(ve))
    except IntegrityError:
        logger.exception("Conflit base de donnees a l'affectation")
        raise HTTPException(status_code=409, detail="Cet infirmier est déjà affecté à ce créneau.")


@router.delete(
    "/{shift_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def delete_shift(shift_id: int, ctrl: NurseShiftController = Depends(get_nurse_shift_controller)):
    try:
        ctrl.remove_shift(shift_id)
        return None
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get(
    "/",
    response_model=list[NurseShiftOut],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def list_shifts(
    start: date = Query(...),
    end: date = Query(...),
    ctrl: NurseShiftController = Depends(get_nurse_shift_controller),
):
    return [_to_out(s) for s in ctrl.list_shifts(start, end)]


@router.get(
    "/nurses",
    response_model=list[ActiveNurseOut],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def list_nurses(ctrl: NurseShiftController = Depends(get_nurse_shift_controller)):
    return [
        ActiveNurseOut(user_id=u.user_id, full_name=u.full_name, is_head_nurse=bool(u.is_head_nurse))
        for u in ctrl.list_active_nurses()
    ]
```

- [ ] **Step 4: Enregistrer le routeur dans `main.py`**

Ajouter l'import, à côté de `from .routes.hospitalizations import hospitalization_endpoint` :

```python
from .routes.nurse_shifts import nurse_shift_endpoint
```

Ajouter l'enregistrement, à côté de `app.include_router(hospitalization_endpoint.router)` :

```python
app.include_router(nurse_shift_endpoint.router)
```

- [ ] **Step 5: Vérifier que l'application démarre toujours**

```bash
python -c "from api_backend.backend_app.main import app; print('OK', len(app.routes))"
```

Attendu : `OK <nombre>` sans traceback.

- [ ] **Step 6: Commit**

```bash
git add api_backend/backend_app/routes/nurse_shifts/ api_backend/backend_app/main.py
git commit -m "feat: POST/GET/DELETE /nurse-shifts endpoints"
```

---

## Task 5: Tests d'intégration HTTP complets

**Files:**
- Create: `tests/test_nurse_shifts_endpoints.py`

**Interfaces:**
- Consumes: routeur de Task 4, `tests/conftest.py` (`api_client`, `auth_headers`, `create_test_user`, `db_session`).

- [ ] **Step 1: Écrire les tests HTTP (Review Focus inclus : infirmier non-chef refusé, doublon, valeurs invalides)**

```python
# tests/test_nurse_shifts_endpoints.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.nurse_shifts import nurse_shift_endpoint
from tests.conftest import create_test_user, auth_headers

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, nurse_shift_endpoint)


def test_medecin_can_create_and_list_shift(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin1", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse1", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin1", TEST_PASSWORD)

    resp = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-10",
        "shift_type": "MATIN",
        "nurse_id": nurse.user_id,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["nurse_name"] == nurse.full_name
    assert body["created_by_name"] == medecin.full_name

    listed = client.get("/nurse-shifts/?start=2026-10-10&end=2026-10-10", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_head_nurse_can_create_shift(db_session, api_client):
    head_nurse = create_test_user(db_session, "nsh_ep_headnurse1", "nurse", password=TEST_PASSWORD)
    head_nurse.is_head_nurse = True
    db_session.flush()
    other_nurse = create_test_user(db_session, "nsh_ep_nurse2", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_headnurse1", TEST_PASSWORD)

    resp = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-11",
        "shift_type": "NUIT",
        "nurse_id": other_nurse.user_id,
    }, headers=headers)

    assert resp.status_code == 201, resp.text


def test_plain_nurse_forbidden_to_create_or_delete_shift(db_session, api_client):
    """Review Focus : un infirmier sans is_head_nurse doit etre refuse
    clairement (403), jamais un succes silencieux."""
    medecin = create_test_user(db_session, "nsh_ep_medecin2", "medecin", password=TEST_PASSWORD)
    plain_nurse = create_test_user(db_session, "nsh_ep_plainnurse", "nurse", password=TEST_PASSWORD)
    target_nurse = create_test_user(db_session, "nsh_ep_nurse3", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    medecin_headers = auth_headers(client, "nsh_ep_medecin2", TEST_PASSWORD)
    plain_headers = auth_headers(client, "nsh_ep_plainnurse", TEST_PASSWORD)

    create_resp = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-12",
        "shift_type": "MATIN",
        "nurse_id": plain_nurse.user_id,
    }, headers=plain_headers)
    assert create_resp.status_code == 403

    existing_id = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-12",
        "shift_type": "APRES_MIDI",
        "nurse_id": target_nurse.user_id,
    }, headers=medecin_headers).json()["id"]

    delete_resp = client.delete(f"/nurse-shifts/{existing_id}", headers=plain_headers)
    assert delete_resp.status_code == 403


def test_create_shift_refuses_duplicate(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin3", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse4", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin3", TEST_PASSWORD)
    payload = {"shift_date": "2026-10-13", "shift_type": "NUIT", "nurse_id": nurse.user_id}

    assert client.post("/nurse-shifts/", json=payload, headers=headers).status_code == 201
    resp = client.post("/nurse-shifts/", json=payload, headers=headers)
    assert resp.status_code == 409


def test_create_shift_validates_shift_type_and_nurse_id(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin4", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse5", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin4", TEST_PASSWORD)

    bad_type = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-14", "shift_type": "SOIREE", "nurse_id": nurse.user_id,
    }, headers=headers)
    assert bad_type.status_code == 422

    bad_nurse = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-14", "shift_type": "MATIN", "nurse_id": 999999999,
    }, headers=headers)
    assert bad_nurse.status_code == 404


def test_delete_unknown_shift_returns_404(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin5", "medecin", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin5", TEST_PASSWORD)

    resp = client.delete("/nurse-shifts/999999999", headers=headers)
    assert resp.status_code == 404


def test_list_shifts_shows_multiple_nurses_same_slot(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin6", "medecin", password=TEST_PASSWORD)
    nurse1 = create_test_user(db_session, "nsh_ep_nurse6a", "nurse", password=TEST_PASSWORD)
    nurse2 = create_test_user(db_session, "nsh_ep_nurse6b", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin6", TEST_PASSWORD)

    for nurse in (nurse1, nurse2):
        client.post("/nurse-shifts/", json={
            "shift_date": "2026-10-15", "shift_type": "MATIN", "nurse_id": nurse.user_id,
        }, headers=headers)

    resp = client.get("/nurse-shifts/?start=2026-10-15&end=2026-10-15", headers=headers)
    assert len(resp.json()) == 2


def test_secretaire_forbidden_on_read_and_write(db_session, api_client):
    create_test_user(db_session, "nsh_ep_secretaire1", "secretaire", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "nsh_ep_medecin7", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse7", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_secretaire1", TEST_PASSWORD)

    assert client.get("/nurse-shifts/?start=2026-10-01&end=2026-10-31", headers=headers).status_code == 403
    assert client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-16", "shift_type": "MATIN", "nurse_id": nurse.user_id,
    }, headers=headers).status_code == 403


def test_list_nurses_returns_only_active_nurses(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin8", "medecin", password=TEST_PASSWORD)
    active_nurse = create_test_user(db_session, "nsh_ep_activenurse", "nurse", password=TEST_PASSWORD)
    create_test_user(db_session, "nsh_ep_inactivenurse", "nurse", password=TEST_PASSWORD, is_active=False)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin8", TEST_PASSWORD)

    resp = client.get("/nurse-shifts/nurses", headers=headers)
    assert resp.status_code == 200
    usernames = {n["user_id"] for n in resp.json()}
    assert active_nurse.user_id in usernames


def test_assign_and_remove_write_audit_entries(db_session, api_client):
    from models.audit import AuditUserAction

    medecin = create_test_user(db_session, "nsh_ep_medecin9", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse9", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin9", TEST_PASSWORD)

    shift_id = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-17", "shift_type": "MATIN", "nurse_id": nurse.user_id,
    }, headers=headers).json()["id"]
    client.delete(f"/nurse-shifts/{shift_id}", headers=headers)

    entries = (
        db_session.query(AuditUserAction)
        .filter(AuditUserAction.resource_type == "NurseShift", AuditUserAction.resource_id == shift_id)
        .all()
    )
    actions = {e.action_performed for e in entries}
    assert "ASSIGN" in actions
    assert "REMOVE" in actions
```

- [ ] **Step 2: Lancer la suite complète des tests du planning**

```bash
python -m pytest tests/test_nurse_shift_schema.py tests/test_nurse_shift_repo.py tests/test_nurse_shift_controller.py tests/test_nurse_shifts_endpoints.py -v
```

Attendu : tout passe (3 + 9 + 8 + 11 = 31 tests).

- [ ] **Step 3: Lancer la suite complète du backend pour vérifier l'absence de régression**

```bash
python -m pytest tests/ -q
```

Attendu : les mêmes échecs préexistants déjà documentés (caisse/prescriptions, sans rapport), aucun nouveau.

- [ ] **Step 4: Commit**

```bash
git add tests/test_nurse_shifts_endpoints.py
git commit -m "test: full HTTP coverage for nurse-shifts (permission gate, conflicts, audit)"
```

---

## Task 6: `is_head_nurse` sur la gestion des comptes (backend)

**Files:**
- Modify: `api_backend/backend_app/routes/admin/users_schemas.py`
- Modify: `api_backend/backend_app/routes/admin/mapping.py`
- Modify: `controller/user_controller.py`
- Test: `tests/test_users_update.py`

**Interfaces:**
- Consumes: `users.is_head_nurse` (Task 1).
- Produces: `UserUpdate.is_head_nurse: Optional[bool]`, `UserCreate.is_head_nurse: Optional[bool]`, `UserOut.is_head_nurse: bool` — consommés par Task 9 (`UserModal.vue`/`userStore.js`).

- [ ] **Step 1: Ajouter le champ aux schémas**

Dans `api_backend/backend_app/routes/admin/users_schemas.py`, ajouter `is_head_nurse: Optional[bool] = None` à `UserCreate` (à côté de `full_name`) et à `UserUpdate` (à côté de `is_active`). Ajouter `is_head_nurse: bool = False` à `UserOut` (à côté de `is_active`, avant `roles`).

- [ ] **Step 2: Inclure le champ dans la normalisation de sortie**

Dans `api_backend/backend_app/routes/admin/mapping.py::normalize_user_data`, ajouter au dict `out` (à côté de `"is_active": get_field(raw, "is_active"),`) :

```python
        "is_head_nurse": get_field(raw, "is_head_nurse") or False,
```

- [ ] **Step 3: Ajouter le champ à la whitelist de mise à jour**

Dans `controller/user_controller.py::update_user`, ajouter `'is_head_nurse'` au tuple existant :

```python
        for field in ('full_name','email', 'contact','postgres_role','is_active','role_id','specialty_id','is_head_nurse'):
```

- [ ] **Step 4: Écrire un test HTTP bout-en-bout**

Ajouter à `tests/test_users_update.py` (le fichier importe déjà `create_test_user`, `auth_headers`, `auth_endpoints`, `users_endpoint`) :

```python
def test_update_user_sets_is_head_nurse_without_breaking_other_fields(db_session, api_client):
    """Review Focus : le nouveau champ doit voyager de bout en bout sans
    casser un champ deja whiteliste (is_active reste modifiable dans le
    meme appel)."""
    admin = create_test_user(db_session, "nsh_admin_headnurse", "admin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_target_headnurse", "nurse", password=TEST_PASSWORD)

    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "nsh_admin_headnurse", TEST_PASSWORD)

    resp = client.put(f"/users/{nurse.user_id}", json={
        "is_head_nurse": True,
        "is_active": True,
    }, headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_head_nurse"] is True
    assert body["is_active"] is True
```

- [ ] **Step 5: Lancer les tests**

```bash
python -m pytest tests/test_users_update.py -v
```

Attendu : tout passe (le test préexistant + le nouveau).

- [ ] **Step 6: Commit**

```bash
git add api_backend/backend_app/routes/admin/users_schemas.py api_backend/backend_app/routes/admin/mapping.py controller/user_controller.py tests/test_users_update.py
git commit -m "feat: expose users.is_head_nurse through the user management API"
```

---

## Task 7: Frontend — Gateway + Store

**Files:**
- Create: `ah2-admin-web/src/services/NurseShiftGateway.js`
- Create: `ah2-admin-web/src/stores/nurseShiftStore.js`

**Interfaces:**
- Consumes: endpoints de Task 4.
- Produces: `NurseShiftGateway` (`fetchShifts`, `fetchActiveNurses`, `createShift`, `deleteShift`) et `useNurseShiftStore()` (state `shifts`, `activeNurses`, `isLoading`, `error`, actions `fetchShifts(start, end)`, `fetchActiveNurses()`, `createShift(shiftDate, shiftType, nurseId)`, `deleteShift(shiftId, start, end)`) — consommé par Task 10.

- [ ] **Step 1: Écrire le gateway**

```javascript
// src/services/NurseShiftGateway.js
import api from '@/services/api';

export const NurseShiftGateway = {
    async fetchShifts(start, end) {
        return api.get('/nurse-shifts/', { params: { start, end } });
    },

    async fetchActiveNurses() {
        return api.get('/nurse-shifts/nurses');
    },

    async createShift(shiftDate, shiftType, nurseId) {
        return api.post('/nurse-shifts/', {
            shift_date: shiftDate,
            shift_type: shiftType,
            nurse_id: nurseId,
        });
    },

    async deleteShift(shiftId) {
        return api.delete(`/nurse-shifts/${shiftId}`);
    },
};
```

- [ ] **Step 2: Écrire le store**

```javascript
// src/stores/nurseShiftStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { NurseShiftGateway } from '@/services/NurseShiftGateway';

// Les 3 seuls creneaux reellement acceptes par le backend (CHECK
// constraint + validation Pydantic, voir schemas.py) - ne pas en ajouter
// ici sans les ajouter aussi cote backend.
export const SHIFT_TYPES = ['MATIN', 'APRES_MIDI', 'NUIT'];

export const useNurseShiftStore = defineStore('nurseShift', () => {
    const shifts = ref([]);
    const activeNurses = ref([]);
    const isLoading = ref(false);
    const error = ref(null);

    async function fetchShifts(start, end) {
        isLoading.value = true;
        error.value = null;
        try {
            const resp = await NurseShiftGateway.fetchShifts(start, end);
            shifts.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement planning infirmiers:', err);
            error.value = "Impossible de charger le planning.";
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchActiveNurses() {
        try {
            const resp = await NurseShiftGateway.fetchActiveNurses();
            activeNurses.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement liste infirmiers:', err);
            activeNurses.value = [];
        }
    }

    async function createShift(shiftDate, shiftType, nurseId, start, end) {
        await NurseShiftGateway.createShift(shiftDate, shiftType, nurseId);
        await fetchShifts(start, end);
    }

    async function deleteShift(shiftId, start, end) {
        await NurseShiftGateway.deleteShift(shiftId);
        await fetchShifts(start, end);
    }

    return {
        shifts,
        activeNurses,
        isLoading,
        error,
        fetchShifts,
        fetchActiveNurses,
        createShift,
        deleteShift,
    };
});
```

- [ ] **Step 3: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, aucune erreur.

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/services/NurseShiftGateway.js ah2-admin-web/src/stores/nurseShiftStore.js
git commit -m "feat: NurseShiftGateway + nurseShiftStore"
```

---

## Task 8: i18n

**Files:**
- Modify: `ah2-admin-web/src/i18n.js`

**Interfaces:**
- Produces: clés `nurseShift.*` (FR + EN), consommées par Task 9, 10.

- [ ] **Step 1: Ajouter les clés FR**

Dans le bloc de messages FR (à côté du bloc `hospitalization: { ... }`), ajouter :

```javascript
    nurseShift: {
      title: "Planning infirmiers",
      subtitle: "Rotation de l'équipe (matin / après-midi / nuit)",
      today: "Aujourd'hui",
      shift: {
        MATIN: "Matin",
        APRES_MIDI: "Après-midi",
        NUIT: "Nuit"
      },
      day_panel_title: "Planning du",
      add_nurse: "Ajouter un infirmier",
      select_nurse: "Choisir un infirmier",
      remove: "Retirer",
      no_assignment: "Aucun infirmier assigné.",
      read_only_note: "Seuls le médecin ou le chef infirmier/infirmière peuvent modifier ce planning.",
      head_nurse_badge: "Chef infirmier/infirmière"
    },
```

- [ ] **Step 2: Ajouter les clés EN**

Dans le bloc de messages EN (à côté du bloc `hospitalization: { ... }` en anglais), ajouter :

```javascript
    nurseShift: {
      title: "Nurse Schedule",
      subtitle: "Team rotation (morning / afternoon / night)",
      today: "Today",
      shift: {
        MATIN: "Morning",
        APRES_MIDI: "Afternoon",
        NUIT: "Night"
      },
      day_panel_title: "Schedule for",
      add_nurse: "Add a nurse",
      select_nurse: "Select a nurse",
      remove: "Remove",
      no_assignment: "No nurse assigned.",
      read_only_note: "Only the physician or the head nurse can edit this schedule.",
      head_nurse_badge: "Head nurse"
    },
```

- [ ] **Step 3: Ajouter la clé du formulaire utilisateur (case à cocher)**

Dans le bloc FR `users: { modal: { ... } }`, ajouter à côté d'`is_active` :

```javascript
        is_head_nurse: "Chef infirmier/infirmière",
```

Dans le bloc EN équivalent :

```javascript
        is_head_nurse: "Head nurse",
```

(Repérer l'emplacement exact en cherchant `is_active:` à l'intérieur du bloc `users.modal` déjà existant, dans les deux langues.)

- [ ] **Step 4: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, aucune erreur.

- [ ] **Step 5: Commit**

```bash
git add ah2-admin-web/src/i18n.js
git commit -m "i18n: nurse-shift strings + user modal head-nurse label (FR/EN)"
```

---

## Task 9: Case à cocher "Chef infirmier/infirmière" dans `UserModal.vue`

**Files:**
- Modify: `ah2-admin-web/src/components/users/UserModal.vue`
- Modify: `ah2-admin-web/src/stores/userStore.js`

**Interfaces:**
- Consumes: `is_head_nurse` (Task 6).

- [ ] **Step 1: Ajouter le champ au formulaire réactif**

Dans `form = reactive({ ... })`, ajouter `is_head_nurse: false` à côté de `is_active: true`.

- [ ] **Step 2: Ajouter un computed pour la visibilité conditionnelle**

À côté de `showSpecialtyField`, ajouter :

```javascript
const showHeadNurseField = computed(() => {
  const selectedRole = props.applicationRoles.find(
    (r) => (r.id === form.role_id) || (r.role_id === form.role_id)
  )
  if (!selectedRole) return false
  return (selectedRole.role_name || '').toLowerCase().trim() === 'nurse'
})
```

- [ ] **Step 3: Réinitialiser le champ quand le rôle change vers autre chose que `nurse`**

Modifier `handleRoleChange` :

```javascript
const handleRoleChange = () => {
  if (!showSpecialtyField.value) {
    form.specialty_id = null
  }
  if (!showHeadNurseField.value) {
    form.is_head_nurse = false
  }
}
```

- [ ] **Step 4: Ajouter la case à cocher dans le template**

Juste après le bloc `<div v-if="showSpecialtyField" ...>` (avant la fermeture du conteneur `Habilitations`), ajouter :

```html
              <div v-if="showHeadNurseField" class="animate-fade-in-down">
                <label class="inline-flex items-center cursor-pointer">
                  <input type="checkbox" v-model="form.is_head_nurse" class="sr-only peer">
                  <div class="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                  <span class="ms-3 text-sm font-medium text-gray-900">{{ t('users.modal.is_head_nurse') }}</span>
                </label>
              </div>
```

- [ ] **Step 5: Initialiser le champ en mode édition**

Dans `onMounted`, ajouter `is_head_nurse: u.is_head_nurse || false` à l'objet passé à `Object.assign(form, { ... })`.

- [ ] **Step 6: Vérifier explicitement le garde (Review Focus)**

Relire le fichier modifié et confirmer par la lecture (pas seulement le build) que :
1. `showHeadNurseField` retourne bien `false` pour tout rôle autre que `nurse`.
2. `handleRoleChange` remet bien `form.is_head_nurse` à `false` dès que `showHeadNurseField` devient faux — un admin qui bascule le rôle d'un compte de `nurse` vers autre chose en cours d'édition ne soumettra jamais silencieusement `is_head_nurse: true`.

- [ ] **Step 7: Propager le champ dans `userStore.js`**

Dans `ah2-admin-web/src/stores/userStore.js`, ajouter `is_head_nurse: formData.is_head_nurse` au `payload` de `addUser` ET de `updateUser` (à côté de `is_active: formData.is_active`).

Dans le mapping de `fetchUsers` (le `.map(u => { ... return { ... } })`), ajouter `isHeadNurse: u.is_head_nurse || false` à côté de `isActive: u.is_active,` — pas strictement nécessaire pour ce chantier (aucun affichage dans le tableau n'est demandé), mais évite que l'information soit silencieusement perdue si un futur écran veut l'afficher.

- [ ] **Step 8: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, aucune erreur.

- [ ] **Step 9: Commit**

```bash
git add ah2-admin-web/src/components/users/UserModal.vue ah2-admin-web/src/stores/userStore.js
git commit -m "feat: head-nurse checkbox in user management (visible for nurse role only)"
```

---

## Task 10: Écran calendrier `/medical/nurse-shifts`

**Files:**
- Create: `ah2-admin-web/src/components/nurseshift/NurseShiftCalendar.vue`
- Create: `ah2-admin-web/src/components/nurseshift/NurseShiftDayPanel.vue`
- Create: `ah2-admin-web/src/views/modules/nurseshift/NurseShiftsView.vue`
- Modify: `ah2-admin-web/src/router/index.js`
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue`

**Interfaces:**
- Consumes: `useNurseShiftStore()` (Task 7).

- [ ] **Step 1: Écrire la grille mensuelle (même construction que `AppointmentsCalendar.vue`, 2026-09-28)**

```vue
<!-- ah2-admin-web/src/components/nurseshift/NurseShiftCalendar.vue -->
<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

    <div class="p-4 border-b border-gray-100 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <button @click="goToPreviousMonth" class="p-2 rounded-lg hover:bg-gray-100 transition">
          <ChevronLeftIcon class="h-5 w-5 text-gray-500" />
        </button>
        <h2 class="text-lg font-bold text-gray-800 w-40 text-center capitalize">{{ monthLabel }}</h2>
        <button @click="goToNextMonth" class="p-2 rounded-lg hover:bg-gray-100 transition">
          <ChevronRightIcon class="h-5 w-5 text-gray-500" />
        </button>
      </div>
      <button @click="goToToday" class="px-4 py-1.5 text-sm font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition">
        {{ t('nurseShift.today') }}
      </button>
    </div>

    <div class="grid grid-cols-7 border-b border-gray-100 bg-gray-50">
      <div v-for="label in weekdayLabels" :key="label" class="px-2 py-2 text-center text-xs font-semibold text-gray-500 uppercase">
        {{ label }}
      </div>
    </div>

    <div class="grid grid-cols-7">
      <button
        v-for="day in daysGrid"
        :key="day.dateStr"
        type="button"
        @click="$emit('day-click', day.dateStr)"
        class="min-h-[7rem] border-b border-r border-gray-100 p-2 text-left align-top hover:bg-gray-50 transition focus:outline-none focus:bg-emerald-50/50"
        :class="{
          'bg-gray-50/60 text-gray-400': !day.inCurrentMonth,
          'ring-2 ring-inset ring-emerald-500': day.isToday,
        }"
      >
        <div class="text-xs font-semibold mb-1" :class="day.isToday ? 'text-emerald-700' : ''">
          {{ day.dayOfMonth }}
        </div>
        <div class="space-y-0.5">
          <div v-for="st in SHIFT_TYPES" :key="st" class="text-[10px] leading-tight truncate">
            <span class="text-gray-400">{{ t(`nurseShift.shift.${st}`) }}:</span>
            <span v-if="day.nursesByShift[st].length" class="text-gray-700"> {{ day.nursesByShift[st].join(', ') }}</span>
            <span v-else class="text-gray-300"> —</span>
          </div>
        </div>
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import 'dayjs/locale/fr';
import { SHIFT_TYPES } from '@/stores/nurseShiftStore';

const { t, locale } = useI18n();

const props = defineProps({
  shifts: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(['day-click', 'month-change']);

watch(locale, (lang) => dayjs.locale(lang === 'en' ? 'en' : 'fr'), { immediate: true });

const currentMonth = ref(dayjs().startOf('month'));

const monthLabel = computed(() => currentMonth.value.format('MMMM YYYY'));
const weekdayLabels = computed(() =>
  locale.value === 'en'
    ? ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    : ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
);

function emitMonthRange() {
  emit('month-change', {
    start: currentMonth.value.startOf('month').format('YYYY-MM-DD'),
    end: currentMonth.value.endOf('month').format('YYYY-MM-DD'),
  });
}

function goToPreviousMonth() {
  currentMonth.value = currentMonth.value.subtract(1, 'month');
  emitMonthRange();
}
function goToNextMonth() {
  currentMonth.value = currentMonth.value.add(1, 'month');
  emitMonthRange();
}
function goToToday() {
  currentMonth.value = dayjs().startOf('month');
  emitMonthRange();
}

const shiftsByDate = computed(() => {
  const map = new Map();
  for (const s of props.shifts) {
    if (!map.has(s.shift_date)) map.set(s.shift_date, []);
    map.get(s.shift_date).push(s);
  }
  return map;
});

const daysGrid = computed(() => {
  const monthStart = currentMonth.value;
  const monthEnd = monthStart.endOf('month');
  const startOffset = (monthStart.day() + 6) % 7;
  const endOffset = (6 - ((monthEnd.day() + 6) % 7));
  const gridStart = monthStart.subtract(startOffset, 'day');
  const gridEnd = monthEnd.add(endOffset, 'day');

  const today = dayjs().format('YYYY-MM-DD');
  const days = [];
  let cursor = gridStart;
  while (!cursor.isAfter(gridEnd, 'day')) {
    const dateStr = cursor.format('YYYY-MM-DD');
    const dayShifts = shiftsByDate.value.get(dateStr) || [];
    const nursesByShift = {};
    for (const st of SHIFT_TYPES) {
      nursesByShift[st] = dayShifts.filter((s) => s.shift_type === st).map((s) => s.nurse_name);
    }
    days.push({
      dateStr,
      dayOfMonth: cursor.date(),
      inCurrentMonth: cursor.isSame(monthStart, 'month'),
      isToday: dateStr === today,
      nursesByShift,
    });
    cursor = cursor.add(1, 'day');
  }
  return days;
});

emitMonthRange();
</script>
```

Ajouter l'import des icônes en tête du fichier `<script setup>` : `import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';`

**Interfaces:**
- Produces: composant émettant `day-click` (string date) et `month-change` ({start, end}) — consommé par `NurseShiftsView.vue`.

- [ ] **Step 2: Écrire le panneau latéral du jour**

```vue
<!-- ah2-admin-web/src/components/nurseshift/NurseShiftDayPanel.vue -->
<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden h-fit">
    <div class="p-4 border-b border-gray-100 flex items-center justify-between">
      <h3 class="text-sm font-bold text-gray-700">{{ t('nurseShift.day_panel_title') }} {{ formattedDate }}</h3>
      <button @click="$emit('close')" class="p-1 rounded-lg hover:bg-gray-100 transition">
        <XMarkIcon class="h-5 w-5 text-gray-400" />
      </button>
    </div>

    <p v-if="!canManage" class="px-4 pt-3 text-xs text-gray-400 italic">{{ t('nurseShift.read_only_note') }}</p>

    <div class="p-4 space-y-4">
      <div v-for="st in SHIFT_TYPES" :key="st">
        <h4 class="text-xs font-bold text-gray-500 uppercase mb-2">{{ t(`nurseShift.shift.${st}`) }}</h4>

        <div v-if="shiftsFor(st).length === 0" class="text-xs text-gray-400 italic mb-2">
          {{ t('nurseShift.no_assignment') }}
        </div>
        <div v-for="s in shiftsFor(st)" :key="s.id" class="flex items-center justify-between text-sm py-1">
          <span>{{ s.nurse_name }}</span>
          <button v-if="canManage" @click="$emit('remove', s.id)" class="text-xs text-red-600 hover:underline">
            {{ t('nurseShift.remove') }}
          </button>
        </div>

        <div v-if="canManage" class="flex gap-2 mt-1">
          <select v-model="selectedNurseByShift[st]" class="flex-1 px-2 py-1 border border-gray-300 rounded-lg text-xs">
            <option value="" disabled>{{ t('nurseShift.select_nurse') }}</option>
            <option v-for="n in availableNurses" :key="n.user_id" :value="n.user_id">
              {{ n.full_name }}{{ n.is_head_nurse ? ` (${t('nurseShift.head_nurse_badge')})` : '' }}
            </option>
          </select>
          <button
            @click="$emit('add', { shiftType: st, nurseId: selectedNurseByShift[st] })"
            :disabled="!selectedNurseByShift[st]"
            class="px-3 py-1 text-xs font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ t('nurseShift.add_nurse') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import { SHIFT_TYPES } from '@/stores/nurseShiftStore';

const { t } = useI18n();

const props = defineProps({
  date: {
    type: String,
    required: true,
  },
  shifts: {
    type: Array,
    default: () => [],
  },
  availableNurses: {
    type: Array,
    default: () => [],
  },
  canManage: {
    type: Boolean,
    default: false,
  },
});

defineEmits(['close', 'add', 'remove']);

const selectedNurseByShift = reactive({ MATIN: '', APRES_MIDI: '', NUIT: '' });

const formattedDate = computed(() => dayjs(props.date).format('DD/MM/YYYY'));

function shiftsFor(shiftType) {
  return props.shifts.filter((s) => s.shift_type === shiftType);
}
</script>
```

**Interfaces:**
- Produces: composant émettant `close`, `add({shiftType, nurseId})`, `remove(shiftId)` — consommé par `NurseShiftsView.vue`. Consomme `SHIFT_TYPES` (Task 7).

- [ ] **Step 3: Écrire la vue qui assemble le tout**

```vue
<!-- ah2-admin-web/src/views/modules/nurseshift/NurseShiftsView.vue -->
<template>
  <div class="space-y-6 w-full">

    <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('nurseShift.title') }}</h1>
      <p class="text-sm text-gray-500">{{ t('nurseShift.subtitle') }}</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      <div class="lg:col-span-2">
        <NurseShiftCalendar :shifts="nurseShiftStore.shifts" @day-click="handleDayClick" @month-change="handleMonthChange" />
      </div>
      <NurseShiftDayPanel
        v-if="selectedDate"
        :date="selectedDate"
        :shifts="selectedDateShifts"
        :available-nurses="nurseShiftStore.activeNurses"
        :can-manage="canManage"
        @close="selectedDate = null"
        @add="handleAdd"
        @remove="handleRemove"
      />
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useNurseShiftStore } from '@/stores/nurseShiftStore';
import { useAuthStore } from '@/stores/auth';
import NurseShiftCalendar from '@/components/nurseshift/NurseShiftCalendar.vue';
import NurseShiftDayPanel from '@/components/nurseshift/NurseShiftDayPanel.vue';

const { t } = useI18n();
const nurseShiftStore = useNurseShiftStore();
const authStore = useAuthStore();

const selectedDate = ref(null);
const currentRange = ref({ start: null, end: null });

// medecin toujours autorise ; infirmier seulement si is_head_nurse - le
// backend refuse (403) de toute facon si ce garde frontend etait
// contourne, voir controller/nurse_shift_controller.py::_ensure_can_manage_schedule.
const canManage = computed(() => {
  if (authStore.hasRole(['medecin'])) return true;
  return authStore.hasRole(['nurse']) && !!authStore.user?.is_head_nurse;
});

const selectedDateShifts = computed(() => {
  if (!selectedDate.value) return [];
  return nurseShiftStore.shifts.filter((s) => s.shift_date === selectedDate.value);
});

function handleMonthChange({ start, end }) {
  currentRange.value = { start, end };
  nurseShiftStore.fetchShifts(start, end);
}

function handleDayClick(dateStr) {
  selectedDate.value = dateStr;
}

async function handleAdd({ shiftType, nurseId }) {
  if (!nurseId) return;
  await nurseShiftStore.createShift(selectedDate.value, shiftType, nurseId, currentRange.value.start, currentRange.value.end);
}

async function handleRemove(shiftId) {
  await nurseShiftStore.deleteShift(shiftId, currentRange.value.start, currentRange.value.end);
}

onMounted(() => {
  nurseShiftStore.fetchActiveNurses();
});
</script>
```

**Interfaces:**
- Consumes: `authStore.hasRole` (déjà existant), `authStore.user.is_head_nurse` (Task 6 — ⚠️ voir Step 4 ci-dessous, le payload `/auth/me`/login doit déjà inclure ce champ pour que ce garde fonctionne).

- [ ] **Step 4: Vérifier que `authStore.user` porte bien `is_head_nurse`**

`authStore.user` est rempli depuis la réponse de connexion/`/auth/me`. Chercher dans `ah2-admin-web/src/stores/auth.js` comment `this.user` est peuplé (probablement `response.data` brut du endpoint d'authentification). Si ce endpoint renvoie déjà l'objet utilisateur complet issu de `UserOut`/`normalize_user_data` (Task 6 y a déjà ajouté `is_head_nurse`), aucune modification n'est nécessaire ici — vérifier seulement, ne pas dupliquer un mapping. Si l'endpoint d'authentification utilise un schéma de sortie différent et plus restreint qui n'inclut pas `is_head_nurse`, ajouter le champ à ce schéma précis (lire le fichier concerné avant de conclure). Documenter dans le rapport ce qui a été trouvé et, le cas échéant, ce qui a été ajouté.

- [ ] **Step 5: Ajouter la route**

Dans `ah2-admin-web/src/router/index.js`, ajouter un enfant au bloc `/medical` (à côté de `path: 'hospitalizations'`) :

```javascript
      {
        path: 'nurse-shifts',
        name: 'medical-nurse-shifts',
        component: () => import('@/views/modules/nurseshift/NurseShiftsView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
```

- [ ] **Step 6: Ajouter l'entrée de menu**

Dans `ah2-admin-web/src/components/layout/MedicalLayout.vue`, ajouter au tableau des items de menu (à côté de l'entrée `/medical/hospitalizations`) :

```javascript
  {
    path: '/medical/nurse-shifts',
    labelKey: 'nurseShift.title',
    icon: CalendarDaysIcon,
  },
```

Vérifier que `CalendarDaysIcon` est bien importé depuis `@heroicons/vue/24/outline` en haut du fichier (l'ajouter à l'import groupé déjà existant si absent — distinct de `CalendarIcon` déjà utilisé pour les RDV, pour ne pas avoir deux entrées de menu avec la même icône).

- [ ] **Step 7: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, nouveau chunk `NurseShiftsView-*.js` visible dans la sortie.

- [ ] **Step 8: Commit**

```bash
git add ah2-admin-web/src/components/nurseshift/ ah2-admin-web/src/views/modules/nurseshift/ ah2-admin-web/src/router/index.js ah2-admin-web/src/components/layout/MedicalLayout.vue
git commit -m "feat: nurse rotation calendar screen (/medical/nurse-shifts)"
```
