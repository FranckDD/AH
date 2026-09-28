# Chantier 3 — Fenêtre médicale, Étape 3 : Dossier Médical (CRUD complet) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner à `medecin`/`nurse` un module Dossier Médical complet (liste + création/édition + suppression de consultations) dans leur fenêtre médicale, port fidèle de `MedicalRecordFormView`/`MedicalRecordListView` (`view_pyqt6/medical_record/`) côté desktop.

**Architecture:** Nouvelle section de navigation "Dossier Médical" dans `MedicalLayout.vue` (déjà construit aux Étapes 1-2), route `/medical/medical-records`, store Pinia + gateway dédiés. Un petit correctif backend est nécessaire (voir Task 2) : la réponse `GET /medical_records/` ne renvoie aujourd'hui aucune information patient (ni nom, ni code), alors que la relation SQLAlchemy est déjà chargée côté requête — juste jamais exposée dans le schéma de réponse. La recherche patient réutilise un nouveau composable partagé `usePatientLookup.js` (troisième occurrence du même pattern après `AppointmentModal.vue` et `PrescriptionModal.vue` — voir Global Constraints).

**Tech Stack:** Vue 3 (Composition API, `<script setup>`), Pinia, vue-router 4, vue-i18n, Tailwind CSS, axios (`src/services/api.js`). FastAPI côté backend (Pydantic v2, SQLAlchemy). Pas de framework de test frontend configuré (`package.json` n'a que `dev`/`build`/`preview`) — vérification via `npm run build` + test manuel navigateur. Le backend a `pytest` configuré (`tests/`, `conftest.py`).

**Spec:** `docs/superpowers/specs/2026-08-13-chantier-3-fenetre-medicale-design.md`

## Global Constraints

- **Le champ identifiant d'un dossier médical dans les réponses API est `record_id`** (`api_backend/backend_app/routes/medical_records/schemas.py:61` : `class MedicalRecordResponse(MedicalRecordBase): record_id: int`) — ni `id`, ni `medical_record_id`. Troisième module de ce chantier, troisième nom de champ différent (Rendez-vous : `id`, Prescription : `prescription_id`, Dossier Médical : `record_id`) — vérifier systématiquement plutôt que supposer.
- **Ne pas répliquer le bug de re-filtrage côté client du desktop.** `mr_list_view.py` pagine côté serveur PUIS re-filtre/re-pagine côté client sur la page déjà reçue (ses filtres de date/motif/gravité/recherche ne s'appliquent en pratique que dans les 20 lignes de la page courante, pas sur l'ensemble des données) — un bug latent identifié pendant l'investigation, pas un comportement à porter. Le port web envoie tous les filtres (`search`, `date_from`, `date_to`, `motif_code`, `severity`) directement au serveur (`GET /medical_records/`, déjà supporté) et n'applique aucun filtrage/re-pagination côté client.
- **`date_from`/`date_to` ne sont envoyés que si les DEUX sont renseignés** — même correctif que celui appliqué après-coup sur le module Prescription (le backend ignore un filtre à une seule borne sans le signaler) ; appliqué ici dès la conception, pas en correction finale.
- **Un nouveau composable partagé `usePatientLookup.js` est introduit dans ce plan** (Task 3) et utilisé par le nouveau `MedicalRecordModal.vue` (Task 4). `AppointmentModal.vue` et `PrescriptionModal.vue` (déjà livrés, déjà revus, déjà en production dans le WIP) **ne sont pas retouchés** dans ce plan — leur propre copie du pattern de recherche patient reste telle quelle. Une consolidation rétroactive de ces deux fichiers vers le composable est un refactor séparé, à faire sur demande explicite, pas inclus ici.
- **Pas d'export PDF/Excel** dans cette passe — le desktop en a un (`mr_list_view.py`, boutons "Export PDF"/"Export Excel"), volontairement différé (YAGNI, aucune demande explicite pour ce chantier).
- **Pas de bouton "Prescrire" en navigation croisée** (desktop : sélectionner un dossier → ouvrir directement une prescription pré-remplie) — volontairement différé, amélioration future possible, pas requis pour un module Dossier Médical fonctionnel.
- **Suppression directement depuis la liste** (bouton dans la colonne Actions), contrairement au desktop où la suppression n'existe que dans le formulaire d'édition — cohérent avec le pattern déjà établi sur Rendez-vous et Prescription dans ce chantier, pas une régression.
- **Les plages de validation des constantes vitales sont uniquement côté client** (température 30–45°C, poids 0–1000kg, taille 30–250cm — bornes de soumission du desktop, pas les bornes plus étroites du validateur de widget) — le backend n'impose aucune contrainte de plage (juste un cast en `float`), donc le port web doit les reproduire pour ne pas perdre ce garde-fou.
- **Ne rien committer.** Comme aux Étapes 1-2, tous les fichiers déjà existants modifiés par ce plan (`router/index.js`, `i18n.js`, `MedicalLayout.vue`, et les deux fichiers backend de la Task 2) sont soit en WIP non commité de l'utilisateur, soit destinés à le rester ; les nouveaux fichiers aussi. Aucune étape ne doit exécuter `git add`/`git commit`.
- `MainLayout.vue` et les modules déjà livrés (`AppointmentsList.vue`/`AppointmentModal.vue`/`appointmentStore.js`/`AppointmentGateway.js`, `PrescriptionsList.vue`/`PrescriptionModal.vue`/`prescriptionStore.js`/`PrescriptionGateway.js`) ne sont pas touchés par ce plan, sauf le composable partagé introduit en Task 3 qui est un nouveau fichier, pas une modification de ces derniers.

---

### Task 1 : Clés i18n du module Dossier Médical

**Files:**
- Modify: `ah2-admin-web/src/i18n.js`
- Test: manuel (pas de framework de test frontend) — voir Step 2

**Interfaces:**
- Consumes: rien (tâche indépendante, pure donnée).
- Produces: le bloc `medicalRecords.*` complet (fr + en) que les Tasks 4-5 consomment via `t('medicalRecords.xxx')`. Clés exactes listées ci-dessous.

- [ ] **Step 1 : Ajouter le bloc `medicalRecords` au français et à l'anglais**

Dans `ah2-admin-web/src/i18n.js`, le bloc `prescriptions` du français se termine par la fermeture de son sous-bloc `modal` (repère : la clé `date_order_error: "La date de fin doit être postérieure ou égale à la date de début."` suivie de deux accolades fermantes puis `finance: {`). Insérer un nouveau bloc `medicalRecords` juste après la fermeture du bloc `prescriptions`, avant `finance: {` :

```js
    medicalRecords: {
      title: "Dossier Médical",
      subtitle: "Consultations et paramètres cliniques",
      new_record: "Nouvelle Consultation",
      search_label: "Recherche",
      search_placeholder: "Rechercher code patient ou nom...",
      date_from: "Du",
      date_to: "Au",
      motif_label: "Motif",
      motif_all: "Tous",
      severity_label: "Gravité",
      severity_all: "Toutes",
      severity_low: "Faible",
      severity_medium: "Moyen",
      severity_high: "Élevé",
      results_count: "consultations trouvées",
      empty: "Aucune consultation trouvée pour ces critères.",
      confirm_delete: "Supprimer cette consultation ?",
      table: {
        patient: "Patient",
        date: "Date",
        motif: "Motif",
        severity: "Gravité",
        diagnosis: "Diagnostic",
        treatment: "Traitement",
        actions: "Actions"
      },
      actions: {
        edit: "Éditer",
        delete: "Supprimer"
      },
      modal: {
        title_new: "Nouvelle Consultation",
        title_edit: "Modifier la Consultation",
        patient_code: "Code Patient",
        patient_not_found: "Patient introuvable",
        section_consultation: "Consultation",
        consultation_date: "Date de consultation",
        motif: "Motif",
        motif_none: "-- Sélectionner un motif --",
        marital_status: "État civil",
        severity: "Gravité",
        section_vitals: "Signes Vitaux",
        bp: "Tension artérielle",
        temperature: "Température (°C)",
        weight: "Poids (kg)",
        height: "Taille (cm)",
        section_notes: "Notes Cliniques",
        medical_history: "Antécédents médicaux",
        allergies: "Allergies",
        symptoms: "Symptômes",
        diagnosis: "Diagnostic",
        treatment: "Traitement",
        notes: "Notes",
        cancel: "Annuler",
        save: "Enregistrer",
        motif_required: "Veuillez sélectionner un motif.",
        temperature_range: "La température doit être comprise entre 30 et 45°C.",
        weight_range: "Le poids doit être compris entre 0 et 1000 kg.",
        height_range: "La taille doit être comprise entre 30 et 250 cm.",
        marital_single: "Célibataire",
        marital_married: "Marié(e)",
        marital_divorced: "Divorcé(e)",
        marital_widowed: "Veuf(ve)"
      }
    },
```

Dans le bloc anglais, insérer symétriquement (même position relative, après le bloc `prescriptions` anglais, avant `finance: {` anglais) :

```js
    medicalRecords: {
      title: "Medical Record",
      subtitle: "Consultations and clinical vitals",
      new_record: "New Consultation",
      search_label: "Search",
      search_placeholder: "Search patient code or name...",
      date_from: "From",
      date_to: "To",
      motif_label: "Reason",
      motif_all: "All",
      severity_label: "Severity",
      severity_all: "All",
      severity_low: "Low",
      severity_medium: "Medium",
      severity_high: "High",
      results_count: "consultations found",
      empty: "No consultations found for these criteria.",
      confirm_delete: "Delete this consultation?",
      table: {
        patient: "Patient",
        date: "Date",
        motif: "Reason",
        severity: "Severity",
        diagnosis: "Diagnosis",
        treatment: "Treatment",
        actions: "Actions"
      },
      actions: {
        edit: "Edit",
        delete: "Delete"
      },
      modal: {
        title_new: "New Consultation",
        title_edit: "Edit Consultation",
        patient_code: "Patient Code",
        patient_not_found: "Patient not found",
        section_consultation: "Consultation",
        consultation_date: "Consultation date",
        motif: "Reason",
        motif_none: "-- Select a reason --",
        marital_status: "Marital status",
        severity: "Severity",
        section_vitals: "Vitals",
        bp: "Blood pressure",
        temperature: "Temperature (°C)",
        weight: "Weight (kg)",
        height: "Height (cm)",
        section_notes: "Clinical Notes",
        medical_history: "Medical history",
        allergies: "Allergies",
        symptoms: "Symptoms",
        diagnosis: "Diagnosis",
        treatment: "Treatment",
        notes: "Notes",
        cancel: "Cancel",
        save: "Save",
        motif_required: "Please select a reason.",
        temperature_range: "Temperature must be between 30 and 45°C.",
        weight_range: "Weight must be between 0 and 1000 kg.",
        height_range: "Height must be between 30 and 250 cm.",
        marital_single: "Single",
        marital_married: "Married",
        marital_divorced: "Divorced",
        marital_widowed: "Widowed"
      }
    },
```

- [ ] **Step 2 : Vérifier la compilation**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur.

- [ ] **Step 3 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Passer à la tâche suivante.

---

### Task 2 : Correctif backend — exposer le patient dans `GET /medical_records/`

**Files:**
- Modify: `api_backend/backend_app/routes/medical_records/schemas.py`
- Modify: `api_backend/backend_app/routes/medical_records/mapping.py`
- Test: Create: `tests/test_medical_record_mapping.py`

**Interfaces:**
- Consumes: la relation SQLAlchemy `MedicalRecord.patient` (`models/medical_record.py:37`, `relationship("Patient", back_populates="medical_records")`), déjà chargée par `repositories/medical_repo.py`'s `list_records()` via `joinedload(MedicalRecord.patient)` (ligne 26) — la donnée existe déjà en mémoire au moment de la sérialisation, elle n'est simplement jamais extraite ni déclarée dans le schéma de réponse.
- Produces: `MedicalRecordResponse.patient` — un dict `{ patient_id, code_patient, first_name, last_name }` ou `None`, même forme que le `patient` déjà exposé par `PrescriptionResponse`/`AppointmentResponse`. La Task 5 (liste) affiche `rec.patient?.code_patient`/`rec.patient?.first_name`/`rec.patient?.last_name` — elle dépend de ce champ étant réellement peuplé par `GET /medical_records/`.

- [ ] **Step 1 : Écrire le test (échoue d'abord)**

Créer `tests/test_medical_record_mapping.py` avec ce contenu exact :

```python
from api_backend.backend_app.routes.medical_records.mapping import normalize_medical_record_data


class FakePatient:
    def __init__(self, patient_id, code_patient, first_name, last_name):
        self.patient_id = patient_id
        self.code_patient = code_patient
        self.first_name = first_name
        self.last_name = last_name


class FakeMedicalRecord:
    def __init__(self, patient=None):
        self.record_id = 1
        self.patient_id = 42
        self.consultation_date = "2026-08-14T00:00:00"
        self.motif_code = "CONSULT"
        self.marital_status = None
        self.bp = None
        self.temperature = None
        self.weight = None
        self.height = None
        self.medical_history = None
        self.allergies = None
        self.symptoms = None
        self.diagnosis = None
        self.treatment = None
        self.severity = None
        self.notes = None
        self.created_by = None
        self.created_by_name = "Dr Test"
        self.last_updated_by = None
        self.last_updated_by_name = None
        self.patient = patient


def test_normalize_includes_patient_dict_when_relation_loaded():
    fake_patient = FakePatient(42, "AH2-000042AB", "Jean", "Dupont")
    record = FakeMedicalRecord(patient=fake_patient)

    result = normalize_medical_record_data(record)

    assert result["patient"] == {
        "patient_id": 42,
        "code_patient": "AH2-000042AB",
        "first_name": "Jean",
        "last_name": "Dupont",
    }


def test_normalize_handles_missing_patient_relation_gracefully():
    record = FakeMedicalRecord(patient=None)

    result = normalize_medical_record_data(record)

    assert result.get("patient") is None
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

Run: `pytest tests/test_medical_record_mapping.py -v`
Expected: `test_normalize_includes_patient_dict_when_relation_loaded` échoue (`KeyError: 'patient'` ou `assert None == {...}`) — `normalize_medical_record_data` ne construit pas encore ce champ. `test_normalize_handles_missing_patient_relation_gracefully` peut déjà passer (comportement actuel : pas de clé `patient` du tout, donc `.get("patient")` est déjà `None`) — c'est acceptable, le premier test est celui qui pilote l'implémentation.

- [ ] **Step 3 : Ajouter le champ `patient` au schéma de réponse**

Dans `api_backend/backend_app/routes/medical_records/schemas.py`, la classe `MedicalRecordResponse` (lignes 60-68) est actuellement :

```python
class MedicalRecordResponse(MedicalRecordBase):
    record_id: int
    consultation_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    last_updated_by: Optional[int] = None
    last_updated_by_name: Optional[str] = None

    model_config = {"from_attributes": True}
```

La remplacer par :

```python
class MedicalRecordResponse(MedicalRecordBase):
    record_id: int
    consultation_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    last_updated_by: Optional[int] = None
    last_updated_by_name: Optional[str] = None
    patient: Optional[dict] = None

    model_config = {"from_attributes": True}
```

(Seule la ligne `patient: Optional[dict] = None` est ajoutée ; ne rien changer d'autre dans cette classe, ni dans les `field_validator` qui suivent.)

- [ ] **Step 4 : Peupler le champ `patient` dans `normalize_medical_record_data`**

Dans `api_backend/backend_app/routes/medical_records/mapping.py`, la fonction `normalize_medical_record_data` se termine actuellement par le bloc `doctor_name` puis `return data` (lignes 78-81) :

```python
    # Alias 'doctor_name' pour le front
    data["doctor_name"] = data["created_by_name"]

    return data
```

La remplacer par :

```python
    # Alias 'doctor_name' pour le front
    data["doctor_name"] = data["created_by_name"]

    # Sous-objet patient (code/nom) pour l'affichage cote frontend - meme
    # convention que Prescription/Appointment (_serialize_patient) : la
    # relation SQLAlchemy MedicalRecord.patient est deja chargee via
    # joinedload dans list_records() (repositories/medical_repo.py:26),
    # mais MedicalRecordResponse ne la declarait pas encore, donc jamais
    # retournee au client malgre la donnee deja presente en memoire.
    if not data.get("patient"):
        patient_obj = getattr(raw, "patient", None)
        if patient_obj:
            data["patient"] = {
                "patient_id": getattr(patient_obj, "patient_id", None),
                "code_patient": getattr(patient_obj, "code_patient", None),
                "first_name": getattr(patient_obj, "first_name", None),
                "last_name": getattr(patient_obj, "last_name", None),
            }

    return data
```

- [ ] **Step 5 : Relancer le test, vérifier qu'il passe**

Run: `pytest tests/test_medical_record_mapping.py -v`
Expected: les deux tests passent.

- [ ] **Step 6 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Passer à la tâche suivante.

---

### Task 3 : `usePatientLookup.js` + `MedicalRecordGateway.js` + `medicalRecordStore.js`

**Files:**
- Create: `ah2-admin-web/src/composables/usePatientLookup.js`
- Create: `ah2-admin-web/src/services/MedicalRecordGateway.js`
- Create: `ah2-admin-web/src/stores/medicalRecordStore.js`
- Test: manuel (pas de framework de test frontend) — voir Step 4

**Interfaces:**
- Consumes: `api` (`src/services/api.js`), endpoint `GET /patients/` avec `search` (même contrat que dans `AppointmentModal.vue`/`PrescriptionModal.vue`), endpoints backend `GET/POST/PUT/DELETE /medical_records/`, `GET /medical_records/motifs` (déjà RBAC `medecin`/`nurse`/`admin`/`manager`, déjà complets — la Task 2 les a seulement enrichis, pas modifiés dans leur contrat).
- Produces:
  - `usePatientLookup(getNotFoundMessage)` — fonction composable prenant en paramètre une fonction `() => string` (résolvant le message d'erreur i18n au moment de l'appel, pas une fois pour toutes). Retourne `{ patientCode, patientId, patientName, patientLookupMessage, lookupPatient, ensureLookup, setFromExisting }` (tous des `ref`s sauf les trois fonctions). `lookupPatient()` fait la recherche (avec le pattern anti-course déjà validé sur les deux autres modules). `ensureLookup()` attend toute recherche en cours ou en déclenche une nouvelle si nécessaire — à appeler avant de vérifier `patientId.value` dans un `handleSubmit`. `setFromExisting({ patientId, code, firstName, lastName })` préremplit l'état pour un mode édition, sans faire d'appel réseau. La Task 4 (modale) consomme cette interface exacte.
  - `MedicalRecordGateway` avec `fetchMedicalRecords(params)`, `fetchMotifs()`, `createMedicalRecord(data)`, `updateMedicalRecord(recordId, data)`, `deleteMedicalRecord(recordId)`.
  - `useMedicalRecordStore()` exposant `records`, `motifs`, `isLoading`, `filters`, `pagination`, `fetchMedicalRecords()`, `fetchMotifs()`, `createMedicalRecord(data)`, `updateMedicalRecord(recordId, data)`, `deleteMedicalRecord(recordId)`, `setPage(page)`, `setFilters(newFilters)`.
  - Le paramètre `data` de `createMedicalRecord`/`updateMedicalRecord` (gateway ET store, même forme) : `{ patientId, consultationDate, motifCode, maritalStatus, severity, bp, temperature, weight, height, medicalHistory, allergies, symptoms, diagnosis, treatment, notes }` — exactement les clés que la modale de la Task 4 émettra.

- [ ] **Step 1 : Créer `usePatientLookup.js`**

Créer `ah2-admin-web/src/composables/usePatientLookup.js` avec ce contenu exact :

```js
import { ref } from 'vue';
import api from '@/services/api';

// Composable partage de recherche patient par code - troisieme occurrence
// du meme pattern (apres AppointmentModal.vue et PrescriptionModal.vue),
// extrait ici pour ne pas le dupliquer une troisieme fois. Les deux
// modales existantes ne sont PAS retouchees dans ce plan (voir Global
// Constraints) - seul ce nouveau module l'utilise pour l'instant.
export function usePatientLookup(getNotFoundMessage) {
  const patientCode = ref('');
  const patientId = ref(null);
  const patientName = ref('');
  const patientLookupMessage = ref('');

  let pendingLookup = null;

  async function lookupPatient() {
    const raw = patientCode.value.trim();
    if (!raw) {
      patientId.value = null;
      patientName.value = '';
      patientLookupMessage.value = '';
      return;
    }

    let code = raw.toUpperCase();
    if (!code.startsWith('AH2-')) {
      code = `AH2-${code}`;
    }
    patientCode.value = code;

    pendingLookup = (async () => {
      try {
        const res = await api.get('/patients/', { params: { search: code, per_page: 5 } });
        const list = Array.isArray(res.data) ? res.data : (res.data.data || []);
        const match = list.find((p) => p.code_patient === code) || list[0] || null;

        if (!match) {
          patientId.value = null;
          patientName.value = '';
          patientLookupMessage.value = getNotFoundMessage();
          return;
        }

        patientId.value = match.id || match.patient_id;
        patientName.value = [match.first_name, match.last_name].filter(Boolean).join(' ');
        patientLookupMessage.value = patientName.value;
      } catch (err) {
        console.error('Erreur recherche patient:', err);
        patientId.value = null;
        patientName.value = '';
        patientLookupMessage.value = getNotFoundMessage();
      }
    })();

    await pendingLookup;
  }

  async function ensureLookup() {
    if (pendingLookup) {
      await pendingLookup;
    } else if (!patientId.value && patientCode.value.trim()) {
      await lookupPatient();
    }
  }

  function setFromExisting({ patientId: pid, code, firstName, lastName }) {
    patientId.value = pid || null;
    patientCode.value = code || '';
    patientName.value = [firstName, lastName].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  }

  return {
    patientCode,
    patientId,
    patientName,
    patientLookupMessage,
    lookupPatient,
    ensureLookup,
    setFromExisting,
  };
}
```

- [ ] **Step 2 : Créer `MedicalRecordGateway.js`**

Créer `ah2-admin-web/src/services/MedicalRecordGateway.js` avec ce contenu exact :

```js
import api from '@/services/api';

const cleanParams = (params) => {
    const cleaned = {};
    for (const key in params) {
        const value = params[key];
        if (value !== null && value !== undefined && value !== '') {
            cleaned[key] = value;
        }
    }
    return cleaned;
};

export const MedicalRecordGateway = {

    async fetchMedicalRecords(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            search: params.searchQuery,
            motif_code: params.motifCode,
            severity: params.severity,
        };

        // Le backend n'applique le filtre de date que si les DEUX bornes
        // sont presentes - voir Global Constraints (meme correctif que
        // Prescription, applique ici des le depart).
        if (params.dateFrom && params.dateTo) {
            rawQuery.date_from = params.dateFrom;
            rawQuery.date_to = params.dateTo;
        }

        return api.get('/medical_records/', { params: cleanParams(rawQuery) });
    },

    async fetchMotifs() {
        return api.get('/medical_records/motifs');
    },

    async createMedicalRecord(data) {
        const payload = {
            patient_id: data.patientId,
            consultation_date: data.consultationDate,
            motif_code: data.motifCode,
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
        };
        return api.post('/medical_records/', payload);
    },

    async updateMedicalRecord(recordId, data) {
        const payload = {
            patient_id: data.patientId,
            consultation_date: data.consultationDate,
            motif_code: data.motifCode,
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
        };
        return api.put(`/medical_records/${recordId}`, payload);
    },

    async deleteMedicalRecord(recordId) {
        return api.delete(`/medical_records/${recordId}`);
    },
};
```

- [ ] **Step 3 : Créer `medicalRecordStore.js`**

Créer `ah2-admin-web/src/stores/medicalRecordStore.js` avec ce contenu exact :

```js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { MedicalRecordGateway } from '@/services/MedicalRecordGateway';

export const useMedicalRecordStore = defineStore('medicalRecord', () => {

    // --- ÉTAT ---
    const records = ref([]);
    const motifs = ref([]);
    const isLoading = ref(false);
    const totalItems = ref(0);

    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        dateFrom: '',
        dateTo: '',
        motifCode: '',
        severity: '',
    });

    // --- ACTIONS ---

    async function fetchMedicalRecords() {
        isLoading.value = true;
        try {
            const params = {
                page: filters.value.page,
                per_page: filters.value.per_page,
                searchQuery: filters.value.searchQuery,
                motifCode: filters.value.motifCode,
                severity: filters.value.severity,
                dateFrom: filters.value.dateFrom,
                dateTo: filters.value.dateTo,
            };

            const res = await MedicalRecordGateway.fetchMedicalRecords(params);
            records.value = res.data.data || [];
            totalItems.value = res.data.total || 0;
        } catch (err) {
            console.error('Erreur chargement dossiers medicaux:', err);
            records.value = [];
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchMotifs() {
        try {
            const res = await MedicalRecordGateway.fetchMotifs();
            motifs.value = res.data || [];
        } catch (err) {
            console.error('Erreur chargement motifs:', err);
            motifs.value = [];
        }
    }

    async function createMedicalRecord(data) {
        await MedicalRecordGateway.createMedicalRecord(data);
        filters.value.page = 1;
        await fetchMedicalRecords();
    }

    async function updateMedicalRecord(recordId, data) {
        await MedicalRecordGateway.updateMedicalRecord(recordId, data);
        await fetchMedicalRecords();
    }

    async function deleteMedicalRecord(recordId) {
        await MedicalRecordGateway.deleteMedicalRecord(recordId);
        await fetchMedicalRecords();
    }

    function setPage(page) {
        filters.value.page = page;
        fetchMedicalRecords();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchMedicalRecords();
    }

    // --- GETTERS ---
    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1,
    }));

    return {
        records,
        motifs,
        isLoading,
        filters,
        pagination,
        fetchMedicalRecords,
        fetchMotifs,
        createMedicalRecord,
        updateMedicalRecord,
        deleteMedicalRecord,
        setPage,
        setFilters,
    };
});
```

- [ ] **Step 4 : Vérifier la compilation**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur.

- [ ] **Step 5 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Passer à la tâche suivante.

---

### Task 4 : `MedicalRecordModal.vue` (création/édition)

**Files:**
- Create: `ah2-admin-web/src/components/medical-records/MedicalRecordModal.vue`
- Test: manuel (pas de framework de test frontend) — voir Step 2. Comme pour les modales précédentes, ce fichier n'est pas encore référencé par une vue (Task 5 le fait) — si `@vue/compiler-sfc` est disponible dans le projet (`npm ls @vue/compiler-sfc` depuis `ah2-admin-web/`), l'utiliser pour parser le fichier isolément et confirmer l'absence d'erreur de syntaxe (voir la note dans les tâches équivalentes des plans précédents de ce chantier pour un exemple de script) ; sinon, une relecture manuelle attentive suffit pour cette étape.

**Interfaces:**
- Consumes: `useMedicalRecordStore` (Task 3 — `motifs`, `fetchMotifs()`), `usePatientLookup` (Task 3 — interface exacte décrite dans la Task 3), clés i18n `medicalRecords.modal.*` et `medicalRecords.severity_*` (Task 1).
- Produces: composant `MedicalRecordModal.vue` avec `props: { record: Object|null }` (`null`/absent = création, objet = édition) et `emits: ['close', 'save']`. Le payload `save` est exactement `{ patientId, consultationDate, motifCode, maritalStatus, severity, bp, temperature, weight, height, medicalHistory, allergies, symptoms, diagnosis, treatment, notes }` — la Task 5 le passe tel quel à `medicalRecordStore.createMedicalRecord(data)`/`updateMedicalRecord(id, data)` (Task 3), dont le gateway attend précisément ces clés. `temperature`/`weight`/`height` sont des `number` ou `null` (jamais une chaîne vide) au moment de l'émission — la validation numérique a déjà eu lieu.

- [ ] **Step 1 : Créer `MedicalRecordModal.vue`**

Créer `ah2-admin-web/src/components/medical-records/MedicalRecordModal.vue` avec ce contenu exact :

```vue
<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
    <div class="relative mx-auto p-6 border w-full max-w-2xl shadow-xl rounded-2xl bg-white my-8">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('medicalRecords.modal.title_edit') : t('medicalRecords.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-6">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            placeholder="Ex: AH2-000818AQ"
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"
          />
          <p class="mt-1 text-xs" :class="patientId ? 'text-emerald-600' : 'text-gray-400'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div>
          <h4 class="text-sm font-bold text-gray-500 uppercase mb-3">{{ t('medicalRecords.modal.section_consultation') }}</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.consultation_date') }}</label>
              <input v-model="form.consultationDate" type="date" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.motif') }}</label>
              <select v-model="form.motifCode" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
                <option value="">{{ t('medicalRecords.modal.motif_none') }}</option>
                <option v-for="m in medicalRecordStore.motifs" :key="m.code" :value="m.code">{{ m.label_fr }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.severity') }}</label>
              <select v-model="form.severity" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
                <option v-for="opt in severityOptions" :key="opt.value" :value="opt.value">{{ t(opt.labelKey) }}</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-4 mt-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.marital_status') }}</label>
              <select v-model="form.maritalStatus" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
                <option v-for="opt in maritalOptions" :key="opt.value" :value="opt.value">{{ t(opt.labelKey) }}</option>
              </select>
            </div>
          </div>
        </div>

        <div>
          <h4 class="text-sm font-bold text-gray-500 uppercase mb-3">{{ t('medicalRecords.modal.section_vitals') }}</h4>
          <div class="grid grid-cols-4 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.bp') }}</label>
              <input v-model="form.bp" type="text" placeholder="Ex: 120/80" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.temperature') }}</label>
              <input v-model="form.temperature" type="number" step="0.1" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.weight') }}</label>
              <input v-model="form.weight" type="number" step="0.1" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.height') }}</label>
              <input v-model="form.height" type="number" step="0.1" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
          </div>
        </div>

        <div>
          <h4 class="text-sm font-bold text-gray-500 uppercase mb-3">{{ t('medicalRecords.modal.section_notes') }}</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.medical_history') }}</label>
              <textarea v-model="form.medicalHistory" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.allergies') }}</label>
              <textarea v-model="form.allergies" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.symptoms') }}</label>
              <textarea v-model="form.symptoms" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.diagnosis') }}</label>
              <textarea v-model="form.diagnosis" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.treatment') }}</label>
              <textarea v-model="form.treatment" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.notes') }}</label>
              <textarea v-model="form.notes" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
          </div>
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-sm">
            {{ t('medicalRecords.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition bg-teal-600 hover:bg-teal-700">
            {{ t('medicalRecords.modal.save') }}
          </button>
        </div>
      </form>

    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { usePatientLookup } from '@/composables/usePatientLookup';

const { t } = useI18n();
const medicalRecordStore = useMedicalRecordStore();
const emit = defineEmits(['close', 'save']);

const props = defineProps({
  record: {
    type: Object,
    default: null,
  },
});

const isEdit = computed(() => !!props.record);

const {
  patientCode,
  patientId,
  patientName,
  patientLookupMessage,
  lookupPatient,
  ensureLookup,
  setFromExisting,
} = usePatientLookup(() => t('medicalRecords.modal.patient_not_found'));

const today = new Date().toISOString().substring(0, 10);

const form = reactive({
  consultationDate: today,
  motifCode: '',
  maritalStatus: '',
  severity: '',
  bp: '',
  temperature: '',
  weight: '',
  height: '',
  medicalHistory: '',
  allergies: '',
  symptoms: '',
  diagnosis: '',
  treatment: '',
  notes: '',
});

const maritalOptions = [
  { value: 'Single', labelKey: 'medicalRecords.modal.marital_single' },
  { value: 'Married', labelKey: 'medicalRecords.modal.marital_married' },
  { value: 'Divorced', labelKey: 'medicalRecords.modal.marital_divorced' },
  { value: 'Widowed', labelKey: 'medicalRecords.modal.marital_widowed' },
];

const severityOptions = [
  { value: 'low', labelKey: 'medicalRecords.severity_low' },
  { value: 'medium', labelKey: 'medicalRecords.severity_medium' },
  { value: 'high', labelKey: 'medicalRecords.severity_high' },
];

onMounted(() => {
  if (!medicalRecordStore.motifs.length) {
    medicalRecordStore.fetchMotifs();
  }

  if (props.record) {
    const rec = props.record;
    setFromExisting({
      patientId: rec.patient_id || rec.patient?.patient_id || null,
      code: rec.patient?.code_patient || '',
      firstName: rec.patient?.first_name,
      lastName: rec.patient?.last_name,
    });
    form.consultationDate = (rec.consultation_date || '').substring(0, 10);
    form.motifCode = rec.motif_code || '';
    form.maritalStatus = rec.marital_status || '';
    form.severity = rec.severity || '';
    form.bp = rec.bp || '';
    form.temperature = rec.temperature ?? '';
    form.weight = rec.weight ?? '';
    form.height = rec.height ?? '';
    form.medicalHistory = rec.medical_history || '';
    form.allergies = rec.allergies || '';
    form.symptoms = rec.symptoms || '';
    form.diagnosis = rec.diagnosis || '';
    form.treatment = rec.treatment || '';
    form.notes = rec.notes || '';
  }
});

function parseVital(value, min, max, errorKey) {
  if (value === '' || value === null || value === undefined) return { ok: true, value: null };
  const num = Number(value);
  if (Number.isNaN(num) || num < min || num >= max) {
    alert(t(errorKey));
    return { ok: false };
  }
  return { ok: true, value: num };
}

async function handleSubmit() {
  await ensureLookup();

  if (!patientId.value) {
    alert(t('medicalRecords.modal.patient_not_found'));
    return;
  }

  if (!form.motifCode) {
    alert(t('medicalRecords.modal.motif_required'));
    return;
  }

  const temp = parseVital(form.temperature, 30, 45, 'medicalRecords.modal.temperature_range');
  if (!temp.ok) return;
  const weight = parseVital(form.weight, 0, 1000, 'medicalRecords.modal.weight_range');
  if (!weight.ok) return;
  const height = parseVital(form.height, 30, 250, 'medicalRecords.modal.height_range');
  if (!height.ok) return;

  emit('save', {
    patientId: patientId.value,
    consultationDate: form.consultationDate,
    motifCode: form.motifCode,
    maritalStatus: form.maritalStatus,
    severity: form.severity,
    bp: form.bp,
    temperature: temp.value,
    weight: weight.value,
    height: height.value,
    medicalHistory: form.medicalHistory,
    allergies: form.allergies,
    symptoms: form.symptoms,
    diagnosis: form.diagnosis,
    treatment: form.treatment,
    notes: form.notes,
  });
}
</script>
```

- [ ] **Step 2 : Relecture de syntaxe**

Relire le fichier créé en entier pour vérifier : balises bien fermées, cohérence des accolades. Si `@vue/compiler-sfc` est disponible, l'utiliser pour parser le fichier isolément et confirmer l'absence d'erreur ; sinon, la relecture manuelle suffit pour cette étape (la Task 5 validera la compilation réelle en impliquant ce fichier dans l'arbre d'imports).

- [ ] **Step 3 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Passer à la tâche suivante.

---

### Task 5 : `MedicalRecordsList.vue` + navigation + route

**Files:**
- Create: `ah2-admin-web/src/views/modules/medical-records/MedicalRecordsList.vue`
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue`
- Modify: `ah2-admin-web/src/router/index.js`
- Test: manuel (pas de framework de test frontend) — voir Step 4

**Interfaces:**
- Consumes: `useMedicalRecordStore` (Task 3), `MedicalRecordModal.vue` (Task 4 — `props: { record }`, `emits: ['close', 'save']`, payload exact décrit dans la Task 4), clés i18n `medicalRecords.*` (Task 1).
- Produces: parcours complet liste + création/édition + suppression de dossiers médicaux, accessible depuis la navigation de `MedicalLayout.vue` — dernière tâche du plan.

- [ ] **Step 1 : Créer `MedicalRecordsList.vue`**

Créer `ah2-admin-web/src/views/modules/medical-records/MedicalRecordsList.vue` avec ce contenu exact :

```vue
<template>
  <div class="space-y-6 w-full">

    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('medicalRecords.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('medicalRecords.subtitle') }}</p>
      </div>

      <button
        @click="openCreateModal"
        class="flex items-center px-6 py-2.5 bg-teal-600 text-white rounded-xl hover:bg-teal-700 shadow-md shadow-teal-200 transition font-semibold"
      >
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('medicalRecords.new_record') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">

      <div class="flex-1 min-w-[220px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.search_label') }}</label>
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
          </div>
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('medicalRecords.search_placeholder')"
            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-teal-500 focus:border-teal-500 sm:text-sm"
          >
        </div>
      </div>

      <div class="w-full md:w-44">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.motif_label') }}</label>
        <select v-model="motifFilter" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-teal-500 focus:border-teal-500 sm:text-sm rounded-lg">
          <option value="">{{ t('medicalRecords.motif_all') }}</option>
          <option v-for="m in medicalRecordStore.motifs" :key="m.code" :value="m.code">{{ m.label_fr }}</option>
        </select>
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.severity_label') }}</label>
        <select v-model="severityFilter" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-teal-500 focus:border-teal-500 sm:text-sm rounded-lg">
          <option value="">{{ t('medicalRecords.severity_all') }}</option>
          <option value="low">{{ t('medicalRecords.severity_low') }}</option>
          <option value="medium">{{ t('medicalRecords.severity_medium') }}</option>
          <option value="high">{{ t('medicalRecords.severity_high') }}</option>
        </select>
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.date_from') }}</label>
        <input v-model="dateFrom" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.date_to') }}</label>
        <input v-model="dateTo" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

      <div class="p-4 border-b border-gray-100 flex items-center justify-between">
        <div class="text-sm text-gray-500">
          {{ medicalRecordStore.pagination.total }} {{ t('medicalRecords.results_count') }}
        </div>
      </div>

      <div v-if="medicalRecordStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></span>
        <p class="mt-2 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.motif') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.severity') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.diagnosis') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.treatment') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('medicalRecords.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="rec in medicalRecordStore.records" :key="rec.record_id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900">{{ patientName(rec) }}</div>
                <div class="text-xs text-gray-500">{{ rec.patient?.code_patient }}</div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ (rec.consultation_date || '').substring(0, 10) }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ motifLabel(rec.motif_code) }}</td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 rounded text-xs font-semibold" :class="severityClass(rec.severity)">
                  {{ severityLabel(rec.severity) }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" :title="rec.diagnosis">{{ rec.diagnosis || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" :title="rec.treatment">{{ rec.treatment || '—' }}</td>
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <button
                    @click="openEditModal(rec)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
                  >
                    {{ t('medicalRecords.actions.edit') }}
                  </button>
                  <button
                    @click="handleDelete(rec)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition"
                  >
                    {{ t('medicalRecords.actions.delete') }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="medicalRecordStore.records.length === 0">
              <td colspan="7" class="px-6 py-8 text-center text-gray-500 italic">
                {{ t('medicalRecords.empty') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="medicalRecordStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">
          {{ t('common.page') }} {{ medicalRecordStore.pagination.page }} / {{ medicalRecordStore.pagination.total_pages }}
        </p>
        <div class="flex space-x-2">
          <button @click="goToPage(medicalRecordStore.pagination.page - 1)" :disabled="medicalRecordStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(medicalRecordStore.pagination.page + 1)" :disabled="medicalRecordStore.pagination.page === medicalRecordStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>

    </div>

    <MedicalRecordModal
      v-if="showModal"
      :record="editingRecord"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { useI18n } from 'vue-i18n';
import MedicalRecordModal from '@/components/medical-records/MedicalRecordModal.vue';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const medicalRecordStore = useMedicalRecordStore();

onMounted(() => {
  medicalRecordStore.fetchMedicalRecords();
  medicalRecordStore.fetchMotifs();
});

const searchQuery = computed({
  get: () => medicalRecordStore.filters.searchQuery,
  set: (val) => medicalRecordStore.setFilters({ searchQuery: val }),
});

const motifFilter = computed({
  get: () => medicalRecordStore.filters.motifCode,
  set: (val) => medicalRecordStore.setFilters({ motifCode: val }),
});

const severityFilter = computed({
  get: () => medicalRecordStore.filters.severity,
  set: (val) => medicalRecordStore.setFilters({ severity: val }),
});

const dateFrom = computed({
  get: () => medicalRecordStore.filters.dateFrom,
  set: (val) => medicalRecordStore.setFilters({ dateFrom: val }),
});

const dateTo = computed({
  get: () => medicalRecordStore.filters.dateTo,
  set: (val) => medicalRecordStore.setFilters({ dateTo: val }),
});

function goToPage(page) {
  if (page >= 1 && page <= medicalRecordStore.pagination.total_pages) {
    medicalRecordStore.setPage(page);
  }
}

function patientName(rec) {
  const p = rec.patient;
  if (!p) return '—';
  return [p.first_name, p.last_name].filter(Boolean).join(' ');
}

function motifLabel(code) {
  const m = medicalRecordStore.motifs.find((x) => x.code === code);
  return m ? m.label_fr : (code || '—');
}

// Coloration par gravite - port exact de mr_list_view.py (rouge/jaune/vert).
function severityClass(severity) {
  if (severity === 'high') return 'bg-red-100 text-red-700';
  if (severity === 'medium') return 'bg-yellow-100 text-yellow-700';
  if (severity === 'low') return 'bg-emerald-100 text-emerald-700';
  return 'bg-gray-100 text-gray-500';
}

function severityLabel(severity) {
  if (severity === 'high') return t('medicalRecords.severity_high');
  if (severity === 'medium') return t('medicalRecords.severity_medium');
  if (severity === 'low') return t('medicalRecords.severity_low');
  return '—';
}

const showModal = ref(false);
const editingRecord = ref(null);

function openCreateModal() {
  editingRecord.value = null;
  showModal.value = true;
}

function openEditModal(rec) {
  editingRecord.value = rec;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingRecord.value = null;
}

async function handleSave(data) {
  try {
    if (editingRecord.value) {
      await medicalRecordStore.updateMedicalRecord(editingRecord.value.record_id, data);
    } else {
      await medicalRecordStore.createMedicalRecord(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement dossier medical:', err);
    alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
  }
}

async function handleDelete(rec) {
  if (!confirm(t('medicalRecords.confirm_delete'))) return;
  try {
    await medicalRecordStore.deleteMedicalRecord(rec.record_id);
  } catch (err) {
    console.error('Erreur suppression dossier medical:', err);
    alert('Erreur lors de la suppression : ' + (err.response?.data?.detail || err.message));
  }
}
</script>
```

Noter que `:key="rec.record_id"` et les appels `updateMedicalRecord(editingRecord.value.record_id, data)` / `deleteMedicalRecord(rec.record_id)` utilisent bien `record_id` — voir Global Constraints.

- [ ] **Step 2 : Ajouter l'entrée de navigation "Dossier Médical" dans `MedicalLayout.vue`**

Dans `ah2-admin-web/src/components/layout/MedicalLayout.vue`, l'import d'icônes actuel (après les Étapes 1-2) est :

```js
import {
  CalendarIcon,
  TagIcon,
  Bars3Icon,
  Bars3CenterLeftIcon
} from '@heroicons/vue/24/outline';
```

Le remplacer par (ajout de `HeartIcon`, déjà utilisé pour le même concept dans `PatientDetailView.vue` pour `medical.tabs.medical_record`) :

```js
import {
  CalendarIcon,
  TagIcon,
  HeartIcon,
  Bars3Icon,
  Bars3CenterLeftIcon
} from '@heroicons/vue/24/outline';
```

Et le tableau `menuItems` actuel :

```js
const menuItems = [
  {
    path: '/medical/appointments',
    labelKey: 'appointments.title',
    icon: CalendarIcon,
  },
  {
    path: '/medical/prescriptions',
    labelKey: 'prescriptions.title',
    icon: TagIcon,
  },
];
```

Le remplacer par :

```js
const menuItems = [
  {
    path: '/medical/appointments',
    labelKey: 'appointments.title',
    icon: CalendarIcon,
  },
  {
    path: '/medical/prescriptions',
    labelKey: 'prescriptions.title',
    icon: TagIcon,
  },
  {
    path: '/medical/medical-records',
    labelKey: 'medicalRecords.title',
    icon: HeartIcon,
  },
];
```

- [ ] **Step 3 : Ajouter la route `/medical/medical-records` dans `router/index.js`**

Dans `ah2-admin-web/src/router/index.js`, à l'intérieur du bloc `/medical`, le tableau `children` contient actuellement (après les Étapes 1-2) les routes `appointments` et `prescriptions`. Ajouter une nouvelle route enfant après `prescriptions`, avant la fermeture du tableau `children` :

```js
      {
        path: 'medical-records',
        name: 'medical-medical-records',
        component: () => import('@/views/modules/medical-records/MedicalRecordsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      }
```

Ne pas toucher au reste du fichier (le bloc `/dashboard` existant, les routes `appointments`/`prescriptions` déjà en place, les routes de secours).

- [ ] **Step 4 : Vérifier la compilation et tester manuellement**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur ; le graphe d'imports compile maintenant réellement `MedicalRecordModal.vue` (via `MedicalRecordsList.vue`) pour la première fois.

Test manuel (connecté en tant que `medecin`/`nurse`) :
1. Une troisième entrée "Dossier Médical" apparaît dans la sidebar, sous "Prescriptions" — cliquer dessus mène à `/medical/medical-records`.
2. Cliquer "Nouvelle Consultation" → la modale s'ouvre, vide, date de consultation pré-remplie à aujourd'hui.
3. Saisir un code patient existant, sortir du champ → le nom s'affiche en vert.
4. Sélectionner un motif (liste chargée depuis `GET /medical_records/motifs`), remplir quelques constantes vitales (tester qu'une température hors plage, ex. 50, déclenche bien le message d'erreur client), remplir diagnostic/traitement, enregistrer → la consultation apparaît dans la liste, avec le nom du patient correctement affiché (grâce au correctif de la Task 2 — sans lui, la colonne Patient serait vide).
5. Vérifier la coloration de la colonne Gravité (rouge/jaune/vert selon Élevé/Moyen/Faible).
6. Cliquer "Éditer" sur une consultation existante → la modale s'ouvre pré-remplie.
7. Cliquer "Supprimer" → confirmation → la consultation disparaît de la liste.
8. Tester les filtres (recherche, motif, gravité, dates Du/Au) — vérifier qu'un filtre de date à une seule borne (seulement "Du" rempli) ne casse rien et n'envoie pas de requête avec une seule borne au serveur.

- [ ] **Step 5 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Ceci termine l'Étape 3 (Dossier Médical) du chantier 3 — rapporter l'état à l'utilisateur pour relecture avant de passer à l'Étape 4 (Patients) de la spec.
