<!-- src/views/modules/labstock/LabStockExpenses.vue -->
<!-- Depenses du stock labo. Breakpoints : < md = blocs empiles (360 px, filtres pleine largeur),
     md = total + fournisseurs sur 2 colonnes, lg = mois (2/3) | fournisseurs (1/3), historique de
     prix en tableau. Acces : SPENDERS (promoteur, ToxicoManager, admin). -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col lg:flex-row justify-between lg:items-end bg-white p-4 md:p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-xl md:text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('labStock.ex_title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('labStock.ex_subtitle') }}</p>
      </div>
      <form class="grid grid-cols-2 md:flex md:items-end gap-3" @submit.prevent="load">
        <label class="text-sm text-gray-700">{{ t('labStock.ex_from') }}
          <input v-model="from" type="date" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 text-sm" />
        </label>
        <label class="text-sm text-gray-700">{{ t('labStock.ex_to') }}
          <input v-model="to" type="date" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 text-sm" />
        </label>
        <button type="submit" :disabled="isLoading"
                class="col-span-2 md:col-span-1 px-5 py-2 min-h-[44px] lg:min-h-0 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
          {{ t('labStock.ex_apply') }}
        </button>
      </form>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="isLoading && !data" class="p-10 text-center text-gray-500">{{ t('stockOps.loading') }}</div>

    <template v-if="data">
      <section class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 md:p-6">
        <p class="text-sm text-gray-500">{{ t('labStock.ex_total') }}</p>
        <p class="text-2xl md:text-3xl font-extrabold text-gray-900">{{ formatMoney(data.total) }}</p>
        <p class="text-xs text-gray-400 mt-1">{{ t('labStock.ex_period', { from: formatDate(data.from), to: formatDate(data.to) }) }}</p>
      </section>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-start">
        <section class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 md:p-6 lg:col-span-2">
          <h2 class="font-semibold text-gray-800 mb-3">{{ t('labStock.ex_by_month') }}</h2>
          <p v-if="!bars.some((b) => !b.empty)" class="text-sm text-gray-500 italic text-center py-4">{{ t('labStock.ex_empty') }}</p>
          <ul v-else class="space-y-2">
            <li v-for="b in bars" :key="b.month" class="grid grid-cols-[5rem_1fr] md:grid-cols-[6rem_1fr_9rem] items-center gap-x-3 gap-y-1">
              <span class="text-xs text-gray-600 capitalize">{{ monthLabel(b.month, locale) }}</span>
              <div class="h-4 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 rounded-full" :style="{ width: b.pct + '%' }"></div>
              </div>
              <span class="col-start-2 md:col-start-auto text-xs md:text-sm md:text-right" :class="b.empty ? 'text-gray-400' : 'text-gray-900 font-medium'">{{ formatMoney(b.total) }}</span>
            </li>
          </ul>
        </section>

        <section class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 md:p-6">
          <h2 class="font-semibold text-gray-800 mb-3">{{ t('labStock.ex_by_supplier') }}</h2>
          <p v-if="!data.by_supplier.length" class="text-sm text-gray-500 italic text-center py-4">{{ t('labStock.ex_empty') }}</p>
          <ul v-else class="divide-y divide-gray-100">
            <li v-for="s in data.by_supplier" :key="s.supplier" class="py-2 flex justify-between gap-3">
              <span class="text-sm text-gray-800 break-words min-w-0">{{ s.supplier }}</span>
              <span class="text-sm font-semibold text-gray-900 shrink-0">{{ formatMoney(s.total) }}</span>
            </li>
          </ul>
        </section>
      </div>
    </template>

    <section class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 md:p-6 space-y-4">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <h2 class="font-semibold text-gray-800">{{ t('labStock.ex_price_title') }}</h2>
        <select v-model="productId" @change="loadPrices"
                class="w-full md:w-72 px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 text-sm">
          <option value="">{{ t('labStock.ex_price_choose') }}</option>
          <option v-for="p in products" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
        </select>
      </div>
      <div v-if="priceError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ priceError }}</div>
      <template v-if="productId && !priceLoading && !priceError">
        <p v-if="!prices.length" class="text-sm text-gray-500 italic text-center py-4">{{ t('labStock.ex_price_empty') }}</p>
        <template v-else>
          <ul class="lg:hidden divide-y divide-gray-100">
            <li v-for="(h, i) in prices" :key="i" class="py-3 flex justify-between gap-3">
              <div class="min-w-0">
                <p class="text-sm font-medium text-gray-900">{{ formatDate(h.delivery_date) }}</p>
                <p class="text-xs text-gray-500 break-words">{{ h.supplier }} · {{ t('labStock.mv_ref_receipt', { id: h.receipt_id }) }}</p>
              </div>
              <div class="text-right shrink-0">
                <p class="text-sm font-bold text-gray-900">{{ formatMoney(h.unit_price) }}</p>
                <p class="text-xs text-gray-500">× {{ Number(h.received_qty) }}</p>
              </div>
            </li>
          </ul>
          <div class="hidden lg:block overflow-x-auto">
            <table class="min-w-full text-left border-collapse">
              <thead>
                <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                  <th class="px-6 py-3 font-semibold">{{ t('labStock.ex_col_date') }}</th>
                  <th class="px-6 py-3 font-semibold">{{ t('labStock.ex_col_supplier') }}</th>
                  <th class="px-6 py-3 font-semibold">{{ t('labStock.ex_col_receipt') }}</th>
                  <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.ex_col_qty') }}</th>
                  <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.ex_col_price') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="(h, i) in prices" :key="i">
                  <td class="px-6 py-3 text-sm text-gray-700">{{ formatDate(h.delivery_date) }}</td>
                  <td class="px-6 py-3 text-sm text-gray-700">{{ h.supplier }}</td>
                  <td class="px-6 py-3 text-sm text-gray-500">{{ t('labStock.mv_ref_receipt', { id: h.receipt_id }) }}</td>
                  <td class="px-6 py-3 text-sm text-right text-gray-900">{{ Number(h.received_qty) }}</td>
                  <td class="px-6 py-3 text-sm text-right font-bold text-gray-900">{{ formatMoney(h.unit_price) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </template>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { formatMoney } from '@/utils/labReceiptLines';
import { buildMonthBars, monthLabel } from '@/utils/labStockExpenses';

const { t, locale } = useI18n();
const from = ref('');
const to = ref('');
const data = ref(null);
const isLoading = ref(false);
const pageError = ref('');
const products = ref([]);
const productId = ref('');
const prices = ref([]);
const priceLoading = ref(false);
const priceError = ref('');

const bars = computed(() => (data.value ? buildMonthBars(data.value.by_month, data.value.from, data.value.to) : []));
const formatDate = (v) => {
  if (!v) return '?';
  const [y, m, d] = String(v).slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString();
};

async function load() {
  isLoading.value = true;
  pageError.value = '';
  try {
    const r = await LabStockGateway.expenses({ from: from.value, to: to.value });
    data.value = { total: r?.total ?? 0, from: r?.from, to: r?.to, by_month: r?.by_month || [], by_supplier: r?.by_supplier || [] };
    if (!from.value && r?.from) from.value = String(r.from).slice(0, 10);
    if (!to.value && r?.to) to.value = String(r.to).slice(0, 10);
  } catch (e) {
    pageError.value = describeLabStockError(e, t('stockOps.error_load'));
  } finally {
    isLoading.value = false;
  }
}

async function loadPrices() {
  prices.value = [];
  priceError.value = '';
  if (!productId.value) return;
  priceLoading.value = true;
  try {
    prices.value = await LabStockGateway.priceHistory(Number(productId.value));
  } catch (e) {
    priceError.value = describeLabStockError(e, t('stockOps.error_load'));
  } finally {
    priceLoading.value = false;
  }
}

onMounted(async () => {
  load();
  try {
    products.value = await LabStockGateway.listProducts({ includeInactive: true });
  } catch { products.value = []; }
});
</script>
