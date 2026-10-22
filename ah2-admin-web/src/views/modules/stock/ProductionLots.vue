<!-- src/views/modules/stock/ProductionLots.vue -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="$t('stockOps.lots.title')" :subtitle="$t('stockAdminScreens.lots_count', { n: lots.length })">
      <template #actions>
        <AppButton :icon="PlusCircleIcon" @click="openForm">{{ $t('stockOps.lots.new') }}</AppButton>
      </template>
    </PageHeader>

    <section :aria-label="$t('stockAdminScreens.status_filter')" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
      <div class="max-w-xs">
        <FormField id="lots-status" :label="$t('stockAdminScreens.status_filter')" v-slot="{ describedBy }">
          <select id="lots-status" v-model="statusFilter" @change="loadLots" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ $t('stockOps.all_statuses') }}</option>
            <option v-for="s in LOT_STATUSES" :key="s" :value="s">{{ $t(`stockOps.lot_status.${s}`) }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <ResponsiveTable
      :columns="columns"
      :rows="lots"
      row-key="id"
      :loading="isLoading"
      :empty-title="$t('stockOps.lots.empty')"
      :empty-message="' '"
      striped
    >
      <template #cell-number="{ row: lot }"><span class="font-mono">{{ lot.lot_number }}</span></template>
      <template #cell-product="{ row: lot }">{{ lot.product_name }}</template>
      <template #cell-quantity="{ row: lot }"><span class="font-semibold">{{ lot.quantity_produced }}</span></template>
      <template #cell-production="{ row: lot }">{{ lot.production_date || '-' }}</template>
      <template #cell-delivery="{ row: lot }">{{ lot.delivery_date || '-' }}</template>
      <template #cell-expiry="{ row: lot }">{{ lot.expiry_date || '-' }}</template>
      <template #cell-producer="{ row: lot }">{{ lot.producer || '-' }}</template>
      <template #cell-status="{ row: lot }"><StatusBadge :tone="badge(lot.status)" :label="$t(`stockOps.lot_status.${lot.status}`)" /></template>
      <template #actions="{ row: lot }">
        <AppButton v-if="lot.status === 'produit'" variant="info" @click="openDeliver(lot)">{{ $t('stockOps.lots.mark_delivered') }}</AppButton>
        <AppButton v-if="lot.status === 'produit' || lot.status === 'livre'" variant="danger" @click="cancelLot(lot)" :disabled="busyId === lot.id" :loading="busyId === lot.id">{{ $t('stockOps.cancel') }}</AppButton>
      </template>
    </ResponsiveTable>

    <!-- Formulaire de creation -->
    <FullScreenPanel v-if="showForm" :title="$t('stockOps.lots.new')" @close="showForm = false">
      <form id="lot-form" @submit.prevent="submitLot" class="grid gap-4">
        <p v-if="formError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ formError }}</p>

        <FormField id="lot-product" :label="$t('stockOps.col_product')" required v-slot="{ describedBy }">
          <select id="lot-product" v-model.number="form.product_id" :aria-describedby="describedBy" :class="fieldClass">
            <option :value="null" disabled>{{ $t('stockOps.choose_product') }}</option>
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </FormField>
        <FormField id="lot-quantity" :label="$t('stockOps.col_quantity_produced')" required v-slot="{ describedBy }">
          <input id="lot-quantity" v-model.number="form.quantity_produced" type="number" min="1" step="1" inputmode="numeric" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
        </FormField>
        <FormField id="lot-production" :label="$t('stockOps.col_production_date')" required v-slot="{ describedBy }">
          <input id="lot-production" v-model="form.production_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="lot-delivery" :label="`${$t('stockOps.col_delivery_date')} (${$t('stockOps.optional')})`" v-slot="{ describedBy }">
            <input id="lot-delivery" v-model="form.delivery_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="lot-expiry" :label="`${$t('stockOps.col_expiry')} (${$t('stockOps.optional')})`" v-slot="{ describedBy }">
            <input id="lot-expiry" v-model="form.expiry_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <FormField id="lot-producer" :label="`${$t('stockOps.col_producer')} (${$t('stockOps.optional')})`" v-slot="{ describedBy }">
          <input id="lot-producer" v-model="form.producer" type="text" maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="showForm = false">{{ $t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="lot-form" :disabled="saving" :loading="saving">
            {{ saving ? $t('stockOps.saving') : $t('stockOps.save') }}
          </AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Marquer livre -->
    <FullScreenPanel v-if="deliverLot" :title="`${$t('stockOps.lots.mark_delivered')} - ${deliverLot.lot_number}`" @close="deliverLot = null">
      <form id="deliver-form" @submit.prevent="submitDeliver" class="grid gap-4">
        <p v-if="deliverError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ deliverError }}</p>
        <FormField id="deliver-date" :label="$t('stockOps.col_delivery_date')" v-slot="{ describedBy }">
          <input id="deliver-date" v-model="deliverDate" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="deliverLot = null">{{ $t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="deliver-form" :disabled="saving" :loading="saving">{{ $t('stockOps.confirm') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { todayLocalISO } from '@/utils/localDate';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { PlusCircleIcon } from '@heroicons/vue/24/outline';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const LOT_STATUSES = ['produit', 'livre', 'recu', 'annule'];
const today = todayLocalISO;

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'number', label: t('stockOps.col_lot_number') },
  { key: 'product', label: t('stockOps.col_product') },
  { key: 'quantity', label: t('stockOps.col_quantity_produced'), align: 'right' },
  { key: 'production', label: t('stockOps.col_production_date') },
  { key: 'delivery', label: t('stockOps.col_delivery_date') },
  { key: 'expiry', label: t('stockOps.col_expiry') },
  { key: 'producer', label: t('stockOps.col_producer') },
  { key: 'status', label: t('stockOps.col_status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
  produit: 'warning',
  livre: 'info',
  recu: 'success',
  annule: 'neutral',
}[s] || 'neutral');

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
