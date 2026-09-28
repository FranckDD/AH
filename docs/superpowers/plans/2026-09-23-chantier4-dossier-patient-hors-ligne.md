# Chantier 4, sous-projet 2 — Dossier patient hors-ligne (medecin/nurse) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre à `medecin`/`nurse` de consulter (dossier clinique, prescriptions, labo) et d'alimenter (nouvelle consultation, nouvelle prescription) le dossier patient sans connexion réseau, avec reprise automatique à la reconnexion.

**Architecture:** Réutilisation stricte du pattern déjà validé par le pilote Rendez-vous (chantier 4, sous-projet 1) : tables PowerSync locales miroir, règles de sync filtrées par rôle/domaine côté serveur, un connecteur unique gérant la file CRUD (PUT/PATCH) pour l'écriture différée.

**Tech Stack:** PowerSync (service self-hosted + SDK web `@powersync/web`), FastAPI, SQLAlchemy, PostgreSQL (procédures stockées), Vue 3 / Pinia.

**Spec:** `docs/superpowers/specs/2026-09-23-chantier4-dossier-patient-hors-ligne-design.md`

## Global Constraints

- Rôles concernés : `medecin`, `nurse` uniquement.
- Cloisonnement clinique déjà en place (chantier périmètre médical, 2026-09-22) : aucune règle de sync ajoutée par ce plan ne doit jamais inclure de colonne de `toxico_dossiers` ou `consultation_spirituelle`.
- Filtre lecture patients : `EXISTS (SELECT 1 FROM medical_records WHERE medical_records.patient_id = patients.patient_id)` — accès large à tout patient clinique, pas de filtre par praticien (politique d'accès large, chantier 6).
- Filtre lecture `lab_results` : `status = 'completed'` uniquement (même filtre que `LabController._est_medical_lecture_seule()`).
- Hors périmètre : suppression de consultation/prescription, modification de prescription existante.
- Convention PowerSync déjà établie (pilote RDV) : colonne locale `id` = `uuid::text` de la ligne Postgres pour toute table **écrite** localement ; `server_id` = clé entière Postgres, renseignée seulement une fois la ligne confirmée côté serveur.
- Toute modification de `powersync/sync-config.yaml` exige un redémarrage du service (`docker restart powersync-powersync-1`).
- **Aucun commit git** — convention constante de ce projet.
- Toute migration Alembic modifiant une procédure stockée réelle nécessite l'accord explicite de l'utilisateur avant application contre la base de développement réelle (pas seulement contre le schéma de test CI).

---

### Task 1: Support du `uuid` client sur `medical_records` (backend)

**Files:**
- Modify: `api_backend/backend_app/routes/medical_records/schemas.py`
- Modify: `repositories/medical_repo.py:113-152`
- Create: `alembic/versions/008_medrec_uuid_param.py`
- Test: `tests/test_medical_records_uuid.py`

**Interfaces:**
- Consumes: rien d'une tâche antérieure de ce plan.
- Produces: `MedicalRecordCreate.uuid: Optional[str]`, `MedicalRecordResponse.uuid: Optional[str]` — consommés par la Tâche 3 (gateway frontend) et la Tâche 6 (connecteur).

La procédure stockée `public.create_medical_record` (actuellement 20 paramètres, dernière version dans `alembic/versions/005_medrec_appointment_id.py`) n'accepte aujourd'hui aucun `uuid` — un appel via `repositories/medical_repo.py::create()` laisse toujours Postgres générer un nouveau uuid (colonne `uuid uuid DEFAULT gen_random_uuid() NOT NULL`, vérifié dans `ci/schema_only.sql:1842`), ce qui casserait la réconciliation PowerSync (le client doit retrouver EXACTEMENT le uuid qu'il a généré localement dans la ligne confirmée par le serveur).

- [ ] **Step 1: Écrire le test qui échoue (API round-trip du uuid client)**

```python
# tests/test_medical_records_uuid.py
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_create_medical_record_avec_uuid_client_le_persiste(db_session, api_client):
    """Chantier 4 sous-projet 2 : un dossier medical cree hors ligne
    (PowerSync) fournit son propre uuid - le serveur doit le persister
    tel quel, jamais en generer un nouveau, sinon la ligne locale ne
    matche jamais la ligne confirmee par le serveur."""
    medecin = create_test_user(db_session, "test_dossier_uuid_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="DossierUuid")
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_dossier_uuid_medecin", TEST_PASSWORD)

    client_uuid = "11111111-2222-3333-4444-555555555555"
    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] == client_uuid


def test_create_medical_record_sans_uuid_en_genere_un(db_session, api_client):
    """Non-regression : la creation en ligne (aucun uuid fourni par le
    client) continue de fonctionner, Postgres genere le uuid comme
    avant ce chantier."""
    medecin = create_test_user(db_session, "test_dossier_uuid_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="DossierSansUuid")
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_dossier_uuid_medecin2", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] is not None
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `python -m pytest tests/test_medical_records_uuid.py -v`
Expected: FAIL — `MedicalRecordCreate` n'a pas de champ `uuid` (422 ou `KeyError` sur `resp.json()["uuid"]`, `MedicalRecordResponse` n'a pas ce champ).

- [ ] **Step 3: Ajouter `uuid` aux schémas**

Dans `api_backend/backend_app/routes/medical_records/schemas.py`, ajouter l'import `field_validator` s'il n'est pas déjà importé (vérifier l'en-tête du fichier avant d'ajouter un import en double), puis :

```python
class MedicalRecordBase(BaseModel):
    patient_id: int
    marital_status: Optional[str] = Field(None, max_length=50)
    bp: Optional[str] = Field(None, max_length=20)
    temperature: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    severity: Optional[str] = None
    notes: Optional[str] = None
    motif_code: str = Field(..., min_length=1, max_length=50)
    appointment_id: Optional[int] = None

    model_config = {"from_attributes": True}


class MedicalRecordCreate(MedicalRecordBase):
    consultation_date: Optional[datetime] = None  # server_default possible
    uuid: Optional[str] = Field(None, description="UUID client (creation hors ligne PowerSync) - si absent, Postgres en genere un")
```

Puis, dans `MedicalRecordResponse` (même fichier), ajouter le champ et son validateur — même motif que `AppointmentResponse` (`api_backend/backend_app/routes/appointment/appointment_schemas.py:56-63`, la colonne Postgres est un `UUID(as_uuid=True)`, l'ORM renvoie un objet `uuid.UUID`, Pydantic v2 ne le coerce plus automatiquement en `str`) :

```python
class MedicalRecordResponse(MedicalRecordBase):
    record_id: int
    consultation_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    last_updated_by: Optional[int] = None
    last_updated_by_name: Optional[str] = None
    patient: Optional[dict] = None
    uuid: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("uuid", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        return str(v) if v is not None else v
```

- [ ] **Step 4: Écrire la migration Alembic étendant la procédure stockée**

```python
# alembic/versions/008_medrec_uuid_param.py
"""add p_uuid param to create_medical_record (chantier 4 sous-projet 2)

Revision ID: 008_medrec_uuid_param
Revises: 007_drop_medrec_19param
Create Date: 2026-09-23 00:00:00.000000

Le dossier patient hors-ligne (PowerSync) doit pouvoir creer une
consultation medicale avec un uuid genere cote client, pour que la ligne
locale (creee hors connexion) matche exactement la ligne confirmee par
le serveur une fois synchronisee - meme motif que appointments.uuid
(migration 004_appointments_uuid_unique). Nouveau parametre p_uuid en
dernier avec DEFAULT NULL (meme convention que p_appointment_id,
migration 005) : tout appelant existant qui ne le fournit pas continue
de fonctionner a l'identique. COALESCE(p_uuid, gen_random_uuid())
preserve le comportement actuel (uuid genere par Postgres) quand le
parametre est absent - la colonne a deja un DEFAULT gen_random_uuid()
mais un INSERT qui nomme explicitement la colonne avec une valeur NULL
ignore ce defaut, d'ou le COALESCE explicite.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_medrec_uuid_param'
down_revision: Union[str, Sequence[str], None] = '007_drop_medrec_19param'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE OR REPLACE PROCEDURE public.create_medical_record(
            IN p_patient_id integer,
            IN p_consultation_date timestamp without time zone,
            IN p_marital_status character varying,
            IN p_bp character varying,
            IN p_temperature numeric,
            IN p_weight numeric,
            IN p_height numeric,
            IN p_medical_history text,
            IN p_allergies text,
            IN p_symptoms text,
            IN p_diagnosis text,
            IN p_treatment text,
            IN p_severity character varying,
            IN p_notes text,
            IN p_motif_code character varying,
            IN p_created_by integer DEFAULT NULL::integer,
            IN p_created_by_name character varying DEFAULT NULL::character varying,
            IN p_last_updated_by integer DEFAULT NULL::integer,
            IN p_last_updated_by_name character varying DEFAULT NULL::character varying,
            IN p_appointment_id integer DEFAULT NULL::integer,
            IN p_uuid uuid DEFAULT NULL::uuid
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name, appointment_id, uuid
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name, p_appointment_id,
                COALESCE(p_uuid, gen_random_uuid())
            );
        END;
        $$;
    """)


def downgrade() -> None:
    """Restaure la procedure a 20 parametres (sans p_uuid) - la colonne
    uuid garde son DEFAULT gen_random_uuid(), aucune perte de donnees
    autre que la possibilite de fournir un uuid client explicite."""
    op.execute("""
        DROP PROCEDURE IF EXISTS public.create_medical_record(
            integer, timestamp without time zone, character varying,
            character varying, numeric, numeric, numeric, text, text, text,
            text, text, character varying, text, character varying,
            integer, character varying, integer, character varying,
            integer, uuid
        );
    """)
    op.execute("""
        CREATE OR REPLACE PROCEDURE public.create_medical_record(
            IN p_patient_id integer,
            IN p_consultation_date timestamp without time zone,
            IN p_marital_status character varying,
            IN p_bp character varying,
            IN p_temperature numeric,
            IN p_weight numeric,
            IN p_height numeric,
            IN p_medical_history text,
            IN p_allergies text,
            IN p_symptoms text,
            IN p_diagnosis text,
            IN p_treatment text,
            IN p_severity character varying,
            IN p_notes text,
            IN p_motif_code character varying,
            IN p_created_by integer DEFAULT NULL::integer,
            IN p_created_by_name character varying DEFAULT NULL::character varying,
            IN p_last_updated_by integer DEFAULT NULL::integer,
            IN p_last_updated_by_name character varying DEFAULT NULL::character varying,
            IN p_appointment_id integer DEFAULT NULL::integer
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name, appointment_id
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name, p_appointment_id
            );
        END;
        $$;
    """)
```

**Application réelle de cette migration contre la base de développement réelle (pas seulement `ci/schema_only.sql`) nécessite l'accord explicite de l'utilisateur, comme pour la migration 003 (registre E) — demander avant `alembic upgrade head` contre la base réelle.** Régénérer `ci/schema_only.sql` après application (même procédure que les migrations précédentes de ce projet).

- [ ] **Step 5: Passer `uuid` à la procédure stockée depuis le repository**

Dans `repositories/medical_repo.py`, méthode `create()` (lignes 113-152) :

```python
    def create(self, data: dict):
        # 1. On s'assure que les données de l'utilisateur sont présentes, sinon NULL
        data.setdefault('created_by', None)
        data.setdefault('created_by_name', None)
        data.setdefault('last_updated_by', None)
        data.setdefault('last_updated_by_name', None)
        data.setdefault('appointment_id', None)
        data.setdefault('uuid', None)

        # 2. Mise à jour de la chaîne SQL pour inclure les 5 derniers paramètres
        sql = text("""
            CALL public.create_medical_record(
                :patient_id,
                LOCALTIMESTAMP,
                :marital_status,
                :bp,
                :temperature,
                :weight,
                :height,
                :medical_history,
                :allergies,
                :symptoms,
                :diagnosis,
                :treatment,
                :severity,
                :notes,
                :motif_code,
                :created_by,
                :created_by_name,
                :last_updated_by,
                :last_updated_by_name,
                :appointment_id,
                :uuid
            )
        """)
```

Le reste de la méthode (`try/except`, `session.execute(sql, data)`, `session.commit()`) reste inchangé — `data['uuid']` est déjà une chaîne (venant de `MedicalRecordCreate.uuid: Optional[str]`), psycopg2 la convertit automatiquement pour un paramètre typé `uuid` côté Postgres, aucune conversion Python nécessaire ici (contrairement à `appointment_repo.py`, qui assigne via l'ORM sur une colonne `UUID(as_uuid=True)` — ce repository-ci utilise un `CALL` SQL brut, pas l'ORM).

- [ ] **Step 6: Lancer le test pour vérifier qu'il passe**

Run: `python -m pytest tests/test_medical_records_uuid.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Non-régression**

Run: `python -m pytest tests/test_medical_records_appointment_link.py tests/test_medical_record_mapping.py -v`
Expected: PASS, aucune régression (ces tests créent des dossiers sans `uuid`, doivent continuer à fonctionner à l'identique).

---

### Task 2: Support du `uuid` client sur `prescriptions` (backend)

**Files:**
- Modify: `api_backend/backend_app/routes/prescription/prescriptions_schemas.py`
- Modify: `repositories/prescription_repo.py:150-171`
- Test: `tests/test_prescriptions_uuid.py`

**Interfaces:**
- Consumes: rien d'une tâche antérieure de ce plan.
- Produces: `PrescriptionCreate.uuid: Optional[str]`, `PrescriptionResponse.uuid: Optional[str]` — consommés par la Tâche 3 et la Tâche 6.

Contrairement aux dossiers médicaux, `repositories/prescription_repo.py::create()` insère directement via l'ORM (`Prescription(**data)`, pas de procédure stockée) — pas de migration nécessaire ici, seulement une conversion `str` → `uuid.UUID` avant l'insertion (la colonne `prescriptions.uuid` est `UUID(as_uuid=True)`, même motif que `appointment_repo.py`).

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_prescriptions_uuid.py
from datetime import date

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.prescription import prescriptions_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_create_prescription_avec_uuid_client_le_persiste(db_session, api_client):
    """Chantier 4 sous-projet 2 : une prescription creee hors ligne
    (PowerSync) fournit son propre uuid - le serveur doit le persister
    tel quel, jamais en generer un nouveau."""
    medecin = create_test_user(db_session, "test_presc_uuid_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="PrescUuid")
    db_session.flush()

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_uuid_medecin", TEST_PASSWORD)

    client_uuid = "66666666-7777-8888-9999-000000000000"
    resp = client.post("/prescriptions/", json={
        "patient_id": patient_id,
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": str(date.today()),
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] == client_uuid


def test_create_prescription_sans_uuid_en_genere_un(db_session, api_client):
    """Non-regression : la creation en ligne continue de fonctionner,
    Postgres genere le uuid comme avant ce chantier."""
    medecin = create_test_user(db_session, "test_presc_uuid_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="PrescSansUuid")
    db_session.flush()

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_uuid_medecin2", TEST_PASSWORD)

    resp = client.post("/prescriptions/", json={
        "patient_id": patient_id,
        "medication": "Amoxicilline",
        "dosage": "1g",
        "frequency": "2x/jour",
        "duration": "7 jours",
        "start_date": str(date.today()),
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] is not None
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `python -m pytest tests/test_prescriptions_uuid.py -v`
Expected: FAIL — `PrescriptionCreate`/`PrescriptionResponse` n'ont pas de champ `uuid`.

- [ ] **Step 3: Ajouter `uuid` aux schémas**

Dans `api_backend/backend_app/routes/prescription/prescriptions_schemas.py`, vérifier d'abord si `field_validator` est déjà importé (probable, `PrescriptionResponse` a déjà un `model_validator`) avant d'ajouter l'import. Dans `PrescriptionBase` :

```python
class PrescriptionBase(BaseModel):
    patient_id: int = Field(..., description="Identifiant du patient")
    medical_record_id: Optional[int] = None
    medication: Optional[str] = Field(None, min_length=1)
    dosage: Optional[str] = Field(None, min_length=1)
    frequency: Optional[str] = Field(None, min_length=1)
    duration: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    is_lab_order: bool = Field(False, description="Vrai si c'est une demande d'examen")
    lab_exams_list: Optional[List[str]] = Field(None, description="Liste des noms d'examens")
    uuid: Optional[str] = Field(None, description="UUID client (creation hors ligne PowerSync) - si absent, Postgres en genere un")

    model_config = {"from_attributes": True}
```

Puis dans `PrescriptionResponse` :

```python
class PrescriptionResponse(PrescriptionBase):
    prescription_id: int
    prescribed_by: Optional[int] = None
    prescribed_by_name: Optional[str] = None
    patient: Optional[dict] = None
    lab_exams: Optional[str] = None

    @field_validator("uuid", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        return str(v) if v is not None else v

    @model_validator(mode="before")
    @classmethod
    def format_output(cls, data: Any) -> Any:
        ...  # code existant inchangé, ne pas le retirer
```

(Le `@model_validator(mode="before") format_output` existant reste tel quel — seul le nouveau `@field_validator("uuid", ...)` est ajouté, avant ou après lui, peu importe l'ordre entre les deux décorateurs sur des champs différents.)

- [ ] **Step 4: Convertir le `uuid` string en `uuid.UUID` avant insertion**

Dans `repositories/prescription_repo.py`, méthode `create()` (lignes 150-171), ajouter la conversion juste avant `Prescription(**data)` :

```python
    def create(self, data: dict) -> Prescription:
        """
        Crée une prescription via l'ORM directement.
        Plus besoin de procédure stockée.
        """
        try:
            # Le modele attend un uuid.UUID (colonne UUID(as_uuid=True)),
            # pas une chaine brute - meme motif que appointment_repo.py.
            # Si absent/None, le defaut Postgres (gen_random_uuid()) s'applique.
            if data.get('uuid') is not None and not isinstance(data['uuid'], uuid.UUID):
                data['uuid'] = uuid.UUID(str(data['uuid']))

            # On crée l'objet directement avec le dictionnaire
            # SQLAlchemy va mapper les clés du dict aux colonnes du modèle
            new_prescription = Prescription(**data)
```

Vérifier en tête de `repositories/prescription_repo.py` si `import uuid` est déjà présent (probable, le modèle `models/prescription.py` l'utilise mais c'est un fichier différent) — l'ajouter s'il manque, ne pas dupliquer s'il est déjà là.

- [ ] **Step 5: Lancer le test pour vérifier qu'il passe**

Run: `python -m pytest tests/test_prescriptions_uuid.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Non-régression**

Run: `python -m pytest tests/test_prescriptions.py tests/test_prescription_repo.py -v`
Expected: PASS, aucune régression (hors les échecs déjà pré-existants et documentés dans `docs/superpowers/SUIVI-AVANCEMENT.md`, sans rapport avec ce changement).

---

### Task 3: Frontend — gateways REST envoient le `uuid` client

**Files:**
- Modify: `ah2-admin-web/src/services/MedicalRecordGateway.js`
- Modify: `ah2-admin-web/src/services/PrescriptionGateway.js`

**Interfaces:**
- Consumes: endpoints `POST /medical_records/` et `POST /prescriptions/` acceptant désormais `uuid` (Tâches 1 et 2).
- Produces: `MedicalRecordGateway.createMedicalRecord(data)` et `PrescriptionGateway.createPrescription(data)` acceptent un champ `data.uuid` — consommé par la Tâche 6 (`DossierConnector.js`).

- [ ] **Step 1: Ajouter `uuid` au payload de `createMedicalRecord`**

Dans `ah2-admin-web/src/services/MedicalRecordGateway.js`, méthode `createMedicalRecord` :

```javascript
    async createMedicalRecord(data) {
        const payload = {
            patient_id: data.patientId,
            consultation_date: data.consultationDate,
            motif_code: data.motifCode,
            appointment_id: data.appointmentId || null,
            marital_status: data.maritalStatus || null,
            severity: data.severity || null,
            bp: data.bp || null,
            temperature: data.temperature,
            weight: data.weight,
            height: data.height,
            medical_history: data.medicalHistory || null,
            allergies: data.allergies || null,
            symptoms: data.symptoms || null,
            diagnosis: data.diagnosis || null,
            treatment: data.treatment || null,
            notes: data.notes || null,
            uuid: data.uuid || null,
        };
        return api.post('/medical_records/', payload);
    },
```

- [ ] **Step 2: Ajouter `uuid` au payload de `createPrescription`**

Dans `ah2-admin-web/src/services/PrescriptionGateway.js`, méthode `createPrescription` :

```javascript
    async createPrescription(data) {
        const payload = {
            patient_id: data.patientId,
            medical_record_id: data.medicalRecordId || null,
            is_lab_order: data.isLabOrder,
            medication: data.medication || null,
            dosage: data.dosage || null,
            frequency: data.frequency || null,
            duration: data.duration || null,
            start_date: data.startDate,
            end_date: data.endDate || null,
            notes: data.notes || null,
            lab_exams_list: data.labExamsList || [],
            uuid: data.uuid || null,
        };
        return api.post('/prescriptions/', payload);
    },
```

- [ ] **Step 3: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi, aucune erreur.

---

### Task 4: Règles de sync PowerSync — dossier clinique

**Files:**
- Modify: `powersync/sync-config.yaml`

**Interfaces:**
- Consumes: colonnes réelles de `patients`, `medical_records`, `prescriptions`, `lab_results` (vérifiées ci-dessous).
- Produces: streams `clinical_patients`, `clinical_medical_records`, `clinical_prescriptions`, `clinical_lab_results` — consommés par la Tâche 6 (`client.js`).

- [ ] **Step 1: Ajouter les 4 nouveaux streams**

Ajouter à la fin de `powersync/sync-config.yaml` (après `doctors_lookup`) :

```yaml
  clinical_patients:
    auto_subscribe: false
    queries:
      # Filtre par DOMAINE (patient ayant au moins un dossier medical),
      # pas par praticien proprietaire - politique d'acces large aux
      # soignants deja en place cote REST (chantier 6). Colonnes
      # is_toxicology/is_spiritual incluses (ce sont de simples booleens
      # d'existence, deja affiches medecin/nurse cote dossier consolide -
      # chantier perimetre medical, "flags") - jamais les tables
      # toxico_dossiers/consultation_spirituelle elles-memes.
      - SELECT uuid::text AS id, patient_id AS server_id, code_patient,
          first_name, last_name, birth_date::text AS birth_date, gender,
          contact_phone, is_clinical, is_toxicology, is_spiritual
        FROM patients
        WHERE is_deleted = false
          AND EXISTS (SELECT 1 FROM medical_records WHERE medical_records.patient_id = patients.patient_id)

  clinical_medical_records:
    auto_subscribe: false
    queries:
      - SELECT medical_records.uuid::text AS id, medical_records.record_id AS server_id,
          medical_records.patient_id, medical_records.consultation_date::text AS consultation_date,
          medical_records.marital_status, medical_records.bp, medical_records.temperature,
          medical_records.weight, medical_records.height, medical_records.medical_history,
          medical_records.allergies, medical_records.symptoms, medical_records.diagnosis,
          medical_records.treatment, medical_records.severity, medical_records.notes,
          medical_records.motif_code, medical_records.appointment_id,
          medical_records.created_by, medical_records.created_by_name
        FROM medical_records
        JOIN patients ON patients.patient_id = medical_records.patient_id
        WHERE patients.is_deleted = false

  clinical_prescriptions:
    auto_subscribe: false
    queries:
      - SELECT prescriptions.uuid::text AS id, prescriptions.prescription_id AS server_id,
          prescriptions.patient_id, prescriptions.medical_record_id, prescriptions.medication,
          prescriptions.dosage, prescriptions.frequency, prescriptions.duration,
          prescriptions.start_date::text AS start_date, prescriptions.end_date::text AS end_date,
          prescriptions.notes, prescriptions.status, prescriptions.prescribed_by,
          prescriptions.prescribed_by_name, prescriptions.is_lab_order
        FROM prescriptions
        JOIN patients ON patients.patient_id = prescriptions.patient_id
        WHERE patients.is_deleted = false

  clinical_lab_results:
    auto_subscribe: false
    queries:
      # Lecture seule (pas de PUT/PATCH cote client sur cette table) -
      # meme filtre status='completed' que LabController._est_medical_lecture_seule()
      # cote REST. Pas de colonne uuid propre sur lab_results (seul
      # batch_id existe, pas destine a cet usage) - result_id::text
      # suffit comme id local, meme motif que patients_lookup deja en
      # place (cle entiere, pas de uuid, car table jamais ecrite hors ligne).
      - SELECT result_id::text AS id, result_id AS server_id, patient_id,
          test_type, test_date::text AS test_date, status, note, examen_id,
          code_lab_patient, prescribed_by_name
        FROM lab_results
        JOIN patients ON patients.patient_id = lab_results.patient_id
        WHERE patients.is_deleted = false AND lab_results.status = 'completed'
```

- [ ] **Step 2: Redémarrer le service PowerSync**

Run: `docker restart powersync-powersync-1`
Expected: le conteneur redémarre sans erreur (vérifier `docker logs powersync-powersync-1 --tail 50` pour confirmer l'absence d'erreur de parsing YAML/SQL).

---

### Task 5: Tables locales PowerSync — dossier clinique

**Files:**
- Modify: `ah2-admin-web/src/powersync-client/AppSchema.js`

**Interfaces:**
- Consumes: colonnes exposées par les streams de la Tâche 4.
- Produces: tables locales `patients`, `medical_records`, `prescriptions`, `lab_results` — consommées par la Tâche 6.

- [ ] **Step 1: Étendre `AppSchema.js`**

```javascript
import { column, Schema, Table } from '@powersync/web';

// La cle primaire "id" de chaque table est implicite (texte, geree par
// PowerSync) et DOIT contenir la valeur de la colonne "uuid" Postgres,
// jamais l'entier "id" de Postgres - voir sync-config.yaml (deja en place)
// qui fait deja cet aliasing cote serveur (SELECT uuid::text AS id, ...).
// "server_id" ci-dessous est l'entier Postgres, disponible seulement une
// fois la ligne confirmee par le serveur (null pour une creation encore
// hors ligne, jamais uploadee).

const appointments = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    doctor_id: column.integer,
    specialty: column.text,
    appointment_date: column.text,
    appointment_time: column.text,
    reason: column.text,
    status: column.text,
    created_at: column.text,
    updated_at: column.text,
  },
  { indexes: { by_doctor: ['doctor_id'], by_date: ['appointment_date'] } }
);

const patients_lookup = new Table({
  patient_id: column.integer,
  code_patient: column.text,
  first_name: column.text,
  last_name: column.text,
  contact_phone: column.text,
});

const doctors_lookup = new Table({
  user_id: column.integer,
  username: column.text,
  full_name: column.text,
});

// Table de lecture complete du dossier patient (medecin/nurse) - distincte
// de patients_lookup (utilisee par le pilote RDV, colonnes minimales pour
// n'afficher qu'un nom sur un RDV). is_toxicology/is_spiritual sont de
// simples booleens d'existence (deja affiches cote dossier consolide,
// chantier perimetre medical "flags") - jamais les donnees toxico/
// spirituelles elles-memes, qui ne transitent par aucun stream de ce plan.
const patients = new Table({
  server_id: column.integer,
  code_patient: column.text,
  first_name: column.text,
  last_name: column.text,
  birth_date: column.text,
  gender: column.text,
  contact_phone: column.text,
  is_clinical: column.integer,
  is_toxicology: column.integer,
  is_spiritual: column.integer,
});

const medical_records = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    consultation_date: column.text,
    marital_status: column.text,
    bp: column.text,
    temperature: column.real,
    weight: column.real,
    height: column.real,
    medical_history: column.text,
    allergies: column.text,
    symptoms: column.text,
    diagnosis: column.text,
    treatment: column.text,
    severity: column.text,
    notes: column.text,
    motif_code: column.text,
    appointment_id: column.integer,
    created_by: column.integer,
    created_by_name: column.text,
  },
  { indexes: { by_patient: ['patient_id'] } }
);

const prescriptions = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    medical_record_id: column.integer,
    medication: column.text,
    dosage: column.text,
    frequency: column.text,
    duration: column.text,
    start_date: column.text,
    end_date: column.text,
    notes: column.text,
    status: column.text,
    prescribed_by: column.integer,
    prescribed_by_name: column.text,
    is_lab_order: column.integer,
  },
  { indexes: { by_patient: ['patient_id'], by_medical_record: ['medical_record_id'] } }
);

// Lecture seule - jamais d'ecriture locale sur cette table (pas de PUT/
// PATCH pour lab_results dans DossierConnector.js).
const lab_results = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    test_type: column.text,
    test_date: column.text,
    status: column.text,
    note: column.text,
    examen_id: column.integer,
    code_lab_patient: column.text,
    prescribed_by_name: column.text,
  },
  { indexes: { by_patient: ['patient_id'] } }
);

