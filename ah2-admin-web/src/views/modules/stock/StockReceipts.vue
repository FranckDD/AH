<!-- src/views/modules/stock/StockReceipts.vue -->
<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-xl font-bold text-gray-800">{{ $t('stockOps.receipts.title') }}</h2>
      <div class="flex items-center gap-3">
        <select v-model="statusFilter" @change="loadReceipts" class="px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="">{{ $t('stockOps.all_statuses') }}</option>
          <option v-for="s in CHECK_STATUSES" :key="s" :value="s">{{ $t(`stockOps.check_status.${s}`) }}</option>
        </select>
        <button type="button" @click="openForm" class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">
          {{ $t('stockOps.receipts.new') }}
        </button>
      </div>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>

    <section class="bg-white rounded-xl shadow-xs border border-gray-200 p-5 overflow-x-auto">
      <div v-if="isLoading" class="text-sm text-gray-400">{{ $t('stockOps.loading') }}</div>
      <div v-else-if="receipts.length === 0" class="text-sm text-gray-400">{{ $t('stockOps.receipts.empty') }}</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 uppercase border-b">
            <th class="py-2">{{ $t('stockOps.col_receipt_number') }}</th>
            <th class="py-2">{{ $t('stockOps.col_origin') }}</th>
            <th class="py-2">{{ $t('stockOps.col_source') }}</th>
            <th class="py-2">{{ $t('stockOps.col_received_date') }}</th>
            <th class="py-2">{{ $t('stockOps.col_status') }}</th>
            <th class="py-2">{{ $t('stockOps.col_action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in receipts" :key="r.id" class="border-b last:border-0 align-top">
            <td class="py-2 font-mono text-gray-600">{{ r.receipt_number }}</td>
            <td class="py-2">{{ $t(`stockOps.origin.${r.origin}`) }}</td>
            <td class="py-2">{{ r.origin === 'fournisseur' ? (r.supplier || '-') : lotLabel(r.production_lot_id) }}</td>
            <td class="py-2">{{ r.received_date }}</td>
            <td class="py-2">
              <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="badge(r.status)">{{ $t(`stockOps.check_status.${r.status}`) }}</span>
              <div v-if="r.status === 'rejete' && r.reject_reason" class="text-xs text-red-700 mt-1">
                {{ $t('stockOps.reject_reason') }} : {{ r.reject_reason }}
              </div>
            </td>
            <td class="py-2 space-x-2 whitespace-nowrap">
              <button type="button" @click="openDetail(r)" class="px-3 py-1 bg-indigo-600 text-white rounded-lg text-xs font-medium">{{ $t('stockOps.detail') }}</button>
              <button v-if="r.status === 'a_controler'" type="button" @click="cancelReceipt(r)" :disabled="busyId === r.id"
                      class="px-3 py-1 bg-gray-200 text-gray-700 rounded-lg text-xs font-medium disabled:opacity-50">{{ $t('stockOps.cancel') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Detail -->
    <div v-if="detail" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-3xl p-6 space-y-3 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-semibold text-gray-800">{{ $t('stockOps.receipts.detail_title') }} {{ detail.receipt_number }}</h3>
        <div v-if="detailError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ detailError }}</div>
        <p class="text-sm text-gray-600">
          {{ $t(`stockOps.origin.${detail.origin}`) }} - {{ detail.received_date }}
          <span v-if="detail.supplier"> - {{ detail.supplier }}</span>
          <span v-if="detail.delivery_ref"> - {{ detail.delivery_ref }}</span>
        </p>
        <p class="text-sm">
          <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="badge(detail.status)">{{ $t(`stockOps.check_status.${detail.status}`) }}</span>
        </p>
        <p v-if="detail.status === 'rejete' && detail.reject_reason" class="text-sm text-red-700">
          {{ $t('stockOps.reject_reason') }} : {{ detail.reject_reason }}
        </p>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-gray-500 uppercase border-b">
              <th class="py-2">{{ $t('stockOps.col_product') }}</th>
              <th class="py-2">{{ $t('stockOps.col_expected') }}</th>
              <th class="py-2">{{ $t('stockOps.col_good') }}</th>
              <th class="py-2">{{ $t('stockOps.col_damaged') }}</th>
              <th class="py-2">{{ $t('stockOps.col_lost') }}</th>
              <th class="py-2">{{ $t('stockOps.col_defective') }}</th>
              <th class="py-2">{{ $t('stockOps.col_lot_number') }}</th>
              <th class="py-2">{{ $t('stockOps.col_expiry') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in detail.lines" :key="l.id" class="border-b last:border-0">
              <td class="py-2">{{ l.product_name }}</td>
              <td class="py-2">{{ l.qty_expected ?? '-' }}</td>
              <td class="py-2">{{ l.qty_good }}</td>
              <td class="py-2">{{ l.qty_damaged }}</td>
              <td class="py-2">{{ l.qty_lost }}</td>
              <td class="py-2">{{ l.qty_defective }}</td>
              <td class="py-2">{{ l.lot_number || '-' }}</td>
              <td class="py-2">{{ l.expiry_date || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div class="flex justify-end">
          <button type="button" @click="detail = null" class="px-4 py-2 bg-gray-200 rounded-lg text-sm">{{ $t('stockOps.close') }}</button>
        </div>
      </div>
    </div>

    <!-- Formulaire de creation -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <form @submit.prevent="submitReceipt" class="bg-white rounded-xl shadow-xl w-full max-w-4xl p-6 space-y-3 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-semibold text-gray-800">{{ $t('stockOps.receipts.new') }}</h3>
        <div v-if="formError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ formError }}</div>

        <div class="flex flex-wrap gap-4 text-sm">
          <label class="flex items-center gap-2">
            <input type="radio" value="fabrication" v-model="form.origin" @change="onOriginChange" />
            {{ $t('stockOps.origin.fabrication') }}
          </label>
          <label class="flex items-center gap-2">
            <input type="radio" value="fournisseur" v-model="form.origin" @change="onOriginChange" />
            {{ $t('stockOps.origin.fournisseur') }}
          </label>
        </div>

        <label class="block text-sm">{{ $t('stockOps.col_received_date') }}
          <input v-model="form.received_date" type="date" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>

        <div v-if="form.origin === 'fabrication'">
          <label class="block text-sm">{{ $t('stockOps.receipts.choose_lot') }}
            <select v-model.number="form.production_lot_id" @change="onLotChange" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option :value="null" disabled>{{ $t('stockOps.receipts.choose_lot') }}</option>
              <option v-for="lot in deliveredLots" :key="lot.id" :value="lot.id">
                {{ lot.lot_number }} - {{ lot.product_name }} ({{ lot.quantity_produced }})
              </option>
            </select>
          </label>
          <p v-if="deliveredLots.length === 0" class="text-xs text-gray-500 mt-1">{{ $t('stockOps.receipts.no_delivered_lot') }}</p>
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label class="block text-sm">{{ $t('stockOps.col_supplier') }}
            <input v-model="form.supplier" type="text" maxlength="150" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
          </label>
          <label class="block text-sm">{{ $t('stockOps.col_delivery_ref') }}
            <input v-model="form.delivery_ref" type="text" maxlength="100" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
          </label>
        </div>

        <div class="space-y-3">
          <div v-for="(line, i) in form.lines" :key="i" class="border border-gray-200 rounded-lg p-3 space-y-2">
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <label class="block text-xs text-gray-600 sm:col-span-2">{{ $t('stockOps.col_product') }}
                <select v-if="form.origin === 'fournisseur'" v-model.number="line.product_id" class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded-sm text-sm">
                  <option :value="null" disabled>{{ $t('stockOps.choose_product') }}</option>
                  <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
                <div v-else class="mt-1 px-2 py-1 text-sm text-gray-800">{{ line.product_name }}</div>
              </label>
              <label class="block text-xs text-gray-600">{{ $t('stockOps.col_expected') }}
                <input v-model.number="line.qty_expected" :disabled="form.origin === 'fabrication'" type="number" min="0" step="1"
                       class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded-sm text-sm disabled:bg-gray-100" />
              </label>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
              <label v-for="f in QTY_FIELDS" :key="f" class="block text-xs text-gray-600">{{ $t(`stockOps.${f}`) }}
                <input v-model.number="line[f]" type="number" min="0" step="1" class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded-sm text-sm" />
              </label>
              <div class="text-xs text-gray-600">{{ $t('stockOps.line_total') }}
                <div class="mt-1 px-2 py-1 text-sm font-semibold" :class="lineCheck(line).ok ? 'text-gray-800' : 'text-red-600'">{{ lineTotal(line) }}</div>
              </div>
            </div>
            <div v-if="form.origin === 'fournisseur'" class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <label class="block text-xs text-gray-600">{{ $t('stockOps.col_lot_number') }} ({{ $t('stockOps.optional') }})
                <input v-model="line.lot_number" type="text" maxlength="30" class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded-sm text-sm" />
              </label>
              <label class="block text-xs text-gray-600">{{ $t('stockOps.col_expiry') }} ({{ $t('stockOps.optional') }})
                <input v-model="line.expiry_date" type="date" class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded-sm text-sm" />
              </label>
            </div>
            <div v-else class="text-xs text-gray-500">{{ $t('stockOps.col_expiry') }} : {{ line.expiry_date || '-' }}</div>
            <p v-if="!lineCheck(line).ok" class="text-xs text-red-600">{{ $t(`stockOps.line_error_${lineCheck(line).error}`) }}</p>
            <button v-if="form.origin === 'fournisseur' && form.lines.length > 1" type="button" @click="form.lines.splice(i, 1)"
                    class="text-xs text-red-600 hover:underline">{{ $t('stockOps.remove_line') }}</button>
          </div>
          <button v-if="form.origin === 'fournisseur'" type="button" @click="addLine"
                  class="px-3 py-1 bg-gray-100 border border-gray-300 rounded-lg text-sm">{{ $t('stockOps.add_line') }}</button>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="showForm = false" class="px-4 py-2 bg-gray-200 rounded-lg text-sm">{{ $t('stockOps.close') }}</button>
          <button type="submit" :disabled="saving" class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
            {{ saving ? $t('stockOps.saving') : $t('stockOps.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { todayLocalISO } from '@/utils/localDate';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { validateReceiptLine, prefillFromLot, lineTotal, QTY_FIELDS } from '@/utils/receiptLines';

const { t } = useI18n();
const CHECK_STATUSES = ['a_controler', 'valide', 'rejete']; // annulation = rejete + motif cote serveur
const today = todayLocalISO;

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
  a_controler: 'bg-amber-100 text-amber-800',
  valide: 'bg-green-100 text-green-800',
  rejete: 'bg-red-100 text-red-800',
  annule: 'bg-gray-200 text-gray-600',
}[s] || 'bg-gray-100 text-gray-700');

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
