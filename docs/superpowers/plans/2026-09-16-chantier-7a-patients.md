# Chantier 7a — Formulaire patient (création/modification/suppression) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L'application web gagne un vrai formulaire de création/modification/suppression de patient — aujourd'hui totalement absent (le seul chemin de création est un effet de bord de l'admission toxicologique).

**Architecture:** Un composant modal réutilisé pour création et modification (`PatientModal.vue`, calqué sur `UserModal.vue`), câblé à `PatientList.vue` (bouton « Ajouter », icônes crayon/poubelle par ligne, patron `UserManagement.vue`). La modale n'appelle jamais l'API elle-même — elle émet `save`, le parent fait l'appel via `patientStore.js` et lui renvoie l'état de chargement/erreur par props. Un correctif backend ciblé accompagne le tout : `PatientController.update_patient` perd un bloc de code mort qui dupliquait, de façon confuse, une protection déjà assurée par la procédure stockée PostgreSQL (`COALESCE` sur les 3 colonnes de drapeaux).

**Tech Stack:** FastAPI + SQLAlchemy (endpoints déjà existants, aucune migration), Vue 3 Composition API + Pinia, pytest avec fixtures `db_session`/`api_client` (intégration réelle contre PostgreSQL local `AH2`).

**Spec:** `docs/superpowers/specs/2026-09-16-chantier-7a-patients-design.md`

## Global Constraints

- Aucune migration de schéma — toutes les colonnes/endpoints nécessaires existent déjà.
- Aucun export (CSV/PDF) dans ce sous-projet — hors périmètre, décidé explicitement.
- Aucun travail hors ligne dans ce sous-projet — chaque sous-projet du chantier 7 statue sur son passage hors-ligne séparément, une fois fonctionnel en ligne.
- Les 3 drapeaux de domaine (`is_clinical`/`is_toxicology`/`is_spiritual`) ne sont **jamais** envoyés par le formulaire patient — depuis le chantier 6, ils ne sont plus une source de vérité (calculés à la lecture).
- Le bouton « Ajouter un patient » et les icônes crayon/poubelle sont visibles pour exactement les 6 rôles déjà autorisés côté backend sur ce routeur : `medecin, nurse, secretaire, admin, manager, Assistant` (casse exacte des `role_name` réels en base, vérifiée — `Assistant` porte une majuscule, les 5 autres non ; `manager` n'a aucune ligne en base aujourd'hui mais reste dans la liste, réservé).
- Aucun commit git à aucune étape sans accord explicite et frais de l'utilisateur à ce moment précis.

---

### Task 1: Simplification backend — `PatientController.update_patient`

**Files:**
- Modify: `controller/patient_controller.py:106-147`
- Modify: `tests/test_patients.py:98-116` (remplace un test actuellement en échec documenté)

**Interfaces:**
- Consumes: `PatientRepository.update_patient(patient_id, data, current_user)` (déjà existant, inchangé — fait `data.get('is_X')` et laisse la procédure stockée `public.update_patient` faire `COALESCE(p_is_X, is_X)` si `None`).
- Produces: `PatientController.update_patient(patient_id, data)` ne construit plus les clés `is_clinical`/`is_toxicology`/`is_spiritual` dans `data` — le dict passé au dépôt ne contient ces clés que si l'appelant les a explicitement envoyées. Signature inchangée, consommée telle quelle par `sync_simple_patient_update` (Task 2) et par l'endpoint `PUT /patients/{id}` (inchangé, hors périmètre de ce plan).

- [ ] **Step 1: Lancer le test actuellement en échec, confirmer l'échec et sa cause réelle**

Run: `pytest tests/test_patients.py::test_update_patient_flag_protection_prevents_any_change -v`
Expected: FAIL — `assert resp.json()["is_toxicology"] is False` échoue car la réponse renvoie `True`. La docstring de ce test décrit un bug d'une version antérieure du code (`user_app_role` toujours vide) qui ne correspond plus au code réel actuel (`_get_user_roles_set()`/`is_admin`/`is_toxico` — un admin peut aujourd'hui changer ce champ avec succès, le test documente un état déjà dépassé).

