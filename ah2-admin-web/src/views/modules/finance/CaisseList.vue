<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('caisse.title') }}</h1>
        <p class="text-sm text-gray-500">{{ caisseStore.pagination.total }} transactions</p>
      </div>
      <button @click="showInvoiceModal = true"
              class="flex items-center px-6 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 shadow-md shadow-green-200 transition font-semibold">
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('caisse.new_invoice') }}
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center">
        <div class="p-3 bg-green-50 rounded-full mr-4"><ArrowTrendingUpIcon class="h-8 w-8 text-green-600" /></div>
        <div>
          <p class="text-sm text-gray-500 font-medium uppercase">{{ t('finance.income') }}</p>
          <p class="text-2xl font-bold text-gray-900">{{ kpiAffiche(formatCurrency(caisseStore.kpi.total_paid)) }}</p>
        </div>
      </div>
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center">
        <div class="p-3 bg-amber-50 rounded-full mr-4"><ClockIcon class="h-8 w-8 text-amber-600" /></div>
        <div>
          <p class="text-sm text-gray-500 font-medium uppercase">{{ t('caisse.table.due') }}</p>
          <p class="text-2xl font-bold text-gray-900">{{ kpiAffiche(formatCurrency(caisseStore.kpi.remaining_due)) }}</p>
        </div>
      </div>
      <div class="bg-gradient-to-r from-gray-800 to-gray-900 p-6 rounded-2xl shadow-lg text-white flex items-center justify-between">
        <div>
          <p class="text-sm text-gray-400 font-medium uppercase">Transactions</p>
          <p class="text-3xl font-bold text-white">{{ kpiAffiche(caisseStore.kpi.total_transactions) }}</p>
        </div>
        <BanknotesIcon class="h-10 w-10 text-gray-500 opacity-50" />
      </div>
    </div>

    <div v-if="pendingApprovalCount > 0 && statusFilter !== 'pending_approval'"
         class="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-xl flex items-center justify-between cursor-pointer hover:bg-amber-100 transition"
         @click="statusFilter = 'pending_approval'">
      <p class="text-sm text-amber-800 font-medium">{{ t('caisse.pending_banner', { count: pendingApprovalCount }) }}</p>
      <span class="text-xs text-amber-600 underline">{{ t('caisse.status.pending_approval') }}</span>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">
      <div class="flex-1 min-w-[200px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Recherche</label>
        <input v-model="searchQuery" type="text" :placeholder="t('caisse.search_placeholder')"
               class="block w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-green-500 focus:border-green-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Du</label>
        <input v-model="startDate" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Au</label>
        <input v-model="endDate" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('caisse.table.status') }}</label>
        <select v-model="statusFilter" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm">
          <option value="active">{{ t('caisse.status.active') }}</option>
          <option value="pending_approval">{{ t('caisse.status.pending_approval') }}</option>
          <option value="cancelled">{{ t('caisse.status.cancelled') }}</option>
          <option value="refunded">{{ t('caisse.status.refunded') }}</option>
          <option value="">{{ t('caisse.status.all') }}</option>
        </select>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="caisseStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></span>
      </div>
      <div v-else-if="caisseStore.loadError" class="p-10 text-center text-red-500">Erreur de chargement</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.type') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('caisse.table.total') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('caisse.table.paid') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('caisse.table.due') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.status') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('caisse.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="tx in caisseStore.transactions" :key="tx.transaction_id || tx.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(tx.paid_at) }}</td>
              <td class="px-6 py-4 text-sm text-gray-900">{{ tx.patient_name || '—' }}</td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                  {{ tx.transaction_type }}
                </span>
              </td>
              <td class="px-6 py-4 text-right font-bold text-sm">{{ formatCurrency(tx.amount) }}</td>
              <td class="px-6 py-4 text-right text-sm text-green-700">{{ formatCurrency(tx.amount_paid) }}</td>
              <td class="px-6 py-4 text-right text-sm" :class="Number(tx.amount_due) > 0 ? 'text-red-600 font-semibold' : 'text-gray-400'">
                {{ formatCurrency(tx.amount_due) }}
              </td>
              <td class="px-6 py-4">
                <span v-if="tx.status === 'active'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  {{ t('caisse.status.active') }}
                </span>
                <span v-else-if="tx.status === 'pending_approval'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                  {{ t('caisse.status.pending_approval') }}
                </span>
                <span v-else-if="tx.status === 'refunded'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                  {{ t('caisse.status.refunded') }}
                </span>
                <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                  {{ t('caisse.status.cancelled') }}
                </span>
                <span v-if="tx.upload_error" :title="tx.upload_error"
                      class="ml-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                  Échec de synchronisation
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center justify-end gap-1.5">
                  <button @click="openViewModal(tx)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-100 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.view') : 'En attente de synchronisation'">
                    <EyeIcon class="h-4 w-4" />
                  </button>
                  <button v-if="tx.status === 'active' && Number(tx.amount_due) > 0" @click="openInstallmentModal(tx)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-green-600 hover:bg-green-50 hover:border-green-200 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.add_payment') : 'En attente de synchronisation'">
                    <CurrencyDollarIcon class="h-4 w-4" />
                  </button>
                  <button v-if="tx.status === 'active' && Number(tx.amount_due) > 0" @click="handleSettle(tx)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.settle') : 'En attente de synchronisation'">
                    <CheckBadgeIcon class="h-4 w-4" />
                  </button>
                  <button v-if="tx.status === 'active'" @click="openCancelModal(tx)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-red-500 hover:bg-red-50 hover:border-red-200 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.cancel') : 'En attente de synchronisation'">
                    <XCircleIcon class="h-4 w-4" />
                  </button>
                  <button @click="downloadInvoice(tx)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-100 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.download') : 'En attente de synchronisation'">
                    <ArrowDownTrayIcon class="h-4 w-4" />
                  </button>
                  <button v-if="tx.status === 'active'" @click="printTicketForTransaction(tx.transaction_id)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-100 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.reprint_ticket') : 'En attente de synchronisation'">
                    <PrinterIcon class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="caisseStore.transactions.length === 0">
              <td colspan="8" class="px-6 py-8 text-center text-gray-500 italic">Aucune transaction trouvée.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="caisseStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">Page {{ caisseStore.pagination.page }} sur {{ caisseStore.pagination.total_pages }}</p>
        <div class="flex space-x-2">
          <button @click="goToPage(caisseStore.pagination.page - 1)" :disabled="caisseStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(caisseStore.pagination.page + 1)" :disabled="caisseStore.pagination.page === caisseStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>

    <div v-if="actionError" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-xl">
      <p class="text-sm text-red-700">{{ actionError }}</p>
    </div>

    <div v-if="printError" class="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-xl">
      <p class="text-sm text-amber-700">{{ printError }}</p>
    </div>

    <CaisseInvoiceModal v-if="showInvoiceModal" :isSaving="isSavingInvoice" :errorMessage="invoiceError"
                         @close="showInvoiceModal = false" @save="handleCreateInvoice"
                         @discount-requested="() => { caisseStore.fetchTransactions(); fetchPendingApprovalCount(); }" />

    <CaisseInstallmentModal v-if="installmentTx" :remainingDue="Number(installmentTx.amount_due)"
                             :isSaving="isSavingInstallment" :errorMessage="installmentError"
                             @close="installmentTx = null" @confirm="handleAddPayment" />

    <CaisseCancelModal v-if="cancellingTx" :isSaving="isCancelling" :errorMessage="cancelError"
                        :label="`Facture ${cancellingTx.transaction_id} — ${formatCurrency(cancellingTx.amount)}`"
                        @close="cancellingTx = null" @confirm="handleCancel" />

    <div v-if="viewingTx" class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
      <div class="relative mx-auto w-full max-w-2xl bg-white shadow-xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
        <div class="px-6 py-4 border-b border-gray-100 bg-gray-700 rounded-t-2xl flex justify-between items-center flex-shrink-0">
          <h3 class="text-lg font-bold text-white">{{ t('caisse.actions.view') }} — {{ viewingTx.patient_name || viewingTx.transaction_id }}</h3>
          <button @click="viewingTx = null" class="text-gray-200 hover:text-white transition">
            <span class="text-2xl font-bold">&times;</span>
          </button>
        </div>
        <div class="p-6 overflow-y-auto space-y-4">
          <div v-if="viewLoading" class="text-center py-6">
            <span class="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-gray-600"></span>
          </div>
          <div v-else-if="viewError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">{{ viewError }}</div>
          <div v-else>
            <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">{{ t('caisse.invoice_modal.section_items') }}</h4>
            <table class="min-w-full text-left border-collapse text-sm">
              <thead>
                <tr class="bg-gray-50 text-gray-500 text-xs uppercase">
                  <th class="px-3 py-2">{{ t('caisse.table.type') }}</th>
                  <th class="px-3 py-2 text-right">{{ t('caisse.invoice_modal.quantity') }}</th>
                  <th class="px-3 py-2 text-right">{{ t('caisse.invoice_modal.unit_price') }}</th>
                  <th class="px-3 py-2 text-right">{{ t('caisse.invoice_modal.line_total') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="item in viewingItems" :key="item.item_id">
                  <td class="px-3 py-2">{{ item.note || item.item_type }}</td>
                  <td class="px-3 py-2 text-right">{{ item.quantity }}</td>
                  <td class="px-3 py-2 text-right">{{ formatCurrency(item.unit_price) }}</td>
                  <td class="px-3 py-2 text-right font-semibold">{{ formatCurrency(item.line_total) }}</td>
                </tr>
                <tr v-if="viewingItems.length === 0">
                  <td colspan="4" class="px-3 py-4 text-center text-gray-400 italic">{{ t('caisse.invoice_modal.no_lines') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useCaisseStore } from '@/stores/caisseStore';
import api from '@/services/api';
import CaisseInvoiceModal from '@/components/caisse/CaisseInvoiceModal.vue';
import CaisseInstallmentModal from '@/components/caisse/CaisseInstallmentModal.vue';
import CaisseCancelModal from '@/components/caisse/CaisseCancelModal.vue';
import {
  PlusCircleIcon, ArrowTrendingUpIcon, ClockIcon, BanknotesIcon,
  ChevronLeftIcon, ChevronRightIcon, CurrencyDollarIcon, CheckBadgeIcon,
  XCircleIcon, ArrowDownTrayIcon, EyeIcon, PrinterIcon,
} from '@heroicons/vue/24/outline';
import { CaisseGateway } from '@/services/CaisseGateway';
import { PrinterBridgeGateway } from '@/services/PrinterBridgeGateway';

const { t } = useI18n();
const caisseStore = useCaisseStore();

// Compteur independant du filtre courant - residu documente au chantier
// notifications ("factures en attente invisibles/mal etiquetees dans le
// filtre par defaut") : sans ca, une secretaire qui reste sur le filtre
// 'active' par defaut ne voit jamais qu'une reduction est en attente.
const pendingApprovalCount = ref(0);
const fetchPendingApprovalCount = async () => {
  try {
    const resp = await CaisseGateway.fetchTransactions({ status: 'pending_approval', page: 1, per_page: 1 });
    pendingApprovalCount.value = resp.data.total || 0;
  } catch {
    pendingApprovalCount.value = 0;
  }
};

onMounted(() => {
  caisseStore.fetchTransactions();
  fetchPendingApprovalCount();
});

const searchQuery = computed({
  get: () => caisseStore.filters.searchQuery,
  set: (val) => caisseStore.setFilters({ searchQuery: val }),
});
const startDate = computed({
  get: () => caisseStore.filters.startDate,
  set: (val) => caisseStore.setFilters({ startDate: val }),
});
const endDate = computed({
  get: () => caisseStore.filters.endDate,
  set: (val) => caisseStore.setFilters({ endDate: val }),
});
const statusFilter = computed({
  get: () => caisseStore.filters.status,
  set: (val) => caisseStore.setFilters({ status: val }),
});

const goToPage = (page) => caisseStore.setPage(page);

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value || 0).replace('XOF', 'FCFA');
const formatDate = (iso) => (iso ? String(iso).split('T')[0] : '');
const kpiAffiche = (value) => (caisseStore.kpiError ? 'Indisponible' : value);

const actionError = ref('');
const mapErrorToMessage = (err) => {
  if (err.response) {
    const status = err.response.status;
    const detail = err.response.data?.detail;
    if (status === 422) return "Données invalides.";
    if (status === 400) return detail || "Requête invalide.";
    return `Erreur serveur (${status}) : ${detail || 'veuillez réessayer'}`;
  }
  if (err.request) return "Erreur réseau. Veuillez vérifier votre connexion.";
  return err.message || "Une erreur inattendue est survenue.";
};

// --- Impression ticket ---
// Impression automatique et best-effort : ne doit jamais bloquer ni
// interferer avec le flux de creation/reimpression de facture, qui a
// deja reussi cote donnees au moment ou on imprime. Declenchee pour
// TOUTE facture qui atteint le statut 'active', qu'une reduction ait
// ete demandee ou non (voir Tache 12) - jamais conditionnee par autre
// chose, pour ne pas rouvrir la faille anti-fraude (facture encaissee
// sans ticket physique puis annulee discretement).
const printError = ref('');

const printTicketForTransaction = async (transactionId) => {
  printError.value = '';
  try {
    const resp = await CaisseGateway.getTicket(transactionId);
    await PrinterBridgeGateway.printTicket(resp.data);
  } catch (err) {
    printError.value = "Ticket non imprimé — imprimante indisponible. Utilisez le bouton Réimprimer pour réessayer.";
    console.error('Erreur impression ticket:', err);
  }
};

// --- Creation facture ---
const showInvoiceModal = ref(false);
const isSavingInvoice = ref(false);
const invoiceError = ref('');

const handleCreateInvoice = async (payload) => {
  isSavingInvoice.value = true;
  invoiceError.value = '';
  try {
    const result = await caisseStore.createInvoice(payload);
    showInvoiceModal.value = false;
    if (result && result.status !== 'pending_approval' && result.transaction_id) {
      printTicketForTransaction(result.transaction_id);
    }
  } catch (err) {
    invoiceError.value = mapErrorToMessage(err);
  } finally {
    isSavingInvoice.value = false;
  }
};

// --- Versement ---
const installmentTx = ref(null);
const isSavingInstallment = ref(false);
const installmentError = ref('');

const openInstallmentModal = (tx) => {
  installmentTx.value = tx;
  installmentError.value = '';
};

const handleAddPayment = async (data) => {
  isSavingInstallment.value = true;
  installmentError.value = '';
  try {
    await caisseStore.addPayment(installmentTx.value.transaction_id, data);
    installmentTx.value = null;
  } catch (err) {
    installmentError.value = mapErrorToMessage(err);
  } finally {
    isSavingInstallment.value = false;
  }
};

// --- Solde ---
const handleSettle = async (tx) => {
  actionError.value = '';
  try {
    await caisseStore.settleTransaction(tx);
  } catch (err) {
    actionError.value = mapErrorToMessage(err);
  }
};

// --- Annulation ---
const cancellingTx = ref(null);
const isCancelling = ref(false);
const cancelError = ref('');

const openCancelModal = (tx) => {
  cancellingTx.value = tx;
  cancelError.value = '';
};

const handleCancel = async (justification) => {
  isCancelling.value = true;
  cancelError.value = '';
  try {
    await caisseStore.cancelTransaction(cancellingTx.value.transaction_id, justification);
    cancellingTx.value = null;
  } catch (err) {
    cancelError.value = mapErrorToMessage(err);
  } finally {
    isCancelling.value = false;
  }
};

// --- Téléchargement facture ---
const downloadInvoice = async (tx) => {
  actionError.value = '';
  try {
    const resp = await api.get(`/caisse/${tx.transaction_id}/invoice/download`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `facture_${tx.transaction_id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    // le backend renvoie deja le vrai motif ("en attente de validation
    // d'une reduction") en JSON, mais responseType:'blob' le recoit comme
    // un Blob binaire, pas un objet - il faut le decoder explicitement,
    // sinon err.response.data.detail est toujours undefined et le message
    // generique masque la vraie cause (residu documente au chantier
    // notifications).
    let detail = null;
    if (err.response?.data instanceof Blob) {
      try {
        const text = await err.response.data.text();
        detail = JSON.parse(text)?.detail;
      } catch {
        detail = null;
      }
    } else {
      detail = err.response?.data?.detail;
    }
    actionError.value = detail || "Impossible de télécharger la facture.";
  }
};

// --- Détail facture ---
const viewingTx = ref(null);
const viewingItems = ref([]);
const viewLoading = ref(false);
const viewError = ref('');

const openViewModal = async (tx) => {
  viewingTx.value = tx;
  viewingItems.value = [];
  viewError.value = '';
  viewLoading.value = true;
  try {
    const resp = await CaisseGateway.getTransaction(tx.transaction_id);
    viewingItems.value = resp.data.items || [];
  } catch (err) {
    viewError.value = "Impossible de charger le détail de la facture.";
  } finally {
    viewLoading.value = false;
  }
};
</script>
