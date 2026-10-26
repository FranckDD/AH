<!-- src/views/modules/labstock/LabStockProducts.vue -->
<!-- Produits du stock labo. Lecture : tous les roles /lab-stock ; ecriture : laborantin,
     StockController, admin ; signalement : laborantin, admin. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('labStock.products_title')" :subtitle="`${t('labStock.products_subtitle')} (${t('labStockScreens.products_count', { n: filtered.length })})`">
      <template #actions>
        <AppButton v-if="canWrite" :icon="PlusIcon" @click="openForm(null)">{{ t('labStock.add_product') }}</AppButton>
      </template>
    </PageHeader>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <section :aria-label="t('labStockScreens.search_label')" class="grid gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card sm:grid-cols-[1fr_auto] sm:items-end">
      <FormField id="lab-products-search" :label="t('labStockScreens.search_label')" v-slot="{ describedBy }">
        <input id="lab-products-search" v-model="search" type="search" autocomplete="off" :placeholder="t('common.search_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <label v-if="canWrite" class="flex min-h-11 items-center gap-3 text-base text-ink">
        <input type="checkbox" v-model="includeInactive" @change="load" class="h-5 w-5 accent-brand-600" />
        {{ t('labStock.show_inactive') }}
      </label>
    </section>

    <ResponsiveTable
      :columns="columns"
      :rows="filtered"
      row-key="id"
      :loading="isLoading"
      :empty-title="t('labStock.no_products')"
      :empty-message="' '"
      striped
    >
      <template #cell-product="{ row: p }">
        <span class="font-medium" :class="p.is_active ? 'text-ink' : 'text-ink-muted'">{{ p.name }}</span>
        <StatusBadge v-if="!p.is_active" class="ml-2" tone="neutral" :label="t('labStock.inactive')" />
      </template>
      <template #cell-packaging="{ row: p }">{{ p.packaging || '-' }}</template>
      <template #cell-supplier="{ row: p }">{{ p.supplier || '-' }}</template>
      <template #cell-stock="{ row: p }">
        <span class="font-bold" :class="isLow(p) ? 'text-tone-danger-text' : 'text-ink'">{{ num(p.quantity) }}</span>
        <StatusBadge v-if="isLow(p)" class="ml-2" tone="danger" :label="t('labStock.low')" />
      </template>
      <template #cell-threshold="{ row: p }">{{ num(p.alert_threshold) }}</template>
      <template #cell-last_count="{ row: p }">{{ formatDate(p.last_counted_at) || t('labStock.never') }}</template>
      <template v-if="canSignal || canWrite" #actions="{ row: p }">
        <AppButton v-if="canSignal && p.is_active" variant="toxico" @click="openSignal(p)">{{ t('labStock.signal') }}</AppButton>
        <AppButton v-if="canWrite" variant="secondary" :icon="PencilSquareIcon" @click="openForm(p)">{{ t('common.edit') }}</AppButton>
      </template>
    </ResponsiveTable>

    <!-- Signalement -->
    <FullScreenPanel v-if="signalTarget" :title="t('labStock.signal_title')" @close="signalTarget = null">
      <div class="grid gap-4">
        <p class="text-base font-medium text-ink">{{ signalTarget.name }}</p>
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <div class="grid gap-2 sm:grid-cols-2" role="group" :aria-label="t('labStockScreens.signal_group')">
          <AppButton v-for="lv in LEVELS" :key="lv" :variant="lv === 'fini' ? 'danger' : 'toxico'" :disabled="busy" :loading="busy" @click="sendSignal(lv)">{{ labelOf(levelLabel(lv)) }}</AppButton>
        </div>
      </div>
      <template #footer>
        <ActionBar>
          <AppButton variant="secondary" @click="signalTarget = null">{{ t('stockOps.close') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Creation / modification -->
    <FullScreenPanel v-if="formOpen" :title="editingId ? t('labStock.edit_product') : t('labStock.add_product')" @close="formOpen = false">
      <form id="lab-product-form" @submit.prevent="saveForm" class="grid gap-4">
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <FormField id="lab-product-name" :label="t('labStock.col_product')" required v-slot="{ describedBy }">
          <input id="lab-product-name" v-model="form.name" type="text" required maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="lab-product-packaging" :label="t('labStock.col_packaging')" v-slot="{ describedBy }">
            <input id="lab-product-packaging" v-model="form.packaging" type="text" maxlength="100" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="lab-product-supplier" :label="t('labStock.col_supplier')" v-slot="{ describedBy }">
            <input id="lab-product-supplier" v-model="form.supplier" type="text" maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <FormField id="lab-product-threshold" :label="t('labStock.col_threshold')" required v-slot="{ describedBy }">
          <input id="lab-product-threshold" v-model.number="form.alert_threshold" type="number" inputmode="numeric" pattern="[0-9]*" min="0" max="1000000" step="1" required
                 :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
        </FormField>
        <label v-if="editingId" class="flex min-h-11 items-center gap-3 text-base text-ink">
          <input type="checkbox" v-model="form.is_active" class="h-5 w-5 accent-brand-600" />
          {{ t('labStock.active') }}
        </label>
        <p v-else class="text-base text-ink-muted">{{ t('labStock.starts_at_zero') }}</p>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="formOpen = false">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="lab-product-form" :disabled="busy" :loading="busy">{{ t('stockOps.save') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { formatDateDMY } from '@/utils/localDate';
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { PlusIcon, MagnifyingGlassIcon, PencilSquareIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { levelLabel } from '@/utils/labStockLabels';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const authStore = useAuthStore();
const LEVELS = ['bientot_fini', 'fini'];

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'product', label: t('labStock.col_product') },
  { key: 'packaging', label: t('labStock.col_packaging') },
  { key: 'supplier', label: t('labStock.col_supplier') },
  { key: 'stock', label: t('labStock.col_stock'), align: 'right' },
  { key: 'threshold', label: t('labStock.col_threshold'), align: 'right' },
  { key: 'last_count', label: t('labStock.col_last_count') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
const formatDate = (v) => (v ? formatDateDMY(new Date(v)) : '');
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
