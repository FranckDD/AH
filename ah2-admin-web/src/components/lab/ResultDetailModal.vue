<template>
  <FullScreenPanel :title="getPatientName" :subtitle="`${t('lab.result_modal.exam_of')} ${formatDate(result.test_date || result.created_at)}`" wide @close="$emit('close')">
    <div class="grid gap-6 text-sm [&_table]:text-sm [&_dd]:text-sm">

      <div class="flex flex-wrap items-center gap-2">
        <StatusBadge :tone="statusTone" :label="translateStatus(result.status)" />
        <span class="rounded-full bg-tone-neutral-bg px-3 py-1 text-sm text-tone-neutral-text">{{ t('labScreens.result_id', { id: result.result_id || result.id }) }}</span>
        <span v-if="result.code" class="rounded-full bg-tone-neutral-bg px-3 py-1 text-sm text-tone-neutral-text">{{ t('lab.result_modal.batch') }} : {{ result.code }}</span>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <section aria-labelledby="lab-detail-patient" class="grid content-start gap-2">
          <h3 id="lab-detail-patient" class="text-lg font-semibold text-ink">{{ t('lab.result_modal.patient_info') }}</h3>
          <dl class="grid gap-1 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4 text-sm">
            <div class="flex flex-wrap gap-x-2">
              <dt class="text-ink-muted">{{ t('lab.result_modal.type') }} :</dt>
              <dd class="font-semibold text-ink">{{ (result.is_external || result.external_patient_info) ? t('lab.result_modal.external') : t('lab.result_modal.internal') }}</dd>
            </div>
            <div class="flex flex-wrap gap-x-2">
              <dt class="text-ink-muted">{{ t('lab.result_modal.sex') }} :</dt>
              <dd class="text-ink">{{ result.patient_info?.sexe || result.patient_sexe || t('lab.result_modal.not_provided') }}</dd>
            </div>
            <div class="flex flex-wrap gap-x-2">
              <dt class="text-ink-muted">{{ t('lab.result_modal.age') }} :</dt>
              <dd class="text-ink">{{ result.patient_info?.age ? `${result.patient_info.age} ${t('lab.result_modal.years')}` : (result.patient_age || t('lab.result_modal.not_provided')) }}</dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="lab-detail-presc" class="grid content-start gap-2">
          <h3 id="lab-detail-presc" class="text-lg font-semibold text-ink">{{ t('lab.result_modal.prescription') }}</h3>
          <dl class="grid gap-1 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4 text-sm">
            <div class="flex flex-wrap gap-x-2">
              <dt class="text-ink-muted">{{ t('lab.result_modal.prescriber') }} :</dt>
              <dd class="text-ink">{{ result.medecin_prescripteur || result.prescriber || t('lab.result_modal.not_specified') }}</dd>
            </div>
            <div class="flex flex-wrap gap-x-2">
              <dt class="text-ink-muted">{{ t('lab.result_modal.exam') }} :</dt>
              <dd class="font-semibold text-ink">{{ result.examen_nom || result.exam_name || t('lab.result_modal.not_specified') }}</dd>
            </div>
          </dl>
        </section>
      </div>

      <section v-if="result.corrected" aria-labelledby="lab-detail-corrected" class="grid gap-2 rounded-card border p-4" :class="toneClasses('info')">
        <h3 id="lab-detail-corrected" class="text-sm font-semibold">{{ t('lab.result_modal.corrected_title') }}</h3>
        <ul class="grid gap-3 text-sm">
          <li v-for="a in (result.amendments || [])" :key="a.amendment_id" class="grid gap-1">
            <p class="font-medium">{{ t('lab.result_modal.corrected_by', { name: a.amended_by_name || t('lab.result_modal.unknown'), date: formatDate(a.amended_at) }) }}</p>
            <p class="whitespace-pre-line">{{ a.reason }}</p>
            <ul class="grid gap-0.5">
              <li v-for="v in (a.previous_values || [])" :key="v.detail_id">
                {{ t('lab.result_modal.previous_value') }} : {{ v.parametre_nom }} = {{ v.valeur_text !== null && v.valeur_text !== '' ? v.valeur_text : '-' }}
              </li>
            </ul>
          </li>
        </ul>
      </section>

      <section aria-labelledby="lab-detail-results" class="grid gap-2">
        <h3 id="lab-detail-results" class="text-lg font-semibold text-ink">{{ t('lab.result_modal.bio_results') }}</h3>
        <ResponsiveTable :columns="columns" :rows="result.details || []" row-key="detail_id" :empty-title="t('lab.result_modal.no_params')" :empty-message="' '" striped>
          <template #cell-param="{ row: detail }"><span class="font-semibold">{{ detail.nom || detail.parameter_name || t('lab.result_modal.unknown') }}</span></template>
          <template #cell-result="{ row: detail }">
            <span class="text-lg font-bold" :class="isAbnormal(detail) ? 'text-tone-danger-text' : 'text-ink'">
              {{ detail.valeur !== null && detail.valeur !== undefined && detail.valeur !== '' ? detail.valeur : '-' }}
            </span>
            <span v-if="isAbnormal(detail)" class="ml-2 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm font-semibold" :class="toneClasses('danger')" :title="t('lab.result_modal.abnormal')">
              <component :is="flagIcon(detail)" class="h-4 w-4 shrink-0" aria-hidden="true" />
              {{ flagLabel(detail) }}
            </span>
          </template>
          <template #cell-unit="{ row: detail }">{{ detail.unite || detail.unit || '-' }}</template>
          <template #cell-ref="{ row: detail }"><span class="whitespace-nowrap">{{ getRange(detail, result.patient_info) }}</span></template>
          <template #cell-interp="{ row: detail }">
            <StatusBadge v-if="detail.interpretation" :tone="isAbnormal(detail) ? 'danger' : 'neutral'" :label="detail.interpretation" />
            <span v-else class="text-ink-muted">-</span>
          </template>
        </ResponsiveTable>
      </section>

      <section v-if="result.conclusion" aria-labelledby="lab-detail-conclusion" class="rounded-card border p-4" :class="toneClasses('info')">
        <h3 id="lab-detail-conclusion" class="mb-1 text-sm font-semibold">{{ t('lab.result_modal.conclusion') }}</h3>
        <p class="whitespace-pre-line text-sm">{{ result.conclusion }}</p>
      </section>

      <section v-if="result.note || result.comments" aria-labelledby="lab-detail-notes" class="rounded-card border p-4" :class="toneClasses('warning')">
        <h3 id="lab-detail-notes" class="mb-1 text-sm font-semibold">{{ t('lab.result_modal.notes') }}</h3>
        <p class="whitespace-pre-line text-sm">{{ result.note || result.comments }}</p>
      </section>
    </div>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('lab.result_modal.close') }}</AppButton>
        </template>
        <AppButton v-if="canAmend && result.status === 'completed'" variant="lab" :icon="PencilSquareIcon" @click="$emit('amend', result)">{{ t('lab.technician.amend_btn') }}</AppButton>
        <AppButton v-if="result.status !== 'pending'" variant="info" :icon="PrinterIcon" @click="printPdf">{{ t('lab.result_modal.print') }}</AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PencilSquareIcon, PrinterIcon, ArrowUpIcon, ArrowDownIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline';
