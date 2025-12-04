<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-75 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    
    <div class="relative mx-auto w-full max-w-4xl bg-white shadow-2xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
      
      <div v-if="isLoading" class="p-20 flex justify-center items-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>

      <div v-else-if="!patient" class="p-10 text-center">
          <p class="text-red-500 mb-4">Impossible de charger le dossier.</p>
          <button @click="$emit('close')" class="text-indigo-600 hover:underline">Fermer</button>
      </div>

      <div v-else class="flex flex-col h-full">
          <div class="px-6 py-5 border-b border-gray-100 bg-indigo-50 rounded-t-2xl flex justify-between items-start flex-shrink-0">
            <div class="flex items-center">
                <div class="h-12 w-12 rounded-full bg-indigo-200 flex items-center justify-center text-indigo-700 font-bold text-xl mr-4 uppercase">
                    {{ (patient.firstName ? patient.firstName.charAt(0) : '?') }}
                </div>
                <div>
                    <h3 class="text-xl font-bold text-gray-900">
                        {{ patient.firstName }} {{ patient.lastName }}
                    </h3>
                    <p class="text-sm text-indigo-600 font-medium">
                        Code: {{ patient.code }} • Substance: {{ patient.substance }}
                    </p>
                </div>
            </div>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 bg-white p-2 rounded-full shadow-sm transition">
                <span class="text-2xl font-bold">&times;</span>
            </button>
          </div>

          <div class="bg-white border-b border-gray-200 px-6 flex-shrink-0">
              <nav class="-mb-px flex space-x-8">
                  <button 
                    v-for="tab in tabs" 
                    :key="tab.id"
                    @click="currentTab = tab.id"
                    :class="[
                      currentTab === tab.id 
                        ? 'border-indigo-500 text-indigo-600' 
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                      'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center'
                    ]"
                  >
                      <component :is="tab.icon" class="h-5 w-5 mr-2" />
                      {{ t(tab.label) }}
                  </button>
              </nav>
          </div>

          <div class="p-6 overflow-y-auto bg-gray-50 flex-1">
            
            <div v-if="currentTab === 'history'" class="space-y-6">
                <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
                    <h4 class="text-sm font-bold text-gray-700 uppercase mb-4">Progression</h4>
                    <div class="relative pt-1">
                        <div class="overflow-hidden h-4 mb-4 text-xs flex rounded bg-indigo-100">
                            <div :style="{ width: ((patient.currentPhase || 1) / 4) * 100 + '%' }" class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-indigo-500 transition-all duration-500"></div>
                        </div>
                        <div class="flex justify-between text-xs text-gray-500 font-medium">
                            <span>Phase 1</span><span>Phase 2</span><span>Phase 3</span><span>Phase 4</span>
                        </div>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
                    <h4 class="text-sm font-bold text-gray-700 uppercase mb-4">{{ t('toxico.dossier.tabs.history') }}</h4>
                    
                    <div v-if="patient.phaseHistory && patient.phaseHistory.length > 0" class="relative border-l-2 border-indigo-200 ml-3 space-y-6">
                        <div v-for="(phase, index) in patient.phaseHistory" :key="index" class="mb-8 ml-6">
                            <span class="absolute flex items-center justify-center w-6 h-6 bg-indigo-100 rounded-full -left-3 ring-4 ring-white">
                                <span class="w-2 h-2 bg-indigo-600 rounded-full"></span>
                            </span>
                            <div class="bg-gray-50 p-3 rounded-lg border border-gray-200">
                                <h5 class="flex items-center mb-1 text-sm font-semibold text-gray-900">
                                    {{ t(`toxico.phases.${phase.phase}`) }}
                                    <span v-if="phase.status && phase.status.includes('Terminé')" class="bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded-full ml-2">{{ phase.status }}</span>
                                    <span v-else class="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full ml-2">{{ phase.status }}</span>
                                </h5>
                                <time class="block mb-2 text-xs font-normal leading-none text-gray-400">
                                    {{ formatDate(phase.start_date) }} <span v-if="phase.end_date"> - {{ formatDate(phase.end_date) }}</span>
                                </time>
                                <p class="text-sm font-normal text-gray-600">{{ phase.comments }}</p>
                            </div>
                        </div>
                    </div>
                    <div v-else class="text-center text-gray-500 py-4 italic">Aucun historique disponible.</div>
                </div>
            </div>

            <div v-if="currentTab === 'medical'" class="space-y-6">
                <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
                    <h4 class="text-sm font-bold text-gray-700 uppercase mb-4">{{ t('toxico.dossier.tabs.medical') }}</h4>
                    <p class="text-gray-500 text-center py-4">Intégration du dossier médical complet en cours...</p>
                </div>
            </div>

            <div v-if="currentTab === 'prescriptions'" class="space-y-6">
                <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
                    <h4 class="text-sm font-bold text-gray-700 uppercase mb-4">{{ t('toxico.dossier.tabs.prescriptions') }}</h4>
                    <p class="text-gray-500 text-center py-4">Intégration des prescriptions en cours...</p>
                </div>
            </div>

          </div>

          <div class="px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-2xl flex justify-end flex-shrink-0">
            <button @click="$emit('close')" class="px-5 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium transition shadow-md">
                Fermer le dossier
            </button>
          </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { ClockIcon, HeartIcon, BeakerIcon } from '@heroicons/vue/24/outline';

const { t } = useI18n();
const toxicoStore = useToxicoStore();

const props = defineProps({
  patientId: { type: Number, required: true }
});

const emit = defineEmits(['close']);

// Initialiser avec un objet vide évite parfois des erreurs, 
// mais ici on utilise v-if="!patient" donc null est correct pour l'état initial.
const patient = ref(null);
const isLoading = ref(true);
const currentTab = ref('history');

const tabs = [
    { id: 'history', label: 'toxico.dossier.tabs.history', icon: ClockIcon },
    { id: 'medical', label: 'toxico.dossier.tabs.medical', icon: HeartIcon },
    { id: 'prescriptions', label: 'toxico.dossier.tabs.prescriptions', icon: BeakerIcon },
];

const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
        return new Date(dateStr).toLocaleDateString();
    } catch (e) {
        return dateStr;
    }
};

onMounted(async () => {
    isLoading.value = true;
    try {
        // Le store appelle l'API get_patient_detail qui renvoie { firstName, lastName, phaseHistory... }
        const data = await toxicoStore.getPatientDetails(props.patientId);
        patient.value = data;
        console.log("✅ Données patient chargées dans Modal:", data);
    } catch (e) {
        console.error("❌ Erreur chargement dossier:", e);
    } finally {
        isLoading.value = false;
    }
});
</script>