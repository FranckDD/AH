<!-- src/views/modules/labstock/LabStockProducts.vue -->
<!-- Produits du stock labo. Breakpoints : < md = cartes (1 colonne, 360 px), md = cartes sur
     2 colonnes, lg = tableau. Lecture : tous les roles /lab-stock ; ecriture : laborantin,
     StockController, admin ; signalement : laborantin, admin. -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between md:items-center bg-white p-4 md:p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-xl md:text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('labStock.products_title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('labStock.products_subtitle') }}</p>
      </div>
      <button v-if="canWrite" type="button" @click="openForm(null)"
              class="flex items-center justify-center px-5 py-2.5 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 shadow-md shadow-emerald-200 transition font-semibold">
        <PlusIcon class="h-5 w-5 mr-2" />{{ t('labStock.add_product') }}
      </button>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>

    <div class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
      <div class="relative w-full sm:w-72">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
        </div>
        <input v-model="search" type="text" :placeholder="t('common.search_placeholder')"
               class="block w-full pl-10 pr-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm" />
      </div>
      <label v-if="canWrite" class="flex items-center gap-2 text-sm text-gray-600">
        <input type="checkbox" v-model="includeInactive" @change="load" class="rounded-sm border-gray-300" />
        {{ t('labStock.show_inactive') }}
      </label>
    </div>

    <div v-if="isLoading" class="p-10 text-center text-gray-500">{{ t('stockOps.loading') }}</div>
    <div v-else-if="filtered.length === 0" class="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-500 italic">
      {{ t('labStock.no_products') }}
    </div>

    <template v-else>
      <!-- Phone + tablette : cartes (1 colonne puis 2 colonnes a partir de md) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 lg:hidden">
        <article v-for="p in filtered" :key="p.id"
                 class="bg-white rounded-2xl shadow-xs border p-4 space-y-3"
                 :class="[isLow(p) ? 'border-red-200' : 'border-gray-100', p.is_active ? '' : 'opacity-60']">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h3 class="font-semibold text-gray-900 break-words">{{ p.name }}</h3>
              <p v-if="p.packaging" class="text-xs text-gray-500">{{ p.packaging }}</p>
              <p v-if="p.supplier" class="text-xs text-gray-500">{{ t('labStock.col_supplier') }} : {{ p.supplier }}</p>
            </div>
            <div class="text-right shrink-0">
              <div class="text-2xl font-bold leading-none" :class="isLow(p) ? 'text-red-600' : 'text-gray-900'">{{ num(p.quantity) }}</div>
              <div class="text-xs text-gray-500 mt-1">{{ t('labStock.col_threshold') }} : {{ num(p.alert_threshold) }}</div>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <span v-if="isLow(p)" class="bg-red-100 text-red-700 text-[10px] px-1.5 py-0.5 rounded-sm font-bold uppercase tracking-wide">{{ t('labStock.low') }}</span>
            <span v-if="!p.is_active" class="bg-gray-200 text-gray-600 text-[10px] px-1.5 py-0.5 rounded-sm font-bold uppercase">{{ t('labStock.inactive') }}</span>
            <span class="text-xs text-gray-400 ml-auto">{{ t('labStock.col_last_count') }} : {{ formatDate(p.last_counted_at) || t('labStock.never') }}</span>
          </div>
          <div v-if="canSignal || canWrite" class="flex flex-wrap gap-2 pt-1">
            <button v-if="canSignal && p.is_active" type="button" @click="openSignal(p)"
                    class="flex-1 min-w-[8rem] px-3 py-2 min-h-[44px] lg:min-h-0 bg-amber-50 text-amber-800 hover:bg-amber-100 rounded-lg text-sm font-medium transition">{{ t('labStock.signal') }}</button>
            <button v-if="canWrite" type="button" @click="openForm(p)"
                    class="flex-1 min-w-[8rem] px-3 py-2 min-h-[44px] lg:min-h-0 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg text-sm font-medium transition">{{ t('common.edit') }}</button>
          </div>
        </article>
      </div>

      <!-- Desktop : tableau -->
      <div class="hidden lg:block bg-white rounded-2xl shadow-xs border border-gray-100 overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_product') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_packaging') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_supplier') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.col_stock') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.col_threshold') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_last_count') }}</th>
              <th v-if="canSignal || canWrite" class="px-6 py-3 font-semibold text-right">{{ t('stockOps.col_action') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="p in filtered" :key="p.id" class="hover:bg-gray-50 transition" :class="p.is_active ? '' : 'opacity-60'">
              <td class="px-6 py-4">
                <div class="font-medium text-gray-900">{{ p.name }}</div>
                <span v-if="!p.is_active" class="bg-gray-200 text-gray-600 text-[10px] px-1.5 py-0.5 rounded-sm font-bold uppercase">{{ t('labStock.inactive') }}</span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ p.packaging || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ p.supplier || '—' }}</td>
              <td class="px-6 py-4 text-right">
                <span class="font-bold" :class="isLow(p) ? 'text-red-600' : 'text-gray-900'">{{ num(p.quantity) }}</span>
                <span v-if="isLow(p)" class="ml-2 bg-red-100 text-red-700 text-[10px] px-1.5 py-0.5 rounded-sm font-bold uppercase tracking-wide">{{ t('labStock.low') }}</span>
              </td>
              <td class="px-6 py-4 text-right text-sm text-gray-600">{{ num(p.alert_threshold) }}</td>
              <td class="px-6 py-4 text-sm text-gray-500">{{ formatDate(p.last_counted_at) || t('labStock.never') }}</td>
              <td v-if="canSignal || canWrite" class="px-6 py-4 text-right space-x-2 whitespace-nowrap">
                <button v-if="canSignal && p.is_active" type="button" @click="openSignal(p)"
                        class="text-amber-800 bg-amber-50 hover:bg-amber-100 px-3 py-1.5 rounded-lg text-xs font-medium transition">{{ t('labStock.signal') }}</button>
                <button v-if="canWrite" type="button" @click="openForm(p)"
                        class="text-indigo-600 hover:text-indigo-900 bg-indigo-50 p-1.5 rounded-lg transition" :title="t('common.edit')">
                  <PencilSquareIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Signalement -->
    <div v-if="signalTarget" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-md p-5 sm:p-6 space-y-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ t('labStock.signal_title') }}</h3>
        <p class="text-sm text-gray-600">{{ signalTarget.name }}</p>
        <div v-if="modalError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ modalError }}</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <button v-for="lv in LEVELS" :key="lv" type="button" :disabled="busy" @click="sendSignal(lv)"
                  class="px-4 py-3 min-h-[44px] lg:min-h-0 rounded-lg text-sm font-semibold disabled:opacity-50"
                  :class="lv === 'fini' ? 'bg-red-600 text-white' : 'bg-amber-500 text-white'">{{ labelOf(levelLabel(lv)) }}</button>
        </div>
        <div class="flex justify-end">
          <button type="button" @click="signalTarget = null" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-gray-200 rounded-lg text-sm">{{ t('stockOps.close') }}</button>
        </div>
      </div>
    </div>

    <!-- Creation / modification -->
    <div v-if="formOpen" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <form @submit.prevent="saveForm" class="bg-white rounded-xl shadow-xl w-full max-w-md p-5 sm:p-6 space-y-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ editingId ? t('labStock.edit_product') : t('labStock.add_product') }}</h3>
        <div v-if="modalError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ modalError }}</div>
        <label class="block text-sm">{{ t('labStock.col_product') }}
          <input v-model="form.name" type="text" required maxlength="150" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ t('labStock.col_packaging') }}
          <input v-model="form.packaging" type="text" maxlength="100" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ t('labStock.col_supplier') }}
          <input v-model="form.supplier" type="text" maxlength="150" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ t('labStock.col_threshold') }}
          <input v-model.number="form.alert_threshold" type="number" inputmode="numeric" pattern="[0-9]*" min="0" max="1000000" step="1" required class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        </label>
        <label v-if="editingId" class="flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="form.is_active" class="rounded-sm border-gray-300" />
          {{ t('labStock.active') }}
        </label>
        <p v-else class="text-xs text-gray-500">{{ t('labStock.starts_at_zero') }}</p>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="formOpen = false" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-gray-200 rounded-lg text-sm">{{ t('stockOps.close') }}</button>
          <button type="submit" :disabled="busy" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-emerald-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ t('stockOps.save') }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { PlusIcon, MagnifyingGlassIcon, PencilSquareIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { levelLabel } from '@/utils/labStockLabels';

const { t } = useI18n();
const authStore = useAuthStore();
const LEVELS = ['bientot_fini', 'fini'];

const canWrite = computed(() => authStore.hasRole(['laborantin', 'StockController', 'admin']));
const canSignal = computed(() => authStore.hasRole(['laborantin', 'admin']));

const products = ref([]);
const search = ref('');
const includeInactive = ref(false);
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const modalError = ref('');
const busy = ref(false);

const signalTarget = ref(null);
const formOpen = ref(false);
const editingId = ref(null);
const form = ref({ name: '', packaging: '', supplier: '', alert_threshold: 0, is_active: true });

const num = (v) => Number(v ?? 0);
const isLow = (p) => num(p.quantity) <= num(p.alert_threshold);
const formatDate = (v) => (v ? new Date(v).toLocaleDateString() : '');
const labelOf = (l) => (l.key ? t(l.key) : l.raw);

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return products.value;
  return products.value.filter((p) => [p.name, p.packaging, p.supplier].some((v) => (v || '').toLowerCase().includes(q)));
});

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
    products.value = await LabStockGateway.listProducts({ includeInactive: canWrite.value && includeInactive.value });
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement des produits du labo echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const openSignal = (p) => { pageMessage.value = ''; signalTarget.value = p; modalError.value = ''; };
const sendSignal = async (level) => {
  busy.value = true;
  modalError.value = '';
  try {
    await LabStockGateway.signalProduct(signalTarget.value.id, level);
    signalTarget.value = null;
    flash(t('labStock.signal_sent'));
    await load();
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Signalement echoue :', err);
  } finally {
    busy.value = false;
  }
};

