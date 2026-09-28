# Suivi des hospitalisations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let médecin/nurse admit a clinical patient, log clinical-trend updates during the stay, and discharge them with a standard hospital disposition — with a real timestamped history and a live count of currently-hospitalized patients.

**Architecture:** Two new Postgres tables (`hospitalizations` — one row per stay, `discharged_at IS NULL` = currently admitted, partial unique index preventing two open stays for the same patient; `hospitalization_status_updates` — free-form timestamped clinical-trend log tied to a stay). A new backend module (model → repository → controller → FastAPI router) mirrors the existing `medical_records` module exactly. Frontend: a new Pinia store + gateway, a card in the patient dossier, and a dedicated list screen of currently-hospitalized patients — all médecin/nurse only, no offline/PowerSync support for this chantier.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic (raw-SQL migrations, this project's convention), pytest with real HTTP (`TestClient`) + real Postgres transactions (`db_session`/`api_client`/`auth_headers` fixtures), Vue 3 `<script setup>`, Pinia, vue-i18n, Tailwind.

**Spec:** `docs/superpowers/specs/2026-09-28-suivi-hospitalisations-design.md`

## Global Constraints

- Périmètre : patients cliniques généraux uniquement (pas le module toxico), routes sous `/medical/...`.
- Rôles autorisés à écrire (admettre / mettre à jour l'état / sortir) : `medecin` et `nurse` uniquement, sans distinction.
- L'endpoint KPI (`GET /hospitalizations/kpi/count_current`) est accessible en plus à `admin` et `promoteur`.
- `discharge_disposition` est l'une de exactement ces 4 valeurs : `GUERI`, `TRANSFERE`, `SORTIE_CONTRE_AVIS_MEDICAL`, `DECES` — obligatoire à la sortie.
- `status` (évolution clinique) est l'une de exactement ces 3 valeurs : `AMELIORATION`, `STABLE`, `AGGRAVATION` — pas de règle de transition entre elles.
- Un patient ne peut avoir qu'un seul séjour ouvert à la fois — contrainte réelle en base (index unique partiel), pas seulement une vérification applicative.
- Chaque admission et chaque sortie s'écrit dans `audit_user_actions` (`resource_type="Hospitalization"`).
- Pas de mode hors ligne / PowerSync pour ce chantier.
- Aucun test automatisé de composant Vue dans ce projet — le frontend se vérifie par build de production + lecture du code, comme le reste des chantiers de cette session.

## Review Focus

- Admettre un patient qui a déjà un séjour ouvert doit être refusé avec un message clair (409), jamais une erreur SQL brute qui fuite en surface. Testé en Task 5.
- Ajouter une évolution clinique ou prononcer une sortie sur un séjour déjà clos doit être refusé (400), jamais silencieusement accepté (ce qui romprait la lecture "dernier état = état actuel"). Testé en Task 5.
- Sortir sans `discharge_disposition` valide (absent, vide, ou valeur hors des 4 autorisées) doit être refusé (422), jamais persisté avec une valeur libre qui romprait les statistiques de sortie plus tard. Testé en Task 5.
- Un rôle non clinique (`secretaire`, `admin` hors endpoint KPI, tout autre rôle) doit être refusé (403) sur les endpoints d'écriture ET sur les endpoints de lecture (`/current`, `/patient/{id}`) — le périmètre clinique est étanche, pas seulement l'écriture. Testé en Task 5.
- Le bouton "Admettre"/carte hospitalisation ne doit être visible, côté `PatientDetailView.vue`, que pour `medecin`/`nurse` — ce composant est réutilisé par `admin`/`ToxicoManager` sur un autre écran, un oubli de garde de rôle y exposerait une action qui échouerait de toute façon côté serveur (403) mais resterait un bouton visible trompeur. Pas de test automatisé possible pour ce point côté frontend (aucun test de composant Vue dans ce projet) — vérifié par une relecture explicite du garde de rôle en Task 9.

---

## Task 1: Migration + modèles SQLAlchemy

**Files:**
- Create: `alembic/versions/015_hospitalizations.py`
- Create: `models/hospitalization.py`
- Modify: `models/__init__.py`
- Modify: `ci/schema_only.sql` (régénéré, pas édité à la main)
- Test: `tests/test_hospitalization_schema.py`

**Interfaces:**
- Produces: table `hospitalizations` (colonnes : `id`, `patient_id`, `admitted_at`, `admitted_by`, `admission_reason`, `discharged_at`, `discharge_disposition`, `discharge_note`, `discharged_by`, `created_at`, `updated_at`) et `hospitalization_status_updates` (`id`, `hospitalization_id`, `status`, `note`, `created_by`, `created_at`) ; index unique partiel `ux_hospitalizations_one_open_per_patient` sur `hospitalizations(patient_id)` `WHERE discharged_at IS NULL`. Modèles SQLAlchemy `Hospitalization`, `HospitalizationStatusUpdate` (`models/hospitalization.py`), consommés par Task 2.

- [ ] **Step 1: Écrire la migration Alembic**

```python
# alembic/versions/015_hospitalizations.py
"""hospitalizations + hospitalization_status_updates

Revision ID: 015_hospitalizations
Revises: 014_ticket_logo_token
Create Date: 2026-09-28

"""
from alembic import op

revision = '015_hospitalizations'
down_revision = '014_ticket_logo_token'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS hospitalizations (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES patients(patient_id),
            admitted_at TIMESTAMP NOT NULL DEFAULT now(),
            admitted_by INTEGER NOT NULL REFERENCES users(user_id),
            admission_reason TEXT,
            discharged_at TIMESTAMP,
            discharge_disposition VARCHAR(30)
                CHECK (discharge_disposition IN ('GUERI', 'TRANSFERE', 'SORTIE_CONTRE_AVIS_MEDICAL', 'DECES')),
            discharge_note TEXT,
            discharged_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_hospitalizations_one_open_per_patient
            ON hospitalizations (patient_id)
            WHERE discharged_at IS NULL;
        CREATE INDEX IF NOT EXISTS ix_hospitalizations_patient
            ON hospitalizations (patient_id);

        CREATE TABLE IF NOT EXISTS hospitalization_status_updates (
            id SERIAL PRIMARY KEY,
            hospitalization_id INTEGER NOT NULL REFERENCES hospitalizations(id),
            status VARCHAR(20) NOT NULL
                CHECK (status IN ('AMELIORATION', 'STABLE', 'AGGRAVATION')),
            note TEXT,
            created_by INTEGER NOT NULL REFERENCES users(user_id),
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_hospitalization_status_updates_hospitalization
            ON hospitalization_status_updates (hospitalization_id);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS hospitalization_status_updates;
        DROP TABLE IF EXISTS hospitalizations;
    """)
```

- [ ] **Step 2: Appliquer la migration contre la base locale réelle**

```bash
alembic upgrade head
```

Vérifier que ça se termine sans erreur et que `alembic current` affiche bien `015_hospitalizations (head)`.

- [ ] **Step 3: Écrire les modèles SQLAlchemy**

```python
# models/hospitalization.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

DISCHARGE_DISPOSITIONS = ("GUERI", "TRANSFERE", "SORTIE_CONTRE_AVIS_MEDICAL", "DECES")
CLINICAL_STATUSES = ("AMELIORATION", "STABLE", "AGGRAVATION")


class Hospitalization(Base):
    __tablename__ = 'hospitalizations'

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.patient_id'), nullable=False)
    admitted_at = Column(DateTime, nullable=False, server_default=func.now())
    admitted_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    admission_reason = Column(Text)
    discharged_at = Column(DateTime, nullable=True)
    discharge_disposition = Column(String(30), nullable=True)
    discharge_note = Column(Text)
    discharged_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    patient = relationship("Patient")
    admitted_by_user = relationship("User", foreign_keys=[admitted_by])
    discharged_by_user = relationship("User", foreign_keys=[discharged_by])
    status_updates = relationship(
        "HospitalizationStatusUpdate",
        back_populates="hospitalization",
        cascade="all, delete-orphan",
        order_by="desc(HospitalizationStatusUpdate.created_at)",
    )


class HospitalizationStatusUpdate(Base):
    __tablename__ = 'hospitalization_status_updates'

    id = Column(Integer, primary_key=True)
    hospitalization_id = Column(Integer, ForeignKey('hospitalizations.id'), nullable=False)
    status = Column(String(20), nullable=False)
    note = Column(Text)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    hospitalization = relationship("Hospitalization", back_populates="status_updates")
    created_by_user = relationship("User", foreign_keys=[created_by])
```

- [ ] **Step 4: Enregistrer les modèles dans `models/__init__.py`**

Ajouter, après la ligne `from .caisse_item import CaisseItem` (ordre alphabétique approximatif déjà en place dans ce fichier, peu importe la position exacte) :

```python
from .hospitalization import Hospitalization, HospitalizationStatusUpdate
```

- [ ] **Step 5: Écrire un test qui vérifie le schéma réel**

```python
# tests/test_hospitalization_schema.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import text
from tests.conftest import create_test_user, create_test_patient


def test_hospitalizations_table_has_partial_unique_index(db_session):
    """La contrainte 'un seul sejour ouvert par patient' doit exister
    reellement en base, pas seulement etre verifiee cote applicatif -
    sinon une course entre deux requetes concurrentes pourrait creer deux
    sejours ouverts pour le meme patient (voir Global Constraints)."""
    row = db_session.execute(text("""
        SELECT indexdef FROM pg_indexes
        WHERE indexname = 'ux_hospitalizations_one_open_per_patient'
    """)).fetchone()
    assert row is not None
    assert "discharged_at IS NULL" in row[0]


def test_hospitalization_status_updates_status_check_constraint(db_session):
    """Les 3 valeurs autorisees pour status sont une vraie contrainte
    CHECK en base, pas seulement une validation Pydantic contournable
    par un appel direct a l'API avec un schema different demain. Un
    vrai sejour valide est cree d'abord, pour que l'echec attendu soit
    bien celui de la contrainte CHECK et non une violation de cle
    etrangere sans rapport."""
    medecin = create_test_user(db_session, "schema_test_medecin", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="SchemaCheck")
    row = db_session.execute(text("""
        INSERT INTO hospitalizations (patient_id, admitted_by)
        VALUES (:patient_id, :admitted_by) RETURNING id
    """), {"patient_id": patient_id, "admitted_by": medecin.user_id}).fetchone()
    hospitalization_id = row[0]
    db_session.flush()

    with pytest.raises(Exception):
        db_session.execute(text("""
            INSERT INTO hospitalization_status_updates
                (hospitalization_id, status, created_by)
            VALUES (:hospitalization_id, 'VALEUR_INVALIDE', :created_by)
        """), {"hospitalization_id": hospitalization_id, "created_by": medecin.user_id})
        db_session.flush()
    db_session.rollback()
```

- [ ] **Step 6: Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_hospitalization_schema.py -v
```

Attendu : 2 passed.

- [ ] **Step 7: Régénérer `ci/schema_only.sql`**

```bash
pg_dump --schema-only --no-owner --no-privileges "$DATABASE_URL" > ci/schema_only.sql
```

(Sous PowerShell, définir d'abord `$env:PGPASSWORD` ou utiliser l'URL complète telle quelle — `pg_dump` accepte une URL de connexion directement comme argument positionnel.) Vérifier avec `git diff ci/schema_only.sql` que le diff contient bien les deux nouvelles tables et rien d'inattendu.

- [ ] **Step 8: Commit**

```bash
git add alembic/versions/015_hospitalizations.py models/hospitalization.py models/__init__.py ci/schema_only.sql tests/test_hospitalization_schema.py
git commit -m "feat: hospitalizations schema (admission/discharge episode + clinical status log)"
```

---

## Task 2: Repository

**Files:**
- Create: `repositories/hospitalization_repo.py`
- Test: `tests/test_hospitalization_repo.py`

**Interfaces:**
- Consumes: `models.hospitalization.Hospitalization`, `HospitalizationStatusUpdate` (Task 1).
- Produces: `HospitalizationRepository(session)` avec les méthodes `admit(patient_id: int, admitted_by_id: int, admission_reason: str | None) -> Hospitalization`, `add_status_update(hospitalization_id: int, status: str, note: str | None, created_by_id: int) -> HospitalizationStatusUpdate`, `discharge(hospitalization_id: int, discharge_disposition: str, discharge_note: str | None, discharged_by_id: int) -> Hospitalization`, `get_open_for_patient(patient_id: int) -> Hospitalization | None`, `list_current() -> list[Hospitalization]`, `get_history_for_patient(patient_id: int) -> list[Hospitalization]`. Toutes lèvent `ValueError` (jamais une exception SQLAlchemy brute) sur une règle métier violée — consommé par Task 3.

- [ ] **Step 1: Écrire les tests du repository (avant l'implémentation)**

```python
# tests/test_hospitalization_repo.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from repositories.hospitalization_repo import HospitalizationRepository
from tests.conftest import create_test_user, create_test_patient


def test_admit_creates_open_hospitalization(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin1", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoAdmit")

    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, "Fièvre persistante")

    assert hosp.id is not None
    assert hosp.patient_id == patient_id
    assert hosp.admitted_by == medecin.user_id
    assert hosp.discharged_at is None


def test_admit_refuses_second_open_stay_for_same_patient(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin2", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoDoubleAdmit")

    repo = HospitalizationRepository(db_session)
    repo.admit(patient_id, medecin.user_id, None)

    with pytest.raises(ValueError, match="déjà"):
        repo.admit(patient_id, medecin.user_id, None)


def test_add_status_update_on_open_stay(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin3", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoStatus")
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)

    update = repo.add_status_update(hosp.id, "AMELIORATION", "Fièvre en baisse", medecin.user_id)

    assert update.hospitalization_id == hosp.id
    assert update.status == "AMELIORATION"


