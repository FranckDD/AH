<!-- src/views/modules/labstock/LabStockReceipts.vue -->
<!-- Receptions du stock labo. Detail en panneau.
     Acces ecran : StockController, promoteur, admin ; annulation : admin seul (motif). -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('labStock.receipts_title')" :subtitle="`${t('labStock.receipts_subtitle')} (${t('labStockScreens.receipts_count', { n: receipts.length })})`">
      <template #actions>
        <router-link v-if="canReceive" to="/dashboard/lab-stock-receipts/new" :class="buttonClasses('primary', 'md')">
          <PlusIcon class="h-5 w-5 shrink-0" aria-hidden="true" />{{ t('labStock.new_receipt') }}
        </router-link>
      </template>
    </PageHeader>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <form @submit.prevent="load" :aria-label="t('labStockScreens.filters_label')"
          class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:grid-cols-4 lg:items-end">
      <FormField id="lab-receipts-supplier" :label="t('labStock.col_supplier')" v-slot="{ describedBy }">
        <input id="lab-receipts-supplier" v-model="filters.supplier" type="text" maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="lab-receipts-from" :label="t('labStock.filter_from')" v-slot="{ describedBy }">
        <input id="lab-receipts-from" v-model="filters.from" type="date" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="lab-receipts-to" :label="t('labStock.filter_to')" v-slot="{ describedBy }">
        <input id="lab-receipts-to" v-model="filters.to" type="date" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <AppButton type="submit">{{ t('labStock.filter_apply') }}</AppButton>
    </form>

    <ResponsiveTable
      :columns="columns"
      :rows="receipts"
      row-key="id"
      :loading="isLoading"
      :empty-title="t('labStock.no_receipts')"
      :empty-message="' '"
      striped
    >
      <template #cell-date="{ row: r }">{{ formatDate(r.delivery_date) }}</template>
      <template #cell-supplier="{ row: r }"><span class="font-medium">{{ r.supplier }}</span></template>
      <template #cell-invoice="{ row: r }">{{ r.invoice_number }}</template>
      <template #cell-lines="{ row: r }">{{ (r.lines || []).length }}</template>
      <template #cell-total="{ row: r }"><span class="font-semibold">{{ money(r.total_amount) }}</span></template>
      <template #cell-status="{ row: r }"><StatusBadge :tone="r.status === 'annule' ? 'neutral' : 'success'" :label="statusText(r.status)" /></template>
      <template #cell-by="{ row: r }">{{ r.created_by_name || '-' }}</template>
      <template #actions="{ row: r }">
        <AppButton variant="info" @click="openDetail(r.id)">{{ t('labStock.view_detail') }}</AppButton>
      </template>
    </ResponsiveTable>

    <!-- Detail -->
    <FullScreenPanel v-if="detail || detailLoading" :title="detail ? `${detail.supplier} - ${detail.invoice_number}` : t('stockOps.loading')" wide @close="closeDetail">
      <p v-if="detailLoading" role="status" class="py-6 text-center text-base text-ink-muted">{{ t('stockOps.loading') }}</p>
      <div v-else class="grid gap-4">
        <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <p class="text-base text-ink-muted">
            {{ t('labStock.delivery_date') }} : {{ formatDate(detail.delivery_date) }}
            <span v-if="detail.created_by_name">, {{ detail.created_by_name }}</span>
          </p>
          <p><StatusBadge :tone="detail.status === 'annule' ? 'neutral' : 'success'" :label="statusText(detail.status)" /></p>
        </div>
        <p v-if="detail.status === 'annule'" class="rounded-control border p-3 text-base" :class="toneClasses('neutral')">
          {{ t('labStock.cancelled_info', { name: detail.cancelled_by_name || '?', reason: detail.cancel_reason || '' }) }}
        </p>
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>

        <ResponsiveTable :columns="lineColumns" :rows="detail.lines || []" row-key="id" :empty-title="t('labStock.no_receipts')" :empty-message="' '" striped>
          <template #cell-no="{ row: ln }">{{ (detail.lines || []).indexOf(ln) + 1 }}</template>
          <template #cell-designation="{ row: ln }"><span class="font-medium">{{ ln.product_name }}</span></template>
          <template #cell-packaging="{ row: ln }">{{ ln.packaging || '-' }}</template>
          <template #cell-ordered="{ row: ln }">{{ ln.ordered_qty != null ? num(ln.ordered_qty) : '-' }}</template>
          <template #cell-received="{ row: ln }">{{ num(ln.received_qty) }}</template>
          <template #cell-lot="{ row: ln }">{{ ln.lot_number }}</template>
          <template #cell-expiry="{ row: ln }">{{ formatDate(ln.expiry_date) }}</template>
          <template #cell-unit_price="{ row: ln }">{{ money(ln.unit_price) }}</template>
          <template #cell-line_total="{ row: ln }"><span class="font-semibold">{{ money(ln.line_total) }}</span></template>
        </ResponsiveTable>

        <p class="flex justify-end text-lg font-bold text-ink">{{ t('labStock.receipt_total') }} : {{ money(detail.total_amount) }}</p>

        <div v-if="canCancel && detail.status === 'valide'" class="grid gap-2 border-t border-tone-neutral-border pt-4">
          <FormField id="lab-receipt-cancel-reason" :label="t('labStock.cancel_reason')" v-slot="{ describedBy }">
            <textarea id="lab-receipt-cancel-reason" v-model="cancelReason" rows="2" maxlength="2000" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
          </FormField>
        </div>
      </div>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="closeDetail">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton v-if="detail && canCancel && detail.status === 'valide'" variant="danger" :disabled="busy || !cancelReason.trim()" :loading="busy" @click="cancelReceipt">{{ t('labStock.cancel_receipt') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { formatDateDMY } from '@/utils/localDate';
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { PlusIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { formatMoney } from '@/utils/labReceiptLines';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { buttonClasses } from '@/utils/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const route = useRoute();
const authStore = useAuthStore();
const canReceive = computed(() => authStore.hasRole(['StockController', 'promoteur']));
const canCancel = computed(() => authStore.hasRole(['admin']));

// Colonnes des tableaux (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'date', label: t('labStock.delivery_date') },
  { key: 'supplier', label: t('labStock.col_supplier') },
  { key: 'invoice', label: t('labStock.invoice_number') },
  { key: 'lines', label: t('labStock.col_lines'), align: 'right' },
  { key: 'total', label: t('labStock.receipt_total'), align: 'right' },
  { key: 'status', label: t('labStock.col_status') },
  { key: 'by', label: t('labStock.created_by') },
]);
const lineColumns = computed(() => [
  { key: 'no', label: t('labStock.col_no') },
  { key: 'designation', label: t('labStock.col_designation') },
  { key: 'packaging', label: t('labStock.col_packaging') },
  { key: 'ordered', label: t('labStock.col_ordered'), align: 'right' },
  { key: 'received', label: t('labStock.col_received'), align: 'right' },
  { key: 'lot', label: t('labStock.col_lot') },
  { key: 'expiry', label: t('labStock.col_expiry') },
  { key: 'unit_price', label: t('labStock.col_unit_price'), align: 'right' },
  { key: 'line_total', label: t('labStock.col_line_total'), align: 'right' },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const receipts = ref([]);
const filters = ref({ supplier: '', from: '', to: '' });
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const modalError = ref('');
const detail = ref(null);
const detailLoading = ref(false);
const cancelReason = ref('');
const busy = ref(false);

const num = (v) => Number(v ?? 0);
const money = formatMoney;
const formatDate = (v) => (v ? formatDateDMY(v) : '');
const statusText = (s) => (s === 'valide' ? t('labStock.receipt_valid') : s === 'annule' ? t('labStock.receipt_cancelled') : (s || '?'));

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
    receipts.value = await LabStockGateway.listReceipts({ ...filters.value });
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement des receptions echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const openDetail = async (id) => {
  modalError.value = '';
  cancelReason.value = '';
  detailLoading.value = true;
  try {
    detail.value = await LabStockGateway.getReceipt(id);
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement du detail de reception echoue :', err);
  } finally {
    detailLoading.value = false;
  }
};
const closeDetail = () => { detail.value = null; };

const cancelReceipt = async () => {
  if (busy.value || !cancelReason.value.trim()) return;
  busy.value = true;
  modalError.value = '';
  try {
    await LabStockGateway.cancelReceipt(detail.value.id, cancelReason.value.trim());
    detail.value = null;
    flash(t('labStock.receipt_cancel_done'));
    await load();
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Annulation de reception echouee :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(() => {
  if (route.query.saved) flash(t('labStock.receipt_saved'));
  load();
});
</script>
