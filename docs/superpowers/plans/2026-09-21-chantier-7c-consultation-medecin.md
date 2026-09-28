# Chantier 7c — Flux de consultation du médecin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le médecin (et l'infirmier) peut démarrer une consultation depuis un rendez-vous, voir le rendez-vous se terminer automatiquement à l'enregistrement du dossier médical, et enchaîner sur une prescription liée — un flux complet qui n'existe nulle part aujourd'hui dans l'application web.

**Architecture:** Une colonne `appointment_id` (nullable) relie un dossier médical au rendez-vous dont il découle. `MedicalRecordModal.vue` et `PrescriptionModal.vue` gagnent chacune un mode de pré-remplissage « création sans ressaisie » (distinct de leur mode édition existant), pilotées par `PatientDetailView.vue` qui orchestre l'enchaînement complet (créer le dossier → compléter le rendez-vous lié → proposer une prescription liée). La liste des rendez-vous gagne deux actions de navigation vers ce flux.

**Tech Stack:** FastAPI + SQLAlchemy + PostgreSQL (procédure stockée modifiée via migration Alembic), Vue 3 Composition API + Pinia, pytest avec fixtures `db_session`/`api_client` (intégration réelle contre PostgreSQL local `AH2`).

**Spec:** `docs/superpowers/specs/2026-09-21-chantier-7c-consultation-medecin-design.md`

## Global Constraints

- Migration Alembic requise (colonne + procédure stockée modifiée) — écriture réelle en base : confirmation explicite de l'utilisateur requise avant application, comme pour toute migration dans ce projet.
- Aucune garde de rôle existante n'est modifiée. Le routeur `/appointments` (aujourd'hui sans `role_required`) reste tel quel — écart réel déjà identifié, traité par le nettoyage `L4b-e` planifié juste après ce sous-projet, pas par ce plan.
- Aucun travail hors ligne — les dossiers médicaux et prescriptions sont explicitement exclus du pilote PowerSync (seuls `appointments`, `patients_lookup`, `doctors_lookup` sont synchronisés). Toute écriture de ce plan passe par le réseau (REST direct), jamais par PowerSync.
- `usePatientLookup.js` (composable partagé) n'est PAS retouché par ce plan — `PrescriptionModal.vue` garde sa propre implémentation de recherche patient, distincte de celle de `MedicalRecordModal.vue` (qui utilise déjà le composable). Les deux modales gagnent leur pré-remplissage indépendamment, chacune dans son propre style existant.
- Aucun commit git à aucune étape sans accord explicite et frais de l'utilisateur à ce moment précis.

---

### Task 1: Backend — colonne `appointment_id` sur `medical_records`

**Files:**
- Create: `alembic/versions/005_medical_records_appointment_id.py`
- Modify: `models/medical_record.py`
- Modify: `repositories/medical_repo.py:113-151` (méthode `create`)
- Modify: `api_backend/backend_app/routes/medical_records/schemas.py:8-24` (`MedicalRecordBase`)
- Test: `tests/test_medical_records_appointment_link.py` (nouveau fichier)

**Interfaces:**
- Consumes : rien de nouveau (colonnes/tables existantes).
- Produces (consommé par les Tâches 2 et 4) : `MedicalRecordCreate`/`MedicalRecordResponse` portent désormais un champ `appointment_id: Optional[int] = None` ; `POST /medical_records/` accepte et renvoie ce champ sans changement de signature d'endpoint (la donnée traverse déjà `data.model_dump()` → `medical_ctrl.create_record(data)` → `repo.create(data)` sans transformation intermédiaire — vérifié dans le code réel).

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_medical_records_appointment_link.py` :

```python
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_create_medical_record_with_appointment_id(db_session, api_client):
    """Chantier 7c : un dossier medical peut etre cree avec un
    appointment_id, persiste et renvoye par l'API."""
    medecin = create_test_user(db_session, "test_7c_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Consultation")
    db_session.flush()

    from models.appointment import Appointment
    from datetime import date, time
    appt = Appointment(
        patient_id=patient_id, doctor_id=medecin.user_id,
        appointment_date=date.today(), appointment_time=time(9, 0), status="pending",
    )
    db_session.add(appt)
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_7c_medecin", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
        "appointment_id": appt.id,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["appointment_id"] == appt.id