def test_add_status_update_refuses_on_discharged_stay(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin4", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoStatusClosed")
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)
    repo.discharge(hosp.id, "GUERI", None, medecin.user_id)

    with pytest.raises(ValueError, match="clos"):
        repo.add_status_update(hosp.id, "STABLE", None, medecin.user_id)


def test_discharge_closes_stay(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin5", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoDischarge")
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)

    discharged = repo.discharge(hosp.id, "TRANSFERE", "Vers hôpital régional", medecin.user_id)

    assert discharged.discharged_at is not None
    assert discharged.discharge_disposition == "TRANSFERE"
    assert discharged.discharged_by == medecin.user_id


def test_discharge_refuses_already_discharged_stay(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin6", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoDoubleDischarge")
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)
    repo.discharge(hosp.id, "GUERI", None, medecin.user_id)

    with pytest.raises(ValueError, match="clos"):
        repo.discharge(hosp.id, "GUERI", None, medecin.user_id)


def test_get_open_for_patient(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin7", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoGetOpen")
    repo = HospitalizationRepository(db_session)

    assert repo.get_open_for_patient(patient_id) is None

    hosp = repo.admit(patient_id, medecin.user_id, None)
    assert repo.get_open_for_patient(patient_id).id == hosp.id

    repo.discharge(hosp.id, "GUERI", None, medecin.user_id)
    assert repo.get_open_for_patient(patient_id) is None


