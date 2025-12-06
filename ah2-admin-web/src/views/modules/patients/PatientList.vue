<template>
  <div class="space-y-6 w-full">
    
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('patients.title') }}
        </h1>
        <p class="text-sm text-gray-500">
          Total : {{ activeTabCount }} patients
        </p>
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

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      
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
                <button 
                    @click="viewPatientDossier(patient.id)" 
                    class="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center justify-end w-full"
                >
                    Voir Dossier 
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                </button>
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
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { usePatientStore } from '@/stores/patientStore';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { 
    MagnifyingGlassIcon, UsersIcon, SparklesIcon, 
    BeakerIcon, HeartIcon, ChevronLeftIcon, ChevronRightIcon 
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const patientStore = usePatientStore();
const router = useRouter();

// 🟢 Chargement initial
onMounted(() => {
    patientStore.fetchPatients();
    // 🟢 Charger les compteurs globaux au montage
    patientStore.fetchCounts();
});

// 🟢 Configuration des Onglets (MAINTENANT COMPUTED)
const tabs = computed(() => [
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
]);

// Helper pour afficher le total de l'onglet actif sous le titre
const activeTabCount = computed(() => {
    const active = tabs.value.find(t => t.value === currentTab.value);
    return active ? active.count : 0;
});

// 3. Créer la fonction de navigation
const viewPatientDossier = (patientId) => {
    router.push({ 
        name: 'PatientDetail', 
        params: { id: patientId } 
    });
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