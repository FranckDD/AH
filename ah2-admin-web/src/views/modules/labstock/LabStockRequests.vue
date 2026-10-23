<!-- src/views/modules/labstock/LabStockRequests.vue -->
<!-- Liste « a commander ». Lecture : roles /lab-stock ; actions (commander / date /
     annuler) : promoteur, ToxicoManager, admin. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('labStock.requests_title')" :subtitle="`${t('labStock.requests_subtitle')} (${t('labStockScreens.requests_count', { n: visible.length })})`" />

    <section :aria-label="t('labStockScreens.status_filter')" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
      <div class="max-w-xs">
        <FormField id="lab-requests-status" :label="t('labStockScreens.status_filter')" v-slot="{ describedBy }">
          <select id="lab-requests-status" v-model="statusFilter" :aria-describedby="describedBy" :class="fieldClass">
            <option value="open">{{ t('labStock.filter_open') }}</option>
            <option v-for="s in STATUSES" :key="s" :value="s">{{ labelOf(requestStatusLabel(s)) }}</option>
            <option value="all">{{ t('labStock.filter_all') }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <ResponsiveTable
      :columns="columns"
      :rows="visible"
      row-key="id"
      :loading="isLoading"
      :empty-title="t('labStock.no_requests')"
      :empty-message="' '"
      striped
    >
      <template #cell-product="{ row: r }">
        <span class="font-medium">{{ r.product_name }}</span>
        <span v-if="r.packaging" class="block text-base text-ink-muted">{{ r.packaging }}</span>
        <span v-if="r.supplier" class="block text-base text-ink-muted">{{ r.supplier }}</span>
      </template>
      <template #cell-stock="{ row: r }"><span class="font-semibold" :class="isLow(r) ? 'text-tone-danger-text' : 'text-ink'">{{ num(r.quantity) }}</span></template>
      <template #cell-threshold="{ row: r }">{{ num(r.alert_threshold) }}</template>
      <template #cell-origin="{ row: r }">{{ originText(r) }}</template>
      <template #cell-status="{ row: r }">
        <StatusBadge :tone="badge(r.status)" :label="labelOf(requestStatusLabel(r.status))" />
        <span v-if="r.cancel_reason" class="mt-1 block text-base text-ink-muted">{{ t('labStock.cancel_reason') }} : {{ r.cancel_reason }}</span>
      </template>
      <template #cell-expected="{ row: r }"><span class="whitespace-nowrap">{{ formatDate(r.expected_date) }}</span></template>
      <template v-if="canOrder" #actions="{ row: r }">
        <template v-if="isOpen(r)">
          <AppButton v-if="r.status === 'a_commander'" variant="info" @click="openOrder(r, false)">{{ t('labStock.mark_ordered') }}</AppButton>
          <AppButton v-if="r.status === 'commande'" variant="secondary" @click="openOrder(r, true)">{{ t('labStock.edit_date') }}</AppButton>
          <AppButton variant="danger" @click="openCancel(r)">{{ t('labStock.cancel_request') }}</AppButton>
        </template>
      </template>
    </ResponsiveTable>

    <!-- Commander / modifier la date attendue -->
    <FullScreenPanel v-if="orderTarget" :title="orderIsEdit ? t('labStock.edit_date') : t('labStock.mark_ordered')" @close="orderTarget = null">
      <form id="lab-order-form" @submit.prevent="confirmOrder" class="grid gap-4">
        <p class="text-base font-medium text-ink">{{ orderTarget.product_name }}</p>
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <FormField id="lab-order-date" :label="t('labStock.col_expected')" required v-slot="{ describedBy }">
          <input id="lab-order-date" v-model="orderDate" type="date" required :min="today" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="orderTarget = null">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="lab-order-form" :disabled="busy" :loading="busy">{{ t('stockOps.save') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Annuler avec motif -->
    <FullScreenPanel v-if="cancelTarget" :title="t('labStock.cancel_request')" @close="cancelTarget = null">
      <form id="lab-cancel-form" @submit.prevent="confirmCancel" class="grid gap-4">
        <p class="text-base font-medium text-ink">{{ cancelTarget.product_name }}</p>
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <FormField id="lab-cancel-reason" :label="t('labStock.cancel_reason')" required v-slot="{ describedBy }">
          <textarea id="lab-cancel-reason" v-model="cancelReason" rows="3" maxlength="2000" required :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="cancelTarget = null">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="lab-cancel-form" variant="danger" :disabled="busy" :loading="busy">{{ t('labStock.cancel_request') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { requestOriginLabel, requestStatusLabel, levelLabel } from '@/utils/labStockLabels';
import { todayLocalISO } from '@/utils/localDate';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const authStore = useAuthStore();
const STATUSES = ['a_commander', 'commande', 'recu', 'annule'];

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'product', label: t('labStock.col_product') },
  { key: 'stock', label: t('labStock.col_stock'), align: 'right' },
  { key: 'threshold', label: t('labStock.col_threshold'), align: 'right' },
  { key: 'origin', label: t('labStock.col_origin') },
  { key: 'status', label: t('labStock.col_status') },
  { key: 'expected', label: t('labStock.col_expected') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const canOrder = computed(() => authStore.hasRole(['promoteur', 'ToxicoManager', 'admin']));

const requests = ref([]);
const statusFilter = ref('open');
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const modalError = ref('');
const busy = ref(false);
const today = todayLocalISO();

const orderTarget = ref(null);
const orderIsEdit = ref(false);
const orderDate = ref('');
const cancelTarget = ref(null);
const cancelReason = ref('');

const visible = computed(() => {
  const f = statusFilter.value;
  if (f === 'all') return requests.value;
  if (f === 'open') return requests.value.filter(isOpen);
  return requests.value.filter((r) => r.status === f);
});

let msgTimer = null;
const flash = (msg) => {
  pageMessage.value = msg;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { pageMessage.value = ''; }, 5000);
};
onBeforeUnmount(() => clearTimeout(msgTimer));

const num = (v) => Number(v ?? 0);
const isLow = (r) => num(r.quantity) <= num(r.alert_threshold);
const isOpen = (r) => r.status === 'a_commander' || r.status === 'commande';
const labelOf = (l) => (l.key ? t(l.key) : l.raw);
const formatDate = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString() : '');
const originText = (r) => {
  const base = labelOf(requestOriginLabel(r.origin));
  const lv = r.level ? labelOf(levelLabel(r.level)) : '';
  return lv ? `${base} (${lv})` : base;
};
const badge = (s) => ({
  a_commander: 'warning',
  commande: 'info',
  recu: 'success',
  annule: 'neutral',
}[s] || 'neutral');

const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    requests.value = await LabStockGateway.listRequests();
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement des demandes du labo echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const openOrder = (r, isEdit) => {
  pageMessage.value = '';
  orderTarget.value = r;
  orderIsEdit.value = isEdit;
  orderDate.value = isEdit && r.expected_date ? String(r.expected_date).slice(0, 10) : '';
  modalError.value = '';
};

const confirmOrder = async () => {
  modalError.value = '';
  if (!orderDate.value) { modalError.value = t('labStock.err_date_required'); return; }
  if (orderDate.value < today) { modalError.value = t('labStock.err_date_past'); return; }
  busy.value = true;
  try {
    if (orderIsEdit.value) await LabStockGateway.updateExpectedDate(orderTarget.value.id, orderDate.value);
    else await LabStockGateway.markOrdered(orderTarget.value.id, orderDate.value);
    orderTarget.value = null;
    flash(t('labStock.order_saved'));
    await load();
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Commande echouee :', err);
  } finally {
    busy.value = false;
  }
};

const openCancel = (r) => { pageMessage.value = ''; cancelTarget.value = r; cancelReason.value = ''; modalError.value = ''; };

const confirmCancel = async () => {
  modalError.value = '';
  const reason = cancelReason.value.trim();
  if (!reason) { modalError.value = t('labStock.err_reason_required'); return; }
  busy.value = true;
  try {
    await LabStockGateway.cancelRequest(cancelTarget.value.id, reason);
    cancelTarget.value = null;
    flash(t('labStock.request_cancelled'));
    await load();
  } catch (err) {
    modalError.value = describeLabStockError(err, t('stockOps.error_save'));
    console.error('Annulation echouee :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(load);
</script>
