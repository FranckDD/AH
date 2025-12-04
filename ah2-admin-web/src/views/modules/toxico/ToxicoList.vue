<template>
  <div class="space-y-6 w-full">
    
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('toxico.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ toxicoStore.totalActive }} patients suivis</p>
      </div>
      
      <div class="flex space-x-3 w-full md:w-auto">
          <div class="relative w-full md:w-64">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
            </div>
            <input 
                :value="toxicoStore.filters.search"
                @input="handleSearch"
                type="text"
                :placeholder="t('common.search_placeholder') || 'Rechercher...'"
                class="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-xl bg-gray-50 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>

          <button 
                @click="showAdmissionModal = true" 
                class="flex items-center px-6 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 shadow-md transition font-semibold"
            >
                <PlusCircleIcon class="h-5 w-5 mr-2" />
                {{ t('toxico.new_admission') }}
            </button>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        
        <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
            <div class="flex justify-between items-start">
                <div>
                    <p class="text-xs font-bold text-gray-500 uppercase tracking-wider">Patients Actifs</p>
                    <h3 class="text-2xl font-extrabold text-gray-900 mt-1">{{ toxicoStore.totalActive }}</h3>
                </div>
                <div class="p-2 bg-blue-50 rounded-lg">
                    <UserGroupIcon class="h-5 w-5 text-blue-600" />
                </div>
            </div>
            <div class="mt-4 flex items-center text-xs text-green-600 font-medium">
                <ArrowTrendingUpIcon class="h-3 w-3 mr-1" />
                <span>+{{ newPatientsThisWeek }} cette semaine</span>
            </div>
        </div>

        <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
            <div class="flex justify-between items-start">
                <div>
                    <p class="text-xs font-bold text-gray-500 uppercase tracking-wider">Admissions (Mois)</p>
                    <h3 class="text-2xl font-extrabold text-indigo-900 mt-1">
                        {{ toxicoStore.currentMonthAdmissions }}
                    </h3>
                </div>
                <div class="p-2 bg-indigo-50 rounded-lg">
                    <CalendarIcon class="h-5 w-5 text-indigo-600" />
                </div>
            </div>
            <p class="mt-4 text-xs text-indigo-400">Dossiers créés ce mois-ci</p>
        </div>

        <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
            <div class="flex justify-between items-start">
                <div>
                    <p class="text-xs font-bold text-gray-500 uppercase tracking-wider">Taux de Rechute</p>
                    <h3 class="text-2xl font-extrabold text-gray-900 mt-1">{{ toxicoStore.relapseRate }}%</h3>
                </div>
                <div class="p-2 bg-red-50 rounded-lg">
                    <ExclamationCircleIcon class="h-5 w-5 text-red-600" />
                </div>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-1.5 mt-4">
                <div class="bg-red-500 h-1.5 rounded-full transition-all duration-1000" :style="{ width: toxicoStore.relapseRate + '%' }"></div>
            </div>
        </div>

        <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
            <div class="flex justify-between items-start">
                <div>
                    <p class="text-xs font-bold text-gray-500 uppercase tracking-wider">En Sevrage (P1)</p>
                    <h3 class="text-2xl font-extrabold text-gray-900 mt-1">{{ toxicoStore.statsByPhase[1] || 0 }}</h3>
                </div>
                <div class="p-2 bg-orange-50 rounded-lg">
                    <FireIcon class="h-5 w-5 text-orange-600" />
                </div>
            </div>
            <p class="mt-4 text-xs text-orange-400">Surveillance accrue requise</p>
        </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div v-if="toxicoStore.isLoading" class="p-10 text-center text-gray-500 flex flex-col items-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-2"></div>
            {{ t('common.loading') }}
        </div>

        <div v-else-if="toxicoStore.patients.length === 0" class="p-10 text-center text-gray-500">
            Aucun patient trouvé.
        </div>

        <div v-else class="overflow-x-auto">
            <table class="min-w-full text-left border-collapse">
                <thead>
                    <tr class="bg-indigo-50 text-indigo-900 text-xs uppercase tracking-wider">
                        <th class="px-6 py-4 font-semibold">{{ t('toxico.table.patient') }}</th>
                        <th class="px-6 py-4 font-semibold">{{ t('toxico.table.phase') }}</th>
                        <th class="px-6 py-4 font-semibold text-center">Rechutes</th> 
                        <th class="px-6 py-4 font-semibold">{{ t('toxico.table.psy') }}</th>
                        <th class="px-6 py-4 font-semibold text-right">{{ t('toxico.table.actions') }}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="p in toxicoStore.patients" :key="p.patient_id" class="hover:bg-gray-50 transition">
                        <td class="px-6 py-4">
                            <div class="font-medium text-gray-900">{{ p.patientName }}</div>
                            <div class="text-xs text-gray-500 font-mono mb-1">{{ p.code }}</div>
                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
                                {{ p.substance }}
                            </span>
                        </td>
                        <td class="px-6 py-4">
                            <span :class="getPhaseColor(p.currentPhase)" class="px-3 py-1 text-xs font-bold rounded-full border shadow-sm">
                                {{ t(`toxico.phases.${p.currentPhase}`) }}
                            </span>
                            <div class="w-24 h-1.5 bg-gray-200 rounded-full mt-2 overflow-hidden">
                                <div class="h-full bg-indigo-500" :style="{ width: (p.currentPhase / 4) * 100 + '%' }"></div>
                            </div>
                        </td>
                        <td class="px-6 py-4 text-center">
                            <span v-if="p.relapseCount > 0" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700 animate-pulse">
                                ⚠️ {{ p.relapseCount }}
                            </span>
                            <span v-else class="text-gray-400 text-xs">-</span>
                        </td>
                        <td class="px-6 py-4 text-sm text-gray-600">
                            <div class="flex items-center">
                                <UserIcon class="h-4 w-4 mr-1 text-gray-400" />
                                {{ p.psychologist }}
                            </div>
                        </td>
                        <td class="px-6 py-4 text-right space-x-2">

                            <button 
                                @click="openPatientDetails(p)"
                                class="text-gray-600 hover:text-gray-900 bg-gray-50 hover:bg-gray-100 px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center inline-flex"
                                title="Voir les détails du patient"
                            >
                                <EyeIcon class="h-4 w-4 mr-1" />
                                Détails
                            </button>
                            
                            <button 
                                @click="openDossier(p)" 
                                class="text-blue-600 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center inline-flex"
                            >
                                <ClipboardDocumentListIcon class="h-4 w-4 mr-1" />
                                Dossier
                            </button>

                            <button 
                                @click="openEvaluation(p)"
                                class="text-purple-600 hover:text-purple-900 bg-purple-50 hover:bg-purple-100 px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center inline-flex"
                            >
                                <PencilSquareIcon class="h-4 w-4 mr-1" />
                                {{ t('toxico.actions.evaluate') }}
                            </button>

                            <button 
                                @click="confirmDischarge(p)"
                                class="text-red-600 hover:text-red-900 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center inline-flex"
                                :title="t('toxico.actions.discharge')"
                            >
                                <ArrowRightStartOnRectangleIcon class="h-4 w-4 mr-1" />
                                Sortie
                            </button>

                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div v-if="toxicoStore.totalActive > 20" class="p-4 border-t border-gray-100 flex justify-end space-x-2">
             <button 
                :disabled="toxicoStore.filters.page === 1"
                @click="toxicoStore.setPage(toxicoStore.filters.page - 1)"
                class="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50"
             >
                Précédent
             </button>
             <button 
                @click="toxicoStore.setPage(toxicoStore.filters.page + 1)"
                class="px-3 py-1 border rounded hover:bg-gray-50"
             >
                Suivant
             </button>
        </div>
    </div>

    <ToxicoDossierModal 
        v-if="showDossierModal"
        :patientId="selectedPatientId" 
        @close="closeDossierModal"
    />

    <ToxicoEvaluationModal 
        v-if="showEvalModal"
        :patient="selectedPatientForEval"
        @close="closeEvalModal"
        @save="handleSaveEvaluation"
    />

    <ToxicoAdmissionModal
        v-if="showAdmissionModal"
        @close="showAdmissionModal = false"
        @save="handleAdmission"
    />

    <ToxicoPatientDetailsModal
        v-if="showPatientDetailsModal"
        :patient="selectedPatientForDetails"
        @close="closePatientDetailsModal"
        @open-dossier="openDossierFromDetails"
    />

    <div v-if="showDischargeConfirm" class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
      <div class="relative mx-auto w-full max-w-md bg-white shadow-2xl rounded-2xl border border-gray-200">
        <div class="px-6 py-4 border-b border-gray-100 bg-red-50 rounded-t-2xl">
          <h3 class="text-lg font-bold text-red-800 flex items-center">
            <ExclamationTriangleIcon class="h-6 w-6 mr-2" />
            Confirmation de sortie
          </h3>
        </div>
        
        <div class="p-6">
          <p class="text-gray-700 mb-4">
            Voulez-vous vraiment clôturer le dossier de <span class="font-semibold">{{ patientToDischarge?.patientName }}</span> ?
          </p>
          <p class="text-sm text-gray-500 mb-6">
            Cette action est irréversible. Le patient sera marqué comme "sorti" du programme.
          </p>
          
          <div class="flex justify-end space-x-3">
            <button 
              @click="showDischargeConfirm = false"
              class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition"
            >
              Annuler
            </button>
            <button 
              @click="handleDischarge"
              class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition flex items-center"
            >
              <CheckIcon class="h-5 w-5 mr-2" />
              Confirmer la sortie
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useToxicoStore } from '@/stores/toxicoStore';
import { useI18n } from 'vue-i18n';
import ToxicoEvaluationModal from '@/components/toxico/ToxicoEvaluationModal.vue';
import ToxicoDossierModal from '@/components/toxico/ToxicoDossierModal.vue';
import ToxicoAdmissionModal from '@/components/toxico/ToxicoAdmissionModal.vue';
import ToxicoPatientDetailsModal from '@/components/toxico/ToxicoPatientDetailsModal.vue';
import { 
    PlusCircleIcon, 
    UserIcon, 
    UserGroupIcon, // Nouveau
    CalendarIcon, // Nouveau
    ArrowTrendingUpIcon, // Nouveau
    ExclamationCircleIcon, // Nouveau
    FireIcon, // Nouveau
    MagnifyingGlassIcon, 
    ClipboardDocumentListIcon, 
    PencilSquareIcon,
    ArrowRightStartOnRectangleIcon,
    ExclamationTriangleIcon,
    CheckIcon,
    EyeIcon 
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const toxicoStore = useToxicoStore();

// --- ÉTATS LOCAUX ---
const showDossierModal = ref(false);
const showAdmissionModal = ref(false);
const showEvalModal = ref(false);
const showDischargeConfirm = ref(false);
const showPatientDetailsModal = ref(false);

const selectedPatientId = ref(null);
const selectedPatientForEval = ref(null);
const patientToDischarge = ref(null);
const selectedPatientForDetails = ref(null);

// --- 💡 CALCUL DYNAMIQUE : +X cette semaine ---
const newPatientsThisWeek = computed(() => {
    // Note : Ce calcul est approximatif car il se base sur la liste actuellement chargée (paginée).
    // Pour un chiffre exact sur TOUTE la base, il faudrait un endpoint backend dédié.
    const now = new Date();
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(now.getDate() - 7);

    return toxicoStore.patients.filter(p => {
        const dateSource = p.admissionDate || p.createdAt;
        if (!dateSource) return false;
        
        // Sécurisation de la date
        const d = new Date(typeof dateSource === 'string' ? dateSource.split('T')[0] : dateSource);
        if (isNaN(d.getTime())) return false;

        return d >= oneWeekAgo;
    }).length;
});

// --- LIFECYCLE ---
onMounted(() => {
    // Charger la liste
    toxicoStore.fetchToxicoPatients();
    // Charger la stat critique des admissions (Backend)
    toxicoStore.fetchDashboardStats(); 
    // Précharger les psys
    toxicoStore.fetchPsychologists();
});

// --- ACTIONS UI ---
let searchTimeout;
const handleSearch = (event) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        toxicoStore.setSearch(event.target.value);
    }, 500);
};

