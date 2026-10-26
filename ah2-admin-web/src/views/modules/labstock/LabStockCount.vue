<!-- src/views/modules/labstock/LabStockCount.vue -->
<!-- Comptage hebdomadaire. Un seul tableau responsive (cartes empilees sous lg). Acces :
     laborantin, admin. Les produits en conflit gardent leur saisie pour recomptage ; les
     autres sont vides apres l'envoi. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('labStock.count_title')" :subtitle="`${t('labStock.count_subtitle')} (${t('labStock.count_last', { date: lastCountText })})`" />

    <p v-if="reminderDue" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('warning')">
      {{ daysSince == null ? t('labStock.count_reminder_never') : t('labStock.count_reminder', { days: daysSince }) }}
    </p>
    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <section v-if="conflicts.length" role="alert" class="grid gap-2 rounded-card border p-4 text-base" :class="toneClasses('warning')">
      <h2 class="font-semibold">{{ t('labStock.count_conflicts_title') }}</h2>
      <ul class="list-disc space-y-1 pl-5">
        <li v-for="c in conflicts" :key="c.product_id">{{ t('labStock.count_conflict_line', { name: c.name, expected: c.expected, actual: c.actual }) }}</li>
      </ul>
    </section>

    <section :aria-label="t('labStockScreens.search_label')" class="grid gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card sm:grid-cols-[minmax(0,20rem)_1fr] sm:items-end">
      <FormField id="lab-count-search" :label="t('labStockScreens.search_label')" v-slot="{ describedBy }">
        <input id="lab-count-search" v-model="search" type="text" :placeholder="t('common.search_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <p class="text-base text-ink-muted sm:text-right">{{ t('labStock.count_filled', { n: filledCount, total: products.length }) }}</p>
    </section>

    <ResponsiveTable
      :columns="columns"
      :rows="filtered"
      row-key="id"
      :loading="isLoading"
      :empty-title="t('labStock.no_products')"
      :empty-message="' '"
      role="region"
      :aria-label="t('labStockScreens.count_table')"
      striped
    >
      <template #cell-name="{ row: p }">
        <span class="font-medium">{{ p.name }}</span>
        <span v-if="isConflict(p.id)" class="mt-1 block"><StatusBadge tone="warning" :label="t('labStockScreens.count_conflict_badge')" /></span>
      </template>
      <template #cell-packaging="{ row: p }">{{ p.packaging || '-' }}</template>
      <template #cell-stock="{ row: p }"><span class="font-semibold">{{ num(p.quantity) }}</span></template>
      <template #cell-last="{ row: p }">{{ formatDate(p.last_counted_at) || t('labStock.never') }}</template>
      <template #cell-counted="{ row: p }">
        <input v-model="entered[p.id]" type="number" inputmode="numeric" pattern="[0-9]*" min="0" step="1"
               :aria-label="t('labStockScreens.count_input_label', { name: p.name })"
               :aria-invalid="invalid(p.id) ? 'true' : undefined"
               :aria-describedby="invalid(p.id) ? 'lab-count-invalid' : undefined"
               :class="[fieldClass, 'text-right lg:w-28', invalid(p.id) ? 'border-tone-danger-border bg-tone-danger-bg' : '']" />
      </template>
    </ResponsiveTable>

    <ActionBar>
      <template #secondary>
        <p v-if="hasInvalid" id="lab-count-invalid" role="alert" class="text-base text-tone-danger-text">{{ t('labStock.count_err_invalid') }}</p>
      </template>
      <AppButton @click="submit" :disabled="busy || !filledCount || hasInvalid" :loading="busy">
        {{ busy ? t('labStock.submitting') : t('labStock.submit_count') }}
      </AppButton>
    </ActionBar>
  </div>
</template>

<script setup>
import { formatDateDMY } from '@/utils/localDate';
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { buildCountPayload, describeConflicts, isValidCount } from '@/utils/labCount';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'name', label: t('labStock.col_product') },
  { key: 'packaging', label: t('labStock.col_packaging') },
  { key: 'stock', label: t('labStock.last_stock'), align: 'right' },
  { key: 'last', label: t('labStock.col_last_count') },
  { key: 'counted', label: t('labStock.counted_qty'), align: 'right' },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const products = ref([]);
const entered = reactive({});
const status = ref(null);
const conflicts = ref([]);
const search = ref('');
const isLoading = ref(false);
const busy = ref(false);
const pageError = ref('');
const pageMessage = ref('');

const num = (v) => Number(v ?? 0);
const formatDate = (v) => (v ? formatDateDMY(new Date(v)) : '');
const blank = (v) => v === undefined || v === null || String(v).trim() === '';
const invalid = (id) => !blank(entered[id]) && !isValidCount(entered[id]);
const isConflict = (id) => conflicts.value.some((c) => c.product_id === id);

const st = computed(() => status.value?.count_status ?? status.value ?? {});
const reminderDue = computed(() => !!st.value.reminder_due);
const daysSince = computed(() => st.value.days_since ?? null);
const lastCountText = computed(() => formatDate(st.value.last_counted_at) || t('labStock.never'));

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return products.value;
  return products.value.filter((p) => [p.name, p.packaging].some((v) => (v || '').toLowerCase().includes(q)));
});
const filledCount = computed(() => products.value.filter((p) => !blank(entered[p.id])).length);
const hasInvalid = computed(() => products.value.some((p) => invalid(p.id)));

let msgTimer = null;
const flash = (msg) => {
  pageMessage.value = msg;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { pageMessage.value = ''; }, 6000);
};
onBeforeUnmount(() => clearTimeout(msgTimer));

const loadProducts = async () => {
  products.value = await LabStockGateway.listProducts();
};
const loadStatus = async () => {
  try { status.value = await LabStockGateway.countStatus(); } catch (err) { console.error('Statut de comptage indisponible :', err); }
};
const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    await loadProducts();
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement des produits du labo echoue :', err);
  } finally {
    isLoading.value = false;
  }
  loadStatus();
};

// Ne garde que la saisie des produits en conflit (a recompter).
const keepOnly = (ids) => {
  for (const k of Object.keys(entered)) if (!ids.has(Number(k))) delete entered[k];
};

const submit = async () => {
  if (busy.value || hasInvalid.value) return;
  const lines = buildCountPayload(products.value, entered);
  if (!lines.length) return;
  busy.value = true;
  pageError.value = '';
  conflicts.value = [];
  try {
    const resp = await LabStockGateway.submitCount(lines);
    conflicts.value = describeConflicts(resp);
    keepOnly(new Set(conflicts.value.map((c) => c.product_id)));
    flash(t('labStock.count_saved', { n: (resp?.applied || []).length }));
  } catch (err) {
    const c = err?.response?.status === 409 ? describeConflicts(err) : [];
    if (c.length) {
      conflicts.value = c;
      keepOnly(new Set(c.map((x) => x.product_id)));
    } else {
      pageError.value = describeLabStockError(err, t('stockOps.error_save'));
    }
    console.error('Envoi du comptage echoue :', err);
  } finally {
    busy.value = false;
  }
  try { await loadProducts(); } catch (err) { console.error('Rechargement des produits echoue :', err); }
  loadStatus();
};

onMounted(load);
</script>