- [ ] **Step 2: Remplacer ce test par un test qui documente le comportement réel actuel (avant la simplification)**

Dans `tests/test_patients.py`, remplacer les lignes 98-116 (la fonction `test_update_patient_flag_protection_prevents_any_change` et sa docstring) par :

```python
def test_update_patient_toxicology_flag_reflects_the_stored_procedure(db_session, api_client):
    """La procedure stockee public.update_patient (ci/schema_only.sql)
    fait COALESCE(p_is_toxicology, is_toxicology) - un appelant autorise
    qui envoie explicitement une nouvelle valeur la voit appliquee. Le
    bloc Python qui pretendait proteger ce champ (retire par ce chantier,
    voir la spec chantier 7a) etait redondant avec cette protection deja
    assuree par la base, et cachait ce comportement reel derriere une
    logique de roles confuse et partiellement obsolete (roles 'app_*' qui
    ne correspondent a aucun role reel du systeme depuis le chantier 6)."""
    user = create_test_user(db_session, "test_patients_admin_flag2", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, is_toxicology=False)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_flag2", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"is_toxicology": True}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["is_toxicology"] is True


def test_update_patient_sans_drapeaux_les_laisse_inchanges(db_session, api_client):
    """Le formulaire patient (chantier 7a) n'envoie jamais les 3 drapeaux
    de domaine - une mise a jour classique (juste le telephone, par
    exemple) ne doit avoir aucun effet sur eux, exactement comme avant la
    simplification (COALESCE(None, is_X) preserve la valeur existante)."""
    user = create_test_user(db_session, "test_patients_admin_flag3", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, is_toxicology=True, is_clinical=False, is_spiritual=False)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_flag3", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"contact_phone": "+237600000000"}, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_toxicology"] is True
    assert body["is_clinical"] is False
    assert body["is_spiritual"] is False
    assert body["contact_phone"] == "+237600000000"
```

- [ ] **Step 3: Lancer les deux nouveaux tests, vérifier qu'ils échouent pour la bonne raison**

Run: `pytest tests/test_patients.py::test_update_patient_toxicology_flag_reflects_the_stored_procedure tests/test_patients.py::test_update_patient_sans_drapeaux_les_laisse_inchanges -v`
Expected: le premier PASSE déjà (documente le comportement actuel, avant simplification — normal, rien à corriger pour celui-ci). Le second doit aussi déjà PASSER (le `COALESCE` protège déjà) — **ces deux tests caractérisent le comportement avant modification, ils doivent passer avant ET après le Step 4**. C'est la simplification elle-même (retrait de code mort) qui est sous test, pas un changement de comportement observable.

- [ ] **Step 4: Retirer le bloc de code mort dans `update_patient`**

Dans `controller/patient_controller.py`, remplacer les lignes 106-133 :

```python
    def update_patient(self, patient_id: int, data: dict) -> tuple[int, str]:
        existing_patient = self.repo.get_by_id(patient_id)
        if not existing_patient:
            raise ValueError("Patient introuvable")

        # Chantier 7a : l'ancien bloc de "protection" des drapeaux
        # is_clinical/is_toxicology/is_spiritual (roles 'app_admin',
        # 'app_secretaire', 'app_toxico_web'... qui ne correspondent a
        # aucun role reel du systeme) est retire - il dupliquait de facon
        # confuse une protection deja assuree par la procedure stockee
        # public.update_patient (ci/schema_only.sql : COALESCE(p_is_X, is_X)
        # preserve la valeur existante si le champ n'est pas envoye). Ces
        # 3 colonnes ne sont de toute facon plus une source de verite
        # depuis le chantier 6 (compute_domain_flags, calcul a la lecture).

        old_values = {k: existing_patient.get(k) for k in data.keys() if k in existing_patient}
```

(le reste de la méthode, à partir de `self.repo.update_patient(patient_id, data, self.user)`, reste inchangé)

