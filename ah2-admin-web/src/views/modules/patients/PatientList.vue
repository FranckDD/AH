<template>
  <div class="space-y-6 w-full">
    
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('patients.title') }}
        </h1>
        <p class="text-sm text-gray-500">
          Total : {{ activeTabCount }} patients
        </p>
      </div>

      <div class="flex items-center gap-3">
        <button @click="showExportModal = true" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition">
          {{ t('export.confirm') }}
        </button>
        <button
            v-if="canManagePatients"
            @click="openCreateModal"
            class="flex items-center gap-2 bg-green-600 text-white px-4 py-2.5 rounded-xl hover:bg-green-700 font-medium shadow-xs transition"
        >
            <PlusIcon class="h-5 w-5" />
            Ajouter un patient
        </button>
      </div>

      <div class="relative w-full md:w-80">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
        </div>
        <input 
          v-model.lazy="searchQuery"
          @keyup.enter="patientStore.fetchPatients()"
          type="text"
          :placeholder="t('patients.search_placeholder')"
          class="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-xl bg-gray-50 focus:ring-green-500 focus:border-green-500 sm:text-sm"
        />
      </div>
    </div>

    <div class="border-b border-gray-200">
      <nav class="-mb-px flex space-x-8" aria-label="Tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.value"
          @click="currentTab = tab.value" 
          :class="[
            currentTab === tab.value
              ? 'border-green-500 text-green-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center'
          ]"
        >
          <component :is="tab.icon" class="h-5 w-5 mr-2" />
          {{ t(tab.labelKey) }}
          <span class="ml-2 bg-gray-100 text-gray-600 py-0.5 px-2.5 rounded-full text-xs font-bold">
            {{ tab.count }}
          </span>
        </button>
      </nav>
    </div>

    <div class="bg-white rounded-2xl shadow-xs border border-gray-100 overflow-hidden">
      
      <div v-if="patientStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></span>
        <p class="mt-2 text-gray-500">Chargement des données...</p>
      </div>

      <div v-else-if="patientStore.error" class="p-10 text-center text-red-500">
        {{ patientStore.error }}
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">Code / Patient</th>
              <th class="px-6 py-4 font-semibold">Type</th>
              <th class="px-6 py-4 font-semibold">Téléphone</th>
              <th class="px-6 py-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="patient in patientStore.patients" :key="patient.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <div class="flex flex-col">
                    <span class="text-xs font-bold text-gray-400 uppercase tracking-wide">{{ patient.code }}</span>
                    <span class="text-sm font-medium text-gray-900">{{ patient.firstName }} {{ patient.lastName }}</span>
                </div>
              </td>
              <td class="px-6 py-4">
                <span :class="getTypeBadgeClass(patient.type)" class="px-3 py-1 text-xs font-bold rounded-full border">
                  {{ patient.type }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">
                {{ patient.phone || 'N/A' }}
              </td>
              <td class="px-6 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                    <button v-if="canManagePatients" @click="openEditModal(patient)" :disabled="patient.pending"
                            class="p-2 bg-white border border-gray-200 rounded-lg text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200 transition shadow-xs disabled:opacity-40 disabled:cursor-not-allowed"
                            :title="patient.pending ? 'En attente de synchronisation' : 'Modifier'">
                        <PencilSquareIcon class="h-4 w-4" />
                    </button>
                    <button v-if="canManagePatients" @click="confirmDelete(patient)" :disabled="patient.pending"
                            class="p-2 bg-white border border-gray-200 rounded-lg text-red-500 hover:bg-red-50 hover:border-red-200 transition shadow-xs disabled:opacity-40 disabled:cursor-not-allowed"
                            :title="patient.pending ? 'En attente de synchronisation' : 'Supprimer'">
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
            </tr>
          </tbody>
        </table>
        
        <div v-if="patientStore.patients.length === 0" class="p-8 text-center text-gray-500">
            Aucun patient trouvé.
        </div>
      </div>

      <div class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <button 
            @click="goToPage(patientStore.pagination.page - 1)" 
            :disabled="patientStore.pagination.page === 1" 
            class="px-4 py-2 border rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50 flex items-center"
        >
            <ChevronLeftIcon class="h-4 w-4 mr-2"/> Précédent
        </button>

        <span class="text-sm font-medium text-gray-700">
            Page {{ patientStore.pagination.page }} sur {{ patientStore.pagination.total_pages }}
        </span>

        <button 
            @click="goToPage(patientStore.pagination.page + 1)" 
            :disabled="!patientStore.pagination.hasNext" 
            class="px-4 py-2 border rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50 flex items-center"
        >
            Suivant <ChevronRightIcon class="h-4 w-4 ml-2"/>
        </button>
      </div>

    </div>

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

    <ExportModal
      v-if="showExportModal"
      :title="t('export.confirm') + ' — ' + t('patients.title')"
      :formats="[{ value: 'pdf', label: 'PDF' }, { value: 'csv', label: 'CSV' }]"
      :onExport="exportPatients"
      @close="showExportModal = false"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { usePatientStore } from '@/stores/patientStore';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import {
    MagnifyingGlassIcon, UsersIcon, SparklesIcon,
    BeakerIcon, HeartIcon, ChevronLeftIcon, ChevronRightIcon,
    PlusIcon, PencilSquareIcon, TrashIcon
} from '@heroicons/vue/24/outline';
import PatientModal from '@/components/patients/PatientModal.vue';
import ExportModal from '@/components/common/ExportModal.vue';
import { useAuthStore } from '@/stores/auth';
import api from '@/services/api';

const props = defineProps({ disableDetailLink: { type: Boolean, default: false } });

const { t } = useI18n();
const patientStore = usePatientStore();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

// Roles avec droit d'ECRITURE (POST/PUT/DELETE) sur /patients - depuis le
// chantier L4b-e, distinct des roles avec droit de LECTURE au niveau du
// routeur (qui inclut aussi assistant et ToxicoManager pour la recherche,
// voir patients_endpoints.py). Assistant est volontairement absent ici :
// il garde /patients en lecture/recherche seule (dette parquee au
// chantier 6, refermee au chantier L4b-e).
const canManagePatients = computed(() =>
    authStore.hasRole(['medecin', 'nurse', 'secretaire', 'admin', 'manager'])
);

const showModal = ref(false);
const patientBeingEdited = ref(null);
const modalError = ref('');
const isSavingPatient = ref(false);
const deleteError = ref('');
const showExportModal = ref(false);

const exportPatients = async ({ format, dateFrom, dateTo }) => {
    const params = {
        format,
        type: patientStore.filters.type,
        search: patientStore.filters.search || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
    };
    const response = await api.get('/patients/export', {
        params,
        responseType: format === 'pdf' ? 'blob' : 'text',
    });
    const blob = format === 'pdf'
        ? new Blob([response.data], { type: 'application/pdf' })
        : new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `patients_export.${format}`;
    link.click();
    window.URL.revokeObjectURL(url);
};

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
        if (status === 409) return detail || "Ce patient existe peut-être déjà (identifiant en conflit).";
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

// 🟢 Chargement initial
onMounted(() => {
    patientStore.fetchPatients();
    // 🟢 Charger les compteurs globaux au montage
    patientStore.fetchCounts();
});

// 🟢 Configuration des Onglets (MAINTENANT COMPUTED)
const tabs = computed(() => {
    const tousLesOnglets = [
        {
            value: 'ALL',
            labelKey: 'patients.tabs.all',
            icon: UsersIcon,
            count: patientStore.counts.ALL
        },
        {
            value: 'CLINIQUE',
            labelKey: 'patients.tabs.clinical',
            icon: HeartIcon,
            count: patientStore.counts.CLINIQUE
        },
        {
            value: 'TOXICO',
            labelKey: 'patients.tabs.toxico',
            icon: BeakerIcon,
            count: patientStore.counts.TOXICO
        },
        {
            value: 'SPIRITUEL',
            labelKey: 'patients.tabs.spiritual',
            icon: SparklesIcon,
            count: patientStore.counts.SPIRITUEL
        },
    ];
    // medecin/nurse : le backend refuse desormais /patients/toxicology et
    // /patients/spiritual/list (403) - sans ce filtre, ces deux onglets
    // restaient cliquables et menaient a un cul-de-sac affiche comme
    // "Erreur de connexion au serveur", masquant un refus de permission
    // volontaire derriere un message d'erreur technique trompeur.
    if (authStore.hasRole(['medecin', 'nurse'])) {
        return tousLesOnglets.filter((t) => t.value !== 'TOXICO' && t.value !== 'SPIRITUEL');
    }
    return tousLesOnglets;
});

// Helper pour afficher le total de l'onglet actif sous le titre
const activeTabCount = computed(() => {
    const active = tabs.value.find(t => t.value === currentTab.value);
    return active ? active.count : 0;
});

// 3. Créer la fonction de navigation
// Relatif a route.path (pas de nom de route en dur) : ce composant est
// monte a la fois sous /dashboard/patients (admin/ToxicoManager) et
// /medical/patients (medecin/nurse) - un nom fige pointerait toujours
// vers /dashboard/patients/:id, hors de portee des roles medicaux.
const viewPatientDossier = (patientId) => {
    router.push(`${route.path}/${patientId}`);
};

// Getter/Setter pour la recherche
const searchQuery = computed({
    get: () => patientStore.filters.search,
    set: (val) => patientStore.setFilters({ search: val })
});

// Getter/Setter pour les onglets
const currentTab = computed({
    get: () => patientStore.filters.type,
    set: (val) => patientStore.setFilters({ type: val })
});

const goToPage = (page) => {
    patientStore.setPage(page);
};

const getTypeBadgeClass = (type) => {
    switch(type) {
        case 'CLINIQUE': return 'bg-blue-50 text-blue-700 border-blue-200';
        case 'TOXICO': return 'bg-purple-50 text-purple-700 border-purple-200';
        case 'SPIRITUEL': return 'bg-amber-50 text-amber-700 border-amber-200'; 
        default: return 'bg-gray-100 text-gray-600 border-gray-200';
    }
};
</script>