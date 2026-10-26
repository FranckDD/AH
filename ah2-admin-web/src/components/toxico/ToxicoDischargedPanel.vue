<template>
  <div class="grid gap-4">
    <!-- Filtres -->
    <section :aria-label="t('toxico.discharged.filters.search')" class="grid grid-cols-1 gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:grid-cols-4">
      <FormField id="tox-dis-search" :label="t('toxico.discharged.filters.search')" v-slot="{ describedBy }">
        <input id="tox-dis-search" :value="store.dischargedFilters.search" @input="onSearch" type="search"
               :placeholder="t('toxico.discharged.filters.search_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="tox-dis-reason" :label="t('toxico.discharged.filters.reason')" v-slot="{ describedBy }">
        <select id="tox-dis-reason" :value="store.dischargedFilters.reason" @change="store.setDischargedFilters({ reason: $event.target.value })" :aria-describedby="describedBy" :class="fieldClass">
          <option value="">{{ t('toxico.discharged.filters.all_reasons') }}</option>
          <option v-for="r in DISCHARGE_REASONS" :key="r" :value="r">{{ t(dischargeReasonLabelKey(r)) }}</option>
        </select>
      </FormField>
      <FormField id="tox-dis-from" :label="t('toxico.discharged.filters.from')" v-slot="{ describedBy }">
        <input id="tox-dis-from" type="date" :value="dateFrom" @change="onDate('from', $event.target.value)" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="tox-dis-to" :label="t('toxico.discharged.filters.to')" v-slot="{ describedBy }">
        <input id="tox-dis-to" type="date" :value="dateTo" @change="onDate('to', $event.target.value)" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <p v-if="dateError" role="alert" class="text-base font-medium text-tone-danger-text md:col-span-2 lg:col-span-4">{{ t(dateError) }}</p>
      <div v-if="canExportList" class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end md:col-span-2 lg:col-span-4">
        <p v-if="exportError" role="alert" class="text-base font-medium text-tone-danger-text sm:mr-auto">{{ t(exportError) }}</p>
        <AppButton :disabled="listExporting || !!dateError" :loading="listExporting" @click="exportList">
          {{ listExporting ? t('toxico.export.exporting') : t('toxico.export.list_pdf') }}
        </AppButton>
      </div>
    </section>

    <!-- Etats (periode invalide : resultats vides, pas d'ancienne periode appliquee en silence) -->
    <p v-if="dateError" role="status" class="rounded-card border border-tone-neutral-border bg-white p-10 text-center text-base text-ink-muted shadow-card">{{ t('toxico.discharged.invalid_range_hint') }}</p>
    <p v-else-if="store.dischargedLoading" role="status" class="rounded-card border border-tone-neutral-border bg-white p-10 text-center text-base text-ink-muted shadow-card">{{ t('toxico.discharged.loading') }}</p>
    <div v-else-if="store.dischargedError" role="alert" class="grid justify-items-center gap-3 rounded-card border border-tone-neutral-border bg-white p-10 text-center shadow-card">
      <p class="text-base font-medium text-tone-danger-text">{{ t('toxico.discharged.error') }}</p>
      <AppButton @click="store.fetchDischarged()">{{ t('toxico.discharged.retry') }}</AppButton>
    </div>

    <ResponsiveTable v-else :columns="columns" :rows="store.discharged" row-key="dossier_id" :empty-title="t('toxico.discharged.empty')" :empty-message="' '" striped>
      <template #cell-patient="{ row }">
        <span class="block font-semibold">{{ row.patientName }}</span>
        <span class="block font-mono text-sm text-ink-muted">{{ row.code }}</span>
      </template>
      <template #cell-stay="{ row }">{{ stayDates(row) }}</template>
      <template #cell-reason="{ row }">
        <StatusBadge :tone="reasonTone(row.last_stay?.discharge_reason)" :label="t(dischargeReasonLabelKey(row.last_stay?.discharge_reason))" />
      </template>
      <template #cell-psy="{ row }">{{ row.last_stay?.psychologist_name || t('toxico.discharged.none') }}</template>
      <template #cell-stays="{ row }"><span class="font-semibold">{{ row.stays_count }}</span></template>
      <template #actions="{ row }">
        <AppButton variant="info" size="sm" @click="$emit('view', row)">{{ t('toxico.discharged.view') }}</AppButton>
        <AppButton v-if="canExportDossier" variant="secondary" size="sm" :title="t('toxico.export.dossier_pdf')" :disabled="rowExporting === row.patient_id" @click="exportRow(row)">
          {{ rowExporting === row.patient_id ? t('toxico.export.exporting') : t('toxico.export.row_pdf') }}
        </AppButton>
        <AppButton v-if="canReadmit" variant="success" size="sm" @click="$emit('readmit', row)">{{ t('toxico.discharged.readmit') }}</AppButton>
      </template>
    </ResponsiveTable>

    <!-- Pagination : visible des qu'il existe des lignes, meme si la page courante est vide -->
    <nav v-if="!dateError && !store.dischargedLoading && !store.dischargedError && store.dischargedTotal > 0"
         class="flex items-center justify-between gap-2 rounded-card border border-tone-neutral-border bg-white p-3 shadow-card" :aria-label="t('toxico.discharged.pagination')">
      <AppButton variant="secondary" :disabled="page <= 1" @click="store.setDischargedPage(page - 1)">{{ t('toxico.discharged.prev') }}</AppButton>
      <span class="text-base text-ink">
        {{ t('toxico.discharged.page_of', { page, pages: Math.max(store.dischargedTotalPages, 1), total: store.dischargedTotal }, store.dischargedTotal) }}
      </span>
      <AppButton variant="secondary" :disabled="page >= Math.max(store.dischargedTotalPages, 1)" @click="store.setDischargedPage(page + 1)">{{ t('toxico.discharged.next') }}</AppButton>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { DISCHARGE_REASONS, dischargeReasonLabelKey } from '@/utils/toxicoStays';
import { dischargedDateRangeError } from '@/utils/toxicoDischarged';
import { formatDateDMY } from '@/utils/localDate';
import { useAuthStore } from '@/stores/auth';
import { AppButton, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';
import { ToxicoGateway } from '@/services/ToxicoGateway';
import {
    buildDischargedExportQuery, resolveExportSearch, downloadPdfBlob, dossierExportFilename, exportErrorKey,
    DISCHARGED_EXPORT_FILENAME, TOXICO_DOSSIER_EXPORT_ROLES, TOXICO_LIST_EXPORT_ROLES,
} from '@/utils/toxicoExport';

defineProps({ canReadmit: { type: Boolean, default: false } });
defineEmits(['view', 'readmit']);

const { t } = useI18n();
const store = useToxicoStore();
const page = computed(() => store.dischargedFilters.page);

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
    { key: 'patient', label: t('toxico.discharged.col.patient') },
    { key: 'stay', label: t('toxico.discharged.col.stay') },
    { key: 'reason', label: t('toxico.discharged.col.reason') },
    { key: 'psy', label: t('toxico.discharged.col.psy') },
    { key: 'stays', label: t('toxico.discharged.col.stays'), align: 'center' },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';


// --- Exports PDF ---
const authStore = useAuthStore();
const canExportList = computed(() => authStore.hasRole(TOXICO_LIST_EXPORT_ROLES));
const canExportDossier = computed(() => authStore.hasRole(TOXICO_DOSSIER_EXPORT_ROLES));
const listExporting = ref(false);
const rowExporting = ref(null);
const exportError = ref(null);
const exportList = async () => {
    listExporting.value = true;
    exportError.value = null;
    try {
        // Memes filtres que l'ecran (dates locales validees), toutes les pages.
        // Saisie en attente (debounce) : on l'applique d'abord (liste + export alignes).
        const search = resolveExportSearch(pendingSearch, store.dischargedFilters.search);
        if (pendingSearch !== null) {
            clearTimeout(searchTimeout);
            pendingSearch = null;
            if (!dateError.value) store.setDischargedFilters({ search });
            else store.dischargedFilters.search = search;
        }
        const params = buildDischargedExportQuery({ ...store.dischargedFilters, search, from: dateFrom.value, to: dateTo.value });
        const res = await ToxicoGateway.exportDischargedPdf(params);
        downloadPdfBlob(res.data, DISCHARGED_EXPORT_FILENAME);
    } catch (e) {
        exportError.value = exportErrorKey(e);
    } finally {
        listExporting.value = false;
    }
};
const exportRow = async (row) => {
    rowExporting.value = row.patient_id;
    exportError.value = null;
    try {
        const res = await ToxicoGateway.exportDossierPdf(row.patient_id);
        downloadPdfBlob(res.data, dossierExportFilename(row.patient_id));
    } catch (e) {
        exportError.value = exportErrorKey(e);
    } finally {
        rowExporting.value = null;
    }
};

// Dates saisies localement : envoyees seulement si la periode est valide.
const dateFrom = ref(store.dischargedFilters.from);
const dateTo = ref(store.dischargedFilters.to);
const dateError = computed(() => dischargedDateRangeError(dateFrom.value, dateTo.value));
const onDate = (which, value) => {
    if (which === 'from') dateFrom.value = value; else dateTo.value = value;
    if (dateError.value) store.clearDischarged();
    else store.setDischargedFilters({ from: dateFrom.value, to: dateTo.value });
};

let searchTimeout;
let pendingSearch = null;
const onSearch = (e) => {
    clearTimeout(searchTimeout);
    const value = e.target.value;
    pendingSearch = value;
    searchTimeout = setTimeout(() => {
        pendingSearch = null;
        if (dateError.value) store.dischargedFilters.search = value;
        else store.setDischargedFilters({ search: value });
    }, 400);
};

const fmt = (d) => (d ? formatDateDMY(d) : '-');
const stayDates = (row) => row.last_stay
    ? t('toxico.discharged.stay_dates', { n: row.last_stay.stay_number, from: fmt(row.last_stay.admission_date), to: fmt(row.last_stay.discharge_date) })
    : t('toxico.discharged.no_stay');

// Meme couleurs qu'avant (vert, orange, rouge, gris) via les tonalites du theme ; le motif reste ecrit.
const reasonTone = (r) => ({
    guerison: 'success',
    abandon: 'warning',
    exclusion: 'danger',
    autre: 'neutral',
}[r] || 'neutral');

onMounted(() => { if (!dateError.value) store.fetchDischarged(); });
onBeforeUnmount(() => clearTimeout(searchTimeout));
</script>