- [ ] **Step 5: Relancer les 2 nouveaux tests, vérifier qu'ils passent toujours**

Run: `pytest tests/test_patients.py -v`
Expected: PASS pour tout le fichier (10 tests — les 2 nouveaux remplacent l'ancien, les 8 autres non affectés).

---

### Task 2: `patientStore.js` — actions corrigées et complétées

**Files:**
- Modify: `ah2-admin-web/src/stores/patientStore.js`

**Interfaces:**
- Consumes: `GET/POST/PUT/DELETE /patients/{id}` (déjà existants, `PatientCreate`/`PatientUpdate`/`PatientResponse` — voir Task 1).
- Produces (consommé par les Tasks 3-4) :
  - `addPatient(formData) -> Promise<void>` — lève l'erreur au lieu de l'avaler (`throw err`, pas de `alert()`).
  - `updatePatient(patientId, formData) -> Promise<void>` — nouveau, même convention d'erreur.
  - `deletePatient(id) -> Promise<void>` — même signature qu'avant, mais lève désormais l'erreur au lieu d'un `alert()`.
  - `getPatientById(id) -> Promise<Object>` — nouveau, renvoie l'enregistrement complet (`GET /patients/{id}`, réponse brute snake_case telle que renvoyée par le backend — **pas** le format abrégé camelCase de la liste mappée, qui n'a que 8 champs). Nécessaire pour pré-remplir la modale d'édition : la liste paginée (`patients`, via `fetchPatients`) ne contient pas `gender`/`national_id`/`assurance`/`residence`/`father_name`/`mother_name`.

- [ ] **Step 1: Corriger `addPatient` — envoyer les 10 champs, retirer le repli codé en dur**

Remplacer les lignes 133-156 :

```javascript
    async function addPatient(formData) {
        isLoading.value = true;
        try {
            const payload = {
                first_name: formData.firstName,
                last_name: formData.lastName,
                birth_date: formData.birthDate,
                gender: formData.gender || null,
                national_id: formData.nationalId || null,
                contact_phone: formData.contactPhone || null,
                assurance: formData.assurance || null,
                residence: formData.residence || null,
                father_name: formData.fatherName || null,
                mother_name: formData.motherName || null,
            };

            await api.post('/patients/', payload);

            // Rafraîchir la liste ET les compteurs après un ajout
            await Promise.all([
                fetchPatients(),
                fetchCounts()
            ]);
        } catch (err) {
            console.error("Erreur addPatient:", err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }
```

- [ ] **Step 2: Ajouter `updatePatient`**

Ajouter juste après `addPatient` :

```javascript
    async function updatePatient(patientId, formData) {
        isLoading.value = true;
        try {
            const payload = {
                first_name: formData.firstName,
                last_name: formData.lastName,
                birth_date: formData.birthDate,
                gender: formData.gender || null,
                national_id: formData.nationalId || null,
                contact_phone: formData.contactPhone || null,
                assurance: formData.assurance || null,
                residence: formData.residence || null,
                father_name: formData.fatherName || null,
                mother_name: formData.motherName || null,
            };

            await api.put(`/patients/${patientId}`, payload);

            await Promise.all([
                fetchPatients(),
                fetchCounts()
            ]);
        } catch (err) {
            console.error("Erreur updatePatient:", err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }
```

- [ ] **Step 3: Ajouter `getPatientById`**

Ajouter juste après `updatePatient` :

```javascript
    async function getPatientById(id) {
        const response = await api.get(`/patients/${id}`);
        return response.data;
    }
```

- [ ] **Step 4: Corriger `deletePatient` — lever l'erreur au lieu d'un `alert()`**

Remplacer les lignes 158-172 :

```javascript
    async function deletePatient(id) {
        try {
            await api.delete(`/patients/${id}`);

            // Optimiste : on retire de la liste locale
            patientData.value.data = patientData.value.data.filter(p => p.id !== id);

            // Rafraîchir les compteurs réels
            fetchCounts();
        } catch (err) {
            console.error("Erreur deletePatient:", err);
            throw err;
        }
    }
```

