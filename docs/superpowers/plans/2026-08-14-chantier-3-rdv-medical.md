# Chantier 3 — Fenêtre médicale, Étape 1 : Rendez-vous (shell + modale) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner à `medecin`/`nurse` leur propre shell de dashboard indépendant (`MedicalLayout.vue`), les rediriger dessus après login, et y monter un module Rendez-vous complet (liste déjà construite + création/édition via une nouvelle modale).

**Architecture:** Nouveau shell `MedicalLayout.vue` (même patron que `MainLayout.vue` mais navigation propre, aucun partage de `menuItems`), nouvelle branche de route `/medical/...`, remontage de `AppointmentsList.vue`/`appointmentStore.js`/`AppointmentGateway.js`/`StatusBadge.vue` (déjà construits, actuellement non référencés par aucune route), et une nouvelle `AppointmentModal.vue` portant la logique métier de `book_appoint_view.py` (recherche patient par code, spécialité, créneau 30 min).

**Tech Stack:** Vue 3 (Composition API, `<script setup>`), Pinia (stores existants), vue-router 4, vue-i18n, Tailwind CSS, axios (`src/services/api.js`). Pas de framework de test frontend configuré (`package.json` n'a que `dev`/`build`/`preview`) — la vérification de chaque étape se fait par `npm run build` (compilation/types) + test manuel navigateur.

**Spec:** `docs/superpowers/specs/2026-08-13-chantier-3-fenetre-medicale-design.md`

## Global Constraints

- Architecture REST classique uniquement — aucune préparation PowerSync dans ce chantier (décision utilisateur explicite, chantier 4 séparé).
- `MedicalLayout.vue` est indépendant de `MainLayout.vue` : ne pas modifier `MainLayout.vue`, ne pas réutiliser son `menuItems`/`filteredMenu`. Aucune régression sur les rôles déjà servis par `MainLayout.vue`.
- `medecin` et `nurse` partagent le même shell (comme `DashboardView` côté desktop) — pas de filtrage de navigation par rôle à l'intérieur de `MedicalLayout.vue`.
- Le bouton "Accepter" ne doit jamais être ajouté côté web (registre C4, `docs/superpowers/SUIVI-AVANCEMENT.md`) — seuls "Compléter" et "Refuser" existent, déjà en place dans `AppointmentsList.vue`.
- Les 3 seuls statuts réels sont `pending`/`cancelled`/`completed` (`APPOINTMENT_STATUSES` dans `appointmentStore.js`) — ne pas en introduire d'autres.
- Créneaux horaires : pas de 30 minutes, 08:00 à 18:30 (port exact de `book_appoint_view.py`).
- **Ne rien committer.** Tous les fichiers touchés par ce plan (nouveaux et modifiés) sont soit déjà en WIP non commité de l'utilisateur (`router/index.js`, `LoginView.vue`, `i18n.js`, `AppointmentsList.vue`), soit de nouveaux fichiers destinés à rester non commités jusqu'à relecture explicite de l'utilisateur — même convention que `AppointmentGateway.js`/`appointmentStore.js`/`AppointmentsList.vue`/`StatusBadge.vue` construits plus tôt dans ce chantier. Aucune étape de ce plan ne doit exécuter `git add`/`git commit`.

---

### Task 1 : `MedicalLayout.vue` + route `/medical` + correction de la redirection post-login

**Files:**
- Create: `ah2-admin-web/src/components/layout/MedicalLayout.vue`
- Modify: `ah2-admin-web/src/router/index.js`
- Modify: `ah2-admin-web/src/views/LoginView.vue`
- Test: manuel (pas de framework de test frontend) — voir Step 4

**Interfaces:**
- Consumes: `useAuthStore` (`src/stores/auth.js`, déjà existant — `user`, `userRole`, `logout()`), `useConfigStore` (`src/stores/configStore.js` — `structureInfo`, `fetchStructureInfo()`), route déjà existante `AppointmentsList.vue` à `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue`.
- Produces: route nommée `medical-appointments` sur le chemin `/medical/appointments`, montée sous le shell `MedicalLayout.vue`. Les tâches suivantes (2 et 3) ne dépendent pas de cette route par son nom, seulement du fait que `AppointmentsList.vue` est désormais atteignable et fonctionnelle dans le navigateur.

- [ ] **Step 1 : Créer `MedicalLayout.vue`**

Créer `ah2-admin-web/src/components/layout/MedicalLayout.vue` avec ce contenu exact :

```vue
<template>
  <div class="flex w-full h-screen bg-gray-50">

    <aside
      :class="[
        'bg-slate-800 text-white flex-shrink-0 transition-all duration-300 ease-in-out flex flex-col z-20',
        isSidebarOpen ? 'w-64' : 'w-20'
      ]"
    >
      <div class="p-4 flex items-center justify-between h-16 bg-slate-900 overflow-hidden">
        <div v-if="isSidebarOpen" class="flex items-center space-x-2 min-w-0">
          <img
            v-if="configStore.structureInfo.logo_url"
            :src="configStore.structureInfo.logo_url"
            class="h-8 w-8 object-contain bg-white rounded-full p-0.5 flex-shrink-0"
            alt="Logo"
          />
          <div v-else class="h-8 w-8 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-xs flex-shrink-0">
            {{ (configStore.structureInfo.name || 'AH').substring(0,2).toUpperCase() }}
          </div>

          <h2 class="text-lg font-bold truncate">{{ configStore.structureInfo.name || 'AH2 Médical' }}</h2>
        </div>

        <button
          @click="toggleSidebar"
          :class="[
            'p-1 rounded hover:bg-slate-700 text-gray-400 hover:text-white transition-colors',
            isSidebarOpen ? 'ml-auto' : 'mx-auto'
          ]"
        >
          <Bars3CenterLeftIcon v-if="isSidebarOpen" class="h-6 w-6" />
          <Bars3Icon v-else class="h-6 w-6" />
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto py-4 space-y-2 px-2 custom-scrollbar">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'flex items-center py-2 px-3 rounded transition duration-150 group',
            isActive(item.path)
              ? 'bg-slate-700 font-semibold text-white'
              : 'text-gray-400 hover:bg-slate-700 hover:text-white'
          ]"
          :title="!isSidebarOpen ? t(item.labelKey) : ''"
        >
          <component
            :is="item.icon"
            class="h-6 w-6 flex-shrink-0"
            :class="isSidebarOpen ? 'mr-3' : 'mx-auto'"
          />
          <span v-if="isSidebarOpen" class="whitespace-nowrap transition-opacity duration-200">
            {{ t(item.labelKey) }}
          </span>
        </router-link>
      </nav>
    </aside>

    <div class="flex-1 flex flex-col overflow-hidden w-full">

      <header class="bg-white shadow-md p-4 flex justify-between items-center z-10">

        <h1 class="text-lg font-semibold text-gray-800">
          {{ $t('common.welcome') }}, <span class="text-emerald-600">{{ authStore.user?.username || 'Utilisateur' }}</span>
          <span class="text-xs text-gray-400 ml-2 font-normal">({{ authStore.userRole }})</span>
        </h1>

        <div class="flex items-center space-x-4">
          <div class="flex bg-gray-100 rounded-lg p-1">
            <button
              @click="changeLanguage('fr')"
              :class="locale === 'fr' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >FR</button>
            <button
              @click="changeLanguage('en')"
              :class="locale === 'en' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >EN</button>
          </div>

          <button
            @click="handleLogout"
            class="bg-red-500 hover:bg-red-600 text-white text-sm font-semibold py-2 px-4 rounded transition duration-150"
          >
            {{ $t('common.logout') }}
          </button>
        </div>
      </header>

      <main class="flex-1 overflow-x-hidden overflow-y-auto p-6 bg-gray-100 w-full">
        <router-view :key="route.fullPath" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useConfigStore } from '@/stores/configStore';

import {
  CalendarIcon,
  Bars3Icon,
  Bars3CenterLeftIcon
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();
const configStore = useConfigStore();
const router = useRouter();
const route = useRoute();
const { locale, t } = useI18n();

const isSidebarOpen = ref(true);

// Navigation propre a la fenetre medicale (medecin + nurse partagent le
// meme shell, comme DashboardView cote desktop) - pas de filtrage par
// role ici, contrairement a MainLayout.vue : ce shell n'est jamais charge
// par un autre role (garde deja faite par le routeur, meta.roles).
// Etendu au fil des etapes 2-5 du chantier 3 (Prescription, Dossier
// Medical, Patients, Medecins).
const menuItems = [
  {
    path: '/medical/appointments',
    labelKey: 'appointments.title',
    icon: CalendarIcon,
  },
];

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

const changeLanguage = (lang) => {
  locale.value = lang;
  localStorage.setItem('lang', lang);
};

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};

const isActive = (path) => {
  return route.path.includes(path);
};

onMounted(() => {
  configStore.fetchStructureInfo();
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: #1e293b;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 2px;
}
</style>
```

- [ ] **Step 2 : Ajouter la branche de route `/medical` dans `router/index.js`**

Dans `ah2-admin-web/src/router/index.js`, modifier le bloc `ROLES` (ligne 10-16) pour ajouter `MEDECIN` et `NURSE` :

```js
const ROLES = {
  ADMIN: 'admin',
  PSYCHOLOGIST: 'Psychologist',
  SPIRITUAL: 'SpiritualCounsellor',
  TOXICO_MANAGER: 'ToxicoManager',
  ASSISTANT: 'Assistant',
  MEDECIN: 'medecin',
  NURSE: 'nurse'
};
```

Puis, juste après la fermeture du bloc `/dashboard` (après la ligne `]` qui ferme `children` et avant la ligne `},` qui ferme l'objet de route `/dashboard`, c'est-à-dire juste après la dernière route `logs` du bloc existant), ajouter une toute nouvelle route de premier niveau `/medical`, insérée entre la fermeture de l'objet `/dashboard` et le commentaire `// Routes de secours` :

```js
  // --- ROUTE PARENT : /medical (fenetre medicale independante, medecin+nurse) ---
  {
    path: '/medical',
    component: () => import('@/components/layout/MedicalLayout.vue'),
    meta: { requiresAuth: true },
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
  },

```

Cette nouvelle route doit être un frère (sibling) du bloc `/dashboard` existant, pas un enfant — `MedicalLayout.vue` est un shell de premier niveau, exactement comme `MainLayout.vue`. Ne touche à aucune ligne du bloc `/dashboard` existant.

- [ ] **Step 3 : Corriger la redirection post-login dans `LoginView.vue`**

Dans `ah2-admin-web/src/views/LoginView.vue`, dans `getRedirectPath(role)`, ajouter un cas pour `medecin`/`nurse` avant le `default` :

```js
        case 'ToxicoManager':
        case 'Assistant':
            // Le manager Toxico a aussi intérêt à voir le dashboard Toxico en premier
            return '/dashboard/toxico-dashboard';

        case 'medecin':
        case 'nurse':
            // Fenetre medicale independante (chantier 3) - jamais le dashboard toxico
            return '/medical/appointments';

        default:
```

(Remplace le bloc existant qui va de `case 'ToxicoManager':` jusqu'à `default:` par la version ci-dessus — seule l'insertion du nouveau `case` change, le reste est identique.)

- [ ] **Step 4 : Vérifier la compilation et tester manuellement**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur (aucun import cassé, aucune erreur de syntaxe Vue).

Test manuel (le serveur `npm run dev` a un problème `EACCES` connu localement, non lié à ce chantier — si bloqué, utiliser `npm run preview` après le build, ou signaler le blocage) :
1. Se connecter avec un compte `medecin` ou `nurse`.
2. Vérifier l'arrivée sur `/medical/appointments`, jamais sur `/dashboard/overview` ou `/dashboard/toxico-dashboard`.
3. Vérifier que le shell affiche la sidebar avec une seule entrée "Rendez-vous", le header avec le nom d'utilisateur/rôle, le switch FR/EN, et le bouton de déconnexion.
4. Vérifier que la liste des rendez-vous se charge (ou affiche l'état vide si la base est vide).
5. Se connecter avec un compte `admin` existant et vérifier qu'il continue d'arriver sur `/dashboard/overview` comme avant (pas de régression).

- [ ] **Step 5 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit` sur `MedicalLayout.vue`, `router/index.js` ou `LoginView.vue`. Passer directement à la tâche suivante.

---

### Task 2 : `AppointmentModal.vue` (création/édition)

**Files:**
- Create: `ah2-admin-web/src/components/appointments/AppointmentModal.vue`
- Modify: `ah2-admin-web/src/i18n.js`
- Test: manuel (pas de framework de test frontend) — voir Step 3

**Interfaces:**
- Consumes: `useAppointmentStore` (`src/stores/appointmentStore.js`, déjà existant — `specialties` ref, déjà peuplé par `AppointmentsList.vue` via `fetchSpecialties()` avant que la modale ne puisse être ouverte), `api` (`src/services/api.js`, instance axios partagée), endpoint `GET /patients/` avec le paramètre `search` (même contrat que `patientStore.fetchPatients()` dans `src/stores/patientStore.js:60`, qui renvoie soit un tableau brut soit `{ data: [...] }`, et où chaque patient a les champs `id`/`patient_id`, `code_patient`, `first_name`, `last_name`).
- Produces: composant `AppointmentModal.vue` avec `props: { appointment: Object|null }` (`null`/absent = mode création, objet = mode édition) et `emits: ['close', 'save']`. L'événement `save` transporte exactement `{ patientId, specialty, appointmentDate, appointmentTime, reason }` — la Task 3 doit passer cet objet tel quel à `appointmentStore.createAppointment(data)`/`updateAppointment(id, data)`, dont les gateways (`AppointmentGateway.js:33-53`) attendent déjà précisément ces clés (`data.patientId`, `data.specialty`, `data.appointmentDate`, `data.appointmentTime`, `data.reason`).

- [ ] **Step 1 : Créer `AppointmentModal.vue`**

Créer `ah2-admin-web/src/components/appointments/AppointmentModal.vue` avec ce contenu exact :

```vue
<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-md shadow-xl rounded-2xl bg-white">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('appointments.modal.title_edit') : t('appointments.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            placeholder="Ex: AH2-000818AQ"
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
          />
          <p class="mt-1 text-xs" :class="patientId ? 'text-emerald-600' : 'text-gray-400'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.specialty') }}</label>
          <select v-model="form.specialty" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm">
            <option value="">{{ t('appointments.modal.specialty_none') }}</option>
            <option v-for="spec in appointmentStore.specialties" :key="spec" :value="spec">{{ spec }}</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.date') }}</label>
            <input
              v-model="form.appointmentDate"
              type="date"
              required
              class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.time') }}</label>
            <select v-model="form.appointmentTime" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm">
              <option value="" disabled>--:--</option>
              <option v-for="slot in timeSlots" :key="slot" :value="slot">{{ slot }}</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.reason') }}</label>
          <textarea
            v-model="form.reason"
            rows="2"
            placeholder="Ex: Consultation de suivi..."
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
          ></textarea>
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-sm">
            {{ t('appointments.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition bg-emerald-600 hover:bg-emerald-700">
            {{ t('appointments.modal.save') }}
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
import { useAppointmentStore } from '@/stores/appointmentStore';

const { t } = useI18n();
const appointmentStore = useAppointmentStore();
const emit = defineEmits(['close', 'save']);

const props = defineProps({
  appointment: {
    type: Object,
    default: null,
  },
});

const isEdit = computed(() => !!props.appointment);

const patientCode = ref('');
const patientId = ref(null);
const patientName = ref('');
const patientLookupMessage = ref('');

const form = reactive({
  specialty: '',
  appointmentDate: '',
  appointmentTime: '',
  reason: '',
});

// Creneaux de 30 min, 08:00-18:30 - port exact de book_appoint_view.py
// (f"{h:02d}:{m:02d}" for h in range(8, 19) for m in (0, 30))
const timeSlots = computed(() => {
  const slots = [];
  for (let h = 8; h <= 18; h++) {
    for (const m of [0, 30]) {
      slots.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
    }
  }
  return slots;
});

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

  try {
    const res = await api.get('/patients/', { params: { search: code, per_page: 5 } });
    const list = Array.isArray(res.data) ? res.data : (res.data.data || []);
    const match = list.find((p) => p.code_patient === code) || list[0] || null;

    if (!match) {
      patientId.value = null;
      patientName.value = '';
      patientLookupMessage.value = t('appointments.modal.patient_not_found');
      return;
    }

    patientId.value = match.id || match.patient_id;
    patientName.value = [match.first_name, match.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  } catch (err) {
    console.error('Erreur recherche patient:', err);
    patientId.value = null;
    patientName.value = '';
    patientLookupMessage.value = t('appointments.modal.patient_not_found');
  }
}

onMounted(() => {
  if (props.appointment) {
    const appt = props.appointment;
    patientId.value = appt.patient_id || appt.patient?.patient_id || null;
    patientCode.value = appt.patient?.code_patient || '';
    patientName.value = [appt.patient?.first_name, appt.patient?.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
    form.specialty = appt.specialty || '';
    form.appointmentDate = (appt.appointment_date || '').substring(0, 10);
    form.appointmentTime = appt.appointment_time || '';
    form.reason = appt.reason || '';
  }
});

function handleSubmit() {
  if (!patientId.value) {
    alert(t('appointments.modal.patient_not_found'));
    return;
  }

  emit('save', {
    patientId: patientId.value,
    specialty: form.specialty,
    appointmentDate: form.appointmentDate,
    appointmentTime: form.appointmentTime,
    reason: form.reason,
  });
}
</script>
```

- [ ] **Step 2 : Ajouter les clés i18n de la modale**

Dans `ah2-admin-web/src/i18n.js`, dans le bloc `appointments` du français (commence ligne 115), ajouter une section `modal` juste après `actions` (avant la fermeture `},` du bloc `appointments` français) :

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
```

Dans le bloc `appointments` de l'anglais (commence ligne 653), même ajout avec les traductions anglaises, juste après `actions` :

```js
      actions: {
        complete: "Complete",
        cancel: "Reject",
        edit: "Edit"
      },
      modal: {
        title_new: "New Appointment",
        title_edit: "Edit Appointment",
        patient_code: "Patient Code",
        specialty: "Specialty",
        specialty_none: "-- None --",
        date: "Date",
        time: "Time",
        reason: "Reason",
        cancel: "Cancel",
        save: "Save",
        patient_not_found: "Patient not found"
      }
```

- [ ] **Step 3 : Vérifier la compilation**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur. `AppointmentModal.vue` n'est encore référencé par aucune vue à ce stade (Task 3 le fait) — le build valide uniquement qu'il compile de façon isolée (pas d'import cassé, syntaxe Vue/JS valide).

- [ ] **Step 4 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Passer à la tâche suivante.

---

### Task 3 : Câbler `AppointmentModal.vue` dans `AppointmentsList.vue`

**Files:**
- Modify: `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue`
- Test: manuel (pas de framework de test frontend) — voir Step 3

**Interfaces:**
- Consumes: `AppointmentModal.vue` de la Task 2 (`props: { appointment }`, `emits: ['close', 'save']`, payload `save` = `{ patientId, specialty, appointmentDate, appointmentTime, reason }`), `appointmentStore.createAppointment(data)`/`updateAppointment(id, data)` déjà existants (`src/stores/appointmentStore.js:81-90`).
- Produces: parcours complet création/édition de rendez-vous fonctionnel dans le navigateur — rien de plus n'en dépend dans ce plan (dernière tâche).

- [ ] **Step 1 : Remplacer les imports et les stubs dans `AppointmentsList.vue`**

Dans `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue`, remplacer le bloc d'imports (lignes 179-188) :

```js
import { ref, computed, onMounted } from 'vue';
import { useAppointmentStore, APPOINTMENT_STATUSES } from '@/stores/appointmentStore';
import { useI18n } from 'vue-i18n';
import StatusBadge from '@/components/appointments/StatusBadge.vue';
import AppointmentModal from '@/components/appointments/AppointmentModal.vue';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/vue/24/outline';
```

Puis remplacer les stubs `openCreateModal`/`openEditModal` (lignes 237-246, y compris le commentaire qui les précède) par :

```js
const showModal = ref(false);
const editingAppointment = ref(null);

function openCreateModal() {
  editingAppointment.value = null;
  showModal.value = true;
}

function openEditModal(appt) {
  editingAppointment.value = appt;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingAppointment.value = null;
}

async function handleSave(data) {
  if (editingAppointment.value) {
    await appointmentStore.updateAppointment(editingAppointment.value.appointment_id, data);
  } else {
    await appointmentStore.createAppointment(data);
  }
  closeModal();
}
```

- [ ] **Step 2 : Remplacer le commentaire placeholder par la modale dans le template**

Dans le `<template>` de `AppointmentsList.vue`, remplacer ce bloc de commentaire :

```html
    <!--
      AppointmentModal.vue (creation/edition) : pas encore construit dans
      cette passe de design, meme role que book_appoint_view.py cote
      desktop (recherche patient par code, specialite, date, creneau
      30 min 08:00-18:30, raison). A faire dans un second temps, meme
      convention que FinanceModal.vue.
    -->
```

par :

```html
    <AppointmentModal
      v-if="showModal"
      :appointment="editingAppointment"
      @close="closeModal"
      @save="handleSave"
    />
```

- [ ] **Step 3 : Vérifier la compilation et tester manuellement**

Run: `cd ah2-admin-web && npm run build`
Expected: build réussit sans erreur.

Test manuel (connecté en tant que `medecin`/`nurse`, sur `/medical/appointments`) :
1. Cliquer sur "Prendre RDV" → la modale s'ouvre, vide, en mode création.
2. Saisir un code patient existant (ou un extrait de nom/code — la recherche utilise le même paramètre `search` que la page Patients) dans le champ code, sortir du champ (blur) → le nom du patient s'affiche en dessous en vert.
3. Saisir un code patient inexistant → le message "Patient introuvable" s'affiche.
4. Choisir une spécialité (si la liste est vide en base, vérifier que l'option "-- Aucune --" reste sélectionnable sans bloquer la soumission), une date, un créneau horaire (vérifier que la liste va bien de 08:00 à 18:30 par pas de 30 minutes), un motif, puis "Enregistrer" → la modale se ferme, le nouveau rendez-vous apparaît dans la liste.
5. Cliquer sur "Éditer" sur un rendez-vous existant → la modale s'ouvre pré-remplie (code patient, spécialité, date, heure, motif). Modifier le motif et enregistrer → la liste reflète la modification.
6. Vérifier qu'aucun bouton "Accepter" n'apparaît nulle part (conforme au registre C4).

- [ ] **Step 4 : Ne pas committer**

Conformément aux Global Constraints, ne pas exécuter `git add`/`git commit`. Ceci termine l'Étape 1 (Rendez-vous) du chantier 3 — rapporter l'état à l'utilisateur pour relecture avant de passer à l'Étape 2 (Prescription) de la spec.