def test_list_current_only_returns_open_stays(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin8", "medecin")
    p1, _ = create_test_patient(db_session, medecin, first_name="RepoCurrent1")
    p2, _ = create_test_patient(db_session, medecin, first_name="RepoCurrent2")
    repo = HospitalizationRepository(db_session)

    open_hosp = repo.admit(p1, medecin.user_id, None)
    closed_hosp = repo.admit(p2, medecin.user_id, None)
    repo.discharge(closed_hosp.id, "GUERI", None, medecin.user_id)

    current_ids = [h.id for h in repo.list_current()]
    assert open_hosp.id in current_ids
    assert closed_hosp.id not in current_ids


def test_get_history_for_patient_includes_open_and_closed_stays(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin9", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoHistory")
    repo = HospitalizationRepository(db_session)

    first_stay = repo.admit(patient_id, medecin.user_id, None)
    repo.discharge(first_stay.id, "GUERI", None, medecin.user_id)
    second_stay = repo.admit(patient_id, medecin.user_id, None)

    history_ids = [h.id for h in repo.get_history_for_patient(patient_id)]
    assert first_stay.id in history_ids
    assert second_stay.id in history_ids
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

```bash
python -m pytest tests/test_hospitalization_repo.py -v
```

Attendu : ÉCHEC avec `ModuleNotFoundError: No module named 'repositories.hospitalization_repo'`.

- [ ] **Step 3: Écrire le repository**

```python
# repositories/hospitalization_repo.py
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from models.hospitalization import (
    Hospitalization,
    HospitalizationStatusUpdate,
    DISCHARGE_DISPOSITIONS,
    CLINICAL_STATUSES,
)


class HospitalizationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_open_for_patient(self, patient_id: int) -> Optional[Hospitalization]:
        return (
            self.session.query(Hospitalization)
            .filter(Hospitalization.patient_id == patient_id, Hospitalization.discharged_at.is_(None))
            .one_or_none()
        )

    def admit(self, patient_id: int, admitted_by_id: int, admission_reason: Optional[str]) -> Hospitalization:
        if self.get_open_for_patient(patient_id) is not None:
            raise ValueError("Ce patient est déjà hospitalisé (séjour en cours).")

        hosp = Hospitalization(
            patient_id=patient_id,
            admitted_by=admitted_by_id,
            admission_reason=admission_reason,
        )
        self.session.add(hosp)
        self.session.commit()
        self.session.refresh(hosp)
        return hosp

    def _get_or_raise(self, hospitalization_id: int) -> Hospitalization:
        hosp = self.session.get(Hospitalization, hospitalization_id)
        if hosp is None:
            raise ValueError(f"Aucune hospitalisation trouvée pour l'ID={hospitalization_id}")
        return hosp

    def add_status_update(
        self, hospitalization_id: int, status: str, note: Optional[str], created_by_id: int
    ) -> HospitalizationStatusUpdate:
        if status not in CLINICAL_STATUSES:
            raise ValueError(f"Statut clinique invalide : {status}")

        hosp = self._get_or_raise(hospitalization_id)
        if hosp.discharged_at is not None:
            raise ValueError("Ce séjour est déjà clos — impossible d'ajouter une évolution clinique.")

        update = HospitalizationStatusUpdate(
            hospitalization_id=hospitalization_id,
            status=status,
            note=note,
            created_by=created_by_id,
        )
        self.session.add(update)
        self.session.commit()
        self.session.refresh(update)
        return update

    def discharge(
        self,
        hospitalization_id: int,
        discharge_disposition: str,
        discharge_note: Optional[str],
        discharged_by_id: int,
    ) -> Hospitalization:
        if discharge_disposition not in DISCHARGE_DISPOSITIONS:
            raise ValueError(f"Type de sortie invalide : {discharge_disposition}")

        hosp = self._get_or_raise(hospitalization_id)
        if hosp.discharged_at is not None:
            raise ValueError("Ce séjour est déjà clos.")

        from datetime import datetime
        hosp.discharged_at = datetime.utcnow()
        hosp.discharge_disposition = discharge_disposition
        hosp.discharge_note = discharge_note
        hosp.discharged_by = discharged_by_id
        self.session.add(hosp)
        self.session.commit()
        self.session.refresh(hosp)
        return hosp

    def list_current(self) -> List[Hospitalization]:
        return (
            self.session.query(Hospitalization)
            .options(joinedload(Hospitalization.patient), joinedload(Hospitalization.status_updates))
            .filter(Hospitalization.discharged_at.is_(None))
            .order_by(Hospitalization.admitted_at.desc())
            .all()
        )

    def get_history_for_patient(self, patient_id: int) -> List[Hospitalization]:
        return (
            self.session.query(Hospitalization)
            .options(joinedload(Hospitalization.status_updates))
            .filter(Hospitalization.patient_id == patient_id)
            .order_by(Hospitalization.admitted_at.desc())
            .all()
        )

    def count_current(self) -> int:
        return (
            self.session.query(Hospitalization)
            .filter(Hospitalization.discharged_at.is_(None))
            .count()
        )
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_hospitalization_repo.py -v
```

Attendu : 9 passed.

- [ ] **Step 5: Commit**

```bash
git add repositories/hospitalization_repo.py tests/test_hospitalization_repo.py
git commit -m "feat: HospitalizationRepository (admit/status/discharge/current/history)"
```

---

## Task 3: Controller (audit + orchestration)

**Files:**
- Create: `controller/hospitalization_controller.py`
- Test: `tests/test_hospitalization_controller.py`

**Interfaces:**
- Consumes: `repositories.hospitalization_repo.HospitalizationRepository` (Task 2), `repositories.audit_repo.AuditRepository` (déjà existant, signature `log_user_action(current_user, resource_type, action_performed, resource_id=None, details=None)`).
- Produces: `HospitalizationController(repo, current_user, audit_repo=None)` avec `admit(patient_id, admission_reason) -> Hospitalization`, `add_status_update(hospitalization_id, status, note) -> HospitalizationStatusUpdate`, `discharge(hospitalization_id, discharge_disposition, discharge_note) -> Hospitalization`, `list_current() -> list[Hospitalization]`, `get_history_for_patient(patient_id) -> list[Hospitalization]`, `count_current() -> int` — consommé par Task 4.

- [ ] **Step 1: Écrire les tests du controller (avant l'implémentation)**

```python
# tests/test_hospitalization_controller.py
import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock
from controller.hospitalization_controller import HospitalizationController


def test_admit_logs_audit_entry():
    repo = MagicMock()
    hosp = MagicMock(id=42)
    repo.admit.return_value = hosp
    user = MagicMock(user_id=7)
    audit_repo = MagicMock()

    ctrl = HospitalizationController(repo=repo, current_user=user, audit_repo=audit_repo)
    result = ctrl.admit(patient_id=1, admission_reason="Fièvre")

    assert result is hosp
    repo.admit.assert_called_once_with(1, 7, "Fièvre")
    audit_repo.log_user_action.assert_called_once()
    call_kwargs = audit_repo.log_user_action.call_args.kwargs
    assert call_kwargs["resource_type"] == "Hospitalization"
    assert call_kwargs["action_performed"] == "ADMIT"
    assert call_kwargs["resource_id"] == 42


def test_discharge_logs_audit_entry():
    repo = MagicMock()
    hosp = MagicMock(id=42)
    repo.discharge.return_value = hosp
    user = MagicMock(user_id=7)
    audit_repo = MagicMock()

    ctrl = HospitalizationController(repo=repo, current_user=user, audit_repo=audit_repo)
    ctrl.discharge(hospitalization_id=42, discharge_disposition="GUERI", discharge_note=None)

    repo.discharge.assert_called_once_with(42, "GUERI", None, 7)
    audit_repo.log_user_action.assert_called_once()
    assert audit_repo.log_user_action.call_args.kwargs["action_performed"] == "DISCHARGE"


def test_controller_logs_when_audit_fails(caplog):
    """Meme motif que le reste du projet (test_audit_logging.py) : un
    echec d'ecriture d'audit ne doit jamais faire echouer l'action
    metier elle-meme."""
    repo = MagicMock()
    repo.admit.return_value = MagicMock(id=1)
    user = MagicMock(user_id=7)
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = HospitalizationController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.admit(patient_id=1, admission_reason=None)

    assert result is not None
    assert any("audit" in r.message.lower() for r in caplog.records)


def test_add_status_update_delegates_to_repo():
    repo = MagicMock()
    update = MagicMock()
    repo.add_status_update.return_value = update
    user = MagicMock(user_id=9)

    ctrl = HospitalizationController(repo=repo, current_user=user)
    result = ctrl.add_status_update(hospitalization_id=42, status="AMELIORATION", note="ok")

    assert result is update
    repo.add_status_update.assert_called_once_with(42, "AMELIORATION", "ok", 9)


def test_list_current_delegates_to_repo():
    repo = MagicMock()
    repo.list_current.return_value = ["a", "b"]
    ctrl = HospitalizationController(repo=repo, current_user=MagicMock())

    assert ctrl.list_current() == ["a", "b"]


def test_count_current_delegates_to_repo():
    repo = MagicMock()
    repo.count_current.return_value = 3
    ctrl = HospitalizationController(repo=repo, current_user=MagicMock())

    assert ctrl.count_current() == 3
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

```bash
python -m pytest tests/test_hospitalization_controller.py -v
```

Attendu : ÉCHEC avec `ModuleNotFoundError: No module named 'controller.hospitalization_controller'`.

- [ ] **Step 3: Écrire le controller**

```python
# controller/hospitalization_controller.py
import logging
from typing import Optional, List

from repositories.hospitalization_repo import HospitalizationRepository
from repositories.audit_repo import AuditRepository


class HospitalizationController:
    def __init__(
        self,
        repo: HospitalizationRepository,
        current_user,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.repo = repo
        self.user = current_user
        self.audit_repo = audit_repo
        self.logger = logging.getLogger(__name__)

    def _log_audit(self, action_performed: str, resource_id: int, details: Optional[str] = None):
        if not (self.audit_repo and self.user):
            return
        try:
            self.audit_repo.log_user_action(
                current_user=self.user,
                resource_type="Hospitalization",
                action_performed=action_performed,
                resource_id=resource_id,
                details=details,
            )
        except Exception:
            self.logger.exception("Échec de l'écriture d'audit")

    def admit(self, patient_id: int, admission_reason: Optional[str]):
        hosp = self.repo.admit(patient_id, self.user.user_id, admission_reason)
        self._log_audit("ADMIT", hosp.id, details=admission_reason)
        return hosp

    def add_status_update(self, hospitalization_id: int, status: str, note: Optional[str]):
        return self.repo.add_status_update(hospitalization_id, status, note, self.user.user_id)

    def discharge(self, hospitalization_id: int, discharge_disposition: str, discharge_note: Optional[str]):
        hosp = self.repo.discharge(hospitalization_id, discharge_disposition, discharge_note, self.user.user_id)
        self._log_audit("DISCHARGE", hosp.id, details=discharge_disposition)
        return hosp

    def list_current(self) -> List:
        return self.repo.list_current()

    def get_history_for_patient(self, patient_id: int) -> List:
        return self.repo.get_history_for_patient(patient_id)

    def count_current(self) -> int:
        return self.repo.count_current()
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_hospitalization_controller.py -v
```

Attendu : 6 passed.

- [ ] **Step 5: Commit**

```bash
git add controller/hospitalization_controller.py tests/test_hospitalization_controller.py
git commit -m "feat: HospitalizationController (audit logging, never blocks on audit failure)"
```

---

## Task 4: Schémas Pydantic + routeur FastAPI + enregistrement

**Files:**
- Create: `api_backend/backend_app/routes/hospitalizations/__init__.py`
- Create: `api_backend/backend_app/routes/hospitalizations/schemas.py`
- Create: `api_backend/backend_app/routes/hospitalizations/hospitalization_endpoint.py`
- Modify: `api_backend/backend_app/main.py`

**Interfaces:**
- Consumes: `controller.hospitalization_controller.HospitalizationController` (Task 3).
- Produces: routeur monté sur `/hospitalizations`, endpoints `POST /`, `POST /{id}/status`, `POST /{id}/discharge`, `GET /current`, `GET /patient/{patient_id}`, `GET /kpi/count_current` — consommé par Task 5 (tests HTTP) et par le frontend (Task 6).

- [ ] **Step 1: Créer le fichier vide de package**

```python
# api_backend/backend_app/routes/hospitalizations/__init__.py
```

- [ ] **Step 2: Écrire les schémas Pydantic**

```python
# api_backend/backend_app/routes/hospitalizations/schemas.py
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class HospitalizationAdmit(BaseModel):
    patient_id: int
    admission_reason: Optional[str] = None


class HospitalizationStatusCreate(BaseModel):
    status: str = Field(..., description="AMELIORATION | STABLE | AGGRAVATION")
    note: Optional[str] = None


class HospitalizationDischarge(BaseModel):
    discharge_disposition: str = Field(
        ..., description="GUERI | TRANSFERE | SORTIE_CONTRE_AVIS_MEDICAL | DECES"
    )
    discharge_note: Optional[str] = None


class HospitalizationStatusUpdateOut(BaseModel):
    id: int
    status: str
    note: Optional[str] = None
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class HospitalizationOut(BaseModel):
    id: int
    patient_id: int
    admitted_at: datetime
    admitted_by: int
    admission_reason: Optional[str] = None
    discharged_at: Optional[datetime] = None
    discharge_disposition: Optional[str] = None
    discharge_note: Optional[str] = None
    discharged_by: Optional[int] = None
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    status_updates: List[HospitalizationStatusUpdateOut] = []

    model_config = {"from_attributes": True}


class HospitalizationCountOut(BaseModel):
    count: int
```

- [ ] **Step 3: Écrire le routeur**

```python
# api_backend/backend_app/routes/hospitalizations/hospitalization_endpoint.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .schemas import (
    HospitalizationAdmit,
    HospitalizationStatusCreate,
    HospitalizationDischarge,
    HospitalizationOut,
    HospitalizationStatusUpdateOut,
    HospitalizationCountOut,
)
from ...database import SessionLocal
from controller.hospitalization_controller import HospitalizationController
from repositories.hospitalization_repo import HospitalizationRepository
from repositories.audit_repo import AuditRepository
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hospitalizations",
    tags=["Hospitalisations"],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_hospitalization_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HospitalizationController:
    repo = HospitalizationRepository(db)
    audit_repo = AuditRepository(db)
    return HospitalizationController(repo=repo, current_user=current_user, audit_repo=audit_repo)


def _to_out(hosp) -> HospitalizationOut:
    return HospitalizationOut(
        id=hosp.id,
        patient_id=hosp.patient_id,
        admitted_at=hosp.admitted_at,
        admitted_by=hosp.admitted_by,
        admission_reason=hosp.admission_reason,
        discharged_at=hosp.discharged_at,
        discharge_disposition=hosp.discharge_disposition,
        discharge_note=hosp.discharge_note,
        discharged_by=hosp.discharged_by,
        patient_first_name=getattr(hosp.patient, "first_name", None) if hosp.patient else None,
        patient_last_name=getattr(hosp.patient, "last_name", None) if hosp.patient else None,
        status_updates=[HospitalizationStatusUpdateOut.model_validate(u) for u in (hosp.status_updates or [])],
    )


@router.post("/", response_model=HospitalizationOut, status_code=status.HTTP_201_CREATED)
def admit(data: HospitalizationAdmit, ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    try:
        hosp = ctrl.admit(data.patient_id, data.admission_reason)
        return _to_out(hosp)
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except IntegrityError:
        logger.exception("Conflit base de donnees a l'admission")
        raise HTTPException(status_code=409, detail="Ce patient est déjà hospitalisé (séjour en cours).")


@router.post("/{hospitalization_id}/status", response_model=HospitalizationStatusUpdateOut, status_code=status.HTTP_201_CREATED)
def add_status_update(
    hospitalization_id: int,
    data: HospitalizationStatusCreate,
    ctrl: HospitalizationController = Depends(get_hospitalization_controller),
):
    if data.status not in ("AMELIORATION", "STABLE", "AGGRAVATION"):
        raise HTTPException(status_code=422, detail="Statut clinique invalide.")
    try:
        update = ctrl.add_status_update(hospitalization_id, data.status, data.note)
        return HospitalizationStatusUpdateOut.model_validate(update)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/{hospitalization_id}/discharge", response_model=HospitalizationOut)
def discharge(
    hospitalization_id: int,
    data: HospitalizationDischarge,
    ctrl: HospitalizationController = Depends(get_hospitalization_controller),
):
    if data.discharge_disposition not in ("GUERI", "TRANSFERE", "SORTIE_CONTRE_AVIS_MEDICAL", "DECES"):
        raise HTTPException(status_code=422, detail="Type de sortie invalide.")
    try:
        hosp = ctrl.discharge(hospitalization_id, data.discharge_disposition, data.discharge_note)
        return _to_out(hosp)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/current", response_model=list[HospitalizationOut])
def list_current(ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return [_to_out(h) for h in ctrl.list_current()]


@router.get("/patient/{patient_id}", response_model=list[HospitalizationOut])
def get_history_for_patient(patient_id: int, ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return [_to_out(h) for h in ctrl.get_history_for_patient(patient_id)]


@router.get(
    "/kpi/count_current",
    response_model=HospitalizationCountOut,
    dependencies=[Depends(role_required("medecin", "nurse", "admin", "promoteur"))],
)
def count_current(ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return HospitalizationCountOut(count=ctrl.count_current())
```

- [ ] **Step 4: Enregistrer le routeur dans `main.py`**

Ajouter l'import, à côté de `from .routes.medical_records import medical_records_endpoint` :

```python
from .routes.hospitalizations import hospitalization_endpoint
```

Ajouter l'enregistrement, à côté de `app.include_router(medical_records_endpoint.router)` :

```python
app.include_router(hospitalization_endpoint.router)
```

- [ ] **Step 5: Vérifier que l'application démarre toujours**

```bash
python -c "from api_backend.backend_app.main import app; print('OK', len(app.routes))"
```

Attendu : `OK <nombre>` sans traceback.

- [ ] **Step 6: Commit**

```bash
git add api_backend/backend_app/routes/hospitalizations/ api_backend/backend_app/main.py
git commit -m "feat: POST/GET /hospitalizations endpoints"
```

---

## Task 5: Tests d'intégration HTTP complets

**Files:**
- Create: `tests/test_hospitalizations_endpoints.py`

**Interfaces:**
- Consumes: routeur de Task 4, `tests/conftest.py` (`api_client`, `auth_headers`, `create_test_user`, `create_test_patient`, `db_session`).

- [ ] **Step 1: Écrire les tests HTTP (Review Focus inclus : admission double, action sur séjour clos, disposition invalide, rôles non cliniques, accès KPI élargi)**

```python
# tests/test_hospitalizations_endpoints.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.hospitalizations import hospitalization_endpoint
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, hospitalization_endpoint)


def test_admit_success(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpAdmit")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin1", TEST_PASSWORD)

    resp = client.post("/hospitalizations/", json={
        "patient_id": patient_id,
        "admission_reason": "Fièvre persistante",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["patient_id"] == patient_id
    assert body["discharged_at"] is None


def test_admit_refuses_double_open_stay(db_session, api_client):
    """Review Focus : admettre un patient deja hospitalise doit etre
    refuse avec un message clair, jamais une erreur SQL brute."""
    medecin = create_test_user(db_session, "hosp_ep_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpDoubleAdmit")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin2", TEST_PASSWORD)

    client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers)
    resp = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers)

    assert resp.status_code == 409
    assert "déjà" in resp.json()["detail"]


def test_status_update_refused_on_discharged_stay(db_session, api_client):
    """Review Focus : ajouter une evolution clinique sur un sejour
    deja clos doit etre refuse (400)."""
    medecin = create_test_user(db_session, "hosp_ep_medecin3", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpStatusClosed")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin3", TEST_PASSWORD)

    hosp_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)

    resp = client.post(f"/hospitalizations/{hosp_id}/status", json={"status": "STABLE"}, headers=headers)
    assert resp.status_code == 400


def test_discharge_requires_valid_disposition(db_session, api_client):
    """Review Focus : sortir sans discharge_disposition valide doit
    etre refuse (422), jamais persiste avec une valeur libre."""
    medecin = create_test_user(db_session, "hosp_ep_medecin4", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpBadDisposition")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin4", TEST_PASSWORD)

    hosp_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]

    resp = client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "PAS_UNE_VRAIE_VALEUR"}, headers=headers)
    assert resp.status_code == 422

    resp_missing = client.post(f"/hospitalizations/{hosp_id}/discharge", json={}, headers=headers)
    assert resp_missing.status_code == 422


def test_discharge_refused_on_already_discharged_stay(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin5", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpDoubleDischarge")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin5", TEST_PASSWORD)

    hosp_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)

    resp = client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)
    assert resp.status_code == 400


