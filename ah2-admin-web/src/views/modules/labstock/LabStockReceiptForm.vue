<!-- src/views/modules/labstock/LabStockReceiptForm.vue -->
<!-- Saisie d'une reception (fiche papier) : en-tete de facture, lignes (tableau a partir de lg, cartes dessous),
     total colle en bas. Acces : StockController, promoteur, admin ;
     « Creer un produit » : laborantin, StockController, admin (droits d'ecriture produit). -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('labStock.receipt_form_title')" :subtitle="t('labStock.receipt_form_subtitle')">
      <template #actions>
        <router-link to="/dashboard/lab-stock-receipts" :class="buttonClasses('secondary', 'md')">{{ t('labStock.back_to_receipts') }}</router-link>
      </template>
    </PageHeader>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <div v-if="duplicateError" role="alert" class="rounded-card border-2 p-4 text-base" :class="toneClasses('danger')">
      <p class="font-bold">{{ t('labStock.duplicate_invoice_title') }}</p>
      <p>{{ duplicateError }}</p>
    </div>

    <!-- En-tete facture -->
    <section :aria-label="t('labStockScreens.invoice_header')" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-3 md:p-5">
      <FormField id="lab-invoice-number" :label="t('labStock.invoice_number')" required v-slot="{ describedBy }">
        <input id="lab-invoice-number" v-model="form.invoice_number" type="text" maxlength="100" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="lab-invoice-supplier" :label="t('labStock.col_supplier')" required v-slot="{ describedBy }">
        <input id="lab-invoice-supplier" v-model="form.supplier" type="text" maxlength="150" list="lab-suppliers" :aria-describedby="describedBy" :class="fieldClass" />
        <datalist id="lab-suppliers"><option v-for="s in suppliers" :key="s" :value="s" /></datalist>
      </FormField>
      <FormField id="lab-invoice-date" :label="t('labStock.delivery_date')" required v-slot="{ describedBy }">
        <input id="lab-invoice-date" v-model="form.delivery_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
    </section>

    <!-- Lignes -->
    <section class="grid gap-3">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 class="text-lg font-semibold text-ink">{{ t('labStock.receipt_lines') }} ({{ form.lines.length }})</h2>
        <AppButton :icon="PlusIcon" @click="openPicker" :disabled="form.lines.length >= MAX_RECEIPT_LINES">{{ t('labStock.add_line') }}</AppButton>
      </div>

      <p v-if="!form.lines.length" class="rounded-card border border-dashed border-tone-neutral-border bg-white p-8 text-center text-base text-ink-muted">{{ t('labStock.no_lines') }}</p>

      <ResponsiveTable v-else :columns="lineColumns" :rows="form.lines" row-key="product_id" :aria-label="t('labStockScreens.lines_table')" :empty-title="t('labStock.no_lines')" :empty-message="' '" striped>
        <template #cell-check="{ row: ln }">
          <input type="checkbox" v-model="ln.checked" class="h-5 w-5 accent-brand-600" :aria-label="t('labStock.checked')" />
        </template>
        <template #cell-no="{ row: ln }">{{ form.lines.indexOf(ln) + 1 }}</template>
        <template #cell-designation="{ row: ln }">
          <span class="font-medium">{{ ln.product_name }}</span>
          <span v-if="ln.packaging" class="block text-base text-ink-muted">{{ ln.packaging }}</span>
        </template>
        <template #cell-ordered="{ row: ln }">
          <input v-model="ln.ordered_qty" type="number" inputmode="numeric" pattern="[0-9]*" min="0" step="1" :aria-label="t('labStock.col_ordered')" :class="[fieldClass, 'text-right lg:w-24']" />
        </template>
        <template #cell-received="{ row: ln }">
          <input v-model="ln.received_qty" type="number" inputmode="numeric" pattern="[0-9]*" min="1" step="1" :aria-label="t('labStock.col_received')" :class="[fieldClass, 'text-right lg:w-24']" />
        </template>
        <template #cell-lot="{ row: ln }">
          <input v-model="ln.lot_number" type="text" maxlength="50" :aria-label="t('labStock.col_lot')" :class="[fieldClass, 'lg:w-32']" />
        </template>
        <template #cell-expiry="{ row: ln }">
          <input v-model="ln.expiry_date" type="date" :aria-label="t('labStock.col_expiry')" :class="[fieldClass, 'lg:w-40']" />
        </template>
        <template #cell-unit_price="{ row: ln }">
          <input v-model="ln.unit_price" type="number" inputmode="decimal" min="0" step="0.01" :aria-label="t('labStock.col_unit_price')" :class="[fieldClass, 'text-right lg:w-32']" />
        </template>
        <template #cell-line_total="{ row: ln }"><span class="whitespace-nowrap font-bold">{{ money(lineTotal(ln.received_qty, ln.unit_price)) }}</span></template>
        <template #actions="{ row: ln }">
          <AppButton variant="danger" :icon="TrashIcon" :title="t('labStock.remove_line')" @click="removeLine(form.lines.indexOf(ln))">
            <span class="lg:sr-only">{{ t('labStock.remove_line') }}</span>
          </AppButton>
        </template>
      </ResponsiveTable>
    </section>

    <!-- Pied : total + validation (colle en bas sur telephone/tablette) -->
    <div class="sticky bottom-0 z-30 rounded-card border border-tone-neutral-border bg-white p-3 shadow-card md:p-4 lg:static">
      <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div class="flex items-baseline justify-between gap-3 md:justify-start">
          <span class="text-base text-ink-muted">{{ t('labStock.receipt_total') }}</span>
          <span class="text-2xl font-extrabold text-ink">{{ money(total) }}</span>
          <span class="text-base text-ink-muted">{{ t('labStock.checked_count', { n: checkedCount, total: form.lines.length }) }}</span>
        </div>
        <div class="flex flex-col gap-1 md:items-end">
          <p v-if="errors.length && touched" role="alert" class="text-base text-tone-danger-text">{{ errors.map((k) => t(k)).join(', ') }}</p>
          <AppButton variant="success" class="w-full md:w-auto" @click="submit" :disabled="errors.length > 0 || busy" :loading="busy">
            {{ busy ? t('labStock.submitting') : t('labStock.submit_receipt') }}
          </AppButton>
        </div>
      </div>
    </div>

    <!-- Choix d'un produit -->
    <FullScreenPanel v-if="pickerOpen" :title="t('labStock.add_line')" @close="pickerOpen = false">
      <div class="grid gap-3">
        <FormField id="lab-picker-search" :label="t('labStockScreens.picker_title')" v-slot="{ describedBy }">
          <input id="lab-picker-search" ref="pickerInput" v-model="pickerSearch" type="search" autocomplete="off" :placeholder="t('labStock.search_product')" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <ul class="max-h-80 divide-y divide-tone-neutral-border overflow-y-auto rounded-control border border-tone-neutral-border">
          <li v-for="p in pickable" :key="p.id">
            <button type="button" @click="addLine(p)" class="min-h-11 w-full px-3 py-2 text-left text-base text-ink hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600">
              <span class="font-medium">{{ p.name }}</span>
              <span v-if="p.packaging" class="text-ink-muted">, {{ p.packaging }}</span>
              <span v-if="p.supplier" class="block text-base text-ink-muted">{{ p.supplier }}</span>
            </button>
          </li>
          <li v-if="!pickable.length" class="px-3 py-4 text-base text-ink-muted">{{ t('labStock.no_match') }}</li>
        </ul>
      </div>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="pickerOpen = false">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton v-if="canCreateProduct" variant="secondary" @click="openCreate">{{ t('labStock.create_product') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Creation rapide d'un produit -->
    <FullScreenPanel v-if="createOpen" :title="t('labStock.create_product')" @close="createOpen = false">
      <form id="lab-new-product-form" @submit.prevent="createProduct" class="grid gap-4">
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <FormField id="lab-new-product-name" :label="t('labStock.col_product')" required v-slot="{ describedBy }">
          <input id="lab-new-product-name" v-model="newProduct.name" type="text" required maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="lab-new-product-packaging" :label="t('labStock.col_packaging')" v-slot="{ describedBy }">
          <input id="lab-new-product-packaging" v-model="newProduct.packaging" type="text" maxlength="100" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="lab-new-product-threshold" :label="t('labStock.col_threshold')" required v-slot="{ describedBy }">
          <input id="lab-new-product-threshold" v-model.number="newProduct.alert_threshold" type="number" inputmode="numeric" pattern="[0-9]*" min="0" step="1" required
                 :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="createOpen = false">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="lab-new-product-form" :disabled="creating" :loading="creating">{{ t('stockOps.save') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
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
import { AppButton, PageHeader, FormField, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { buttonClasses } from '@/utils/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();
const canCreateProduct = computed(() => authStore.hasRole(['laborantin', 'StockController', 'admin']));

// Colonnes du tableau des lignes (cartes empilees sous lg) et style commun des champs.
const lineColumns = computed(() => [
  { key: 'check', label: t('labStock.checked') },
  { key: 'no', label: t('labStock.col_no') },
  { key: 'designation', label: t('labStock.col_designation') },
  { key: 'ordered', label: t('labStock.col_ordered'), align: 'right' },
  { key: 'received', label: t('labStock.col_received'), align: 'right' },
  { key: 'lot', label: t('labStock.col_lot') },
  { key: 'expiry', label: t('labStock.col_expiry') },
  { key: 'unit_price', label: t('labStock.col_unit_price'), align: 'right' },
  { key: 'line_total', label: t('labStock.col_line_total'), align: 'right' },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
