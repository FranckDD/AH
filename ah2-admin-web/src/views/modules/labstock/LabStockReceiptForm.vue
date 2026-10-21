<!-- src/views/modules/labstock/LabStockReceiptForm.vue -->
<!-- Saisie d'une reception (fiche papier). Breakpoints : < md = en-tete et lignes en cartes
     empilees (360 px), md = en-tete sur 3 colonnes et cartes de ligne sur 2 colonnes,
     lg = tableau de lignes (n° | designation | conditionnement | qte commandee | qte recue |
     lot | peremption | prix unitaire | total). Acces : StockController, promoteur, admin ;
     « Creer un produit » : laborantin, StockController, admin (droits d'ecriture produit). -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between md:items-center bg-white p-4 md:p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-xl md:text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('labStock.receipt_form_title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('labStock.receipt_form_subtitle') }}</p>
      </div>
      <router-link to="/dashboard/lab-stock-receipts" class="flex items-center justify-center px-4 py-2 min-h-[44px] lg:min-h-0 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 text-sm font-medium">
        {{ t('labStock.back_to_receipts') }}
      </router-link>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="duplicateError" class="bg-red-50 border-2 border-red-400 p-4 rounded-xl text-sm text-red-800">
      <p class="font-bold">{{ t('labStock.duplicate_invoice_title') }}</p>
      <p>{{ duplicateError }}</p>
    </div>

    <!-- En-tete facture -->
    <section class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 md:p-6 grid grid-cols-1 md:grid-cols-3 gap-3">
      <label class="block text-sm text-gray-700">{{ t('labStock.invoice_number') }} *
        <input v-model="form.invoice_number" type="text" maxlength="100" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
      </label>
      <label class="block text-sm text-gray-700">{{ t('labStock.col_supplier') }} *
        <input v-model="form.supplier" type="text" maxlength="150" list="lab-suppliers" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        <datalist id="lab-suppliers"><option v-for="s in suppliers" :key="s" :value="s" /></datalist>
      </label>
      <label class="block text-sm text-gray-700">{{ t('labStock.delivery_date') }} *
        <input v-model="form.delivery_date" type="date" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
      </label>
    </section>

    <!-- Lignes -->
    <section class="space-y-3">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <h2 class="font-semibold text-gray-800">{{ t('labStock.receipt_lines') }} ({{ form.lines.length }})</h2>
        <button type="button" @click="openPicker" :disabled="form.lines.length >= MAX_RECEIPT_LINES"
                class="flex items-center justify-center px-4 py-2 min-h-[44px] lg:min-h-0 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
          <PlusIcon class="h-5 w-5 mr-1" />{{ t('labStock.add_line') }}
        </button>
      </div>

      <div v-if="!form.lines.length" class="bg-white rounded-2xl border border-dashed border-gray-300 p-8 text-center text-gray-500 italic">{{ t('labStock.no_lines') }}</div>

      <!-- Telephone + tablette : une carte par ligne -->
      <div v-if="form.lines.length" class="grid grid-cols-1 md:grid-cols-2 gap-3 lg:hidden">
        <article v-for="(ln, i) in form.lines" :key="ln.product_id"
                 class="bg-white rounded-2xl shadow-xs border p-4 space-y-3"
                 :class="ln.checked ? 'border-emerald-300' : 'border-gray-100'">
          <div class="flex items-start justify-between gap-3">
            <label class="flex items-start gap-3 min-h-[44px] min-w-0">
              <input type="checkbox" v-model="ln.checked" class="mt-1 h-6 w-6 rounded-sm border-gray-300 text-emerald-600" :aria-label="t('labStock.checked')" />
              <span class="min-w-0">
                <span class="block font-semibold text-gray-900 break-words">{{ i + 1 }}. {{ ln.product_name }}</span>
                <span v-if="ln.packaging" class="block text-xs text-gray-500">{{ ln.packaging }}</span>
              </span>
            </label>
            <button type="button" @click="removeLine(i)" class="shrink-0 h-11 w-11 flex items-center justify-center text-red-600 bg-red-50 rounded-lg" :title="t('labStock.remove_line')">
              <TrashIcon class="h-5 w-5" />
            </button>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <label class="block text-xs text-gray-600">{{ t('labStock.col_ordered') }}
              <input v-model="ln.ordered_qty" type="number" inputmode="numeric" pattern="[0-9]*" min="0" step="1" class="mt-1 block w-full px-3 py-2 min-h-[44px] border border-gray-300 rounded-lg" />
            </label>
            <label class="block text-xs text-gray-600">{{ t('labStock.col_received') }} *
              <input v-model="ln.received_qty" type="number" inputmode="numeric" pattern="[0-9]*" min="1" step="1" class="mt-1 block w-full px-3 py-2 min-h-[44px] border border-gray-300 rounded-lg" />
            </label>
            <label class="block text-xs text-gray-600">{{ t('labStock.col_lot') }} *
              <input v-model="ln.lot_number" type="text" maxlength="50" class="mt-1 block w-full px-3 py-2 min-h-[44px] border border-gray-300 rounded-lg" />
            </label>
            <label class="block text-xs text-gray-600">{{ t('labStock.col_expiry') }} *
              <input v-model="ln.expiry_date" type="date" class="mt-1 block w-full px-2 py-2 min-h-[44px] border border-gray-300 rounded-lg" />
            </label>
            <label class="block text-xs text-gray-600 col-span-2">{{ t('labStock.col_unit_price') }} *
              <input v-model="ln.unit_price" type="number" inputmode="decimal" min="0" step="0.01" class="mt-1 block w-full px-3 py-2 min-h-[44px] border border-gray-300 rounded-lg" />
            </label>
          </div>
          <div class="flex justify-between text-sm border-t border-gray-100 pt-2">
            <span class="text-gray-500">{{ t('labStock.col_line_total') }}</span>
            <span class="font-bold text-gray-900">{{ money(lineTotal(ln.received_qty, ln.unit_price)) }}</span>
          </div>
        </article>
      </div>

      <!-- PC : tableau type fiche papier -->
      <div v-if="form.lines.length" class="hidden lg:block bg-white rounded-2xl shadow-xs border border-gray-100 overflow-x-auto">
        <table class="min-w-full text-left text-sm border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-2 py-3 w-8" :title="t('labStock.checked')">✓</th>
              <th class="px-2 py-3">{{ t('labStock.col_no') }}</th>
              <th class="px-2 py-3">{{ t('labStock.col_designation') }}</th>
              <th class="px-2 py-3">{{ t('labStock.col_packaging') }}</th>
              <th class="px-2 py-3 text-right">{{ t('labStock.col_ordered') }}</th>
              <th class="px-2 py-3 text-right">{{ t('labStock.col_received') }}</th>
              <th class="px-2 py-3">{{ t('labStock.col_lot') }}</th>
              <th class="px-2 py-3">{{ t('labStock.col_expiry') }}</th>
              <th class="px-2 py-3 text-right">{{ t('labStock.col_unit_price') }}</th>
              <th class="px-2 py-3 text-right">{{ t('labStock.col_line_total') }}</th>
              <th class="px-2 py-3"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(ln, i) in form.lines" :key="ln.product_id" :class="ln.checked ? 'bg-emerald-50/40' : ''">
              <td class="px-2 py-2"><input type="checkbox" v-model="ln.checked" class="h-4 w-4 rounded-sm border-gray-300 text-emerald-600" :aria-label="t('labStock.checked')" /></td>
              <td class="px-2 py-2 text-gray-500">{{ i + 1 }}</td>
              <td class="px-2 py-2 font-medium text-gray-900">{{ ln.product_name }}</td>
              <td class="px-2 py-2 text-gray-600">{{ ln.packaging || '—' }}</td>
              <td class="px-2 py-2"><input v-model="ln.ordered_qty" type="number" inputmode="numeric" min="0" step="1" class="w-20 px-2 py-1 border border-gray-300 rounded-sm text-right" /></td>
              <td class="px-2 py-2"><input v-model="ln.received_qty" type="number" inputmode="numeric" min="1" step="1" class="w-20 px-2 py-1 border border-gray-300 rounded-sm text-right" /></td>
              <td class="px-2 py-2"><input v-model="ln.lot_number" type="text" maxlength="50" class="w-28 px-2 py-1 border border-gray-300 rounded-sm" /></td>
              <td class="px-2 py-2"><input v-model="ln.expiry_date" type="date" class="w-36 px-2 py-1 border border-gray-300 rounded-sm" /></td>
              <td class="px-2 py-2"><input v-model="ln.unit_price" type="number" inputmode="decimal" min="0" step="0.01" class="w-28 px-2 py-1 border border-gray-300 rounded-sm text-right" /></td>
              <td class="px-2 py-2 text-right font-semibold whitespace-nowrap">{{ money(lineTotal(ln.received_qty, ln.unit_price)) }}</td>
              <td class="px-2 py-2 text-right">
                <button type="button" @click="removeLine(i)" class="text-red-600 bg-red-50 hover:bg-red-100 p-1.5 rounded-lg" :title="t('labStock.remove_line')"><TrashIcon class="h-4 w-4" /></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Pied : total + validation (colle en bas sur telephone/tablette) -->
    <div class="sticky bottom-0 z-30 lg:static bg-white border border-gray-200 rounded-2xl shadow-lg lg:shadow-xs p-3 md:p-4">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
        <div class="flex items-baseline justify-between md:justify-start gap-3">
          <span class="text-sm text-gray-500">{{ t('labStock.receipt_total') }}</span>
          <span class="text-xl font-extrabold text-gray-900">{{ money(total) }}</span>
          <span class="text-xs text-gray-400">{{ t('labStock.checked_count', { n: checkedCount, total: form.lines.length }) }}</span>
        </div>
        <div class="flex flex-col md:items-end gap-1">
          <p v-if="errors.length && touched" class="text-xs text-red-600">{{ errors.map((k) => t(k)).join(' · ') }}</p>
          <button type="button" @click="submit" :disabled="errors.length > 0 || busy"
                  class="w-full md:w-auto px-6 py-3 lg:py-2 min-h-[44px] bg-emerald-600 text-white rounded-xl font-semibold hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {{ busy ? t('labStock.submitting') : t('labStock.submit_receipt') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Choix d'un produit -->
    <div v-if="pickerOpen" class="fixed inset-0 bg-black/40 flex items-start md:items-center justify-center z-50 p-2 md:p-4">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-lg p-4 md:p-6 space-y-3 max-h-[90vh] flex flex-col">
        <h3 class="text-lg font-semibold text-gray-800">{{ t('labStock.add_line') }}</h3>
        <input ref="pickerInput" v-model="pickerSearch" type="text" :placeholder="t('labStock.search_product')"
               class="block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        <ul class="overflow-y-auto divide-y divide-gray-100 flex-1 min-h-0">
          <li v-for="p in pickable" :key="p.id">
            <button type="button" @click="addLine(p)" class="w-full text-left px-3 py-3 min-h-[44px] hover:bg-indigo-50 rounded-lg">
              <span class="font-medium text-gray-900">{{ p.name }}</span>
              <span v-if="p.packaging" class="text-xs text-gray-500"> · {{ p.packaging }}</span>
              <span v-if="p.supplier" class="block text-xs text-gray-400">{{ p.supplier }}</span>
            </button>
          </li>
          <li v-if="!pickable.length" class="px-3 py-4 text-sm text-gray-500 italic">{{ t('labStock.no_match') }}</li>
        </ul>
        <div class="flex flex-col-reverse md:flex-row md:justify-between gap-2 pt-2">
          <button type="button" @click="pickerOpen = false" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-gray-200 rounded-lg text-sm">{{ t('stockOps.close') }}</button>
          <button v-if="canCreateProduct" type="button" @click="openCreate" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg text-sm font-medium">
            {{ t('labStock.create_product') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Creation rapide d'un produit -->
    <div v-if="createOpen" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <form @submit.prevent="createProduct" class="bg-white rounded-xl shadow-xl w-full max-w-md p-5 sm:p-6 space-y-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ t('labStock.create_product') }}</h3>
        <div v-if="modalError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ modalError }}</div>
        <label class="block text-sm">{{ t('labStock.col_product') }}
          <input v-model="newProduct.name" type="text" required maxlength="150" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ t('labStock.col_packaging') }}
          <input v-model="newProduct.packaging" type="text" maxlength="100" class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        </label>
        <label class="block text-sm">{{ t('labStock.col_threshold') }}
          <input v-model.number="newProduct.alert_threshold" type="number" inputmode="numeric" pattern="[0-9]*" min="0" step="1" required class="mt-1 block w-full px-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg" />
        </label>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="createOpen = false" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-gray-200 rounded-lg text-sm">{{ t('stockOps.close') }}</button>
          <button type="submit" :disabled="creating" class="px-4 py-2 min-h-[44px] lg:min-h-0 bg-emerald-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ t('stockOps.save') }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { PlusIcon, TrashIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { lineTotal, receiptTotal, validateReceipt, buildReceiptPayload, MAX_RECEIPT_LINES, formatMoney } from '@/utils/labReceiptLines';

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();
const canCreateProduct = computed(() => authStore.hasRole(['laborantin', 'StockController', 'admin']));

