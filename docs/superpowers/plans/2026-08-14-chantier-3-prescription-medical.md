# Chantier 3 — Fenêtre médicale, Étape 2 : Prescription (CRUD complet) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner à `medecin`/`nurse` un module Prescription complet (liste + création/édition + suppression) dans leur fenêtre médicale, port fidèle de `PrescriptionFormView`/`PrescriptionListView` (`view_pyqt6/prescription_views/`) côté desktop.

**Architecture:** Nouvelle section de navigation "Prescription" dans `MedicalLayout.vue` (déjà construit à l'Étape 1), route `/medical/prescriptions`, store Pinia + gateway dédiés (même convention qu'`appointmentStore.js`/`AppointmentGateway.js`), une liste avec recherche/filtre de dates/pagination, et une modale de création/édition qui bascule entre mode "médicament" et mode "bon d'examen laboratoire" (`is_lab_order`), avec recherche patient par code (même pattern anti-race déjà validé sur `AppointmentModal.vue`) et sélection multiple d'examens via le catalogue réel `GET /labo/exams`.

**Tech Stack:** Vue 3 (Composition API, `<script setup>`), Pinia, vue-router 4, vue-i18n, Tailwind CSS, axios (`src/services/api.js`). Backend FastAPI déjà complet et correct pour ce module (`api_backend/backend_app/routes/prescription/prescriptions_endpoints.py` : `GET/POST/PUT/DELETE /prescriptions/`, déjà RBAC `medecin`/`nurse`/`admin`/`manager` — aucune modification backend nécessaire dans ce plan). Pas de framework de test frontend configuré (`package.json` n'a que `dev`/`build`/`preview`) — vérification via `npm run build` + test manuel navigateur.

**Spec:** `docs/superpowers/specs/2026-08-13-chantier-3-fenetre-medicale-design.md`

## Global Constraints

- **Le champ identifiant d'une prescription dans les réponses API est `prescription_id`, PAS `id`.** C'est différent du module Rendez-vous (Étape 1) où c'est `id` — vérifié dans `api_backend/backend_app/routes/prescription/prescriptions_schemas.py:129` (`class PrescriptionResponse(PrescriptionBase): prescription_id: int`). Toute référence à l'identifiant d'une prescription dans le code de ce plan (clé `:key`, appels `updatePrescription`/`deletePrescription`) doit utiliser `prescription_id`.
- `lab_exams_list` est un vrai tableau JSON côté backend (`List[str]`, noms d'examens, pas des ids) — l'envoyer directement comme tableau, ne pas répliquer le hack "chaîne séparée par des virgules" du client desktop (celui-ci n'existe que pour compatibilité ascendante côté backend, voir `prescriptions_schemas.py:29-51`).
- `GET /labo/exams` est le catalogue réel d'examens, déjà accessible à `medecin`/`nurse` (`api_backend/backend_app/routes/labo/lab_endpoints.py:62-69`, commentaire "ACCÈS ÉLARGI : Permet au personnel de soins de voir la liste pour prescrire") — l'utiliser au lieu d'une liste codée en dur.
- `PrescriptionCreate` exige que les clés `medication`/`dosage`/`frequency`/`duration` soient présentes dans le payload (même avec une valeur `null`) — ne jamais omettre ces clés, y compris pour un bon d'examen (le backend les remplit automatiquement à `"N/A"`/`"DEMANDE D'EXAMEN"` si `is_lab_order=true` et qu'elles sont vides).
- Le champ `medical_record_id` (référence dossier médical) est volontairement omis de l'interface dans ce plan (toujours envoyé `null`) : c'est un champ optionnel dont la vraie source (le Dossier Médical, Étape 3 du chantier) n'existe pas encore côté web — à raccorder plus tard si besoin, pas maintenant (YAGNI).
- **Ne rien committer.** Comme pour l'Étape 1, tous les fichiers modifiés (`router/index.js`, `i18n.js`, `MedicalLayout.vue`) sont déjà en WIP non commité de l'utilisateur ou destinés à le rester ; les nouveaux fichiers de ce plan aussi. Aucune étape ne doit exécuter `git add`/`git commit`.
- Pas de bouton "imprimer"/PDF pour les prescriptions — confirmé absent du client desktop lui-même (aucune génération PDF trouvée pour les prescriptions), donc hors périmètre ici aussi.
- `MainLayout.vue` n'est pas touché par ce plan (même contrainte qu'à l'Étape 1).

---

### Task 1 : Clés i18n du module Prescription

**Files:**
- Modify: `ah2-admin-web/src/i18n.js`
- Test: manuel (pas de framework de test frontend) — voir Step 2

**Interfaces:**
- Consumes: rien (tâche indépendante, pure donnée).
- Produces: le bloc `prescriptions.*` complet (fr + en) que les Tasks 2-4 consomment via `t('prescriptions.xxx')`. Clés exactes listées ci-dessous — les tâches suivantes les utilisent verbatim, ne pas en inventer d'autres à la volée dans le code sans les ajouter ici d'abord.

- [ ] **Step 1 : Ajouter le bloc `prescriptions` au français et à l'anglais**

Dans `ah2-admin-web/src/i18n.js`, le bloc `appointments` du français se termine ainsi (repère exact à chercher, ne pas se fier aux numéros de ligne qui ont pu dériver) :

```js
      actions: {
        complete: "Compléter",
        cancel: "Refuser",
        edit: "Éditer"
      },
      modal: {
        title_new: "Nouveau Rendez-vous",
        title_edit: "Modifier le Rendez-vous",
        patient_code: "Code Patient",
        specialty: "Spécialité",
        specialty_none: "-- Aucune --",
        date: "Date",
        time: "Heure",
        reason: "Motif",
        cancel: "Annuler",
        save: "Enregistrer",
        patient_not_found: "Patient introuvable"
      }
    },
    finance: {
```

Insérer un nouveau bloc `prescriptions` juste après la fermeture du bloc `appointments` (après le `},` qui suit `patient_not_found: "Patient introuvable"` de la section `modal`) et juste avant `finance: {` :

```js
    prescriptions: {
      title: "Prescriptions",
      subtitle: "Ordonnances et bons d'examen",
      new_prescription: "Nouvelle Prescription",
      search_label: "Recherche",
      search_placeholder: "Rechercher code patient ou médicament...",
      date_from: "Du",
      date_to: "Au",
      results_count: "prescriptions trouvées",
      empty: "Aucune prescription trouvée pour ces critères.",
      confirm_delete: "Supprimer cette prescription ?",
      table: {
        patient: "Patient",
        content: "Prescription",
        duration: "Durée",
        start_date: "Début",
        end_date: "Fin",
        prescriber: "Prescripteur",
        actions: "Actions",
        lab_order_badge: "Bon d'examen"
      },
      actions: {
        edit: "Éditer",
        delete: "Supprimer"
      },
      modal: {
        title_new: "Nouvelle Prescription",
        title_edit: "Modifier la Prescription",
        patient_code: "Code Patient",
        is_lab_order: "Ceci est une demande d'examen (Laboratoire)",
        medication: "Médicament",
        dosage: "Dosage",
        frequency: "Fréquence",
        duration: "Durée",
        start_date: "Date de début",
        end_date: "Date de fin",
        exams: "Examens",
        exams_filter: "Filtrer les examens...",
        exams_empty: "Aucun examen disponible.",
        notes: "Notes",
        cancel: "Annuler",
        save: "Enregistrer",
        patient_not_found: "Patient introuvable",
        medication_required: "Le nom du médicament est requis.",
        exams_required: "Sélectionnez au moins un examen.",
        date_order_error: "La date de fin doit être postérieure ou égale à la date de début."
      }
    },
```

Le bloc `appointments` de l'anglais se termine de façon symétrique (mêmes clés, valeurs anglaises), suivi de `finance: {`. Insérer là aussi, au même endroit relatif (après la fermeture du bloc `appointments` anglais, avant `finance: {` anglais) :

```js
    prescriptions: {
      title: "Prescriptions",
      subtitle: "Prescriptions and lab orders",
      new_prescription: "New Prescription",
      search_label: "Search",
      search_placeholder: "Search patient code or medication...",
      date_from: "From",
      date_to: "To",
      results_count: "prescriptions found",
      empty: "No prescriptions found for these criteria.",
      confirm_delete: "Delete this prescription?",
      table: {
        patient: "Patient",
        content: "Prescription",
        duration: "Duration",
        start_date: "Start",
        end_date: "End",
        prescriber: "Prescriber",
        actions: "Actions",
        lab_order_badge: "Lab order"
      },
      actions: {
        edit: "Edit",
        delete: "Delete"
      },
      modal: {
        title_new: "New Prescription",
        title_edit: "Edit Prescription",
        patient_code: "Patient Code",
        is_lab_order: "This is a lab order",
        medication: "Medication",
        dosage: "Dosage",
        frequency: "Frequency",
        duration: "Duration",
        start_date: "Start date",
        end_date: "End date",
        exams: "Exams",
        exams_filter: "Filter exams...",
        exams_empty: "No exams available.",
        notes: "Notes",
        cancel: "Cancel",
        save: "Save",
        patient_not_found: "Patient not found",
        medication_required: "Medication name is required.",
        exams_required: "Select at least one exam.",
        date_order_error: "End date must be on or after start date."
      }
    },
```

Il doit y avoir exactement deux blocs `prescriptions:` dans le fichier au total (un dans la section `fr`, un dans la section `en`) — le fichier a déjà cette structure à deux sections pour tous les autres modules (`appointments`, `finance`, etc.), suivre le même schéma.

- [ ] **Step 2 : Vérifier la compilation**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur (JSON/JS valide, pas de virgule manquante).

- [ ] **Step 3 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Passer à la tâche suivante.

---

### Task 2 : `PrescriptionGateway.js` + `prescriptionStore.js`

**Files:**
- Create: `ah2-admin-web/src/services/PrescriptionGateway.js`
- Create: `ah2-admin-web/src/stores/prescriptionStore.js`
- Test: manuel (pas de framework de test frontend) — voir Step 3

**Interfaces:**
- Consumes: `api` (`src/services/api.js`, instance axios partagée), endpoints backend déjà existants et corrects : `GET /prescriptions/` (params `page`/`per_page`/`search`/`date_from`/`date_to`), `GET /labo/exams`, `POST /prescriptions/`, `PUT /prescriptions/{id}`, `DELETE /prescriptions/{id}`.
- Produces: `PrescriptionGateway` avec les méthodes `fetchPrescriptions(params)`, `fetchExamTypes()`, `createPrescription(data)`, `updatePrescription(prescriptionId, data)`, `deletePrescription(prescriptionId)` — signatures exactes ci-dessous. `usePrescriptionStore()` exposant `prescriptions`, `examTypes`, `isLoading`, `filters`, `pagination`, `fetchPrescriptions()`, `fetchExamTypes()`, `createPrescription(data)`, `updatePrescription(prescriptionId, data)`, `deletePrescription(prescriptionId)`, `setPage(page)`, `setFilters(newFilters)` — la Task 3 (modale) et la Task 4 (liste) consomment exactement ces noms.
- Le paramètre `data` de `createPrescription`/`updatePrescription` (côté gateway ET côté store, même forme) est un objet `{ patientId, medicalRecordId, isLabOrder, medication, dosage, frequency, duration, startDate, endDate, notes, labExamsList }` — ce sont exactement les clés que la modale de la Task 3 émettra dans son événement `save`.

- [ ] **Step 1 : Créer `PrescriptionGateway.js`**

Créer `ah2-admin-web/src/services/PrescriptionGateway.js` avec ce contenu exact :

```js
import api from '@/services/api';

// Nettoie les paramètres vides avant envoi (évite un 422 sur des query
// params vides) - meme convention que AppointmentGateway.js/FinanceGateway.js.
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

export const PrescriptionGateway = {

    async fetchPrescriptions(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            search: params.searchQuery,
            date_from: params.dateFrom,
            date_to: params.dateTo,
        };
        return api.get('/prescriptions/', { params: cleanParams(rawQuery) });
    },

    // Catalogue reel d'examens, deja accessible a medecin/nurse (voir
    // lab_endpoints.py:62-69, "ACCES ELARGI... pour prescrire") - pas de
    // liste codee en dur cote web.
    async fetchExamTypes() {
        return api.get('/labo/exams');
    },

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
        };
        return api.post('/prescriptions/', payload);
    },

    async updatePrescription(prescriptionId, data) {
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
        };
        return api.put(`/prescriptions/${prescriptionId}`, payload);
    },

    async deletePrescription(prescriptionId) {
        return api.delete(`/prescriptions/${prescriptionId}`);
    },
};
```

- [ ] **Step 2 : Créer `prescriptionStore.js`**

Créer `ah2-admin-web/src/stores/prescriptionStore.js` avec ce contenu exact :

```js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { PrescriptionGateway } from '@/services/PrescriptionGateway';

export const usePrescriptionStore = defineStore('prescription', () => {

    // --- ÉTAT ---
    const prescriptions = ref([]);
    const examTypes = ref([]);
    const isLoading = ref(false);
    const totalItems = ref(0);

    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        dateFrom: '',
        dateTo: '',
    });

    // --- ACTIONS ---

    async function fetchPrescriptions() {
        isLoading.value = true;
        try {
            const params = {
                page: filters.value.page,
                per_page: filters.value.per_page,
                searchQuery: filters.value.searchQuery,
                dateFrom: filters.value.dateFrom,
                dateTo: filters.value.dateTo,
            };

            const res = await PrescriptionGateway.fetchPrescriptions(params);
            prescriptions.value = res.data.data || [];
            totalItems.value = res.data.total || 0;
        } catch (err) {
            console.error('Erreur chargement prescriptions:', err);
            prescriptions.value = [];
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchExamTypes() {
        try {
            const res = await PrescriptionGateway.fetchExamTypes();
            examTypes.value = res.data || [];
        } catch (err) {
            console.error('Erreur chargement types examens:', err);
            examTypes.value = [];
        }
    }

    async function createPrescription(data) {
        await PrescriptionGateway.createPrescription(data);
        filters.value.page = 1;
        await fetchPrescriptions();
    }

    async function updatePrescription(prescriptionId, data) {
        await PrescriptionGateway.updatePrescription(prescriptionId, data);
        await fetchPrescriptions();
    }

    async function deletePrescription(prescriptionId) {
        await PrescriptionGateway.deletePrescription(prescriptionId);
        await fetchPrescriptions();
    }

    function setPage(page) {
        filters.value.page = page;
        fetchPrescriptions();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchPrescriptions();
    }

    // --- GETTERS ---
    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1,
    }));

    return {
        prescriptions,
        examTypes,
        isLoading,
        filters,
        pagination,
        fetchPrescriptions,
        fetchExamTypes,
        createPrescription,
        updatePrescription,
        deletePrescription,
        setPage,
        setFilters,
    };
});
```

- [ ] **Step 3 : Vérifier la compilation**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur.

- [ ] **Step 4 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Passer à la tâche suivante.

---

### Task 3 : `PrescriptionModal.vue` (création/édition, bascule médicament/examen)

**Files:**
- Create: `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue`
- Test: manuel (pas de framework de test frontend) — voir Step 2. Note : ce fichier n'est encore référencé par aucune vue à ce stade (Task 4 le fait) — `npm run build` ne le compile donc pas via l'arbre d'imports. Si un outil `@vue/compiler-sfc` est disponible dans le projet, l'utiliser pour valider la syntaxe du fichier isolément ; sinon, une relecture attentive du fichier après création suffit, la Task 4 exercera réellement sa compilation.

**Interfaces:**
- Consumes: `usePrescriptionStore` (Task 2 — `examTypes`, `fetchExamTypes()`), `api` (`src/services/api.js`), endpoint `GET /patients/` avec `search` (même contrat que `AppointmentModal.vue`, déjà vérifié : réponse `Array.isArray(resData) ? resData : (resData.data || [])`, champs `id`/`patient_id`, `code_patient`, `first_name`, `last_name`), clés i18n `prescriptions.modal.*` (Task 1).
- Produces: composant `PrescriptionModal.vue` avec `props: { prescription: Object|null }` (`null`/absent = création, objet = édition) et `emits: ['close', 'save']`. Le payload `save` est exactement `{ patientId, medicalRecordId, isLabOrder, medication, dosage, frequency, duration, startDate, endDate, notes, labExamsList }` — la Task 4 le passe tel quel à `prescriptionStore.createPrescription(data)`/`updatePrescription(id, data)` (Task 2), dont le gateway attend précisément ces clés.

- [ ] **Step 1 : Créer `PrescriptionModal.vue`**

Créer `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue` avec ce contenu exact :

```vue
<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-lg shadow-xl rounded-2xl bg-white">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('prescriptions.modal.title_edit') : t('prescriptions.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            placeholder="Ex: AH2-000818AQ"
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
          />
          <p class="mt-1 text-xs" :class="patientId ? 'text-emerald-600' : 'text-gray-400'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div class="flex items-center">
          <input
            id="is_lab_order"
            v-model="form.isLabOrder"
            type="checkbox"
            class="h-4 w-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
          />
          <label for="is_lab_order" class="ml-2 block text-sm text-gray-700">
            {{ t('prescriptions.modal.is_lab_order') }}
          </label>
        </div>

        <template v-if="!form.isLabOrder">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.medication') }}</label>
            <input
              v-model="form.medication"
              type="text"
              required
              placeholder="Ex: Paracétamol 1000mg"
              class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.dosage') }}</label>
              <input
                v-model="form.dosage"
                type="text"
                placeholder="Ex: 1000mg"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.frequency') }}</label>
              <input
                v-model="form.frequency"
                type="text"
                placeholder="Ex: 3x / jour"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.duration') }}</label>
              <input
                v-model="form.duration"
                type="text"
                placeholder="Ex: 7 jours"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.end_date') }}</label>
              <input
                v-model="form.endDate"
                type="date"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
          </div>
        </template>

        <template v-else>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.exams') }}</label>
            <input
              v-model="examFilter"
              type="text"
              :placeholder="t('prescriptions.modal.exams_filter')"
              class="block w-full px-3 py-2 border border-gray-300 rounded-lg mb-2 focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
            />
            <div class="max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-2 space-y-1">
              <label v-for="exam in filteredExamTypes" :key="exam.id" class="flex items-center text-sm py-0.5">
                <input
                  type="checkbox"
                  :value="exam.nom"
                  v-model="form.labExamsList"
                  class="h-4 w-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-2"
                />
                {{ exam.nom }}
              </label>
              <p v-if="filteredExamTypes.length === 0" class="text-xs text-gray-400 italic py-1">
                {{ t('prescriptions.modal.exams_empty') }}
              </p>
            </div>
          </div>
        </template>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.start_date') }}</label>
          <input
            v-model="form.startDate"
            type="date"
            required
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.notes') }}</label>
          <textarea
            v-model="form.notes"
            rows="2"
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
          ></textarea>
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-sm">
            {{ t('prescriptions.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition bg-purple-600 hover:bg-purple-700">
            {{ t('prescriptions.modal.save') }}
          </button>
        </div>
      </form>

    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { usePrescriptionStore } from '@/stores/prescriptionStore';

const { t } = useI18n();
const prescriptionStore = usePrescriptionStore();
const emit = defineEmits(['close', 'save']);

const props = defineProps({
  prescription: {
    type: Object,
    default: null,
  },
});

const isEdit = computed(() => !!props.prescription);

const patientCode = ref('');
const patientId = ref(null);
const patientName = ref('');
const patientLookupMessage = ref('');
const examFilter = ref('');

const today = new Date().toISOString().substring(0, 10);

const form = reactive({
  isLabOrder: false,
  medication: '',
  dosage: '',
  frequency: '',
  duration: '',
  startDate: today,
  endDate: '',
  notes: '',
  labExamsList: [],
});

const filteredExamTypes = computed(() => {
  const q = examFilter.value.trim().toLowerCase();
  if (!q) return prescriptionStore.examTypes;
  return prescriptionStore.examTypes.filter((e) => e.nom.toLowerCase().includes(q));
});

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
        patientLookupMessage.value = t('prescriptions.modal.patient_not_found');
        return;
      }

      patientId.value = match.id || match.patient_id;
      patientName.value = [match.first_name, match.last_name].filter(Boolean).join(' ');
      patientLookupMessage.value = patientName.value;
    } catch (err) {
      console.error('Erreur recherche patient:', err);
      patientId.value = null;
      patientName.value = '';
      patientLookupMessage.value = t('prescriptions.modal.patient_not_found');
    }
  })();

  await pendingLookup;
}

onMounted(() => {
  if (!prescriptionStore.examTypes.length) {
    prescriptionStore.fetchExamTypes();
  }

  if (props.prescription) {
    const presc = props.prescription;
    patientId.value = presc.patient_id || presc.patient?.patient_id || null;
    patientCode.value = presc.patient?.code_patient || '';
    patientName.value = [presc.patient?.first_name, presc.patient?.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
    form.isLabOrder = !!presc.is_lab_order;
    form.medication = presc.medication || '';
    form.dosage = presc.dosage || '';
    form.frequency = presc.frequency || '';
    form.duration = presc.duration || '';
    form.startDate = (presc.start_date || '').substring(0, 10);
    form.endDate = (presc.end_date || '').substring(0, 10);
    form.notes = presc.notes || '';
    form.labExamsList = Array.isArray(presc.lab_exams_list) ? [...presc.lab_exams_list] : [];
  }
});

async function handleSubmit() {
  if (pendingLookup) {
    await pendingLookup;
  } else if (!patientId.value && patientCode.value.trim()) {
    await lookupPatient();
  }

  if (!patientId.value) {
    alert(t('prescriptions.modal.patient_not_found'));
    return;
  }

  if (!form.isLabOrder && !form.medication.trim()) {
    alert(t('prescriptions.modal.medication_required'));
    return;
  }

  if (form.isLabOrder && form.labExamsList.length === 0) {
    alert(t('prescriptions.modal.exams_required'));
    return;
  }

  if (!form.isLabOrder && form.endDate && form.startDate > form.endDate) {
    alert(t('prescriptions.modal.date_order_error'));
    return;
  }

  emit('save', {
    patientId: patientId.value,
    medicalRecordId: null,
    isLabOrder: form.isLabOrder,
    medication: form.isLabOrder ? '' : form.medication,
    dosage: form.isLabOrder ? '' : form.dosage,
    frequency: form.isLabOrder ? '' : form.frequency,
    duration: form.isLabOrder ? '' : form.duration,
    startDate: form.startDate,
    endDate: form.isLabOrder ? '' : form.endDate,
    notes: form.notes,
    labExamsList: form.isLabOrder ? form.labExamsList : [],
  });
}
</script>
```

- [ ] **Step 2 : Relecture de syntaxe**

Relire le fichier créé en entier pour vérifier : balises `<template>`/`<script setup>` bien fermées, pas de `v-model` orphelin, cohérence des accolades dans les blocs `<template v-if>`/`<template v-else>`. Si le projet a `@vue/compiler-sfc` installé (vérifier avec `cd ah2-admin-web && npm ls @vue/compiler-sfc`), l'utiliser pour parser le fichier isolément et confirmer l'absence d'erreur de syntaxe ; sinon, la relecture manuelle suffit pour cette étape (la Task 4 validera la compilation réelle en impliquant ce fichier dans l'arbre d'imports).

- [ ] **Step 3 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Passer à la tâche suivante.

---

### Task 4 : `PrescriptionsList.vue` + navigation + route

**Files:**
- Create: `ah2-admin-web/src/views/modules/prescriptions/PrescriptionsList.vue`
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue`
- Modify: `ah2-admin-web/src/router/index.js`
- Test: manuel (pas de framework de test frontend) — voir Step 4

**Interfaces:**
- Consumes: `usePrescriptionStore` (Task 2), `PrescriptionModal.vue` (Task 3 — `props: { prescription }`, `emits: ['close', 'save']`, payload exact décrit dans la Task 3), clés i18n `prescriptions.*` (Task 1).
- Produces: parcours complet liste + création/édition + suppression de prescriptions, accessible depuis la navigation de `MedicalLayout.vue` — dernière tâche du plan, rien n'en dépend davantage.

- [ ] **Step 1 : Créer `PrescriptionsList.vue`**

Créer `ah2-admin-web/src/views/modules/prescriptions/PrescriptionsList.vue` avec ce contenu exact :

```vue
<template>
  <div class="space-y-6 w-full">

    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('prescriptions.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('prescriptions.subtitle') }}</p>
      </div>

      <button
        @click="openCreateModal"
        class="flex items-center px-6 py-2.5 bg-purple-600 text-white rounded-xl hover:bg-purple-700 shadow-md shadow-purple-200 transition font-semibold"
      >
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('prescriptions.new_prescription') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">

      <div class="flex-1 min-w-[220px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('prescriptions.search_label') }}</label>
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
          </div>
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('prescriptions.search_placeholder')"
            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
          >
        </div>
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('prescriptions.date_from') }}</label>
        <input v-model="dateFrom" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm" />
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('prescriptions.date_to') }}</label>
        <input v-model="dateTo" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm" />
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

      <div class="p-4 border-b border-gray-100 flex items-center justify-between">
        <div class="text-sm text-gray-500">
          {{ prescriptionStore.pagination.total }} {{ t('prescriptions.results_count') }}
        </div>
      </div>

      <div v-if="prescriptionStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></span>
        <p class="mt-2 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.content') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.duration') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.start_date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.end_date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.prescriber') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('prescriptions.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="presc in prescriptionStore.prescriptions" :key="presc.prescription_id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900">{{ patientName(presc) }}</div>
                <div class="text-xs text-gray-500">{{ presc.patient?.code_patient }}</div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">
                <template v-if="presc.is_lab_order">
                  <span class="font-semibold text-purple-800">{{ t('prescriptions.table.lab_order_badge') }}</span>
                  <div class="text-xs text-gray-500">{{ (presc.lab_exams_list || []).join(', ') || '—' }}</div>
                </template>
                <template v-else>
                  <span class="font-semibold text-gray-800">{{ presc.medication }}</span>
                  <div class="text-xs text-gray-500">{{ presc.dosage }} — {{ presc.frequency }}</div>
                </template>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ presc.is_lab_order ? '—' : (presc.duration || '—') }}</td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ presc.start_date }}</td>
              <td class="px-6 py-4 text-sm font-mono">
                <span v-if="!presc.is_lab_order && presc.end_date" class="px-2 py-1 rounded" :class="endDateUrgencyClass(presc)">
                  {{ presc.end_date }}
                </span>
                <span v-else class="text-gray-400">—</span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ presc.prescribed_by_name || '—' }}</td>
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <button
                    @click="openEditModal(presc)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
                  >
                    {{ t('prescriptions.actions.edit') }}
                  </button>
                  <button
                    @click="handleDelete(presc)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition"
                  >
                    {{ t('prescriptions.actions.delete') }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="prescriptionStore.prescriptions.length === 0">
              <td colspan="7" class="px-6 py-8 text-center text-gray-500 italic">
                {{ t('prescriptions.empty') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="prescriptionStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">
          {{ t('common.page') }} {{ prescriptionStore.pagination.page }} / {{ prescriptionStore.pagination.total_pages }}
        </p>
        <div class="flex space-x-2">
          <button @click="goToPage(prescriptionStore.pagination.page - 1)" :disabled="prescriptionStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(prescriptionStore.pagination.page + 1)" :disabled="prescriptionStore.pagination.page === prescriptionStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>

    </div>

    <PrescriptionModal
      v-if="showModal"
      :prescription="editingPrescription"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { usePrescriptionStore } from '@/stores/prescriptionStore';
import { useI18n } from 'vue-i18n';
import PrescriptionModal from '@/components/prescriptions/PrescriptionModal.vue';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const prescriptionStore = usePrescriptionStore();

onMounted(() => {
  prescriptionStore.fetchPrescriptions();
  prescriptionStore.fetchExamTypes();
});

const searchQuery = computed({
  get: () => prescriptionStore.filters.searchQuery,
  set: (val) => prescriptionStore.setFilters({ searchQuery: val }),
});

const dateFrom = computed({
  get: () => prescriptionStore.filters.dateFrom,
  set: (val) => prescriptionStore.setFilters({ dateFrom: val }),
});

const dateTo = computed({
  get: () => prescriptionStore.filters.dateTo,
  set: (val) => prescriptionStore.setFilters({ dateTo: val }),
});

function goToPage(page) {
  if (page >= 1 && page <= prescriptionStore.pagination.total_pages) {
    prescriptionStore.setPage(page);
  }
}

function patientName(presc) {
  const p = presc.patient;
  if (!p) return '—';
  return [p.first_name, p.last_name].filter(Boolean).join(' ');
}

// Coloration "urgence de renouvellement" sur la date de fin - port exact
// de la logique desktop (prescription_list.py) : gris si echue, rouge
// <=3j, orange <=7j, jaune <=14j, vert au-dela. Uniquement pertinent pour
// les prescriptions medicamenteuses (les bons d'examen n'ont pas de date
// de fin, voir le v-if qui encadre l'appel a cette fonction).
function endDateUrgencyClass(presc) {
  const end = new Date(presc.end_date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.floor((end - today) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return 'bg-gray-100 text-gray-500';
  if (diffDays <= 3) return 'bg-red-100 text-red-700 font-semibold';
  if (diffDays <= 7) return 'bg-orange-100 text-orange-700 font-semibold';
  if (diffDays <= 14) return 'bg-yellow-100 text-yellow-700';
  return 'bg-emerald-50 text-emerald-700';
}

const showModal = ref(false);
const editingPrescription = ref(null);

function openCreateModal() {
  editingPrescription.value = null;
  showModal.value = true;
}

function openEditModal(presc) {
  editingPrescription.value = presc;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingPrescription.value = null;
}

async function handleSave(data) {
  try {
    if (editingPrescription.value) {
      await prescriptionStore.updatePrescription(editingPrescription.value.prescription_id, data);
    } else {
      await prescriptionStore.createPrescription(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement prescription:', err);
    alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
  }
}

async function handleDelete(presc) {
  if (!confirm(t('prescriptions.confirm_delete'))) return;
  try {
    await prescriptionStore.deletePrescription(presc.prescription_id);
  } catch (err) {
    console.error('Erreur suppression prescription:', err);
    alert('Erreur lors de la suppression : ' + (err.response?.data?.detail || err.message));
  }
}
</script>
```

Noter que `:key="presc.prescription_id"` et les deux appels `prescriptionStore.updatePrescription(editingPrescription.value.prescription_id, data)` / `prescriptionStore.deletePrescription(presc.prescription_id)` utilisent bien `prescription_id`, pas `id` — voir Global Constraints.

- [ ] **Step 2 : Ajouter l'entrée de navigation "Prescription" dans `MedicalLayout.vue`**

Dans `ah2-admin-web/src/components/layout/MedicalLayout.vue`, l'import d'icônes actuel est :

```js
import {
  CalendarIcon,
  Bars3Icon,
  Bars3CenterLeftIcon
} from '@heroicons/vue/24/outline';
```

Le remplacer par (ajout de `TagIcon`, déjà utilisé pour le même concept "traitements/pharma" dans `PatientDetailView.vue`) :

```js
import {
  CalendarIcon,
  TagIcon,
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
];
```

- [ ] **Step 3 : Ajouter la route `/medical/prescriptions` dans `router/index.js`**

Dans `ah2-admin-web/src/router/index.js`, à l'intérieur du bloc `/medical` (ajouté à l'Étape 1), le tableau `children` contient actuellement :

```js
    children: [
      {
        path: '',
        redirect: '/medical/appointments'
      },
      {
        path: 'appointments',
        name: 'medical-appointments',
        component: () => import('@/views/modules/appointments/AppointmentsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      }
    ]
```

Ajouter une nouvelle route enfant après `appointments`, avant la fermeture du tableau `children` :

```js
    children: [
      {
        path: '',
        redirect: '/medical/appointments'
      },
      {
        path: 'appointments',
        name: 'medical-appointments',
        component: () => import('@/views/modules/appointments/AppointmentsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'prescriptions',
        name: 'medical-prescriptions',
        component: () => import('@/views/modules/prescriptions/PrescriptionsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      }
    ]
```

Ne pas toucher au reste du fichier (le bloc `/dashboard` existant, les routes de secours).

- [ ] **Step 4 : Vérifier la compilation et tester manuellement**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur ; le graphe d'imports compile maintenant réellement `PrescriptionModal.vue` (via `PrescriptionsList.vue`) pour la première fois — traiter toute erreur de compilation dans ce fichier comme relevant de cette étape, même si le code lui-même vient de la Task 3.

Test manuel (connecté en tant que `medecin`/`nurse`) :
1. Dans la sidebar de `MedicalLayout.vue`, une deuxième entrée "Prescriptions" apparaît sous "Rendez-vous" — cliquer dessus mène à `/medical/prescriptions`.
2. Cliquer "Nouvelle Prescription" → la modale s'ouvre en mode médicament par défaut (case "demande d'examen" décochée), date de début pré-remplie à aujourd'hui.
3. Saisir un code patient existant, sortir du champ → le nom s'affiche en vert. Remplir médicament/dosage/fréquence/durée, enregistrer → la prescription apparaît dans la liste avec le médicament et la coloration de la date de fin (si elle est proche, la cellule doit être rouge/orange/jaune selon le nombre de jours restants).
4. Cocher "Ceci est une demande d'examen" → les champs médicament/dosage/fréquence/durée/date fin disparaissent, la liste d'examens (chargée depuis `GET /labo/exams`) apparaît avec un filtre de recherche. Cocher 2-3 examens, enregistrer → la prescription apparaît dans la liste avec le badge "Bon d'examen" et la liste des examens choisis, sans coloration de date de fin.
5. Cliquer "Éditer" sur une prescription existante → la modale s'ouvre pré-remplie (patient, mode médicament/examen, tous les champs pertinents).
6. Cliquer "Supprimer" sur une prescription → une confirmation apparaît ; confirmer → la prescription disparaît de la liste.
7. Tester le filtre de recherche et les filtres de date (Du/Au) sur la liste.

- [ ] **Step 5 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Ceci termine l'Étape 2 (Prescription) du chantier 3 — rapporter l'état à l'utilisateur pour relecture avant de passer à l'Étape 3 (Dossier Médical) de la spec.
