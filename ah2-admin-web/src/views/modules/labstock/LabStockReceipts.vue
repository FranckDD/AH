<!-- src/views/modules/labstock/LabStockReceipts.vue -->
<!-- Receptions du stock labo. Breakpoints : < md = cartes 1 colonne (360 px), md = cartes sur
     2 colonnes, lg = tableau. Detail en fenetre (lignes en cartes < lg, tableau a lg).
     Acces ecran : StockController, promoteur, admin ; annulation : admin seul (motif). -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between md:items-center bg-white p-4 md:p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-xl md:text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('labStock.receipts_title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('labStock.receipts_subtitle') }}</p>
      </div>
      <router-link v-if="canReceive" to="/dashboard/lab-stock-receipts/new"
                   class="flex items-center justify-center px-5 py-2.5 min-h-[44px] lg:min-h-0 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 shadow-md shadow-emerald-200 transition font-semibold">
        <PlusIcon class="h-5 w-5 mr-2" />{{ t('labStock.new_receipt') }}
      </router-link>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>

    <form @submit.prevent="load" class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 lg:items-end">
      <label class="block text-sm text-gray-600">{{ t('labStock.col_supplier') }}
        <input v-model="filters.supplier" type="text" maxlength="150" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 sm:text-sm" />
      </label>
      <label class="block text-sm text-gray-600">{{ t('labStock.filter_from') }}
        <input v-model="filters.from" type="date" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 sm:text-sm" />
      </label>
      <label class="block text-sm text-gray-600">{{ t('labStock.filter_to') }}
        <input v-model="filters.to" type="date" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 sm:text-sm" />
      </label>
      <button type="submit" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">{{ t('labStock.filter_apply') }}</button>
    </form>

    <div v-if="isLoading" class="p-10 text-center text-gray-500">{{ t('stockOps.loading') }}</div>
    <div v-else-if="receipts.length === 0" class="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-500 italic">
      {{ t('labStock.no_receipts') }}
    </div>

    <template v-else>
      <!-- Telephone + tablette : cartes -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 lg:hidden">
        <button v-for="r in receipts" :key="r.id" type="button" @click="openDetail(r.id)"
                class="text-left bg-white rounded-2xl shadow-xs border p-4 space-y-2 min-h-[44px]"
                :class="r.status === 'annule' ? 'border-gray-200 opacity-70' : 'border-gray-100'">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h3 class="font-semibold text-gray-900 break-words">{{ r.supplier }}</h3>
              <p class="text-xs text-gray-500">{{ t('labStock.invoice_number') }} : {{ r.invoice_number }}</p>
            </div>
            <div class="text-right shrink-0">
              <div class="font-bold text-gray-900">{{ money(r.total_amount) }}</div>
              <div class="text-xs text-gray-500">{{ formatDate(r.delivery_date) }}</div>
            </div>
          </div>
          <div class="flex items-center gap-2 text-xs text-gray-500">
            <span :class="statusClass(r.status)" class="text-[10px] px-1.5 py-0.5 rounded-sm font-bold uppercase">{{ statusText(r.status) }}</span>
            <span>{{ t('labStock.lines_count', { n: (r.lines || []).length }) }}</span>
            <span v-if="r.created_by_name" class="ml-auto truncate">{{ r.created_by_name }}</span>
          </div>
        </button>
      </div>

      <!-- PC : tableau -->
      <div class="hidden lg:block bg-white rounded-2xl shadow-xs border border-gray-100 overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-3 font-semibold">{{ t('labStock.delivery_date') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_supplier') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.invoice_number') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.col_lines') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.receipt_total') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_status') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.created_by') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('stockOps.col_action') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="r in receipts" :key="r.id" class="hover:bg-gray-50 transition" :class="r.status === 'annule' ? 'opacity-70' : ''">
              <td class="px-6 py-4 text-sm text-gray-700">{{ formatDate(r.delivery_date) }}</td>
              <td class="px-6 py-4 font-medium text-gray-900">{{ r.supplier }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ r.invoice_number }}</td>
              <td class="px-6 py-4 text-sm text-right text-gray-600">{{ (r.lines || []).length }}</td>
              <td class="px-6 py-4 text-right font-semibold text-gray-900">{{ money(r.total_amount) }}</td>
              <td class="px-6 py-4"><span :class="statusClass(r.status)" class="text-[10px] px-1.5 py-0.5 rounded-sm font-bold uppercase">{{ statusText(r.status) }}</span></td>
              <td class="px-6 py-4 text-sm text-gray-500">{{ r.created_by_name || '—' }}</td>
              <td class="px-6 py-4 text-right">
                <button type="button" @click="openDetail(r.id)" class="text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg text-xs font-medium transition">{{ t('labStock.view_detail') }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Detail -->
    <div v-if="detail || detailLoading" class="fixed inset-0 bg-black/40 flex items-start md:items-center justify-center z-50 p-2 md:p-4 overflow-y-auto">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-5xl p-4 md:p-6 space-y-4 my-4">
        <div v-if="detailLoading" class="p-6 text-center text-gray-500">{{ t('stockOps.loading') }}</div>
        <template v-else>
          <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-2">
            <div>
              <h3 class="text-lg font-semibold text-gray-800">{{ detail.supplier }} — {{ detail.invoice_number }}</h3>
              <p class="text-sm text-gray-500">{{ t('labStock.delivery_date') }} : {{ formatDate(detail.delivery_date) }}
                <span v-if="detail.created_by_name"> · {{ detail.created_by_name }}</span></p>
            </div>
            <span :class="statusClass(detail.status)" class="self-start text-xs px-2 py-1 rounded-sm font-bold uppercase">{{ statusText(detail.status) }}</span>
          </div>
          <div v-if="detail.status === 'annule'" class="bg-gray-50 border-l-4 border-gray-400 p-3 rounded-sm text-sm text-gray-700">
            {{ t('labStock.cancelled_info', { name: detail.cancelled_by_name || '?', reason: detail.cancel_reason || '' }) }}
          </div>
          <div v-if="modalError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ modalError }}</div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 lg:hidden">
            <article v-for="(ln, i) in detail.lines" :key="ln.id" class="border border-gray-100 rounded-xl p-3 text-sm space-y-1">
              <div class="flex justify-between gap-2">
                <span class="font-semibold text-gray-900">{{ i + 1 }}. {{ ln.product_name }}</span>
                <span class="font-bold">{{ money(ln.line_total) }}</span>
              </div>
              <p v-if="ln.packaging" class="text-xs text-gray-500">{{ ln.packaging }}</p>
              <p class="text-xs text-gray-600">{{ t('labStock.col_received') }} : {{ num(ln.received_qty) }}
                <span v-if="ln.ordered_qty != null"> / {{ t('labStock.col_ordered') }} : {{ num(ln.ordered_qty) }}</span></p>
              <p class="text-xs text-gray-600">{{ t('labStock.col_lot') }} : {{ ln.lot_number }} · {{ t('labStock.col_expiry') }} : {{ formatDate(ln.expiry_date) }}</p>
              <p class="text-xs text-gray-600">{{ t('labStock.col_unit_price') }} : {{ money(ln.unit_price) }}</p>
            </article>
          </div>
          <div class="hidden lg:block overflow-x-auto">
            <table class="min-w-full text-left text-sm border-collapse">
              <thead>
                <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                  <th class="px-3 py-2">{{ t('labStock.col_no') }}</th>
                  <th class="px-3 py-2">{{ t('labStock.col_designation') }}</th>
                  <th class="px-3 py-2">{{ t('labStock.col_packaging') }}</th>
                  <th class="px-3 py-2 text-right">{{ t('labStock.col_ordered') }}</th>
                  <th class="px-3 py-2 text-right">{{ t('labStock.col_received') }}</th>
                  <th class="px-3 py-2">{{ t('labStock.col_lot') }}</th>
                  <th class="px-3 py-2">{{ t('labStock.col_expiry') }}</th>
                  <th class="px-3 py-2 text-right">{{ t('labStock.col_unit_price') }}</th>
                  <th class="px-3 py-2 text-right">{{ t('labStock.col_line_total') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="(ln, i) in detail.lines" :key="ln.id">
                  <td class="px-3 py-2 text-gray-500">{{ i + 1 }}</td>
                  <td class="px-3 py-2 font-medium text-gray-900">{{ ln.product_name }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ ln.packaging || '—' }}</td>
                  <td class="px-3 py-2 text-right">{{ ln.ordered_qty != null ? num(ln.ordered_qty) : '—' }}</td>
                  <td class="px-3 py-2 text-right">{{ num(ln.received_qty) }}</td>
                  <td class="px-3 py-2">{{ ln.lot_number }}</td>
                  <td class="px-3 py-2">{{ formatDate(ln.expiry_date) }}</td>
                  <td class="px-3 py-2 text-right">{{ money(ln.unit_price) }}</td>
                  <td class="px-3 py-2 text-right font-semibold">{{ money(ln.line_total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="flex justify-end text-base font-bold text-gray-900">{{ t('labStock.receipt_total') }} : {{ money(detail.total_amount) }}</div>

          <div v-if="canCancel && detail.status === 'valide'" class="border-t border-gray-100 pt-4 space-y-2">
            <label class="block text-sm text-gray-700">{{ t('labStock.cancel_reason') }}
              <textarea v-model="cancelReason" rows="2" maxlength="2000" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"></textarea>
            </label>
          </div>
          <div class="flex flex-col-reverse md:flex-row md:justify-end gap-2">
            <button type="button" @click="closeDetail" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-gray-200 rounded-lg text-sm">{{ t('stockOps.close') }}</button>
            <button v-if="canCancel && detail.status === 'valide'" type="button" :disabled="busy || !cancelReason.trim()" @click="cancelReceipt"
                    class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ t('labStock.cancel_receipt') }}</button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { PlusIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { formatMoney } from '@/utils/labReceiptLines';

const { t } = useI18n();
const route = useRoute();
const authStore = useAuthStore();
const canReceive = computed(() => authStore.hasRole(['StockController', 'promoteur']));
const canCancel = computed(() => authStore.hasRole(['admin']));

const receipts = ref([]);
const filters = ref({ supplier: '', from: '', to: '' });
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const modalError = ref('');
const detail = ref(null);
const detailLoading = ref(false);
const cancelReason = ref('');
const busy = ref(false);

const num = (v) => Number(v ?? 0);
const money = formatMoney;
const formatDate = (v) => (v ? new Date(v).toLocaleDateString() : '');
const statusText = (s) => (s === 'valide' ? t('labStock.receipt_valid') : s === 'annule' ? t('labStock.receipt_cancelled') : (s || '?'));
const statusClass = (s) => (s === 'annule' ? 'bg-gray-200 text-gray-600' : 'bg-emerald-100 text-emerald-700');

let msgTimer = null;
const flash = (msg) => {
  pageMessage.value = msg;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { pageMessage.value = ''; }, 5000);
};
onBeforeUnmount(() => clearTimeout(msgTimer));

const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    receipts.value = await LabStockGateway.listReceipts({ ...filters.value });
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement des receptions echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const openDetail = async (id) => {
  modalError.value = '';
  cancelReason.value = '';
  detailLoading.value = true;
  try {
    detail.value = await LabStockGateway.getReceipt(id);
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement du detail de reception echoue :', err);
  } finally {
    detailLoading.value = false;
  }
};
const closeDetail = () => { detail.value = null; };

const cancelReceipt = async () => {
  if (busy.value || !cancelReason.value.trim()) return;
  busy.value = true;
  modalError.value = '';
  try {
    await LabStockGateway.cancelReceipt(detail.value.id, cancelReason.value.trim());
    detail.value = null;
    flash(t('labStock.receipt_cancel_done'));
    await load();
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Annulation de reception echouee :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(() => {
  if (route.query.saved) flash(t('labStock.receipt_saved'));
  load();
});
</script>
