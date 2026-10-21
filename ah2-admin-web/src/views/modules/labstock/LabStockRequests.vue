<!-- src/views/modules/labstock/LabStockRequests.vue -->
<!-- Liste « a commander ». Breakpoints : < md = cartes (1 colonne, 360 px), md = cartes sur
     2 colonnes, lg = tableau. Lecture : roles /lab-stock ; actions (commander / date /
     annuler) : promoteur, ToxicoManager, admin. -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between bg-white p-4 md:p-6 rounded-2xl shadow-xs border border-gray-100 gap-3">
      <div>
        <h1 class="text-xl md:text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('labStock.requests_title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('labStock.requests_subtitle') }}</p>
      </div>
      <select v-model="statusFilter" class="px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg text-sm w-full sm:w-auto">
        <option value="open">{{ t('labStock.filter_open') }}</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ labelOf(requestStatusLabel(s)) }}</option>
        <option value="all">{{ t('labStock.filter_all') }}</option>
      </select>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>

    <div v-if="isLoading" class="p-10 text-center text-gray-500">{{ t('stockOps.loading') }}</div>
    <div v-else-if="visible.length === 0" class="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-500 italic">
      {{ t('labStock.no_requests') }}
    </div>

    <template v-else>
      <!-- Phone + tablette : cartes -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 lg:hidden">
        <article v-for="r in visible" :key="r.id" class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 space-y-3">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h3 class="font-semibold text-gray-900 break-words">{{ r.product_name }}</h3>
              <p v-if="r.packaging" class="text-xs text-gray-500">{{ r.packaging }}</p>
            </div>
            <span class="px-2 py-0.5 rounded-full text-xs font-medium shrink-0" :class="badge(r.status)">{{ labelOf(requestStatusLabel(r.status)) }}</span>
          </div>
          <dl class="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
            <dt class="text-gray-500">{{ t('labStock.col_stock') }}</dt>
            <dd class="text-right font-semibold" :class="isLow(r) ? 'text-red-600' : 'text-gray-900'">{{ num(r.quantity) }}</dd>
            <dt class="text-gray-500">{{ t('labStock.col_threshold') }}</dt>
            <dd class="text-right">{{ num(r.alert_threshold) }}</dd>
            <dt class="text-gray-500">{{ t('labStock.col_origin') }}</dt>
            <dd class="text-right">{{ originText(r) }}</dd>
            <template v-if="r.expected_date">
              <dt class="text-gray-500">{{ t('labStock.col_expected') }}</dt>
              <dd class="text-right">{{ formatDate(r.expected_date) }}</dd>
            </template>
            <template v-if="r.supplier">
              <dt class="text-gray-500">{{ t('labStock.col_supplier') }}</dt>
              <dd class="text-right break-words">{{ r.supplier }}</dd>
            </template>
          </dl>
          <p v-if="r.cancel_reason" class="text-xs text-gray-600">{{ t('labStock.cancel_reason') }} : {{ r.cancel_reason }}</p>
          <div v-if="canOrder && isOpen(r)" class="flex flex-wrap gap-2 pt-1">
            <button v-if="r.status === 'a_commander'" type="button" @click="openOrder(r, false)"
                    class="flex-1 min-w-[8rem] px-3 py-2 min-h-[44px] lg:min-h-0 bg-emerald-600 text-white rounded-lg text-sm font-medium">{{ t('labStock.mark_ordered') }}</button>
            <button v-if="r.status === 'commande'" type="button" @click="openOrder(r, true)"
                    class="flex-1 min-w-[8rem] px-3 py-2 min-h-[44px] lg:min-h-0 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-medium">{{ t('labStock.edit_date') }}</button>
            <button type="button" @click="openCancel(r)"
                    class="flex-1 min-w-[8rem] px-3 py-2 min-h-[44px] lg:min-h-0 bg-red-50 text-red-700 rounded-lg text-sm font-medium">{{ t('labStock.cancel_request') }}</button>
          </div>
        </article>
      </div>

      <!-- Desktop : tableau -->
      <div class="hidden lg:block bg-white rounded-2xl shadow-xs border border-gray-100 overflow-x-auto">
        <table class="min-w-full text-sm text-left">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_product') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.col_stock') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.col_threshold') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_origin') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_status') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_expected') }}</th>
              <th v-if="canOrder" class="px-6 py-3 font-semibold text-right">{{ t('stockOps.col_action') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="r in visible" :key="r.id" class="hover:bg-gray-50 align-top">
              <td class="px-6 py-3">
                <div class="font-medium text-gray-900">{{ r.product_name }}</div>
                <div v-if="r.packaging" class="text-xs text-gray-500">{{ r.packaging }}</div>
                <div v-if="r.supplier" class="text-xs text-gray-500">{{ r.supplier }}</div>
              </td>
              <td class="px-6 py-3 text-right font-semibold" :class="isLow(r) ? 'text-red-600' : 'text-gray-900'">{{ num(r.quantity) }}</td>
              <td class="px-6 py-3 text-right text-gray-600">{{ num(r.alert_threshold) }}</td>
              <td class="px-6 py-3">{{ originText(r) }}</td>
              <td class="px-6 py-3">
                <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="badge(r.status)">{{ labelOf(requestStatusLabel(r.status)) }}</span>
                <div v-if="r.cancel_reason" class="text-xs text-gray-600 mt-1">{{ t('labStock.cancel_reason') }} : {{ r.cancel_reason }}</div>
              </td>
              <td class="px-6 py-3 whitespace-nowrap">{{ formatDate(r.expected_date) }}</td>
              <td v-if="canOrder" class="px-6 py-3 text-right whitespace-nowrap space-x-1">
                <template v-if="isOpen(r)">
                  <button v-if="r.status === 'a_commander'" type="button" @click="openOrder(r, false)"
                          class="px-3 py-1 bg-emerald-600 text-white rounded-lg text-xs font-medium">{{ t('labStock.mark_ordered') }}</button>
                  <button v-if="r.status === 'commande'" type="button" @click="openOrder(r, true)"
                          class="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-medium">{{ t('labStock.edit_date') }}</button>
                  <button type="button" @click="openCancel(r)"
                          class="px-3 py-1 bg-red-50 text-red-700 rounded-lg text-xs font-medium">{{ t('labStock.cancel_request') }}</button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Commander / modifier la date attendue -->
    <div v-if="orderTarget" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <form @submit.prevent="confirmOrder" class="bg-white rounded-xl shadow-xl w-full max-w-md p-5 sm:p-6 space-y-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ orderIsEdit ? t('labStock.edit_date') : t('labStock.mark_ordered') }}</h3>
        <p class="text-sm text-gray-600">{{ orderTarget.product_name }}</p>
        <div v-if="modalError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ modalError }}</div>
        <label class="block text-sm">{{ t('labStock.col_expected') }}
          <input v-model="orderDate" type="date" required :min="today" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        </label>
        <div class="flex justify-end gap-2">
          <button type="button" @click="orderTarget = null" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-gray-200 rounded-lg text-sm">{{ t('stockOps.close') }}</button>
          <button type="submit" :disabled="busy" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-emerald-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ t('stockOps.save') }}</button>
        </div>
      </form>
    </div>

    <!-- Annuler avec motif -->
    <div v-if="cancelTarget" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <form @submit.prevent="confirmCancel" class="bg-white rounded-xl shadow-xl w-full max-w-md p-5 sm:p-6 space-y-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ t('labStock.cancel_request') }}</h3>
        <p class="text-sm text-gray-600">{{ cancelTarget.product_name }}</p>
        <div v-if="modalError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ modalError }}</div>
        <label class="block text-sm">{{ t('labStock.cancel_reason') }}
          <textarea v-model="cancelReason" rows="3" maxlength="2000" required class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg"></textarea>
        </label>
        <div class="flex justify-end gap-2">
          <button type="button" @click="cancelTarget = null" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-gray-200 rounded-lg text-sm">{{ t('stockOps.close') }}</button>
          <button type="submit" :disabled="busy" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ t('labStock.cancel_request') }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { requestOriginLabel, requestStatusLabel, levelLabel } from '@/utils/labStockLabels';
