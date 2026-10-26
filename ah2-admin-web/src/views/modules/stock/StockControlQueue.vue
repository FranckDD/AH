<!-- src/views/modules/stock/StockControlQueue.vue -->
<!-- File "A controler" : receptions et avaries en attente de controle (StockController / admin). -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="$t('stockControl.title')">
      <template #actions>
        <AppButton variant="secondary" :icon="ArrowPathIcon" @click="loadAll">{{ $t('stockControl.refresh') }}</AppButton>
      </template>
    </PageHeader>

    <div role="tablist" :aria-label="$t('stockAdminScreens.tabs_label')" class="flex flex-col gap-1 border-b border-tone-neutral-border sm:flex-row sm:gap-2">
      <button v-for="tb in TABS" :key="tb" type="button" role="tab" :aria-selected="tab === tb" @click="tab = tb"
              :class="[
                tab === tb ? 'border-brand-600 text-brand-700 font-semibold' : 'border-transparent text-ink-muted hover:border-tone-neutral-border hover:text-ink',
                'flex min-h-11 items-center border-b-4 px-3 text-base focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600'
              ]">
        {{ $t(`stockControl.tab_${tb}`) }} ({{ loadFailed ? '-' : (tb === 'receipts' ? receipts.length : incidents.length) }})
      </button>
    </div>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>
    <p v-if="isLoading" role="status" class="py-6 text-center text-base text-ink-muted">{{ $t('stockOps.loading') }}</p>

    <!-- RECEPTIONS -->
    <section v-else-if="tab === 'receipts'" class="grid gap-4 lg:grid-cols-3">
      <div class="grid content-start gap-2 rounded-card border border-tone-neutral-border bg-white p-3 shadow-card lg:col-span-1" role="group" :aria-label="$t('stockAdminScreens.receipts_list_label')">
        <p v-if="receipts.length === 0" class="p-2 text-base text-ink-muted">{{ $t('stockControl.empty_receipts') }}</p>
        <button v-for="r in receipts" :key="r.id" type="button" @click="selectReceipt(r)" :aria-pressed="selected?.id === r.id"
                class="min-h-11 w-full rounded-control border px-3 py-2 text-left text-base focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600"
                :class="selected?.id === r.id ? 'border-brand-600 bg-brand-50' : 'border-tone-neutral-border hover:bg-tone-neutral-bg'">
          <span class="block font-medium text-ink">{{ r.receipt_number || ('#' + r.id) }}</span>
          <span class="block text-base text-ink-muted">
            {{ r.received_date }}, {{ $t(`stockOps.origin.${r.origin}`) }}, {{ r.lines.length }} {{ $t('stockControl.lines') }}
          </span>
          <span v-if="isMine(r)" class="block text-base font-medium text-tone-warning-text">{{ $t('stockControl.own_entry') }}</span>
        </button>
      </div>

      <div class="grid content-start gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card lg:col-span-2 md:p-5">
        <p v-if="!selected" class="text-base text-ink-muted">{{ $t('stockControl.select_hint') }}</p>
        <template v-else>
          <div class="grid gap-1 text-base text-ink">
            <p class="text-lg font-semibold">{{ selected.receipt_number || ('#' + selected.id) }}</p>
            <p>{{ $t('stockOps.col_origin') }} : {{ $t(`stockOps.origin.${selected.origin}`) }}</p>
            <p v-if="selected.supplier">{{ $t('stockOps.col_supplier') }} : {{ selected.supplier }}</p>
            <p v-if="selected.delivery_ref">{{ $t('stockOps.col_delivery_ref') }} : {{ selected.delivery_ref }}</p>
            <p>{{ $t('stockOps.col_received_date') }} : {{ selected.received_date }}</p>
            <p>{{ $t('stockControl.entered_by') }} : {{ actorLabel(selected.created_by_name, selected.created_by) }}</p>
          </div>

          <ResponsiveTable :columns="lineColumns" :rows="editLines" row-key="id" :empty-title="$t('stockControl.empty_receipts')" :empty-message="' '" striped>
            <template #cell-product="{ row: l }">
              <span class="font-medium">{{ l.product_name }}</span>
              <span v-if="l.lot_number || l.expiry_date" class="block text-base text-ink-muted">
                {{ l.lot_number }} {{ l.expiry_date ? ', ' + l.expiry_date : '' }}
              </span>
              <span v-if="lineErrors[editLines.indexOf(l)]" role="alert" class="mt-1 block text-base text-tone-danger-text">{{ $t(`stockOps.line_error_${lineErrors[editLines.indexOf(l)]}`) }}</span>
            </template>
            <template #cell-expected="{ row: l }">{{ l.qty_expected ?? '-' }}</template>
            <template v-for="f in QTY_FIELDS" :key="f" #[qtySlot(f)]="{ row: l }">
              <input v-if="canDecide" v-model.number="l[f]" type="number" min="0" step="1" inputmode="numeric" @input="clearLineError(l)"
                     :aria-label="$t(`stockOps.${f}`)" :class="[fieldClass, 'w-24 text-right']" />
              <span v-else>{{ l[f] }}</span>
            </template>
            <template #cell-total="{ row: l }"><span class="font-bold">{{ lineTotal(l) }}</span></template>
          </ResponsiveTable>

          <p v-if="!canDecide" class="rounded-control border p-3 text-base" :class="toneClasses('warning')">{{ $t('stockControl.own_entry_help') }}</p>
          <div v-else class="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <AppButton v-if="linesDirty" variant="secondary" @click="saveLines" :disabled="busy">{{ $t('stockControl.save_corrections') }}</AppButton>
            <AppButton variant="danger" @click="openReject('receipt', selected)" :disabled="busy">{{ $t('stockControl.reject') }}</AppButton>
            <AppButton variant="success" @click="validateReceipt" :disabled="busy">{{ $t('stockControl.validate') }}</AppButton>
          </div>
        </template>
      </div>
    </section>

    <!-- AVARIES -->
    <section v-else class="grid gap-3">
      <ResponsiveTable :columns="incidentColumns" :rows="incidents" row-key="id" :empty-title="$t('stockControl.empty_incidents')" :empty-message="' '" striped>
        <template #cell-date="{ row: inc }">{{ inc.incident_date }}</template>
        <template #cell-product="{ row: inc }">{{ inc.product_name }}</template>
        <template #cell-kind="{ row: inc }">{{ $t(`stockOps.kind.${inc.kind}`) }}</template>
        <template #cell-quantity="{ row: inc }"><span class="font-semibold">{{ inc.quantity }}</span></template>
        <template #cell-reason="{ row: inc }"><span class="block max-w-xs">{{ inc.reason }}</span></template>
        <template #cell-by="{ row: inc }">{{ actorLabel(inc.created_by_name, inc.created_by) }}</template>
        <template #actions="{ row: inc }">
          <span v-if="isMine(inc)" class="text-base font-medium text-tone-warning-text">{{ $t('stockControl.own_entry') }}</span>
          <template v-else>
            <AppButton variant="success" @click="validateIncident(inc)" :disabled="busy">{{ $t('stockControl.validate') }}</AppButton>
            <AppButton variant="danger" @click="openReject('incident', inc)" :disabled="busy">{{ $t('stockControl.reject') }}</AppButton>
          </template>
        </template>
      </ResponsiveTable>
    </section>

    <!-- Motif de rejet -->
    <FullScreenPanel v-if="rejectTarget" :title="$t('stockControl.reject_title')" @close="rejectTarget = null">
      <form id="reject-form" @submit.prevent="confirmReject" class="grid gap-4">
        <p v-if="rejectError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ rejectError }}</p>
        <FormField id="reject-reason" :label="$t('stockOps.reject_reason')" required v-slot="{ describedBy }">
          <textarea id="reject-reason" v-model="rejectReason" rows="3" maxlength="2000" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="rejectTarget = null">{{ $t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="reject-form" variant="danger" :disabled="busy" :loading="busy">{{ $t('stockControl.reject') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { actorLabel } from '@/utils/actorName';
import { describeStockLineError } from '@/utils/stockLineError';
import { QTY_FIELDS, lineTotal, validateReceiptLine } from '@/utils/receiptLines';
import { ArrowPathIcon } from '@heroicons/vue/24/outline';
import { AppButton, PageHeader, FormField, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t, te } = useI18n();
const authStore = useAuthStore();
const TABS = ['receipts', 'incidents'];

// Colonnes des tableaux (cartes empilees sous lg) et style commun des champs. Une colonne par champ de quantite.
const lineColumns = computed(() => [
  { key: 'product', label: t('stockOps.col_product') },
  { key: 'expected', label: t('stockOps.col_expected'), align: 'right' },
  ...QTY_FIELDS.map((f) => ({ key: f, label: t(`stockOps.${f}`), align: 'right' })),
  { key: 'total', label: t('stockOps.line_total'), align: 'right' },
]);
const qtySlot = (f) => `cell-${f}`;
const incidentColumns = computed(() => [
  { key: 'date', label: t('stockOps.col_date') },
  { key: 'product', label: t('stockOps.col_product') },
  { key: 'kind', label: t('stockOps.col_kind') },
  { key: 'quantity', label: t('stockOps.col_quantity'), align: 'right' },
  { key: 'reason', label: t('stockOps.col_reason') },
  { key: 'by', label: t('stockControl.entered_by') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const tab = ref('receipts');
const receipts = ref([]);
const incidents = ref([]);
const selected = ref(null);
const editLines = ref([]);
const lineErrors = ref([]);
const isLoading = ref(false);
const busy = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const rejectTarget = ref(null);
const rejectReason = ref('');
const rejectError = ref('');

// authStore.user.id = user_id (GET /auth/me). Le serveur refuse de toute
// facon (403) le controle de sa propre saisie ; on masque juste les boutons.
const myId = computed(() => authStore.user?.id ?? null);
const isMine = (item) => myId.value !== null && item?.created_by === myId.value;
const canDecide = computed(() => !!selected.value && !isMine(selected.value));

const linesDirty = computed(() => {
  if (!selected.value) return false;
  return editLines.value.some((l, i) => QTY_FIELDS.some((f) => l[f] !== selected.value.lines[i]?.[f]));
});

const resetMessages = () => { pageError.value = ''; pageMessage.value = ''; };

const loadFailed = ref(false); // file non chargee : les compteurs des onglets affichent "-", jamais (0)
const loadAll = async () => {
  isLoading.value = true;
  pageError.value = '';
  loadFailed.value = false;
  try {
    const [r, i] = await Promise.all([
      StockOpsGateway.listReceipts({ status: 'a_controler' }),
      StockOpsGateway.listIncidents({ status: 'a_controler' }),
    ]);
    receipts.value = r || [];
    incidents.value = i || [];
    if (selected.value) {
      const again = receipts.value.find((x) => x.id === selected.value.id);
      if (again) selectReceipt(again); else { selected.value = null; editLines.value = []; }
    }
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_load'));
    loadFailed.value = true;
    console.error('Chargement de la file de controle echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const selectReceipt = (r) => {
  selected.value = r;
  editLines.value = r.lines.map((l) => ({ ...l }));
  lineErrors.value = [];
};

// La remarque d'une ligne disparait des que sa valeur est modifiee (elle est recalculee a la prochaine validation).
const clearLineError = (l) => {
  const i = editLines.value.indexOf(l);
  if (i >= 0 && lineErrors.value[i]) lineErrors.value[i] = null;
};

// Refus serveur sur une ligne : code traduit + produit de la ligne ; sinon le message du serveur.
const serverMessage = (err) => describeStockLineError(err, editLines.value, t, te) || describeStockError(err, t('stockOps.error_save'));

const checkLines = () => {
  lineErrors.value = editLines.value.map((l) => {
    const res = validateReceiptLine(l);
    return res.ok ? null : res.error;
  });
  return lineErrors.value.every((e) => !e);
};

const pushCorrections = async () => {
  const changed = editLines.value
    .filter((l, i) => QTY_FIELDS.some((f) => l[f] !== selected.value.lines[i]?.[f]))
    .map((l) => ({ id: l.id, ...Object.fromEntries(QTY_FIELDS.map((f) => [f, l[f]])) }));
  if (changed.length) await StockOpsGateway.updateReceiptLines(selected.value.id, changed);
};

const saveLines = async () => {
  resetMessages();
  if (!checkLines()) return;
  busy.value = true;
  try {
    await pushCorrections();
    pageMessage.value = t('stockControl.corrections_saved');
    await loadAll();
  } catch (err) {
    pageError.value = serverMessage(err);
    console.error('Correction des lignes echouee :', err);
  } finally {
    busy.value = false;
  }
};

const validateReceipt = async () => {
  resetMessages();
  if (!checkLines()) return;
  if (!window.confirm(t('stockControl.confirm_validate'))) return;
  busy.value = true;
  try {
    if (linesDirty.value) await pushCorrections();
    await StockOpsGateway.validateReceipt(selected.value.id);
    pageMessage.value = t('stockControl.validated');
    selected.value = null;
    editLines.value = [];
    await loadAll();
  } catch (err) {
    pageError.value = serverMessage(err);
    console.error('Validation de la reception echouee :', err);
  } finally {
    busy.value = false;
  }
};

const validateIncident = async (inc) => {
  resetMessages();
  if (!window.confirm(t('stockControl.confirm_validate'))) return;
  busy.value = true;
  try {
    await StockOpsGateway.validateIncident(inc.id);
    pageMessage.value = t('stockControl.validated');
    await loadAll();
  } catch (err) {
    pageError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Validation de l\'avarie echouee :', err);
  } finally {
    busy.value = false;
  }
};

const openReject = (kind, item) => {
  rejectTarget.value = { kind, id: item.id };
  rejectReason.value = '';
  rejectError.value = '';
};

const confirmReject = async () => {
  rejectError.value = '';
  const reason = rejectReason.value.trim();
  if (!reason) { rejectError.value = t('stockOps.err_reason_required'); return; }
  busy.value = true;
  try {
    const { kind, id } = rejectTarget.value;
    if (kind === 'receipt') await StockOpsGateway.rejectReceipt(id, reason);
    else await StockOpsGateway.rejectIncident(id, reason);
    rejectTarget.value = null;
    resetMessages();
    pageMessage.value = t('stockControl.rejected');
    if (kind === 'receipt') { selected.value = null; editLines.value = []; }
    await loadAll();
  } catch (err) {
    rejectError.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Rejet echoue :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(loadAll);
</script>
