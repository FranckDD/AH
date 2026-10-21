<!-- src/views/modules/stock/AdjustmentRequestsAdmin.vue -->
<!-- File admin des demandes d'ajustement de stock (secretaire -> admin). -->
<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-xl font-bold text-gray-800">{{ $t('stockAdjust.admin_title') }}</h2>
      <select v-model="statusFilter" @change="load" class="px-3 py-2 border border-gray-300 rounded-lg text-sm">
        <option value="">{{ $t('stockOps.all_statuses') }}</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ $t(`stockAdjust.status.${s}`) }}</option>
      </select>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>

    <section class="bg-white rounded-xl shadow-xs border border-gray-200 p-5 overflow-x-auto">
      <div v-if="isLoading" class="text-sm text-gray-400">{{ $t('stockOps.loading') }}</div>
      <div v-else-if="requests.length === 0" class="text-sm text-gray-400">{{ $t('stockAdjust.no_requests') }}</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 uppercase border-b">
            <th class="py-2">{{ $t('stockOps.col_date') }}</th>
            <th class="py-2">{{ $t('stockOps.col_product') }}</th>
            <th class="py-2">{{ $t('stockAdjust.col_kind') }}</th>
            <th class="py-2">{{ $t('stockOps.col_quantity') }}</th>
            <th class="py-2">{{ $t('stockOps.col_reason') }}</th>
            <th class="py-2">{{ $t('stockAdjust.requester') }}</th>
            <th class="py-2">{{ $t('stockOps.col_status') }}</th>
            <th class="py-2">{{ $t('stockOps.col_action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in requests" :key="r.id" class="border-b last:border-0 align-top">
            <td class="py-2 whitespace-nowrap">{{ formatDateTime(r.requested_at) }}</td>
            <td class="py-2">
              {{ r.product_name }}
              <div v-if="r.kind === 'correction' && r.stock_at_request !== null && r.stock_at_request !== undefined" class="text-xs text-gray-500">
                {{ $t('stockAdjust.correction_detail', { n: r.quantity, m: r.stock_at_request, k: r.current_quantity ?? '—' }) }}
              </div>
              <div v-else-if="r.status === 'en_attente' && r.current_quantity !== null && r.current_quantity !== undefined" class="text-xs text-gray-500">
                {{ $t('stockAdjust.current_stock_n', { n: r.current_quantity }) }}
              </div>
            </td>
            <td class="py-2">{{ $t(`stockAdjust.kind.${r.kind}`) }}</td>
            <td class="py-2">{{ r.kind === 'reapprovisionnement' ? '+' : '= ' }}{{ r.quantity }}</td>
            <td class="py-2 max-w-xs">{{ r.reason }}</td>
            <td class="py-2">{{ actorLabel(r.requested_by_name, r.requested_by) }}</td>
            <td class="py-2">
              <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="badge(r.status)">{{ $t(`stockAdjust.status.${r.status}`) }}</span>
              <div v-if="r.decision_note" class="text-xs text-gray-600 mt-1">{{ $t('stockAdjust.decision_note') }} : {{ r.decision_note }}</div>
              <div v-if="r.stock_before !== null && r.stock_before !== undefined" class="text-xs text-gray-600 mt-1">
                {{ $t('stockAdjust.col_stock_change') }} : {{ r.stock_before }} → {{ r.stock_after }}
              </div>
              <div v-if="rowErrors[r.id]" class="text-xs text-red-700 mt-1">{{ rowErrors[r.id] }}</div>
            </td>
            <td class="py-2 whitespace-nowrap">
              <template v-if="r.status === 'en_attente'">
                <button type="button" @click="approve(r)" :disabled="busyId === r.id"
                        class="px-3 py-1 bg-green-600 text-white rounded-lg text-xs font-medium disabled:opacity-50 mr-1">{{ $t('stockAdjust.approve') }}</button>
                <button type="button" @click="openRefuse(r)" :disabled="busyId === r.id"
                        class="px-3 py-1 bg-red-600 text-white rounded-lg text-xs font-medium disabled:opacity-50">{{ $t('stockAdjust.refuse') }}</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <div v-if="refuseTarget" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <form @submit.prevent="confirmRefuse" class="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ $t('stockAdjust.refuse_title') }}</h3>
        <p class="text-sm text-gray-600">{{ refuseTarget.product_name }} — {{ $t(`stockAdjust.kind.${refuseTarget.kind}`) }} {{ refuseTarget.quantity }}</p>
        <div v-if="refuseError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ refuseError }}</div>
        <label class="block text-sm">{{ $t('stockAdjust.decision_note') }}
          <textarea v-model="refuseNote" rows="3" maxlength="2000" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"></textarea>
        </label>
        <div class="flex justify-end gap-2">
          <button type="button" @click="refuseTarget = null" class="px-4 py-2 bg-gray-200 rounded-lg text-sm">{{ $t('stockOps.close') }}</button>
          <button type="submit" :disabled="busyId !== null" class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ $t('stockAdjust.refuse') }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { actorLabel } from '@/utils/actorName';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';

const { t } = useI18n();
const STATUSES = ['en_attente', 'approuve', 'refuse', 'annule'];

const requests = ref([]);
const statusFilter = ref('en_attente');
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const rowErrors = ref({});
const busyId = ref(null);
const refuseTarget = ref(null);
const refuseNote = ref('');
const refuseError = ref('');

const badge = (s) => ({
  en_attente: 'bg-amber-100 text-amber-800',
  approuve: 'bg-green-100 text-green-800',
  refuse: 'bg-red-100 text-red-800',
  annule: 'bg-gray-200 text-gray-600',
}[s] || 'bg-gray-100 text-gray-700');

const formatDateTime = (v) => (v ? new Date(v).toLocaleString() : '');

const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    requests.value = (await StockOpsGateway.listAdjustmentRequests({ status: statusFilter.value })) || [];
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_load'));
    console.error('Chargement des demandes echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const approve = async (r) => {
  if (!window.confirm(t('stockAdjust.confirm_approve'))) return;
  pageMessage.value = '';
  rowErrors.value = { ...rowErrors.value, [r.id]: '' };
  busyId.value = r.id;
  try {
    await StockOpsGateway.approveAdjustmentRequest(r.id);
    pageMessage.value = t('stockAdjust.approved');
    await load();
  } catch (err) {
    // 409 (stock insuffisant / deja traitee), 403, 422 : message serveur tel quel.
    rowErrors.value = { ...rowErrors.value, [r.id]: describeStockError(err, t('stockOps.error_save')) };
    console.error('Approbation echouee :', err);
  } finally {
    busyId.value = null;
  }
};

const openRefuse = (r) => {
  refuseTarget.value = r;
  refuseNote.value = '';
  refuseError.value = '';
};

const confirmRefuse = async () => {
  refuseError.value = '';
  const note = refuseNote.value.trim();
  if (!note) { refuseError.value = t('stockAdjust.err_note_required'); return; }
  busyId.value = refuseTarget.value.id;
  try {
    await StockOpsGateway.rejectAdjustmentRequest(refuseTarget.value.id, note);
    refuseTarget.value = null;
    pageMessage.value = t('stockAdjust.refused');
    await load();
  } catch (err) {
    refuseError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Refus echoue :', err);
  } finally {
    busyId.value = null;
  }
};

onMounted(load);
</script>
