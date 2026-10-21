<!-- src/views/modules/labstock/LabStockMovements.vue -->
<!-- Historique des mouvements du stock labo. Breakpoints : < md = cartes empilees (360 px),
     md = cartes sur 2 colonnes, lg = tableau. Filtre produit. Acces : READERS. -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between md:items-center bg-white p-4 md:p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-xl md:text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('labStock.mv_title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('labStock.mv_subtitle') }}</p>
      </div>
      <select v-model="productId" @change="load"
              class="w-full md:w-72 px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 text-sm">
        <option value="">{{ t('labStock.mv_all_products') }}</option>
        <option v-for="p in products" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
      </select>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="isLoading" class="p-10 text-center text-gray-500">{{ t('stockOps.loading') }}</div>
    <div v-else-if="!rows.length" class="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-500 italic">{{ t('labStock.mv_empty') }}</div>

    <template v-else>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 lg:hidden">
        <article v-for="m in rows" :key="m.id" class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 space-y-2">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h3 class="font-semibold text-gray-900 break-words">{{ m.product_name || '?' }}</h3>
              <span class="inline-block mt-1 text-xs font-semibold px-2 py-0.5 rounded-full" :class="typeClass(m.movement_type)">{{ typeLabel(m.movement_type) }}</span>
            </div>
            <div class="text-right shrink-0">
              <div class="text-2xl font-bold leading-none" :class="changeClass(m.change_qty)">{{ signed(m.change_qty) }}</div>
              <div class="text-xs text-gray-500 mt-1">{{ t('labStock.mv_col_after') }} : {{ Number(m.quantity_after) }}</div>
            </div>
          </div>
          <p class="text-xs text-gray-500">{{ formatDateTime(m.created_at) }} · {{ m.created_by_name || '—' }}</p>
          <p class="text-xs text-gray-400">{{ refText(m) }}</p>
        </article>
      </div>

      <div class="hidden lg:block bg-white rounded-2xl shadow-xs border border-gray-100 overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-3 font-semibold">{{ t('labStock.mv_col_date') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_product') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.mv_col_type') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.mv_col_change') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.mv_col_after') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.mv_col_by') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.mv_col_ref') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="m in rows" :key="m.id" class="hover:bg-gray-50">
              <td class="px-6 py-3 text-sm text-gray-600 whitespace-nowrap">{{ formatDateTime(m.created_at) }}</td>
              <td class="px-6 py-3 font-medium text-gray-900">{{ m.product_name || '?' }}</td>
              <td class="px-6 py-3"><span class="text-xs font-semibold px-2 py-0.5 rounded-full" :class="typeClass(m.movement_type)">{{ typeLabel(m.movement_type) }}</span></td>
              <td class="px-6 py-3 text-right font-bold" :class="changeClass(m.change_qty)">{{ signed(m.change_qty) }}</td>
              <td class="px-6 py-3 text-right text-gray-900">{{ Number(m.quantity_after) }}</td>
              <td class="px-6 py-3 text-sm text-gray-600">{{ m.created_by_name || '—' }}</td>
              <td class="px-6 py-3 text-sm text-gray-500">{{ refText(m) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="rows.length >= LIMIT" class="text-xs text-gray-500 text-center">{{ t('labStock.mv_limit_note', { n: LIMIT }) }}</p>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';

const LIMIT = 200;
const TYPES = ['reception', 'comptage', 'annulation_reception'];
const { t } = useI18n();
const products = ref([]);
const rows = ref([]);
const productId = ref('');
const isLoading = ref(false);
const pageError = ref('');

const typeLabel = (ty) => (TYPES.includes(ty) ? t(`labStock.mv_type.${ty}`) : String(ty || '?'));
const typeClass = (ty) => ({
  reception: 'bg-green-100 text-green-700',
  comptage: 'bg-blue-100 text-blue-700',
  annulation_reception: 'bg-red-100 text-red-700',
}[ty] || 'bg-gray-100 text-gray-700');
const signed = (v) => { const n = Number(v ?? 0); return n > 0 ? `+${n}` : String(n); };
const changeClass = (v) => (Number(v) > 0 ? 'text-green-700' : Number(v) < 0 ? 'text-red-700' : 'text-gray-500');
const formatDateTime = (v) => {
  if (!v) return '';
  const s = String(v);
  // horodatages serveur en UTC naif : on les lit comme UTC
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString();
};
const refText = (m) => {
  if (m.ref_type === 'receipt' && m.ref_id) return t('labStock.mv_ref_receipt', { id: m.ref_id });
  if (m.ref_type === 'count' && m.ref_id) return t('labStock.mv_ref_count', { id: m.ref_id });
  return m.ref_type ? `${m.ref_type} ${m.ref_id ?? ''}` : '—';
};

async function load() {
  isLoading.value = true;
  pageError.value = '';
  try {
    rows.value = await LabStockGateway.listMovements({ productId: productId.value ? Number(productId.value) : undefined, limit: LIMIT });
  } catch (e) {
    rows.value = [];
    pageError.value = describeLabStockError(e, t('stockOps.error_load'));
  } finally {
    isLoading.value = false;
  }
}

onMounted(async () => {
  try {
    products.value = await LabStockGateway.listProducts({ includeInactive: true });
  } catch { products.value = []; }
  await load();
});
</script>
