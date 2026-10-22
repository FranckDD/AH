<!-- src/views/modules/stock/StockIncidents.vue -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="$t('stockOps.incidents.title')" :subtitle="$t('stockAdminScreens.incidents_count', { n: incidents.length })">
      <template #actions>
        <AppButton :icon="PlusCircleIcon" @click="openForm">{{ $t('stockOps.incidents.new') }}</AppButton>
      </template>
    </PageHeader>

    <section :aria-label="$t('stockAdminScreens.status_filter')" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
      <div class="max-w-xs">
        <FormField id="incidents-status" :label="$t('stockAdminScreens.status_filter')" v-slot="{ describedBy }">
          <select id="incidents-status" v-model="statusFilter" @change="loadIncidents" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ $t('stockOps.all_statuses') }}</option>
            <option v-for="s in CHECK_STATUSES" :key="s" :value="s">{{ $t(`stockOps.check_status.${s}`) }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <ResponsiveTable
      :columns="columns"
      :rows="incidents"
      row-key="id"
      :loading="isLoading"
      :empty-title="$t('stockOps.incidents.empty')"
      :empty-message="' '"
      striped
    >
      <template #cell-date="{ row: inc }">{{ inc.incident_date }}</template>
      <template #cell-product="{ row: inc }">{{ inc.product_name }}</template>
      <template #cell-kind="{ row: inc }">{{ $t(`stockOps.kind.${inc.kind}`) }}</template>
      <template #cell-quantity="{ row: inc }"><span class="font-semibold">{{ inc.quantity }}</span></template>
      <template #cell-reason="{ row: inc }"><span class="block max-w-xs">{{ inc.reason }}</span></template>
      <template #cell-status="{ row: inc }">
        <StatusBadge :tone="badge(inc.status)" :label="$t(`stockOps.check_status.${inc.status}`)" />
        <p v-if="inc.status === 'rejete' && inc.reject_reason" class="mt-1 text-base text-tone-danger-text">
          {{ $t('stockOps.reject_reason') }} : {{ inc.reject_reason }}
        </p>
      </template>
      <template #actions="{ row: inc }">
        <AppButton v-if="inc.status === 'a_controler'" variant="danger" @click="cancelIncident(inc)" :disabled="busyId === inc.id" :loading="busyId === inc.id">{{ $t('stockOps.cancel') }}</AppButton>
      </template>
    </ResponsiveTable>

    <FullScreenPanel v-if="showForm" :title="$t('stockOps.incidents.new')" @close="showForm = false">
      <form id="incident-form" @submit.prevent="submitIncident" class="grid gap-4">
        <p v-if="formError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ formError }}</p>

        <FormField id="incident-product" :label="$t('stockOps.col_product')" required v-slot="{ describedBy }">
          <select id="incident-product" v-model.number="form.product_id" :aria-describedby="describedBy" :class="fieldClass">
            <option :value="null" disabled>{{ $t('stockOps.choose_product') }}</option>
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </FormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="incident-kind" :label="$t('stockOps.col_kind')" required v-slot="{ describedBy }">
            <select id="incident-kind" v-model="form.kind" :aria-describedby="describedBy" :class="fieldClass">
              <option v-for="k in KINDS" :key="k" :value="k">{{ $t(`stockOps.kind.${k}`) }}</option>
            </select>
          </FormField>
          <FormField id="incident-quantity" :label="$t('stockOps.col_quantity')" required v-slot="{ describedBy }">
            <input id="incident-quantity" v-model.number="form.quantity" type="number" min="1" step="1" inputmode="numeric" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
        </div>
        <FormField id="incident-reason" :label="$t('stockOps.col_reason')" required v-slot="{ describedBy }">
          <textarea id="incident-reason" v-model="form.reason" rows="3" maxlength="2000" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
        </FormField>
        <FormField id="incident-date" :label="$t('stockOps.col_date')" required v-slot="{ describedBy }">
          <input id="incident-date" v-model="form.incident_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="showForm = false">{{ $t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="incident-form" :disabled="saving" :loading="saving">
            {{ saving ? $t('stockOps.saving') : $t('stockOps.save') }}
          </AppButton>
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
const KINDS = ['endommage', 'perdu', 'defectueux'];
const CHECK_STATUSES = ['a_controler', 'valide', 'rejete']; // annulation = rejete + motif cote serveur
const today = todayLocalISO;

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'date', label: t('stockOps.col_date') },
  { key: 'product', label: t('stockOps.col_product') },
  { key: 'kind', label: t('stockOps.col_kind') },
  { key: 'quantity', label: t('stockOps.col_quantity'), align: 'right' },
  { key: 'reason', label: t('stockOps.col_reason') },
  { key: 'status', label: t('stockOps.col_status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
  a_controler: 'warning',
  valide: 'success',
  rejete: 'danger',
  annule: 'neutral',
}[s] || 'neutral');

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
