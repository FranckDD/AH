<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    
    <div class="relative mx-auto w-full max-w-2xl bg-white shadow-2xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
      
      <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50 rounded-t-2xl flex-shrink-0">
        <div>
            <h3 class="text-lg font-bold text-gray-800 flex items-center">
                <span class="bg-indigo-100 text-indigo-700 p-1.5 rounded-lg mr-3">
                    <ClipboardDocumentCheckIcon class="h-5 w-5" />
                </span>
                {{ t('toxico.modal.eval_title') }}
            </h3>
            <p class="text-sm text-gray-500 mt-1 ml-11">
                Patient: <span class="font-semibold text-gray-900">{{ patient.patientName }}</span> • 
                Phase actuelle: <span class="font-semibold text-indigo-600">{{ t(`toxico.phases.${patient.currentPhase}`) }}</span>
            </p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 bg-white p-2 rounded-full shadow-sm border border-gray-200 transition">
          <span class="text-xl font-bold">&times;</span>
        </button>
      </div>

      <div class="p-6 overflow-y-auto">
        <form @submit.prevent="handleSubmit" class="space-y-6">
            
            <div>
                <label class="block text-sm font-bold text-gray-700 mb-3">{{ t('toxico.modal.decision_label') }}</label>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div 
                        @click="form.decision = 'MAINTAIN'"
                        class="cursor-pointer border-2 rounded-xl p-4 flex flex-col items-center justify-center transition-all duration-200 hover:shadow-md"
                        :class="form.decision === 'MAINTAIN' ? 'border-gray-500 bg-gray-50 ring-1 ring-gray-500' : 'border-gray-200 hover:border-gray-300'"
                    >
                        <div class="p-2 bg-gray-100 rounded-full mb-2 text-2xl">⏹️</div>
                        <span class="font-bold text-gray-700">{{ t('toxico.modal.maintain') }}</span>
                        <span class="text-xs text-gray-500 text-center mt-1">Reste Phase {{ patient.currentPhase }}</span>
                    </div>

                    <div 
                        @click="form.decision = 'PROGRESS'"
                        class="cursor-pointer border-2 rounded-xl p-4 flex flex-col items-center justify-center transition-all duration-200 hover:shadow-md"
                        :class="form.decision === 'PROGRESS' ? 'border-green-500 bg-green-50 ring-1 ring-green-500' : 'border-gray-200 hover:border-green-200'"
                    >
                        <div class="p-2 bg-green-100 rounded-full mb-2 text-2xl">⏩</div>
                        <span class="font-bold text-green-700">{{ t('toxico.modal.progress') }}</span>
                        <span class="text-xs text-green-600 text-center mt-1">Vers Phase {{ nextPhase }}</span>
                    </div>

                    <div 
                        @click="form.decision = 'REGRESS'"
                        class="cursor-pointer border-2 rounded-xl p-4 flex flex-col items-center justify-center transition-all duration-200 hover:shadow-md"
                        :class="form.decision === 'REGRESS' ? 'border-red-500 bg-red-50 ring-1 ring-red-500' : 'border-gray-200 hover:border-red-200'"
                    >
                        <div class="p-2 bg-red-100 rounded-full mb-2 text-2xl">⏪</div>
                        <span class="font-bold text-red-700">{{ t('toxico.modal.regress') }}</span>
                        <span class="text-xs text-red-600 text-center mt-1">Retour Phase {{ prevPhase }}</span>
                    </div>
                </div>
            </div>

            <div v-if="form.decision === 'REGRESS'" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-r">
                <div class="flex items-start">
                    <ExclamationTriangleIcon class="h-5 w-5 text-red-500 mr-2 mt-0.5" />
                    <p class="text-sm text-red-700 font-medium">
                        Attention : Ceci sera enregistré comme une <span class="font-bold">Rechute</span>. Justification détaillée requise.
                    </p>
                </div>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ t('toxico.modal.observations') }} <span class="text-red-500">*</span>
                    <span class="text-xs text-gray-500 ml-2">({{ form.observation.length }}/500)</span>
                </label>
                <textarea 
                    v-model="form.observation" 
                    rows="3" 
                    required
                    maxlength="500"
                    :class="[
                        'w-full px-4 py-2 border rounded-lg transition',
                        form.observation.length < 10 && form.decision === 'REGRESS' 
                            ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                            : 'border-gray-300 focus:ring-indigo-500 focus:border-indigo-500'
                    ]"
                    placeholder="État psychologique, comportement, progrès, difficultés..."
                ></textarea>
                <p v-if="form.observation.length < 10 && form.decision === 'REGRESS'" class="text-xs text-red-600 mt-1">
                    Pour une régression, l'observation doit être détaillée (minimum 10 caractères)
                </p>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ t('toxico.modal.recommendations') }}
                    <span class="text-xs text-gray-500 ml-2">({{ form.recommendation.length }}/200)</span>
                </label>
                <textarea 
                    v-model="form.recommendation" 
                    rows="2" 
                    maxlength="200"
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition"
                    placeholder="Actions à entreprendre, suivi recommandé..."
                ></textarea>
            </div>

            <!-- Résumé de la décision -->
            <div class="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <InformationCircleIcon class="h-5 w-5 text-blue-400" />
                    </div>
                    <div class="ml-3">
                        <p class="text-sm text-blue-700">
                            <span class="font-semibold">Résumé :</span> 
                            {{ getDecisionSummary() }}
                        </p>
                    </div>
                </div>
            </div>

            <!-- Message d'erreur -->
            <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-4 rounded">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <ExclamationCircleIcon class="h-5 w-5 text-red-400" />
                    </div>
                    <div class="ml-3">
                        <p class="text-sm text-red-700">{{ errorMessage }}</p>
                    </div>
                </div>
            </div>

        </form>
      </div>

      <div class="px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-2xl flex justify-end space-x-3 flex-shrink-0">
        <button @click="$emit('close')" :disabled="isLoading" 
                class="px-5 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 font-medium transition disabled:opacity-50">
            {{ t('common.cancel') || 'Annuler' }}
        </button>
        <button 
            @click="handleSubmit" 
            :class="submitButtonClass"
            :disabled="isLoading || !isFormValid"
            class="px-6 py-2 text-white rounded-lg shadow-md font-semibold transition flex items-center disabled:opacity-75 disabled:cursor-not-allowed"
        >
            <template v-if="isLoading">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Enregistrement...
            </template>
            <template v-else>
                <CheckIcon class="h-5 w-5 mr-2" />
                {{ t('toxico.modal.validate_eval') }}
            </template>
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { reactive, computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { 
    ClipboardDocumentCheckIcon, 
    ExclamationTriangleIcon, 
    CheckIcon,
    InformationCircleIcon,
    ExclamationCircleIcon 
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const toxicoStore = useToxicoStore();
const props = defineProps({
    patient: { type: Object, required: true }
});
const emit = defineEmits(['close', 'save']);

const isLoading = ref(false);
const errorMessage = ref('');

const form = reactive({
    decision: 'MAINTAIN',
    observation: '',
    recommendation: ''
});

// Logique Phases
const nextPhase = computed(() => props.patient.currentPhase < 4 ? props.patient.currentPhase + 1 : 4);
const prevPhase = computed(() => props.patient.currentPhase > 1 ? props.patient.currentPhase - 1 : 1);

// Calcul de la phase cible
const targetPhase = computed(() => {
    switch(form.decision) {
        case 'PROGRESS': return nextPhase.value;
        case 'REGRESS': return prevPhase.value;
        default: return props.patient.currentPhase;
    }
});

// Validation du formulaire
const isFormValid = computed(() => {
    if (!form.observation.trim()) return false;
    if (form.decision === 'REGRESS' && form.observation.trim().length < 10) return false;
    return true;
});

const submitButtonClass = computed(() => {
    switch(form.decision) {
        case 'PROGRESS': return 'bg-green-600 hover:bg-green-700';
        case 'REGRESS': return 'bg-red-600 hover:bg-red-700';
        default: return 'bg-indigo-600 hover:bg-indigo-700';
    }
});

// Watcher pour reset les erreurs
watch(form, () => {
    errorMessage.value = '';
});

// Fonction pour le résumé
const getDecisionSummary = () => {
    switch(form.decision) {
        case 'PROGRESS': 
            return `Le patient passera de la Phase ${props.patient.currentPhase} à la Phase ${nextPhase.value}`;
        case 'REGRESS':
            return `Le patient retournera de la Phase ${props.patient.currentPhase} à la Phase ${prevPhase.value} (Rechute)`;
        default:
            return `Le patient restera en Phase ${props.patient.currentPhase}`;
    }
};

const handleSubmit = async () => {
    console.log("=".repeat(60));
    console.log("📤 TOXICO EVALUATION - Début de l'envoi");
    console.log("=".repeat(60));
    
    // Validation
    if (!isFormValid.value) {
        errorMessage.value = form.decision === 'REGRESS' 
            ? "Pour une régression, l'observation doit être détaillée (minimum 10 caractères)"
            : "L'observation est obligatoire";
        return;
    }

    if (isLoading.value) return;
    isLoading.value = true;
    errorMessage.value = '';

    // 🟢 Préparation du payload
    const dossierId = props.patient.dossier_id || props.patient.id;
    
    if (!dossierId) {
        errorMessage.value = "Erreur technique : ID du dossier introuvable.";
        isLoading.value = false;
        return;
    }

    const payload = {
        dossier_id: Number(dossierId),
        decision: form.decision,
        observation: form.observation.trim(),
        recommendation: form.recommendation?.trim() || null,
        targetPhase: Number(targetPhase.value)
    };

    // Log détaillé
    console.log("📋 Patient info:", props.patient);
    console.log("📋 Payload préparé:", JSON.stringify(payload, null, 2));
    console.log("🔍 Types:", {
        dossier_id: typeof payload.dossier_id,
        decision: typeof payload.decision,
        targetPhase: typeof payload.targetPhase,
        observation_length: payload.observation.length
    });

    try {
        console.log("🔄 Appel à toxicoStore.submitEvaluation...");
        await toxicoStore.submitEvaluation(payload);
        
        console.log("✅ Évaluation réussie!");
        emit('save'); 
        emit('close');
        
    } catch (error) {
        console.error("❌ Erreur lors de l'évaluation:", error);
        
        // Gestion détaillée des erreurs
        if (error.response) {
            console.error("📊 Détails de l'erreur:", {
                status: error.response.status,
                data: error.response.data,
                headers: error.response.headers
            });
            
            if (error.response.status === 422) {
                // Erreur de validation Pydantic
                const details = error.response.data.detail;
                if (Array.isArray(details)) {
                    const errors = details.map(err => {
                        const field = err.loc.join('.');
                        return `${field}: ${err.msg}`;
                    });
                    errorMessage.value = `Erreurs de validation:\n${errors.join('\n')}`;
                } else {
                    errorMessage.value = `Erreur: ${details}`;
                }
            } else if (error.response.status === 400) {
                errorMessage.value = error.response.data.detail || "Données invalides";
            } else if (error.response.status === 401) {
                errorMessage.value = "Session expirée. Veuillez vous reconnecter.";
            } else if (error.response.status === 404) {
                errorMessage.value = "Dossier non trouvé. Veuillez rafraîchir la page.";
            } else {
                errorMessage.value = `Erreur serveur (${error.response.status}): ${error.response.data.detail || 'Veuillez réessayer'}`;
            }
        } else if (error.request) {
            errorMessage.value = "Erreur réseau. Veuillez vérifier votre connexion.";
            console.error("🌐 Erreur réseau:", error.request);
        } else {
            errorMessage.value = error.message || "Une erreur inattendue est survenue";
            console.error("⚠️ Erreur inattendue:", error.message);
        }
        
        // Garder la modale ouverte pour permettre la correction
    } finally {
        isLoading.value = false;
        //console.log("=".repeat(60));
        //console.log("📤 TOXICO EVALUATION - Fin du traitement");
        //console.log("=".repeat(60));
    }
};
</script>