- [ ] **Step 5: Exposer les nouvelles fonctions dans le `return` du store**

Remplacer la ligne du `return` (actuellement ligne 195-199) :

```javascript
    return { 
        patients, isLoading, error, pagination, filters, 
        counts, globalCounts,
        fetchPatients, fetchCounts, addPatient, updatePatient, deletePatient, getPatientById, setPage, setFilters 
    };
```

- [ ] **Step 6: Vérifier la compilation**

Run (depuis `ah2-admin-web/`): `npx vite build`
Expected: succès, aucune erreur (ce store n'est pas encore consommé par une modale à ce stade — Tasks 3-4 le font — donc rien ne doit casser en aval).

---

### Task 3: `PatientModal.vue` (nouveau composant)

**Files:**
- Create: `ah2-admin-web/src/components/patients/PatientModal.vue`

**Interfaces:**
- Consumes: rien de nouveau (composant autonome, Vue 3 Composition API, patron visuel de `UserModal.vue` + gestion d'erreur de `ToxicoAdmissionModal.vue`).
- Produces (consommé par Task 4) :
  - Props : `patientToEdit: Object | null` (objet snake_case tel que renvoyé par `GET /patients/{id}` — voir Task 2 `getPatientById` — ou `null` pour une création), `errorMessage: String` (défaut `''`), `isSaving: Boolean` (défaut `false`).
  - Emits : `close` (aucun payload), `save` (payload `{firstName, lastName, birthDate, gender, nationalId, contactPhone, assurance, residence, fatherName, motherName}` — camelCase, converti en snake_case côté store, cohérent avec le patron déjà établi par `UserModal.vue`/`userStore.js`).

- [ ] **Step 1: Créer le composant**

Créer `ah2-admin-web/src/components/patients/PatientModal.vue` :

```vue
<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    <div class="relative mx-auto w-full max-w-2xl bg-white shadow-2xl rounded-2xl flex flex-col max-h-[90vh]">

      <div class="flex justify-between items-center p-6 border-b border-gray-100">
        <h3 class="text-xl font-bold text-gray-800">
          {{ isEditing ? 'Modifier le patient' : 'Nouveau patient' }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition p-2 rounded-full hover:bg-gray-100">
          <span class="text-2xl leading-none">&times;</span>
        </button>
      </div>

      <div class="p-6 overflow-y-auto custom-scrollbar">
        <form @submit.prevent="handleSubmit" id="patientForm" class="space-y-6">

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Prénom <span class="text-red-500">*</span></label>
              <input v-model="form.firstName" type="text" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Nom <span class="text-red-500">*</span></label>
              <input v-model="form.lastName" type="text" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Date de naissance <span class="text-red-500">*</span></label>
              <input v-model="form.birthDate" type="date" required :max="today" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Genre</label>
              <select v-model="form.gender" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 bg-white">
                <option :value="null">— Non précisé —</option>
                <option value="M">Masculin</option>
                <option value="F">Féminin</option>
                <option value="A">Autre</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Numéro national d'identité</label>
              <input v-model="form.nationalId" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Téléphone</label>
              <input v-model="form.contactPhone" type="tel" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Assurance</label>
              <input v-model="form.assurance" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Résidence</label>
              <input v-model="form.residence" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Nom du père</label>
              <input v-model="form.fatherName" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Nom de la mère</label>
              <input v-model="form.motherName" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-4 rounded">
            <p class="text-sm text-red-700">{{ errorMessage }}</p>
          </div>

        </form>
      </div>

      <div class="p-6 border-t border-gray-100 flex justify-end gap-3 bg-gray-50 rounded-b-2xl">
        <button type="button" @click="$emit('close')" :disabled="isSaving" class="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition shadow-sm disabled:opacity-50">
          Annuler
        </button>
        <button type="submit" form="patientForm" :disabled="isSaving || !isFormValid" class="px-5 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 font-medium shadow-lg shadow-green-200 transition transform active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed flex items-center">
          <svg v-if="isSaving" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ isEditing ? 'Enregistrer' : 'Créer' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted } from 'vue';

const props = defineProps({
  patientToEdit: { type: Object, default: null },
  errorMessage: { type: String, default: '' },
  isSaving: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'save']);
const isEditing = computed(() => !!props.patientToEdit);
const today = new Date().toISOString().split('T')[0];

const form = reactive({
  firstName: '',
  lastName: '',
  birthDate: '',
  gender: null,
  nationalId: '',
  contactPhone: '',
  assurance: '',
  residence: '',
  fatherName: '',
  motherName: '',
});

onMounted(() => {
  if (props.patientToEdit) {
    const p = props.patientToEdit;
    Object.assign(form, {
      firstName: p.first_name,
      lastName: p.last_name,
      birthDate: p.birth_date,
      gender: p.gender,
      nationalId: p.national_id || '',
      contactPhone: p.contact_phone || '',
      assurance: p.assurance || '',
      residence: p.residence || '',
      fatherName: p.father_name || '',
      motherName: p.mother_name || '',
    });
  }
});

const isFormValid = computed(() => {
  return form.firstName.trim() && form.lastName.trim() && form.birthDate;
});

const handleSubmit = () => {
  if (!isFormValid.value) return;
  emit('save', { ...form });
};
</script>
```

- [ ] **Step 2: Vérifier la compilation**

Run (depuis `ah2-admin-web/`): `npx vite build`
Expected: succès (composant autonome, non encore importé nulle part — juste une vérification de syntaxe/imports).

---

### Task 4: Câblage `PatientList.vue`

**Files:**
- Modify: `ah2-admin-web/src/views/modules/patients/PatientList.vue`

**Interfaces:**
- Consumes : `PatientModal.vue` (Task 3, props `patientToEdit`/`errorMessage`/`isSaving`, événements `close`/`save`), `patientStore.addPatient`/`updatePatient`/`deletePatient`/`getPatientById` (Task 2), `useAuthStore().userRole` (`ah2-admin-web/src/stores/auth.js`, déjà existant — chaîne unique, ex. `"admin"`, `"medecin"`, `"Assistant"`).

- [ ] **Step 1: Ajouter le bouton « Ajouter un patient » et l'état de la modale**

Dans le `<template>`, dans le bloc d'en-tête (juste après le `<div>` du titre/sous-titre, avant le bloc de recherche, ligne ~12) :

```html
      <div class="flex items-center gap-3">
        <button
            v-if="canManagePatients"
            @click="openCreateModal"
            class="flex items-center gap-2 bg-green-600 text-white px-4 py-2.5 rounded-xl hover:bg-green-700 font-medium shadow-sm transition"
        >
            <PlusIcon class="h-5 w-5" />
            Ajouter un patient
        </button>
      </div>
```

- [ ] **Step 2: Ajouter la colonne Actions (crayon/poubelle) dans le tableau**

Remplacer la cellule `<td class="px-6 py-4 text-right">` (lignes 87-98) :

```html
              <td class="px-6 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                    <button v-if="canManagePatients" @click="openEditModal(patient)" class="p-2 bg-white border border-gray-200 rounded-lg text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200 transition shadow-sm" title="Modifier">
                        <PencilSquareIcon class="h-4 w-4" />
                    </button>
                    <button v-if="canManagePatients" @click="confirmDelete(patient)" class="p-2 bg-white border border-gray-200 rounded-lg text-red-500 hover:bg-red-50 hover:border-red-200 transition shadow-sm" title="Supprimer">
                        <TrashIcon class="h-4 w-4" />
                    </button>
                    <button
                        v-if="!disableDetailLink"
                        @click="viewPatientDossier(patient.id)"
                        class="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center"
                    >
                        Voir Dossier
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                        </svg>
                    </button>
                </div>
              </td>
```

- [ ] **Step 3: Ajouter la modale et la bannière d'erreur de suppression en fin de template**

Juste avant la fermeture du `</div>` racine (dernière ligne du template, après le bloc de pagination) :

```html
    <div v-if="deleteError" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-xl">
        <p class="text-sm text-red-700">{{ deleteError }}</p>
    </div>

    <PatientModal
        v-if="showModal"
        :patientToEdit="patientBeingEdited"
        :errorMessage="modalError"
        :isSaving="isSavingPatient"
        @close="closeModal"
        @save="handleSave"
    />
```

- [ ] **Step 4: Ajouter la logique dans `<script setup>`**

Ajouter les imports nécessaires (compléter la ligne d'import `@heroicons/vue/24/outline` existante et ajouter les deux nouveaux imports) :

```javascript
import { 
    MagnifyingGlassIcon, UsersIcon, SparklesIcon, 
    BeakerIcon, HeartIcon, ChevronLeftIcon, ChevronRightIcon,
    PlusIcon, PencilSquareIcon, TrashIcon
} from '@heroicons/vue/24/outline';
import PatientModal from '@/components/patients/PatientModal.vue';
import { useAuthStore } from '@/stores/auth';
```

Ajouter, après la déclaration de `route` (après `const route = useRoute();`) :

```javascript
const authStore = useAuthStore();

// Memes 6 roles que le routeur backend (patients_endpoints.py) - parite
// UI/backend, ni plus ni moins (chantier 7a).
const canManagePatients = computed(() => 
    ['medecin', 'nurse', 'secretaire', 'admin', 'manager', 'Assistant'].includes(authStore.userRole)
);

const showModal = ref(false);
const patientBeingEdited = ref(null);
const modalError = ref('');
const isSavingPatient = ref(false);
const deleteError = ref('');

const openCreateModal = () => {
    patientBeingEdited.value = null;
    modalError.value = '';
    showModal.value = true;
};

const openEditModal = async (patient) => {
    modalError.value = '';
    try {
        patientBeingEdited.value = await patientStore.getPatientById(patient.id);
        showModal.value = true;
    } catch (err) {
        deleteError.value = "Impossible de charger les détails du patient pour modification.";
    }
};

const closeModal = () => {
    showModal.value = false;
    patientBeingEdited.value = null;
    modalError.value = '';
};

const mapErrorToMessage = (err) => {
    if (err.response) {
        const status = err.response.status;
        const detail = err.response.data?.detail;
        if (status === 422) {
            const errors = Array.isArray(detail) ? detail : [];
            if (errors.length) {
                return `Erreurs de validation : ${errors.map(e => e.msg).join(', ')}`;
            }
            return "Données invalides.";
        }
        if (status === 400) return detail || "Requête invalide.";
        if (status === 401) return "Session expirée. Veuillez vous reconnecter.";
        return `Erreur serveur (${status}) : ${detail || 'veuillez réessayer'}`;
    }
    if (err.request) return "Erreur réseau. Veuillez vérifier votre connexion.";
    return err.message || "Une erreur inattendue est survenue.";
};

const handleSave = async (payload) => {
    isSavingPatient.value = true;
    modalError.value = '';
    try {
        if (patientBeingEdited.value) {
            await patientStore.updatePatient(patientBeingEdited.value.patient_id, payload);
        } else {
            await patientStore.addPatient(payload);
        }
        closeModal();
    } catch (err) {
        modalError.value = mapErrorToMessage(err);
    } finally {
        isSavingPatient.value = false;
    }
};

const confirmDelete = async (patient) => {
    deleteError.value = '';
    if (confirm(`Voulez-vous vraiment supprimer ${patient.firstName} ${patient.lastName} ?`)) {
        try {
            await patientStore.deletePatient(patient.id);
        } catch (err) {
            deleteError.value = mapErrorToMessage(err);
        }
    }
};
```

- [ ] **Step 5: Vérifier la compilation**

Run (depuis `ah2-admin-web/`): `npx vite build`
Expected: succès, aucune erreur.

- [ ] **Step 6: Vérification manuelle (checklist pour un testeur humain — pas d'outil navigateur dans cet environnement)**

1. Se connecter avec un compte `admin` (ou tout rôle parmi les 6 autorisés) → le bouton « Ajouter un patient » et les icônes crayon/poubelle sont visibles sur `PatientList.vue`.
2. Se connecter avec un compte `laborantin`/`Psychologist` (hors des 6 rôles) → aucun bouton de gestion visible (seul « Voir Dossier » si applicable).
3. Créer un patient avec tous les champs remplis → vérifier en base que les 10 champs sont bien persistés (pas seulement les 3 d'avant), qu'aucun drapeau de domaine n'est envoyé.
4. Modifier un patient existant → la modale se pré-remplit avec ses données réelles (y compris genre/assurance/résidence/parents, absents de la liste paginée) ; enregistrer et vérifier la persistance.
5. Provoquer une erreur de validation (ex. date de naissance vide en contournant le `required` HTML via les devtools, ou un national_id dupliqué) → la bannière d'erreur inline s'affiche dans la modale, qui reste ouverte.
6. Supprimer un patient → confirmation `window.confirm`, disparition de la liste après confirmation ; annuler la confirmation → rien ne se passe.
7. Ouvrir le dossier consolidé (chantier 6) d'un patient modifié → les nouveaux champs apparaissent correctement dans l'en-tête si `PatientHeader.vue` les affiche déjà (pas de régression attendue, ce composant n'est pas touché par ce plan).

---

## Self-Review

**1. Couverture de la spec :**
- Section 1 (`PatientModal.vue`) → Task 3, y compris la correction de la spec sur le canal d'erreur (`errorMessage`/`isSaving` en props, pas d'appel API dans la modale). ✅
- Section 2 (`PatientList.vue`) → Task 4 : bouton, icônes, confirmation `window.confirm`, visibilité par rôle. ✅
- Section 3 (`patientStore.js`) → Task 2 : `addPatient` corrigé, `updatePatient` nouveau, `deletePatient` conservé (erreur non avalée). `getPatientById`, ajout nécessaire non explicitement prévu par la spec mais requis pour pré-remplir la modale d'édition avec les champs absents de la liste paginée (gender/national_id/assurance/residence/father_name/mother_name) — cohérent avec l'esprit de la spec, pas une déviation de sa substance. ✅
- Section 4 (simplification backend) → Task 1, mise à jour avec la correction faite pendant l'écriture de ce plan (COALESCE déjà protecteur, pas un bug de perte de données — confirmé avec l'utilisateur). ✅
- Exclusions (exports, hors ligne, nettoyage de rôles plus large, changement de politique d'accès) : aucune tâche n'y touche. ✅
- Définition du « terminé » : chaque point correspond à une étape vérifiable d'une tâche (Task 1 Steps 1-5 pour les drapeaux ; Task 4 Step 6 pour la création/modification/suppression et la visibilité par rôle). ✅

**2. Scan de placeholders :** aucun "TBD"/"TODO" ; chaque étape de code contient le code réel à écrire. Le seul renvoi à "voir Task N" est purement pour le contexte narratif (Self-Review elle-même), jamais à l'intérieur d'une étape de code.

**3. Cohérence des types/signatures :** `PatientModal.vue` (Task 3) émet exactement `{firstName, lastName, birthDate, gender, nationalId, contactPhone, assurance, residence, fatherName, motherName}` ; `patientStore.addPatient`/`updatePatient` (Task 2) lisent exactement ces mêmes clés camelCase pour construire le payload snake_case. `patientBeingEdited` (Task 4) vient de `getPatientById` (Task 2, réponse brute `GET /patients/{id}` donc snake_case — `first_name`, `birth_date`, etc.) et `PatientModal.vue`'s `onMounted` lit bien ces clés snake_case depuis `props.patientToEdit`, pas les clés camelCase de la liste mappée. `patient.id` (utilisé par `openEditModal`/`confirmDelete` dans Task 4) correspond au champ `id` déjà présent dans le mapping existant de `fetchPatients` (`id: p.id || p.patient_id`), inchangé par ce plan.
