<!-- src/views/modules/labstock/LabStockMovements.vue -->
<!-- Historique des mouvements du stock labo. Tableau responsive (cartes empilees sous lg).
     Filtre produit. Acces : READERS. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('labStock.mv_title')" :subtitle="`${t('labStock.mv_subtitle')} (${t('labStockScreens.movements_count', { n: rows.length })})`" />

    <section :aria-label="t('labStockScreens.product_filter')" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
      <div class="max-w-sm">
        <FormField id="lab-mv-product" :label="t('labStockScreens.product_filter')" v-slot="{ describedBy }">
          <select id="lab-mv-product" v-model="productId" @change="load" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ t('labStock.mv_all_products') }}</option>
            <option v-for="p in products" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>

    <ResponsiveTable
      :columns="columns"
      :rows="rows"
      row-key="id"
      :loading="isLoading"
      :empty-title="t('labStock.mv_empty')"
      :empty-message="' '"
      striped
    >
      <template #cell-date="{ row: m }"><span class="whitespace-nowrap">{{ formatDateTime(m.created_at) }}</span></template>
      <template #cell-product="{ row: m }"><span class="font-medium">{{ m.product_name || '?' }}</span></template>
      <template #cell-type="{ row: m }"><StatusBadge :tone="typeTone(m.movement_type)" :label="typeLabel(m.movement_type)" /></template>
      <template #cell-change="{ row: m }"><span class="font-bold" :class="changeClass(m.change_qty)">{{ signed(m.change_qty) }}</span></template>
      <template #cell-after="{ row: m }">{{ Number(m.quantity_after) }}</template>
      <template #cell-by="{ row: m }">{{ m.created_by_name || '-' }}</template>
      <template #cell-ref="{ row: m }">{{ refText(m) }}</template>
    </ResponsiveTable>
    <p v-if="rows.length >= LIMIT" class="text-center text-base text-ink-muted">{{ t('labStock.mv_limit_note', { n: LIMIT }) }}</p>
  </div>
</template>

<script setup>
import { formatDateTimeDMY } from '@/utils/localDate';
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { PageHeader, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const LIMIT = 200;
const TYPES = ['reception', 'comptage', 'annulation_reception'];
const { t } = useI18n();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'date', label: t('labStock.mv_col_date') },
  { key: 'product', label: t('labStock.col_product') },
  { key: 'type', label: t('labStock.mv_col_type') },
  { key: 'change', label: t('labStock.mv_col_change'), align: 'right' },
  { key: 'after', label: t('labStock.mv_col_after'), align: 'right' },
  { key: 'by', label: t('labStock.mv_col_by') },
  { key: 'ref', label: t('labStock.mv_col_ref') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const products = ref([]);
const rows = ref([]);
const productId = ref('');
const isLoading = ref(false);
const pageError = ref('');

const typeLabel = (ty) => (TYPES.includes(ty) ? t(`labStock.mv_type.${ty}`) : String(ty || '?'));
const typeTone = (ty) => ({
  reception: 'success',
  comptage: 'info',
  annulation_reception: 'danger',
}[ty] || 'neutral');
const signed = (v) => { const n = Number(v ?? 0); return n > 0 ? `+${n}` : String(n); };
const changeClass = (v) => (Number(v) > 0 ? 'text-tone-success-text' : Number(v) < 0 ? 'text-tone-danger-text' : 'text-ink-muted');
const formatDateTime = (v) => {
  if (!v) return '';
  const s = String(v);
  // horodatages serveur en UTC naif : on les lit comme UTC
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`);
  return Number.isNaN(d.getTime()) ? s : formatDateTimeDMY(d);
};
const refText = (m) => {
  if (m.ref_type === 'receipt' && m.ref_id) return t('labStock.mv_ref_receipt', { id: m.ref_id });
  if (m.ref_type === 'count' && m.ref_id) return t('labStock.mv_ref_count', { id: m.ref_id });
  return m.ref_type ? `${m.ref_type} ${m.ref_id ?? ''}` : '-';
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
