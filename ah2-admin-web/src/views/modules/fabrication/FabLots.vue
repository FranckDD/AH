<!-- src/views/modules/fabrication/FabLots.vue -->
<!-- Lots de fabrication. Lecture : ProductionManager, promoteur, admin. Creation : ProductionManager seul. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('fabrication.lots_title')" :subtitle="t('fabrication.lots_subtitle')">
      <template #actions>
        <AppButton v-if="canWrite" :icon="PlusIcon" @click="openCreate">{{ t('fabrication.new_batch') }}</AppButton>
      </template>
    </PageHeader>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <AppCard>
      <div class="mb-4 flex flex-wrap items-end gap-4">
        <div class="w-full max-w-xs">
          <FormField id="fab-lots-status" :label="t('fabrication.filter_status')" v-slot="{ describedBy }">
            <select id="fab-lots-status" v-model="statusFilter" :aria-describedby="describedBy" :class="fieldClass" @change="load">
              <option value="">{{ t('fabrication.filter_all') }}</option>
              <option v-for="s in STATUSES" :key="s" :value="s">{{ t(`fabrication.batch_status_${s}`) }}</option>
            </select>
          </FormField>
        </div>
        <FormField id="fab-lots-from" :label="t('fabrication.filter_date_from')" v-slot="{ describedBy }">
          <input id="fab-lots-from" v-model="dateFrom" type="date" :aria-describedby="describedBy" :class="fieldClass" @change="load" />
        </FormField>
        <FormField id="fab-lots-to" :label="t('fabrication.filter_date_to')" v-slot="{ describedBy }">
          <input id="fab-lots-to" v-model="dateTo" type="date" :aria-describedby="describedBy" :class="fieldClass" @change="load" />
        </FormField>
        <AppButton v-if="dateFrom || dateTo" variant="ghost" @click="resetDates">{{ t('fabrication.filter_reset') }}</AppButton>
      </div>
      <ResponsiveTable
        :columns="columns"
        :rows="batches"
        row-key="id"
        :loading="isLoading"
        :empty-title="t('fabrication.no_batches')"
        :empty-message="' '"
        striped
      >
        <template #cell-batch_number="{ row: b }"><span class="font-medium text-ink">{{ b.batch_number }}</span></template>
        <template #cell-product="{ row: b }">{{ b.product_name || productName(b.product_id) }}</template>
        <template #cell-production_date="{ row: b }">{{ formatDate(b.production_date) }}</template>
        <template #cell-qty_good="{ row: b }">{{ b.status === 'brouillon' || b.status === 'en_production' ? '-' : b.qty_good }}</template>
        <template #cell-status="{ row: b }">
          <StatusBadge :tone="STATUS_TONES[b.status] || 'neutral'" :label="t(`fabrication.batch_status_${b.status}`)" />
          <StatusBadge v-if="b.out_of_tolerance" class="ml-2" tone="danger" :label="t('fabrication.out_of_tolerance')" />
        </template>
        <template #actions="{ row: b }">
          <AppButton variant="secondary" :icon="EyeIcon" @click="openBatch(b)">{{ t('fabrication.open_batch') }}</AppButton>
        </template>
      </ResponsiveTable>
    </AppCard>

    <FullScreenPanel v-if="createOpen" :title="t('fabrication.new_batch')" @close="createOpen = false">
      <form id="fab-batch-form" @submit.prevent="saveBatch" class="grid gap-4">
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <p v-if="productsError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('warning')">{{ productsError }}</p>
        <FormField id="fab-batch-product" :label="t('fabrication.finished_product')" required v-slot="{ describedBy }">
          <select id="fab-batch-product" v-model="form.product_id" required :aria-describedby="describedBy" :class="fieldClass">
            <option :value="null" disabled>{{ t('fabrication.choose_product') }}</option>
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </FormField>
        <FormField id="fab-batch-date" :label="t('fabrication.production_date')" required v-slot="{ describedBy }">
          <input id="fab-batch-date" v-model="form.production_date" type="date" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="fab-batch-producer" :label="t('fabrication.producer')" v-slot="{ describedBy }">
          <input id="fab-batch-producer" v-model="form.producer_name" type="text" maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="createOpen = false">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-batch-form" variant="brand" :disabled="busy" :loading="busy">{{ t('fabrication.create_batch') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { todayLocalISO } from '@/utils/localDate';
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { PlusIcon, EyeIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { FabricationGateway, describeFabricationError } from '@/services/FabricationGateway';
import { AppButton, AppCard, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();

const canWrite = computed(() => authStore.hasRole(['ProductionManager']));

const STATUSES = ['brouillon', 'en_production', 'termine', 'expedie', 'annule'];
const STATUS_TONES = { brouillon: 'neutral', en_production: 'info', termine: 'warning', expedie: 'success', annule: 'neutral' };

const columns = computed(() => [
  { key: 'batch_number', label: t('fabrication.col_batch_number') },
  { key: 'product', label: t('fabrication.col_product') },
  { key: 'production_date', label: t('fabrication.col_date') },
  { key: 'qty_good', label: t('fabrication.col_qty_good'), align: 'right' },
  { key: 'status', label: t('fabrication.col_status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const batches = ref([]);
const products = ref([]);
const productsError = ref('');
const statusFilter = ref('');
const dateFrom = ref('');
const dateTo = ref('');
const resetDates = () => { dateFrom.value = ''; dateTo.value = ''; load(); };
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const modalError = ref('');
const busy = ref(false);
const createOpen = ref(false);

const today = () => todayLocalISO();
const emptyForm = () => ({ product_id: null, production_date: today(), producer_name: '' });
const form = ref(emptyForm());

const formatDate = (v) => (v ? new Date(v).toLocaleDateString('fr-FR') : '-');
const productName = (id) => products.value.find((p) => p.id === id)?.name || '-';

let msgTimer = null;
const flash = (msg) => {
  pageMessage.value = msg;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { pageMessage.value = ''; }, 5000);
};
onBeforeUnmount(() => clearTimeout(msgTimer));

const loadProducts = async () => {
  productsError.value = '';
  try {
    products.value = await FabricationGateway.listProducts();
  } catch (err) {
    products.value = [];
    productsError.value = describeFabricationError(err, t('fabrication.error_products'));
    console.error('Chargement du catalogue echoue :', err);
  }
};

const load = async () => {
  pageError.value = '';
  if (dateFrom.value && dateTo.value && dateFrom.value > dateTo.value) {
    pageError.value = t('fabrication.err_date_range');
    return;
  }
  isLoading.value = true;
  try {
    batches.value = await FabricationGateway.listBatches({
      status: statusFilter.value || undefined,
      dateFrom: dateFrom.value || undefined, dateTo: dateTo.value || undefined,
    });
  } catch (err) {
    pageError.value = describeFabricationError(err, t('fabrication.error_load'));
    console.error('Chargement des lots echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const openBatch = (b) => router.push({ name: 'fabrication-lot', params: { id: b.id } });

const openCreate = () => {
  pageMessage.value = '';
  modalError.value = '';
  form.value = emptyForm();
  createOpen.value = true;
};

const saveBatch = async () => {
  modalError.value = '';
  const f = form.value;
  if (!f.product_id) { modalError.value = t('fabrication.err_product_required'); return; }
  if (!f.production_date) { modalError.value = t('fabrication.err_production_date'); return; }
  busy.value = true;
  try {
    const created = await FabricationGateway.createBatch({
      product_id: f.product_id,
      production_date: f.production_date,
      producer_name: (f.producer_name || '').trim(),
    });
    createOpen.value = false;
    flash(t('fabrication.batch_created'));
    router.push({ name: 'fabrication-lot', params: { id: created.id } });
  } catch (err) {
    modalError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Creation du lot echouee :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(() => { loadProducts(); });
onMounted(load);
</script>
