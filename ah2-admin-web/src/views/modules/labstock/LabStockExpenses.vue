<!-- src/views/modules/labstock/LabStockExpenses.vue -->
<!-- Depenses du stock labo : total de la periode, par mois, par fournisseur, historique de
     prix d'un produit. Acces : SPENDERS (promoteur, ToxicoManager, admin). -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('labStock.ex_title')" :subtitle="t('labStock.ex_subtitle')" />

    <form @submit.prevent="load" :aria-label="t('labStockScreens.expenses_period_label')"
          class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-3 md:items-end">
      <FormField id="lab-ex-from" :label="t('labStock.ex_from')" v-slot="{ describedBy }">
        <input id="lab-ex-from" v-model="from" type="date" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="lab-ex-to" :label="t('labStock.ex_to')" v-slot="{ describedBy }">
        <input id="lab-ex-to" v-model="to" type="date" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <AppButton type="submit" :disabled="isLoading" :loading="isLoading">{{ t('labStock.ex_apply') }}</AppButton>
    </form>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="isLoading && !data" role="status" class="p-10 text-center text-base text-ink-muted">{{ t('stockOps.loading') }}</p>

    <template v-if="data">
      <StatTile :title="t('labStock.ex_total')" :value="formatMoney(data.total)" :note="t('labStock.ex_period', { from: formatDate(data.from), to: formatDate(data.to) })" />

      <div class="grid items-start gap-6 md:grid-cols-2 lg:grid-cols-3">
        <section aria-labelledby="lab-ex-months" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card lg:col-span-2">
          <h2 id="lab-ex-months" class="mb-3 text-lg font-semibold text-ink">{{ t('labStock.ex_by_month') }}</h2>
          <p v-if="!bars.some((b) => !b.empty)" class="py-4 text-center text-base text-ink-muted">{{ t('labStock.ex_empty') }}</p>
          <ul v-else class="grid gap-3">
            <li v-for="b in bars" :key="b.month" class="grid grid-cols-[6rem_1fr] items-center gap-x-3 gap-y-1 md:grid-cols-[7rem_1fr_9rem]">
              <span class="text-base capitalize text-ink">{{ monthLabel(b.month, locale) }}</span>
              <div class="h-4 overflow-hidden rounded-full bg-tone-neutral-bg" aria-hidden="true">
                <div class="h-full rounded-full bg-brand-600" :style="{ width: b.pct + '%' }"></div>
              </div>
              <span class="col-start-2 text-base md:col-start-auto md:text-right" :class="b.empty ? 'text-ink-muted' : 'font-medium text-ink'">{{ formatMoney(b.total) }}</span>
            </li>
          </ul>
        </section>

        <section aria-labelledby="lab-ex-suppliers" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
          <h2 id="lab-ex-suppliers" class="mb-3 text-lg font-semibold text-ink">{{ t('labStock.ex_by_supplier') }}</h2>
          <p v-if="!data.by_supplier.length" class="py-4 text-center text-base text-ink-muted">{{ t('labStock.ex_empty') }}</p>
          <ul v-else class="divide-y divide-tone-neutral-border">
            <li v-for="s in data.by_supplier" :key="s.supplier" class="flex justify-between gap-3 py-2">
              <span class="min-w-0 break-words text-base text-ink">{{ s.supplier }}</span>
              <span class="shrink-0 text-base font-semibold text-ink">{{ formatMoney(s.total) }}</span>
            </li>
          </ul>
        </section>
      </div>
    </template>

    <section aria-labelledby="lab-ex-prices" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
      <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <h2 id="lab-ex-prices" class="text-lg font-semibold text-ink">{{ t('labStock.ex_price_title') }}</h2>
        <div class="w-full md:w-80">
          <FormField id="lab-ex-product" :label="t('labStockScreens.product_filter')" v-slot="{ describedBy }">
            <select id="lab-ex-product" v-model="productId" @change="loadPrices" :aria-describedby="describedBy" :class="fieldClass">
              <option value="">{{ t('labStock.ex_price_choose') }}</option>
              <option v-for="p in products" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
            </select>
          </FormField>
        </div>
      </div>
      <p v-if="priceError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ priceError }}</p>
      <template v-if="productId && !priceLoading && !priceError">
        <p v-if="!prices.length" class="py-4 text-center text-base text-ink-muted">{{ t('labStock.ex_price_empty') }}</p>
        <template v-else>
          <p class="text-base text-ink-muted">{{ t('labStockScreens.prices_count', { n: prices.length }) }}</p>
          <ResponsiveTable :columns="priceColumns" :rows="priceRows" row-key="key" striped>
            <template #cell-date="{ row: h }">{{ formatDate(h.delivery_date) }}</template>
            <template #cell-supplier="{ row: h }">{{ h.supplier }}</template>
            <template #cell-receipt="{ row: h }">{{ t('labStock.mv_ref_receipt', { id: h.receipt_id }) }}</template>
            <template #cell-qty="{ row: h }">{{ Number(h.received_qty) }}</template>
            <template #cell-price="{ row: h }"><span class="font-bold">{{ formatMoney(h.unit_price) }}</span></template>
          </ResponsiveTable>
        </template>
      </template>
    </section>
  </div>
</template>

<script setup>
import { formatDateDMY } from '@/utils/localDate';
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { AppButton, PageHeader, FormField, StatTile, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';
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

// Colonnes de l'historique de prix (cartes empilees sous lg) et style commun des champs.
const priceColumns = computed(() => [
  { key: 'date', label: t('labStock.ex_col_date') },
  { key: 'supplier', label: t('labStock.ex_col_supplier') },
  { key: 'receipt', label: t('labStock.ex_col_receipt') },
  { key: 'qty', label: t('labStock.ex_col_qty'), align: 'right' },
  { key: 'price', label: t('labStock.ex_col_price'), align: 'right' },
]);
const priceRows = computed(() => prices.value.map((h, i) => ({ ...h, key: i })));
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const bars = computed(() => (data.value ? buildMonthBars(data.value.by_month, data.value.from, data.value.to) : []));
const formatDate = (v) => {
  if (!v) return '?';
  const [y, m, d] = String(v).slice(0, 10).split('-').map(Number);
  return formatDateDMY(new Date(y, m - 1, d));
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