import { todayLocalISO } from '@/utils/localDate';

const { t } = useI18n();
const authStore = useAuthStore();
const STATUSES = ['a_commander', 'commande', 'recu', 'annule'];

const canOrder = computed(() => authStore.hasRole(['promoteur', 'ToxicoManager', 'admin']));

const requests = ref([]);
const statusFilter = ref('open');
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const modalError = ref('');
const busy = ref(false);
const today = todayLocalISO();

const orderTarget = ref(null);
const orderIsEdit = ref(false);
const orderDate = ref('');
const cancelTarget = ref(null);
const cancelReason = ref('');

const visible = computed(() => {
  const f = statusFilter.value;
  if (f === 'all') return requests.value;
  if (f === 'open') return requests.value.filter(isOpen);
  return requests.value.filter((r) => r.status === f);
});

let msgTimer = null;
const flash = (msg) => {
  pageMessage.value = msg;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { pageMessage.value = ''; }, 5000);
};
onBeforeUnmount(() => clearTimeout(msgTimer));

const num = (v) => Number(v ?? 0);
const isLow = (r) => num(r.quantity) <= num(r.alert_threshold);
const isOpen = (r) => r.status === 'a_commander' || r.status === 'commande';
const labelOf = (l) => (l.key ? t(l.key) : l.raw);
const formatDate = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString() : '');
const originText = (r) => {
  const base = labelOf(requestOriginLabel(r.origin));
  const lv = r.level ? labelOf(levelLabel(r.level)) : '';
  return lv ? `${base} (${lv})` : base;
};
const badge = (s) => ({
  a_commander: 'bg-amber-100 text-amber-800',
  commande: 'bg-blue-100 text-blue-800',
  recu: 'bg-green-100 text-green-800',
  annule: 'bg-gray-200 text-gray-600',
}[s] || 'bg-gray-100 text-gray-700');