const openForm = (p) => {
  pageMessage.value = '';
  modalError.value = '';
  editingId.value = p ? p.id : null;
  form.value = p
    ? { name: p.name, packaging: p.packaging || '', supplier: p.supplier || '', alert_threshold: num(p.alert_threshold), is_active: !!p.is_active }
    : { name: '', packaging: '', supplier: '', alert_threshold: 0, is_active: true };
  formOpen.value = true;
};

const saveForm = async () => {
  modalError.value = '';
  const f = form.value;
  const name = (f.name || '').trim();
  if (!name) { modalError.value = t('labStock.err_name_required'); return; }
  const threshold = Number(f.alert_threshold);
  if (!Number.isInteger(threshold) || threshold < 0) { modalError.value = t('labStock.err_threshold'); return; }
  busy.value = true;
  try {
    if (editingId.value) {
      await LabStockGateway.updateProduct(editingId.value, {
        name, packaging: (f.packaging || '').trim() || null, supplier: (f.supplier || '').trim() || null,
        alert_threshold: threshold, is_active: f.is_active,
      });
    } else {
      await LabStockGateway.createProduct({
        name, packaging: (f.packaging || '').trim(), supplier: (f.supplier || '').trim(), alert_threshold: threshold,
      });
    }
    formOpen.value = false;
    flash(t('labStock.product_saved'));
    await load();
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Enregistrement du produit echoue :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(load);
</script>