const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
const form = ref({ invoice_number: '', supplier: '', delivery_date: today(), lines: [] });
const products = ref([]);
const knownSuppliers = ref([]);
const pageError = ref('');
const duplicateError = ref('');
const modalError = ref('');
const busy = ref(false);
const touched = ref(false);

const pickerOpen = ref(false);
const pickerSearch = ref('');
const pickerInput = ref(null);
const createOpen = ref(false);
const creating = ref(false);
const newProduct = ref({ name: '', packaging: '', alert_threshold: 0 });

const money = formatMoney;
const total = computed(() => receiptTotal(form.value.lines));
const errors = computed(() => validateReceipt(form.value));
const checkedCount = computed(() => form.value.lines.filter((l) => l.checked).length);

const suppliers = computed(() => {
  const all = [...knownSuppliers.value, ...products.value.map((p) => p.supplier)];
  return [...new Set(all.filter((s) => s && s.trim()).map((s) => s.trim()))].sort();
});

const pickable = computed(() => {
  const used = new Set(form.value.lines.map((l) => l.product_id));
  const q = pickerSearch.value.trim().toLowerCase();
  return products.value
    .filter((p) => p.is_active !== false && !used.has(p.id))
    .filter((p) => !q || [p.name, p.packaging, p.supplier].some((v) => (v || '').toLowerCase().includes(q)));
});