def test_list_current_only_shows_open_stays(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin6", "medecin", password=TEST_PASSWORD)
    p_open, _ = create_test_patient(db_session, medecin, first_name="EpCurrentOpen")
    p_closed, _ = create_test_patient(db_session, medecin, first_name="EpCurrentClosed")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin6", TEST_PASSWORD)

    open_id = client.post("/hospitalizations/", json={"patient_id": p_open}, headers=headers).json()["id"]
    closed_id = client.post("/hospitalizations/", json={"patient_id": p_closed}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{closed_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)

    resp = client.get("/hospitalizations/current", headers=headers)
    assert resp.status_code == 200
    ids = [h["id"] for h in resp.json()]
    assert open_id in ids
    assert closed_id not in ids


def test_patient_history_includes_all_stays(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin7", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpHistory")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin7", TEST_PASSWORD)

    first_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{first_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)
    second_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]

    resp = client.get(f"/hospitalizations/patient/{patient_id}", headers=headers)
    assert resp.status_code == 200
    ids = [h["id"] for h in resp.json()]
    assert first_id in ids
    assert second_id in ids


def test_nurse_has_same_rights_as_medecin(db_session, api_client):
    nurse = create_test_user(db_session, "hosp_ep_nurse1", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse, first_name="EpNurse")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_nurse1", TEST_PASSWORD)

    resp = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers)
    assert resp.status_code == 201


