<template>
  <AppCard :title="t('hospitalization.card_title')">
    <template #actions>
      <AppButton v-if="!openStay" variant="hospital" @click="showAdmitForm = true">
        {{ t('hospitalization.admit_button') }}
      </AppButton>
    </template>

    <p v-if="error" role="alert" class="mb-4 text-base font-medium text-tone-danger-text">{{ error }}</p>

    <p v-if="!openStay && !showAdmitForm" class="text-base text-ink-muted">
      {{ t('hospitalization.not_hospitalized') }}
    </p>

    <div v-if="showAdmitForm" class="mb-4 grid gap-3 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4">
      <FormField id="hosp-reason" :label="t('hospitalization.admission_reason')" v-slot="{ describedBy }">
        <textarea id="hosp-reason" v-model="admissionReason" rows="2" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>
      <div class="flex flex-col gap-2 sm:flex-row">
        <AppButton variant="hospital" @click="submitAdmit" :disabled="isSubmitting" :loading="isSubmitting">
          {{ t('hospitalization.confirm') }}
        </AppButton>
        <AppButton variant="ghost" @click="showAdmitForm = false" :disabled="isSubmitting">
          {{ t('hospitalization.cancel') }}
        </AppButton>
      </div>
    </div>

    <div v-if="openStay" class="space-y-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div class="text-sm text-ink-muted">{{ t('hospitalization.admitted_since') }}</div>
          <div class="text-base font-semibold text-ink">{{ formatDate(openStay.admitted_at) }} ({{ daysSince(openStay.admitted_at) }} {{ t('hospitalization.days_count') }})</div>
          <div class="text-sm text-ink-muted">{{ t('hospitalization.admitted_by') }} {{ openStay.admitted_by_name || t('hospitalization.unknown_user') }}</div>
        </div>
        <div class="sm:text-right">
          <div class="text-sm text-ink-muted">{{ t('hospitalization.current_status') }}</div>
          <!-- Alerte d'aggravation : icone + texte en rouge -->
          <div class="mt-1 inline-flex items-center gap-2">
            <ExclamationTriangleIcon v-if="latestStatus === 'AGGRAVATION'" class="h-5 w-5 text-tone-danger-text" aria-hidden="true" />
            <StatusBadge
              :tone="statusTone(latestStatus)"
              :label="latestStatus ? t(`hospitalization.status.${latestStatus}`) : t('hospitalization.no_status_yet')"
            />
          </div>
        </div>
      </div>

      <!-- Retour terrain : la seule "derniere evolution" ci-dessus ne
           permet pas de retrouver les etats precedents pendant le sejour -
           chaque entree est deja horodatee et attribuee cote backend, elle
           manquait juste d'un affichage complet. -->
      <div v-if="openStay.status_updates?.length" class="border-t border-tone-neutral-border pt-3">
        <h4 class="mb-2 text-base font-semibold text-ink">{{ t('hospitalization.evolution_title') }}</h4>
        <ul class="max-h-56 space-y-2 overflow-y-auto pr-1">
          <li v-for="u in openStay.status_updates" :key="u.id" class="flex flex-col gap-1 text-base sm:flex-row sm:flex-wrap sm:items-center sm:gap-2">
            <StatusBadge :tone="statusTone(u.status)" :label="t(`hospitalization.status.${u.status}`)" />
            <span class="text-sm text-ink-muted">{{ formatDate(u.created_at) }}</span>
            <span class="text-sm text-ink-muted">{{ t('hospitalization.recorded_by') }} {{ u.created_by_name || t('hospitalization.unknown_user') }}</span>
            <span v-if="u.note" class="italic text-ink">{{ u.note }}</span>
          </li>
        </ul>
      </div>

      <div class="flex flex-col gap-2 sm:flex-row">
        <AppButton variant="secondary" @click="showStatusForm = !showStatusForm">
          {{ t('hospitalization.update_status_button') }}
        </AppButton>
        <AppButton variant="danger" @click="showDischargeForm = !showDischargeForm">
          {{ t('hospitalization.discharge_button') }}
        </AppButton>
      </div>

      <div v-if="showStatusForm" class="grid gap-3 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4">
        <FormField id="hosp-status" :label="t('hospitalization.update_status_button')" v-slot="{ describedBy }">
          <select id="hosp-status" v-model="newStatus" :aria-describedby="describedBy" :class="fieldClass" :disabled="isSubmitting">
            <option v-for="s in CLINICAL_STATUSES" :key="s" :value="s">{{ t(`hospitalization.status.${s}`) }}</option>
          </select>
        </FormField>
        <FormField id="hosp-status-note" :label="t('hospitalization.status_note')" v-slot="{ describedBy }">
          <textarea id="hosp-status-note" v-model="statusNote" rows="2" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']" :disabled="isSubmitting"></textarea>
        </FormField>
        <div>
          <AppButton @click="submitStatusUpdate" :disabled="isSubmitting" :loading="isSubmitting">
            {{ t('hospitalization.confirm') }}
          </AppButton>
        </div>
      </div>

      <div v-if="showDischargeForm" class="grid gap-3 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4">
        <FormField id="hosp-discharge" :label="t('hospitalization.discharge_disposition_label')" required v-slot="{ describedBy }">
          <select id="hosp-discharge" v-model="dischargeDisposition" :aria-describedby="describedBy" :class="fieldClass" :disabled="isSubmitting">
            <option value="" disabled>{{ t('hospitalization.discharge_disposition_label') }}</option>
            <option v-for="d in DISCHARGE_DISPOSITIONS" :key="d" :value="d">{{ t(`hospitalization.disposition.${d}`) }}</option>
          </select>
        </FormField>
        <FormField id="hosp-discharge-note" :label="t('hospitalization.discharge_note')" v-slot="{ describedBy }">
          <textarea id="hosp-discharge-note" v-model="dischargeNote" rows="2" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']" :disabled="isSubmitting"></textarea>
        </FormField>
        <div>
          <AppButton
            variant="danger"
            @click="submitDischarge"
            :disabled="isSubmitting || !dischargeDisposition"
          >
            {{ t('hospitalization.confirm') }}
          </AppButton>
        </div>
      </div>
    </div>

    <div v-if="hospitalizationStore.patientHistory.length > 0" class="mt-6 border-t border-tone-neutral-border pt-4">
      <h4 class="mb-3 text-base font-semibold text-ink">{{ t('hospitalization.history_title') }}</h4>
      <ul class="space-y-4">
        <li v-for="stay in hospitalizationStore.patientHistory" :key="stay.id" class="text-base">
          <div class="flex flex-col gap-2 text-ink sm:flex-row sm:items-center sm:justify-between">
            <span>{{ formatDate(stay.admitted_at) }} - {{ stay.discharged_at ? formatDate(stay.discharged_at) : '...' }}</span>
            <div class="flex flex-wrap items-center gap-2">
              <span v-if="stay.discharge_disposition" class="font-medium">{{ t(`hospitalization.disposition.${stay.discharge_disposition}`) }}</span>
              <AppButton
                v-if="stay.discharge_disposition"
                variant="secondary"
                @click="downloadLetter(stay.id)"
                :disabled="downloadingLetterId === stay.id"
                :loading="downloadingLetterId === stay.id"
              >
                {{ t('hospitalization.download_letter') }}
              </AppButton>
            </div>
          </div>
          <div v-if="stay.discharge_disposition" class="text-sm text-ink-muted">
            {{ t('hospitalization.discharged_by') }} {{ stay.discharged_by_name || t('hospitalization.unknown_user') }}
          </div>
          <ul v-if="stay.status_updates?.length" class="mt-2 space-y-2 border-l-2 border-tone-neutral-border pl-3">
            <li v-for="u in stay.status_updates" :key="u.id" class="flex flex-col gap-1 sm:flex-row sm:flex-wrap sm:items-center sm:gap-2">
              <StatusBadge :tone="statusTone(u.status)" :label="t(`hospitalization.status.${u.status}`)" />
              <span class="text-sm text-ink-muted">{{ formatDate(u.created_at) }}</span>
              <span v-if="u.note" class="italic text-ink">{{ u.note }}</span>
            </li>
          </ul>
        </li>
      </ul>
    </div>
  </AppCard>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline';