def test_create_medical_record_without_appointment_id_stays_null(db_session, api_client):
    """Non-regression : une consultation spontanee (bouton "Nouvelle
    consultation" du dossier patient, sans RDV d'origine) continue de
    fonctionner, appointment_id reste NULL."""
    medecin = create_test_user(db_session, "test_7c_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Spontanee")
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_7c_medecin2", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["appointment_id"] is None
```

- [ ] **Step 2: Lancer les tests, vérifier l'échec**

Run: `pytest tests/test_medical_records_appointment_link.py -v`
Expected: FAIL — `appointment_id` non reconnu par `MedicalRecordCreate` (422, champ non déclaré rejeté ou silencieusement absent de la réponse selon la validation Pydantic — dans les deux cas le test échoue sur `resp.json()["appointment_id"]`).

- [ ] **Step 3: Ajouter la colonne au modèle SQLAlchemy**

Dans `models/medical_record.py`, ajouter l'import et la colonne :

```python
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey
```

(déjà présent — `ForeignKey` déjà importé, aucun nouvel import nécessaire)

Ajouter la colonne juste après `motif_code` (ligne 27) :

```python
    appointment_id     = Column(Integer, ForeignKey('appointments.id', ondelete='SET NULL'), nullable=True)
```

Ajouter la relation juste après `patient` (ligne 37) :

```python
    appointment        = relationship("Appointment")
```

- [ ] **Step 4: Ajouter le champ au schéma Pydantic**

Dans `api_backend/backend_app/routes/medical_records/schemas.py`, `MedicalRecordBase` (ligne 8-24), ajouter juste après `motif_code` :

```python
    appointment_id: Optional[int] = None
```

(`MedicalRecordCreate` et `MedicalRecordResponse` héritent toutes deux de `MedicalRecordBase` — aucune modification supplémentaire nécessaire dans ce fichier)

- [ ] **Step 5: Écrire la migration Alembic**

Créer `alembic/versions/005_medical_records_appointment_id.py` :

```python
"""add medical_records.appointment_id (chantier 7c)

Revision ID: 005_medical_records_appointment_id
Revises: 004_appointments_uuid_unique
Create Date: 2026-09-21 00:00:00.000000

Chantier 7c (docs/superpowers/SUIVI-AVANCEMENT.md, registre L3c) : relie un
dossier medical au rendez-vous dont il decoule, quand il en vient un.
Nullable - une consultation spontanee (bouton "Nouvelle consultation" du
dossier patient, sans RDV d'origine) reste possible, appointment_id reste
NULL dans ce cas. ON DELETE SET NULL (pas CASCADE) : si un rendez-vous est
un jour supprime, le dossier medical qui en decoule doit survivre.

La procedure stockee public.create_medical_record est etendue avec un
nouveau parametre p_appointment_id, ajoute en dernier avec DEFAULT NULL -
tout appelant existant qui ne le fournit pas continue de fonctionner a
l'identique (aucun appelant PL/pgSQL direct connu en dehors de
repositories/medical_repo.py::create, deja mis a jour dans ce meme plan).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_medical_records_appointment_id'
down_revision: Union[str, Sequence[str], None] = '004_appointments_uuid_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE public.medical_records
            ADD COLUMN IF NOT EXISTS appointment_id integer
            REFERENCES public.appointments(id) ON DELETE SET NULL;
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


def downgrade() -> None:
    """Restaure la procedure a sa signature d'origine (sans
    p_appointment_id), puis retire la colonne. Aucune perte de donnees
    autre que le lien RDV<->dossier lui-meme, jamais la seule copie d'une
    information (le RDV et le dossier restent intacts independamment)."""
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
            IN p_last_updated_by_name character varying DEFAULT NULL::character varying
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name
            );
        END;
        $$;
    """)
    op.execute("ALTER TABLE public.medical_records DROP COLUMN IF EXISTS appointment_id;")