export const AppSchema = new Schema({
  appointments,
  patients_lookup,
  doctors_lookup,
  patients,
  medical_records,
  prescriptions,
  lab_results,
});
```

- [ ] **Step 2: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 6: Connecteur unique et souscription par rôle

**Files:**
- Create: `ah2-admin-web/src/powersync-client/DossierConnector.js`
- Modify: `ah2-admin-web/src/powersync-client/client.js`
- Delete: `ah2-admin-web/src/powersync-client/AppointmentConnector.js` (renommé en `DossierConnector.js`, contenu étendu)

**Interfaces:**
- Consumes: `AppSchema.js` (Tâche 5), streams PowerSync (Tâche 4), `MedicalRecordGateway.createMedicalRecord` / `PrescriptionGateway.createPrescription` (Tâche 3), `AppointmentGateway` (déjà existant, inchangé).
- Produces: `DossierConnector` — classe unique gérant RDV + consultations + prescriptions, utilisée par `client.js`.

- [ ] **Step 1: Créer `DossierConnector.js` (renommage + extension de `AppointmentConnector.js`)**

```javascript
// ah2-admin-web/src/powersync-client/DossierConnector.js
import { UpdateType } from '@powersync/web';
import { useAuthStore } from '@/stores/auth';
import { AppointmentGateway } from '@/services/AppointmentGateway';
import { MedicalRecordGateway } from '@/services/MedicalRecordGateway';
import { PrescriptionGateway } from '@/services/PrescriptionGateway';
import { API_URL } from '@/services/api';