import { useHospitalizationStore, DISCHARGE_DISPOSITIONS, CLINICAL_STATUSES } from '@/stores/hospitalizationStore';
import { HospitalizationGateway } from '@/services/HospitalizationGateway';
import { AppButton, AppCard, FormField, StatusBadge } from '@/components/ui';

const { t } = useI18n();
const hospitalizationStore = useHospitalizationStore();

const props = defineProps({
  patientId: {
    type: Number,
    required: true,
  },
});

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const showAdmitForm = ref(false);
const admissionReason = ref('');
const showStatusForm = ref(false);
const newStatus = ref('AMELIORATION');
const statusNote = ref('');
const showDischargeForm = ref(false);
const dischargeDisposition = ref('');
const dischargeNote = ref('');
const error = ref(null);
const isSubmitting = ref(false);

const openStay = computed(() => hospitalizationStore.patientHistory.find((s) => !s.discharged_at) || null);
const latestStatus = computed(() => {
  if (!openStay.value || !openStay.value.status_updates?.length) return null;
  return openStay.value.status_updates[0].status;
});

function formatDate(d) {
  return dayjs(d).format('DD/MM/YYYY HH:mm');
}
function daysSince(d) {
  return dayjs().diff(dayjs(d), 'day');
}
// Vert = amelioration, rouge = aggravation (alerte), neutre sinon.
function statusTone(status) {
  if (status === 'AMELIORATION') return 'success';
  if (status === 'AGGRAVATION') return 'danger';
  return 'neutral';
}

