<!-- src/views/modules/labstock/LabStockAlerts.vue -->
<!-- Alertes du stock labo. Breakpoints : < md = cartes empilees (360 px), md = 2 colonnes
     (stocks bas | peremptions), lg = deux tableaux cote a cote. Acces : READERS. -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between md:items-center bg-white p-4 md:p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-xl md:text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('labStock.alerts_title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('labStock.alerts_subtitle') }}</p>
      </div>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="isLoading" class="p-10 text-center text-gray-500">{{ t('stockOps.loading') }}</div>

    <template v-else-if="data">
      <!-- rappel de comptage -->
      <section class="rounded-2xl border p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
               :class="countDue ? 'bg-amber-50 border-amber-300' : 'bg-white border-gray-100 shadow-xs'">
        <div>
          <h2 class="font-semibold text-gray-800">{{ t('labStock.alerts_count_title') }}</h2>
          <p class="text-sm" :class="countDue ? 'text-amber-800' : 'text-gray-500'">{{ countText }}</p>
        </div>
        <router-link v-if="canCount" to="/dashboard/lab-stock-count"
                     class="inline-flex items-center justify-center w-full md:w-auto px-5 min-h-[44px] rounded-xl font-semibold text-white bg-emerald-600 hover:bg-emerald-700">
          {{ t('labStock.alerts_go_count') }}
        </router-link>
      </section>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <!-- stocks bas -->
        <section class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 space-y-3">
          <div class="flex items-center justify-between gap-3">
            <h2 class="font-semibold text-gray-800">{{ t('labStock.alerts_low_title') }}
              <span class="ml-1 text-xs font-bold px-2 py-0.5 rounded-full bg-orange-100 text-orange-700">{{ data.low.length }}</span>
            </h2>
          </div>
          <p v-if="!data.low.length" class="text-sm text-gray-500 italic py-4 text-center">{{ t('labStock.alerts_low_empty') }}</p>
          <ul v-else class="divide-y divide-gray-100">
            <li v-for="p in data.low" :key="p.product_id" class="py-3 flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="font-medium text-gray-900 break-words">{{ p.name }}</p>
                <p v-if="p.packaging" class="text-xs text-gray-500">{{ p.packaging }}</p>
                <p class="text-xs mt-1" :class="p.request_status ? 'text-blue-700' : 'text-gray-400'">
                  {{ p.request_status ? t('labStock.alerts_request_open', { status: label(requestStatusLabel(p.request_status)) }) : t('labStock.alerts_no_request') }}
                </p>
              </div>
              <span class="shrink-0 text-sm font-bold px-2 py-1 rounded-lg"
                    :class="Number(p.quantity) === 0 ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'">
                {{ t('labStock.alerts_qty_threshold', { quantity: Number(p.quantity), threshold: Number(p.alert_threshold) }) }}
              </span>
            </li>
          </ul>
          <router-link v-if="data.low.length" to="/dashboard/lab-stock-requests"
                       class="flex items-center justify-center w-full min-h-[44px] rounded-xl font-semibold border border-blue-200 text-blue-700 hover:bg-blue-50">
            {{ t('labStock.alerts_go_requests') }}
          </router-link>
        </section>

        <!-- peremptions -->
        <section class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 space-y-3">
          <h2 class="font-semibold text-gray-800">{{ t('labStock.alerts_expiring_title') }}
            <span class="ml-1 text-xs font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700">{{ data.expiring.length }}</span>
          </h2>
          <p v-if="!data.expiring.length" class="text-sm text-gray-500 italic py-4 text-center">{{ t('labStock.alerts_expiring_empty') }}</p>
          <ul v-else class="divide-y divide-gray-100">
            <li v-for="e in sortedExpiring" :key="e.receipt_line_id" class="py-3 flex items-start justify-between gap-3"
                :class="e.days_left < 0 ? 'bg-red-50 -mx-2 px-2 rounded-lg' : ''">
              <div class="min-w-0">
                <p class="font-medium break-words" :class="e.days_left < 0 ? 'text-red-800' : 'text-gray-900'">{{ e.product_name || '?' }}</p>
                <p class="text-xs text-gray-500">{{ t('labStock.alerts_lot', { lot: e.lot_number || '?' }) }} · {{ t('labStock.alerts_expiry_on', { date: formatDate(e.expiry_date) }) }}</p>
              </div>
              <span class="shrink-0 text-sm font-bold px-2 py-1 rounded-lg" :class="daysClass(e.days_left)">{{ daysText(e.days_left) }}</span>
            </li>
          </ul>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { requestStatusLabel } from '@/utils/labStockLabels';

const { t } = useI18n();
const auth = useAuthStore();
const data = ref(null);
const isLoading = ref(false);
const pageError = ref('');

const canCount = computed(() => auth.hasRole(['laborantin', 'admin']));
const label = (l) => (l.key ? t(l.key) : l.raw);
const formatDate = (v) => {
  if (!v) return '?';
  const [y, m, d] = String(v).slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString();
};
const sortedExpiring = computed(() => [...(data.value?.expiring || [])].sort((a, b) => a.days_left - b.days_left));
const countDue = computed(() => !!data.value?.count_status?.reminder_due);
const countText = computed(() => {
  const st = data.value?.count_status || {};
  if (st.days_since == null) return t('labStock.count_reminder_never');
  return st.reminder_due ? t('labStock.count_reminder', { days: st.days_since }) : t('labStock.alerts_count_ok', { days: st.days_since });
});
const daysText = (d) => (d < 0 ? t('labStock.alerts_expired', { days: -d }) : d === 0 ? t('labStock.alerts_expires_today') : t('labStock.alerts_days_left', { days: d }));
const daysClass = (d) => (d <= 0 ? 'bg-red-600 text-white' : d <= 15 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-800');

onMounted(async () => {
  isLoading.value = true;
  try {
    const r = await LabStockGateway.getAlerts();
    data.value = { low: r?.low || [], expiring: r?.expiring || [], count_status: r?.count_status || {} };
  } catch (e) {
    pageError.value = describeLabStockError(e, t('stockOps.error_load'));
  } finally {
    isLoading.value = false;
  }
});
</script>
