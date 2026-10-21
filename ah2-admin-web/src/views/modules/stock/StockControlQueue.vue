<!-- src/views/modules/stock/StockControlQueue.vue -->
<!-- File "A controler" : receptions et avaries en attente de controle (StockController / admin). -->
<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-xl font-bold text-gray-800">{{ $t('stockControl.title') }}</h2>
      <button type="button" @click="loadAll" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">
        {{ $t('stockControl.refresh') }}
      </button>
    </div>

    <div class="flex gap-2 border-b border-gray-200">
      <button v-for="tb in TABS" :key="tb" type="button" @click="tab = tb"
              class="px-4 py-2 text-sm font-medium -mb-px border-b-2"
              :class="tab === tb ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-700'">
        {{ $t(`stockControl.tab_${tb}`) }} ({{ tb === 'receipts' ? receipts.length : incidents.length }})
      </button>
    </div>

    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>
    <div v-if="isLoading" class="text-sm text-gray-400">{{ $t('stockOps.loading') }}</div>

    <!-- RECEPTIONS -->
    <section v-else-if="tab === 'receipts'" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="bg-white rounded-xl shadow-xs border border-gray-200 p-3 space-y-1 lg:col-span-1">
        <div v-if="receipts.length === 0" class="text-sm text-gray-400 p-2">{{ $t('stockControl.empty_receipts') }}</div>
        <button v-for="r in receipts" :key="r.id" type="button" @click="selectReceipt(r)"
                class="w-full text-left px-3 py-2 rounded-lg text-sm"
                :class="selected?.id === r.id ? 'bg-emerald-50 border border-emerald-200' : 'hover:bg-gray-50'">
          <div class="font-medium text-gray-800">{{ r.receipt_number || ('#' + r.id) }}</div>
          <div class="text-xs text-gray-500">
            {{ r.received_date }} · {{ $t(`stockOps.origin.${r.origin}`) }} · {{ r.lines.length }} {{ $t('stockControl.lines') }}
          </div>
          <div v-if="isMine(r)" class="text-xs text-amber-700">{{ $t('stockControl.own_entry') }}</div>
        </button>
      </div>

      <div class="bg-white rounded-xl shadow-xs border border-gray-200 p-5 lg:col-span-2 space-y-4">
        <div v-if="!selected" class="text-sm text-gray-400">{{ $t('stockControl.select_hint') }}</div>
        <template v-else>
          <div class="text-sm text-gray-700 space-y-1">
            <div class="font-semibold text-gray-800">{{ selected.receipt_number || ('#' + selected.id) }}</div>
            <div>{{ $t('stockOps.col_origin') }} : {{ $t(`stockOps.origin.${selected.origin}`) }}</div>
            <div v-if="selected.supplier">{{ $t('stockOps.col_supplier') }} : {{ selected.supplier }}</div>
            <div v-if="selected.delivery_ref">{{ $t('stockOps.col_delivery_ref') }} : {{ selected.delivery_ref }}</div>
            <div>{{ $t('stockOps.col_received_date') }} : {{ selected.received_date }}</div>
            <div>{{ $t('stockControl.entered_by') }} : {{ actorLabel(selected.created_by_name, selected.created_by) }}</div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-xs text-gray-500 uppercase border-b">
                  <th class="py-2">{{ $t('stockOps.col_product') }}</th>
                  <th class="py-2">{{ $t('stockOps.col_expected') }}</th>
                  <th v-for="f in QTY_FIELDS" :key="f" class="py-2">{{ $t(`stockOps.${f}`) }}</th>
                  <th class="py-2">{{ $t('stockOps.line_total') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(l, i) in editLines" :key="l.id" class="border-b last:border-0 align-top">
                  <td class="py-2">
                    {{ l.product_name }}
                    <div v-if="l.lot_number || l.expiry_date" class="text-xs text-gray-500">
                      {{ l.lot_number }} {{ l.expiry_date ? '· ' + l.expiry_date : '' }}
                    </div>
                    <div v-if="lineErrors[i]" class="text-xs text-red-700 mt-1">{{ $t(`stockOps.line_error_${lineErrors[i]}`) }}</div>
                  </td>
                  <td class="py-2">{{ l.qty_expected ?? '—' }}</td>
                  <td v-for="f in QTY_FIELDS" :key="f" class="py-2 pr-2">
                    <input v-if="canDecide" v-model.number="l[f]" type="number" min="0" step="1"
                           class="w-20 px-2 py-1 border border-gray-300 rounded-sm" />
                    <span v-else>{{ l[f] }}</span>
                  </td>
                  <td class="py-2 font-medium">{{ lineTotal(l) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="!canDecide" class="text-sm text-amber-700">{{ $t('stockControl.own_entry_help') }}</div>
          <div v-else class="flex flex-wrap justify-end gap-2">
            <button v-if="linesDirty" type="button" @click="saveLines" :disabled="busy"
                    class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg text-sm font-medium disabled:opacity-50">{{ $t('stockControl.save_corrections') }}</button>
            <button type="button" @click="openReject('receipt', selected)" :disabled="busy"
                    class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ $t('stockControl.reject') }}</button>
            <button type="button" @click="validateReceipt" :disabled="busy"
                    class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ $t('stockControl.validate') }}</button>
          </div>
        </template>
      </div>
    </section>

    <!-- AVARIES -->
    <section v-else class="bg-white rounded-xl shadow-xs border border-gray-200 p-5 overflow-x-auto">
      <div v-if="incidents.length === 0" class="text-sm text-gray-400">{{ $t('stockControl.empty_incidents') }}</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 uppercase border-b">
            <th class="py-2">{{ $t('stockOps.col_date') }}</th>
            <th class="py-2">{{ $t('stockOps.col_product') }}</th>
            <th class="py-2">{{ $t('stockOps.col_kind') }}</th>
            <th class="py-2">{{ $t('stockOps.col_quantity') }}</th>
            <th class="py-2">{{ $t('stockOps.col_reason') }}</th>
            <th class="py-2">{{ $t('stockControl.entered_by') }}</th>
            <th class="py-2">{{ $t('stockOps.col_action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inc in incidents" :key="inc.id" class="border-b last:border-0 align-top">
            <td class="py-2">{{ inc.incident_date }}</td>
            <td class="py-2">{{ inc.product_name }}</td>
            <td class="py-2">{{ $t(`stockOps.kind.${inc.kind}`) }}</td>
            <td class="py-2">{{ inc.quantity }}</td>
            <td class="py-2 max-w-xs">{{ inc.reason }}</td>
            <td class="py-2">{{ actorLabel(inc.created_by_name, inc.created_by) }}</td>
            <td class="py-2 whitespace-nowrap">
              <span v-if="isMine(inc)" class="text-xs text-amber-700">{{ $t('stockControl.own_entry') }}</span>
              <template v-else>
                <button type="button" @click="validateIncident(inc)" :disabled="busy"
                        class="px-3 py-1 bg-green-600 text-white rounded-lg text-xs font-medium disabled:opacity-50 mr-1">{{ $t('stockControl.validate') }}</button>
                <button type="button" @click="openReject('incident', inc)" :disabled="busy"
                        class="px-3 py-1 bg-red-600 text-white rounded-lg text-xs font-medium disabled:opacity-50">{{ $t('stockControl.reject') }}</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Motif de rejet -->
    <div v-if="rejectTarget" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <form @submit.prevent="confirmReject" class="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ $t('stockControl.reject_title') }}</h3>
        <div v-if="rejectError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ rejectError }}</div>
        <label class="block text-sm">{{ $t('stockOps.reject_reason') }}
          <textarea v-model="rejectReason" rows="3" maxlength="2000" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"></textarea>
        </label>
        <div class="flex justify-end gap-2">
          <button type="button" @click="rejectTarget = null" class="px-4 py-2 bg-gray-200 rounded-lg text-sm">{{ $t('stockOps.close') }}</button>
          <button type="submit" :disabled="busy" class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{{ $t('stockControl.reject') }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { actorLabel } from '@/utils/actorName';
import { QTY_FIELDS, lineTotal, validateReceiptLine } from '@/utils/receiptLines';

const { t } = useI18n();
const authStore = useAuthStore();
const TABS = ['receipts', 'incidents'];

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

const loadAll = async () => {
  isLoading.value = true;
  pageError.value = '';
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
    pageError.value = describeStockError(err, t('stockOps.error_save'));
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
    pageError.value = describeStockError(err, t('stockOps.error_save'));
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
