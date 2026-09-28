# Formulaires réellement utilisables hors ligne — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre réellement utilisables hors ligne (vraie coupure réseau) la création/modification de consultation et de prescription, la création de patient (médecin/nurse/secrétaire) avec enchaînement immédiat, et la recherche d'examen en caisse, sans jamais perdre ni mal rattacher une donnée médicale.

**Architecture:** Même motif que les sous-projets 2 et 3 : écriture toujours locale (PowerSync) pour `medecin`/`nurse`/`secretaire`, lecture HTTP d'abord avec secours local uniquement sur coupure réelle (`!err.response`), connecteur unique `DossierConnector.js`. Nouveautés : catalogues de référence synchronisés (examens, motifs), résolution serveur du patient par `patient_uuid` (approche A), table locale `sync_quarantine` (`localOnly`) pour retenir un patient refusé et ses enfants.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (Postgres 17), pytest ; Vue 3 + Pinia + `@powersync/web` ; PowerSync self-hosted (Docker, port 18080).

**Spec:** `docs/superpowers/specs/2026-09-24-chantier4-formulaires-hors-ligne-design.md`

## Global Constraints

- **Aucun commit git, jamais.** Chaque tâche : snapshot `cp` des fichiers touchés vers `.superpowers/sdd/2026-09-24-chantier4-formulaires-hors-ligne/task-N-before/` AVANT modification (attention aux homonymes : préfixer le nom si deux fichiers ont le même basename), revue via `diff -u`.
- Travail direct dans le répertoire principal, pas de worktree.
- **Migration DB réelle (`alembic upgrade head`) uniquement avec accord explicite de l'utilisateur**, demandé par le contrôleur.
- Rôles concernés par l'écriture locale : `medecin`, `nurse`, `secretaire`, via `authStore.hasRole([...])` (point de vérité unique, jamais `role === '...'` dans les stores/composants). Tout autre rôle garde le comportement HTTP d'origine.
- Secours local seulement si `!err.response` (vraie coupure) — jamais sur une erreur applicative 4xx/5xx.
- `sync-config.yaml` : **alias `FROM <table_source> AS <table_locale>` obligatoire** dès que les noms diffèrent (bug déjà subi deux fois).
- Toute table ajoutée dans `AppSchema.js` doit aussi être ajoutée à l'export `AppSchema = new Schema({...})`.
- Ne pas se fier à `rowsAffected` après un `UPDATE` PowerSync (documenté non fiable par le SDK) : vérifier l'existence de la ligne AVANT.
- Toute ligne locale lue par un template doit exposer les mêmes champs que la réponse HTTP (`prescription_id`, `record_id`, `patient`, `lab_exams_list` en tableau…).
- Textes d'interface nouveaux : en français en dur (précédent accepté du sous-projet 3), sauf l'entrée de menu qui passe par i18n (clé fournie).
- Frontend : vérifier à chaque tâche front `cd ah2-admin-web && npx vite build --mode production` (build vert). Backend : `python -m pytest <fichiers> -q`. Les 9 échecs pré-existants documentés dans `docs/superpowers/SUIVI-AVANCEMENT.md` ne sont pas des régressions.
- Ne jamais dispatcher de sous-agent depuis une tâche.

---

## File Structure

| Fichier | Rôle | Tâche |
|---|---|---|
| `alembic/versions/010_patients_uuid_motifs_pk.py` (créé) | index unique `patients.uuid` + PK `motif_translations.code` | 1 |
| `api_backend/backend_app/routes/patients/patients_schemas.py` | `PatientCreate.uuid` | 2 |
| `repositories/patient_repo.py` | écriture de l'uuid client, `get_id_by_uuid` | 2 |
| `api_backend/backend_app/routes/patients/patients_endpoints.py` | rejeu idempotent | 2 |
| `tests/test_patients_uuid.py` (créé) | tests patients uuid | 2 |
| `api_backend/backend_app/utils/patient_resolution.py` (créé) | `resolve_patient_id()` | 3 |
| `api_backend/backend_app/routes/medical_records/schemas.py`, `medical_records_endpoint.py` | `patient_uuid` | 3 |
| `api_backend/backend_app/routes/prescription/prescriptions_schemas.py`, `prescriptions_endpoints.py` | `patient_uuid` | 3 |
| `tests/test_patient_uuid_resolution.py` (créé) | tests résolution | 3 |
| `powersync/sync-config.yaml` | streams catalogues + `lab_exams_list` | 4 |
| `ah2-admin-web/src/powersync-client/AppSchema.js` | nouvelles tables/colonnes | 4 |
| `ah2-admin-web/src/powersync-client/client.js` | souscriptions | 4 |
| `ah2-admin-web/src/powersync-client/referenceData.js` (créé) | lecture locale catalogue examens | 5 |
| `ah2-admin-web/src/stores/medicalRecordStore.js`, `prescriptionStore.js`, `services/labGateway.js` | secours catalogues | 5 |
| `ah2-admin-web/src/composables/usePatientLookup.js` | recherche locale + `patientUuid` | 6 |
| `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue`, `components/medical-records/MedicalRecordModal.vue` | usage du composable | 6 |
| `ah2-admin-web/src/stores/medicalRecordStore.js`, `prescriptionStore.js` | `patient_uuid`, update local, listes locales | 7 |
| `ah2-admin-web/src/views/modules/prescriptions/PrescriptionsList.vue`, `views/modules/medical-records/MedicalRecordsList.vue` | clés/boutons lignes locales | 7 |
| `ah2-admin-web/src/stores/patientStore.js`, `stores/patientDossierStore.js`, `views/modules/patients/PatientList.vue`, `views/modules/patients/PatientDetailView.vue` | création patient hors ligne, fiche par uuid | 8 |
| `ah2-admin-web/src/powersync-client/syncQuarantine.js` (créé) | quarantaine | 9 |
| `ah2-admin-web/src/powersync-client/DossierConnector.js`, `services/MedicalRecordGateway.js`, `services/PrescriptionGateway.js` | nouveaux cases + quarantaine | 9 |
| `ah2-admin-web/src/views/modules/sync/SyncFailuresView.vue` (créé), `composables/useSyncQuarantineCount.js` (créé), `router/index.js`, `components/layout/MedicalLayout.vue`, `components/layout/SecretaireLayout.vue`, `i18n.js` | écran des échecs + menu | 10 |

---

### Task 1: Migration 010 — unicité `patients.uuid` + clé primaire `motif_translations`

**Files:**
- Create: `alembic/versions/010_patients_uuid_motifs_pk.py`

**Interfaces:**
- Produces: index unique `patients_uuid_key` sur `public.patients(uuid)` (requis par Tâches 2/3) ; PK `motif_translations_pkey` sur `public.motif_translations(code)` (requis par la réplication PowerSync du stream `reference_motifs`, Tâche 4).

Données vérifiées au cadrage (2026-09-24) : 102 patients / 102 uuid distincts ; 6 motifs / 6 codes distincts ; `motif_translations` sans aucune PK (`relreplident = d`).

- [ ] **Step 1: Snapshot** — rien à snapshoter (fichier créé).

- [ ] **Step 2: Créer la migration**

```python
"""unique patients.uuid + primary key motif_translations.code

Revision ID: 010_patients_uuid_motifs_pk
Revises: 009_caisse_uuid_and_upload_error
Create Date: 2026-09-24 00:00:00.000000

Chantier 4, sous-projet 4 (formulaires hors ligne) :

1. patients.uuid existe deja (NOT NULL, defaut gen_random_uuid()) et
   models/patient.py le declare unique=True, mais aucun index unique
   n'existe reellement en base - meme situation que K1 (migration 004,
   appointments). Le serveur doit desormais resoudre un patient par son
   uuid (consultation/prescription creees hors ligne pour un patient
   lui-meme cree hors ligne) et rendre idempotent le rejeu d'un
   POST /patients : l'unicite doit etre garantie par la base.

2. motif_translations n'a aucune cle primaire. La replication logique
   PowerSync (stream reference_motifs) a besoin d'une identite de
   replique pour suivre les mises a jour de cette table.

Verifie avant ecriture (2026-09-24) : 102 patients / 102 uuid distincts,
6 motifs / 6 codes distincts - applicable sans nettoyage prealable.
IF NOT EXISTS / verification pg_constraint : rejouable sans risque.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_patients_uuid_motifs_pk'
down_revision: Union[str, Sequence[str], None] = '009_caisse_uuid_and_upload_error'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS patients_uuid_key
            ON public.patients (uuid);
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'motif_translations_pkey'
            ) THEN
                ALTER TABLE public.motif_translations
                    ADD CONSTRAINT motif_translations_pkey PRIMARY KEY (code);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Reversible sans risque - retire uniquement les garanties, ne modifie
    ni ne supprime aucune donnee."""
    op.execute("""
        ALTER TABLE public.motif_translations
            DROP CONSTRAINT IF EXISTS motif_translations_pkey;
    """)
    op.execute("""
        DROP INDEX IF EXISTS public.patients_uuid_key;
    """)
```

- [ ] **Step 3: Vérifier la syntaxe sans appliquer**

Run: `python -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('m','alembic/versions/010_patients_uuid_motifs_pk.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.revision, m.down_revision)"`
Expected: `010_patients_uuid_motifs_pk 009_caisse_uuid_and_upload_error`

Run: `alembic heads`
Expected: une seule tête, `010_patients_uuid_motifs_pk (head)`.

- [ ] **Step 4: NE PAS appliquer.** Signaler DONE au contrôleur : l'application réelle (`alembic upgrade head`) et la régénération de `ci/schema_only.sql` sont faites par le contrôleur après accord explicite de l'utilisateur.

---

### Task 2: Backend — `POST /patients` accepte un `uuid` client, rejeu idempotent

**Files:**
- Modify: `api_backend/backend_app/routes/patients/patients_schemas.py` (classe `PatientCreate`, ligne ~67)
- Modify: `repositories/patient_repo.py` (`create_patient`, lignes ~125-136 ; nouvelle méthode après `get_by_id`)
- Modify: `api_backend/backend_app/routes/patients/patients_endpoints.py` (import ligne 1, `create_patient` lignes ~404-440)
- Create: `tests/test_patients_uuid.py`

**Interfaces:**
- Consumes: index unique `patients_uuid_key` (Tâche 1, appliquée par le contrôleur).
- Produces: `POST /patients/` accepte `uuid` (str UUID) optionnel ; même `uuid` rejoué → **200** + patient existant ; `national_id` déjà pris par un autre patient → **409**. `PatientRepository.get_id_by_uuid(client_uuid: str, only_active: bool = False) -> Optional[int]` (réutilisée par Tâche 3).

- [ ] **Step 1: Snapshot** des 3 fichiers modifiés vers `task-2-before/`.

- [ ] **Step 2: Écrire les tests (échouent)** — `tests/test_patients_uuid.py` :

