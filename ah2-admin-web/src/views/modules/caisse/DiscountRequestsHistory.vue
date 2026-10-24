<!-- src/views/modules/caisse/DiscountRequestsHistory.vue -->
<template>
  <div class="grid w-full gap-6">
    <PageHeader :title="t('discount_history.title')" :subtitle="`${pagination.total} ${t('discount_history.results')}`" />

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatTile :title="t('discount_history.kpi.approved')" :value="kpi.approved_count" tone="success" />
      <StatTile :title="t('discount_history.kpi.refused')" :value="kpi.refused_count" tone="danger" />
      <StatTile :title="t('discount_history.kpi.pending')" :value="kpi.pending_count" tone="warning" />
      <StatTile :title="t('discount_history.kpi.total_reduced')" :value="formatCurrency(kpi.total_reduced_amount)" />
    </div>

    <section :aria-label="t('discountScreens.filters')" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:flex lg:flex-wrap lg:items-end">
      <div class="flex flex-wrap gap-2 md:col-span-2" role="group">
        <button v-for="preset in periodPresets" :key="preset.key" type="button" @click="applyPreset(preset.key)"
                :aria-pressed="activePreset === preset.key"
                :class="activePreset === preset.key ? 'bg-brand-600 text-white border-transparent' : 'bg-white text-ink border-tone-neutral-border hover:bg-tone-neutral-bg'"
                class="min-h-11 rounded-control border px-4 text-base font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600">
          {{ t(preset.labelKey) }}
        </button>
      </div>
      <div class="lg:w-48">
        <FormField id="dh-from" :label="`${t('caisse.table.date')} (${t('discount_history.from')})`" v-slot="{ describedBy }">
          <input id="dh-from" v-model="dateFrom" type="date" @change="onCustomDateChange" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-48">
        <FormField id="dh-to" :label="t('discount_history.to')" v-slot="{ describedBy }">
          <input id="dh-to" v-model="dateTo" type="date" @change="onCustomDateChange" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-56">
        <FormField id="dh-status" :label="t('caisse.table.status')" v-slot="{ describedBy }">
          <select id="dh-status" v-model="statusFilter" @change="fetchAll" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ t('caisse.status.all') }}</option>
            <option value="approved">{{ t('discount_history.status.approved') }}</option>
            <option value="refused">{{ t('discount_history.status.refused') }}</option>
            <option value="pending">{{ t('discount_history.status.pending') }}</option>
            <option value="cancelled">{{ t('discount_history.status.cancelled') }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <section class="grid gap-3">
      <ResponsiveTable
        :columns="columns"
        :rows="rows"
        row-key="id"
        :loading="isLoading"
        :empty-title="t('discount_history.empty')"
        :empty-message="' '"
      >
        <template #cell-date="{ row: r }"><span class="font-mono">{{ formatDate(r.created_at) }}</span></template>
        <template #cell-patient="{ row: r }">{{ r.patient_label || '-' }}</template>
        <template #cell-requested_by="{ row: r }">{{ r.requested_by_name || '-' }}</template>
        <template #cell-decided_by="{ row: r }">{{ r.decided_by_name || '-' }}</template>
        <template #cell-invoice_amount="{ row: r }"><span class="font-medium">{{ formatCurrency(r.original_amount) }}</span></template>
        <template #cell-percent="{ row: r }">{{ r.decision_percent ? `${r.decision_percent}%` : '-' }}</template>
        <template #cell-reduced_amount="{ row: r }">
          <span class="font-semibold text-tone-success-text">{{ r.reduced_amount ? formatCurrency(r.reduced_amount) : '-' }}</span>
        </template>
        <template #cell-status="{ row: r }">
          <StatusBadge :tone="statusTone(r.status)" :label="t(`discount_history.status.${r.status}`)" />
        </template>
      </ResponsiveTable>

      <div v-if="pagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">Page {{ pagination.page }} / {{ pagination.total_pages }}</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="t('discountScreens.prev_page')" @click="goToPage(pagination.page - 1)" :disabled="pagination.page === 1" />
          <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="t('discountScreens.next_page')" @click="goToPage(pagination.page + 1)" :disabled="pagination.page === pagination.total_pages" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';
import { DiscountRequestGateway } from '@/services/DiscountRequestGateway';
import { todayLocalISO } from '@/utils/localDate';
import { AppButton, PageHeader, FormField, StatTile, StatusBadge, ResponsiveTable } from '@/components/ui';

const { t } = useI18n();

// Colonnes du tableau (cartes sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'date', label: t('discount_history.table.date') },
  { key: 'patient', label: t('caisse.table.patient') },
  { key: 'requested_by', label: t('discount_history.table.requested_by') },
  { key: 'decided_by', label: t('discount_history.table.decided_by') },
  { key: 'invoice_amount', label: t('discount_history.table.invoice_amount'), align: 'right' },
  { key: 'percent', label: '%', align: 'right' },
  { key: 'reduced_amount', label: t('discount_history.table.reduced_amount'), align: 'right' },
  { key: 'status', label: t('caisse.table.status') },
]);
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const rows = ref([]);
const isLoading = ref(false);
const kpi = reactive({ approved_count: 0, refused_count: 0, pending_count: 0, cancelled_count: 0, total_reduced_amount: 0 });
const pagination = reactive({ page: 1, per_page: 20, total: 0, total_pages: 1 });