import { AppButton, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { rangeLabelForDetail } from '@/utils/labRanges';
import dayjs from 'dayjs';

const props = defineProps({
  result: { type: Object, required: true },
  // Bouton « Corriger ce resultat » (historique du labo, roles autorises seulement).
  canAmend: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'print', 'amend']);
const { t } = useI18n();

// --- COMPUTED ---
const getPatientName = computed(() => {
  const r = props.result;
  if (r.patient_info?.nom) return r.patient_info.nom;
  if (r.patient_name) return r.patient_name; 
  if (r.external_patient_info) return r.external_patient_info.nom_complet || t('lab.result_modal.external_patient');
  return t('lab.result_modal.anonymous');
});

const statusTone = computed(() => {
    switch(props.result.status) {
        case 'validated': return 'success';
        case 'completed': return 'info';
        default: return 'warning';
    }
});

// Colonnes du tableau des resultats (cartes empilees sous lg).
const columns = computed(() => [
    { key: 'param', label: t('lab.result_modal.param') },
    { key: 'result', label: t('lab.result_modal.result') },
    { key: 'unit', label: t('lab.result_modal.unit') },
    { key: 'ref', label: t('lab.result_modal.ref_values') },
    { key: 'interp', label: t('lab.result_modal.interpretation'), align: 'right' },
]);

// --- METHODS ---
const translateStatus = (status) => {
    const map = {
        'pending': t('lab.status.pending'),
        'completed': t('lab.status.completed'),
        'validated': t('lab.status.validated')
    };
    return map[status] || status || t('lab.result_modal.unknown');
};

const formatDate = (date) => {
    if (!date) return t('lab.result_modal.unknown_date');
    return dayjs(date).format('DD/MM/YYYY HH:mm');
};

// Fonction récupérée de ta paillasse pour lire la valeur de référence correctement
const getRange = (detail, info) => rangeLabelForDetail(detail, info?.sexe, info?.age_days ?? null, null);

// Le backend (GET /labo/results/{id}) renvoie `is_abnormal` par parametre ;
// `flag`/`flagged` restent lus en repli (autres sources, ex. saisie en cours).
const isAbnormal = (detail) =>
    !!(detail.is_abnormal || detail.flagged || ['H', 'L', 'A'].includes(detail.flag));

const flagLabel = (detail) => {
    const interp = (detail.interpretation || '').toLowerCase();
    if (interp === 'haut') return t('lab.result_modal.flag_high');
    if (interp === 'bas') return t('lab.result_modal.flag_low');
    return t('lab.result_modal.abnormal');
};

// Icone de l'anomalie, a cote du texte (haut, bas, ou anormal sans sens).
const flagIcon = (detail) => {
    const interp = (detail.interpretation || '').toLowerCase();
    if (interp === 'haut') return ArrowUpIcon;
    if (interp === 'bas') return ArrowDownIcon;
    return ExclamationTriangleIcon;
};

const printPdf = () => emit('print', props.result);
</script>