```python
# tests/test_patients_uuid.py
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def _uuid_of(db_session, patient_id):
    return db_session.execute(
        text("SELECT uuid::text FROM patients WHERE patient_id = :pid"), {"pid": patient_id}
    ).scalar()


def test_create_patient_avec_uuid_client_le_persiste(db_session, api_client):
    """Chantier 4 sous-projet 4 : un patient cree hors ligne fournit son
    uuid - le serveur doit le persister tel quel (sinon la ligne locale
    PowerSync ne correspond jamais a la ligne confirmee)."""
    create_test_user(db_session, "test_pat_uuid_nurse", "nurse", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_nurse", TEST_PASSWORD)

    client_uuid = "aaaaaaaa-1111-2222-3333-444444444444"
    resp = client.post("/patients/", json={
        "first_name": "Hors", "last_name": "Ligne", "birth_date": "1990-01-01",
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert _uuid_of(db_session, resp.json()["patient_id"]) == client_uuid


def test_create_patient_rejoue_meme_uuid_est_idempotent(db_session, api_client):
    """Rejeu d'un envoi dont la reponse a ete perdue (coupure) : 200 avec le
    patient deja cree, jamais un doublon ni un 500 (un 500 bloquerait la
    file d'envoi PowerSync indefiniment)."""
    create_test_user(db_session, "test_pat_uuid_sec", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_sec", TEST_PASSWORD)

    client_uuid = "bbbbbbbb-1111-2222-3333-444444444444"
    payload = {"first_name": "Rejeu", "last_name": "Test", "birth_date": "1991-02-02", "uuid": client_uuid}
    first = client.post("/patients/", json=payload, headers=headers)
    second = client.post("/patients/", json=payload, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["patient_id"] == first.json()["patient_id"]
    count = db_session.execute(
        text("SELECT count(*) FROM patients WHERE uuid = CAST(:u AS uuid)"), {"u": client_uuid}
    ).scalar()
    assert count == 1


def test_create_patient_national_id_deja_pris_renvoie_409(db_session, api_client):
    """Vrai doublon (autre patient, autre uuid) : 409, c'est ce code qui
    declenche la quarantaine cote client - jamais 500."""
    create_test_user(db_session, "test_pat_uuid_nurse2", "nurse", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_nurse2", TEST_PASSWORD)

    base = {"first_name": "Doublon", "last_name": "Nid", "birth_date": "1992-03-03", "national_id": "NID-TEST-DOUBLON-010"}
    first = client.post("/patients/", json={**base, "uuid": "cccccccc-1111-2222-3333-444444444444"}, headers=headers)
    second = client.post("/patients/", json={**base, "uuid": "dddddddd-1111-2222-3333-444444444444"}, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text


def test_create_patient_uuid_invalide_renvoie_422(db_session, api_client):
    create_test_user(db_session, "test_pat_uuid_nurse3", "nurse", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_nurse3", TEST_PASSWORD)

    resp = client.post("/patients/", json={
        "first_name": "Mauvais", "last_name": "Uuid", "birth_date": "1993-04-04", "uuid": "pas-un-uuid",
    }, headers=headers)
    assert resp.status_code == 422, resp.text


def test_index_unique_patients_uuid_present(db_session):
    """Migration 010 : deux patients ne peuvent pas partager un uuid."""
    user = create_test_user(db_session, "test_pat_uuid_idx", "admin", password=TEST_PASSWORD)
    pid_a, _ = create_test_patient(db_session, user, first_name="IdxA")
    pid_b, _ = create_test_patient(db_session, user, first_name="IdxB")
    uuid_a = _uuid_of(db_session, pid_a)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text("UPDATE patients SET uuid = CAST(:u AS uuid) WHERE patient_id = :pid"),
                {"u": uuid_a, "pid": pid_b},
            )
```

- [ ] **Step 3: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_patients_uuid.py -q`
Expected: échecs sur les 4 premiers tests (uuid ignoré / 201 au lieu de 200 / 201 au lieu de 422). `test_index_unique_patients_uuid_present` passe seulement si la migration 010 est appliquée (sinon échec — signaler au contrôleur, ne pas appliquer soi-même).

- [ ] **Step 4: `PatientCreate.uuid`** — dans `patients_schemas.py`, ajouter en tête `import uuid as uuid_lib` (après `import re`), puis dans `class PatientCreate`, juste après `is_spiritual: bool = False` :

```python
    # Chantier 4 sous-projet 4 : uuid client d'un patient cree hors ligne
    # (PowerSync). Persiste tel quel ; un rejeu du meme uuid est idempotent
    # cote endpoint (voir patients_endpoints.create_patient).
    uuid: Optional[str] = None

    @field_validator("uuid", mode="before")
    @classmethod
    def _val_uuid_create(cls, v):
        if v in (None, ""):
            return None
        return str(uuid_lib.UUID(str(v)))
```

- [ ] **Step 5: Écriture de l'uuid dans le dépôt** — dans `repositories/patient_repo.py::create_patient`, remplacer :

```python
        patient_id, patient_code = row[0], row[1]
        
        # 🛑 self.session.commit() RETIRÉ
        
        return int(patient_id), patient_code
```

par :

```python
        patient_id, patient_code = row[0], row[1]

        # La fonction stockee create_patient() ne prend pas d'uuid : l'uuid
        # client (patient cree hors ligne) est ecrit juste apres l'insertion,
        # dans la meme transaction (aucun commit ici, gere par l'appelant).
        client_uuid = data.get("uuid")
        if client_uuid:
            self.session.execute(
                text("UPDATE patients SET uuid = CAST(:u AS uuid) WHERE patient_id = :pid"),
                {"u": str(client_uuid), "pid": int(patient_id)},
            )

        # 🛑 self.session.commit() RETIRÉ

        return int(patient_id), patient_code
```

Puis ajouter, juste avant `def get_by_id(self, patient_id: int)` :

```python
    def get_id_by_uuid(self, client_uuid: str, only_active: bool = False) -> Optional[int]:
        """patient_id correspondant a un uuid (index unique patients_uuid_key).
        only_active=True exclut les patients supprimes (resolution d'un
        rattachement consultation/prescription) ; False les inclut (rejeu
        idempotent d'une creation)."""
        sql = "SELECT patient_id FROM patients WHERE uuid = CAST(:u AS uuid)"
        if only_active:
            sql += " AND is_deleted = false"
        row = self.session.execute(text(sql), {"u": str(client_uuid)}).fetchone()
        return int(row[0]) if row else None
```

(`Optional` et `text` sont déjà importés dans ce fichier — vérifier les imports en tête ; ajouter `from typing import Optional` s'il manquait.)

- [ ] **Step 6: Rejeu idempotent dans l'endpoint** — dans `patients_endpoints.py`, ligne 1, ajouter `Response` à l'import :

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
```

Puis remplacer la signature et le début de `create_patient` :

```python
def create_patient(
    data: PatientCreate,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    try:
        # 🟢 CHANGEMENT ICI : On appelle la méthode "Sync" qui fait le COMMIT
```

par :

```python
def create_patient(
    data: PatientCreate,
    response: Response,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    try:
        # Rejeu idempotent (chantier 4 sous-projet 4) : un patient cree hors
        # ligne peut etre renvoye si la reponse du premier envoi a ete perdue
        # (coupure). Meme uuid deja present = succes deja acquis : 200 avec le
        # patient existant, jamais un doublon.
        if data.uuid:
            existing_id = patient_ctrl.repo.get_id_by_uuid(data.uuid)
            if existing_id is not None:
                existing = patient_ctrl.repo.get_by_id(existing_id)
                if existing:
                    response.status_code = status.HTTP_200_OK
                    return _safe_validate_patient(existing)

        # 🟢 CHANGEMENT ICI : On appelle la méthode "Sync" qui fait le COMMIT
```

Le reste de la fonction est inchangé (le `except IntegrityError` existant traduit déjà le doublon `national_id` en 409).

- [ ] **Step 7: Lancer les tests**

Run: `python -m pytest tests/test_patients_uuid.py tests/test_patients.py -q`
Expected: `test_patients_uuid.py` 5/5 (migration 010 appliquée par le contrôleur au préalable) ; `test_patients.py` sans nouvel échec par rapport aux échecs pré-existants documentés.

---

### Task 3: Backend — consultation/prescription rattachables par `patient_uuid`

**Files:**
- Create: `api_backend/backend_app/utils/patient_resolution.py`
- Modify: `api_backend/backend_app/routes/medical_records/schemas.py` (`MedicalRecordCreate`, ~ligne 28)
- Modify: `api_backend/backend_app/routes/medical_records/medical_records_endpoint.py` (`create_record`, ~lignes 128-137)
- Modify: `api_backend/backend_app/routes/prescription/prescriptions_schemas.py` (`PrescriptionCreate`, ~ligne 124)
- Modify: `api_backend/backend_app/routes/prescription/prescriptions_endpoints.py` (`create_prescription`, ~lignes 140-146)
- Create: `tests/test_patient_uuid_resolution.py`

**Interfaces:**
- Consumes: index unique `patients_uuid_key` (Tâche 1).
- Produces: `POST /medical_records/` et `POST /prescriptions/` acceptent `patient_uuid` (str) quand `patient_id` est absent ; `patient_uuid` inconnu → 422 ; ni l'un ni l'autre → 400. `resolve_patient_id(session, patient_id, patient_uuid) -> int`.

- [ ] **Step 1: Snapshot** des 4 fichiers modifiés vers `task-3-before/` (préfixer : `medical_schemas.py`, `prescriptions_schemas.py`, etc. — homonymes possibles).

- [ ] **Step 2: Tests (échouent)** — `tests/test_patient_uuid_resolution.py` :

```python
# tests/test_patient_uuid_resolution.py
from datetime import date

from sqlalchemy import text

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from api_backend.backend_app.routes.prescription import prescriptions_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def _uuid_of(db_session, patient_id):
    return db_session.execute(
        text("SELECT uuid::text FROM patients WHERE patient_id = :pid"), {"pid": patient_id}
    ).scalar()


def test_medical_record_par_patient_uuid(db_session, api_client):
    """Consultation creee hors ligne pour un patient lui-meme cree hors
    ligne : le client ne connait que l'uuid du patient."""
    medecin = create_test_user(db_session, "test_res_med1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="ResMed")
    db_session.flush()
    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_res_med1", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_uuid": _uuid_of(db_session, patient_id),
        "motif_code": "consultation",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["patient_id"] == patient_id


def test_medical_record_patient_uuid_inconnu_renvoie_422(db_session, api_client):
    create_test_user(db_session, "test_res_med2", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_res_med2", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_uuid": "eeeeeeee-1111-2222-3333-444444444444",
        "motif_code": "consultation",
    }, headers=headers)
    assert resp.status_code == 422, resp.text


def test_medical_record_sans_patient_renvoie_400(db_session, api_client):
    create_test_user(db_session, "test_res_med3", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_res_med3", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={"motif_code": "consultation"}, headers=headers)
    assert resp.status_code == 400, resp.text


def test_prescription_par_patient_uuid(db_session, api_client):
    medecin = create_test_user(db_session, "test_res_presc1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="ResPresc")
    db_session.flush()
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_res_presc1", TEST_PASSWORD)

    resp = client.post("/prescriptions/", json={
        "patient_uuid": _uuid_of(db_session, patient_id),
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": str(date.today()),
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["patient_id"] == patient_id


def test_prescription_patient_uuid_inconnu_renvoie_422(db_session, api_client):
    create_test_user(db_session, "test_res_presc2", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_res_presc2", TEST_PASSWORD)

    resp = client.post("/prescriptions/", json={
        "patient_uuid": "ffffffff-1111-2222-3333-444444444444",
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": str(date.today()),
    }, headers=headers)
    assert resp.status_code == 422, resp.text
```

- [ ] **Step 3: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_patient_uuid_resolution.py -q`
Expected: FAIL (422 de validation Pydantic sur `patient_id` manquant, au lieu des codes attendus).

- [ ] **Step 4: Créer `api_backend/backend_app/utils/patient_resolution.py`**

```python
import uuid as uuid_lib
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session


