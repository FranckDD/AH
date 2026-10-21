<!-- src/views/modules/stock/ProductionLots.vue -->
<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-xl font-bold text-gray-800">{{ $t('stockOps.lots.title') }}</h2>
      <div class="flex items-center gap-3">
        <select v-model="statusFilter" @change="loadLots" class="px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="">{{ $t('stockOps.all_statuses') }}</option>
          <option v-for="s in LOT_STATUSES" :key="s" :value="s">{{ $t(`stockOps.lot_status.${s}`) }}</option>
        </select>
        <button type="button" @click="openForm" class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">
          {{ $t('stockOps.lots.new') }}
        </button>
      </div>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>

    <section class="bg-white rounded-xl shadow-xs border border-gray-200 p-5 overflow-x-auto">
      <div v-if="isLoading" class="text-sm text-gray-400">{{ $t('stockOps.loading') }}</div>
      <div v-else-if="lots.length === 0" class="text-sm text-gray-400">{{ $t('stockOps.lots.empty') }}</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 uppercase border-b">
            <th class="py-2">{{ $t('stockOps.col_lot_number') }}</th>
            <th class="py-2">{{ $t('stockOps.col_product') }}</th>
            <th class="py-2">{{ $t('stockOps.col_quantity_produced') }}</th>
            <th class="py-2">{{ $t('stockOps.col_production_date') }}</th>
            <th class="py-2">{{ $t('stockOps.col_delivery_date') }}</th>
            <th class="py-2">{{ $t('stockOps.col_expiry') }}</th>
            <th class="py-2">{{ $t('stockOps.col_producer') }}</th>
            <th class="py-2">{{ $t('stockOps.col_status') }}</th>
            <th class="py-2">{{ $t('stockOps.col_action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="lot in lots" :key="lot.id" class="border-b last:border-0">
            <td class="py-2 font-mono text-gray-600">{{ lot.lot_number }}</td>
            <td class="py-2">{{ lot.product_name }}</td>
            <td class="py-2">{{ lot.quantity_produced }}</td>
            <td class="py-2">{{ lot.production_date || '-' }}</td>
            <td class="py-2">{{ lot.delivery_date || '-' }}</td>
            <td class="py-2">{{ lot.expiry_date || '-' }}</td>
            <td class="py-2">{{ lot.producer || '-' }}</td>
            <td class="py-2">
              <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="badge(lot.status)">{{ $t(`stockOps.lot_status.${lot.status}`) }}</span>
            </td>
            <td class="py-2 space-x-2 whitespace-nowrap">
              <button v-if="lot.status === 'produit'" type="button" @click="openDeliver(lot)"
                      class="px-3 py-1 bg-emerald-600 text-white rounded-lg text-xs font-medium">{{ $t('stockOps.lots.mark_delivered') }}</button>
              <button v-if="lot.status === 'produit' || lot.status === 'livre'" type="button" @click="cancelLot(lot)"
                      :disabled="busyId === lot.id"
                      class="px-3 py-1 bg-gray-200 text-gray-700 rounded-lg text-xs font-medium disabled:opacity-50">{{ $t('stockOps.cancel') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Formulaire de creation -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <form @submit.prevent="submitLot" class="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-3 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-semibold text-gray-800">{{ $t('stockOps.lots.new') }}</h3>
        <div v-if="formError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ formError }}</div>
        <label class="block text-sm">{{ $t('stockOps.col_product') }}
          <select v-model.number="form.product_id" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option :value="null" disabled>{{ $t('stockOps.choose_product') }}</option>
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_quantity_produced') }}
          <input v-model.number="form.quantity_produced" type="number" min="1" step="1" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_production_date') }}
          <input v-model="form.production_date" type="date" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_delivery_date') }} ({{ $t('stockOps.optional') }})
          <input v-model="form.delivery_date" type="date" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_expiry') }} ({{ $t('stockOps.optional') }})
          <input v-model="form.expiry_date" type="date" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ $t('stockOps.col_producer') }} ({{ $t('stockOps.optional') }})
          <input v-model="form.producer" type="text" maxlength="150" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="showForm = false" class="px-4 py-2 bg-gray-200 rounded-lg text-sm">{{ $t('stockOps.close') }}</button>
          <button type="submit" :disabled="saving" class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
            {{ saving ? $t('stockOps.saving') : $t('stockOps.save') }}
          </button>
        </div>
      </form>
    </div>

    <!-- Marquer livre -->
    <div v-if="deliverLot" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <form @submit.prevent="submitDeliver" class="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ $t('stockOps.lots.mark_delivered') }} - {{ deliverLot.lot_number }}</h3>
        <div v-if="deliverError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ deliverError }}</div>
        <label class="block text-sm">{{ $t('stockOps.col_delivery_date') }}
          <input v-model="deliverDate" type="date" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
        <div class="flex justify-end gap-2">
          <button type="button" @click="deliverLot = null" class="px-4 py-2 bg-gray-200 rounded-lg text-sm">{{ $t('stockOps.close') }}</button>
          <button type="submit" :disabled="saving" class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ $t('stockOps.confirm') }}</button>
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
const LOT_STATUSES = ['produit', 'livre', 'recu', 'annule'];
const today = todayLocalISO;

const lots = ref([]);
const products = ref([]);
const statusFilter = ref('');
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const busyId = ref(null);
const saving = ref(false);

const showForm = ref(false);
const formError = ref('');
const emptyForm = () => ({ product_id: null, quantity_produced: null, production_date: today(), delivery_date: '', expiry_date: '', producer: '' });
const form = reactive(emptyForm());

const deliverLot = ref(null);
const deliverDate = ref('');
const deliverError = ref('');

const badge = (s) => ({
  produit: 'bg-amber-100 text-amber-800',
  livre: 'bg-blue-100 text-blue-800',
  recu: 'bg-green-100 text-green-800',
  annule: 'bg-gray-200 text-gray-600',
}[s] || 'bg-gray-100 text-gray-700');

const loadLots = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    lots.value = (await StockOpsGateway.listLots(statusFilter.value)) || [];
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_load'));
    console.error('Chargement des lots echoue :', err);
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

const submitLot = async () => {
  formError.value = '';
  if (!form.product_id) { formError.value = t('stockOps.err_product_required'); return; }
  if (!Number.isInteger(form.quantity_produced) || form.quantity_produced <= 0) { formError.value = t('stockOps.err_quantity_positive'); return; }
  if (!form.production_date) { formError.value = t('stockOps.err_date_required'); return; }
  const payload = {
    product_id: form.product_id,
    quantity_produced: form.quantity_produced,
    production_date: form.production_date,
    delivery_date: form.delivery_date || null,
    expiry_date: form.expiry_date || null,
    producer: form.producer.trim() || null,
  };
  saving.value = true;
  try {
    await StockOpsGateway.createLot(payload);
    showForm.value = false;
    pageMessage.value = t('stockOps.lots.created');
    await loadLots();
  } catch (err) {
    formError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Creation du lot echouee :', err);
  } finally {
    saving.value = false;
  }
};

const openDeliver = (lot) => {
  deliverLot.value = lot;
  deliverDate.value = today();
  deliverError.value = '';
};

const submitDeliver = async () => {
  deliverError.value = '';
  saving.value = true;
  try {
    await StockOpsGateway.deliverLot(deliverLot.value.id, deliverDate.value || null);
    deliverLot.value = null;
    pageMessage.value = t('stockOps.lots.delivered');
    await loadLots();
  } catch (err) {
    deliverError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Livraison du lot echouee :', err);
  } finally {
    saving.value = false;
  }
};

const cancelLot = async (lot) => {
  if (!window.confirm(t('stockOps.confirm_cancel'))) return;
  pageError.value = '';
  pageMessage.value = '';
  busyId.value = lot.id;
  try {
    await StockOpsGateway.cancelLot(lot.id);
    pageMessage.value = t('stockOps.cancelled');
    await loadLots();
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Annulation du lot echouee :', err);
  } finally {
    busyId.value = null;
  }
};

onMounted(loadLots);
</script>