const load = async () => {
  pageError.value = '';
  try {
    products.value = await LabStockGateway.listProducts();
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement des produits du labo echoue :', err);
  }
  try {
    knownSuppliers.value = (await LabStockGateway.listReceipts()).map((r) => r.supplier);
  } catch (err) {
    console.error('Chargement des fournisseurs connus echoue :', err); // suggestions seulement
  }
};

const openPicker = async () => {
  pickerSearch.value = '';
  pickerOpen.value = true;
  await nextTick();
  pickerInput.value?.focus();
};

const addLine = (p) => {
  touched.value = true;
  form.value.lines.push({
    product_id: p.id, product_name: p.name, packaging: p.packaging || '',
    ordered_qty: '', received_qty: '', lot_number: '', expiry_date: '', unit_price: '', checked: false,
  });
  if (!form.value.supplier && p.supplier) form.value.supplier = p.supplier;
  pickerOpen.value = false;
};
const removeLine = (i) => { form.value.lines.splice(i, 1); };

const openCreate = () => {
  modalError.value = '';
  newProduct.value = { name: pickerSearch.value.trim(), packaging: '', alert_threshold: 0 };
  pickerOpen.value = false;
  createOpen.value = true;
};
const createProduct = async () => {
  if (creating.value) return;
  modalError.value = '';
  const name = (newProduct.value.name || '').trim();
  if (!name) { modalError.value = t('labStock.err_name_required'); return; }
  const threshold = Number(newProduct.value.alert_threshold);
  if (!Number.isInteger(threshold) || threshold < 0) { modalError.value = t('labStock.err_threshold'); return; }
  creating.value = true;
  try {
    const p = await LabStockGateway.createProduct({
      name, packaging: (newProduct.value.packaging || '').trim(),
      supplier: (form.value.supplier || '').trim(), alert_threshold: threshold,
    });
    products.value.push(p);
    createOpen.value = false;
    addLine(p);
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Creation de produit echouee :', err);
  } finally {
    creating.value = false;
  }
};

const submit = async () => {
  touched.value = true;
  if (busy.value || errors.value.length) return; // verrou : un double appui n'envoie qu'une fois
  busy.value = true;
  pageError.value = '';
  duplicateError.value = '';
  try {
    const r = await LabStockGateway.createReceipt(buildReceiptPayload(form.value));
    router.push({ path: '/dashboard/lab-stock-receipts', query: { saved: r?.id || 1 } });
  } catch (err) {
    const msg = describeLabStockError(err, t('stockOps.error_save'));
    if (err?.response?.status === 409) duplicateError.value = msg;
    else pageError.value = msg;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    console.error('Enregistrement de la reception echoue :', err);
    busy.value = false;
  }
};

onMounted(load);
</script>
