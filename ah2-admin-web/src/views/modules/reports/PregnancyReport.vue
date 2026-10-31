<template>
  <div class="mx-auto grid max-w-6xl gap-6 pb-6" data-testid="pregnancy-report">
    <PageHeader :title="$t('pregnancy.report_title')" :subtitle="$t('pregnancy.report_subtitle')" />

    <AppCard>
      <form class="grid gap-4 md:grid-cols-[1fr_1fr_auto_auto] md:items-end" @submit.prevent="load">
        <FormField id="preg-report-from" :label="$t('pregnancy.report_from')" v-slot="{ describedBy }">
          <input id="preg-report-from" v-model="from" type="date" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="preg-report-to" :label="$t('pregnancy.report_to')" v-slot="{ describedBy }">
          <input id="preg-report-to" v-model="to" type="date" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <AppButton type="submit" :disabled="!!rangeError || loading" :loading="loading">{{ $t('pregnancy.report_run') }}</AppButton>
        <AppButton variant="secondary" :disabled="!!rangeError || downloading" :loading="downloading" @click="downloadPdf">{{ $t('pregnancy.report_pdf') }}</AppButton>
      </form>
      <p v-if="rangeError" role="alert" class="mt-3 text-base font-medium text-tone-danger-text" data-testid="pregnancy-range-error">{{ $t('pregnancy.report_range_error') }}</p>
    </AppCard>

    <p v-if="errorText" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ errorText }}</p>

    <AppCard v-if="report">
      <template #actions>
        <span class="text-base font-semibold text-ink" data-testid="pregnancy-total">{{ $t('pregnancy.report_total', { patients: report.total_patients, rows: report.total_rows }) }}</span>
      </template>
      <ResponsiveTable :columns="columns" :rows="rows" row-key="key" :loading="loading" :empty-title="$t('pregnancy.report_empty')" striped>
        <template #cell-number="{ row }">{{ row.patient_number || $t('pregnancy.report_external') }}</template>
        <template #cell-ga="{ row }">{{ row.gestational_age_weeks ?? '-' }}</template>
        <template #cell-program="{ row }">{{ row.pregnancy_program_number || '-' }}</template>
        <template #cell-exams="{ row }">{{ row.exams.join(', ') }}</template>
      </ResponsiveTable>
    </AppCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { AppButton, AppCard, FormField, PageHeader, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { localTodayIso } from '@/utils/labAge';
import { defaultPeriod, frDate, periodError, reportParams } from '@/utils/pregnancyReport';
import { describeServerError } from '@/utils/serverError';

const { t } = useI18n();
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const initial = defaultPeriod(localTodayIso());
const from = ref(initial.from);
const to = ref(initial.to);
const report = ref(null);
const loading = ref(false);
const downloading = ref(false);
const errorText = ref('');

const rangeError = computed(() => periodError(from.value, to.value));
const columns = computed(() => [
  { key: 'date', label: t('pregnancy.report_col_date') },
  { key: 'number', label: t('pregnancy.report_col_number') },
  { key: 'patient_name', label: t('pregnancy.report_col_name') },
  { key: 'program', label: t('pregnancy.report_col_program') },
  { key: 'ga', label: t('pregnancy.report_col_ga') },
  { key: 'exams', label: t('pregnancy.report_col_exams') },
]);
const rows = computed(() => (report.value ? report.value.rows.map((r, i) => ({ ...r, key: i, date: frDate(r.validated_on) })) : []));

async function load() {
  if (rangeError.value) return;
  loading.value = true;
  errorText.value = '';
  try {
    const { data } = await api.get('/labo/reports/pregnancy', { params: reportParams(from.value, to.value) });
    report.value = data;
  } catch (err) {
    report.value = null;
    errorText.value = describeServerError(err, t('pregnancy.report_error'));
  } finally {
    loading.value = false;
  }
}

async function downloadPdf() {
  if (rangeError.value) return;
  downloading.value = true;
  errorText.value = '';
  try {
    const response = await api.get('/labo/reports/pregnancy.pdf', { params: reportParams(from.value, to.value), responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `rapport_grossesse_${from.value}_${to.value}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    errorText.value = t('pregnancy.report_pdf_error');
  } finally {
    downloading.value = false;
  }
}

onMounted(load);
</script>
