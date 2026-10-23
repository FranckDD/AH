<template>
  <FullScreenPanel :title="t('toxico.modal.eval_title')"
                   :subtitle="t('toxicoScreens.eval_subtitle', { name: patient.patientName, phase: t(`toxico.phases.${patient.currentPhase}`) })" accent @close="$emit('close')">
    <form id="toxico-eval-form" @submit.prevent="handleSubmit" class="grid gap-4">

      <!-- Decision : gris (maintenir), vert (avancer), rouge (regresser) -->
      <fieldset class="grid gap-2">
        <legend class="mb-1 text-base font-medium text-ink">{{ t('toxico.modal.decision_label') }}</legend>
        <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
          <label :class="[optionClass, form.decision === 'MAINTAIN' ? toneClasses('neutral') : idleClass]">
            <input type="radio" name="eval-decision" value="MAINTAIN" v-model="form.decision" class="peer sr-only" />
            <span :class="[focusRing, 'flex flex-col items-center gap-1 rounded-control p-1 text-center']">
              <PauseCircleIcon class="h-10 w-10" aria-hidden="true" />
              <span class="text-base font-bold">{{ t('toxico.modal.maintain') }}</span>
              <span class="text-sm">{{ t('toxicoScreens.eval_stay', { n: patient.currentPhase }) }}</span>
            </span>
          </label>

          <label :class="[optionClass, form.decision === 'PROGRESS' ? toneClasses('success') : idleClass]">
            <input type="radio" name="eval-decision" value="PROGRESS" v-model="form.decision" class="peer sr-only" />
            <span :class="[focusRing, 'flex flex-col items-center gap-1 rounded-control p-1 text-center']">
              <ForwardIcon class="h-10 w-10 text-tone-success-text" aria-hidden="true" />
              <span class="text-base font-bold text-tone-success-text">{{ t('toxico.modal.progress') }}</span>
              <span class="text-sm">{{ t('toxicoScreens.eval_to', { n: nextPhase }) }}</span>
            </span>
          </label>

          <label :class="[optionClass, form.decision === 'REGRESS' ? toneClasses('danger') : idleClass]">
            <input type="radio" name="eval-decision" value="REGRESS" v-model="form.decision" class="peer sr-only" />
            <span :class="[focusRing, 'flex flex-col items-center gap-1 rounded-control p-1 text-center']">
              <BackwardIcon class="h-10 w-10 text-tone-danger-text" aria-hidden="true" />
              <span class="text-base font-bold text-tone-danger-text">{{ t('toxico.modal.regress') }}</span>
              <span class="text-sm">{{ t('toxicoScreens.eval_back', { n: prevPhase }) }}</span>
            </span>
          </label>
        </div>
      </fieldset>

      <p v-if="form.decision === 'REGRESS'" role="alert" class="flex items-start gap-2 rounded-card border p-3 text-base font-medium" :class="toneClasses('danger')">
        <ExclamationTriangleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        {{ t('toxicoScreens.eval_regress_warning') }}
      </p>

      <FormField id="tox-eval-obs" :label="t('toxico.modal.observations')" required :help="`${form.observation.length}/500`"
                 :error="form.observation.length < 10 && form.decision === 'REGRESS' ? t('toxicoScreens.eval_obs_hint') : ''" v-slot="{ describedBy, invalid }">
        <textarea id="tox-eval-obs" v-model="form.observation" rows="3" required maxlength="500" :aria-describedby="describedBy" :aria-invalid="invalid ? 'true' : undefined"
                  :placeholder="t('toxicoScreens.eval_obs_placeholder')" :class="[fieldClass, 'py-2', invalid ? 'border-tone-danger-border' : '']"></textarea>
      </FormField>

      <FormField id="tox-eval-reco" :label="t('toxico.modal.recommendations')" :help="`${form.recommendation.length}/200`" v-slot="{ describedBy }">
        <textarea id="tox-eval-reco" v-model="form.recommendation" rows="2" maxlength="200" :aria-describedby="describedBy"
                  :placeholder="t('toxicoScreens.eval_reco_placeholder')" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>

      <!-- Resume de la decision -->
      <p role="status" class="flex items-start gap-2 rounded-card border p-3 text-base" :class="toneClasses('info')">
        <InformationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <span><span class="font-semibold">{{ t('toxicoScreens.eval_summary') }}</span> {{ getDecisionSummary() }}</span>
      </p>

      <p v-if="errorMessage" role="alert" class="flex items-start gap-2 whitespace-pre-line rounded-card border p-3 text-base" :class="toneClasses('danger')">
        <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        {{ errorMessage }}
      </p>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="secondary" :disabled="isLoading" @click="$emit('close')">{{ t('common.cancel') }}</AppButton>
        </template>
        <AppButton :variant="submitVariant" :icon="CheckIcon" :loading="isLoading" :disabled="isLoading || !isFormValid" @click="handleSubmit">
          {{ isLoading ? t('toxicoScreens.saving') : t('toxico.modal.validate_eval') }}
        </AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { reactive, computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import {
    ExclamationTriangleIcon,
    CheckIcon,
    InformationCircleIcon,
    ExclamationCircleIcon,
    PauseCircleIcon,
    ForwardIcon,
    BackwardIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const toxicoStore = useToxicoStore();
const props = defineProps({
    patient: { type: Object, required: true }
});
const emit = defineEmits(['close', 'save']);

// Style commun des champs et des trois choix de decision.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const optionClass = 'block cursor-pointer rounded-card border-2 p-3 transition';
const idleClass = 'border-tone-neutral-border bg-white text-ink hover:bg-tone-neutral-bg';
const focusRing = 'peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-600';

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

// Le bouton de validation prend la couleur de la decision : indigo (maintenir), vert (avancer), rouge (regresser).
const submitVariant = computed(() => {
    switch(form.decision) {
        case 'PROGRESS': return 'success';
        case 'REGRESS': return 'danger';
        default: return 'primary';
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
            return t('toxicoScreens.eval_summary_progress', { from: props.patient.currentPhase, to: nextPhase.value });
        case 'REGRESS':
            return t('toxicoScreens.eval_summary_regress', { from: props.patient.currentPhase, to: prevPhase.value });
        default:
            return t('toxicoScreens.eval_summary_maintain', { phase: props.patient.currentPhase });
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
        emit('save',payload); 
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