```

- [ ] **Step 6: Appliquer la migration — confirmation explicite requise**

Cette étape n'est **pas** exécutée par le sous-agent implémenteur. Le contrôleur SDD (la session qui pilote ce plan) demande confirmation explicite à l'utilisateur, puis exécute lui-même, contre la base `AH2` locale :

```bash
alembic upgrade head
```

Vérification après exécution : `\d medical_records` (ou requête `information_schema.columns`) doit montrer la colonne `appointment_id`, et `\df+ public.create_medical_record` doit montrer la nouvelle signature à 19 paramètres.

- [ ] **Step 7: Mettre à jour le dépôt pour passer le nouveau paramètre**

Dans `repositories/medical_repo.py`, remplacer le bloc SQL de `create` (lignes 121-143) :

```python
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
                :appointment_id
            )
        """)
```

Et juste avant l'appel (après les `data.setdefault(...)` existants, ligne 118), ajouter :

```python
        data.setdefault('appointment_id', None)
```

- [ ] **Step 8: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_medical_records_appointment_link.py -v`
Expected: PASS (2 tests)

- [ ] **Step 9: Vérifier la non-régression du module dossiers médicaux**

Run: `pytest tests/ -k medical_record -v`
Expected: PASS, aucune régression

---

### Task 2: `MedicalRecordModal.vue` — pré-remplissage sans ressaisie

**Files:**
- Modify: `ah2-admin-web/src/components/medical-records/MedicalRecordModal.vue`

**Interfaces:**
- Consumes : `usePatientLookup()`'s `setFromExisting({patientId, code, firstName, lastName})` (déjà existant, déjà utilisé par le mode édition de ce même fichier).
- Produces (consommé par la Tâche 4) : nouvelles props `prefilledPatient: {patientId, code, firstName, lastName} | null` et `appointmentId: number | null`. Le payload émis par `save` gagne une clé `appointmentId` (miroir de la prop, transmise telle quelle — `null` si consultation spontanée).

- [ ] **Step 1: Ajouter les nouvelles props**

Dans `ah2-admin-web/src/components/medical-records/MedicalRecordModal.vue`, remplacer le bloc `defineProps` (lignes 142-147) :

```javascript
const props = defineProps({
  record: {
    type: Object,
    default: null,
  },
  prefilledPatient: {
    type: Object,
    default: null,
  },
  appointmentId: {
    type: Number,
    default: null,
  },
});
```

- [ ] **Step 2: Pré-remplir depuis `prefilledPatient` quand fourni**

Dans le bloc `onMounted` (lignes 193-221), ajouter juste après le bloc `if (props.record) { ... }` existant (avant la fermeture de `onMounted`) :

```javascript
  if (!props.record && props.prefilledPatient) {
    setFromExisting(props.prefilledPatient);
  }
```

- [ ] **Step 3: Verrouiller le champ code patient aussi en mode pré-rempli**

Remplacer la ligne `:readonly="isEdit"` (ligne 23) et la classe conditionnelle associée (lignes 24-27) :

```html
            :readonly="isEdit || !!prefilledPatient"
            :class="[
              'block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm',
              (isEdit || !!prefilledPatient) ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''
            ]"
```

- [ ] **Step 4: Transmettre `appointmentId` dans le payload émis**

Dans `handleSubmit` (lignes 233-270), ajouter `appointmentId: props.appointmentId,` au dernier objet passé à `emit('save', {...})` (juste après `patientId: patientId.value,`, ligne 254) :

```javascript
  emit('save', {
    patientId: patientId.value,
    appointmentId: props.appointmentId,
    consultationDate: form.consultationDate,
```

- [ ] **Step 5: Vérifier la compilation**

Run (depuis `ah2-admin-web/`): `npx vite build`
Expected: succès, aucune erreur (nouvelles props non encore consommées par un appelant — Task 4 le fait — donc rien ne doit casser en aval).

---

### Task 3: `PrescriptionModal.vue` — pré-remplissage sans ressaisie, lié à un dossier médical

**Files:**
- Modify: `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue`

**Interfaces:**
- Consumes : rien de nouveau (ce fichier a sa propre implémentation de recherche patient, distincte du composable partagé — non touchée).
- Produces (consommé par la Tâche 4) : nouvelles props `prefilledPatient: {patientId, code, firstName, lastName} | null` et `prefilledMedicalRecordId: number | null`.

- [ ] **Step 1: Ajouter les nouvelles props**

Dans `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue`, remplacer le bloc `defineProps` (lignes 169-174) :

```javascript
const props = defineProps({
  prescription: {
    type: Object,
    default: null,
  },
  prefilledPatient: {
    type: Object,
    default: null,
  },
  prefilledMedicalRecordId: {
    type: Number,
    default: null,
  },
});
```

- [ ] **Step 2: Pré-remplir depuis les nouvelles props quand fournies**

Dans le bloc `onMounted` (lignes 249-271), ajouter juste après le bloc `if (props.prescription) { ... }` existant :

```javascript
  if (!props.prescription && props.prefilledPatient) {
    const p = props.prefilledPatient;
    patientId.value = p.patientId || null;
    patientCode.value = p.code || '';
    patientName.value = [p.firstName, p.lastName].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  }

  if (!props.prescription && props.prefilledMedicalRecordId) {
    medicalRecordId.value = props.prefilledMedicalRecordId;
  }
```

- [ ] **Step 3: Verrouiller le champ code patient en mode pré-rempli**

Remplacer l'`<input>` du code patient (lignes 18-25) :

```html
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            :readonly="!!prefilledPatient"
            :class="[
              'block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm',
              prefilledPatient ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''
            ]"
            placeholder="Ex: AH2-000818AQ"
          />
```

- [ ] **Step 4: Vérifier la compilation**

Run (depuis `ah2-admin-web/`): `npx vite build`
Expected: succès, aucune erreur.

---

### Task 4: `PatientDetailView.vue` — orchestration du flux complet

**Files:**
- Modify: `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue`
- Modify: `ah2-admin-web/src/stores/medicalRecordStore.js:59-63` (`createMedicalRecord`)
- Modify: `ah2-admin-web/src/services/MedicalRecordGateway.js:38-53` (`createMedicalRecord`)

**Interfaces:**
- Consumes : `MedicalRecordModal` (Tâche 2, props `prefilledPatient`/`appointmentId`, emit `save` avec `appointmentId` inclus), `PrescriptionModal` (Tâche 3, props `prefilledPatient`/`prefilledMedicalRecordId`), `appointmentStore.completeAppointment(appointmentId)` (déjà existant, déjà utilisé par `AppointmentsList.vue`), `dossierStore.refreshMedicalHistory(patientId)` (déjà existant).
- Produces (consommé par la Tâche 5) : la route `/medical/patients/{id}` (et les routes équivalentes montant ce même composant) accepte désormais un paramètre de requête `?appointmentId=X` qui déclenche l'auto-ouverture de la modale de consultation pré-remplie et pré-liée.

- [ ] **Step 1: `medicalRecordStore.createMedicalRecord` renvoie l'enregistrement créé**

Dans `ah2-admin-web/src/stores/medicalRecordStore.js`, remplacer `createMedicalRecord` (lignes 59-63) :

```javascript
    async function createMedicalRecord(data) {
        const res = await MedicalRecordGateway.createMedicalRecord(data);
        filters.value.page = 1;
        await fetchMedicalRecords();
        return res.data;
    }
```

- [ ] **Step 2: `MedicalRecordGateway.createMedicalRecord` transmet `appointment_id`**

Dans `ah2-admin-web/src/services/MedicalRecordGateway.js`, dans `createMedicalRecord` (lignes 38-53), ajouter au `payload` juste après `motif_code: data.motifCode,` :

```javascript
            appointment_id: data.appointmentId || null,
```

- [ ] **Step 3: Câbler le bouton « Nouvelle consultation » et l'ouverture automatique**

Dans `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue`, remplacer le bouton statique (lignes 55-57) :

```html
                        <button @click="openConsultationModal()" class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition">
                            {{ t('medical.actions.new_consultation') }}
                        </button>
```

Ajouter le montage de la modale et de la bannière de proposition, juste avant la fermeture du `<div v-else-if="dossierStore.patientSummary" ...>` racine (après le `</div>` qui ferme le bloc `bg-white rounded-2xl shadow-xl ...`, avant la ligne 114) :

```html
        <div v-if="prescriptionOffer.visible" class="mx-1 bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center justify-between">
            <p class="text-sm text-emerald-800">Ajouter une prescription pour cette consultation ?</p>
            <div class="flex gap-2">
                <button @click="declinePrescriptionOffer" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-emerald-300 text-emerald-700 hover:bg-emerald-100 transition">
                    Non
                </button>
                <button @click="acceptPrescriptionOffer" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition">
                    Oui, prescrire
                </button>
            </div>
        </div>

        <MedicalRecordModal
            v-if="showConsultationModal"
            :appointmentId="consultationAppointmentId"
            :prefilledPatient="patientPrefill"
            @close="closeConsultationModal"
            @save="handleConsultationSave"
        />

        <PrescriptionModal
            v-if="showPrescriptionModal"
            :prefilledPatient="patientPrefill"
            :prefilledMedicalRecordId="prescriptionOffer.medicalRecordId"
            @close="showPrescriptionModal = false"
            @save="handlePrescriptionSave"
        />
```

- [ ] **Step 4: Ajouter la logique dans `<script setup>`**

Ajouter les imports nécessaires, juste après les imports existants (après la ligne `import SpiritualTimeline ...`, ligne 133) :

```javascript
import MedicalRecordModal from '@/components/medical-records/MedicalRecordModal.vue';
import PrescriptionModal from '@/components/prescriptions/PrescriptionModal.vue';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { usePrescriptionStore } from '@/stores/prescriptionStore';
import { useAppointmentStore } from '@/stores/appointmentStore';
```

Ajouter, juste après `const dossierStore = usePatientDossierStore();` (ligne 143) :

```javascript
const medicalRecordStore = useMedicalRecordStore();
const prescriptionStore = usePrescriptionStore();
const appointmentStore = useAppointmentStore();

const showConsultationModal = ref(false);
const consultationAppointmentId = ref(null);
const showPrescriptionModal = ref(false);
const prescriptionOffer = ref({ visible: false, medicalRecordId: null });

const patientPrefill = computed(() => {
    const p = dossierStore.patientSummary;
    if (!p) return null;
    return {
        patientId: p.patient_id,
        code: p.code,
        firstName: (p.full_name || '').split(' ')[0] || '',
        lastName: (p.full_name || '').split(' ').slice(1).join(' ') || '',
    };
});

function openConsultationModal(appointmentId = null) {
    consultationAppointmentId.value = appointmentId;
    showConsultationModal.value = true;
}

function closeConsultationModal() {
    showConsultationModal.value = false;
    consultationAppointmentId.value = null;
}

async function handleConsultationSave(data) {
    try {
        const record = await medicalRecordStore.createMedicalRecord(data);
        await dossierStore.refreshMedicalHistory(route.params.id);

        if (data.appointmentId) {
            try {
                await appointmentStore.completeAppointment(data.appointmentId);
            } catch (err) {
                console.error('Erreur complétion RDV:', err);
                alert("Le dossier a été enregistré, mais le rendez-vous n'a pas pu être marqué terminé automatiquement. Utilisez le bouton \"Terminer\" sur la liste des rendez-vous.");
            }
        }

        closeConsultationModal();
        prescriptionOffer.value = { visible: true, medicalRecordId: record.record_id };
    } catch (err) {
        console.error('Erreur enregistrement dossier medical:', err);
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
    }
}

function declinePrescriptionOffer() {
    prescriptionOffer.value = { visible: false, medicalRecordId: null };
}

function acceptPrescriptionOffer() {
    prescriptionOffer.value.visible = false;
    showPrescriptionModal.value = true;
}

async function handlePrescriptionSave(data) {
    try {
        await prescriptionStore.createPrescription(data);
        showPrescriptionModal.value = false;
        prescriptionOffer.value = { visible: false, medicalRecordId: null };
    } catch (err) {
        console.error('Erreur enregistrement prescription:', err);
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
    }
}
```

Remplacer le bloc `onMounted` existant (lignes 146-149) :

```javascript
onMounted(() => {
    const id = route.params.id;
    if (id) dossierStore.fetchDossierComplete(id);

    const appointmentId = route.query.appointmentId ? Number(route.query.appointmentId) : null;
    if (appointmentId) {
        openConsultationModal(appointmentId);
    }
});
```

Ajouter `computed` à l'import Vue existant (ligne 123, actuellement `import { ref, onMounted } from 'vue';`) :

```javascript
import { ref, computed, onMounted } from 'vue';
```

- [ ] **Step 5: Vérifier la compilation**

Run (depuis `ah2-admin-web/`): `npx vite build`
Expected: succès, aucune erreur.

---

### Task 5: `AppointmentsList.vue` — navigation vers le dossier et démarrage de consultation

**Files:**
- Modify: `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue`

**Interfaces:**
- Consumes : la route montant `PatientDetailView.vue` (Tâche 4) accepte `?appointmentId=X`.

- [ ] **Step 1: Ajouter les deux boutons**

Dans `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue`, ajouter dans la colonne actions (juste après le bouton Annuler, avant le bouton Modifier — lignes 118-126, avant ligne 127) :

```html
                  <button
                    v-if="appt.status === 'pending'"
                    @click="voirDossier(appt)"
                    :disabled="!appt.patient_id"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Voir dossier
                  </button>
                  <button
                    v-if="appt.status === 'pending'"
                    @click="demarrerConsultation(appt)"
                    :disabled="!appt.patient_id || !appt.server_id"
                    :title="!appt.server_id ? t('appointments.pending_sync') : ''"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Démarrer consultation
                  </button>
```

- [ ] **Step 2: Ajouter les fonctions de navigation**

Dans `<script setup>`, ajouter l'import du routeur juste après `import { useI18n } from 'vue-i18n';` (ligne 160) :

```javascript
import { useRouter } from 'vue-router';
```

Ajouter, juste après `const appointmentStore = useAppointmentStore();` (ligne 169) :

```javascript
const router = useRouter();

function voirDossier(appt) {
  router.push(`/medical/patients/${appt.patient_id}`);
}

function demarrerConsultation(appt) {
  router.push(`/medical/patients/${appt.patient_id}?appointmentId=${appt.server_id}`);
}
```

(le chemin `/medical/patients/{id}` reprend le préfixe déjà utilisé pour ce même écran par le rôle médecin/infirmier — même route que celle empruntée par `PatientList.vue::viewPatientDossier`, qui construit son lien de façon relative à `route.path` : ici la route de départ est `/medical/appointments`, donc un chemin absolu est nécessaire plutôt qu'une construction relative)

- [ ] **Step 3: Vérifier la compilation**

Run (depuis `ah2-admin-web/`): `npx vite build`
Expected: succès, aucune erreur.

- [ ] **Step 4: Vérification manuelle (checklist pour un testeur humain — pas d'outil navigateur dans cet environnement)**

1. Se connecter avec un compte `medecin`, créer un rendez-vous en attente pour un patient existant.
2. Sur la liste des rendez-vous, cliquer « Voir dossier » → arrivée sur le dossier du bon patient, aucune modale ouverte.
3. Revenir à la liste, cliquer « Démarrer consultation » → arrivée sur le dossier du même patient, la modale de consultation s'ouvre automatiquement avec le patient déjà renseigné (champ code patient grisé, non modifiable).
4. Remplir et enregistrer le dossier médical → vérifier en base que `appointment_id` est bien renseigné sur le nouveau dossier, et que le rendez-vous d'origine est passé à `completed` sur la liste des rendez-vous.
5. La bannière « Ajouter une prescription pour cette consultation ? » apparaît → cliquer « Oui, prescrire » → la modale de prescription s'ouvre avec le patient déjà renseigné ; enregistrer et vérifier en base que `medical_record_id` correspond au dossier créé à l'étape 4.
6. Cliquer « Non » sur la bannière (avec un autre dossier créé sans y donner suite) → la bannière disparaît, rien d'autre ne se passe.
7. Depuis le dossier patient (sans venir d'un rendez-vous), cliquer « Nouvelle consultation » → la modale s'ouvre pré-remplie avec le patient courant ; enregistrer et vérifier que `appointment_id` reste `NULL` en base, qu'aucun rendez-vous n'est affecté.

---

## Self-Review

**1. Couverture de la spec :**
- Modèle de données (colonne + procédure stockée) → Task 1. ✅
- Section 1 (pré-remplissage des deux modales) → Tasks 2-3, y compris le verrouillage du champ code patient dans les deux cas. ✅
- Section 2 (actions sur la liste des rendez-vous) → Task 5. ✅
- Section 3 (câblage du bouton + auto-ouverture + enchaînement complet : création → complétion RDV → proposition prescription) → Task 4, avec gestion explicite du cas d'échec de complétion du RDV (dossier déjà créé conservé, message d'erreur distinct, bouton Terminer existant comme filet de secours — exactement ce que la spec demande). ✅
- Exclusions (durcissement de `/appointments`, hors ligne, export/impression) : aucune tâche n'y touche. ✅
- Définition du « terminé » : chaque point correspond à une étape vérifiable (Task 1 pour le lien en base, Task 5 Step 4 pour le flux de bout en bout). ✅

**2. Scan de placeholders :** aucun "TBD"/"TODO" ; chaque étape de code contient le code réel à écrire, y compris la migration complète (upgrade et downgrade) et la procédure stockée réécrite en entier.

**3. Cohérence des types/signatures :** `MedicalRecordModal.vue` (Task 2) émet `appointmentId` dans son payload `save` ; `PatientDetailView.vue` (Task 4) lit `data.appointmentId` dans `handleConsultationSave` et le transmet à `medicalRecordStore.createMedicalRecord` → `MedicalRecordGateway.createMedicalRecord` (Task 4, Steps 1-2) qui le convertit en `appointment_id` snake_case pour l'API — cohérent avec `MedicalRecordCreate.appointment_id` (Task 1). `PrescriptionModal.vue` (Task 3) lit `prefilledMedicalRecordId` ; `PatientDetailView.vue` (Task 4) le fournit depuis `prescriptionOffer.value.medicalRecordId`, lui-même alimenté par `record.record_id` — le nom de champ `record_id` correspond exactement à `MedicalRecordResponse.record_id` (Task 1, hérité de la table `medical_records`, jamais renommé). `patientPrefill` (Task 4) construit `{patientId, code, firstName, lastName}` — la forme exacte que `setFromExisting()` (Task 2, déjà existant) et le bloc ajouté à `PrescriptionModal.vue` (Task 3) attendent tous deux. `appt.server_id`/`appt.patient_id` (Task 5) correspondent aux champs déjà utilisés par les boutons Terminer/Annuler existants du même fichier, vérifiés dans le code réel avant d'écrire cette tâche.
