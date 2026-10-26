<!-- src/views/modules/stock/StockMovements.vue -->
<!-- Historique (lecture seule) des mouvements de stock. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="$t('stockControl.movements_title')" :subtitle="$t('stockAdminScreens.movements_count', { n: total })" />

    <form @submit.prevent="applyFilters" :aria-label="$t('stockAdminScreens.filters_label')"
          class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:grid-cols-5 lg:items-end">
      <div class="grid gap-3 md:col-span-2">
        <FormField id="mov-search" :label="$t('stockControl.product_search')" v-slot="{ describedBy }">
          <input id="mov-search" v-model="productSearch" type="search" autocomplete="off" :placeholder="$t('stockControl.product_search')" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="mov-product" :label="$t('stockOps.col_product')" v-slot="{ describedBy }">
          <select id="mov-product" v-model="filters.productId" :aria-describedby="describedBy" :class="fieldClass">
            <option :value="null">{{ $t('stockControl.all_products') }}</option>
            <option v-for="p in visibleProducts" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </FormField>
      </div>
      <FormField id="mov-type" :label="$t('stockControl.movement_type')" v-slot="{ describedBy }">
        <select id="mov-type" v-model="filters.movementType" :aria-describedby="describedBy" :class="fieldClass">
          <option value="">{{ $t('stockControl.all_types') }}</option>
          <option v-for="mt in MOVEMENT_TYPES" :key="mt" :value="mt">{{ $t(`stockControl.movement.${mt}`) }}</option>
        </select>
      </FormField>
      <FormField id="mov-from" :label="$t('stockControl.date_from')" v-slot="{ describedBy }">
        <input id="mov-from" v-model="filters.dateFrom" type="date" :max="today" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="mov-to" :label="$t('stockControl.date_to')" v-slot="{ describedBy }">
        <input id="mov-to" v-model="filters.dateTo" type="date" :max="today" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <div class="flex flex-col gap-2 md:col-span-2 md:flex-row md:justify-end lg:col-span-5">
        <AppButton variant="secondary" @click="resetFilters">{{ $t('stockControl.reset') }}</AppButton>
        <AppButton type="submit">{{ $t('stockControl.apply') }}</AppButton>
      </div>
    </form>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>

    <section class="grid gap-3">
      <ResponsiveTable
        :columns="columns"
        :rows="items"
        row-key="movement_id"
        :loading="isLoading"
        :empty-title="$t('stockControl.no_movements')"
        :empty-message="' '"
        striped
      >
        <template #cell-date="{ row: m }"><span class="whitespace-nowrap">{{ formatDateTime(m.created_at) }}</span></template>
        <template #cell-product="{ row: m }">{{ m.product_name || ('#' + m.product_id) }}</template>
        <template #cell-type="{ row: m }">{{ movementLabel(m.movement_type) }}</template>
        <template #cell-quantity="{ row: m }">
          <span class="font-mono font-semibold"
                :class="m.change_qty > 0 ? 'text-tone-success-text' : (m.change_qty < 0 ? 'text-tone-danger-text' : 'text-ink-muted')">
            {{ m.change_qty > 0 ? '+' : '' }}{{ m.change_qty }}
          </span>
        </template>
        <template #cell-note="{ row: m }"><span class="block max-w-xs">{{ m.note }}</span></template>
        <template #cell-author="{ row: m }">{{ m.created_by_name || m.created_by || '' }}</template>
      </ResponsiveTable>

      <div v-if="totalPages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">{{ $t('stockControl.page_of', { page, total: totalPages }) }} ({{ total }})</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="$t('stockAdminScreens.prev_page')" @click="goTo(page - 1)" :disabled="page <= 1" />
          <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="$t('stockAdminScreens.next_page')" @click="goTo(page + 1)" :disabled="page >= totalPages" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { formatDateTimeDMY, todayLocalISO } from '@/utils/localDate';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';
import { AppButton, PageHeader, FormField, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t, te } = useI18n();
const MOVEMENT_TYPES = ['VENTE', 'ANNULATION_VENTE', 'initial', 'update', 'renew', 'reception',
  'avarie_endommage', 'avarie_perdu', 'avarie_defectueux'];
const PER_PAGE = 50;

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'date', label: t('stockOps.col_date') },
  { key: 'product', label: t('stockOps.col_product') },
  { key: 'type', label: t('stockControl.movement_type') },
  { key: 'quantity', label: t('stockOps.col_quantity'), align: 'right' },
  { key: 'note', label: t('stockControl.note') },
  { key: 'author', label: t('stockControl.author') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
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
const formatDateTime = (v) => (v ? formatDateTimeDMY(new Date(v)) : '');

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