// URL du service PowerSync self-hoste (voir powersync/.env, PS_PORT) -
// distincte de l'API FastAPI (API_URL). A definir dans .env.local du
// frontend si elle differe de la valeur par defaut locale.
const POWERSYNC_URL = import.meta.env.VITE_POWERSYNC_URL || 'http://localhost:18080';

// Codes d'erreur qu'il ne faut JAMAIS re-essayer indefiniment - abandonner
// l'operation et la retirer de la file plutot que de bloquer toute la
// synchronisation dessus.
function isFatalUploadError(error) {
  const status = error?.response?.status;
  return status === 400 || status === 404 || status === 409 || status === 422;
}

export class DossierConnector {
  async fetchCredentials() {
    const authStore = useAuthStore();
    if (!authStore.token) {
      throw new Error('Aucun token d\'authentification disponible pour PowerSync.');
    }
    return {
      endpoint: POWERSYNC_URL,
      token: authStore.token,
    };
  }

  async uploadData(database) {
    const transaction = await database.getNextCrudTransaction();
    if (!transaction) {
      return;
    }

    let lastOp = null;
    try {
      for (const op of transaction.crud) {
        lastOp = op;

        switch (`${op.table}:${op.op}`) {
          case 'appointments:PUT': {
            await AppointmentGateway.createAppointment({
              patientId: op.opData.patient_id,
              specialty: op.opData.specialty,
              appointmentDate: op.opData.appointment_date,
              appointmentTime: op.opData.appointment_time,
              reason: op.opData.reason,
              uuid: op.id,
            });
            break;
          }
          case 'appointments:PATCH': {
            // Modification RDV : necessite server_id, pas le uuid local.
            // Relit la ligne locale COMPLETE (pas op.opData, qui peut
            // n'avoir que les colonnes modifiees) - meme motif que le
            // pilote : PowerSync a deja applique l'ecriture locale avant
            // de mettre l'operation en file.
            const current = await database.getOptional(
              'SELECT server_id, patient_id, specialty, appointment_date, appointment_time, reason FROM appointments WHERE id = ?',
              [op.id]
            );
            if (!current?.server_id) {
              console.warn(`RDV ${op.id} : modification hors ligne d'une creation pas encore confirmee, ignoree pour cet upload (sera reprise via le prochain PUT).`);
              break;
            }
            await AppointmentGateway.updateAppointment(current.server_id, {
              patientId: current.patient_id,
              specialty: current.specialty,
              appointmentDate: current.appointment_date,
              appointmentTime: current.appointment_time,
              reason: current.reason,
            });
            break;
          }
          case 'medical_records:PUT': {
            await MedicalRecordGateway.createMedicalRecord({
              patientId: op.opData.patient_id,
              consultationDate: op.opData.consultation_date,
              motifCode: op.opData.motif_code,
              appointmentId: op.opData.appointment_id,
              maritalStatus: op.opData.marital_status,
              severity: op.opData.severity,
              bp: op.opData.bp,
              temperature: op.opData.temperature,
              weight: op.opData.weight,
              height: op.opData.height,
              medicalHistory: op.opData.medical_history,
              allergies: op.opData.allergies,
              symptoms: op.opData.symptoms,
              diagnosis: op.opData.diagnosis,
              treatment: op.opData.treatment,
              notes: op.opData.notes,
              uuid: op.id,
            });
            break;
          }
          case 'medical_records:PATCH': {
            // Modification d'une consultation existante - EN PERIMETRE
            // (contrairement aux prescriptions/RDV, la spec inclut
            // explicitement "creer/modifier une consultation medicale").
            // Meme motif que appointments:PATCH : necessite server_id,
            // relit la ligne locale COMPLETE (pas op.opData) pour ne pas
            // ecraser un champ non modifie localement avec null.
            const currentRecord = await database.getOptional(
              `SELECT server_id, patient_id, consultation_date, motif_code, marital_status,
                      severity, bp, temperature, weight, height, medical_history, allergies,
                      symptoms, diagnosis, treatment, notes
               FROM medical_records WHERE id = ?`,
              [op.id]
            );
            if (!currentRecord?.server_id) {
              console.warn(`Consultation ${op.id} : modification hors ligne d'une creation pas encore confirmee, ignoree pour cet upload (sera reprise via le prochain PUT).`);
              break;
            }
            await MedicalRecordGateway.updateMedicalRecord(currentRecord.server_id, {
              patientId: currentRecord.patient_id,
              consultationDate: currentRecord.consultation_date,
              motifCode: currentRecord.motif_code,
              maritalStatus: currentRecord.marital_status,
              severity: currentRecord.severity,
              bp: currentRecord.bp,
              temperature: currentRecord.temperature,
              weight: currentRecord.weight,
              height: currentRecord.height,
              medicalHistory: currentRecord.medical_history,
              allergies: currentRecord.allergies,
              symptoms: currentRecord.symptoms,
              diagnosis: currentRecord.diagnosis,
              treatment: currentRecord.treatment,
              notes: currentRecord.notes,
            });
            break;
          }
          case 'prescriptions:PUT': {
            // Si la prescription est liee a une consultation creee dans
            // le meme geste hors ligne, sa ligne locale medical_records
            // doit deja avoir un server_id - PowerSync traite les
            // operations de la transaction CRUD dans leur ordre de
            // creation locale, donc la consultation est deja passee par
            // le case 'medical_records:PUT' ci-dessus AVANT que cette
            // prescription ne soit traitee, SAUF si son server_id n'a pas
            // encore ete confirme par le serveur (upload precedent
            // encore en vol / echoue). Dans ce cas, abandonner cette
            // prescription pour CET upload - elle sera reprise
            // automatiquement au prochain cycle, une fois le server_id
            // de sa consultation disponible.
            let medicalRecordServerId = null;
            if (op.opData.medical_record_id) {
              const linkedRecord = await database.getOptional(
                'SELECT server_id FROM medical_records WHERE id = ?',
                [op.opData.medical_record_id]
              );
              if (!linkedRecord?.server_id) {
                console.warn(`Prescription ${op.id} : liee a une consultation ${op.opData.medical_record_id} pas encore confirmee, ignoree pour cet upload (sera reprise via le prochain PUT).`);
                break;
              }
              medicalRecordServerId = linkedRecord.server_id;
            }
            await PrescriptionGateway.createPrescription({
              patientId: op.opData.patient_id,
              medicalRecordId: medicalRecordServerId,
              isLabOrder: !!op.opData.is_lab_order,
              medication: op.opData.medication,
              dosage: op.opData.dosage,
              frequency: op.opData.frequency,
              duration: op.opData.duration,
              startDate: op.opData.start_date,
              endDate: op.opData.end_date,
              notes: op.opData.notes,
              uuid: op.id,
            });
            break;
          }
          default: {
            // DELETE (toutes tables) et PATCH sur prescriptions : hors
            // perimetre de ce sous-projet (aucun ecran ne les declenche
            // actuellement - la modification de prescription n'est pas
            // possible non plus en ligne) - log defensif.
            console.warn(`Operation ${op.op} sur ${op.table}/${op.id} recue par le connecteur mais hors perimetre - ignoree.`);
          }
        }
      }

      await transaction.complete();
    } catch (error) {
      console.error('Erreur upload PowerSync:', lastOp, error);
      if (isFatalUploadError(error)) {
        console.error(`Operation ${lastOp?.op} sur ${lastOp?.table}/${lastOp?.id} abandonnee (erreur non recuperable) - retiree de la file.`);
        await transaction.complete();
      } else {
        // Erreur reseau/serveur transitoire - ne pas completer la
        // transaction, PowerSync retentera plus tard.
        throw error;
      }
    }
  }
}
```

Supprimer `ah2-admin-web/src/powersync-client/AppointmentConnector.js` (entièrement remplacé par `DossierConnector.js` ci-dessus — vérifier au préalable, par une recherche exhaustive dans `ah2-admin-web/src/`, qu'aucun autre fichier n'importe encore `AppointmentConnector` avant de le supprimer).

- [ ] **Step 2: Étendre `client.js` — souscription aux nouveaux streams et nouveau connecteur**

Dans `ah2-admin-web/src/powersync-client/client.js`, remplacer l'import :

```javascript
import { DossierConnector } from './DossierConnector';
```

Dans `openConnection(role)`, étendre le bloc de construction de `streamHandles` :

```javascript
    const streamHandles = [];
    if (role === 'medecin') {
      streamHandles.push(db.syncStream('my_appointments'));
    } else if (role === 'nurse') {
      streamHandles.push(db.syncStream('all_appointments'));
    }
    streamHandles.push(db.syncStream('patients_lookup'));
    streamHandles.push(db.syncStream('doctors_lookup'));
    if (role === 'medecin' || role === 'nurse') {
      streamHandles.push(db.syncStream('clinical_patients'));
      streamHandles.push(db.syncStream('clinical_medical_records'));
      streamHandles.push(db.syncStream('clinical_prescriptions'));
      streamHandles.push(db.syncStream('clinical_lab_results'));
    }
