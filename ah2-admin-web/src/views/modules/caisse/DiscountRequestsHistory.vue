<!-- src/views/modules/caisse/DiscountRequestsHistory.vue -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('discount_history.title') }}</h1>
        <p class="text-sm text-gray-500">{{ pagination.total }} {{ t('discount_history.results') }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
        <p class="text-xs text-gray-500 font-medium uppercase">{{ t('discount_history.kpi.approved') }}</p>
        <p class="text-2xl font-bold text-green-700 mt-1">{{ kpi.approved_count }}</p>
      </div>
      <div class="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
        <p class="text-xs text-gray-500 font-medium uppercase">{{ t('discount_history.kpi.refused') }}</p>
        <p class="text-2xl font-bold text-red-600 mt-1">{{ kpi.refused_count }}</p>
      </div>
      <div class="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
        <p class="text-xs text-gray-500 font-medium uppercase">{{ t('discount_history.kpi.pending') }}</p>
        <p class="text-2xl font-bold text-amber-600 mt-1">{{ kpi.pending_count }}</p>
      </div>
      <div class="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
        <p class="text-xs text-gray-500 font-medium uppercase">{{ t('discount_history.kpi.total_reduced') }}</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{{ formatCurrency(kpi.total_reduced_amount) }}</p>
      </div>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-3 items-end">
      <div class="flex gap-2">
        <button v-for="preset in periodPresets" :key="preset.key" @click="applyPreset(preset.key)"
                :class="activePreset === preset.key ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
                class="px-3 py-2 rounded-lg text-sm font-medium transition">
          {{ t(preset.labelKey) }}
        </button>
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('caisse.table.date') }} ({{ t('discount_history.from') }})</label>
        <input v-model="dateFrom" type="date" @change="onCustomDateChange"
               class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('discount_history.to') }}</label>
        <input v-model="dateTo" type="date" @change="onCustomDateChange"
               class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-48">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('caisse.table.status') }}</label>
        <select v-model="statusFilter" @change="fetchAll"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
          <option value="">{{ t('caisse.status.all') }}</option>
          <option value="approved">{{ t('discount_history.status.approved') }}</option>
          <option value="refused">{{ t('discount_history.status.refused') }}</option>
          <option value="pending">{{ t('discount_history.status.pending') }}</option>
          <option value="cancelled">{{ t('discount_history.status.cancelled') }}</option>
        </select>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></span>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('discount_history.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('discount_history.table.requested_by') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('discount_history.table.decided_by') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('discount_history.table.invoice_amount') }}</th>
              <th class="px-6 py-4 font-semibold text-right">%</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('discount_history.table.reduced_amount') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.status') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="r in rows" :key="r.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(r.created_at) }}</td>
              <td class="px-6 py-4 text-sm text-gray-900">{{ r.patient_label || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-700">{{ r.requested_by_name || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-700">{{ r.decided_by_name || '—' }}</td>
              <td class="px-6 py-4 text-right text-sm font-medium">{{ formatCurrency(r.original_amount) }}</td>
              <td class="px-6 py-4 text-right text-sm">{{ r.decision_percent ? `${r.decision_percent}%` : '—' }}</td>
              <td class="px-6 py-4 text-right text-sm font-semibold text-green-700">{{ r.reduced_amount ? formatCurrency(r.reduced_amount) : '—' }}</td>
              <td class="px-6 py-4">
                <span :class="statusBadgeClass(r.status)" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium">
                  {{ t(`discount_history.status.${r.status}`) }}
                </span>
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="8" class="px-6 py-8 text-center text-gray-500 italic">{{ t('discount_history.empty') }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">Page {{ pagination.page }} / {{ pagination.total_pages }}</p>
        <div class="flex space-x-2">
          <button @click="goToPage(pagination.page - 1)" :disabled="pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(pagination.page + 1)" :disabled="pagination.page === pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';
import { DiscountRequestGateway } from '@/services/DiscountRequestGateway';

const { t } = useI18n();

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

const toISO = (d) => d.toISOString().slice(0, 10);

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
const formatDate = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR') : '—');

const statusBadgeClass = (status) => ({
  approved: 'bg-green-100 text-green-800',
  refused: 'bg-red-100 text-red-800',
  pending: 'bg-amber-100 text-amber-800',
  cancelled: 'bg-gray-200 text-gray-600',
}[status] || 'bg-gray-200 text-gray-600');

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
