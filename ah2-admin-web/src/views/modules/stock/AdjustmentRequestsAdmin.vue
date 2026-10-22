<!-- src/views/modules/stock/AdjustmentRequestsAdmin.vue -->
<!-- File admin des demandes d'ajustement de stock (secretaire -> admin). -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="$t('stockAdjust.admin_title')" :subtitle="$t('stockAdminScreens.requests_count', { n: requests.length })" />

    <section :aria-label="$t('stockAdminScreens.status_filter')" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
      <div class="max-w-xs">
        <FormField id="adjust-status" :label="$t('stockAdminScreens.status_filter')" v-slot="{ describedBy }">
          <select id="adjust-status" v-model="statusFilter" @change="load" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ $t('stockOps.all_statuses') }}</option>
            <option v-for="s in STATUSES" :key="s" :value="s">{{ $t(`stockAdjust.status.${s}`) }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <ResponsiveTable
      :columns="columns"
      :rows="requests"
      row-key="id"
      :loading="isLoading"
      :empty-title="$t('stockAdjust.no_requests')"
      :empty-message="' '"
      striped
    >
      <template #cell-date="{ row: r }"><span class="whitespace-nowrap">{{ formatDateTime(r.requested_at) }}</span></template>
      <template #cell-product="{ row: r }">
        <span class="font-medium">{{ r.product_name }}</span>
        <span v-if="r.kind === 'correction' && r.stock_at_request !== null && r.stock_at_request !== undefined" class="block text-base text-ink-muted">
          {{ $t('stockAdjust.correction_detail', { n: r.quantity, m: r.stock_at_request, k: r.current_quantity ?? '-' }) }}
        </span>
        <span v-else-if="r.status === 'en_attente' && r.current_quantity !== null && r.current_quantity !== undefined" class="block text-base text-ink-muted">
          {{ $t('stockAdjust.current_stock_n', { n: r.current_quantity }) }}
        </span>
      </template>
      <template #cell-kind="{ row: r }">{{ $t(`stockAdjust.kind.${r.kind}`) }}</template>
      <template #cell-quantity="{ row: r }"><span class="font-semibold">{{ r.kind === 'reapprovisionnement' ? '+' : '= ' }}{{ r.quantity }}</span></template>
      <template #cell-reason="{ row: r }"><span class="block max-w-xs">{{ r.reason }}</span></template>
      <template #cell-requester="{ row: r }">{{ actorLabel(r.requested_by_name, r.requested_by) }}</template>
      <template #cell-status="{ row: r }">
        <StatusBadge :tone="badge(r.status)" :label="$t(`stockAdjust.status.${r.status}`)" />
        <span v-if="r.decision_note" class="mt-1 block text-base text-ink-muted">{{ $t('stockAdjust.decision_note') }} : {{ r.decision_note }}</span>
        <span v-if="r.stock_before !== null && r.stock_before !== undefined" class="mt-1 block text-base text-ink-muted">
          {{ $t('stockAdjust.col_stock_change') }} : {{ $t('stockAdminScreens.stock_to', { from: r.stock_before, to: r.stock_after }) }}
        </span>
        <span v-if="rowErrors[r.id]" role="alert" class="mt-1 block text-base font-medium text-tone-danger-text">{{ rowErrors[r.id] }}</span>
      </template>
      <template #actions="{ row: r }">
        <template v-if="r.status === 'en_attente'">
          <AppButton @click="approve(r)" :disabled="busyId === r.id" :loading="busyId === r.id">{{ $t('stockAdjust.approve') }}</AppButton>
          <AppButton variant="danger" @click="openRefuse(r)" :disabled="busyId === r.id">{{ $t('stockAdjust.refuse') }}</AppButton>
        </template>
      </template>
    </ResponsiveTable>

    <FullScreenPanel v-if="refuseTarget" :title="$t('stockAdjust.refuse_title')" @close="refuseTarget = null">
      <form id="refuse-form" @submit.prevent="confirmRefuse" class="grid gap-4">
        <p class="text-base text-ink">{{ refuseTarget.product_name }} - {{ $t(`stockAdjust.kind.${refuseTarget.kind}`) }} {{ refuseTarget.quantity }}</p>
        <p v-if="refuseError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ refuseError }}</p>
        <FormField id="refuse-note" :label="$t('stockAdjust.decision_note')" required v-slot="{ describedBy }">
          <textarea id="refuse-note" v-model="refuseNote" rows="3" maxlength="2000" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="refuseTarget = null">{{ $t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="refuse-form" variant="danger" :disabled="busyId !== null" :loading="busyId !== null">{{ $t('stockAdjust.refuse') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { actorLabel } from '@/utils/actorName';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const STATUSES = ['en_attente', 'approuve', 'refuse', 'annule'];

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'date', label: t('stockOps.col_date') },
  { key: 'product', label: t('stockOps.col_product') },
  { key: 'kind', label: t('stockAdjust.col_kind') },
  { key: 'quantity', label: t('stockOps.col_quantity'), align: 'right' },
  { key: 'reason', label: t('stockOps.col_reason') },
  { key: 'requester', label: t('stockAdjust.requester') },
  { key: 'status', label: t('stockOps.col_status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const requests = ref([]);
const statusFilter = ref('en_attente');
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const rowErrors = ref({});
const busyId = ref(null);
const refuseTarget = ref(null);
const refuseNote = ref('');
const refuseError = ref('');

const badge = (s) => ({
  en_attente: 'warning',
  approuve: 'success',
  refuse: 'danger',
  annule: 'neutral',
}[s] || 'neutral');

const formatDateTime = (v) => (v ? new Date(v).toLocaleString() : '');

const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    requests.value = (await StockOpsGateway.listAdjustmentRequests({ status: statusFilter.value })) || [];
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_load'));
    console.error('Chargement des demandes echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const approve = async (r) => {
  if (!window.confirm(t('stockAdjust.confirm_approve'))) return;
  pageMessage.value = '';
  rowErrors.value = { ...rowErrors.value, [r.id]: '' };
  busyId.value = r.id;
  try {
    await StockOpsGateway.approveAdjustmentRequest(r.id);
    pageMessage.value = t('stockAdjust.approved');
    await load();
  } catch (err) {
    // 409 (stock insuffisant / deja traitee), 403, 422 : message serveur tel quel.
    rowErrors.value = { ...rowErrors.value, [r.id]: describeStockError(err, t('stockOps.error_save')) };
    console.error('Approbation echouee :', err);
  } finally {
    busyId.value = null;
  }
};

const openRefuse = (r) => {
  refuseTarget.value = r;
  refuseNote.value = '';
  refuseError.value = '';
};

const confirmRefuse = async () => {
  refuseError.value = '';
  const note = refuseNote.value.trim();
  if (!note) { refuseError.value = t('stockAdjust.err_note_required'); return; }
  busyId.value = refuseTarget.value.id;
  try {
    await StockOpsGateway.rejectAdjustmentRequest(refuseTarget.value.id, note);
    refuseTarget.value = null;
    pageMessage.value = t('stockAdjust.refused');
    await load();
  } catch (err) {
    refuseError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Refus echoue :', err);
  } finally {
    busyId.value = null;
  }
};

onMounted(load);
</script>