def test_secretaire_forbidden_on_write_and_read(db_session, api_client):
    """Review Focus : un role non clinique doit etre refuse aussi bien
    en ecriture qu'en lecture (/current, /patient/{id}) - le perimetre
    clinique est etanche."""
    create_test_user(db_session, "hosp_ep_secretaire1", "secretaire", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "hosp_ep_medecin8", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpSecretaire")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_secretaire1", TEST_PASSWORD)

    assert client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).status_code == 403
    assert client.get("/hospitalizations/current", headers=headers).status_code == 403
    assert client.get(f"/hospitalizations/patient/{patient_id}", headers=headers).status_code == 403


def test_admin_forbidden_except_kpi_endpoint(db_session, api_client):
    """Review Focus : le reste du routeur reste medecin/nurse seul pour
    admin - la seule exception est l'endpoint KPI."""
    create_test_user(db_session, "hosp_ep_admin1", "admin", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_admin1", TEST_PASSWORD)

    assert client.get("/hospitalizations/current", headers=headers).status_code == 403


def test_kpi_endpoint_accessible_to_admin_and_medecin(db_session, api_client):
    """Review Focus : l'endpoint KPI doit rester accessible a
    admin/promoteur EN PLUS de medecin/nurse."""
    medecin = create_test_user(db_session, "hosp_ep_medecin9", "medecin", password=TEST_PASSWORD)
    admin = create_test_user(db_session, "hosp_ep_admin2", "admin", password=TEST_PASSWORD)
    client = _client(api_client)

    medecin_headers = auth_headers(client, "hosp_ep_medecin9", TEST_PASSWORD)
    admin_headers = auth_headers(client, "hosp_ep_admin2", TEST_PASSWORD)

    resp_medecin = client.get("/hospitalizations/kpi/count_current", headers=medecin_headers)
    resp_admin = client.get("/hospitalizations/kpi/count_current", headers=admin_headers)

    assert resp_medecin.status_code == 200
    assert resp_admin.status_code == 200
    assert "count" in resp_admin.json()


def test_admit_and_discharge_write_audit_entries(db_session, api_client):
    from models.audit import AuditUserAction

    medecin = create_test_user(db_session, "hosp_ep_medecin10", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpAudit")
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin10", TEST_PASSWORD)

    hosp_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)

    entries = (
        db_session.query(AuditUserAction)
        .filter(AuditUserAction.resource_type == "Hospitalization", AuditUserAction.resource_id == hosp_id)
        .all()
    )
    actions = {e.action_performed for e in entries}
    assert "ADMIT" in actions
    assert "DISCHARGE" in actions
```

- [ ] **Step 2: Lancer la suite complète des tests hospitalisations**

```bash
python -m pytest tests/test_hospitalization_schema.py tests/test_hospitalization_repo.py tests/test_hospitalization_controller.py tests/test_hospitalizations_endpoints.py -v
```

Attendu : tout passe (2 + 9 + 6 + 12 = 29 tests).

- [ ] **Step 3: Lancer la suite complète du backend pour vérifier l'absence de régression**

```bash
python -m pytest tests/ -q
```

Attendu : les mêmes 9 échecs préexistants déjà documentés (caisse/prescriptions, sans rapport), aucun nouveau.

- [ ] **Step 4: Commit**

```bash
git add tests/test_hospitalizations_endpoints.py
git commit -m "test: full HTTP coverage for hospitalizations (RBAC, conflicts, audit)"
```

---

## Task 6: Frontend — Gateway + Store

**Files:**
- Create: `ah2-admin-web/src/services/HospitalizationGateway.js`
- Create: `ah2-admin-web/src/stores/hospitalizationStore.js`

**Interfaces:**
- Consumes: endpoints de Task 4.
- Produces: `HospitalizationGateway` (`admit`, `addStatusUpdate`, `discharge`, `fetchCurrent`, `fetchPatientHistory`, `fetchKpiCount`) et `useHospitalizationStore()` (state `current`, `patientHistory`, `isLoading`, actions `fetchCurrent()`, `fetchPatientHistory(patientId)`, `admit(patientId, reason)`, `addStatusUpdate(id, status, note)`, `discharge(id, disposition, note)`) — consommé par Task 8, 9, 10.

- [ ] **Step 1: Écrire le gateway**

```javascript
// src/services/HospitalizationGateway.js
import api from '@/services/api';

export const HospitalizationGateway = {
    async admit(patientId, admissionReason) {
        return api.post('/hospitalizations/', {
            patient_id: patientId,
            admission_reason: admissionReason || null,
        });
    },

    async addStatusUpdate(hospitalizationId, statusValue, note) {
        return api.post(`/hospitalizations/${hospitalizationId}/status`, {
            status: statusValue,
            note: note || null,
        });
    },

    async discharge(hospitalizationId, dischargeDisposition, dischargeNote) {
        return api.post(`/hospitalizations/${hospitalizationId}/discharge`, {
            discharge_disposition: dischargeDisposition,
            discharge_note: dischargeNote || null,
        });
    },

    async fetchCurrent() {
        return api.get('/hospitalizations/current');
    },

    async fetchPatientHistory(patientId) {
        return api.get(`/hospitalizations/patient/${patientId}`);
    },

    async fetchKpiCount() {
        return api.get('/hospitalizations/kpi/count_current');
    },
};
```

- [ ] **Step 2: Écrire le store**

```javascript
// src/stores/hospitalizationStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { HospitalizationGateway } from '@/services/HospitalizationGateway';

// Les 4 seules valeurs reellement acceptees par le backend (CHECK
// constraint + validation Pydantic, voir schemas.py) - ne pas en
// ajouter ici sans les ajouter aussi cote backend.
export const DISCHARGE_DISPOSITIONS = ['GUERI', 'TRANSFERE', 'SORTIE_CONTRE_AVIS_MEDICAL', 'DECES'];
export const CLINICAL_STATUSES = ['AMELIORATION', 'STABLE', 'AGGRAVATION'];

export const useHospitalizationStore = defineStore('hospitalization', () => {
    const current = ref([]);
    const patientHistory = ref([]);
    const isLoading = ref(false);
    const error = ref(null);

    async function fetchCurrent() {
        isLoading.value = true;
        error.value = null;
        try {
            const resp = await HospitalizationGateway.fetchCurrent();
            current.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement hospitalisations en cours:', err);
            error.value = "Impossible de charger la liste des patients hospitalisés.";
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchPatientHistory(patientId) {
        try {
            const resp = await HospitalizationGateway.fetchPatientHistory(patientId);
            patientHistory.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement historique hospitalisation:', err);
            patientHistory.value = [];
        }
    }

    async function admit(patientId, admissionReason) {
        await HospitalizationGateway.admit(patientId, admissionReason);
        await fetchPatientHistory(patientId);
    }

    async function addStatusUpdate(hospitalizationId, statusValue, note, patientId) {
        await HospitalizationGateway.addStatusUpdate(hospitalizationId, statusValue, note);
        if (patientId) await fetchPatientHistory(patientId);
    }

    async function discharge(hospitalizationId, dischargeDisposition, dischargeNote, patientId) {
        await HospitalizationGateway.discharge(hospitalizationId, dischargeDisposition, dischargeNote);
        if (patientId) await fetchPatientHistory(patientId);
    }

    return {
        current,
        patientHistory,
        isLoading,
        error,
        fetchCurrent,
        fetchPatientHistory,
        admit,
        addStatusUpdate,
        discharge,
    };
});
```

- [ ] **Step 3: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, aucune erreur (ces deux fichiers ne sont pas encore importés ailleurs, donc aucun changement de bundle visible — juste vérifier l'absence d'erreur de syntaxe).

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/services/HospitalizationGateway.js ah2-admin-web/src/stores/hospitalizationStore.js
git commit -m "feat: HospitalizationGateway + hospitalizationStore"
```

---

## Task 7: i18n

**Files:**
- Modify: `ah2-admin-web/src/i18n.js`

**Interfaces:**
- Produces: clés `hospitalization.*` (FR + EN), consommées par Task 8, 9, 10.

- [ ] **Step 1: Ajouter les clés FR**

Dans le bloc de messages FR (à côté du bloc `appointments: { ... }`), ajouter :

```javascript
    hospitalization: {
      title: "Patients hospitalisés",
      subtitle: "Séjours en cours",
      card_title: "Hospitalisation",
      not_hospitalized: "Ce patient n'est pas actuellement hospitalisé.",
      admit_button: "Admettre",
      update_status_button: "Mettre à jour l'état",
      discharge_button: "Sortir",
      admission_reason: "Motif d'admission",
      admitted_since: "Hospitalisé depuis",
      days_count: "jour(s)",
      current_status: "Dernière évolution",
      no_status_yet: "Aucune mise à jour depuis l'admission.",
      history_title: "Historique",
      status: {
        AMELIORATION: "Amélioration",
        STABLE: "Stable",
        AGGRAVATION: "Aggravation"
      },
      disposition: {
        GUERI: "Guéri",
        TRANSFERE: "Transféré",
        SORTIE_CONTRE_AVIS_MEDICAL: "Sortie contre avis médical",
        DECES: "Décès"
      },
      status_note: "Note",
      discharge_note: "Note de sortie",
      discharge_disposition_label: "Type de sortie",
      confirm: "Confirmer",
      cancel: "Annuler",
      empty_list: "Aucun patient actuellement hospitalisé.",
      table: {
        patient: "Patient",
        admitted_since: "Hospitalisé depuis",
        days: "Jours",
        current_status: "État actuel",
        admitted_by: "Admis par"
      }
    },
```

- [ ] **Step 2: Ajouter les clés EN**

Dans le bloc de messages EN (à côté du bloc `appointments: { ... }` en anglais), ajouter :

```javascript
    hospitalization: {
      title: "Hospitalized Patients",
      subtitle: "Current stays",
      card_title: "Hospitalization",
      not_hospitalized: "This patient is not currently hospitalized.",
      admit_button: "Admit",
      update_status_button: "Update status",
      discharge_button: "Discharge",
      admission_reason: "Admission reason",
      admitted_since: "Hospitalized since",
      days_count: "day(s)",
      current_status: "Latest update",
      no_status_yet: "No update since admission.",
      history_title: "History",
      status: {
        AMELIORATION: "Improving",
        STABLE: "Stable",
        AGGRAVATION: "Worsening"
      },
      disposition: {
        GUERI: "Recovered",
        TRANSFERE: "Transferred",
        SORTIE_CONTRE_AVIS_MEDICAL: "Left against medical advice",
        DECES: "Deceased"
      },
      status_note: "Note",
      discharge_note: "Discharge note",
      discharge_disposition_label: "Discharge type",
      confirm: "Confirm",
      cancel: "Cancel",
      empty_list: "No patient currently hospitalized.",
      table: {
        patient: "Patient",
        admitted_since: "Hospitalized since",
        days: "Days",
        current_status: "Current status",
        admitted_by: "Admitted by"
      }
    },
```

- [ ] **Step 3: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, aucune erreur.

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/i18n.js
git commit -m "i18n: hospitalization strings (FR/EN)"
```

---

## Task 8: Composant `HospitalizationCard.vue`

**Files:**
- Create: `ah2-admin-web/src/components/hospitalization/HospitalizationCard.vue`

**Interfaces:**
- Consumes: `useHospitalizationStore()` (Task 6), props `patientId: Number`.
- Produces: composant autonome (admet, met à jour, sort, affiche l'historique) — consommé par Task 9.

- [ ] **Step 1: Écrire le composant**

```vue
<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-gray-800">{{ t('hospitalization.card_title') }}</h3>
      <button
        v-if="!openStay"
        @click="showAdmitForm = true"
        class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition"
      >
        {{ t('hospitalization.admit_button') }}
      </button>
    </div>

    <div v-if="!openStay && !showAdmitForm" class="text-sm text-gray-500 italic">
      {{ t('hospitalization.not_hospitalized') }}
    </div>

    <div v-if="showAdmitForm" class="space-y-3 mb-4 p-4 bg-gray-50 rounded-xl">
      <label class="text-xs font-bold text-gray-500 uppercase block">{{ t('hospitalization.admission_reason') }}</label>
      <textarea v-model="admissionReason" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"></textarea>
      <div class="flex gap-2">
        <button @click="submitAdmit" class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition">
          {{ t('hospitalization.confirm') }}
        </button>
        <button @click="showAdmitForm = false" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition">
          {{ t('hospitalization.cancel') }}
        </button>
      </div>
    </div>

    <div v-if="openStay" class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-xs text-gray-500">{{ t('hospitalization.admitted_since') }}</div>
          <div class="text-sm font-semibold text-gray-900">{{ formatDate(openStay.admitted_at) }} ({{ daysSince(openStay.admitted_at) }} {{ t('hospitalization.days_count') }})</div>
        </div>
        <div class="text-right">
          <div class="text-xs text-gray-500">{{ t('hospitalization.current_status') }}</div>
          <div class="text-sm font-semibold" :class="statusColorClass(latestStatus)">
            {{ latestStatus ? t(`hospitalization.status.${latestStatus}`) : t('hospitalization.no_status_yet') }}
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <button @click="showStatusForm = !showStatusForm" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition">
          {{ t('hospitalization.update_status_button') }}
        </button>
        <button @click="showDischargeForm = !showDischargeForm" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition">
          {{ t('hospitalization.discharge_button') }}
        </button>
      </div>

      <div v-if="showStatusForm" class="space-y-2 p-3 bg-gray-50 rounded-xl">
        <select v-model="newStatus" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option v-for="s in CLINICAL_STATUSES" :key="s" :value="s">{{ t(`hospitalization.status.${s}`) }}</option>
        </select>
        <textarea v-model="statusNote" :placeholder="t('hospitalization.status_note')" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"></textarea>
        <button @click="submitStatusUpdate" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition">
          {{ t('hospitalization.confirm') }}
        </button>
      </div>

      <div v-if="showDischargeForm" class="space-y-2 p-3 bg-gray-50 rounded-xl">
        <select v-model="dischargeDisposition" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="" disabled>{{ t('hospitalization.discharge_disposition_label') }}</option>
          <option v-for="d in DISCHARGE_DISPOSITIONS" :key="d" :value="d">{{ t(`hospitalization.disposition.${d}`) }}</option>
        </select>
        <textarea v-model="dischargeNote" :placeholder="t('hospitalization.discharge_note')" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"></textarea>
        <button
          @click="submitDischarge"
          :disabled="!dischargeDisposition"
          class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {{ t('hospitalization.confirm') }}
        </button>
      </div>
    </div>

    <div v-if="hospitalizationStore.patientHistory.length > 0" class="mt-6 pt-4 border-t border-gray-100">
      <h4 class="text-xs font-bold text-gray-500 uppercase mb-2">{{ t('hospitalization.history_title') }}</h4>
      <div class="space-y-2">
        <div v-for="stay in hospitalizationStore.patientHistory" :key="stay.id" class="text-xs text-gray-600 flex justify-between">
          <span>{{ formatDate(stay.admitted_at) }} → {{ stay.discharged_at ? formatDate(stay.discharged_at) : '…' }}</span>
          <span v-if="stay.discharge_disposition">{{ t(`hospitalization.disposition.${stay.discharge_disposition}`) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { useHospitalizationStore, DISCHARGE_DISPOSITIONS, CLINICAL_STATUSES } from '@/stores/hospitalizationStore';

const { t } = useI18n();
const hospitalizationStore = useHospitalizationStore();

const props = defineProps({
  patientId: {
    type: Number,
    required: true,
  },
});

const showAdmitForm = ref(false);
const admissionReason = ref('');
const showStatusForm = ref(false);
const newStatus = ref('AMELIORATION');
const statusNote = ref('');
const showDischargeForm = ref(false);
const dischargeDisposition = ref('');
const dischargeNote = ref('');

const openStay = computed(() => hospitalizationStore.patientHistory.find((s) => !s.discharged_at) || null);
const latestStatus = computed(() => {
  if (!openStay.value || !openStay.value.status_updates?.length) return null;
  return openStay.value.status_updates[0].status;
});

function formatDate(d) {
  return dayjs(d).format('DD/MM/YYYY HH:mm');
}
function daysSince(d) {
  return dayjs().diff(dayjs(d), 'day');
}
function statusColorClass(status) {
  if (status === 'AMELIORATION') return 'text-emerald-700';
  if (status === 'AGGRAVATION') return 'text-red-700';
  return 'text-gray-700';
}

async function submitAdmit() {
  await hospitalizationStore.admit(props.patientId, admissionReason.value);
  showAdmitForm.value = false;
  admissionReason.value = '';
}

async function submitStatusUpdate() {
  if (!openStay.value) return;
  await hospitalizationStore.addStatusUpdate(openStay.value.id, newStatus.value, statusNote.value, props.patientId);
  showStatusForm.value = false;
  statusNote.value = '';
}

async function submitDischarge() {
  if (!openStay.value || !dischargeDisposition.value) return;
  await hospitalizationStore.discharge(openStay.value.id, dischargeDisposition.value, dischargeNote.value, props.patientId);
  showDischargeForm.value = false;
  dischargeDisposition.value = '';
  dischargeNote.value = '';
}

onMounted(() => {
  hospitalizationStore.fetchPatientHistory(props.patientId);
});
</script>
```

- [ ] **Step 2: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...` (composant pas encore importé ailleurs — juste vérifier l'absence d'erreur de syntaxe Vue/JS).

- [ ] **Step 3: Commit**

```bash
git add ah2-admin-web/src/components/hospitalization/HospitalizationCard.vue
git commit -m "feat: HospitalizationCard.vue (admit/status/discharge/history)"
```

---

## Task 9: Intégration dans `PatientDetailView.vue`

**Files:**
- Modify: `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue`

**Interfaces:**
- Consumes: `HospitalizationCard.vue` (Task 8), `authStore.hasRole` (déjà existant, motif déjà utilisé dans ce fichier pour `canCreateConsultation`).

- [ ] **Step 1: Ajouter un onglet "Hospitalisation", gardé par rôle**

Modifier le bloc `<nav>` des onglets (juste après le bouton `PHARMA`, avant les boutons `TOXICO`/`SPIRITUEL`) :

```html
                    <button v-if="authStore.hasRole(['medecin', 'nurse'])" @click="currentTab = 'HOSPITALISATION'" :class="[currentTab === 'HOSPITALISATION' ? 'border-red-500 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700', 'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center transition duration-150']">
                        <BuildingOffice2Icon class="h-5 w-5 mr-2" /> {{ t('hospitalization.card_title') }}
                    </button>
```

Ajouter le contenu de l'onglet, après le `</div>` qui ferme le bloc `currentTab === 'PHARMA'` et avant celui de `TOXICO` :

```html
                <div v-if="currentTab === 'HOSPITALISATION'">
                    <HospitalizationCard :patient-id="dossierStore.patientSummary.patient_id" />
                </div>
```

- [ ] **Step 2: Importer le composant et l'icône**

Dans le `<script setup>`, ajouter :

```javascript
import HospitalizationCard from '@/components/hospitalization/HospitalizationCard.vue';
```

Ajouter `BuildingOffice2Icon` à l'import déjà existant depuis `@heroicons/vue/24/outline` (repérer la ligne d'import groupée d'icônes déjà présente dans ce fichier et y ajouter `BuildingOffice2Icon`).

- [ ] **Step 3: Vérifier explicitement le garde de rôle (Review Focus)**

Relire le fichier modifié et confirmer par la lecture (pas seulement le build) que :
1. Le bouton d'onglet "Hospitalisation" est bien derrière `v-if="authStore.hasRole(['medecin', 'nurse'])"`.
2. `PatientDetailView.vue` est réutilisé par `admin`/`ToxicoManager` (route `/dashboard/patients`) — confirmer qu'aucun de ces rôles ne peut voir l'onglet en inspectant que la condition ci-dessus est bien évaluée à `false` pour eux (`authStore.hasRole(['medecin', 'nurse'])` retourne `false` pour un utilisateur dont le rôle n'est ni l'un ni l'autre — comportement déjà garanti par l'implémentation existante de `hasRole`, aucune modification nécessaire ici, seulement la vérification que ce nouvel onglet suit bien le même motif que `canCreateConsultation` déjà présent dans ce fichier).

- [ ] **Step 4: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, nouveau chunk contenant `HospitalizationCard` visible dans la sortie.

- [ ] **Step 5: Commit**

```bash
git add ah2-admin-web/src/views/modules/patients/PatientDetailView.vue
git commit -m "feat: hospitalization tab in patient dossier (médecin/nurse only)"
```

---

## Task 10: Écran liste `/medical/hospitalizations`

**Files:**
- Create: `ah2-admin-web/src/views/modules/hospitalization/HospitalizationsList.vue`
- Modify: `ah2-admin-web/src/router/index.js`
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue`

**Interfaces:**
- Consumes: `useHospitalizationStore()` (Task 6), `HospitalizationCard.vue` n'est pas réutilisé ici (actions rapides inline, plus simples que la carte dossier complète).

- [ ] **Step 1: Écrire l'écran liste**

```vue
<template>
  <div class="space-y-6 w-full">

    <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('hospitalization.title') }}</h1>
      <p class="text-sm text-gray-500">{{ t('hospitalization.subtitle') }}</p>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="hospitalizationStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></span>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.admitted_since') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.days') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.current_status') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('appointments.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="stay in hospitalizationStore.current" :key="stay.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <button @click="goToDossier(stay.patient_id)" class="text-sm font-medium text-emerald-700 hover:underline">
                  {{ stay.patient_first_name }} {{ stay.patient_last_name }}
                </button>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(stay.admitted_at) }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ daysSince(stay.admitted_at) }}</td>
              <td class="px-6 py-4 text-sm" :class="statusColorClass(latestStatusOf(stay))">
                {{ latestStatusOf(stay) ? t(`hospitalization.status.${latestStatusOf(stay)}`) : t('hospitalization.no_status_yet') }}
              </td>
              <td class="px-6 py-4 text-right">
                <button @click="goToDossier(stay.patient_id)" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition">
                  {{ t('appointments.actions.view_dossier') }}
                </button>
              </td>
            </tr>
            <tr v-if="hospitalizationStore.current.length === 0">
              <td colspan="5" class="px-6 py-8 text-center text-gray-500 italic">
                {{ t('hospitalization.empty_list') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import dayjs from 'dayjs';
import { useHospitalizationStore } from '@/stores/hospitalizationStore';

const { t } = useI18n();
const router = useRouter();
const hospitalizationStore = useHospitalizationStore();

function formatDate(d) {
  return dayjs(d).format('DD/MM/YYYY HH:mm');
}
function daysSince(d) {
  return dayjs().diff(dayjs(d), 'day');
}
function latestStatusOf(stay) {
  return stay.status_updates?.length ? stay.status_updates[0].status : null;
}
function statusColorClass(status) {
  if (status === 'AMELIORATION') return 'text-emerald-700 font-medium';
  if (status === 'AGGRAVATION') return 'text-red-700 font-medium';
  return 'text-gray-600';
}
function goToDossier(patientId) {
  router.push(`/medical/patients/${patientId}`);
}

onMounted(() => {
  hospitalizationStore.fetchCurrent();
});
</script>
```

- [ ] **Step 2: Ajouter la route**

Dans `ah2-admin-web/src/router/index.js`, ajouter un enfant au bloc `/medical` (à côté de `path: 'doctors'`) :

```javascript
      {
        path: 'hospitalizations',
        name: 'medical-hospitalizations',
        component: () => import('@/views/modules/hospitalization/HospitalizationsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
```

- [ ] **Step 3: Ajouter l'entrée de menu**

Dans `ah2-admin-web/src/components/layout/MedicalLayout.vue`, ajouter au tableau des items de menu (à côté de l'entrée `/medical/doctors`) :

```javascript
  {
    path: '/medical/hospitalizations',
    labelKey: 'hospitalization.title',
    icon: BuildingOffice2Icon,
  },
```

Vérifier que `BuildingOffice2Icon` est bien importé depuis `@heroicons/vue/24/outline` en haut du fichier (ajouter à l'import groupé déjà existant si absent).

- [ ] **Step 4: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, nouveau chunk `HospitalizationsList-*.js` visible dans la sortie.

- [ ] **Step 5: Commit**

```bash
git add ah2-admin-web/src/views/modules/hospitalization/ ah2-admin-web/src/router/index.js ah2-admin-web/src/components/layout/MedicalLayout.vue
git commit -m "feat: hospitalizations list screen (/medical/hospitalizations)"
```
