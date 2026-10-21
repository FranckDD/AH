<!-- src/views/modules/stock/StockMovements.vue -->
<!-- Historique (lecture seule) des mouvements de stock. -->
<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6">
    <h2 class="text-xl font-bold text-gray-800">{{ $t('stockControl.movements_title') }}</h2>

    <form @submit.prevent="applyFilters" class="bg-white rounded-xl shadow-xs border border-gray-200 p-4 grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
      <label class="block text-sm md:col-span-2">{{ $t('stockOps.col_product') }}
        <input v-model="productSearch" type="text" :placeholder="$t('stockControl.product_search')"
               class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
        <select v-model="filters.productId" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option :value="null">{{ $t('stockControl.all_products') }}</option>
          <option v-for="p in visibleProducts" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </label>
      <label class="block text-sm">{{ $t('stockControl.movement_type') }}
        <select v-model="filters.movementType" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="">{{ $t('stockControl.all_types') }}</option>
          <option v-for="mt in MOVEMENT_TYPES" :key="mt" :value="mt">{{ $t(`stockControl.movement.${mt}`) }}</option>
        </select>
      </label>
      <label class="block text-sm">{{ $t('stockControl.date_from') }}
        <input v-model="filters.dateFrom" type="date" :max="today" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
      </label>
      <label class="block text-sm">{{ $t('stockControl.date_to') }}
        <input v-model="filters.dateTo" type="date" :max="today" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
      </label>
      <div class="md:col-span-5 flex justify-end gap-2">
        <button type="button" @click="resetFilters" class="px-4 py-2 bg-gray-200 rounded-lg text-sm">{{ $t('stockControl.reset') }}</button>
        <button type="submit" class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium">{{ $t('stockControl.apply') }}</button>
      </div>
    </form>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>

    <section class="bg-white rounded-xl shadow-xs border border-gray-200 p-5 overflow-x-auto">
      <div v-if="isLoading" class="text-sm text-gray-400">{{ $t('stockOps.loading') }}</div>
      <div v-else-if="items.length === 0" class="text-sm text-gray-400">{{ $t('stockControl.no_movements') }}</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 uppercase border-b">
            <th class="py-2">{{ $t('stockOps.col_date') }}</th>
            <th class="py-2">{{ $t('stockOps.col_product') }}</th>
            <th class="py-2">{{ $t('stockControl.movement_type') }}</th>
            <th class="py-2 text-right">{{ $t('stockOps.col_quantity') }}</th>
            <th class="py-2">{{ $t('stockControl.note') }}</th>
            <th class="py-2">{{ $t('stockControl.author') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in items" :key="m.movement_id" class="border-b last:border-0 align-top">
            <td class="py-2 whitespace-nowrap">{{ formatDateTime(m.created_at) }}</td>
            <td class="py-2">{{ m.product_name || ('#' + m.product_id) }}</td>
            <td class="py-2">{{ movementLabel(m.movement_type) }}</td>
            <td class="py-2 text-right font-mono font-semibold"
                :class="m.change_qty > 0 ? 'text-green-700' : (m.change_qty < 0 ? 'text-red-700' : 'text-gray-600')">
              {{ m.change_qty > 0 ? '+' : '' }}{{ m.change_qty }}
            </td>
            <td class="py-2 max-w-xs">{{ m.note }}</td>
            <td class="py-2">{{ m.created_by || '' }}</td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalPages > 1" class="flex items-center justify-between pt-4 text-sm">
        <span class="text-gray-600">{{ $t('stockControl.page_of', { page, total: totalPages }) }} · {{ total }}</span>
        <div class="flex gap-2">
          <button type="button" @click="goTo(page - 1)" :disabled="page <= 1" class="px-3 py-1 border rounded-sm disabled:opacity-50">‹</button>
          <button type="button" @click="goTo(page + 1)" :disabled="page >= totalPages" class="px-3 py-1 border rounded-sm disabled:opacity-50">›</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { todayLocalISO } from '@/utils/localDate';

const { t, te } = useI18n();
const MOVEMENT_TYPES = ['VENTE', 'ANNULATION_VENTE', 'initial', 'update', 'renew', 'reception',
  'avarie_endommage', 'avarie_perdu', 'avarie_defectueux'];
const PER_PAGE = 50;
const today = todayLocalISO();

const products = ref([]);
const productSearch = ref('');
const filters = reactive({ productId: null, movementType: '', dateFrom: '', dateTo: '' });
const items = ref([]);
const total = ref(0);
const page = ref(1);
const isLoading = ref(false);
const pageError = ref('');

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PER_PAGE)));
const visibleProducts = computed(() => {
  const q = productSearch.value.trim().toLowerCase();
  if (!q) return products.value;
  return products.value.filter((p) => String(p.name).toLowerCase().includes(q) || String(p.id) === q);
});

const movementLabel = (mt) => (te(`stockControl.movement.${mt}`) ? t(`stockControl.movement.${mt}`) : mt);
const formatDateTime = (v) => (v ? new Date(v).toLocaleString() : '');

const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    const data = await StockOpsGateway.listMovements({
      productId: filters.productId, movementType: filters.movementType,
      dateFrom: filters.dateFrom, dateTo: filters.dateTo, page: page.value, perPage: PER_PAGE,
    });
    items.value = data?.items || [];
    total.value = data?.total || 0;
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_load'));
    console.error('Chargement des mouvements echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const applyFilters = () => {
  // Si le texte ne correspond qu'a un produit, on le selectionne directement.
  if (!filters.productId && productSearch.value.trim() && visibleProducts.value.length === 1) {
    filters.productId = visibleProducts.value[0].id;
  }
  page.value = 1;
  load();
};
const resetFilters = () => {
  Object.assign(filters, { productId: null, movementType: '', dateFrom: '', dateTo: '' });
  productSearch.value = '';
  page.value = 1;
  load();
};
const goTo = (p) => { page.value = p; load(); };

onMounted(async () => {
  load();
  try {
    products.value = await StockOpsGateway.listStockProducts();
  } catch (err) {
    // Liste de filtre seulement : un echec n'empeche pas la consultation.
    if (!pageError.value) pageError.value = describeStockError(err, t('stockOps.error_products'));
    console.error('Chargement des produits echoue :', err);
  }
});
</script>
