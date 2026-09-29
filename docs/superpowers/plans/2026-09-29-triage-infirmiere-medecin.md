# Triage infirmière → médecin + assignation RDV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre à une infirmière de transmettre un dossier médical à un médecin précis (ou à une file d'attente partagée) avec notification, donner au médecin un accès "Patients en attente" depuis son dashboard avec accès direct à l'historique du patient, et corriger l'assignation de RDV (actuellement silencieusement attribuée au créateur du RDV).

**Architecture:** 4 nouveaux champs sur `medical_records` (`needs_doctor_review`, `assigned_doctor_id`, `reviewed_by`, `reviewed_at`) portent la file d'attente ; `appointments.doctor_id` devient nullable. La création de dossier médical passe par PowerSync (écriture locale SQLite puis synchronisation en arrière-plan, chantier 4) — ce chantier doit donc étendre le schéma local PowerSync et le connecteur de synchronisation en plus du backend, pas seulement l'API HTTP. Le tableau de bord médecin (chantier précédent) gagne un nouvel endpoint liste (pas un chiffre agrégé) pour la file d'attente, et un nouveau endpoint "liste des médecins" réutilisé à la fois par le sélecteur RDV et le sélecteur de dossier médical.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PowerSync (SQLite local + connecteur de synchronisation), pytest avec vrais appels HTTP + vraie base Postgres, Vue 3 `<script setup>`, Pinia, vue-i18n.

**Spec:** `docs/superpowers/specs/2026-09-29-triage-infirmiere-medecin-design.md`

## Global Constraints

- `needs_doctor_review`/`assigned_doctor_id` sont posés une seule fois, à la création du dossier médical — pas éditables via le formulaire de modification existant (hors périmètre, décision spec).
- `assigned_doctor_id = NULL` avec `needs_doctor_review=true` = file d'attente partagée, visible par **tous** les médecins.
- `POST /medical_records/{id}/claim` est réservé au rôle `medecin` uniquement (pas `nurse`).
- La notification (`patient_pending_review`) part uniquement quand un médecin précis est assigné à la création — jamais pour la file partagée, jamais pour l'assignation de RDV.
- Aucun effet sur une garde de rôle existante ailleurs dans le projet.
- La création de dossier médical par `medecin`/`nurse` écrit d'abord en local (PowerSync SQLite, `medicalRecordStore.js::createMedicalRecord`) avant synchronisation — toute nouvelle donnée saisie à la création doit traverser ce chemin en plus de l'API HTTP directe, sinon elle ne sera jamais envoyée au serveur.

## Review Focus

- Un dossier assigné à un médecin précis n'apparaît jamais dans la file d'un autre médecin ; un dossier avec `assigned_doctor_id=NULL` apparaît dans la file de tous. Testé en Task 2 (repository) et Task 5 (HTTP).
- `claim()` sur un dossier déjà pris en charge par quelqu'un d'autre doit être refusé (409), jamais une seconde prise en charge silencieuse — scénario réel avec plusieurs médecins. Testé en Task 2 et Task 5.
- La notification part uniquement à l'assignation explicite d'un médecin précis, jamais pour la file partagée ni pour un dossier qui ne coche pas "à transmettre au médecin". Testé en Task 3.
- La saisie hors ligne (PowerSync) des 2 nouveaux champs doit atteindre le serveur au même titre que les champs existants du dossier médical — pas de test automatisé possible pour ce chemin (aucun test PowerSync dans ce projet), mais une relecture explicite de bout en bout (schéma local → connecteur → gateway → backend) est requise en Task 6.
- `nurse` ne peut pas appeler `claim()` (403) ; un RDV assigné à un médecin apparaît sur son dashboard, un RDV non assigné (`doctor_id=NULL`) n'apparaît sur le dashboard d'aucun médecin sans provoquer d'erreur. Testé en Task 5 et Task 8.
- Un choix explicite "Non assigné" sur le formulaire RDV doit réellement laisser `doctor_id=NULL` en base, jamais retomber silencieusement sur le créateur — c'est le bug d'origine signalé par l'utilisateur, un défaut du repli automatique de `book_appointment()` (`"doctor_id" not in data or data.get("doctor_id") is None`) le referait autrement, puisque `payload.model_dump()` envoie toujours la clé `doctor_id`, y compris à `None`. Testé en Task 8.

---

## Task 1: Migration + modèles

**Files:**
- Create: `alembic/versions/017_triage_infirmiere_medecin.py`
- Modify: `models/medical_record.py`
- Modify: `models/appointment.py`
- Test: `tests/test_triage_schema.py`

**Interfaces:**
- Produces: colonnes `medical_records.needs_doctor_review`/`assigned_doctor_id`/`reviewed_by`/`reviewed_at`, `appointments.doctor_id` nullable. Relations SQLAlchemy `MedicalRecord.assigned_doctor`/`MedicalRecord.reviewed_by_user` — consommées par Task 2/4.

- [ ] **Step 1: Écrire la migration**

```python
# alembic/versions/017_triage_infirmiere_medecin.py
"""medical_records triage fields + appointments.doctor_id nullable

Revision ID: 017_triage_infirmiere_medecin
Revises: 016_nurse_shifts
Create Date: 2026-09-29

"""
from alembic import op

revision = '017_triage_infirmiere_medecin'
down_revision = '016_nurse_shifts'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.medical_records
            ADD COLUMN IF NOT EXISTS needs_doctor_review boolean NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS assigned_doctor_id integer REFERENCES users(user_id),
            ADD COLUMN IF NOT EXISTS reviewed_by integer REFERENCES users(user_id),
            ADD COLUMN IF NOT EXISTS reviewed_at timestamp;

        CREATE INDEX IF NOT EXISTS ix_medical_records_pending_review
            ON medical_records (needs_doctor_review, reviewed_at)
            WHERE needs_doctor_review = true AND reviewed_at IS NULL;

        ALTER TABLE public.appointments
            ALTER COLUMN doctor_id DROP NOT NULL;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.appointments
            ALTER COLUMN doctor_id SET NOT NULL;

        DROP INDEX IF EXISTS ix_medical_records_pending_review;
        ALTER TABLE public.medical_records
            DROP COLUMN IF EXISTS reviewed_at,
            DROP COLUMN IF EXISTS reviewed_by,
            DROP COLUMN IF EXISTS assigned_doctor_id,
            DROP COLUMN IF EXISTS needs_doctor_review;
    """)
```

Note : `ALTER COLUMN doctor_id DROP NOT NULL` échouera si des lignes existantes ont `doctor_id NULL` — impossible ici puisque la colonne était `NOT NULL` jusqu'ici, donc aucune ligne existante n'a cette valeur. Pas de backfill nécessaire.

- [ ] **Step 2: Appliquer la migration contre la base locale réelle**

```bash
alembic upgrade head
```

Vérifier `alembic current` → `017_triage_infirmiere_medecin (head)`.

- [ ] **Step 3: Étendre le modèle `MedicalRecord`**

Dans `models/medical_record.py`, ajouter après `uuid = Column(...)` :

```python
    needs_doctor_review = Column(Boolean, nullable=False, default=False, server_default="false")
    assigned_doctor_id = Column(Integer, ForeignKey('users.user_id'))
    reviewed_by = Column(Integer, ForeignKey('users.user_id'))
    reviewed_at = Column(DateTime)
```