def resolve_patient_id(session: Session, patient_id: Optional[int], patient_uuid: Optional[str]) -> int:
    """patient_id a utiliser pour une creation de consultation/prescription.

    Chantier 4 sous-projet 4 : un patient cree hors ligne n'a pas encore
    d'identifiant serveur cote client - ses consultations/prescriptions
    hors ligne portent seulement son uuid. La file PowerSync etant ordonnee,
    le patient est toujours cree cote serveur avant elles : on le retrouve
    ici par son uuid (index unique patients_uuid_key, migration 010).
    """
    if patient_id is not None:
        return patient_id
    if not patient_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id ou patient_uuid est requis")
    try:
        normalized = str(uuid_lib.UUID(str(patient_uuid)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="patient_uuid invalide")
    row = session.execute(
        text("SELECT patient_id FROM patients WHERE uuid = CAST(:u AS uuid) AND is_deleted = false"),
        {"u": normalized},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Patient introuvable pour ce patient_uuid")
    return int(row[0])
```

- [ ] **Step 5: Schéma consultation** — dans `medical_records/schemas.py`, remplacer :

```python
class MedicalRecordCreate(MedicalRecordBase):
    consultation_date: Optional[datetime] = None  # server_default possible
```

par :

```python
class MedicalRecordCreate(MedicalRecordBase):
    # patient_id devient optionnel a la creation SEULEMENT (la reponse garde
    # patient_id obligatoire via MedicalRecordBase) : un patient cree hors
    # ligne n'est connu que par son uuid (resolution cote endpoint).
    patient_id: Optional[int] = None
    patient_uuid: Optional[str] = Field(None, description="UUID du patient cree hors ligne (resolu en patient_id cote serveur)")
    consultation_date: Optional[datetime] = None  # server_default possible
```

- [ ] **Step 6: Endpoint consultation** — dans `medical_records_endpoint.py`, ajouter l'import (après les imports `from .schemas ...`) :

```python
from api_backend.backend_app.utils.patient_resolution import resolve_patient_id
```

puis, dans `create_record`, remplacer :

```python
        if data.patient_id is None:
            raise HTTPException(status_code=400, detail="patient_id est requis")

        created = medical_ctrl.create_record(data.model_dump())
```

par :

```python
        data.patient_id = resolve_patient_id(medical_ctrl.repo.session, data.patient_id, data.patient_uuid)

        created = medical_ctrl.create_record(data.model_dump(exclude={"patient_uuid"}))
```

- [ ] **Step 7: Schéma prescription** — dans `prescriptions_schemas.py`, dans `class PrescriptionCreate`, ajouter en tête du corps (avant `medication: Optional[str] = Field(..., min_length=1)`) :

```python
    # Optionnel a la creation SEULEMENT (voir MedicalRecordCreate) :
    # patient cree hors ligne connu par son uuid.
    patient_id: Optional[int] = None
    patient_uuid: Optional[str] = None
```

- [ ] **Step 8: Endpoint prescription** — dans `prescriptions_endpoints.py`, ajouter l'import :

```python
from api_backend.backend_app.utils.patient_resolution import resolve_patient_id
```

puis dans `create_prescription`, remplacer :

```python
    payload = data.model_dump()
```

par :

```python
    payload = data.model_dump(exclude={"patient_uuid"})
    payload["patient_id"] = resolve_patient_id(prescription_ctrl.repo.session, data.patient_id, data.patient_uuid)
```

- [ ] **Step 9: Lancer les tests**

Run: `python -m pytest tests/test_patient_uuid_resolution.py tests/test_medical_records_uuid.py tests/test_prescriptions_uuid.py tests/test_prescriptions.py -q`
Expected: `test_patient_uuid_resolution.py` 5/5 ; aucun nouvel échec ailleurs (les échecs `test_prescriptions.py` pré-existants documentés restent identiques).

---

### Task 4: Synchronisation — catalogues de référence, `lab_exams_list`, schéma local, souscriptions

**Files:**
- Modify: `powersync/sync-config.yaml` (stream `clinical_prescriptions` + 2 nouveaux streams en fin de fichier)
- Modify: `ah2-admin-web/src/powersync-client/AppSchema.js`
- Modify: `ah2-admin-web/src/powersync-client/client.js` (bloc de souscription, ~lignes 96-117)

**Interfaces:**
- Consumes: PK `motif_translations_pkey` (Tâche 1).
- Produces: tables locales `exam_catalog(server_id, code, nom, categorie, prix)`, `motifs(code, label_fr, label_en)`, `sync_quarantine(kind, local_id, patient_uuid, payload, error, created_at)` (localOnly) ; colonnes `patients.residence/national_id/assurance/father_name/mother_name`, `medical_records.patient_uuid`, `prescriptions.patient_uuid` ; `prescriptions.lab_exams_list` désormais synchronisé (texte JSON).

- [ ] **Step 1: Snapshot** des 3 fichiers.

- [ ] **Step 2: `lab_exams_list` dans `clinical_prescriptions`** — dans `sync-config.yaml`, remplacer :

```yaml
          prescriptions.prescribed_by_name, prescriptions.is_lab_order
        FROM prescriptions
```

par :

```yaml
          prescriptions.prescribed_by_name, prescriptions.is_lab_order,
          prescriptions.lab_exams_list::text AS lab_exams_list
        FROM prescriptions
```

(colonne `jsonb` en base : `::text` donne un JSON texte `["..."]`, identique au format écrit localement par `prescriptionStore`. Sans elle, une demande d'examen synchronisée arrive sans sa liste d'examens et ne peut pas être modifiée hors ligne.)

- [ ] **Step 3: Nouveaux streams** — ajouter à la fin de `sync-config.yaml` (même indentation que les autres streams, sous `streams:`) :

```yaml
  # Catalogues de reference en lecture seule (chantier 4 sous-projet 4) -
  # indispensables pour que les formulaires restent utilisables hors ligne
  # (motif obligatoire d'une consultation, examens d'une demande/facture).
  # Alias FROM ... AS ... OBLIGATOIRE : les noms locaux different des
  # tables Postgres - sans alias, les lignes atterrissent dans une table
  # locale non declaree et restent invisibles (bug deja subi deux fois :
  # patients_lookup, pharmacy_stock).
  reference_exam_catalog:
    auto_subscribe: false
    queries:
      - SELECT id::text AS id, id AS server_id, code, nom, categorie,
          prix::text AS prix
        FROM examens AS exam_catalog

  reference_motifs:
    auto_subscribe: false
    queries:
      - SELECT code AS id, code, label_fr, label_en
        FROM motif_translations AS motifs
```

- [ ] **Step 4: `AppSchema.js`** — dans `const patients = new Table({...})`, ajouter après `is_spiritual: column.integer,` :

```js
  // Champs du formulaire de creation (patient cree hors ligne, chantier 4
  // sous-projet 4) - jamais descendus par clinical_patients, remplis
  // uniquement par une ecriture locale et relus par le connecteur.
  residence: column.text,
  national_id: column.text,
  assurance: column.text,
  father_name: column.text,
  mother_name: column.text,
```

Dans `medical_records`, ajouter après `created_by_name: column.text,` :

```js
    // uuid du patient quand celui-ci a ete cree hors ligne (pas encore de
    // server_id) - resolu cote serveur (POST /medical_records patient_uuid).
    patient_uuid: column.text,
```

et remplacer son index `{ indexes: { by_patient: ['patient_id'] } }` par `{ indexes: { by_patient: ['patient_id'], by_patient_uuid: ['patient_uuid'] } }`.

Dans `prescriptions`, ajouter après `lab_exams_list: column.text,` :

```js
    patient_uuid: column.text,
```

et remplacer son index par `{ indexes: { by_patient: ['patient_id'], by_medical_record: ['medical_record_id'], by_patient_uuid: ['patient_uuid'] } }`.

Ajouter, juste avant `export const AppSchema` :

```js
// Catalogues de reference, lecture seule (streams reference_exam_catalog /
// reference_motifs) - jamais ecrits localement.
const exam_catalog = new Table({
  server_id: column.integer,
  code: column.text,
  nom: column.text,
  categorie: column.text,
  prix: column.text,
});

const motifs = new Table({
  code: column.text,
  label_fr: column.text,
  label_en: column.text,
});

// Quarantaine des envois refuses definitivement (patient en doublon et ses
// consultations/prescriptions). localOnly : jamais synchronisee, donc jamais
// purgee par une reconciliation PowerSync - une donnee medicale retenue ici
// ne peut ni disparaitre ni partir vers le mauvais patient.
const sync_quarantine = new Table(
  {
    kind: column.text,
    local_id: column.text,
    patient_uuid: column.text,
    payload: column.text,
    error: column.text,
    created_at: column.text,
  },
  { localOnly: true, indexes: { by_patient_uuid: ['patient_uuid'] } }
);
```

et étendre l'export :

```js
export const AppSchema = new Schema({
  appointments,
  patients_lookup,
  doctors_lookup,
  patients,
  medical_records,
  prescriptions,
  lab_results,
  caisse,
  caisse_retrait,
  paiement_echelonne,
  pharmacy_stock,
  exam_catalog,
  motifs,
  sync_quarantine,
});
```

- [ ] **Step 5: Souscriptions** — dans `client.js`, remplacer :

```js
    if (role === 'secretaire') {
      streamHandles.push(db.syncStream('secretariat_caisse'));
      streamHandles.push(db.syncStream('secretariat_retraits'));
      streamHandles.push(db.syncStream('secretariat_payments'));
      streamHandles.push(db.syncStream('secretariat_pharmacy_stock'));
    }
```

par :

```js
    if (role === 'secretaire') {
      streamHandles.push(db.syncStream('secretariat_caisse'));
      streamHandles.push(db.syncStream('secretariat_retraits'));
      streamHandles.push(db.syncStream('secretariat_payments'));
      streamHandles.push(db.syncStream('secretariat_pharmacy_stock'));
    }
    // Catalogue d'examens : demandes d'examen (medecin/nurse) et facturation
    // d'un examen en caisse (secretaire). Motifs : consultation seulement.
    if (role === 'medecin' || role === 'nurse' || role === 'secretaire') {
      streamHandles.push(db.syncStream('reference_exam_catalog'));
    }
    if (role === 'medecin' || role === 'nurse') {
      streamHandles.push(db.syncStream('reference_motifs'));
    }
```

(Le garde `connectPowerSync` d'`auth.js`/`App.vue` couvre déjà ces 3 rôles — vérifier qu'il contient bien `medecin`, `nurse`, `secretaire`, ne rien y changer.)

- [ ] **Step 6: Build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

- [ ] **Step 7: Redémarrer PowerSync et vérifier les règles** (après application de la migration 010 par le contrôleur)

Run: `docker ps --format "{{.Names}}: {{.Status}}" | grep powersync` — les 2 conteneurs `Up` et `(healthy)`.
Run: `docker restart powersync-powersync-1`, attendre ~15 s, puis :

```bash
cd powersync && TOKEN=$(grep "^PS_ADMIN_TOKEN" .env | cut -d= -f2-) && curl -s -m 10 -X POST http://localhost:18080/api/admin/v1/diagnostics -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"sync_rules_content":false}' | python -c "import sys,json; d=json.load(sys.stdin)['data']; a=d['active_sync_rules']; print('errors:', a['errors']); print([ (t['name'], t['errors']) for t in a['connections'][0]['tables'] if t['name'] in ('examens','motif_translations','prescriptions')])"
```

Expected: `errors: []` et les 3 tables présentes sans erreur. Ne PAS utiliser `docker logs` (non fiable sur cette machine).

---

### Task 5: Catalogues hors ligne — motifs, examens (prescription et caisse)

**Files:**
- Create: `ah2-admin-web/src/powersync-client/referenceData.js`
- Modify: `ah2-admin-web/src/stores/medicalRecordStore.js` (`fetchMotifs`, ~lignes 51-59)
- Modify: `ah2-admin-web/src/stores/prescriptionStore.js` (`fetchExamTypes`, ~lignes 55-63 ; import)
- Modify: `ah2-admin-web/src/services/labGateway.js` (`getAllExams`, ~lignes 10-12 ; imports)

**Interfaces:**
- Consumes: tables locales `motifs`, `exam_catalog` (Tâche 4).
- Produces: `getExamCatalogLocal(): Promise<Array<{id, code, nom, categorie, prix}>>` — même forme que `GET /labo/exams` (`controller/lab_controller.py::_serialize_examen`, sans `nb_params`, jamais lu par ces écrans).

- [ ] **Step 1: Snapshot** des 3 fichiers modifiés.

- [ ] **Step 2: Créer `referenceData.js`**

```js
import { db } from '@/powersync-client/client';

// Lecture locale du catalogue d'examens, dans la meme forme que la reponse
// HTTP GET /labo/exams (controller/lab_controller.py::_serialize_examen) :
// les ecrans consommateurs (modale de prescription, caisse) n'ont ainsi rien
// a adapter entre le chemin en ligne et le secours hors ligne.
export async function getExamCatalogLocal() {
  const rows = await db.getAll('SELECT * FROM exam_catalog ORDER BY nom');
  return rows.map((r) => ({
    id: r.server_id,
    code: r.code,
    nom: r.nom,
    categorie: r.categorie,
    prix: Number(r.prix) || 0,
  }));
}
```

- [ ] **Step 3: Motifs** — dans `medicalRecordStore.js`, remplacer `fetchMotifs` par :

```js
    async function fetchMotifs() {
        try {
            const res = await MedicalRecordGateway.fetchMotifs();
            motifs.value = res.data || [];
        } catch (err) {
            // Le motif est obligatoire pour enregistrer une consultation
            // (MedicalRecordModal) : sans ce secours, toute consultation hors
            // ligne etait impossible (liste vide).
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Motifs hors ligne - secours sur la table locale PowerSync:', err);
                motifs.value = await db.getAll('SELECT code, label_fr FROM motifs ORDER BY label_fr');
                return;
            }
            console.error('Erreur chargement motifs:', err);
            motifs.value = [];
        }
    }
```

- [ ] **Step 4: Examens (prescription)** — dans `prescriptionStore.js`, ajouter l'import `import { getExamCatalogLocal } from '@/powersync-client/referenceData';` puis remplacer `fetchExamTypes` par :

```js
    async function fetchExamTypes() {
        try {
            const res = await PrescriptionGateway.fetchExamTypes();
            examTypes.value = res.data || [];
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Catalogue examens hors ligne - secours sur la table locale PowerSync:', err);
                examTypes.value = await getExamCatalogLocal();
                return;
            }
            console.error('Erreur chargement types examens:', err);
            examTypes.value = [];
        }
    }