```

Puis, plus bas dans la même fonction, remplacer `new AppointmentConnector()` par `new DossierConnector()` :

```javascript
  const connector = new DossierConnector();
  await db.connect(connector);
```

- [ ] **Step 3: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi, aucune référence résiduelle à `AppointmentConnector`.

---

### Task 7: Vérification finale (hors tâches, à la charge du contrôleur)

Aucun outil de navigateur disponible dans cet environnement agentique — même protocole que le pilote RDV (2026-09-15), diagnostics et validation via code/logs/DB réels à partir de captures fournies par l'utilisateur.

- [ ] Relancer la suite complète (`python -m pytest tests/ -q`) et confirmer qu'aucun nouvel échec n'apparaît en dehors des 9 échecs pré-existants documentés dans `docs/superpowers/SUIVI-AVANCEMENT.md`.
- [ ] Build frontend complet (`cd ah2-admin-web && npx vite build --mode production`).
- [ ] Demander à l'utilisateur de rejouer le protocole de test du pilote RDV, étendu au dossier patient : coupure réseau → ouverture d'un dossier patient déjà synchronisé (lecture) → création d'une consultation + prescription liée hors ligne → reconnexion → vérification côté serveur (via l'écran ou l'API) que les deux lignes apparaissent avec leur `server_id`, sur 2 navigateurs/rôles (medecin et nurse).
- [ ] Vérification explicite demandée à l'utilisateur : inspecter directement le fichier SQLite local (pas seulement l'UI) pour un patient qui a par ailleurs un dossier toxico/spirituel, et confirmer qu'aucune table `toxico_dossiers`/`consultation_spirituelle` ni colonne de ce type n'apparaît dans la base locale.
