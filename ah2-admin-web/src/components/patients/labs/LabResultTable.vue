<template>
  <div class="grid gap-3">
    <ResponsiveTable
      :columns="columns"
      :rows="results"
      row-key="result_id"
      :empty-title="t('lab.patient_table.empty')"
      :empty-message="' '"
    >
      <template #cell-date="{ row: res }">{{ res.test_date }}</template>
      <template #cell-exam="{ row: res }"><span class="font-medium text-ink">{{ res.examen_name }}</span></template>
      <template #cell-lab_code="{ row: res }"><span class="font-mono text-ink-muted">{{ res.code_lab }}</span></template>
      <template #cell-status="{ row: res }">
        <div class="flex flex-wrap items-center gap-2">
          <StatusBadge :tone="statusTone(res.status)" :label="statusLabel(res.status)" />
          <StatusBadge
            v-if="res.nb_anormaux > 0"
            tone="danger"
            :label="t('lab.patient_table.abnormal_count', { n: res.nb_anormaux }, res.nb_anormaux)"
          />
          <StatusBadge v-if="res.corrected" tone="info" :label="t('lab.technician.corrected_badge')" />
        </div>
      </template>

      <template #actions="{ row: res }">
        <AppButton variant="secondary" @click="openDetail(res)">
          {{ t('lab.patient_table.view_results') }}
        </AppButton>
      </template>
    </ResponsiveTable>

    <p v-if="detailError" role="alert" class="text-base font-medium text-tone-danger-text">{{ detailError }}</p>

    <ResultDetailModal
        v-if="selectedResult"
        :result="selectedResult"
        @close="selectedResult = null"
        @print="downloadPdf"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useLabStore } from '@/stores/labStore';
import ResultDetailModal from '@/components/lab/ResultDetailModal.vue';
import { AppButton, StatusBadge, ResponsiveTable } from '@/components/ui';

defineProps({
    results: { type: Array, default: () => [] }
});

const { t } = useI18n();
const labStore = useLabStore();
const selectedResult = ref(null);
const detailError = ref('');

const columns = computed(() => [
    { key: 'date', label: t('lab.patient_table.date') },
    { key: 'exam', label: t('lab.patient_table.exam') },
    { key: 'lab_code', label: t('lab.patient_table.lab_code') },
    { key: 'status', label: t('lab.patient_table.status') },
]);

// Vert = termine, orange = en attente, neutre sinon (toujours accompagne du libelle).
const statusTone = (status) => {
    switch(status) {
        case 'completed': return 'success';
        case 'pending': return 'warning';
        default: return 'neutral';
    }
};

const statusLabel = (status) => {
    const known = ['pending', 'partial', 'analyzed', 'completed', 'validated'];
    return known.includes(status) ? t(`lab.status.${status}`) : (status || '');
};

// Le detail (valeurs, flags, normes) est charge a la demande : la liste du
// dossier reste legere et n'embarque que le compteur d'anomalies.
const openDetail = async (res) => {
    detailError.value = '';
    const detail = await labStore.fetchResultDetail(res.result_id);
    if (detail) {
        selectedResult.value = detail;
    } else {
        detailError.value = t('lab.patient_table.detail_unavailable');
    }
};

const downloadPdf = async (item) => {
    await labStore.downloadPDF(item.result_id, `Resultat_${item.result_id}.pdf`);
};
</script>