```

- [ ] **Step 5: Examens (caisse)** — dans `labGateway.js`, ajouter les imports en tête :

```js
import { useAuthStore } from '@/stores/auth';
import { getExamCatalogLocal } from '@/powersync-client/referenceData';
```

puis remplacer `getAllExams` par :

```js
    async getAllExams() {
        try {
            return await api.get('/labo/exams');
        } catch (err) {
            // Secours hors ligne (caisse : facturation d'un examen). Garde de
            // role explicite : le labo/admin hors ligne voit l'erreur reseau,
            // jamais un catalogue local qui n'est pas synchronise pour eux.
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['secretaire', 'medecin', 'nurse'])) {
                return { data: await getExamCatalogLocal() };
            }
            throw err;
        }
    },
```

(`CaisseInvoiceModal.vue` lit `body.data` : le retour `{ data: [...] }` est compatible sans le modifier.)

- [ ] **Step 6: Build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 6: Recherche patient hors ligne et `patientUuid` dans les modales

**Files:**
- Modify: `ah2-admin-web/src/composables/usePatientLookup.js` (réécriture complète)
- Modify: `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue` (script, ~lignes 192-341)
- Modify: `ah2-admin-web/src/components/medical-records/MedicalRecordModal.vue` (script, ~lignes 159-287)
- Modify: `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue` (`patientPrefill`, ~lignes 211-220)

**Interfaces:**
- Consumes: table locale `patients_lookup` (déjà synchronisée pour les 3 rôles).
- Produces: `usePatientLookup()` expose en plus `patientUuid` ; `setFromExisting({ patientId, patientUuid, code, firstName, lastName })`. Les deux modales émettent `patientUuid` dans le payload `save` (null si le patient a un id serveur). `patientSummary.patient_uuid` (fourni par la Tâche 8) est relayé par `patientPrefill.patientUuid`.

Deux bugs corrigés ici : (1) la recherche par code était HTTP seulement ; (2) `ensureLookup()` relançait une recherche serveur pour un patient pré-rempli (fiche patient) au moment d'enregistrer — hors ligne elle échouait et effaçait le patient (« patient introuvable »), même pour un patient déjà synchronisé.

- [ ] **Step 1: Snapshot** des 4 fichiers.

- [ ] **Step 2: Réécrire `usePatientLookup.js`**

```js
import { ref } from 'vue';
import api from '@/services/api';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';

