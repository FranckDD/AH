<!-- src/views/modules/stock/StockReceipts.vue -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="$t('stockOps.receipts.title')" :subtitle="$t('stockAdminScreens.receipts_count', { n: receipts.length })">
      <template #actions>
        <AppButton :icon="PlusCircleIcon" @click="openForm">{{ $t('stockOps.receipts.new') }}</AppButton>
      </template>
    </PageHeader>

    <section :aria-label="$t('stockAdminScreens.status_filter')" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
      <div class="max-w-xs">
        <FormField id="receipts-status" :label="$t('stockAdminScreens.status_filter')" v-slot="{ describedBy }">
          <select id="receipts-status" v-model="statusFilter" @change="loadReceipts" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ $t('stockOps.all_statuses') }}</option>
            <option v-for="s in CHECK_STATUSES" :key="s" :value="s">{{ $t(`stockOps.check_status.${s}`) }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <ResponsiveTable
      :columns="columns"
      :rows="receipts"
      row-key="id"
      :loading="isLoading"
      :empty-title="$t('stockOps.receipts.empty')"
      :empty-message="' '"
      striped
    >
      <template #cell-number="{ row: r }"><span class="font-mono">{{ r.receipt_number }}</span></template>
      <template #cell-origin="{ row: r }">{{ $t(`stockOps.origin.${r.origin}`) }}</template>
      <template #cell-source="{ row: r }">{{ r.origin === 'fournisseur' ? (r.supplier || '-') : lotLabel(r.production_lot_id) }}</template>
      <template #cell-date="{ row: r }">{{ r.received_date }}</template>
      <template #cell-status="{ row: r }">
        <StatusBadge :tone="badge(r.status)" :label="$t(`stockOps.check_status.${r.status}`)" />
        <p v-if="r.status === 'rejete' && r.reject_reason" class="mt-1 text-base text-tone-danger-text">
          {{ $t('stockOps.reject_reason') }} : {{ r.reject_reason }}
        </p>
      </template>
      <template #actions="{ row: r }">
        <AppButton variant="secondary" @click="openDetail(r)">{{ $t('stockOps.detail') }}</AppButton>
        <AppButton v-if="r.status === 'a_controler'" variant="danger" @click="cancelReceipt(r)" :disabled="busyId === r.id" :loading="busyId === r.id">{{ $t('stockOps.cancel') }}</AppButton>
      </template>
    </ResponsiveTable>

    <!-- Detail -->
    <FullScreenPanel v-if="detail" :title="`${$t('stockOps.receipts.detail_title')} ${detail.receipt_number}`" wide @close="detail = null">
      <div class="grid gap-4">
        <p v-if="detailError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ detailError }}</p>
        <p class="text-base text-ink">
          {{ $t(`stockOps.origin.${detail.origin}`) }} - {{ detail.received_date }}
          <span v-if="detail.supplier"> - {{ detail.supplier }}</span>
          <span v-if="detail.delivery_ref"> - {{ detail.delivery_ref }}</span>
        </p>
        <p><StatusBadge :tone="badge(detail.status)" :label="$t(`stockOps.check_status.${detail.status}`)" /></p>
        <p v-if="detail.status === 'rejete' && detail.reject_reason" class="text-base text-tone-danger-text">
          {{ $t('stockOps.reject_reason') }} : {{ detail.reject_reason }}
        </p>
        <ResponsiveTable :columns="detailColumns" :rows="detail.lines || []" row-key="id" :empty-title="$t('stockOps.receipts.empty')" :empty-message="' '" striped>
          <template #cell-product="{ row: l }">{{ l.product_name }}</template>
          <template #cell-expected="{ row: l }">{{ l.qty_expected ?? '-' }}</template>
          <template #cell-good="{ row: l }">{{ l.qty_good }}</template>
          <template #cell-damaged="{ row: l }">{{ l.qty_damaged }}</template>
          <template #cell-lost="{ row: l }">{{ l.qty_lost }}</template>
          <template #cell-defective="{ row: l }">{{ l.qty_defective }}</template>
          <template #cell-lot="{ row: l }">{{ l.lot_number || '-' }}</template>
          <template #cell-expiry="{ row: l }">{{ l.expiry_date || '-' }}</template>
        </ResponsiveTable>
      </div>
      <template #footer>
        <ActionBar>
          <AppButton variant="secondary" @click="detail = null">{{ $t('stockOps.close') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Formulaire de creation -->
    <FullScreenPanel v-if="showForm" :title="$t('stockOps.receipts.new')" wide @close="showForm = false">
      <form id="receipt-form" @submit.prevent="submitReceipt" class="grid gap-4">
        <p v-if="formError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ formError }}</p>

        <fieldset class="grid gap-1.5">
          <legend class="text-base font-medium text-ink">{{ $t('stockAdminScreens.origin_group') }}</legend>
          <div class="grid gap-2 sm:grid-cols-2">
            <label class="flex min-h-11 items-center gap-3 rounded-control border border-tone-neutral-border px-3 text-base text-ink">
              <input type="radio" value="fabrication" v-model="form.origin" @change="onOriginChange" class="h-5 w-5 accent-brand-600" />
              {{ $t('stockOps.origin.fabrication') }}
            </label>
            <label class="flex min-h-11 items-center gap-3 rounded-control border border-tone-neutral-border px-3 text-base text-ink">
              <input type="radio" value="fournisseur" v-model="form.origin" @change="onOriginChange" class="h-5 w-5 accent-brand-600" />
              {{ $t('stockOps.origin.fournisseur') }}
            </label>
          </div>
        </fieldset>

        <FormField id="receipt-date" :label="$t('stockOps.col_received_date')" v-slot="{ describedBy }">
          <input id="receipt-date" v-model="form.received_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>

        <div v-if="form.origin === 'fabrication'">
          <FormField id="receipt-lot" :label="$t('stockOps.receipts.choose_lot')" v-slot="{ describedBy }">
            <select id="receipt-lot" v-model.number="form.production_lot_id" @change="onLotChange" :aria-describedby="describedBy" :class="fieldClass">
              <option :value="null" disabled>{{ $t('stockOps.receipts.choose_lot') }}</option>
              <option v-for="lot in deliveredLots" :key="lot.id" :value="lot.id">
                {{ lot.lot_number }} - {{ lot.product_name }} ({{ lot.quantity_produced }})
              </option>
            </select>
          </FormField>
          <p v-if="deliveredLots.length === 0" class="mt-1 text-base text-ink-muted">{{ $t('stockOps.receipts.no_delivered_lot') }}</p>
        </div>

        <div v-else class="grid gap-4 sm:grid-cols-2">
          <FormField id="receipt-supplier" :label="$t('stockOps.col_supplier')" v-slot="{ describedBy }">
            <input id="receipt-supplier" v-model="form.supplier" type="text" maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="receipt-delivery" :label="$t('stockOps.col_delivery_ref')" v-slot="{ describedBy }">
            <input id="receipt-delivery" v-model="form.delivery_ref" type="text" maxlength="100" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>

        <h3 class="text-lg font-semibold text-ink">{{ $t('stockAdminScreens.lines_title') }}</h3>
        <div class="grid gap-3">
          <div v-for="(line, i) in form.lines" :key="i" class="grid gap-3 rounded-card border border-tone-neutral-border p-3">
            <div class="flex items-center justify-between gap-2">
              <span class="text-base font-semibold text-ink">{{ $t('stockAdminScreens.line_number', { n: i + 1 }) }}</span>
              <AppButton v-if="form.origin === 'fournisseur' && form.lines.length > 1" variant="ghost" :icon="TrashIcon" @click="form.lines.splice(i, 1)">{{ $t('stockOps.remove_line') }}</AppButton>
            </div>

            <div class="grid gap-3 sm:grid-cols-3">
              <div class="sm:col-span-2">
                <FormField v-if="form.origin === 'fournisseur'" :id="`receipt-line-${i}-product`" :label="$t('stockOps.col_product')" v-slot="{ describedBy }">
                  <select :id="`receipt-line-${i}-product`" v-model.number="line.product_id" :aria-describedby="describedBy" :class="fieldClass">
                    <option :value="null" disabled>{{ $t('stockOps.choose_product') }}</option>
                    <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>
                </FormField>
                <div v-else class="grid gap-1.5">
                  <span class="text-base font-medium text-ink">{{ $t('stockOps.col_product') }}</span>
                  <span class="flex min-h-11 items-center text-base text-ink lg:min-h-10">{{ line.product_name }}</span>
                </div>
              </div>
              <FormField :id="`receipt-line-${i}-expected`" :label="$t('stockOps.col_expected')" v-slot="{ describedBy }">
                <input :id="`receipt-line-${i}-expected`" v-model.number="line.qty_expected" :disabled="form.origin === 'fabrication'" type="number" min="0" step="1" inputmode="numeric"
                       :aria-describedby="describedBy" :class="[fieldClass, 'text-right disabled:bg-tone-neutral-bg']" />
              </FormField>
            </div>

            <div class="grid grid-cols-2 gap-3 sm:grid-cols-5" role="group" :aria-label="$t('stockAdminScreens.qty_group')">
              <FormField v-for="f in QTY_FIELDS" :key="f" :id="`receipt-line-${i}-${f}`" :label="$t(`stockOps.${f}`)" v-slot="{ describedBy }">
                <input :id="`receipt-line-${i}-${f}`" v-model.number="line[f]" type="number" min="0" step="1" inputmode="numeric" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
              </FormField>
              <div class="grid gap-1.5">
                <span class="text-base font-medium text-ink">{{ $t('stockOps.line_total') }}</span>
                <span class="flex min-h-11 items-center justify-end text-base font-bold lg:min-h-10" :class="lineCheck(line).ok ? 'text-ink' : 'text-tone-danger-text'">{{ lineTotal(line) }}</span>
              </div>
            </div>

            <div v-if="form.origin === 'fournisseur'" class="grid gap-3 sm:grid-cols-2">
              <FormField :id="`receipt-line-${i}-lot`" :label="`${$t('stockOps.col_lot_number')} (${$t('stockOps.optional')})`" v-slot="{ describedBy }">
                <input :id="`receipt-line-${i}-lot`" v-model="line.lot_number" type="text" maxlength="30" :aria-describedby="describedBy" :class="fieldClass" />
              </FormField>
              <FormField :id="`receipt-line-${i}-expiry`" :label="`${$t('stockOps.col_expiry')} (${$t('stockOps.optional')})`" v-slot="{ describedBy }">
                <input :id="`receipt-line-${i}-expiry`" v-model="line.expiry_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
              </FormField>
            </div>
            <p v-else class="text-base text-ink-muted">{{ $t('stockOps.col_expiry') }} : {{ line.expiry_date || '-' }}</p>

            <p v-if="!lineCheck(line).ok" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ $t(`stockOps.line_error_${lineCheck(line).error}`) }}</p>
          </div>
          <div v-if="form.origin === 'fournisseur'">
            <AppButton variant="secondary" :icon="PlusCircleIcon" @click="addLine">{{ $t('stockOps.add_line') }}</AppButton>
          </div>
        </div>
      </form>

      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="showForm = false">{{ $t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="receipt-form" :disabled="saving" :loading="saving">
            {{ saving ? $t('stockOps.saving') : $t('stockOps.save') }}
          </AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { todayLocalISO } from '@/utils/localDate';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { validateReceiptLine, prefillFromLot, lineTotal, QTY_FIELDS } from '@/utils/receiptLines';
import { PlusCircleIcon, TrashIcon } from '@heroicons/vue/24/outline';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const CHECK_STATUSES = ['a_controler', 'valide', 'rejete']; // annulation = rejete + motif cote serveur
const today = todayLocalISO;

// Colonnes des tableaux (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'number', label: t('stockOps.col_receipt_number') },
  { key: 'origin', label: t('stockOps.col_origin') },
  { key: 'source', label: t('stockOps.col_source') },
  { key: 'date', label: t('stockOps.col_received_date') },
  { key: 'status', label: t('stockOps.col_status') },
]);
const detailColumns = computed(() => [
  { key: 'product', label: t('stockOps.col_product') },
  { key: 'expected', label: t('stockOps.col_expected'), align: 'right' },
  { key: 'good', label: t('stockOps.col_good'), align: 'right' },
  { key: 'damaged', label: t('stockOps.col_damaged'), align: 'right' },
  { key: 'lost', label: t('stockOps.col_lost'), align: 'right' },
  { key: 'defective', label: t('stockOps.col_defective'), align: 'right' },
  { key: 'lot', label: t('stockOps.col_lot_number') },
  { key: 'expiry', label: t('stockOps.col_expiry') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const receipts = ref([]);
const lots = ref([]);
const products = ref([]);
const statusFilter = ref('');
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const busyId = ref(null);
const saving = ref(false);
const detail = ref(null);
const detailError = ref('');

const showForm = ref(false);
const formError = ref('');
const newLine = () => ({ product_id: null, product_name: '', qty_expected: null, qty_good: 0, qty_damaged: 0, qty_lost: 0, qty_defective: 0, lot_number: '', expiry_date: '' });
const form = reactive({ origin: 'fabrication', production_lot_id: null, supplier: '', delivery_ref: '', received_date: today(), lines: [] });

const deliveredLots = computed(() => lots.value.filter((l) => l.status === 'livre'));
const lineCheck = (line) => validateReceiptLine(line);

const badge = (s) => ({
  a_controler: 'warning',
  valide: 'success',
  rejete: 'danger',
  annule: 'neutral',
}[s] || 'neutral');

const lotLabel = (id) => {
  const lot = lots.value.find((l) => l.id === id);
  return lot ? `${lot.lot_number} - ${lot.product_name}` : (id ? `#${id}` : '-');
};

const loadReceipts = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    receipts.value = (await StockOpsGateway.listReceipts({ status: statusFilter.value })) || [];
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_load'));
    console.error('Chargement des receptions echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const loadLots = async () => {
  try {
    lots.value = (await StockOpsGateway.listLots()) || [];
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_load'));
    console.error('Chargement des lots echoue :', err);
  }
};

const onOriginChange = () => {
  form.production_lot_id = null;
  form.lines = form.origin === 'fournisseur' ? [newLine()] : [];
};

const onLotChange = () => {
  const lot = deliveredLots.value.find((l) => l.id === form.production_lot_id);
  form.lines = lot ? [prefillFromLot(lot)] : [];
};

const addLine = () => form.lines.push(newLine());

const openForm = async () => {
  Object.assign(form, { origin: 'fabrication', production_lot_id: null, supplier: '', delivery_ref: '', received_date: today(), lines: [] });
  formError.value = '';
  showForm.value = true;
  await loadLots();
  if (products.value.length === 0) {
    try {
      products.value = await StockOpsGateway.listProducts();
    } catch (err) {
      formError.value = describeStockError(err, t('stockOps.error_products'));
      console.error('Chargement des produits echoue :', err);
    }
  }
};

const submitReceipt = async () => {
  formError.value = '';
  if (!form.received_date) { formError.value = t('stockOps.err_date_required'); return; }
  if (form.origin === 'fabrication' && !form.production_lot_id) { formError.value = t('stockOps.err_lot_required'); return; }
  if (form.origin === 'fournisseur' && !form.supplier.trim()) { formError.value = t('stockOps.err_supplier_required'); return; }
  if (form.lines.length === 0) { formError.value = t('stockOps.err_lines_required'); return; }
  for (const line of form.lines) {
    if (!line.product_id) { formError.value = t('stockOps.err_product_required'); return; }
    const chk = validateReceiptLine(line);
    if (!chk.ok) { formError.value = t(`stockOps.line_error_${chk.error}`); return; }
  }
  const fab = form.origin === 'fabrication';
  const payload = {
    origin: form.origin,
    production_lot_id: fab ? form.production_lot_id : null,
    supplier: fab ? null : form.supplier.trim(),
    delivery_ref: fab ? null : (form.delivery_ref.trim() || null),
    received_date: form.received_date,
    lines: form.lines.map((l) => ({
      product_id: l.product_id,
      qty_expected: typeof l.qty_expected === 'number' ? l.qty_expected : null,
      qty_good: l.qty_good, qty_damaged: l.qty_damaged, qty_lost: l.qty_lost, qty_defective: l.qty_defective,
      lot_number: fab ? null : ((l.lot_number || '').trim() || null),
      expiry_date: l.expiry_date || null,
    })),
  };
  saving.value = true;
  try {
    await StockOpsGateway.createReceipt(payload);
    showForm.value = false;
    pageMessage.value = t('stockOps.receipts.created');
    await Promise.all([loadReceipts(), loadLots()]);
  } catch (err) {
    formError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Creation de la reception echouee :', err);
  } finally {
    saving.value = false;
  }
};

const openDetail = async (r) => {
  detail.value = r;
  detailError.value = '';
  try {
    detail.value = await StockOpsGateway.getReceipt(r.id);
  } catch (err) {
    detailError.value = describeStockError(err, t('stockOps.error_load'));
    console.error('Chargement du detail echoue :', err);
  }
};

const cancelReceipt = async (r) => {
  if (!window.confirm(t('stockOps.confirm_cancel'))) return;
  pageError.value = '';
  pageMessage.value = '';
  busyId.value = r.id;
  try {
    await StockOpsGateway.cancelReceipt(r.id);
    pageMessage.value = t('stockOps.cancelled');
    await Promise.all([loadReceipts(), loadLots()]);
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Annulation de la reception echouee :', err);
  } finally {
    busyId.value = null;
  }
};

onMounted(() => { loadLots(); loadReceipts(); });
</script>