Ajouter `Boolean` à l'import existant (ligne 3 : `from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey, Boolean`). Ajouter les relations après `patient = relationship(...)` :

```python
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_id])
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by])
```

`foreign_keys=[...]` est nécessaire ici (comme pour `Hospitalization`/`NurseShift` dans les chantiers précédents) car deux colonnes distinctes de ce modèle référencent `users.user_id` (`created_by` a déjà sa propre relation implicite non nommée aujourd'hui — ne pas y toucher, seules les 2 nouvelles relations ont besoin de `foreign_keys=`).

- [ ] **Step 4: Rendre `doctor_id` nullable côté modèle**

Dans `models/appointment.py`, retirer `nullable=False` de la colonne `doctor_id` :

```python
    doctor_id = Column(
        Integer,
        ForeignKey('users.user_id', ondelete='CASCADE')
    )
```

- [ ] **Step 5: Écrire un test qui vérifie le schéma réel**

```python
# tests/test_triage_schema.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from tests.conftest import create_test_user, create_test_patient


def test_medical_records_triage_columns_exist(db_session):
    row = db_session.execute(text("""
        SELECT column_name, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'medical_records'
          AND column_name IN ('needs_doctor_review', 'assigned_doctor_id', 'reviewed_by', 'reviewed_at')
    """)).fetchall()
    cols = {r[0]: r for r in row}
    assert set(cols.keys()) == {'needs_doctor_review', 'assigned_doctor_id', 'reviewed_by', 'reviewed_at'}
    assert cols['needs_doctor_review'][1] == 'NO'


def test_appointments_doctor_id_is_nullable(db_session):
    row = db_session.execute(text("""
        SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'appointments' AND column_name = 'doctor_id'
    """)).fetchone()
    assert row[0] == 'YES'


def test_appointment_without_doctor_id_can_be_inserted(db_session):
    nurse = create_test_user(db_session, "triage_schema_nurse", "nurse")
    patient_id, _ = create_test_patient(db_session, nurse)
    db_session.execute(text("""
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status)
        VALUES (:patient_id, NULL, CURRENT_DATE, '09:00', 'pending')
    """), {"patient_id": patient_id})
    db_session.flush()
```

- [ ] **Step 6: Lancer les tests**

```bash
python -m pytest tests/test_triage_schema.py -v
```

Attendu : 3 passed.

- [ ] **Step 7: Régénérer `ci/schema_only.sql`**

```bash
pg_dump --schema-only --no-owner --no-privileges "$DATABASE_URL" > ci/schema_only.sql
```

Vérifier via `git diff ci/schema_only.sql` que le diff contient exactement les 4 nouvelles colonnes + index sur `medical_records`, et le changement `NOT NULL` → nullable sur `appointments.doctor_id`, rien d'inattendu.

- [ ] **Step 8: Commit**

```bash
git add alembic/versions/017_triage_infirmiere_medecin.py models/medical_record.py models/appointment.py ci/schema_only.sql tests/test_triage_schema.py
git commit -m "feat: triage fields on medical_records + nullable appointments.doctor_id"
```

---

## Task 2: Repository (file d'attente + prise en charge)

**Files:**
- Modify: `repositories/medical_repo.py`
- Test: `tests/test_medical_repo_triage.py`

**Interfaces:**
- Produces: `MedicalRecordRepository.list_pending_for_doctor(doctor_id, limit=20) -> list[MedicalRecord]`, `MedicalRecordRepository.claim(record_id, doctor_id) -> MedicalRecord` (lève `ValueError` si introuvable ou déjà pris en charge) — consommés par Task 3 (controller).

- [ ] **Step 1: Écrire les tests (avant l'implémentation)**

```python
# tests/test_medical_repo_triage.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from repositories.medical_repo import MedicalRecordRepository
from tests.conftest import create_test_user, create_test_patient


def _create_pending_record(session, repo, patient_id, creator, assigned_doctor_id=None):
    data = {
        "patient_id": patient_id,
        "motif_code": "consultation",
        "diagnosis": None, "treatment": None, "notes": None,
        "marital_status": None, "bp": None, "temperature": None,
        "weight": None, "height": None, "medical_history": None,
        "allergies": None, "symptoms": None, "severity": None,
        "created_by": creator.user_id, "created_by_name": creator.username,
    }
    repo.create(data)
    session.flush()
    record = repo.get_last_for_patient(patient_id)
    record.needs_doctor_review = True
    record.assigned_doctor_id = assigned_doctor_id
    session.commit()
    return record


def test_list_pending_for_doctor_returns_own_assignment(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse1", "nurse")
    medecin_a = create_test_user(db_session, "triage_repo_medecin_a", "medecin")
    medecin_b = create_test_user(db_session, "triage_repo_medecin_b", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    record = _create_pending_record(db_session, repo, patient_id, nurse, assigned_doctor_id=medecin_a.user_id)

    pending_a = repo.list_pending_for_doctor(medecin_a.user_id)
    pending_b = repo.list_pending_for_doctor(medecin_b.user_id)

    assert record.record_id in [r.record_id for r in pending_a]
    assert record.record_id not in [r.record_id for r in pending_b]


def test_list_pending_for_doctor_includes_shared_pool(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse2", "nurse")
    medecin_a = create_test_user(db_session, "triage_repo_medecin_a2", "medecin")
    medecin_b = create_test_user(db_session, "triage_repo_medecin_b2", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    record = _create_pending_record(db_session, repo, patient_id, nurse, assigned_doctor_id=None)

    pending_a = repo.list_pending_for_doctor(medecin_a.user_id)
    pending_b = repo.list_pending_for_doctor(medecin_b.user_id)

    assert record.record_id in [r.record_id for r in pending_a]
    assert record.record_id in [r.record_id for r in pending_b]


def test_list_pending_excludes_records_not_flagged(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse3", "nurse")
    medecin = create_test_user(db_session, "triage_repo_medecin3", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    repo.create({
        "patient_id": patient_id, "motif_code": "consultation",
        "diagnosis": None, "treatment": None, "notes": None,
        "marital_status": None, "bp": None, "temperature": None,
        "weight": None, "height": None, "medical_history": None,
        "allergies": None, "symptoms": None, "severity": None,
        "created_by": nurse.user_id, "created_by_name": nurse.username,
    })
    db_session.flush()

    pending = repo.list_pending_for_doctor(medecin.user_id)
    assert pending == []


def test_claim_marks_reviewed_and_assigns_if_pool(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse4", "nurse")
    medecin = create_test_user(db_session, "triage_repo_medecin4", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    record = _create_pending_record(db_session, repo, patient_id, nurse, assigned_doctor_id=None)

    claimed = repo.claim(record.record_id, medecin.user_id)

    assert claimed.reviewed_by == medecin.user_id
    assert claimed.reviewed_at is not None
    assert claimed.assigned_doctor_id == medecin.user_id
    assert repo.list_pending_for_doctor(medecin.user_id) == []


def test_claim_already_reviewed_raises(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse5", "nurse")
    medecin_a = create_test_user(db_session, "triage_repo_medecin_a5", "medecin")
    medecin_b = create_test_user(db_session, "triage_repo_medecin_b5", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    record = _create_pending_record(db_session, repo, patient_id, nurse, assigned_doctor_id=None)
    repo.claim(record.record_id, medecin_a.user_id)

    with pytest.raises(ValueError, match="déjà"):
        repo.claim(record.record_id, medecin_b.user_id)


def test_claim_unknown_record_raises(db_session):
    medecin = create_test_user(db_session, "triage_repo_medecin6", "medecin")
    repo = MedicalRecordRepository(db_session)
    with pytest.raises(ValueError, match="introuvable"):
        repo.claim(999999999, medecin.user_id)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

```bash
python -m pytest tests/test_medical_repo_triage.py -v
```

Attendu : ÉCHEC avec `AttributeError: 'MedicalRecordRepository' object has no attribute 'list_pending_for_doctor'`.

- [ ] **Step 3: Ajouter les méthodes au repository**

Dans `repositories/medical_repo.py`, ajouter après `get_last_for_patient` (avant le commentaire `#KPI Dashboard Medecin`) :

```python
    def list_pending_for_doctor(self, doctor_id: int, limit: int = 20):
        """File d'attente triage : dossiers marques a transmettre au
        medecin, pas encore pris en charge, assignes a ce medecin OU dans
        la file partagee (assigned_doctor_id IS NULL)."""
        return (
            self.session.query(self.model)
            .filter(self.model.needs_doctor_review == True)
            .filter(self.model.reviewed_at.is_(None))
            .filter(
                (self.model.assigned_doctor_id == doctor_id) |
                (self.model.assigned_doctor_id.is_(None))
            )
            .order_by(self.model.consultation_date.asc())
            .limit(limit)
            .all()
        )

    def claim(self, record_id: int, doctor_id: int):
        """Prise en charge : pose reviewed_by/reviewed_at, et assigned_doctor_id
        si le dossier venait de la file partagee. Refuse si deja pris en
        charge par quelqu'un d'autre - protection contre la course a
        plusieurs medecins (scenario explicitement anticipe par ce chantier)."""
        record = self.session.get(self.model, record_id)
        if record is None:
            raise ValueError(f"Dossier medical introuvable (ID={record_id}).")
        if record.reviewed_at is not None:
            raise ValueError("Ce dossier a déjà été pris en charge.")
        record.reviewed_by = doctor_id
        record.reviewed_at = func.now()
        if record.assigned_doctor_id is None:
            record.assigned_doctor_id = doctor_id
        self.session.commit()
        self.session.refresh(record)
        return record
```

`func` est déjà importé dans ce fichier (utilisé par les méthodes KPI existantes) — pas de nouvel import nécessaire.

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_medical_repo_triage.py -v
```

Attendu : 6 passed.

- [ ] **Step 5: Commit**

```bash
git add repositories/medical_repo.py tests/test_medical_repo_triage.py
git commit -m "feat: MedicalRecordRepository triage queue (list_pending_for_doctor/claim)"
```

---

## Task 3: Controller (extension création + prise en charge + notification)

**Files:**
- Modify: `controller/medical_controller.py`
- Test: `tests/test_medical_controller_triage.py`

**Interfaces:**
- Consumes: `repositories.medical_repo.MedicalRecordRepository` (Task 2), `repositories.notification_repo.NotificationRepository.create(recipient_user_id, type, payload)` (déjà existant).
- Produces: `MedicalRecordController.create_record(data)` étendu (accepte `needs_doctor_review`/`assigned_doctor_id`, envoie une notification si pertinent), `MedicalRecordController.claim_review(record_id) -> MedicalRecord` (lève `PermissionError` si l'appelant n'est pas `medecin`) — consommés par Task 5 (endpoints).

- [ ] **Step 1: Lire le fichier actuel pour confirmer le point d'insertion**

Lire `controller/medical_controller.py` en entier — en particulier `__init__` (pour confirmer si `notification_repo` doit être ajouté comme paramètre optionnel, même motif que `HospitalizationController`), `create_record()` (lignes ~119-180), et `get_last_for_patient()` déjà existant (ligne 271).

- [ ] **Step 2: Étendre le constructeur**

Ajouter `notification_repo` optionnel au constructeur, même motif que `HospitalizationController` :

```python
    def __init__(self, repo=None, patient_controller=None, current_user=None, audit_repo: Optional[AuditRepository] = None, notification_repo=None):
        self.repo = repo or MedicalRecordRepository() # type: ignore
        self.patient_ctrl = patient_controller
        self.user = current_user
        self.audit_repo = audit_repo
        self.notification_repo = notification_repo
        self.logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Étendre `create_record()`**

Juste après le bloc `# 1. Création via Repo (qui appelle la Procédure SQL corrigée)` / `record = self.repo.create(data)`, ajouter :

```python
        # Triage infirmiere -> medecin (2026-09-29) : needs_doctor_review/
        # assigned_doctor_id ne passent pas par la procedure stockee
        # create_medical_record (non modifiee pour ce chantier, evite
        # d'alourdir une routine SQL deja complexe) - on relit le dossier
        # via get_last_for_patient (motif deja etabli, voir l'endpoint
        # POST /medical_records/ qui fait exactement cette relecture pour
        # renvoyer la reponse HTTP) et on pose les 2 colonnes en ORM simple.
        if data.get('needs_doctor_review'):
            created = self.repo.get_last_for_patient(data['patient_id'])
            if created:
                created.needs_doctor_review = True
                created.assigned_doctor_id = data.get('assigned_doctor_id')
                self.repo.session.commit()
                self._notify_assigned_doctor(created, data)
```

Ajouter la méthode privée `_notify_assigned_doctor` (avant ou après `create_record`, style cohérent avec `_notify_team_of_aggravation` de `HospitalizationController`) :

```python
    def _notify_assigned_doctor(self, record, data):
        """Notifie le medecin assigne - jamais pour la file partagee
        (assigned_doctor_id=None, on ne sait pas encore a qui notifier),
        jamais bloquant pour la creation du dossier."""
        if not (self.notification_repo and record.assigned_doctor_id):
            return
        try:
            patient = self.patient_ctrl.repo.get(record.patient_id) if self.patient_ctrl else None
            patient_name = f"{getattr(patient, 'first_name', '') or ''} {getattr(patient, 'last_name', '') or ''}".strip() or "Patient"
            payload = {
                "record_id": record.record_id,
                "patient_id": record.patient_id,
                "patient_name": patient_name,
                "motif_code": record.motif_code,
                "created_by_name": data.get('created_by_name'),
            }
            self.notification_repo.create(
                recipient_user_id=record.assigned_doctor_id,
                type="patient_pending_review",
                payload=payload,
            )
        except Exception:
            self.logger.exception("Echec notification patient_pending_review")
```

- [ ] **Step 4: Ajouter `claim_review()`**

Ajouter près de `get_last_for_patient` (section lecture) :

```python
    def claim_review(self, record_id: int):
        roles = getattr(self.user, "roles", []) or []
        if "medecin" not in roles:
            raise PermissionError("Seul un médecin peut prendre en charge un dossier en attente.")
        return self.repo.claim(record_id, self.user.user_id)

    def list_pending_review(self):
        doctor_id = getattr(self.user, "user_id", None)
        return self.repo.list_pending_for_doctor(doctor_id)
```

- [ ] **Step 5: Écrire les tests**

```python
# tests/test_medical_controller_triage.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from controller.medical_controller import MedicalRecordController
from repositories.medical_repo import MedicalRecordRepository
from repositories.notification_repo import NotificationRepository
from repositories.patient_repo import PatientRepository
from controller.patient_controller import PatientController
from models.notification import Notification
from tests.conftest import create_test_user, create_test_patient


def _make_controller(db_session, current_user, with_notifications=True):
    repo = MedicalRecordRepository(db_session)
    patient_ctrl = PatientController(repo=PatientRepository(db_session), current_user=current_user)
    notification_repo = NotificationRepository(db_session) if with_notifications else None
    return MedicalRecordController(repo=repo, patient_controller=patient_ctrl, current_user=current_user, notification_repo=notification_repo)


def test_create_record_with_assigned_doctor_sends_notification(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse1", "nurse")
    medecin = create_test_user(db_session, "triage_ctrl_medecin1", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    ctrl = _make_controller(db_session, nurse)

    ctrl.create_record({
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": medecin.user_id,
    })

    notifs = db_session.query(Notification).filter(Notification.recipient_user_id == medecin.user_id, Notification.type == "patient_pending_review").all()
    assert len(notifs) == 1
    assert notifs[0].payload["patient_id"] == patient_id


def test_create_record_shared_pool_sends_no_notification(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse2", "nurse")
    patient_id, _ = create_test_patient(db_session, nurse)
    ctrl = _make_controller(db_session, nurse)

    ctrl.create_record({
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": None,
    })

    notifs = db_session.query(Notification).filter(Notification.type == "patient_pending_review").all()
    assert notifs == []


def test_create_record_without_flag_sends_no_notification(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse3", "nurse")
    medecin = create_test_user(db_session, "triage_ctrl_medecin3", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    ctrl = _make_controller(db_session, nurse)

    ctrl.create_record({"patient_id": patient_id, "motif_code": "consultation"})

    notifs = db_session.query(Notification).filter(Notification.recipient_user_id == medecin.user_id).all()
    assert notifs == []


def test_claim_review_forbidden_for_nurse(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse4", "nurse")
    patient_id, _ = create_test_patient(db_session, nurse)
    ctrl = _make_controller(db_session, nurse)
    ctrl.create_record({"patient_id": patient_id, "motif_code": "consultation", "needs_doctor_review": True, "assigned_doctor_id": None})
    record = ctrl.repo.get_last_for_patient(patient_id)

    with pytest.raises(PermissionError):
        ctrl.claim_review(record.record_id)


def test_claim_review_allowed_for_medecin(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse5", "nurse")
    medecin = create_test_user(db_session, "triage_ctrl_medecin5", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    nurse_ctrl = _make_controller(db_session, nurse)
    nurse_ctrl.create_record({"patient_id": patient_id, "motif_code": "consultation", "needs_doctor_review": True, "assigned_doctor_id": None})
    record = nurse_ctrl.repo.get_last_for_patient(patient_id)

    medecin_ctrl = _make_controller(db_session, medecin)
    claimed = medecin_ctrl.claim_review(record.record_id)

    assert claimed.reviewed_by == medecin.user_id
```

- [ ] **Step 6: Lancer les tests**

```bash
python -m pytest tests/test_medical_controller_triage.py -v
```

Attendu : 5 passed.

- [ ] **Step 7: Commit**

```bash
git add controller/medical_controller.py tests/test_medical_controller_triage.py
git commit -m "feat: MedicalRecordController triage (create_record extension, claim_review, notification)"
```

---

## Task 4: Endpoint "liste des médecins" partagé

**Files:**
- Create: `api_backend/backend_app/routes/doctor_dashboard/doctors_schema.py`
- Modify: `api_backend/backend_app/routes/doctor_dashboard/doctor_dashboard_endpoint.py`
- Test: `tests/test_doctor_dashboard_endpoint.py`

**Interfaces:**
- Consumes: `UserRepository.get_users_by_role_names(["medecin"])` (déjà existant, déjà utilisé pour le planning infirmiers).
- Produces: `GET /doctor-dashboard/doctors -> list[ActiveDoctorOut]` — consommé par Task 7 (sélecteur RDV) et Task 8 (sélecteur dossier médical).

- [ ] **Step 1: Écrire le schéma**

```python
# api_backend/backend_app/routes/doctor_dashboard/doctors_schema.py
from pydantic import BaseModel


class ActiveDoctorOut(BaseModel):
    user_id: int
    full_name: str
```

- [ ] **Step 2: Ajouter la route**

Dans `api_backend/backend_app/routes/doctor_dashboard/doctor_dashboard_endpoint.py`, ajouter l'import `from .doctors_schema import ActiveDoctorOut` et `from repositories.user_repo import UserRepository`, puis la route (même motif que `GET /nurse-shifts/nurses`) :

```python
def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


@router.get(
    "/doctors",
    response_model=list[ActiveDoctorOut],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def list_doctors(user_repo: UserRepository = Depends(get_user_repo)):
    return [
        ActiveDoctorOut(user_id=u.user_id, full_name=u.full_name)
        for u in user_repo.get_users_by_role_names(["medecin"])
    ]
```

`doctor_dashboard_endpoint.py` n'a pas de `get_db` propre aujourd'hui (il compose uniquement des `Depends()` d'autres modules) — ajouter `get_db()` local minimal (même motif que tous les autres modules du projet) :

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

avec `from ...database import SessionLocal` en tête de fichier si absent (vérifier avant d'ajouter — l'import peut déjà exister via un autre chemin).

- [ ] **Step 3: Écrire le test HTTP**

Ajouter à `tests/test_doctor_dashboard_endpoint.py` (le fichier importe déjà `create_test_user`, `auth_headers`, `doctor_dashboard_endpoint`) :

```python
def test_list_doctors_returns_only_medecin_role(db_session, api_client):
    medecin = create_test_user(db_session, "triage_ep_medecin_list", "medecin", password=TEST_PASSWORD)
    create_test_user(db_session, "triage_ep_nurse_list", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "triage_ep_medecin_list", TEST_PASSWORD)

    resp = client.get("/doctor-dashboard/doctors", headers=headers)

    assert resp.status_code == 200
    user_ids = [d["user_id"] for d in resp.json()]
    assert medecin.user_id in user_ids
```

- [ ] **Step 4: Lancer les tests + vérifier le démarrage de l'app**

```bash
python -c "from api_backend.backend_app.main import app; print('OK', len(app.routes))"
python -m pytest tests/test_doctor_dashboard_endpoint.py -v
```

- [ ] **Step 5: Commit**

```bash
git add api_backend/backend_app/routes/doctor_dashboard/doctors_schema.py api_backend/backend_app/routes/doctor_dashboard/doctor_dashboard_endpoint.py tests/test_doctor_dashboard_endpoint.py
git commit -m "feat: GET /doctor-dashboard/doctors (shared doctor list for RDV + medical record assignment)"
```

---

## Task 5: Endpoints triage (claim + file d'attente + schéma création)

**Files:**
- Modify: `api_backend/backend_app/routes/medical_records/schemas.py`
- Modify: `api_backend/backend_app/routes/medical_records/medical_records_endpoint.py`
- Test: `tests/test_medical_records_triage_endpoints.py`

**Interfaces:**
- Consumes: `MedicalRecordController.claim_review`/`list_pending_review` (Task 3).
- Produces: `POST /medical_records/{id}/claim`, `GET /medical_records/pending-review` — consommés par Task 8 (frontend dashboard).

- [ ] **Step 1: Étendre `MedicalRecordCreate`**

Dans `api_backend/backend_app/routes/medical_records/schemas.py`, ajouter à `MedicalRecordCreate` (près de `uuid`) :

```python
    needs_doctor_review: Optional[bool] = False
    assigned_doctor_id: Optional[int] = None
```

- [ ] **Step 2: Ajouter un schéma de sortie pour la file d'attente**

```python
class PendingReviewRecordOut(BaseModel):
    record_id: int
    patient_id: int
    patient_name: str
    motif_code: str
    consultation_date: Optional[str] = None
    created_by_name: Optional[str] = None
    assigned_doctor_id: Optional[int] = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Ajouter les 2 routes**

Dans `api_backend/backend_app/routes/medical_records/medical_records_endpoint.py`, ajouter (import `PendingReviewRecordOut` en tête) :

```python
@router.get("/pending-review", response_model=list[PendingReviewRecordOut])
def get_pending_review(medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    records = medical_ctrl.list_pending_review()
    out = []
    for r in records:
        patient = getattr(r, "patient", None)
        patient_name = f"{getattr(patient, 'first_name', '') or ''} {getattr(patient, 'last_name', '') or ''}".strip() or "Patient" if patient else "Patient"
        out.append(PendingReviewRecordOut(
            record_id=r.record_id,
            patient_id=r.patient_id,
            patient_name=patient_name,
            motif_code=r.motif_code,
            consultation_date=r.consultation_date.isoformat() if r.consultation_date else None,
            created_by_name=r.created_by_name,
            assigned_doctor_id=r.assigned_doctor_id,
        ))
    return out


@router.post("/{record_id}/claim", response_model=MedicalRecordResponse)
def claim_record(record_id: int, medical_ctrl: MedicalRecordController = Depends(get_medical_controller)):
    try:
        record = medical_ctrl.claim_review(record_id)
        return MedicalRecordResponse.model_validate(normalize_medical_record_data(record))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        if "introuvable" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=409, detail=str(ve))
```

**Placer `GET /pending-review` AVANT toute route existante de la forme `GET /{record_id}`** (si une telle route existe dans ce fichier) — sinon FastAPI matcherait `pending-review` comme une valeur de `record_id` et casserait ce nouvel endpoint. Vérifier l'ordre des routes existantes dans le fichier avant d'insérer.

- [ ] **Step 4: Écrire les tests HTTP**

```python
# tests/test_medical_records_triage_endpoints.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, medical_records_endpoint)


def test_create_record_with_review_flag_appears_in_pending_list(db_session, api_client):
    nurse = create_test_user(db_session, "triage_hep_nurse1", "nurse", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "triage_hep_medecin1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    nurse_headers = auth_headers(client, "triage_hep_nurse1", TEST_PASSWORD)
    medecin_headers = auth_headers(client, "triage_hep_medecin1", TEST_PASSWORD)

    client.post("/medical_records/", json={
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": medecin.user_id,
    }, headers=nurse_headers)

    resp = client.get("/medical_records/pending-review", headers=medecin_headers)
    assert resp.status_code == 200
    assert any(r["patient_id"] == patient_id for r in resp.json())


def test_claim_forbidden_for_nurse(db_session, api_client):
    nurse = create_test_user(db_session, "triage_hep_nurse2", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    headers = auth_headers(client, "triage_hep_nurse2", TEST_PASSWORD)

    create_resp = client.post("/medical_records/", json={
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": None,
    }, headers=headers)
    record_id = create_resp.json()["record_id"]

    resp = client.post(f"/medical_records/{record_id}/claim", headers=headers)
    assert resp.status_code == 403


def test_claim_success_removes_from_pending_list(db_session, api_client):
    nurse = create_test_user(db_session, "triage_hep_nurse3", "nurse", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "triage_hep_medecin3", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    nurse_headers = auth_headers(client, "triage_hep_nurse3", TEST_PASSWORD)
    medecin_headers = auth_headers(client, "triage_hep_medecin3", TEST_PASSWORD)

    create_resp = client.post("/medical_records/", json={
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": None,
    }, headers=nurse_headers)
    record_id = create_resp.json()["record_id"]

    claim_resp = client.post(f"/medical_records/{record_id}/claim", headers=medecin_headers)
    assert claim_resp.status_code == 200

    pending = client.get("/medical_records/pending-review", headers=medecin_headers)
    assert record_id not in [r["record_id"] for r in pending.json()]


def test_claim_twice_returns_409(db_session, api_client):
    nurse = create_test_user(db_session, "triage_hep_nurse4", "nurse", password=TEST_PASSWORD)
    medecin_a = create_test_user(db_session, "triage_hep_medecin_a4", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "triage_hep_medecin_b4", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    nurse_headers = auth_headers(client, "triage_hep_nurse4", TEST_PASSWORD)
    headers_a = auth_headers(client, "triage_hep_medecin_a4", TEST_PASSWORD)
    headers_b = auth_headers(client, "triage_hep_medecin_b4", TEST_PASSWORD)

    create_resp = client.post("/medical_records/", json={
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": None,
    }, headers=nurse_headers)
    record_id = create_resp.json()["record_id"]

    assert client.post(f"/medical_records/{record_id}/claim", headers=headers_a).status_code == 200
    assert client.post(f"/medical_records/{record_id}/claim", headers=headers_b).status_code == 409
```

- [ ] **Step 5: Lancer les tests**

```bash
python -m pytest tests/test_medical_records_triage_endpoints.py -v
```

Attendu : 4 passed.

- [ ] **Step 6: Lancer la suite complète du backend**

```bash
python -m pytest tests/ -q
```

Attendu : mêmes échecs pré-existants déjà documentés, aucun nouveau.

- [ ] **Step 7: Commit**

```bash
git add api_backend/backend_app/routes/medical_records/schemas.py api_backend/backend_app/routes/medical_records/medical_records_endpoint.py tests/test_medical_records_triage_endpoints.py
git commit -m "feat: POST /medical_records/{id}/claim + GET /medical_records/pending-review"
```

---

## Task 6: Intégration PowerSync (schéma local + connecteur + gateway + store)

**Files:**
- Modify: `ah2-admin-web/src/powersync-client/AppSchema.js`
- Modify: `ah2-admin-web/src/powersync-client/DossierConnector.js`
- Modify: `ah2-admin-web/src/services/MedicalRecordGateway.js`
- Modify: `ah2-admin-web/src/stores/medicalRecordStore.js`

**Interfaces:**
- Produces: `needsDoctorReview`/`assignedDoctorId` traversent tout le chemin écriture (formulaire → store → PowerSync local → connecteur → gateway → backend) — consommé par Task 7 (formulaire).

**Aucun test automatisé possible** (aucun test PowerSync existe dans ce projet — infrastructure trop lourde à simuler en pytest). Vérification par relecture explicite de bout en bout + build.

- [ ] **Step 1: Lire les 4 fichiers en entier avant d'éditer**

Ce chantier touche une zone signalée comme sensible (limites PowerSync déjà documentées lors du chantier 4). Lire `AppSchema.js` (table `medical_records`, lignes ~68-94), `DossierConnector.js` (cas `medical_records:PUT`, lignes ~128-163), `MedicalRecordGateway.js::createMedicalRecord`, `medicalRecordStore.js::createMedicalRecord` (lignes ~121-147) en entier avant de modifier quoi que ce soit.

- [ ] **Step 2: Étendre le schéma local PowerSync**

Dans `AppSchema.js`, ajouter au `Table` `medical_records` (après `patient_uuid: column.text,`) :

```javascript
    needs_doctor_review: column.integer,
    assigned_doctor_id: column.integer,
```

SQLite/PowerSync n'a pas de type booléen natif — `column.integer` (0/1), même motif que les autres booléens déjà stockés ainsi ailleurs dans ce schéma (vérifier `is_lab_order` sur `prescriptions` comme référence de style si besoin).

- [ ] **Step 3: Étendre l'écriture locale**

Dans `medicalRecordStore.js::createMedicalRecord`, ajouter les 2 colonnes à l'`INSERT` :

```javascript
            await db.execute(
                `INSERT INTO medical_records (
                    id, patient_id, patient_uuid, consultation_date, motif_code, appointment_id,
                    marital_status, severity, bp, temperature, weight, height,
                    medical_history, allergies, symptoms, diagnosis, treatment, notes,
                    needs_doctor_review, assigned_doctor_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId || null, data.patientUuid || null, data.consultationDate || null, data.motifCode, data.appointmentId || null,
                    data.maritalStatus || null, data.severity || null, data.bp || null,
                    data.temperature ?? null, data.weight ?? null, data.height ?? null,
                    data.medicalHistory || null, data.allergies || null, data.symptoms || null,
                    data.diagnosis || null, data.treatment || null, data.notes || null,
                    data.needsDoctorReview ? 1 : 0, data.assignedDoctorId || null,
                ]
            );
```

- [ ] **Step 4: Étendre le connecteur de synchronisation**

Dans `DossierConnector.js`, cas `medical_records:PUT` (le seul concerné — pas `PATCH`, ces 2 champs ne sont jamais modifiés après création, décision spec), ajouter à l'appel `MedicalRecordGateway.createMedicalRecord({...})` :

```javascript
              needsDoctorReview: !!op.opData.needs_doctor_review,
              assignedDoctorId: op.opData.assigned_doctor_id || null,
```

- [ ] **Step 5: Étendre le gateway**

Dans `MedicalRecordGateway.js::createMedicalRecord`, ajouter au `payload` :

```javascript
            needs_doctor_review: !!data.needsDoctorReview,
            assigned_doctor_id: data.assignedDoctorId || null,
```

- [ ] **Step 6: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, aucune erreur.

- [ ] **Step 7: Auto-relecture explicite de bout en bout (Review Focus)**

Tracer manuellement le chemin complet pour confirmer qu'aucun maillon n'a été oublié : `MedicalRecordModal.vue` (Task 7, pas encore fait — vérifier juste que le contrat `emit('save', { needsDoctorReview, assignedDoctorId })` sera cohérent) → `medicalRecordStore.createMedicalRecord(data)` (Step 3 ci-dessus) → ligne SQLite locale avec les 2 colonnes → PowerSync détecte le changement, crée une opération `medical_records:PUT` avec `opData` contenant les 2 colonnes → `DossierConnector.js` (Step 4) lit `op.opData.needs_doctor_review`/`op.opData.assigned_doctor_id` → `MedicalRecordGateway.createMedicalRecord` (Step 5) → `POST /medical_records/` avec les 2 champs → `MedicalRecordCreate` schema (Task 5) les accepte → `MedicalRecordController.create_record()` (Task 3) les traite. Documenter cette relecture dans le rapport de tâche.

- [ ] **Step 8: Commit**

```bash
git add ah2-admin-web/src/powersync-client/AppSchema.js ah2-admin-web/src/powersync-client/DossierConnector.js ah2-admin-web/src/services/MedicalRecordGateway.js ah2-admin-web/src/stores/medicalRecordStore.js
git commit -m "feat: PowerSync local schema + sync connector carry triage fields end to end"
```

---

## Task 7: Formulaire dossier médical + notification frontend

**Files:**
- Modify: `ah2-admin-web/src/components/medical-records/MedicalRecordModal.vue`
- Modify: `ah2-admin-web/src/components/notifications/NotificationBell.vue`
- Modify: `ah2-admin-web/src/i18n.js`

**Interfaces:**
- Consumes: `GET /doctor-dashboard/doctors` (Task 4), `data.needsDoctorReview`/`data.assignedDoctorId` (Task 6).

- [ ] **Step 1: Ajouter les champs au formulaire réactif**

Dans `MedicalRecordModal.vue`, ajouter à l'objet `form` (près de `notes: ''`) :

```javascript
  needsDoctorReview: false,
  assignedDoctorId: '',
```

- [ ] **Step 2: Charger la liste des médecins**

Ajouter un état local et un chargement au montage :

```javascript
import { ref } from 'vue';
import api from '@/services/api';
// ... (garder les imports existants)

const doctors = ref([]);

onMounted(async () => {
  // ... (code onMounted existant, garder tel quel)
  try {
    const resp = await api.get('/doctor-dashboard/doctors');
    doctors.value = resp.data || [];
  } catch (e) {
    console.error('Erreur chargement liste medecins:', e);
  }
});
```

Fusionner avec le `onMounted` déjà existant (ne pas créer un second bloc `onMounted` — ajouter ce contenu à l'intérieur du bloc déjà présent, lignes ~202-235).

- [ ] **Step 3: Ajouter la section au template**

Ajouter après la section "section_notes" (avant les boutons de soumission) :

```html
        <div>
          <h4 class="text-sm font-bold text-gray-500 uppercase mb-3">{{ t('medicalRecords.modal.section_triage') }}</h4>
          <label class="inline-flex items-center cursor-pointer mb-3">
            <input type="checkbox" v-model="form.needsDoctorReview" class="sr-only peer">
            <div class="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-teal-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal-600"></div>
            <span class="ms-3 text-sm font-medium text-gray-900">{{ t('medicalRecords.modal.needs_doctor_review') }}</span>
          </label>
          <div v-if="form.needsDoctorReview">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.assign_doctor') }}</label>
            <select v-model="form.assignedDoctorId" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
              <option value="">{{ t('medicalRecords.modal.assign_doctor_pool') }}</option>
              <option v-for="d in doctors" :key="d.user_id" :value="d.user_id">{{ d.full_name }}</option>
            </select>
          </div>
        </div>
```

- [ ] **Step 4: Inclure dans le payload émis**

Dans `handleSubmit()`, ajouter à l'objet passé à `emit('save', {...})` :

```javascript
    needsDoctorReview: form.needsDoctorReview,
    assignedDoctorId: form.needsDoctorReview ? (form.assignedDoctorId || null) : null,
```

Le second champ force `null` si la case n'est pas cochée, même si `assignedDoctorId` avait été sélectionné puis la case décochée (évite d'envoyer une assignation fantôme).

- [ ] **Step 5: i18n FR**

Dans `ah2-admin-web/src/i18n.js`, bloc FR `medicalRecords.modal`, ajouter :

```javascript
        section_triage: "Transmission au médecin",
        needs_doctor_review: "À transmettre au médecin",
        assign_doctor: "Médecin",
        assign_doctor_pool: "File d'attente (tout médecin)",
```

- [ ] **Step 6: i18n EN**

Bloc EN équivalent :

```javascript
        section_triage: "Doctor referral",
        needs_doctor_review: "Refer to doctor",
        assign_doctor: "Doctor",
        assign_doctor_pool: "Shared queue (any doctor)",
```

- [ ] **Step 7: Notification frontend**

Dans `NotificationBell.vue::labelFor()`, ajouter un cas (près de `hospitalization_aggravation`) :

```javascript
  if (n.type === 'patient_pending_review') {
    return `🩺 Patient en attente — ${n.payload?.patient_name || 'patient'} (${n.payload?.created_by_name || '?'})`;
  }
```

Dans `handleClick()`, ajouter la navigation :

```javascript
  if (n.type === 'patient_pending_review' && n.payload?.patient_id) {
    router.push(`/medical/patients/${n.payload.patient_id}`);
  }
```

- [ ] **Step 8: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

- [ ] **Step 9: Commit**

```bash
git add ah2-admin-web/src/components/medical-records/MedicalRecordModal.vue ah2-admin-web/src/components/notifications/NotificationBell.vue ah2-admin-web/src/i18n.js
git commit -m "feat: doctor referral checkbox + assignment on medical record creation, notification handling"
```

---

## Task 8: Assignation RDV

**Files:**
- Modify: `controller/appointment_controller.py`
- Modify: `ah2-admin-web/src/components/appointments/AppointmentModal.vue`
- Modify: `ah2-admin-web/src/stores/appointmentStore.js`
- Modify: `ah2-admin-web/src/powersync-client/DossierConnector.js`
- Modify: `ah2-admin-web/src/services/AppointmentGateway.js`
- Test: `tests/test_appointments.py` (ou fichier équivalent déjà existant pour ce module — vérifier avant d'ajouter)

**Interfaces:**
- Consumes: `GET /doctor-dashboard/doctors` (Task 4).

Comme pour le dossier médical (Task 6), la création de RDV passe par
PowerSync (`appointmentStore.js::createAppointment`, toujours en écriture
locale, en ligne comme hors ligne — pas conditionné par le rôle
contrairement au dossier médical). **Bonne nouvelle vérifiée avant
d'écrire ce plan** : `AppSchema.js` a déjà une colonne `doctor_id` sur la
table locale `appointments` (`ah2-admin-web/src/powersync-client/AppSchema.js:15`)
— elle n'est simplement jamais écrite. Aucune migration de schéma local
nécessaire ici, contrairement à Task 6.

**Défaut réel trouvé en vérifiant `book_appointment()` avant d'écrire ce
plan** : la route `POST /appointments/` appelle
`appt_ctrl.book_appointment(payload.model_dump())` — `model_dump()` sans
`exclude_none` inclut TOUJOURS la clé `doctor_id` dans le dict, même
`None`. Or `book_appointment()` (`controller/appointment_controller.py:147-150`)
retombe sur le créateur dès que `"doctor_id" not in data OR
data.get("doctor_id") is None` — la seconde condition se déclenche donc
systématiquement pour tout appel passant par cet endpoint, y compris un
choix explicite "Non assigné" (`doctor_id: null`) depuis le nouveau
sélecteur. **Sans corriger cette condition, le sélecteur ajouté par cette
tâche n'aurait aucun effet réel pour l'option "Non assigné".**

- [ ] **Step 1: Corriger le repli automatique**

Dans `controller/appointment_controller.py::book_appointment`, remplacer :

```python
        # Ensure doctor_id
        if "doctor_id" not in data or data.get("doctor_id") is None:
            if getattr(self.user, "user_id", None) is not None:
                data["doctor_id"] = self.user.user_id
```

par :

```python
        # Ensure doctor_id - ne retombe sur le createur QUE si la cle est
        # absente du dict (vrai appelant historique, jamais le nouveau
        # formulaire web qui envoie toujours la cle, y compris a None pour
        # "Non assigne" explicite - chantier triage 2026-09-29, voir
        # commentaire de book_appointment() dans le plan de ce chantier).
        if "doctor_id" not in data:
            if getattr(self.user, "user_id", None) is not None:
                data["doctor_id"] = self.user.user_id
```

- [ ] **Step 2: Test de non-régression + du nouveau comportement**

Vérifier s'il existe déjà un fichier de test pour ce module
(`tests/test_appointments.py` ou équivalent — chercher avant d'écrire).
Ajouter :

```python
def test_book_appointment_explicit_null_doctor_stays_unassigned(db_session, api_client):
    """Le repli automatique sur le createur ne doit jamais ecraser un
    choix explicite 'Non assigne' venant du formulaire web (payload avec
    doctor_id=None, pas une cle absente)."""
    nurse = create_test_user(db_session, "triage_appt_nurse1", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = api_client(auth_endpoints, appointment_endpoints)
    headers = auth_headers(client, "triage_appt_nurse1", TEST_PASSWORD)

    resp = client.post("/appointments/", json={
        "patient_id": patient_id, "doctor_id": None,
        "appointment_date": "2026-10-15", "appointment_time": "09:00", "reason": "Test",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["doctor_id"] is None


def test_book_appointment_explicit_doctor_id_respected(db_session, api_client):
    nurse = create_test_user(db_session, "triage_appt_nurse2", "nurse", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "triage_appt_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = api_client(auth_endpoints, appointment_endpoints)
    headers = auth_headers(client, "triage_appt_nurse2", TEST_PASSWORD)

    resp = client.post("/appointments/", json={
        "patient_id": patient_id, "doctor_id": medecin.user_id,
        "appointment_date": "2026-10-15", "appointment_time": "09:30", "reason": "Test",
    }, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["doctor_id"] == medecin.user_id
```

Adapter les imports (`create_test_user`, `create_test_patient`,
`auth_headers`, `api_client`, `auth_endpoints`, `appointment_endpoints`,
`TEST_PASSWORD`) au fichier de test réellement utilisé pour ce module —
suivre son style existant plutôt que d'en réinventer un.

```bash
python -m pytest tests/test_appointments.py -v -k "doctor"
```

- [ ] **Step 3: Ajouter le sélecteur au formulaire**

Dans `AppointmentModal.vue`, ajouter un état local pour la liste des
médecins et un champ au formulaire réactif :

```javascript
const doctors = ref([]);
```

Ajouter `doctorId: ''` à l'objet `form` (près de `reason: ''`).

Charger la liste dans le `onMounted` déjà existant (ajouter à l'intérieur
du bloc actuel, ne pas créer un second `onMounted`) :

```javascript
  try {
    const resp = await api.get('/doctor-dashboard/doctors');
    doctors.value = resp.data || [];
  } catch (e) {
    console.error('Erreur chargement liste medecins:', e);
  }
```

Ajouter `import api from '@/services/api';` en tête du `<script setup>`.
En mode édition, initialiser `form.doctorId = appt.doctor_id || '';` dans
la branche `if (props.appointment) { ... }` du `onMounted`.

Ajouter au template, après le bloc "specialty" :

```html
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.doctor') }}</label>
          <select v-model="form.doctorId" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm">
            <option value="">{{ t('appointments.modal.doctor_unassigned') }}</option>
            <option v-for="d in doctors" :key="d.user_id" :value="d.user_id">{{ d.full_name }}</option>
          </select>
        </div>
```

- [ ] **Step 4: Inclure dans le payload d'émission**

Dans `handleSubmit()`, ajouter au `emit('save', {...})` :

```javascript
    doctorId: form.doctorId || null,
```

- [ ] **Step 5: i18n**

Dans `ah2-admin-web/src/i18n.js`, bloc FR `appointments.modal`, ajouter :

```javascript
        doctor: "Médecin",
        doctor_unassigned: "Non assigné",
```

Bloc EN équivalent :

```javascript
        doctor: "Doctor",
        doctor_unassigned: "Unassigned",
```

- [ ] **Step 6: Propager `doctorId` jusqu'à l'écriture locale PowerSync**

Dans `appointmentStore.js::createAppointment`, ajouter la colonne à
l'`INSERT` :

```javascript
    async function createAppointment(data) {
        const uuid = crypto.randomUUID();
        await db.execute(
            `INSERT INTO appointments (id, patient_id, doctor_id, specialty, appointment_date, appointment_time, reason, status)
             VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')`,
            [uuid, data.patientId, data.doctorId || null, data.specialty || null, data.appointmentDate, data.appointmentTime, data.reason || '']
        );
    }
```

Même chose pour `updateAppointment` (ajouter `doctor_id = ?` au `SET` et
`data.doctorId || null` aux bindings), pour rester cohérent — même si ce
chantier ne modifie pas l'UI d'édition, l'écriture locale ne doit jamais
silencieusement effacer une assignation existante sur une mise à jour.

- [ ] **Step 7: Propager jusqu'au connecteur de synchronisation**

Dans `DossierConnector.js`, cas `appointments:PUT`, ajouter à l'appel
`AppointmentGateway.createAppointment({...})` :

```javascript
              doctorId: op.opData.doctor_id || null,
```

Dans le cas `appointments:PATCH`, ajouter `doctor_id` à la requête `SELECT`
qui relit la ligne locale complète (`'SELECT server_id, patient_id, doctor_id, specialty, appointment_date, appointment_time, reason FROM appointments WHERE id = ?'`),
et `doctorId: current.doctor_id || null` à l'appel `AppointmentGateway.updateAppointment(...)` qui suit.

- [ ] **Step 8: Propager jusqu'au gateway**

Dans `AppointmentGateway.js`, ajouter `doctor_id: data.doctorId || null`
au `payload` de `createAppointment` ET de `updateAppointment`.

- [ ] **Step 9: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

- [ ] **Step 10: Auto-relecture explicite de bout en bout (Review Focus)**

Même exigence qu'en Task 6 : tracer le chemin complet
`AppointmentModal.vue` → `appointmentStore.createAppointment` → ligne
SQLite locale → `DossierConnector.js` (`appointments:PUT`) →
`AppointmentGateway.createAppointment` → `POST /appointments/` →
`AppointmentController.book_appointment()` (corrigé en Step 1 : la clé
`doctor_id` est désormais toujours respectée telle quelle dès qu'elle est
présente dans le dict — y compris `None` — le repli sur le créateur ne
s'active plus que pour un appelant qui omettrait totalement la clé, ce
que le nouveau formulaire web ne fait jamais). Documenter cette relecture
dans le rapport de tâche, en confirmant explicitement que Step 1 a bien
été appliqué avant de conclure que le chemin est correct.

- [ ] **Step 11: Commit**

```bash
git add controller/appointment_controller.py tests/test_appointments.py ah2-admin-web/src/components/appointments/AppointmentModal.vue ah2-admin-web/src/stores/appointmentStore.js ah2-admin-web/src/powersync-client/DossierConnector.js ah2-admin-web/src/services/AppointmentGateway.js ah2-admin-web/src/i18n.js
git commit -m "fix: appointment doctor_id fallback + doctor assignment selector, PowerSync end to end"
```

(Adapter le nom du fichier de test dans le `git add` s'il s'avère différent de `tests/test_appointments.py` une fois le fichier réel identifié en Step 2.)

---

## Task 9: Dashboard médecin — section "Patients en attente"

**Files:**
- Modify: `ah2-admin-web/src/stores/doctorKpiStore.js`
- Modify: `ah2-admin-web/src/views/modules/doctors/DoctorKpiView.vue`
- Modify: `ah2-admin-web/src/i18n.js`

**Interfaces:**
- Consumes: `GET /medical_records/pending-review` (Task 5), `POST /medical_records/{id}/claim` (Task 5).

- [ ] **Step 1: Ajouter au store**

Dans `doctorKpiStore.js`, ajouter un état `pendingReview` (tableau) et 2 actions :

```javascript
    const pendingReview = ref([]);

    async function fetchPendingReview() {
        try {
            const resp = await api.get('/medical_records/pending-review');
            pendingReview.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement patients en attente:', err);
        }
    }

    async function claimRecord(recordId) {
        await api.post(`/medical_records/${recordId}/claim`);
        await fetchPendingReview();
    }
```

Importer `api` depuis `@/services/api` en tête de fichier si absent. Ajouter `pendingReview, fetchPendingReview, claimRecord` au `return` du store. Appeler `fetchPendingReview()` dans `fetchKpiData()` (en parallèle du reste, ou juste après) pour que la liste se rafraîchisse avec le reste du dashboard.

- [ ] **Step 2: Ajouter la section au template**

Dans `DoctorKpiView.vue`, ajouter après la grille des 5 cartes KPI :

```html
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4">
          {{ t('doctorKpi.pending_review_title') }}
        </h2>
        <div v-if="kpiStore.pendingReview.length === 0" class="text-sm text-gray-400">
          {{ t('doctorKpi.pending_review_empty') }}
        </div>
        <div v-else class="divide-y divide-gray-100">
          <div v-for="r in kpiStore.pendingReview" :key="r.record_id" class="py-3 flex items-center justify-between">
            <div>
              <router-link :to="`/medical/patients/${r.patient_id}`" class="font-medium text-teal-700 hover:underline">
                {{ r.patient_name }}
              </router-link>
              <p class="text-xs text-gray-400">{{ r.motif_code }} — {{ t('doctorKpi.pending_review_by') }} {{ r.created_by_name || '?' }}</p>
            </div>
            <button
              @click="kpiStore.claimRecord(r.record_id)"
              class="px-3 py-1.5 text-xs font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-700 transition"
            >
              {{ t('doctorKpi.claim_button') }}
            </button>
          </div>
        </div>
      </div>
```

- [ ] **Step 3: i18n FR**

Dans le bloc FR `doctorKpi`, ajouter :

```javascript
      pending_review_title: "Patients en attente",
      pending_review_empty: "Aucun patient en attente.",
      pending_review_by: "signalé par",
      claim_button: "Prendre en charge",
```

- [ ] **Step 4: i18n EN**

```javascript
      pending_review_title: "Patients awaiting review",
      pending_review_empty: "No patient waiting.",
      pending_review_by: "flagged by",
      claim_button: "Take in charge",
```

- [ ] **Step 5: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

- [ ] **Step 6: Vérification manuelle rapide**

Lancer le serveur de dev, se connecter en `nurse`, créer un dossier médical avec "à transmettre" coché et un médecin assigné ; se connecter en ce médecin, confirmer que le dossier apparaît sous "Patients en attente", cliquer "Prendre en charge", confirmer qu'il disparaît de la liste et que la notification était bien apparue.

- [ ] **Step 7: Commit**

```bash
git add ah2-admin-web/src/stores/doctorKpiStore.js ah2-admin-web/src/views/modules/doctors/DoctorKpiView.vue ah2-admin-web/src/i18n.js
git commit -m "feat: 'Patients en attente' section on doctor dashboard (list + claim)"
```