// Composable partage de recherche patient par code (MedicalRecordModal,
// ConsultationModal, PrescriptionModal). Chantier 4 sous-projet 4 :
// secours local hors ligne sur patients_lookup (deja synchronise pour
// medecin/nurse/secretaire - memes patients qu'en ligne, GET /patients/
// etant ouvert a ces roles) et prise en charge d'un patient cree hors
// ligne, qui n'a pas encore d'id serveur ni de code : patientUuid.
export function usePatientLookup(getNotFoundMessage) {
  const patientCode = ref('');
  const patientId = ref(null);
  const patientUuid = ref(null);
  const patientName = ref('');
  const patientLookupMessage = ref('');

  let pendingLookup = null;
  let pendingLookupCode = null;

  function normalizeCode(raw) {
    const trimmed = (raw || '').trim();
    if (!trimmed) return '';
    let code = trimmed.toUpperCase();
    if (!code.startsWith('AH2-')) {
      code = `AH2-${code}`;
    }
    return code;
  }

  function applyMatch(match) {
    patientId.value = match.id || match.patient_id;
    patientUuid.value = null;
    patientName.value = [match.first_name, match.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  }

  function applyNotFound() {
    patientId.value = null;
    patientUuid.value = null;
    patientName.value = '';
    patientLookupMessage.value = getNotFoundMessage();
  }

  async function lookupPatient() {
    const code = normalizeCode(patientCode.value);
    if (!code) {
      patientId.value = null;
      patientUuid.value = null;
      patientName.value = '';
      patientLookupMessage.value = '';
      pendingLookup = null;
      pendingLookupCode = null;
      return;
    }
    patientCode.value = code;
    pendingLookupCode = code;

    pendingLookup = (async () => {
      try {
        const res = await api.get('/patients/', { params: { search: code, per_page: 5 } });
        const list = Array.isArray(res.data) ? res.data : (res.data.data || []);
        const match = list.find((p) => p.code_patient === code) || list[0] || null;
        if (match) applyMatch(match);
        else applyNotFound();
      } catch (err) {
        const authStore = useAuthStore();
        if (!err.response && authStore.hasRole(['medecin', 'nurse', 'secretaire'])) {
          const local = await db.getOptional(
            'SELECT patient_id, code_patient, first_name, last_name FROM patients_lookup WHERE code_patient = ?',
            [code]
          );
          if (local) {
            applyMatch(local);
            return;
          }
        } else {
          console.error('Erreur recherche patient:', err);
        }
        applyNotFound();
      }
    })();

    await pendingLookup;
  }

  async function ensureLookup() {
    const currentCode = normalizeCode(patientCode.value);
    if (!currentCode) return;

    if (pendingLookup && pendingLookupCode === currentCode) {
      await pendingLookup;
      return;
    }

    // Le code a change depuis le dernier lookup (ou aucun lookup n'a
    // encore ete declenche) : recherche fraiche plutot que d'attendre une
    // promesse perimee qui validerait le submit contre un autre patient.
    await lookupPatient();
  }

  // Patient deja connu (fiche patient, edition d'un dossier existant) :
  // marque comme resolu - ensureLookup() ne relance PAS de recherche pour ce
  // meme code (hors ligne, cette recherche echouait et effacait le patient).
  function setFromExisting({ patientId: pid, patientUuid: puuid, code, firstName, lastName }) {
    patientId.value = pid || null;
    patientUuid.value = pid ? null : (puuid || null);
    patientCode.value = code || '';
    pendingLookupCode = normalizeCode(code || '');
    pendingLookup = Promise.resolve();
    patientName.value = [firstName, lastName].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  }

  return {
    patientCode,
    patientId,
    patientUuid,
    patientName,
    patientLookupMessage,
    lookupPatient,
    ensureLookup,
    setFromExisting,
  };
}
```

- [ ] **Step 3: `MedicalRecordModal.vue`** — dans le script :

Remplacer le destructuring :

```js
const {
  patientCode,
  patientId,
  patientName,
  patientLookupMessage,
  lookupPatient,
  ensureLookup,
  setFromExisting,
} = usePatientLookup(() => t('medicalRecords.modal.patient_not_found'));
```

par :

```js
const {
  patientCode,
  patientId,
  patientUuid,
  patientName,
  patientLookupMessage,
  lookupPatient,
  ensureLookup,
  setFromExisting,
} = usePatientLookup(() => t('medicalRecords.modal.patient_not_found'));
```

Dans `onMounted`, remplacer :

```js
    setFromExisting({
      patientId: rec.patient_id || rec.patient?.patient_id || null,
      code: rec.patient?.code_patient || '',
```

par :

```js
    setFromExisting({
      patientId: rec.patient_id || rec.patient?.patient_id || null,
      patientUuid: rec.patient_uuid || null,
      code: rec.patient?.code_patient || '',
```

Dans `handleSubmit`, remplacer :

```js
  if (!patientId.value) {
    alert(t('medicalRecords.modal.patient_not_found'));
    return;
  }
```

par :

```js
  if (!patientId.value && !patientUuid.value) {
    alert(t('medicalRecords.modal.patient_not_found'));
    return;
  }
```

et dans l'`emit('save', {...})`, remplacer `patientId: patientId.value,` par :

```js
    patientId: patientId.value,
    patientUuid: patientUuid.value,
```

- [ ] **Step 4: `PrescriptionModal.vue`** — passer au composable partagé (fin de la copie locale, qui n'avait ni secours local ni `patientUuid`). Dans le script :

Ajouter l'import : `import { usePatientLookup } from '@/composables/usePatientLookup';`

Supprimer ces déclarations :

```js
const patientCode = ref('');
const patientId = ref(null);
const patientName = ref('');
const patientLookupMessage = ref('');
```

et les remplacer par :

```js
const {
  patientCode,
  patientId,
  patientUuid,
  patientName,
  patientLookupMessage,
  lookupPatient,
  ensureLookup,
  setFromExisting,
} = usePatientLookup(() => t('prescriptions.modal.patient_not_found'));
```

Supprimer entièrement le bloc `let pendingLookup = null;` et la fonction locale `async function lookupPatient() { ... }` (lignes ~221-263).

Dans `onMounted`, remplacer :

```js
    patientId.value = presc.patient_id || presc.patient?.patient_id || null;
    medicalRecordId.value = presc.medical_record_id || null;
    patientCode.value = presc.patient?.code_patient || '';
    patientName.value = [presc.patient?.first_name, presc.patient?.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
```

par :

```js
    setFromExisting({
      patientId: presc.patient_id || presc.patient?.patient_id || null,
      patientUuid: presc.patient_uuid || null,
      code: presc.patient?.code_patient || '',
      firstName: presc.patient?.first_name,
      lastName: presc.patient?.last_name,
    });
    medicalRecordId.value = presc.medical_record_id || null;
```

et remplacer :

```js
    const p = props.prefilledPatient;
    patientId.value = p.patientId || null;
    patientCode.value = p.code || '';
    patientName.value = [p.firstName, p.lastName].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
```

par :

```js
    setFromExisting(props.prefilledPatient);
```

Dans `handleSubmit`, remplacer :

```js
  if (pendingLookup) {
    await pendingLookup;
  } else if (!patientId.value && patientCode.value.trim()) {
    await lookupPatient();
  }

  if (!patientId.value) {
    alert(t('prescriptions.modal.patient_not_found'));
    return;
  }
```

par :

```js
  await ensureLookup();

  if (!patientId.value && !patientUuid.value) {
    alert(t('prescriptions.modal.patient_not_found'));
    return;
  }
```

et dans l'`emit('save', {...})`, remplacer `patientId: patientId.value,` par :

```js
    patientId: patientId.value,
    patientUuid: patientUuid.value,
```

Vérifier que le template n'utilise que `patientCode`, `patientId`, `patientLookupMessage`, `lookupPatient` (noms identiques fournis par le composable) ; si `ref` n'est plus utilisé nulle part dans le script, le retirer de l'import `vue`.

- [ ] **Step 5: `PatientDetailView.vue`** — remplacer :

```js
    return {
        patientId: p.patient_id,
        code: p.code,
```

par :

```js
    return {
        patientId: p.patient_id,
        patientUuid: p.patient_uuid || null,
        code: p.code,
```

- [ ] **Step 6: Build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 7: Consultations et prescriptions — `patient_uuid`, modification de prescription hors ligne, listes locales

**Files:**
- Modify: `ah2-admin-web/src/stores/medicalRecordStore.js`
- Modify: `ah2-admin-web/src/stores/prescriptionStore.js`
- Modify: `ah2-admin-web/src/views/modules/prescriptions/PrescriptionsList.vue`
- Modify: `ah2-admin-web/src/views/modules/medical-records/MedicalRecordsList.vue`

**Interfaces:**
- Consumes: colonnes `patient_uuid`, `lab_exams_list` (Tâche 4) ; `patientUuid` émis par les modales (Tâche 6).
- Produces: lignes locales exposées aux écrans avec `record_id`/`prescription_id` (= `server_id`, null si non synchronisé), `local_id` (= uuid local), `patient { patient_id, code_patient, first_name, last_name }`, `lab_exams_list` tableau, `is_lab_order` booléen. `updatePrescription(prescriptionId, data)` écrit localement pour medecin/nurse.

Corrige aussi un bug latent du sous-projet 2 : après une écriture locale, les listes relues localement n'avaient ni `record_id`/`prescription_id` (clés Vue en collision, boutons cassés) ni `patient` (nom vide), et `lab_exams_list` restait une chaîne JSON — le `.join()` du template de `PrescriptionsList.vue` plantait tout le rendu après une demande d'examen créée localement.

- [ ] **Step 1: Snapshot** des 4 fichiers.

- [ ] **Step 2: `prescriptionStore.js` — mapping et refresh local** — remplacer `refreshPrescriptionsLocal` par :

```js
    // Forme identique a la reponse HTTP (registre Important I1 + famille de
    // bugs "champ derive du serveur jamais peuple localement") : les ecrans
    // lisent prescription_id, patient.*, lab_exams_list (tableau).
    function parseList(raw) {
        if (!raw) return [];
        try {
            const v = JSON.parse(raw);
            return Array.isArray(v) ? v : [];
        } catch {
            return [];
        }
    }

    function mapLocalPrescription(r) {
        return {
            ...r,
            prescription_id: r.server_id,
            local_id: r.id,
            is_lab_order: !!r.is_lab_order,
            lab_exams_list: parseList(r.lab_exams_list),
            patient: {
                patient_id: r.patient_id,
                code_patient: r.p_code,
                first_name: r.p_first_name,
                last_name: r.p_last_name,
            },
        };
    }

    async function refreshPrescriptionsLocal() {
        const rows = await db.getAll(
            `SELECT pr.*,
                    COALESCE(pl.code_patient, lp.code_patient) AS p_code,
                    COALESCE(pl.first_name, lp.first_name) AS p_first_name,
                    COALESCE(pl.last_name, lp.last_name) AS p_last_name
             FROM prescriptions pr
             LEFT JOIN patients_lookup pl ON pl.patient_id = pr.patient_id
             LEFT JOIN patients lp ON lp.id = pr.patient_uuid
             ORDER BY pr.start_date DESC`
        );
        prescriptions.value = rows.map(mapLocalPrescription);
        totalItems.value = rows.length;
    }
```

- [ ] **Step 3: `prescriptionStore.js` — secours de liste** — dans `fetchPrescriptions`, remplacer :

```js
        } catch (err) {
            console.error('Erreur chargement prescriptions:', err);
            prescriptions.value = [];
        } finally {
```

par :

```js
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Prescriptions hors ligne - secours sur la table locale PowerSync:', err);
                await refreshPrescriptionsLocal();
            } else {
                console.error('Erreur chargement prescriptions:', err);
                prescriptions.value = [];
            }
        } finally {
```

- [ ] **Step 4: `prescriptionStore.js` — création avec `patient_uuid`** — dans `createPrescription`, remplacer le `db.execute` :

```js
            await db.execute(
                `INSERT INTO prescriptions (
                    id, patient_id, medical_record_id, medication, dosage, frequency,
                    duration, start_date, end_date, notes, is_lab_order, lab_exams_list
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId, data.medicalRecordId || null, data.medication || null,
```

par :

```js
            await db.execute(
                `INSERT INTO prescriptions (
                    id, patient_id, patient_uuid, medical_record_id, medication, dosage, frequency,
                    duration, start_date, end_date, notes, is_lab_order, lab_exams_list
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId || null, data.patientUuid || null, data.medicalRecordId || null, data.medication || null,
```

(le reste du tableau de paramètres inchangé).

- [ ] **Step 5: `prescriptionStore.js` — modification locale** — remplacer `updatePrescription` par :

```js
    // Ecriture locale pour medecin/nurse (connecteur : prescriptions:PATCH).
    // prescriptionId = server_id (bouton "modifier" desactive tant qu'une
    // prescription n'est pas synchronisee). Existence verifiee AVANT
    // l'UPDATE : rowsAffected n'est pas fiable pour un UPDATE PowerSync, et
    // une modification sur une ligne absente localement serait perdue sans
    // bruit.
    async function updatePrescription(prescriptionId, data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['medecin', 'nurse'])) {
            const existing = await db.getOptional(
                'SELECT id FROM prescriptions WHERE id = ? OR server_id = ?',
                [String(prescriptionId), prescriptionId]
            );
            if (!existing) {
                throw new Error('Prescription introuvable localement - modification impossible hors ligne.');
            }
            await db.execute(
                `UPDATE prescriptions SET
                    medication = ?, dosage = ?, frequency = ?, duration = ?, start_date = ?,
                    end_date = ?, notes = ?, is_lab_order = ?, lab_exams_list = ?
                 WHERE id = ?`,
                [
                    data.medication || null, data.dosage || null, data.frequency || null,
                    data.duration || null, data.startDate || null, data.endDate || null,
                    data.notes || null, data.isLabOrder ? 1 : 0,
                    JSON.stringify(data.labExamsList || []), existing.id,
                ]
            );
            await refreshPrescriptionsLocal();
            return;
        }

        await PrescriptionGateway.updatePrescription(prescriptionId, data);
        await fetchPrescriptions();
    }
```

- [ ] **Step 6: `medicalRecordStore.js` — mapping, refresh, secours de liste** — remplacer `refreshMedicalRecordsLocal` par :

```js
    function mapLocalMedicalRecord(r) {
        return {
            ...r,
            record_id: r.server_id,
            local_id: r.id,
            patient: {
                patient_id: r.patient_id,
                code_patient: r.p_code,
                first_name: r.p_first_name,
                last_name: r.p_last_name,
            },
        };
    }

    async function refreshMedicalRecordsLocal() {
        const rows = await db.getAll(
            `SELECT mr.*,
                    COALESCE(pl.code_patient, lp.code_patient) AS p_code,
                    COALESCE(pl.first_name, lp.first_name) AS p_first_name,
                    COALESCE(pl.last_name, lp.last_name) AS p_last_name
             FROM medical_records mr
             LEFT JOIN patients_lookup pl ON pl.patient_id = mr.patient_id
             LEFT JOIN patients lp ON lp.id = mr.patient_uuid
             ORDER BY mr.consultation_date DESC`
        );
        records.value = rows.map(mapLocalMedicalRecord);
        totalItems.value = rows.length;
    }
```

et dans `fetchMedicalRecords`, remplacer :

```js
        } catch (err) {
            console.error('Erreur chargement dossiers medicaux:', err);
            records.value = [];
        } finally {
```

par :

```js
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Consultations hors ligne - secours sur la table locale PowerSync:', err);
                await refreshMedicalRecordsLocal();
            } else {
                console.error('Erreur chargement dossiers medicaux:', err);
                records.value = [];
            }
        } finally {
```

- [ ] **Step 7: `medicalRecordStore.js` — création avec `patient_uuid`** — dans `createMedicalRecord`, remplacer :

```js
                `INSERT INTO medical_records (
                    id, patient_id, consultation_date, motif_code, appointment_id,
                    marital_status, severity, bp, temperature, weight, height,
                    medical_history, allergies, symptoms, diagnosis, treatment, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId, data.consultationDate || null, data.motifCode, data.appointmentId || null,
```

par :

```js
                `INSERT INTO medical_records (
                    id, patient_id, patient_uuid, consultation_date, motif_code, appointment_id,
                    marital_status, severity, bp, temperature, weight, height,
                    medical_history, allergies, symptoms, diagnosis, treatment, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId || null, data.patientUuid || null, data.consultationDate || null, data.motifCode, data.appointmentId || null,
```

(le reste inchangé).

- [ ] **Step 8: `medicalRecordStore.js` — garde d'existence sur la modification** — dans `updateMedicalRecord`, branche medecin/nurse, insérer AVANT le `db.execute('UPDATE medical_records ...')` :

```js
            const existing = await db.getOptional(
                'SELECT id FROM medical_records WHERE id = ? OR server_id = ?',
                [String(recordId), recordId]
            );
            if (!existing) {
                throw new Error('Consultation introuvable localement - modification impossible hors ligne.');
            }
```

- [ ] **Step 9: `PrescriptionsList.vue`** — clé, boutons, identifiant :

Remplacer `:key="presc.prescription_id"` par `:key="presc.prescription_id || presc.local_id"`.

Remplacer le bouton modifier :

```html
                  <button
                    @click="openEditModal(presc)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
                  >
```

par :

```html
                  <button
                    @click="openEditModal(presc)"
                    :disabled="!presc.prescription_id"
                    :title="presc.prescription_id ? '' : 'En attente de synchronisation'"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
```

et le bouton supprimer :

```html
                  <button
                    @click="handleDelete(presc)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition"
                  >
```

par :

```html
                  <button
                    @click="handleDelete(presc)"
                    :disabled="!presc.prescription_id"
                    :title="presc.prescription_id ? '' : 'En attente de synchronisation'"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
```

- [ ] **Step 10: `MedicalRecordsList.vue`** — remplacer `:key="rec.record_id"` par `:key="rec.record_id || rec.local_id"`.

Le bouton **modifier** reste actif (une consultation non synchronisée se modifie localement : `updateMedicalRecord` cherche `WHERE id = ? OR server_id = ?`). Remplacer le bouton **supprimer** (suppression = HTTP seulement) :

```html
                  <button
                    @click="handleDelete(rec)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition"
                  >
```

par :

```html
                  <button
                    @click="handleDelete(rec)"
                    :disabled="!rec.record_id"
                    :title="rec.record_id ? '' : 'En attente de synchronisation'"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
```

Dans `handleSave`, remplacer :

```js
      await medicalRecordStore.updateMedicalRecord(editingRecord.value.record_id, data);
```

par :

```js
      await medicalRecordStore.updateMedicalRecord(editingRecord.value.record_id ?? editingRecord.value.local_id, data);
```

- [ ] **Step 11: Build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 8: Création de patient hors ligne, liste et fiche patient par uuid

**Files:**
- Modify: `ah2-admin-web/src/stores/patientStore.js`
- Modify: `ah2-admin-web/src/views/modules/patients/PatientList.vue` (`handleSave`, ~lignes 282-297)
- Modify: `ah2-admin-web/src/stores/patientDossierStore.js` (`loadDossierFromLocalDb`, `refreshMedicalHistoryLocal`, `refreshPrescriptionHistoryLocal`, ~lignes 47-129)

**Interfaces:**
- Consumes: colonnes locales `patients.*` (Tâche 4) ; `patient_uuid` sur consultations/prescriptions (Tâche 7).
- Produces: `addPatient(formData)` retourne `{ localUuid }` pour medecin/nurse/secretaire (ligne locale `patients`, id = uuid, `server_id` null) ; liste patients avec patients en attente (code "Code en attente") en ligne comme hors ligne ; `patientSummary.patient_uuid` pour un patient créé hors ligne ; fiche accessible par `/medical/patients/<uuid>`.

- [ ] **Step 1: Snapshot** des 3 fichiers.

- [ ] **Step 2: `patientStore.js` — imports** — ajouter après `import api from '@/services/api';` :

```js
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';
```

- [ ] **Step 3: `patientStore.js` — patients en attente et secours local** — ajouter, juste avant `// 1. Récupérer les patients (Liste paginée)` :

```js
    const LOCAL_ROLES = ['medecin', 'nurse', 'secretaire'];

    function mapPendingPatient(p) {
        return {
            id: p.id,
            code: 'Code en attente',
            firstName: p.first_name,
            lastName: p.last_name,
            admissionDate: p.birth_date,
            phone: p.contact_phone,
            type: 'AUTRE',
            pending: true,
            flags: { is_clinical: false, is_toxicology: false, is_spiritual: false },
        };
    }

    // Patients crees localement, pas encore confirmes par le serveur
    // (server_id nul) - affiches en tete de liste, en ligne comme hors
    // ligne, sinon un patient tout juste cree n'apparait nulle part tant
    // que l'envoi n'est pas termine.
    async function pendingLocalPatients() {
        const authStore = useAuthStore();
        if (!authStore.hasRole(LOCAL_ROLES)) return [];
        const rows = await db.getAll(
            'SELECT * FROM patients WHERE server_id IS NULL ORDER BY last_name'
        );
        return rows.map(mapPendingPatient);
    }

    // Secours hors ligne : patients_lookup (memes patients que GET /patients/
    // en ligne pour ces roles), filtre de recherche applique localement. Le
    // filtre par onglet (CLINIQUE/TOXICO/SPIRITUEL) n'est pas applicable :
    // patients_lookup ne porte pas les indicateurs de domaine.
    async function localPatientList() {
        const search = (filters.value.search || '').trim();
        const like = `%${search}%`;
        const rows = search
            ? await db.getAll(
                `SELECT * FROM patients_lookup
                 WHERE code_patient LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                 ORDER BY last_name LIMIT 200`,
                [like, like, like]
            )
            : await db.getAll('SELECT * FROM patients_lookup ORDER BY last_name LIMIT 200');
        return rows.map((p) => ({
            id: p.patient_id,
            code: p.code_patient,
            firstName: p.first_name,
            lastName: p.last_name,
            admissionDate: null,
            phone: p.contact_phone,
            type: 'AUTRE',
            flags: { is_clinical: false, is_toxicology: false, is_spiritual: false },
        }));
    }
```

- [ ] **Step 4: `patientStore.js` — `fetchPatients`** — remplacer :

```js
            patientData.value.data = mappedList;
```

par :

```js
            patientData.value.data = [...(await pendingLocalPatients()), ...mappedList];
```

et remplacer le bloc `catch` de `fetchPatients` :

```js
        } catch (err) {
            console.error("Erreur fetchPatients:", err);
            error.value = "Erreur de connexion au serveur.";
            patientData.value.data = [];
            patientData.value.total = 0;
        } finally {
```

par :

```js
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(LOCAL_ROLES)) {
                console.warn('Patients hors ligne - secours sur les tables locales PowerSync:', err);
                const list = [...(await pendingLocalPatients()), ...(await localPatientList())];
                patientData.value.data = list;
                patientData.value.total = list.length;
                patientData.value.total_pages = 1;
            } else {
                console.error("Erreur fetchPatients:", err);
                error.value = "Erreur de connexion au serveur.";
                patientData.value.data = [];
                patientData.value.total = 0;
            }
        } finally {
```

- [ ] **Step 5: `patientStore.js` — `addPatient`** — remplacer :

```js
            await api.post('/patients/', payload);

            // Rafraîchir la liste ET les compteurs après un ajout
            await Promise.all([
                fetchPatients(),
                fetchCounts()
            ]);
```

par :

```js
            // Ecriture locale pour medecin/nurse/secretaire, en ligne comme
            // hors ligne (connecteur : patients:PUT). Creation neutre en
            // domaine, comme en ligne : les indicateurs clinique/spirituel
            // sont calcules cote serveur a partir des dossiers (chantier 6).
            const authStore = useAuthStore();
            if (authStore.hasRole(LOCAL_ROLES)) {
                const uuid = crypto.randomUUID();
                await db.execute(
                    `INSERT INTO patients (
                        id, first_name, last_name, birth_date, gender, national_id,
                        contact_phone, assurance, residence, father_name, mother_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                    [
                        uuid, payload.first_name, payload.last_name, payload.birth_date,
                        payload.gender || null, payload.national_id || null,
                        payload.contact_phone || null, payload.assurance || null,
                        payload.residence || null, payload.father_name || null,
                        payload.mother_name || null,
                    ]
                );
                await fetchPatients();
                return { localUuid: uuid };
            }

            await api.post('/patients/', payload);

            // Rafraîchir la liste ET les compteurs après un ajout
            await Promise.all([
                fetchPatients(),
                fetchCounts()
            ]);
```

- [ ] **Step 6: `PatientList.vue` — ouvrir la fiche après création locale** — remplacer :

```js
        } else {
            await patientStore.addPatient(payload);
        }
        closeModal();
```

par :

```js
        } else {
            const created = await patientStore.addPatient(payload);
            closeModal();
            // medecin/nurse : on enchaine directement sur la fiche du patient
            // cree (consultation/prescription possibles hors ligne, identifie
            // par son uuid tant qu'il n'a pas de code). Secretaire : pas de
            // fiche (disableDetailLink), il reste visible dans la liste.
            if (created?.localUuid && !props.disableDetailLink) {
                router.push(`${route.path}/${created.localUuid}`);
            }
            return;
        }
        closeModal();
```

Vérifier que les lignes `pending` restent cliquables : `viewPatientDossier(patient.id)` reçoit l'uuid (aucune autre modification du template nécessaire).

- [ ] **Step 7: `patientDossierStore.js` — fiche par uuid** — ajouter en tête de la fonction store (avant `loadDossierFromLocalDb`) :

```js
    // L'identifiant de route est soit un patient_id serveur ("51"), soit
    // l'uuid local d'un patient cree hors ligne. Les colonnes entieres des
    // vues PowerSync ne correspondent jamais a une chaine : le patient_id
    // est lie en Number(), l'uuid en texte.
    function patientKeys(patientId) {
        const asNumber = Number(patientId);
        return {
            serverId: Number.isInteger(asNumber) ? asNumber : -1,
            localId: String(patientId),
        };
    }
```

Remplacer dans `loadDossierFromLocalDb` :

```js
        const rows = await db.getAll(
            'SELECT * FROM patients WHERE server_id = ?',
            [patientId]
        );
        const p = rows[0];

        if (p) {
            patientSummary.value = {
                patient_id: p.server_id,
```

par :

```js
        const { serverId, localId } = patientKeys(patientId);
        let p = await db.getOptional(
            'SELECT * FROM patients WHERE server_id = ? OR id = ?',
            [serverId, localId]
        );
        if (!p) {
            // Patient sans aucun dossier medical (donc absent de
            // clinical_patients) mais connu de patients_lookup : identite
            // seule, suffisante pour lui creer sa premiere consultation.
            const lookup = await db.getOptional(
                'SELECT patient_id, code_patient, first_name, last_name, contact_phone FROM patients_lookup WHERE patient_id = ?',
                [serverId]
            );
            if (lookup) {
                p = { ...lookup, server_id: lookup.patient_id, id: null };
            }
        }

        if (p) {
            patientSummary.value = {
                patient_id: p.server_id,
                patient_uuid: p.server_id ? null : p.id,
```

(le reste de l'objet `patientSummary` inchangé ; `code: p.code_patient` vaut null pour un patient créé hors ligne — remplacer `code: p.code_patient,` par `code: p.code_patient || 'Code en attente',`).

Remplacer dans ce même `loadDossierFromLocalDb` la requête labo :

```js
            'SELECT * FROM lab_results WHERE patient_id = ? ORDER BY test_date DESC',
            [Number(patientId)]
```

par :

```js
            'SELECT * FROM lab_results WHERE patient_id = ? ORDER BY test_date DESC',
            [serverId]
```

Remplacer `refreshMedicalHistoryLocal` et `refreshPrescriptionHistoryLocal` par :

```js
    async function refreshMedicalHistoryLocal(patientId) {
        const { serverId, localId } = patientKeys(patientId);
        medicalHistory.value = await db.getAll(
            'SELECT * FROM medical_records WHERE patient_id = ? OR patient_uuid = ? ORDER BY consultation_date DESC',
            [serverId, localId]
        );
    }

    async function refreshPrescriptionHistoryLocal(patientId) {
        const { serverId, localId } = patientKeys(patientId);
        const rows = await db.getAll(
            'SELECT * FROM prescriptions WHERE patient_id = ? OR patient_uuid = ? ORDER BY start_date DESC',
            [serverId, localId]
        );
        prescriptionHistory.value = rows.map((r) => {
            let exams = [];
            try { exams = r.lab_exams_list ? JSON.parse(r.lab_exams_list) : []; } catch { exams = []; }
            return { ...r, prescription_id: r.server_id, is_lab_order: !!r.is_lab_order, lab_exams_list: Array.isArray(exams) ? exams : [] };
        });
    }
```

Dans `fetchDossierComplete`, remplacer :

```js
        isLoading.value = true;
        error.value = null;

        try {
            const { data } = await api.get(`/patients/${patientId}/dossier`);
```

par :

```js
        isLoading.value = true;
        error.value = null;

        // Identifiant non entier = uuid d'un patient cree localement : le
        // serveur ne le connait pas (ou pas encore). Comme l'ecriture est
        // toujours locale, c'est aussi le cas EN LIGNE juste apres la
        // creation (redirection automatique vers la fiche) - lecture locale
        // directe, jamais un GET /patients/<uuid>/dossier voue a l'echec.
        if (!Number.isInteger(Number(patientId))) {
            await loadDossierFromLocalDb(patientId);
            isLoading.value = false;
            return;
        }

        try {
            const { data } = await api.get(`/patients/${patientId}/dossier`);
```

Ne PAS toucher `refreshVitalsSummaryLocal` : il ne lit aucune table locale (appel HTTP best-effort, erreur simplement journalisée), il est déjà sans risque pour un identifiant uuid.

- [ ] **Step 8: Build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 9: Connecteur — patients, modification de prescription, `patient_uuid`, quarantaine

**Files:**
- Create: `ah2-admin-web/src/powersync-client/syncQuarantine.js`
- Modify: `ah2-admin-web/src/powersync-client/DossierConnector.js`
- Modify: `ah2-admin-web/src/services/MedicalRecordGateway.js` (`createMedicalRecord`)
- Modify: `ah2-admin-web/src/services/PrescriptionGateway.js` (`createPrescription`)

**Interfaces:**
- Consumes: table `sync_quarantine` (Tâche 4) ; colonnes locales `patients.*`, `patient_uuid` (Tâches 4/7/8) ; `POST /patients` avec `uuid` (Tâche 2) ; `patient_uuid` côté backend (Tâche 3).
- Produces: `isPatientQuarantined(database, patientUuid): Promise<boolean>`, `quarantine(database, { kind, localId, patientUuid, payload, error })`, `listQuarantine()`, `reattachToExistingPatient(patientUuid, existingPatientId)` (consommés par la Tâche 10).

- [ ] **Step 1: Snapshot** des 3 fichiers modifiés.

- [ ] **Step 2: Créer `syncQuarantine.js`**

```js
import { db } from '@/powersync-client/client';

// Quarantaine locale (table localOnly sync_quarantine, jamais synchronisee
// donc jamais purgee) : un patient refuse definitivement a l'envoi (doublon
// national_id, 409) y est conserve avec ses consultations/prescriptions
// hors ligne, au lieu que celles-ci partent vers un patient inexistant puis
// disparaissent de la file. Resolution manuelle : reattachToExistingPatient.

export async function isPatientQuarantined(database, patientUuid) {
  if (!patientUuid) return false;
  const row = await database.getOptional(
    "SELECT id FROM sync_quarantine WHERE kind = 'patient' AND local_id = ?",
    [patientUuid]
  );
  return !!row;
}

export async function quarantine(database, { kind, localId, patientUuid, payload, error }) {
  await database.execute(
    `INSERT INTO sync_quarantine (id, kind, local_id, patient_uuid, payload, error, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [
      crypto.randomUUID(), kind, localId, patientUuid || null,
      JSON.stringify(payload || {}), error || null, new Date().toISOString(),
    ]
  );
}

export async function listQuarantine() {
  return db.getAll('SELECT * FROM sync_quarantine ORDER BY created_at');
}

// Reinjecte les consultations/prescriptions retenues d'un patient refuse avec
// l'id d'un patient existant : nouvelles lignes locales (nouveaux uuid, les
// anciens ont deja ete retires de la file d'envoi) qui repartent dans la file
// normalement, prescriptions rechainees vers la nouvelle consultation. Puis
// suppression de la quarantaine et des lignes locales abandonnees.
export async function reattachToExistingPatient(patientUuid, existingPatientId) {
  const children = await db.getAll(
    `SELECT * FROM sync_quarantine
     WHERE patient_uuid = ? AND kind IN ('medical_record', 'prescription')
     ORDER BY created_at`,
    [patientUuid]
  );

  await db.writeTransaction(async (tx) => {
    const newRecordIds = {};

    for (const c of children.filter((x) => x.kind === 'medical_record')) {
      const p = JSON.parse(c.payload);
      const newId = crypto.randomUUID();
      newRecordIds[c.local_id] = newId;
      await tx.execute('DELETE FROM medical_records WHERE id = ?', [c.local_id]);
      await tx.execute(
        `INSERT INTO medical_records (
            id, patient_id, consultation_date, motif_code, appointment_id,
            marital_status, severity, bp, temperature, weight, height,
            medical_history, allergies, symptoms, diagnosis, treatment, notes
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          newId, existingPatientId, p.consultation_date ?? null, p.motif_code ?? null, p.appointment_id ?? null,
          p.marital_status ?? null, p.severity ?? null, p.bp ?? null,
          p.temperature ?? null, p.weight ?? null, p.height ?? null,
          p.medical_history ?? null, p.allergies ?? null, p.symptoms ?? null,
          p.diagnosis ?? null, p.treatment ?? null, p.notes ?? null,
        ]
      );
    }

    for (const c of children.filter((x) => x.kind === 'prescription')) {
      const p = JSON.parse(c.payload);
      const linkedRecord = p.medical_record_id ? (newRecordIds[p.medical_record_id] || p.medical_record_id) : null;
      await tx.execute('DELETE FROM prescriptions WHERE id = ?', [c.local_id]);
      await tx.execute(
        `INSERT INTO prescriptions (
            id, patient_id, medical_record_id, medication, dosage, frequency,
            duration, start_date, end_date, notes, is_lab_order, lab_exams_list
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          crypto.randomUUID(), existingPatientId, linkedRecord, p.medication ?? null,
          p.dosage ?? null, p.frequency ?? null, p.duration ?? null,
          p.start_date ?? null, p.end_date ?? null, p.notes ?? null,
          p.is_lab_order ? 1 : 0, p.lab_exams_list ?? '[]',
        ]
      );
    }

    await tx.execute('DELETE FROM patients WHERE id = ?', [patientUuid]);
    await tx.execute(
      "DELETE FROM sync_quarantine WHERE patient_uuid = ? OR (kind = 'patient' AND local_id = ?)",
      [patientUuid, patientUuid]
    );
  });
}
```

- [ ] **Step 3: Gateways** — dans `MedicalRecordGateway.createMedicalRecord`, dans l'objet `payload`, remplacer `patient_id: data.patientId,` par :

```js
            patient_id: data.patientId || null,
            patient_uuid: data.patientUuid || null,
```

Dans `PrescriptionGateway.createPrescription`, même remplacement de `patient_id: data.patientId,` (dans `createPrescription` seulement, PAS dans `updatePrescription`).

- [ ] **Step 4: Connecteur — imports** — dans `DossierConnector.js`, remplacer :

```js
import { API_URL } from '@/services/api';
```

par :

```js
import api, { API_URL } from '@/services/api';
import { isPatientQuarantined, quarantine } from '@/powersync-client/syncQuarantine';
```

- [ ] **Step 5: Connecteur — `patients:PUT`** — ajouter ce case juste avant `case 'medical_records:PUT': {` :

```js
          case 'patients:PUT': {
            // Patient cree hors ligne (medecin/nurse/secretaire). Meme appel
            // que patientStore.addPatient en ligne (pas de gateway patient
            // dediee). Rejeu du meme uuid = 200 idempotent cote serveur.
            await api.post('/patients/', {
              first_name: op.opData.first_name,
              last_name: op.opData.last_name,
              birth_date: op.opData.birth_date,
              gender: op.opData.gender || null,
              national_id: op.opData.national_id || null,
              contact_phone: op.opData.contact_phone || null,
              assurance: op.opData.assurance || null,
              residence: op.opData.residence || null,
              father_name: op.opData.father_name || null,
              mother_name: op.opData.mother_name || null,
              uuid: op.id,
            });
            break;
          }
```

- [ ] **Step 6: Connecteur — `medical_records:PUT`** — remplacer le début du case :

```js
          case 'medical_records:PUT': {
            await MedicalRecordGateway.createMedicalRecord({
              patientId: op.opData.patient_id,
```

par :

```js
          case 'medical_records:PUT': {
            // Patient en quarantaine (refuse definitivement) : la consultation
            // est retenue avec lui au lieu d'etre envoyee vers un patient qui
            // n'existe pas cote serveur (elle serait refusee puis perdue).
            if (await isPatientQuarantined(database, op.opData.patient_uuid)) {
              await quarantine(database, {
                kind: 'medical_record',
                localId: op.id,
                patientUuid: op.opData.patient_uuid,
                payload: op.opData,
                error: 'Patient en echec de synchronisation',
              });
              break;
            }
            await MedicalRecordGateway.createMedicalRecord({
              patientId: op.opData.patient_id,
              patientUuid: op.opData.patient_uuid,
```

- [ ] **Step 7: Connecteur — `prescriptions:PUT`** — insérer en tête du case `prescriptions:PUT` (avant `let medicalRecordServerId = null;`) :

```js
            if (await isPatientQuarantined(database, op.opData.patient_uuid)) {
              await quarantine(database, {
                kind: 'prescription',
                localId: op.id,
                patientUuid: op.opData.patient_uuid,
                payload: op.opData,
                error: 'Patient en echec de synchronisation',
              });
              break;
            }
```

et dans l'appel `PrescriptionGateway.createPrescription({...})` de ce case, remplacer `patientId: op.opData.patient_id,` par :

```js
              patientId: op.opData.patient_id,
              patientUuid: op.opData.patient_uuid,
```

- [ ] **Step 8: Connecteur — `prescriptions:PATCH`** — ajouter ce case juste avant `case 'caisse:PUT': {` :

```js
          case 'prescriptions:PATCH': {
            // Modification hors ligne d'une prescription synchronisee (bouton
            // "modifier" desactive tant qu'elle n'a pas de server_id). Relit
            // la ligne locale COMPLETE (pas op.opData, qui peut n'avoir que
            // les colonnes modifiees) - meme motif que appointments:PATCH.
            const currentPresc = await database.getOptional(
              `SELECT server_id, patient_id, medical_record_id, medication, dosage, frequency,
                      duration, start_date, end_date, notes, is_lab_order, lab_exams_list
               FROM prescriptions WHERE id = ?`,
              [op.id]
            );
            if (!currentPresc?.server_id) {
              console.warn(`Prescription ${op.id} : modification d'une creation pas encore confirmee, ignoree pour cet upload.`);
              break;
            }
            let exams = [];
            try { exams = currentPresc.lab_exams_list ? JSON.parse(currentPresc.lab_exams_list) : []; } catch { exams = []; }
            await PrescriptionGateway.updatePrescription(currentPresc.server_id, {
              patientId: currentPresc.patient_id,
              medicalRecordId: currentPresc.medical_record_id,
              isLabOrder: !!currentPresc.is_lab_order,
              medication: currentPresc.medication,
              dosage: currentPresc.dosage,
              frequency: currentPresc.frequency,
              duration: currentPresc.duration,
              startDate: currentPresc.start_date,
              endDate: currentPresc.end_date,
              notes: currentPresc.notes,
              labExamsList: Array.isArray(exams) ? exams : [],
            });
            break;
          }
```

- [ ] **Step 9: Connecteur — commentaire `default`** — remplacer le commentaire du `default:` par :

```js
            // DELETE (toutes tables), PATCH caisse/patients : hors perimetre
            // (ecritures locales purement cosmetiques ou suppressions de
            // lignes abandonnees par la quarantaine) - log defensif.
```

- [ ] **Step 10: Connecteur — quarantaine d'un patient refusé** — dans le `catch`, juste APRÈS le bloc `if (lastOp?.table === 'caisse') { ... }` et AVANT `await transaction.complete();`, ajouter :

```js
        // Patient refuse definitivement (doublon national_id, donnees
        // invalides) : mis en quarantaine locale - ses consultations et
        // prescriptions suivantes y seront retenues (cases ci-dessus) au lieu
        // d'etre envoyees vers un patient inexistant. Protege par son propre
        // try/catch : ne doit jamais faire planter le connecteur.
        if (lastOp?.table === 'patients') {
          try {
            await quarantine(database, {
              kind: 'patient',
              localId: lastOp.id,
              patientUuid: lastOp.id,
              payload: lastOp.opData,
              error: error?.response?.data?.detail || 'Patient refuse par le serveur.',
            });
          } catch (quarantineError) {
            console.error('Impossible de mettre le patient en quarantaine:', quarantineError);
          }
        }
```

- [ ] **Step 11: Build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 10: Écran « Échecs de synchronisation » et entrée de menu

**Files:**
- Create: `ah2-admin-web/src/composables/useSyncQuarantineCount.js`
- Create: `ah2-admin-web/src/views/modules/sync/SyncFailuresView.vue`
- Modify: `ah2-admin-web/src/router/index.js` (enfants `/medical` et `/secretariat`)
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue`, `ah2-admin-web/src/components/layout/SecretaireLayout.vue`
- Modify: `ah2-admin-web/src/i18n.js` (`secretariat.nav`, fr et en)

**Interfaces:**
- Consumes: `listQuarantine()`, `reattachToExistingPatient(patientUuid, existingPatientId)` (Tâche 9).
- Produces: routes `medical-sync-failures` (`/medical/sync-failures`, medecin/nurse) et `secretariat-sync-failures` (`/secretariat/sync-failures`, secretaire) ; entrée de menu visible seulement si la quarantaine contient au moins un patient.

- [ ] **Step 1: Snapshot** des 4 fichiers modifiés.

- [ ] **Step 2: `useSyncQuarantineCount.js`**

```js
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { db } from '@/powersync-client/client';

// Nombre de patients en quarantaine, mis a jour en continu (db.watch) - sert
// a afficher l'entree de menu "Echecs de synchronisation" seulement quand il
// y a quelque chose a resoudre.
export function useSyncQuarantineCount() {
  const count = ref(0);
  const controller = new AbortController();

  onMounted(() => {
    (async () => {
      try {
        for await (const result of db.watch(
          "SELECT COUNT(*) AS n FROM sync_quarantine WHERE kind = 'patient'",
          [],
          { signal: controller.signal }
        )) {
          count.value = result.rows?._array?.[0]?.n ?? 0;
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error('Surveillance de la quarantaine interrompue:', err);
        }
      }
    })();
  });

  onBeforeUnmount(() => controller.abort());

  return count;
}
```

- [ ] **Step 3: `SyncFailuresView.vue`**

```vue
<template>
  <div class="space-y-6 w-full">
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">Échecs de synchronisation</h1>
      <p class="text-sm text-gray-500 mt-1">
        Patients créés hors ligne refusés par le serveur (par exemple un numéro d'identité nationale déjà utilisé).
        Leurs consultations et prescriptions sont conservées ici, jamais envoyées au mauvais patient.
      </p>
    </div>

    <div v-if="isLoading" class="p-10 text-center">
      <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></span>
    </div>

    <div v-else-if="groups.length === 0" class="bg-white p-10 rounded-2xl border border-gray-100 text-center text-gray-500">
      Aucun échec de synchronisation.
    </div>

    <div v-for="g in groups" :key="g.patientUuid" class="bg-white p-6 rounded-2xl shadow-sm border border-red-100 space-y-3">
      <div class="flex flex-wrap justify-between gap-2">
        <div>
          <p class="text-lg font-semibold text-gray-900">{{ g.name }}</p>
          <p class="text-xs text-gray-500">Né(e) le {{ g.birthDate || '—' }} · N° d'identité : {{ g.nationalId || '—' }}</p>
        </div>
        <span class="inline-flex items-center px-2 py-0.5 h-fit rounded text-xs font-medium bg-red-100 text-red-800">
          Échec de synchronisation
        </span>
      </div>
      <p class="text-sm text-red-700">Motif : {{ g.error }}</p>
      <p class="text-sm text-gray-600">
        Données retenues : {{ g.recordCount }} consultation(s), {{ g.prescriptionCount }} prescription(s).
      </p>

      <div class="flex flex-wrap items-end gap-2 pt-2 border-t border-gray-100">
        <div class="flex-1 min-w-[200px]">
          <label :for="`code-${g.patientUuid}`" class="text-xs font-bold text-gray-500 uppercase mb-1 block">
            Code du patient existant (AH2-…)
          </label>
          <input :id="`code-${g.patientUuid}`" v-model="codes[g.patientUuid]" type="text"
                 class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
        </div>
        <button type="button" @click="handleReattach(g)" :disabled="busy[g.patientUuid]"
                class="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 font-medium disabled:opacity-50">
          {{ busy[g.patientUuid] ? 'Rattachement…' : 'Rattacher à ce patient' }}
        </button>
      </div>
      <p v-if="messages[g.patientUuid]" class="text-sm" :class="messages[g.patientUuid].ok ? 'text-emerald-700' : 'text-red-700'">
        {{ messages[g.patientUuid].text }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '@/services/api';
import { listQuarantine, reattachToExistingPatient } from '@/powersync-client/syncQuarantine';

const isLoading = ref(false);
const groups = ref([]);
const codes = reactive({});
const busy = reactive({});
const messages = reactive({});

async function load() {
  isLoading.value = true;
  try {
    const rows = await listQuarantine();
    const patients = rows.filter((r) => r.kind === 'patient');
    groups.value = patients.map((p) => {
      const payload = JSON.parse(p.payload || '{}');
      const children = rows.filter((r) => r.patient_uuid === p.local_id && r.kind !== 'patient');
      return {
        patientUuid: p.local_id,
        name: [payload.first_name, payload.last_name].filter(Boolean).join(' ') || 'Patient sans nom',
        birthDate: payload.birth_date,
        nationalId: payload.national_id,
        error: p.error,
        recordCount: children.filter((c) => c.kind === 'medical_record').length,
        prescriptionCount: children.filter((c) => c.kind === 'prescription').length,
      };
    });
  } finally {
    isLoading.value = false;
  }
}

function normalizeCode(raw) {
  const code = (raw || '').trim().toUpperCase();
  if (!code) return '';
  return code.startsWith('AH2-') ? code : `AH2-${code}`;
}

// Resolution du patient existant par son code : necessite le reseau
// (source de verite serveur, jamais une copie locale pour une decision
// d'identite medicale).
async function handleReattach(g) {
  const code = normalizeCode(codes[g.patientUuid]);
  if (!code) {
    messages[g.patientUuid] = { ok: false, text: 'Saisissez le code du patient existant.' };
    return;
  }
  busy[g.patientUuid] = true;
  messages[g.patientUuid] = null;
  try {
    const res = await api.get('/patients/', { params: { search: code, per_page: 5 } });
    const list = Array.isArray(res.data) ? res.data : (res.data.data || []);
    const match = list.find((p) => p.code_patient === code);
    if (!match) {
      messages[g.patientUuid] = { ok: false, text: `Aucun patient avec le code ${code}.` };
      return;
    }
    await reattachToExistingPatient(g.patientUuid, match.patient_id || match.id);
    messages[g.patientUuid] = { ok: true, text: `Données rattachées à ${match.first_name} ${match.last_name}.` };
    await load();
  } catch (err) {
    messages[g.patientUuid] = {
      ok: false,
      text: err.response ? 'Erreur serveur, réessayez.' : 'Connexion requise pour rattacher un patient.',
    };
  } finally {
    busy[g.patientUuid] = false;
  }
}

onMounted(load);
</script>
```

- [ ] **Step 4: Routes** — dans `router/index.js`, ajouter dans les `children` de `/medical` (après l'entrée `medical-patient-detail`) :

```js
      {
        path: 'sync-failures',
        name: 'medical-sync-failures',
        component: () => import('@/views/modules/sync/SyncFailuresView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
```

et dans les `children` de `/secretariat` (après `secretariat-consultations`) :

```js
      {
        path: 'sync-failures',
        name: 'secretariat-sync-failures',
        component: () => import('@/views/modules/sync/SyncFailuresView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
```

- [ ] **Step 5: i18n** — dans `i18n.js`, dans `fr.secretariat.nav`, ajouter `sync_failures: "Échecs de synchronisation",` ; dans `en.secretariat.nav`, ajouter `sync_failures: "Sync failures",`.

- [ ] **Step 6: Layouts** — dans `MedicalLayout.vue` ET `SecretaireLayout.vue` :

Remplacer `import { ref, onMounted } from 'vue';` par `import { ref, computed, onMounted } from 'vue';`, ajouter `ExclamationTriangleIcon` à la liste de l'import `@heroicons/vue/24/outline` existant, et ajouter l'import :

```js
import { useSyncQuarantineCount } from '@/composables/useSyncQuarantineCount';
```

Ajouter à la fin du tableau `menuItems` (chemin `/medical/sync-failures` dans `MedicalLayout.vue`, `/secretariat/sync-failures` dans `SecretaireLayout.vue`) :

```js
  {
    path: '/medical/sync-failures',
    labelKey: 'secretariat.nav.sync_failures',
    icon: ExclamationTriangleIcon,
    onlyWhenQuarantine: true,
  },
```

Ajouter après la déclaration de `menuItems` :

```js
const quarantineCount = useSyncQuarantineCount();
const visibleMenuItems = computed(() =>
  menuItems.filter((item) => !item.onlyWhenQuarantine || quarantineCount.value > 0)
);
```

Dans le template, remplacer `v-for="item in menuItems"` par `v-for="item in visibleMenuItems"`, et remplacer :

```html
          <span v-if="isSidebarOpen" class="whitespace-nowrap transition-opacity duration-200">
            {{ t(item.labelKey) }}
          </span>
```

par :

```html
          <span v-if="isSidebarOpen" class="whitespace-nowrap transition-opacity duration-200">
            {{ t(item.labelKey) }}
          </span>
          <span v-if="item.onlyWhenQuarantine && isSidebarOpen"
                class="ml-auto inline-flex items-center justify-center min-w-[1.25rem] px-1.5 rounded-full text-xs font-bold bg-red-600 text-white">
            {{ quarantineCount }}
          </span>
```

(bloc identique dans les deux layouts, lignes ~55-57.)

- [ ] **Step 7: Build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 11: Vérification finale (contrôleur)

Pas de dispatch — à la charge du contrôleur.

- [ ] `python -m pytest tests/ -q` : aucun nouvel échec hors des 9 pré-existants documentés.
- [ ] Build frontend production vert.
- [ ] Diagnostic PowerSync (`/api/admin/v1/diagnostics`) : `errors: []`, tables `examens`/`motif_translations` répliquées.
- [ ] `docker ps` : les 2 conteneurs `powersync-*` stables et `(healthy)` sur plusieurs relevés espacés.
- [ ] Demander à l'utilisateur le protocole manuel de la spec (section Tests, points 1-5), en **vraie coupure** (arrêter uvicorn, jamais le toggle DevTools), avec en plus :
  - après création hors ligne d'un patient puis synchronisation, vérifier qu'il n'apparaît pas en double dans la liste (ligne locale « Code en attente » disparue une fois confirmée) — comportement de réconciliation PowerSync à confirmer empiriquement ;
  - demande d'examen créée hors ligne visible dans la liste des prescriptions sans plantage.
