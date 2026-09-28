# Chantier 3, sous-projet 2 : Fenêtre secrétariat — Plan d'implémentation

> **Pour les exécutants agentiques :** SOUS-COMPÉTENCE REQUISE : utiliser superpowers:subagent-driven-development pour exécuter ce plan tâche par tâche. Les étapes utilisent la syntaxe case à cocher (`- [ ]`) pour le suivi.

**Objectif :** donner au rôle `secretaire` un accès web complet — un shell indépendant (`SecretaireLayout.vue`) avec 5 sections (Accueil, Patients, Stock, Caisse, Consultation Spirituelle), en réutilisant au maximum les modules déjà construits pour d'autres rôles, et en construisant de zéro le seul module qui n'existe pas encore côté web (Consultation Spirituelle).

**Architecture :** même patron que `MedicalLayout.vue` (chantier 3, sous-projet 1, déjà livré) : shell indépendant de `MainLayout.vue`, routes `/secretariat/*` dédiées, `meta.roles: ['secretaire']`. Patients/Stock/Caisse sont montés en réutilisant tels quels des composants existants sous de nouvelles routes (même pattern que l'Étape 4 de la fenêtre médicale pour Patients). Consultation Spirituelle est un module CRUD neuf suivant le patron déjà établi (Gateway REST + store Pinia + modale + liste), avec réutilisation directe de `usePatientLookup.js` (composable déjà extrait au sous-projet précédent).

**Tech Stack :** Vue 3 (`<script setup>`), Pinia (stores en syntaxe `defineStore` avec fonction setup, pas d'options API), Vue Router 4, Tailwind, `@heroicons/vue/24/outline`, axios (`@/services/api`).

**Spec :** `docs/superpowers/specs/2026-09-13-chantier-3-fenetre-secretariat-design.md`

## Contraintes globales

- **AUCUN commit git, sur aucun fichier, à aucun moment de ce plan.** L'utilisateur a 60-90+ fichiers modifiés non commités dans son arbre de travail ; ce plan ajoute des fichiers neufs et modifie des fichiers existants (`router/index.js`, `LoginView.vue`) sans jamais committer quoi que ce soit. Toute étape "Commit" du patron standard de la compétence `writing-plans` est supprimée de ce plan — remplacée par une vérification manuelle.
- **Pas de worktree isolé.** Travail direct dans l'arbre de travail actuel de l'utilisateur, comme le sous-projet précédent — c'est le but même de ce chantier (superposer une fonctionnalité neuve sur son WIP existant).
- **Diffing manuel, pas `git diff` sur des commits.** Copier le fichier avant modification (`cp fichier fichier.snapshot`), comparer après (`diff -u`), même adaptation que le sous-projet précédent puisque les commits sont interdits.
- **Identifiants par module — ne jamais supposer `id` générique :** Patients = `patient_id` / `id` (React déjà existant, voir `PatientList.vue`), Stock = `medication_id`, Caisse = `transaction_id`, Consultation Spirituelle = `consultation_id`. Toujours vérifier le schéma Pydantic exact avant d'écrire du code qui consomme une réponse API.
- **Aucun changement backend n'est nécessaire dans ce plan.** Vérifié pour chaque endpoint utilisé : `/patients/*`, `/pharmacy/*` (`role_required("secretaire","admin","Assistant","ToxicoManager")`, `pharmacy_endpoints.py:23`), `/caisse/*` (`role_required("secretaire", "admin")`, `caisse_endpoints.py:34`), `/cs/*` (`role_required("secretaire", "admin", "medecin", "nurse", "SpiritualCounsellor")`, `cs_endpoint.py:26`) autorisent déjà `secretaire`. Si un exécutant rencontre une 403 sur un de ces endpoints en testant, c'est un signal d'arrêt (BLOCKED) — pas un backend à corriger silencieusement dans ce plan.
- **Aucune logique de rôle codée en dur** dans `PatientList.vue`, `PatientDetailView.vue`, `StockList.vue`, `ProductModal.vue`, `FinancialList.vue`, `FinanceModal.vue` — vérifié par grep (`authStore`, `userRole`, `ROLES.`) avant d'écrire ce plan. Ces composants n'ont besoin d'aucune modification, seulement d'un nouveau point de montage (route).
- **`FinanceModal.vue` est création-uniquement**, pas d'édition (pas de prop `transaction`/`product`-like, contrairement à `ProductModal.vue` qui accepte `product: Object|null`). Ne pas essayer d'ajouter une édition de transaction dans ce plan — c'est une limite déjà présente pour `admin`, pas quelque chose que ce sous-projet doit combler.
- **`GET /cs/` pagine en mémoire côté endpoint et ne renvoie aucun `total`/`total_pages`** (contrairement à `/medical_records/` qui utilise `PaginatedResponse`). La pagination de `ConsultationsList.vue` doit désactiver le bouton "page suivante" quand la page reçue contient moins de `per_page` éléments — jamais afficher un compteur de pages total inexistant.
- **`type_consultation` a exactement deux valeurs utilisées en pratique** (vérifié dans `view_pyqt6/secretaire/cs_form.py:118`) : `"Spiritual"` (affiche `mp_type` + `psaume`) et `"FamilyRestoration"` (affiche les champs `fr_*`). `ConsultationModal.vue` doit basculer les sections de champs visibles selon cette valeur, pas afficher tous les champs en permanence.
- **`presc_generic`/`presc_med_spirituel`** sont des tableaux de chaînes libres (pas de table de référence) — traiter comme des champs texte multi-valeurs simples (saisie séparée par virgules, split/join en JS), pas comme des selects.
- **`mp_type` est un `type_code`** provenant de `GET /cs/prayer-book-types` (`[{type_code, label}]`) — c'est un vrai select lié à une table de référence, contrairement à `presc_generic`/`presc_med_spirituel`.
- **Pas de rôle `admin` sur les routes `/secretariat/*`.** L'admin a déjà ses propres routes vers les mêmes composants (`/dashboard/patients`, `/dashboard/stock`, `/dashboard/finance`) — ajouter `admin` ici serait redondant, pas un accès supplémentaire réel.

---

## Tâche 1 : Rôle `secretaire` + shell `SecretaireLayout.vue` + montage Patients

**Fichiers :**
- Modifier : `ah2-admin-web/src/router/index.js`
- Modifier : `ah2-admin-web/src/views/LoginView.vue`
- Créer : `ah2-admin-web/src/components/layout/SecretaireLayout.vue`
- Modifier : `ah2-admin-web/src/i18n.js`

**Interfaces :**
- Produit : `ROLES.SECRETAIRE = 'secretaire'` dans `router/index.js`, réutilisé par toutes les tâches suivantes de ce plan.
- Produit : bloc route parent `/secretariat` avec `children` — les tâches 2, 3, 5, 6, 7 ajoutent chacune un enfant à ce tableau `children` existant, en respectant l'ordre alphabétique implicite déjà utilisé dans `/medical` (voir `router/index.js` lignes ~216-260 pour le patron exact du sous-projet précédent).
- Produit : bloc i18n `secretariat: { title, nav: { home, patients, stock, caisse, consultations } }` (fr + en), consommé par `SecretaireLayout.vue`.

- [ ] **Étape 1 : Ajouter le rôle**

Dans `ah2-admin-web/src/router/index.js`, dans la constante `ROLES` (actuellement lignes 10-18) :

```js
const ROLES = {
  ADMIN: 'admin',
  PSYCHOLOGIST: 'Psychologist',
  SPIRITUAL: 'SpiritualCounsellor',
  TOXICO_MANAGER: 'ToxicoManager',
  ASSISTANT: 'Assistant',
  MEDECIN: 'medecin',
  NURSE: 'nurse',
  SECRETAIRE: 'secretaire'
};
```

- [ ] **Étape 2 : Créer le bloc de routes `/secretariat`**

Ajouter, juste après le bloc `/medical` existant (avant `// Routes de secours`) :

```js
  // --- ROUTE PARENT : /secretariat (fenetre secretariat independante) ---
  {
    path: '/secretariat',
    component: () => import('@/components/layout/SecretaireLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/secretariat/patients'
      },
      {
        path: 'patients',
        name: 'secretariat-patients',
        component: () => import('@/views/modules/patients/PatientList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
      {
        path: 'patients/:id',
        name: 'secretariat-patient-detail',
        component: () => import('@/views/modules/patients/PatientDetailView.vue'),
        props: true,
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      }
    ]
  },
```

Note : le `redirect: '/secretariat/patients'` de l'enfant `''` est **temporaire** — la Tâche 7 le remplacera par le dashboard d'accueil une fois celui-ci construit. Ne pas construire de vue vide en attendant, la redirection suffit.

- [ ] **Étape 3 : Redirection post-login**

Dans `ah2-admin-web/src/views/LoginView.vue`, fonction `getRedirectPath` (actuellement lignes 77-110), ajouter un `case` avant le `default` :

```js
        case 'secretaire':
            // Fenetre secretariat independante (chantier 3, sous-projet 2)
            return '/secretariat/patients'; // devient '/secretariat/' a la Tache 7 (dashboard d'accueil)
```

- [ ] **Étape 4 : Bloc i18n du shell**

Dans `ah2-admin-web/src/i18n.js`, insérer après le bloc `doctorKpi` (fr, actuellement juste avant `finance:`) :

```js
    secretariat: {
      title: "Secrétariat",
      nav: {
        home: "Accueil",
        patients: "Patients",
        stock: "Stock",
        caisse: "Caisse",
        consultations: "Consultations"
      }
    },
```

Et l'équivalent en (juste avant `finance:` côté en) :

```js
    secretariat: {
      title: "Secretary",
      nav: {
        home: "Home",
        patients: "Patients",
        stock: "Stock",
        caisse: "Cashier",
        consultations: "Consultations"
      }
    },
```

- [ ] **Étape 5 : Créer `SecretaireLayout.vue`**

Copier la structure de `ah2-admin-web/src/components/layout/MedicalLayout.vue` à l'identique (sidebar, topbar, changement de langue, logout), en changeant uniquement :
- Le titre de secours : `configStore.structureInfo.name || 'AH2 Secrétariat'` (au lieu de `'AH2 Médical'`).
- Les imports d'icônes : `HomeIcon, UserGroupIcon, CubeIcon, BanknotesIcon, SparklesIcon` (au lieu des icônes médicales) — `CubeIcon`/`BanknotesIcon` réutilisés à l'identique de `MainLayout.vue` (lignes ~171, 189) pour la cohérence visuelle Stock/Caisse déjà établie ailleurs dans l'app ; `SparklesIcon` déjà utilisé pour "Soins Spirituels" dans `PatientList.vue` (ligne ~177), réutilisé ici pour "Consultations".
- Le tableau `menuItems` :

```js
const menuItems = [
  {
    path: '/secretariat/patients',
    labelKey: 'secretariat.nav.patients',
    icon: UserGroupIcon,
  },
  {
    path: '/secretariat/stock',
    labelKey: 'secretariat.nav.stock',
    icon: CubeIcon,
  },
  {
    path: '/secretariat/caisse',
    labelKey: 'secretariat.nav.caisse',
    icon: BanknotesIcon,
  },
  {
    path: '/secretariat/consultations',
    labelKey: 'secretariat.nav.consultations',
    icon: SparklesIcon,
  },
];
```

Note : l'entrée "Accueil" (`HomeIcon`, `secretariat.nav.home`, `/secretariat/`) sera ajoutée à ce tableau par la Tâche 7, une fois la vue d'accueil construite — ne pas l'ajouter maintenant pour éviter un lien mort.

- [ ] **Étape 6 : Vérification manuelle**

`npm run build` doit réussir sans erreur. Vérifier dans le navigateur (avec un compte `secretaire` existant, ou en modifiant temporairement le rôle retourné par l'API d'auth pour un compte de test) : connexion → atterrissage sur `/secretariat/patients`, sidebar avec 4 entrées (pas encore 5), recherche patient fonctionnelle, clic sur un patient → `/secretariat/patients/:id` (pas de redirection vers `/forbidden`).

---

## Tâche 2 : Montage Stock

**Fichiers :**
- Modifier : `ah2-admin-web/src/router/index.js`

**Interfaces :**
- Consomme : `ROLES.SECRETAIRE` (Tâche 1), composant `StockList.vue` existant (aucune modification), store `useStockStore` existant (aucune modification).

- [ ] **Étape 1 : Ajouter la route**

Dans le bloc `/secretariat` créé à la Tâche 1, ajouter un enfant après `patients/:id` :

```js
      {
        path: 'stock',
        name: 'secretariat-stock',
        component: () => import('@/views/modules/stock/StockList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
```

- [ ] **Étape 2 : Vérification manuelle**

`npm run build`. Dans le navigateur : nav "Stock" visible et fonctionnelle, liste des produits chargée, `ProductModal.vue` s'ouvre en création (`openModal(null)`) et en édition (`openModal(prod)`), suppression fonctionnelle. Aucune régression sur `/dashboard/stock` (toujours accessible à `admin`/`ToxicoManager`/`Assistant`).

---

## Tâche 3 : Montage Caisse

**Fichiers :**
- Modifier : `ah2-admin-web/src/router/index.js`

**Interfaces :**
- Consomme : `ROLES.SECRETAIRE` (Tâche 1), composant `FinancialList.vue` existant (aucune modification), store `useFinancialStore` existant (aucune modification).

- [ ] **Étape 1 : Ajouter la route**

Ajouter un enfant après `stock` :

```js
      {
        path: 'caisse',
        name: 'secretariat-caisse',
        component: () => import('@/views/modules/finance/FinancialList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
```

- [ ] **Étape 2 : Vérification manuelle**

`npm run build`. Dans le navigateur : nav "Caisse" visible, liste des transactions chargée, `FinanceModal.vue` s'ouvre en création (recette/dépense). Rappel : pas d'édition de transaction possible (`FinanceModal.vue` est création-uniquement, voir Contraintes globales — ce n'est pas un bug de cette tâche). Aucune régression sur `/dashboard/finance` (toujours réservé à `admin`).

---

## Tâche 4 : Consultation Spirituelle — Gateway + Store

**Fichiers :**
- Créer : `ah2-admin-web/src/services/ConsultationGateway.js`
- Créer : `ah2-admin-web/src/stores/consultationStore.js`

**Interfaces :**
- Produit : `ConsultationGateway.fetchConsultations({page, perPage, search})`, `fetchPrayerBookTypes()`, `createConsultation(data)`, `updateConsultation(consultationId, data)`, `deleteConsultation(consultationId)` — consommés par la Tâche 6 (liste) et indirectement par la Tâche 5 (modale, via le store) et la Tâche 7 (dashboard, `fetchConsultations` pour le compte de la période).
- Produit : `useConsultationStore` exposant `consultations, prayerBookTypes, isLoading, filters, hasNextPage, fetchConsultations, fetchPrayerBookTypes, createConsultation, updateConsultation, deleteConsultation, setPage, setFilters`.

- [ ] **Étape 1 : Écrire `ConsultationGateway.js`**

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

export const ConsultationGateway = {

    async fetchConsultations(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.perPage || 20,
            search: params.search,
        };
        return api.get('/cs/', { params: cleanParams(rawQuery) });
    },

    async fetchPrayerBookTypes() {
        return api.get('/cs/prayer-book-types');
    },

    async createConsultation(data) {
        const payload = {
            patient_id: data.patientId,
            type_consultation: data.typeConsultation,
            presc_generic: data.prescGeneric || [],
            presc_med_spirituel: data.prescMedSpirituel || [],
            mp_type: data.mpType || null,
            psaume: data.psaume || null,
            notes: data.notes || null,
            fr_registered_at: data.frRegisteredAt || null,
            fr_appointment_at: data.frAppointmentAt || null,
            fr_amount_paid: data.frAmountPaid || null,
            fr_observation: data.frObservation || null,
            consultation_date: data.consultationDate || null,
        };
        return api.post('/cs/', payload);
    },

    async updateConsultation(consultationId, data) {
        const payload = {
            patient_id: data.patientId,
            type_consultation: data.typeConsultation,
            presc_generic: data.prescGeneric || [],
            presc_med_spirituel: data.prescMedSpirituel || [],
            mp_type: data.mpType || null,
            psaume: data.psaume || null,
            notes: data.notes || null,
            fr_registered_at: data.frRegisteredAt || null,
            fr_appointment_at: data.frAppointmentAt || null,
            fr_amount_paid: data.frAmountPaid || null,
            fr_observation: data.frObservation || null,
            consultation_date: data.consultationDate || null,
        };
        return api.put(`/cs/${consultationId}`, payload);
    },

    async deleteConsultation(consultationId) {
        return api.delete(`/cs/${consultationId}`);
    },
};
```

- [ ] **Étape 2 : Écrire `consultationStore.js`**

```js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { ConsultationGateway } from '@/services/ConsultationGateway';

export const useConsultationStore = defineStore('consultation', () => {

    const isLoading = ref(false);
    const consultations = ref([]);
    const prayerBookTypes = ref([]);
    // GET /cs/ ne renvoie ni total ni total_pages (pagination en memoire
    // cote endpoint) - on deduit "page suivante possible" du remplissage
    // de la page recue, pas d'un compteur total inexistant.
    const hasNextPage = ref(false);

    const filters = ref({
        search: '',
    });

    const pagination = ref({
        page: 1,
        perPage: 20,
    });

    async function fetchConsultations() {
        isLoading.value = true;
        try {
            const res = await ConsultationGateway.fetchConsultations({
                page: pagination.value.page,
                perPage: pagination.value.perPage,
                search: filters.value.search,
            });
            consultations.value = res.data || [];
            hasNextPage.value = consultations.value.length === pagination.value.perPage;
        } catch (error) {
            console.error('Erreur chargement consultations:', error);
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchPrayerBookTypes() {
        try {
            const res = await ConsultationGateway.fetchPrayerBookTypes();
            prayerBookTypes.value = res.data || [];
        } catch (error) {
            console.error('Erreur chargement types de livres de priere:', error);
        }
    }

    async function createConsultation(data) {
        await ConsultationGateway.createConsultation(data);
        await fetchConsultations();
    }

    async function updateConsultation(consultationId, data) {
        await ConsultationGateway.updateConsultation(consultationId, data);
        await fetchConsultations();
    }

    async function deleteConsultation(consultationId) {
        await ConsultationGateway.deleteConsultation(consultationId);
        await fetchConsultations();
    }

    function setPage(page) {
        pagination.value.page = page;
        fetchConsultations();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters };
        pagination.value.page = 1;
        fetchConsultations();
    }

    return {
        consultations, prayerBookTypes, isLoading, filters, pagination, hasNextPage,
        fetchConsultations, fetchPrayerBookTypes,
        createConsultation, updateConsultation, deleteConsultation,
        setPage, setFilters,
    };
});
```

- [ ] **Étape 3 : Vérification manuelle**

Pas de vue encore branchée sur ce store — vérifier seulement que `npm run build` réussit (aucune erreur d'import/syntaxe). La vérification fonctionnelle réelle arrive à la Tâche 6 une fois la liste branchée.

---

## Tâche 5 : Consultation Spirituelle — `ConsultationModal.vue`

**Fichiers :**
- Créer : `ah2-admin-web/src/components/consultations/ConsultationModal.vue`
- Modifier : `ah2-admin-web/src/i18n.js`

**Interfaces :**
- Consomme : `usePatientLookup` (`@/composables/usePatientLookup.js`, déjà extrait au sous-projet précédent — signature : `usePatientLookup(getNotFoundMessage)` retournant `{ patientCode, patientId, patientName, patientLookupMessage, lookupPatient, ensureLookup, setFromExisting }`), `useConsultationStore` (Tâche 4, pour `prayerBookTypes` + `fetchPrayerBookTypes`).
- Props : `{ consultation: Object|null }`. Emits : `['close', 'save']`, payload de save : `{ patientId, typeConsultation, prescGeneric, prescMedSpirituel, mpType, psaume, notes, frRegisteredAt, frAppointmentAt, frAmountPaid, frObservation, consultationDate }` — noms exacts consommés par `ConsultationGateway.createConsultation`/`updateConsultation` (Tâche 4).

- [ ] **Étape 1 : Bloc i18n `consultations.*`**

Dans `ah2-admin-web/src/i18n.js`, insérer après le bloc `secretariat` (fr) :

```js
    consultations: {
      title: "Consultations Spirituelles",
      subtitle: "Suivi des consultations et accompagnements",
      search_placeholder: "Rechercher code patient ou nom...",
      new_consultation: "Nouvelle Consultation",
      empty: "Aucune consultation trouvée.",
      confirm_delete: "Supprimer cette consultation ?",
      table: {
        patient: "Patient",
        type: "Type",
        date: "Date",
        actions: "Actions"
      },
      actions: {
        edit: "Éditer",
        delete: "Supprimer"
      },
      type_spiritual: "Spirituelle",
      type_family_restoration: "Restauration Familiale",
      modal: {
        title_new: "Nouvelle Consultation",
        title_edit: "Modifier la Consultation",
        patient_code: "Code Patient",
        patient_not_found: "Patient introuvable",
        type_label: "Type de consultation",
        consultation_date: "Date de consultation",
        section_spiritual: "Détails Spirituels",
        prayer_book_type: "Type de livre de prière",
        prayer_book_none: "-- Sélectionner --",
        psaume: "Psaume",
        section_family_restoration: "Restauration Familiale",
        fr_registered_at: "Date d'inscription",
        fr_appointment_at: "Date de rendez-vous",
        fr_amount_paid: "Montant payé",
        fr_observation: "Observation",
        section_common: "Informations complémentaires",
        presc_generic: "Prescriptions générales (séparées par virgule)",
        presc_med_spirituel: "Prescriptions médico-spirituelles (séparées par virgule)",
        notes: "Notes",
        cancel: "Annuler",
        save: "Enregistrer",
        type_required: "Veuillez sélectionner un type de consultation."
      }
    },
```

Et l'équivalent en :

```js
    consultations: {
      title: "Spiritual Consultations",
      subtitle: "Consultation and support tracking",
      search_placeholder: "Search patient code or name...",
      new_consultation: "New Consultation",
      empty: "No consultations found.",
      confirm_delete: "Delete this consultation?",
      table: {
        patient: "Patient",
        type: "Type",
        date: "Date",
        actions: "Actions"
      },
      actions: {
        edit: "Edit",
        delete: "Delete"
      },
      type_spiritual: "Spiritual",
      type_family_restoration: "Family Restoration",
      modal: {
        title_new: "New Consultation",
        title_edit: "Edit Consultation",
        patient_code: "Patient Code",
        patient_not_found: "Patient not found",
        type_label: "Consultation type",
        consultation_date: "Consultation date",
        section_spiritual: "Spiritual Details",
        prayer_book_type: "Prayer book type",
        prayer_book_none: "-- Select --",
        psaume: "Psalm",
        section_family_restoration: "Family Restoration",
        fr_registered_at: "Registration date",
        fr_appointment_at: "Appointment date",
        fr_amount_paid: "Amount paid",
        fr_observation: "Observation",
        section_common: "Additional information",
        presc_generic: "General prescriptions (comma-separated)",
        presc_med_spirituel: "Medico-spiritual prescriptions (comma-separated)",
        notes: "Notes",
        cancel: "Cancel",
        save: "Save",
        type_required: "Please select a consultation type."
      }
    },
```

- [ ] **Étape 2 : Écrire `ConsultationModal.vue`**

```vue
<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
    <div class="relative mx-auto p-6 border w-full max-w-2xl shadow-xl rounded-2xl bg-white max-h-[90vh] overflow-y-auto">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('consultations.modal.title_edit') : t('consultations.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            :readonly="isEdit"
            :class="[
              'block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm',
              isEdit ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''
            ]"
            placeholder="Ex: AH2-000818AQ"
          />
          <p v-if="patientLookupMessage" class="text-sm mt-1" :class="patientId ? 'text-green-600' : 'text-red-500'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.type_label') }}</label>
          <select v-model="form.typeConsultation" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
            <option value="Spiritual">{{ t('consultations.type_spiritual') }}</option>
            <option value="FamilyRestoration">{{ t('consultations.type_family_restoration') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.consultation_date') }}</label>
          <input v-model="form.consultationDate" type="datetime-local" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
        </div>

        <template v-if="form.typeConsultation === 'Spiritual'">
          <fieldset class="border border-gray-200 rounded-lg p-4 space-y-4">
            <legend class="text-sm font-semibold text-gray-600 px-1">{{ t('consultations.modal.section_spiritual') }}</legend>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.prayer_book_type') }}</label>
              <select v-model="form.mpType" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
                <option value="">{{ t('consultations.modal.prayer_book_none') }}</option>
                <option v-for="pbt in consultationStore.prayerBookTypes" :key="pbt.type_code" :value="pbt.type_code">
                  {{ pbt.label || pbt.type_code }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.psaume') }}</label>
              <input v-model="form.psaume" type="text" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
          </fieldset>
        </template>

        <template v-else-if="form.typeConsultation === 'FamilyRestoration'">
          <fieldset class="border border-gray-200 rounded-lg p-4 space-y-4">
            <legend class="text-sm font-semibold text-gray-600 px-1">{{ t('consultations.modal.section_family_restoration') }}</legend>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.fr_registered_at') }}</label>
                <input v-model="form.frRegisteredAt" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.fr_appointment_at') }}</label>
                <input v-model="form.frAppointmentAt" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.fr_amount_paid') }}</label>
              <input v-model="form.frAmountPaid" type="number" min="0" step="0.01" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.fr_observation') }}</label>
              <textarea v-model="form.frObservation" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
          </fieldset>
        </template>

        <fieldset class="border border-gray-200 rounded-lg p-4 space-y-4">
          <legend class="text-sm font-semibold text-gray-600 px-1">{{ t('consultations.modal.section_common') }}</legend>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.presc_generic') }}</label>
            <input v-model="prescGenericText" type="text" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.presc_med_spirituel') }}</label>
            <input v-model="prescMedSpirituelText" type="text" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.notes') }}</label>
            <textarea v-model="form.notes" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
          </div>
        </fieldset>

        <div class="flex justify-end gap-3 pt-2">
          <button type="button" @click="$emit('close')" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 text-sm font-medium">
            {{ t('consultations.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 text-sm font-medium">
            {{ t('consultations.modal.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { usePatientLookup } from '@/composables/usePatientLookup.js';
import { useConsultationStore } from '@/stores/consultationStore';

const { t } = useI18n();
const consultationStore = useConsultationStore();

const props = defineProps({ consultation: { type: Object, default: null } });
const emit = defineEmits(['close', 'save']);

const isEdit = computed(() => !!props.consultation);

const {
  patientCode, patientId, patientName, patientLookupMessage,
  lookupPatient, ensureLookup, setFromExisting,
} = usePatientLookup(() => t('consultations.modal.patient_not_found'));

const form = reactive({
  typeConsultation: 'Spiritual',
  consultationDate: '',
  mpType: '',
  psaume: '',
  frRegisteredAt: '',
  frAppointmentAt: '',
  frAmountPaid: '',
  frObservation: '',
  notes: '',
});

const prescGenericText = ref('');
const prescMedSpirituelText = ref('');

function splitCsv(text) {
  return (text || '').split(',').map((s) => s.trim()).filter(Boolean);
}

onMounted(() => {
  consultationStore.fetchPrayerBookTypes();

  if (props.consultation) {
    const rec = props.consultation;
    setFromExisting({
      patientId: rec.patient_id,
      code: rec.patient?.code_patient,
      firstName: rec.patient?.first_name,
      lastName: rec.patient?.last_name,
    });
    form.typeConsultation = rec.type_consultation || 'Spiritual';
    form.consultationDate = rec.consultation_date ? rec.consultation_date.slice(0, 16) : '';
    form.mpType = rec.mp_type || '';
    form.psaume = rec.psaume || '';
    form.frRegisteredAt = rec.fr_registered_at ? rec.fr_registered_at.slice(0, 10) : '';
    form.frAppointmentAt = rec.fr_appointment_at ? rec.fr_appointment_at.slice(0, 10) : '';
    form.frAmountPaid = rec.fr_amount_paid || '';
    form.frObservation = rec.fr_observation || '';
    form.notes = rec.notes || '';
    prescGenericText.value = (rec.presc_generic || []).join(', ');
    prescMedSpirituelText.value = (rec.presc_med_spirituel || []).join(', ');
  }
});

async function handleSubmit() {
  await ensureLookup();

  if (!patientId.value) {
    alert(t('consultations.modal.patient_not_found'));
    return;
  }
  if (!form.typeConsultation) {
    alert(t('consultations.modal.type_required'));
    return;
  }

  emit('save', {
    patientId: patientId.value,
    typeConsultation: form.typeConsultation,
    prescGeneric: splitCsv(prescGenericText.value),
    prescMedSpirituel: splitCsv(prescMedSpirituelText.value),
    mpType: form.mpType || null,
    psaume: form.psaume || null,
    notes: form.notes || null,
    frRegisteredAt: form.frRegisteredAt || null,
    frAppointmentAt: form.frAppointmentAt || null,
    frAmountPaid: form.frAmountPaid || null,
    frObservation: form.frObservation || null,
    consultationDate: form.consultationDate || null,
  });
}
</script>
```

Note pour l'exécutant : le champ `patient` dans `props.consultation` (utilisé dans `onMounted` pour `setFromExisting`) suppose que le backend renvoie un sous-objet patient, **ce qui n'est pas garanti** — `ConsultationResponse` (`schemas_cs.py`) n'a qu'un `patient_id` brut, pas de sous-objet `patient`. Vérifier à l'exécution (via `console.log` ou l'onglet réseau du navigateur) si `GET /cs/` renvoie un sous-objet patient enrichi (comme `MedicalRecordResponse` le fait depuis le correctif du sous-projet précédent) ou seulement `patient_id`. Si seulement `patient_id` : soit appeler `GET /patients/{patient_id}` pour résoudre le nom en édition, soit accepter que le champ "Code Patient" affiche l'ID brut en édition faute de mieux — **ne pas modifier le backend `cs_endpoint.py`/`mapping.py` dans cette tâche sans en discuter d'abord**, ce serait un changement de périmètre plus large que ce plan (contrairement au sous-projet précédent où exposer `patient` dans `MedicalRecordResponse` était le sujet même de la Tâche 2). Documenter le choix fait dans le rapport de tâche.

- [ ] **Étape 3 : Vérification manuelle**

`npm run build`. Pas encore de vue liste pour ouvrir cette modale en conditions réelles — vérifier au minimum que le composant compile et qu'il n'y a pas d'erreur de référence (`prayerBookTypes`, `usePatientLookup`). La vérification fonctionnelle complète arrive à la Tâche 6.

---

## Tâche 6 : Consultation Spirituelle — `ConsultationsList.vue` + route + nav

**Fichiers :**
- Créer : `ah2-admin-web/src/views/modules/consultations/ConsultationsList.vue`
- Modifier : `ah2-admin-web/src/router/index.js`
- Modifier : `ah2-admin-web/src/components/layout/SecretaireLayout.vue`

**Interfaces :**
- Consomme : `useConsultationStore` (Tâche 4), `ConsultationModal` (Tâche 5).

- [ ] **Étape 1 : Écrire `ConsultationsList.vue`**

```vue
<template>
  <div class="space-y-6 w-full">

    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('consultations.title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('consultations.subtitle') }}</p>
      </div>

      <div class="flex items-center gap-3 w-full md:w-auto">
        <input
          v-model.lazy="searchQuery"
          @keyup.enter="consultationStore.fetchConsultations()"
          type="text"
          :placeholder="t('consultations.search_placeholder')"
          class="block w-full md:w-64 px-3 py-2.5 border border-gray-300 rounded-xl bg-gray-50 focus:ring-teal-500 focus:border-teal-500 sm:text-sm"
        />
        <button @click="openModal(null)" class="flex-shrink-0 px-4 py-2.5 bg-teal-600 text-white rounded-xl hover:bg-teal-700 text-sm font-semibold">
          {{ t('consultations.new_consultation') }}
        </button>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="consultationStore.isLoading" class="p-10 text-center text-gray-500">
        {{ t('common.loading') }}
      </div>
      <table v-else class="min-w-full divide-y divide-gray-100">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{{ t('consultations.table.patient') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{{ t('consultations.table.type') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{{ t('consultations.table.date') }}</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{{ t('consultations.table.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="consultationStore.consultations.length === 0">
            <td colspan="4" class="px-6 py-8 text-center text-gray-400">{{ t('consultations.empty') }}</td>
          </tr>
          <tr v-for="rec in consultationStore.consultations" :key="rec.consultation_id" class="hover:bg-gray-50">
            <td class="px-6 py-4 text-sm text-gray-700">{{ rec.patient_id }}</td>
            <td class="px-6 py-4 text-sm text-gray-700">
              {{ rec.type_consultation === 'Spiritual' ? t('consultations.type_spiritual') : t('consultations.type_family_restoration') }}
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">{{ (rec.consultation_date || '').slice(0, 10) }}</td>
            <td class="px-6 py-4 text-right text-sm space-x-2">
              <button @click="openModal(rec)" class="text-teal-600 hover:text-teal-800">{{ t('consultations.actions.edit') }}</button>
              <button @click="handleDelete(rec)" class="text-red-500 hover:text-red-700">{{ t('consultations.actions.delete') }}</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <button
          @click="consultationStore.setPage(consultationStore.pagination.page - 1)"
          :disabled="consultationStore.pagination.page === 1"
          class="px-3 py-1 border rounded bg-white disabled:opacity-50"
        >&laquo;</button>
        <span class="text-sm text-gray-500">{{ consultationStore.pagination.page }}</span>
        <button
          @click="consultationStore.setPage(consultationStore.pagination.page + 1)"
          :disabled="!consultationStore.hasNextPage"
          class="px-3 py-1 border rounded bg-white disabled:opacity-50"
        >&raquo;</button>
      </div>
    </div>

    <ConsultationModal
      v-if="showModal"
      :consultation="editingConsultation"
      @close="showModal = false"
      @save="handleSave"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useConsultationStore } from '@/stores/consultationStore';
import ConsultationModal from '@/components/consultations/ConsultationModal.vue';

const { t } = useI18n();
const consultationStore = useConsultationStore();

const showModal = ref(false);
const editingConsultation = ref(null);

const searchQuery = computed({
  get: () => consultationStore.filters.search,
  set: (val) => consultationStore.setFilters({ search: val }),
});

function openModal(rec) {
  editingConsultation.value = rec;
  showModal.value = true;
}

async function handleSave(data) {
  try {
    if (editingConsultation.value) {
      await consultationStore.updateConsultation(editingConsultation.value.consultation_id, data);
    } else {
      await consultationStore.createConsultation(data);
    }
    showModal.value = false;
  } catch (err) {
    alert(err.response?.data?.detail || err.message);
  }
}

async function handleDelete(rec) {
  if (!confirm(t('consultations.confirm_delete'))) return;
  try {
    await consultationStore.deleteConsultation(rec.consultation_id);
  } catch (err) {
    alert(err.response?.data?.detail || err.message);
  }
}

onMounted(() => {
  consultationStore.fetchConsultations();
});
</script>
```

Note pour l'exécutant : la colonne "Patient" affiche `rec.patient_id` brut (pas un nom), pour la même raison que la note de la Tâche 5 — `ConsultationResponse` n'expose pas de sous-objet `patient`. Si l'exécutant constate à l'exécution que le backend renvoie effectivement un sous-objet enrichi, adapter cette colonne pour afficher le nom (cohérent avec `MedicalRecordsList.vue`) ; sinon, documenter la limite dans le rapport de tâche plutôt que de la corriger silencieusement (même ligne de conduite que la note de la Tâche 5).

- [ ] **Étape 2 : Ajouter la route**

```js
      {
        path: 'consultations',
        name: 'secretariat-consultations',
        component: () => import('@/views/modules/consultations/ConsultationsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
```

- [ ] **Étape 3 : Ajouter l'entrée de nav**

Dans `SecretaireLayout.vue`, ajouter au tableau `menuItems` (après `caisse`) :

```js
  {
    path: '/secretariat/consultations',
    labelKey: 'secretariat.nav.consultations',
    icon: SparklesIcon,
  },
```

- [ ] **Étape 4 : Vérification manuelle**

`npm run build`. Dans le navigateur : nav "Consultations" visible, liste chargée (vide au départ, normal), création d'une consultation "Spiritual" (avec type de livre de prière + psaume) et d'une consultation "FamilyRestoration" (avec les champs `fr_*`) — vérifier que les sections de champs basculent bien selon le type choisi. Édition et suppression fonctionnelles. Pagination : bouton "page suivante" désactivé quand moins de 20 résultats.

---

## Tâche 7 : Dashboard d'accueil

**Fichiers :**
- Créer : `ah2-admin-web/src/stores/secretariatHomeStore.js`
- Créer : `ah2-admin-web/src/views/modules/secretariat/SecretariatHomeView.vue`
- Modifier : `ah2-admin-web/src/router/index.js`
- Modifier : `ah2-admin-web/src/components/layout/SecretaireLayout.vue`
- Modifier : `ah2-admin-web/src/views/LoginView.vue`
- Modifier : `ah2-admin-web/src/i18n.js`

**Interfaces :**
- Consomme : `FinanceGateway` (existant, aucune modification — `getIncomeTotal`, `getExpenseTotal`, `getDebtTotal`), `ConsultationGateway.fetchConsultations` (Tâche 4), deux nouveaux appels directs `api.get('/pharmacy/kpi/critical_stock_count')` / `api.get('/pharmacy/kpi/expiring_product_count')` (pas de nouveau fichier Gateway pour ceux-ci — `stockStore.js` existant appelle déjà `api` directement sans Gateway dédié, même convention suivie ici).

- [ ] **Étape 1 : Bloc i18n**

Dans `ah2-admin-web/src/i18n.js`, ajouter dans le bloc `secretariat` existant (fr) :

```js
    secretariat: {
      title: "Secrétariat",
      nav: {
        home: "Accueil",
        patients: "Patients",
        stock: "Stock",
        caisse: "Caisse",
        consultations: "Consultations"
      },
      home: {
        title: "Vue d'ensemble",
        period_from: "Du",
        period_to: "Au",
        total_paid: "Total Encaissé",
        total_withdrawn: "Total Retraits",
        balance: "Solde Net",
        remaining_due: "Reste à Recouvrer",
        critical_stock: "Stock Critique",
        expiring_stock: "Péremptions Proches (30j)",
        consultations_period: "Consultations (période)"
      }
    },
```

Et l'équivalent en :

```js
    secretariat: {
      title: "Secretary",
      nav: {
        home: "Home",
        patients: "Patients",
        stock: "Stock",
        caisse: "Cashier",
        consultations: "Consultations"
      },
      home: {
        title: "Overview",
        period_from: "From",
        period_to: "To",
        total_paid: "Total Paid",
        total_withdrawn: "Total Withdrawn",
        balance: "Net Balance",
        remaining_due: "Remaining Due",
        critical_stock: "Critical Stock",
        expiring_stock: "Expiring Soon (30d)",
        consultations_period: "Consultations (period)"
      }
    },
```

- [ ] **Étape 2 : Écrire `secretariatHomeStore.js`**

```js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import api from '@/services/api';
import { FinanceGateway } from '@/services/FinanceGateway';
import { ConsultationGateway } from '@/services/ConsultationGateway';

export const useSecretariatHomeStore = defineStore('secretariatHome', () => {

    const isLoading = ref(false);

    const today = new Date().toISOString().split('T')[0];

    const filters = ref({
        startDate: today,
        endDate: today,
    });

    const stats = ref({
        totalPaid: 0,
        totalWithdrawn: 0,
        remainingDue: 0,
        criticalStockCount: 0,
        expiringStockCount: 0,
        consultationsCount: 0,
    });

    async function fetchHomeData() {
        isLoading.value = true;
        try {
            const dateParams = {
                startDate: filters.value.startDate,
                endDate: filters.value.endDate,
            };

            const [incomeRes, expenseRes, debtRes, criticalRes, expiringRes, consultationsRes] = await Promise.all([
                FinanceGateway.getIncomeTotal(dateParams),
                FinanceGateway.getExpenseTotal(dateParams),
                FinanceGateway.getDebtTotal(dateParams),
                api.get('/pharmacy/kpi/critical_stock_count'),
                api.get('/pharmacy/kpi/expiring_product_count', { params: { days: 30 } }),
                ConsultationGateway.fetchConsultations({ page: 1, perPage: 200 }),
            ]);

            stats.value.totalPaid = Number(incomeRes.data) || 0;
            stats.value.totalWithdrawn = Number(expenseRes.data) || 0;
            stats.value.remainingDue = Number(debtRes.data) || 0;
            stats.value.criticalStockCount = criticalRes.data?.stock_alerts_count || 0;
            stats.value.expiringStockCount = expiringRes.data?.expiring_alerts_count || 0;
            stats.value.consultationsCount = (consultationsRes.data || []).length;
        } catch (error) {
            console.error('Erreur chargement dashboard secretariat:', error);
        } finally {
            isLoading.value = false;
        }
    }

    function setDates(start, end) {
        filters.value.startDate = start;
        filters.value.endDate = end;
        fetchHomeData();
    }

    return { isLoading, filters, stats, fetchHomeData, setDates };
});
```

Note pour l'exécutant : `stats.value.consultationsCount` utilise `(consultationsRes.data || []).length` sur une page de 200 résultats **sans filtre de date** — `ConsultationGateway.fetchConsultations` (Tâche 4) n'a pas de paramètres `date_from`/`date_to` (le backend `/cs/` n'en accepte pas non plus, vérifié dans `cs_endpoint.py`). C'est donc un total global, pas borné à la période sélectionnée dans les date pickers — comme le compteur "Dossiers médicaux" du sous-projet précédent (registre H1), documenter cette limite dans le rapport de tâche plutôt que d'inventer un filtrage qui n'existe pas côté backend.

- [ ] **Étape 3 : Écrire `SecretariatHomeView.vue`**

```vue
<template>
  <div class="space-y-8 w-full">

    <div class="flex flex-col md:flex-row md:items-center md:justify-between bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <h1 class="text-3xl font-extrabold text-gray-800 tracking-tight">{{ t('secretariat.home.title') }}</h1>

      <div class="mt-4 md:mt-0 flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-3 items-end">
        <div class="flex flex-col">
          <label class="text-xs font-medium text-gray-500 mb-1">{{ t('secretariat.home.period_from') }}</label>
          <input type="date" v-model="homeStore.filters.startDate" @change="applyFilters" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-teal-500 focus:border-teal-500" />
        </div>
        <div class="flex flex-col">
          <label class="text-xs font-medium text-gray-500 mb-1">{{ t('secretariat.home.period_to') }}</label>
          <input type="date" v-model="homeStore.filters.endDate" @change="applyFilters" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-teal-500 focus:border-teal-500" />
        </div>
      </div>
    </div>

    <div v-if="homeStore.isLoading" class="p-10 text-center text-gray-500">{{ t('common.loading') }}</div>

    <template v-else>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard :title="t('secretariat.home.total_paid')" :value="formatCurrency(homeStore.stats.totalPaid)" :icon="BanknotesIcon" colorClass="bg-green-50" iconColor="text-green-600" />
        <StatCard :title="t('secretariat.home.total_withdrawn')" :value="formatCurrency(homeStore.stats.totalWithdrawn)" :icon="ArrowTrendingDownIcon" colorClass="bg-red-50" iconColor="text-red-600" />
        <StatCard :title="t('secretariat.home.balance')" :value="formatCurrency(homeStore.stats.totalPaid - homeStore.stats.totalWithdrawn)" :icon="ArrowTrendingUpIcon" colorClass="bg-blue-50" iconColor="text-blue-600" />
        <StatCard :title="t('secretariat.home.remaining_due')" :value="formatCurrency(homeStore.stats.remainingDue)" :icon="ExclamationTriangleIcon" colorClass="bg-orange-50" iconColor="text-orange-600" />
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard :title="t('secretariat.home.critical_stock')" :value="homeStore.stats.criticalStockCount" :icon="CubeIcon" colorClass="bg-red-50" iconColor="text-red-600" />
        <StatCard :title="t('secretariat.home.expiring_stock')" :value="homeStore.stats.expiringStockCount" :icon="ClockIcon" colorClass="bg-amber-50" iconColor="text-amber-600" />
        <StatCard :title="t('secretariat.home.consultations_period')" :value="homeStore.stats.consultationsCount" :icon="SparklesIcon" colorClass="bg-teal-50" iconColor="text-teal-600" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useSecretariatHomeStore } from '@/stores/secretariatHomeStore';
import StatCard from '@/components/dashboard/StatCard.vue';
import {
  BanknotesIcon, ArrowTrendingDownIcon, ArrowTrendingUpIcon,
  ExclamationTriangleIcon, CubeIcon, ClockIcon, SparklesIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const homeStore = useSecretariatHomeStore();

const formatCurrency = (value) => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF', minimumFractionDigits: 0 }).format(value).replace('XOF', 'FCFA');
};

const applyFilters = () => {
  homeStore.setDates(homeStore.filters.startDate, homeStore.filters.endDate);
};

onMounted(() => {
  homeStore.fetchHomeData();
});
</script>
```

- [ ] **Étape 4 : Router — route racine + remplacement de la redirection**

Dans `router/index.js`, remplacer l'enfant `''` du bloc `/secretariat` (créé Tâche 1) :

```js
      {
        path: '',
        name: 'secretariat-home',
        component: () => import('@/views/modules/secretariat/SecretariatHomeView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
```

(remplace le `redirect: '/secretariat/patients'` — supprimer cette ligne, elle n'est plus nécessaire).

- [ ] **Étape 5 : Nav + redirection post-login**

Dans `SecretaireLayout.vue`, ajouter `HomeIcon` aux imports et l'entrée en tête de `menuItems` :

```js
  {
    path: '/secretariat/',
    labelKey: 'secretariat.nav.home',
    icon: HomeIcon,
  },
```

Dans `LoginView.vue`, changer le `case 'secretaire'` (ajouté Tâche 1) :

```js
        case 'secretaire':
            return '/secretariat/';
```

- [ ] **Étape 6 : Vérification manuelle**

`npm run build`. Dans le navigateur : connexion `secretaire` → atterrissage sur `/secretariat/` (dashboard d'accueil, plus `/secretariat/patients`), 5 entrées de nav visibles et toutes fonctionnelles, cartes KPI affichant des valeurs réelles (pas des `NaN`/`undefined`), filtre de dates fonctionnel. Vérifier qu'aucune régression n'a été introduite sur les Tâches 1-6 (navigation complète du shell, aller-retour entre toutes les sections).

---

## Auto-revue (à faire par le contrôleur avant de lancer la Tâche 1, pas par un sous-agent)

- **Couverture de la spec :** les 5 sections de la spec (Patients, Stock, Caisse, Consultation Spirituelle, Dashboard) correspondent chacune à une ou plusieurs tâches ci-dessus (Tâche 1 / 2 / 3 / 4-6 / 7). Aucun écart identifié.
- **Cohérence des types :** `consultation_id` utilisé de façon cohérente entre `ConsultationGateway.js` (Tâche 4), `ConsultationModal.vue` (Tâche 5) et `ConsultationsList.vue` (Tâche 6). Noms de champs du payload (`patientId`, `typeConsultation`, `prescGeneric`, etc.) identiques entre la modale qui les émet (Tâche 5) et le gateway qui les consomme (Tâche 4).
- **Point d'incertitude assumé, pas un trou du plan :** le sous-objet `patient` dans les réponses `/cs/*` n'est pas confirmé (contrairement à `/medical_records/*`, corrigé au sous-projet précédent). Signalé explicitement aux Tâches 5 et 6 comme décision à documenter par l'exécutant plutôt que comme un gap à combler dans ce plan — corriger le backend `cs_endpoint.py`/`mapping.py` serait un élargissement de périmètre non demandé par la spec.
