<!-- src/views/modules/stock/StockIncidents.vue -->
<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-xl font-bold text-gray-800">{{ $t('stockOps.incidents.title') }}</h2>
      <div class="flex items-center gap-3">
        <select v-model="statusFilter" @change="loadIncidents" class="px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="">{{ $t('stockOps.all_statuses') }}</option>
          <option v-for="s in CHECK_STATUSES" :key="s" :value="s">{{ $t(`stockOps.check_status.${s}`) }}</option>
        </select>
        <button type="button" @click="openForm" class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">
          {{ $t('stockOps.incidents.new') }}
        </button>
      </div>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>

    <section class="bg-white rounded-xl shadow-xs border border-gray-200 p-5 overflow-x-auto">
      <div v-if="isLoading" class="text-sm text-gray-400">{{ $t('stockOps.loading') }}</div>
      <div v-else-if="incidents.length === 0" class="text-sm text-gray-400">{{ $t('stockOps.incidents.empty') }}</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 uppercase border-b">
            <th class="py-2">{{ $t('stockOps.col_date') }}</th>
            <th class="py-2">{{ $t('stockOps.col_product') }}</th>
            <th class="py-2">{{ $t('stockOps.col_kind') }}</th>
            <th class="py-2">{{ $t('stockOps.col_quantity') }}</th>
            <th class="py-2">{{ $t('stockOps.col_reason') }}</th>
            <th class="py-2">{{ $t('stockOps.col_status') }}</th>
            <th class="py-2">{{ $t('stockOps.col_action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inc in incidents" :key="inc.id" class="border-b last:border-0 align-top">
            <td class="py-2">{{ inc.incident_date }}</td>
            <td class="py-2">{{ inc.product_name }}</td>
            <td class="py-2">{{ $t(`stockOps.kind.${inc.kind}`) }}</td>
            <td class="py-2">{{ inc.quantity }}</td>
            <td class="py-2 max-w-xs">{{ inc.reason }}</td>
            <td class="py-2">
              <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="badge(inc.status)">{{ $t(`stockOps.check_status.${inc.status}`) }}</span>
              <div v-if="inc.status === 'rejete' && inc.reject_reason" class="text-xs text-red-700 mt-1">
                {{ $t('stockOps.reject_reason') }} : {{ inc.reject_reason }}
              </div>
            </td>
            <td class="py-2">
              <button v-if="inc.status === 'a_controler'" type="button" @click="cancelIncident(inc)" :disabled="busyId === inc.id"
                      class="px-3 py-1 bg-gray-200 text-gray-700 rounded-lg text-xs font-medium disabled:opacity-50">{{ $t('stockOps.cancel') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <form @submit.prevent="submitIncident" class="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-3 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-semibold text-gray-800">{{ $t('stockOps.incidents.new') }}</h3>
        <div v-if="formError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ formError }}</div>
        <label class="block text-sm">{{ $t('stockOps.col_product') }}
          <select v-model.number="form.product_id" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option :value="null" disabled>{{ $t('stockOps.choose_product') }}</option>
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_kind') }}
          <select v-model="form.kind" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option v-for="k in KINDS" :key="k" :value="k">{{ $t(`stockOps.kind.${k}`) }}</option>
          </select>
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_quantity') }}
          <input v-model.number="form.quantity" type="number" min="1" step="1" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_reason') }}
          <textarea v-model="form.reason" rows="3" maxlength="2000" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"></textarea>
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_date') }}
          <input v-model="form.incident_date" type="date" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
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
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { todayLocalISO } from '@/utils/localDate';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';

const { t } = useI18n();
const KINDS = ['endommage', 'perdu', 'defectueux'];
const CHECK_STATUSES = ['a_controler', 'valide', 'rejete']; // annulation = rejete + motif cote serveur
const today = todayLocalISO;

const incidents = ref([]);
const products = ref([]);
const statusFilter = ref('');
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const busyId = ref(null);
const saving = ref(false);
const showForm = ref(false);
const formError = ref('');
const emptyForm = () => ({ product_id: null, kind: 'endommage', quantity: null, reason: '', incident_date: today() });
const form = reactive(emptyForm());

const badge = (s) => ({
  a_controler: 'bg-amber-100 text-amber-800',
  valide: 'bg-green-100 text-green-800',
  rejete: 'bg-red-100 text-red-800',
  annule: 'bg-gray-200 text-gray-600',
}[s] || 'bg-gray-100 text-gray-700');

const loadIncidents = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    incidents.value = (await StockOpsGateway.listIncidents({ status: statusFilter.value })) || [];
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_load'));
    console.error('Chargement des avaries echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const openForm = async () => {
  Object.assign(form, emptyForm());
  formError.value = '';
  showForm.value = true;
  if (products.value.length === 0) {
    try {
      products.value = await StockOpsGateway.listProducts();
    } catch (err) {
      formError.value = describeStockError(err, t('stockOps.error_products'));
      console.error('Chargement des produits echoue :', err);
    }
  }
};

const submitIncident = async () => {
  formError.value = '';
  if (!form.product_id) { formError.value = t('stockOps.err_product_required'); return; }
  if (!Number.isInteger(form.quantity) || form.quantity <= 0) { formError.value = t('stockOps.err_quantity_positive'); return; }
  if (!form.reason.trim()) { formError.value = t('stockOps.err_reason_required'); return; }
  if (!form.incident_date) { formError.value = t('stockOps.err_date_required'); return; }
  saving.value = true;
  try {
    await StockOpsGateway.createIncident({
      product_id: form.product_id, kind: form.kind, quantity: form.quantity,
      reason: form.reason.trim(), incident_date: form.incident_date,
    });
    showForm.value = false;
    pageMessage.value = t('stockOps.incidents.created');
    await loadIncidents();
  } catch (err) {
    formError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Declaration de l\'avarie echouee :', err);
  } finally {
    saving.value = false;
  }
};

const cancelIncident = async (inc) => {
  if (!window.confirm(t('stockOps.confirm_cancel'))) return;
  pageError.value = '';
  pageMessage.value = '';
  busyId.value = inc.id;
  try {
    await StockOpsGateway.cancelIncident(inc.id);
    pageMessage.value = t('stockOps.cancelled');
    await loadIncidents();
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Annulation de l\'avarie echouee :', err);
  } finally {
    busyId.value = null;
  }
};

onMounted(loadIncidents);
</script>