async function submitAdmit() {
  error.value = null;
  isSubmitting.value = true;
  try {
    await hospitalizationStore.admit(props.patientId, admissionReason.value);
    showAdmitForm.value = false;
    admissionReason.value = '';
  } catch (err) {
    console.error('Erreur lors de l\'admission:', err);
    error.value = "Erreur lors de l'admission du patient.";
  } finally {
    isSubmitting.value = false;
  }
}

async function submitStatusUpdate() {
  if (!openStay.value) return;
  error.value = null;
  isSubmitting.value = true;
  try {
    await hospitalizationStore.addStatusUpdate(openStay.value.id, newStatus.value, statusNote.value, props.patientId);
    showStatusForm.value = false;
    statusNote.value = '';
  } catch (err) {
    console.error('Erreur lors de la mise à jour du statut:', err);
    error.value = "Erreur lors de la mise à jour du statut.";
  } finally {
    isSubmitting.value = false;
  }
}

const downloadingLetterId = ref(null);

async function downloadLetter(hospitalizationId) {
  error.value = null;
  downloadingLetterId.value = hospitalizationId;
  try {
    const resp = await HospitalizationGateway.downloadDischargeLetter(hospitalizationId);
    const url = window.URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `lettre_sortie_${hospitalizationId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    // Meme motif que CaisseList.vue::downloadInvoice : responseType 'blob'
    // recoit une erreur JSON du backend comme un Blob binaire, jamais un
    // objet exploitable directement - decodage explicite necessaire.
    let detail = null;
    if (err.response?.data instanceof Blob) {
      try {
        const text = await err.response.data.text();
        detail = JSON.parse(text)?.detail;
      } catch {
        detail = null;
      }
    } else {
      detail = err.response?.data?.detail;
    }
    error.value = detail || "Impossible de télécharger la lettre de sortie.";
  } finally {
    downloadingLetterId.value = null;
  }
}

async function submitDischarge() {
  if (!openStay.value || !dischargeDisposition.value) return;
  error.value = null;
  isSubmitting.value = true;
  try {
    await hospitalizationStore.discharge(openStay.value.id, dischargeDisposition.value, dischargeNote.value, props.patientId);
    showDischargeForm.value = false;
    dischargeDisposition.value = '';
    dischargeNote.value = '';
  } catch (err) {
    console.error('Erreur lors de la sortie:', err);
    error.value = "Erreur lors de la sortie du patient.";
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(async () => {
  error.value = null;
  try {
    await hospitalizationStore.fetchPatientHistory(props.patientId);
  } catch (err) {
    console.error('Erreur chargement historique hospitalisation:', err);
    error.value = "Impossible de charger l'historique d'hospitalisation.";
  }
});
</script>