const dateFrom = ref('');
const dateTo = ref('');
const statusFilter = ref('');
const activePreset = ref('month');

const periodPresets = [
  { key: 'week', labelKey: 'discount_history.preset.week' },
  { key: 'month', labelKey: 'discount_history.preset.month' },
  { key: 'custom', labelKey: 'discount_history.preset.custom' },
];

const toISO = (d) => todayLocalISO(d); // date locale (pas UTC)

const applyPreset = (key) => {
  activePreset.value = key;
  const today = new Date();
  if (key === 'week') {
    const day = today.getDay() || 7; // lundi=1..dimanche=7
    const monday = new Date(today);
    monday.setDate(today.getDate() - day + 1);
    dateFrom.value = toISO(monday);
    dateTo.value = toISO(today);
  } else if (key === 'month') {
    const first = new Date(today.getFullYear(), today.getMonth(), 1);
    dateFrom.value = toISO(first);
    dateTo.value = toISO(today);
  }
  // 'custom' : on laisse les champs tels quels, l'utilisateur choisit lui-meme
  if (key !== 'custom') fetchAll();
};

const onCustomDateChange = () => {
  activePreset.value = 'custom';
  fetchAll();
};

const formatCurrency = (v) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(v || 0).replace('XOF', 'FCFA');
const formatDate = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR') : '-');

// Vert = approuve, rouge = refuse, orange = en attente, neutre = annule (toujours avec le texte du statut).
const statusTone = (status) => ({
  approved: 'success',
  refused: 'danger',
  pending: 'warning',
  cancelled: 'neutral',
}[status] || 'neutral');

const currentParams = () => ({
  date_from: dateFrom.value || undefined,
  date_to: dateTo.value || undefined,
  status: statusFilter.value || undefined,
});

const fetchHistory = async () => {
  isLoading.value = true;
  try {
    const resp = await DiscountRequestGateway.getHistory({ ...currentParams(), page: pagination.page, per_page: pagination.per_page });
    rows.value = resp.data.data || [];
    pagination.total = resp.data.total || 0;
    pagination.total_pages = Math.ceil(pagination.total / pagination.per_page) || 1;
  } finally {
    isLoading.value = false;
  }
};

const fetchKpi = async () => {
  const resp = await DiscountRequestGateway.getKpi(currentParams());
  Object.assign(kpi, resp.data);
};

const fetchAll = () => {
  pagination.page = 1;
  fetchHistory();
  fetchKpi();
};

const goToPage = (page) => {
  if (page < 1 || page > pagination.total_pages) return;
  pagination.page = page;
  fetchHistory();
};

onMounted(() => {
  applyPreset('month');
});
</script>