const openDossier = (patient) => {
    console.log("🟢 Ouverture dossier pour patient:", patient);
    selectedPatientId.value = patient.patient_id;
    showDossierModal.value = true;
};

const closeDossierModal = () => {
    showDossierModal.value = false;
    selectedPatientId.value = null;
};

const openEvaluation = (patient) => {
    if (!patient.dossier_id && !patient.id) {
        console.error("❌ Patient n'a pas de dossier_id:", patient);
        alert("Erreur: Impossible de trouver l'identifiant du dossier. Veuillez rafraîchir la page.");
        return;
    }
    
    if (!patient.dossier_id && patient.id) {
        patient.dossier_id = patient.id;
    }
    
    selectedPatientForEval.value = patient;
    showEvalModal.value = true;
};

const closeEvalModal = () => {
    showEvalModal.value = false;
    selectedPatientForEval.value = null;
};

const handleAdmission = async (admissionData) => {
    try {
        await toxicoStore.fetchToxicoPatients();
        await toxicoStore.fetchDashboardStats(); // MAJ des stats
        alert("Admission validée avec succès !");
    } catch (error) {
        console.error("Erreur lors du rafraîchissement:", error);
        alert("Admission enregistrée, mais erreur lors du rafraîchissement");
    }
};

const handleSaveEvaluation = async (evalData) => {
    if (!evalData) {
        console.error("❌ evalData est undefined!");
        return;
    }
    try {
        await toxicoStore.submitEvaluation(evalData);
        closeEvalModal();
    } catch (e) {
        console.error("❌ Erreur handleSaveEvaluation:", e);
    }
};