const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    requests.value = await LabStockGateway.listRequests();
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement des demandes du labo echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const openOrder = (r, isEdit) => {
  pageMessage.value = '';
  orderTarget.value = r;
  orderIsEdit.value = isEdit;
  orderDate.value = isEdit && r.expected_date ? String(r.expected_date).slice(0, 10) : '';
  modalError.value = '';
};

const confirmOrder = async () => {
  modalError.value = '';
  if (!orderDate.value) { modalError.value = t('labStock.err_date_required'); return; }
  if (orderDate.value < today) { modalError.value = t('labStock.err_date_past'); return; }
  busy.value = true;
  try {
    if (orderIsEdit.value) await LabStockGateway.updateExpectedDate(orderTarget.value.id, orderDate.value);
    else await LabStockGateway.markOrdered(orderTarget.value.id, orderDate.value);
    orderTarget.value = null;
    flash(t('labStock.order_saved'));
    await load();
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Commande echouee :', err);
  } finally {
    busy.value = false;
  }
};

const openCancel = (r) => { pageMessage.value = ''; cancelTarget.value = r; cancelReason.value = ''; modalError.value = ''; };

const confirmCancel = async () => {
  modalError.value = '';
  const reason = cancelReason.value.trim();
  if (!reason) { modalError.value = t('labStock.err_reason_required'); return; }
  busy.value = true;
  try {
    await LabStockGateway.cancelRequest(cancelTarget.value.id, reason);
    cancelTarget.value = null;
    flash(t('labStock.request_cancelled'));
    await load();
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Annulation echouee :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(load);
</script>
