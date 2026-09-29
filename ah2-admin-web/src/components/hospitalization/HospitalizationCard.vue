<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-gray-800">{{ t('hospitalization.card_title') }}</h3>
      <button
        v-if="!openStay"
        @click="showAdmitForm = true"
        class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition"
      >
        {{ t('hospitalization.admit_button') }}
      </button>
    </div>

    <p v-if="error" class="text-sm text-red-600 mb-4">{{ error }}</p>

    <div v-if="!openStay && !showAdmitForm" class="text-sm text-gray-500 italic">
      {{ t('hospitalization.not_hospitalized') }}
    </div>

    <div v-if="showAdmitForm" class="space-y-3 mb-4 p-4 bg-gray-50 rounded-xl">
      <label class="text-xs font-bold text-gray-500 uppercase block">{{ t('hospitalization.admission_reason') }}</label>
      <textarea v-model="admissionReason" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"></textarea>
      <div class="flex gap-2">
        <button @click="submitAdmit" :disabled="isSubmitting" class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-40 disabled:cursor-not-allowed">
          {{ t('hospitalization.confirm') }}
        </button>
        <button @click="showAdmitForm = false" :disabled="isSubmitting" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition disabled:opacity-40 disabled:cursor-not-allowed">
          {{ t('hospitalization.cancel') }}
        </button>
      </div>
    </div>

    <div v-if="openStay" class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-xs text-gray-500">{{ t('hospitalization.admitted_since') }}</div>
          <div class="text-sm font-semibold text-gray-900">{{ formatDate(openStay.admitted_at) }} ({{ daysSince(openStay.admitted_at) }} {{ t('hospitalization.days_count') }})</div>
          <div class="text-xs text-gray-400">{{ t('hospitalization.admitted_by') }} {{ openStay.admitted_by_name || t('hospitalization.unknown_user') }}</div>
        </div>
        <div class="text-right">
          <div class="text-xs text-gray-500">{{ t('hospitalization.current_status') }}</div>
          <div class="text-sm font-semibold" :class="statusColorClass(latestStatus)">
            {{ latestStatus ? t(`hospitalization.status.${latestStatus}`) : t('hospitalization.no_status_yet') }}
          </div>
        </div>
      </div>

      <!-- Retour terrain : la seule "derniere evolution" ci-dessus ne
           permet pas de retrouver les etats precedents pendant le sejour -
           chaque entree est deja horodatee et attribuee cote backend, elle
           manquait juste d'un affichage complet. -->
      <div v-if="openStay.status_updates?.length" class="pt-2 border-t border-gray-100">
        <h4 class="text-xs font-bold text-gray-500 uppercase mb-2">{{ t('hospitalization.evolution_title') }}</h4>
        <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          <div v-for="u in openStay.status_updates" :key="u.id" class="text-xs flex items-start gap-2">
            <span class="font-semibold flex-shrink-0" :class="statusColorClass(u.status)">{{ t(`hospitalization.status.${u.status}`) }}</span>
            <span class="text-gray-400 flex-shrink-0">{{ formatDate(u.created_at) }}</span>
            <span class="text-gray-400 flex-shrink-0">{{ t('hospitalization.recorded_by') }} {{ u.created_by_name || t('hospitalization.unknown_user') }}</span>
            <span v-if="u.note" class="text-gray-600 italic truncate">— {{ u.note }}</span>
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <button @click="showStatusForm = !showStatusForm" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition">
          {{ t('hospitalization.update_status_button') }}
        </button>
        <button @click="showDischargeForm = !showDischargeForm" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition">
          {{ t('hospitalization.discharge_button') }}
        </button>
      </div>

      <div v-if="showStatusForm" class="space-y-2 p-3 bg-gray-50 rounded-xl">
        <select v-model="newStatus" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" :disabled="isSubmitting">
          <option v-for="s in CLINICAL_STATUSES" :key="s" :value="s">{{ t(`hospitalization.status.${s}`) }}</option>
        </select>
        <textarea v-model="statusNote" :placeholder="t('hospitalization.status_note')" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" :disabled="isSubmitting"></textarea>
        <button @click="submitStatusUpdate" :disabled="isSubmitting" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-40 disabled:cursor-not-allowed">
          {{ t('hospitalization.confirm') }}
        </button>
      </div>

      <div v-if="showDischargeForm" class="space-y-2 p-3 bg-gray-50 rounded-xl">
        <select v-model="dischargeDisposition" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" :disabled="isSubmitting">
          <option value="" disabled>{{ t('hospitalization.discharge_disposition_label') }}</option>
          <option v-for="d in DISCHARGE_DISPOSITIONS" :key="d" :value="d">{{ t(`hospitalization.disposition.${d}`) }}</option>
        </select>
        <textarea v-model="dischargeNote" :placeholder="t('hospitalization.discharge_note')" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" :disabled="isSubmitting"></textarea>
        <button
          @click="submitDischarge"
          :disabled="isSubmitting || !dischargeDisposition"
          class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {{ t('hospitalization.confirm') }}
        </button>
      </div>
    </div>

    <div v-if="hospitalizationStore.patientHistory.length > 0" class="mt-6 pt-4 border-t border-gray-100">
      <h4 class="text-xs font-bold text-gray-500 uppercase mb-2">{{ t('hospitalization.history_title') }}</h4>
      <div class="space-y-3">
        <div v-for="stay in hospitalizationStore.patientHistory" :key="stay.id" class="text-xs">
          <div class="flex justify-between items-center text-gray-600">
            <span>{{ formatDate(stay.admitted_at) }} → {{ stay.discharged_at ? formatDate(stay.discharged_at) : '…' }}</span>
            <div class="flex items-center gap-2">
              <span v-if="stay.discharge_disposition" class="font-medium">{{ t(`hospitalization.disposition.${stay.discharge_disposition}`) }}</span>
              <button
                v-if="stay.discharge_disposition"
                @click="downloadLetter(stay.id)"
                :disabled="downloadingLetterId === stay.id"
                class="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200 transition disabled:opacity-40"
              >
                {{ t('hospitalization.download_letter') }}
              </button>
            </div>
          </div>
          <div v-if="stay.discharge_disposition" class="text-gray-400">
            {{ t('hospitalization.discharged_by') }} {{ stay.discharged_by_name || t('hospitalization.unknown_user') }}
          </div>
          <div v-if="stay.status_updates?.length" class="mt-1 pl-3 border-l-2 border-gray-100 space-y-1">
            <div v-for="u in stay.status_updates" :key="u.id" class="flex items-start gap-2">
              <span class="font-medium flex-shrink-0" :class="statusColorClass(u.status)">{{ t(`hospitalization.status.${u.status}`) }}</span>
              <span class="text-gray-400 flex-shrink-0">{{ formatDate(u.created_at) }}</span>
              <span v-if="u.note" class="text-gray-500 italic truncate">— {{ u.note }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { useHospitalizationStore, DISCHARGE_DISPOSITIONS, CLINICAL_STATUSES } from '@/stores/hospitalizationStore';
import { HospitalizationGateway } from '@/services/HospitalizationGateway';

const { t } = useI18n();
const hospitalizationStore = useHospitalizationStore();

const props = defineProps({
  patientId: {
    type: Number,
    required: true,
  },
});

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
function statusColorClass(status) {
  if (status === 'AMELIORATION') return 'text-emerald-700';
  if (status === 'AGGRAVATION') return 'text-red-700';
  return 'text-gray-700';
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