const confirmDischarge = (patient) => {
    if (!patient.dossier_id && !patient.id) {
        alert("Erreur: Impossible de trouver l'identifiant du dossier.");
        return;
    }
    patientToDischarge.value = patient;
    showDischargeConfirm.value = true;
};

const handleDischarge = async () => {
    if (!patientToDischarge.value) return;
    try {
        const dossierId = patientToDischarge.value.dossier_id || patientToDischarge.value.id;
        await toxicoStore.dischargePatient(dossierId);
        showDischargeConfirm.value = false;
        patientToDischarge.value = null;
        await toxicoStore.fetchToxicoPatients();
        await toxicoStore.fetchDashboardStats(); // MAJ des stats
        alert("Dossier clôturé avec succès !");
    } catch (error) {
        console.error("❌ Erreur lors de la sortie:", error);
        alert("Erreur lors de la sortie.");
    }
};

const openPatientDetails = async (patient) => {
    try {
        selectedPatientForDetails.value = null;
        showPatientDetailsModal.value = true;
        const patientId = patient.patient_id || patient.id;
        if (!patientId) {
            alert("Erreur: ID patient introuvable.");
            showPatientDetailsModal.value = false;
            return;
        }
        const detailedPatient = await toxicoStore.getPatientDetails(patientId);
        selectedPatientForDetails.value = detailedPatient;
    } catch (error) {
        console.error("❌ Erreur chargement détails:", error);
        alert("Impossible de charger les détails.");
        showPatientDetailsModal.value = false;
    }
};

const closePatientDetailsModal = () => {
    showPatientDetailsModal.value = false;
    selectedPatientForDetails.value = null;
};

const openDossierFromDetails = (patientId) => {
    closePatientDetailsModal();
    selectedPatientId.value = patientId;
    showDossierModal.value = true;
};

const getPhaseColor = (phase) => {
    switch(phase) {
        case 1: return 'bg-red-100 text-red-800 border-red-200'; 
        case 2: return 'bg-orange-100 text-orange-800 border-orange-200'; 
        case 3: return 'bg-blue-100 text-blue-800 border-blue-200'; 
        case 4: return 'bg-green-100 text-green-800 border-green-200'; 
        default: return 'bg-gray-100';
    }
};
</script>