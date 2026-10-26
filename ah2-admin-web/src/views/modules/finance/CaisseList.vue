<template>
  <div class="grid w-full grid-cols-[minmax(0,1fr)] gap-6">
    <PageHeader :title="t('caisse.title')" :subtitle="t('caisseScreens.invoices_shown', { n: caisseStore.transactions.length })">
      <template #actions>
        <AppButton :icon="PlusCircleIcon" @click="showInvoiceModal = true">{{ t('caisse.new_invoice') }}</AppButton>
      </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <StatTile :title="`${t('finance.income')} (${kpiScope})`" :value="kpiAffiche(formatCurrency(caisseStore.kpi.total_paid))" :icon="ArrowTrendingUpIcon" tone="success" />
      <StatTile :title="`${t('caisse.table.due')} (${kpiScope})`" :value="kpiAffiche(formatCurrency(caisseStore.kpi.remaining_due))" :icon="ClockIcon" tone="danger" alert />
      <StatTile :title="`${t('caisseScreens.kpi_transactions')} (${kpiScope})`" :value="kpiAffiche(caisseStore.kpi.total_transactions)" :icon="BanknotesIcon" />
    </div>

    <button v-if="pendingApprovalCount > 0 && statusFilter !== 'pending_approval'" type="button"
            class="flex w-full min-h-11 flex-col items-start gap-1 rounded-card border p-4 text-left text-base transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 sm:flex-row sm:items-center sm:justify-between"
            :class="toneClasses('warning')"
            @click="statusFilter = 'pending_approval'">
      <span class="font-medium">{{ t('caisse.pending_banner', { count: pendingApprovalCount }) }}</span>
      <span class="font-semibold underline">{{ t('caisse.status.pending_approval') }}</span>
    </button>

    <section :aria-label="t('caisse.table.status')" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:flex lg:flex-wrap lg:items-end">
      <div class="md:col-span-2 lg:min-w-64 lg:flex-1">
        <FormField id="caisse-search" :label="t('caisseScreens.search_label')" v-slot="{ describedBy }">
          <input id="caisse-search" v-model="searchQuery" type="search" :placeholder="t('caisse.search_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-44">
        <FormField id="caisse-from" :label="t('caisseScreens.from')" v-slot="{ describedBy }">
          <input id="caisse-from" v-model="startDate" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-44">
        <FormField id="caisse-to" :label="t('caisseScreens.to')" v-slot="{ describedBy }">
          <input id="caisse-to" v-model="endDate" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="md:col-span-2 lg:w-52">
        <FormField id="caisse-status" :label="t('caisse.table.status')" v-slot="{ describedBy }">
          <select id="caisse-status" v-model="statusFilter" :aria-describedby="describedBy" :class="fieldClass">
            <option value="active">{{ t('caisse.status.active') }}</option>
            <option value="pending_approval">{{ t('caisse.status.pending_approval') }}</option>
            <option value="cancelled">{{ t('caisse.status.cancelled') }}</option>
            <option value="refunded">{{ t('caisse.status.refunded') }}</option>
            <option value="">{{ t('caisse.status.all') }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <section class="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
      <p v-if="caisseStore.loadError" role="alert" class="rounded-card border p-4 text-center text-base font-medium" :class="toneClasses('danger')">
        {{ t('caisseScreens.load_error') }}
      </p>
      <ResponsiveTable
        v-else
        :columns="columns"
        :rows="caisseStore.transactions"
        row-key="transaction_id"
        :loading="caisseStore.isLoading"
        striped
        :empty-title="t('caisseScreens.empty')"
        :empty-message="' '"
      >
        <template #cell-date="{ row: tx }"><span class="font-mono">{{ formatDate(tx.paid_at) }}</span></template>
        <template #cell-patient="{ row: tx }">{{ tx.patient_name || '-' }}</template>
        <template #cell-type="{ row: tx }">{{ tx.transaction_type }}</template>
        <template #cell-amount="{ row: tx }">
          <span class="font-bold" :class="tx.status === 'cancelled' ? 'text-ink-muted line-through' : ''">{{ formatCurrency(tx.amount) }}</span>
          <div v-if="Number(tx.staff_discount_amount) > 0" class="text-sm font-semibold text-tone-success-text">
            {{ t('staffDiscount.invoice_line') }} -{{ formatCurrency(tx.staff_discount_amount) }}
          </div>
        </template>
        <template #cell-paid="{ row: tx }"><span :class="tx.status === 'cancelled' ? 'text-ink-muted line-through' : 'text-tone-success-text'">{{ formatCurrency(tx.amount_paid) }}</span></template>
        <template #cell-due="{ row: tx }">
          <span :class="tx.status === 'cancelled' ? 'text-ink-muted line-through' : Number(tx.amount_due) > 0 ? 'font-semibold text-tone-danger-text' : 'text-ink-muted'">
            {{ formatCurrency(tx.amount_due) }}
          </span>
        </template>
        <template #cell-status="{ row: tx }">
          <div class="flex flex-wrap items-center gap-1.5">
            <StatusBadge v-if="tx.status === 'active'" tone="success" :label="t('caisse.status.active')" />
            <StatusBadge v-else-if="tx.status === 'pending_approval'" tone="warning" :label="t('caisse.status.pending_approval')" />
            <StatusBadge v-else-if="tx.status === 'refunded'" tone="info" :label="t('caisse.status.refunded')" />
            <StatusBadge v-else tone="neutral" :label="t('caisse.status.cancelled')" />
            <StatusBadge v-if="tx.upload_error" tone="danger" :label="t('caisseScreens.sync_failed')" :title="tx.upload_error" />
          </div>
        </template>
        <template #actions="{ row: tx }">
          <AppButton variant="lab" :icon="EyeIcon" @click="openViewModal(tx)" :disabled="!tx.transaction_id"
                     :title="tx.transaction_id ? t('caisse.actions.view') : t('caisseScreens.pending_sync')">
            <span class="lg:sr-only">{{ t('caisse.actions.view') }}</span>
          </AppButton>
          <AppButton v-if="tx.status === 'active' && Number(tx.amount_due) > 0" variant="record" :icon="CurrencyDollarIcon" @click="openInstallmentModal(tx)" :disabled="!tx.transaction_id"
                     :title="tx.transaction_id ? t('caisse.actions.add_payment') : t('caisseScreens.pending_sync')">
            <span class="lg:sr-only">{{ t('caisse.actions.add_payment') }}</span>
          </AppButton>
          <AppButton v-if="tx.status === 'active' && Number(tx.amount_due) > 0" variant="spirit" :icon="CheckBadgeIcon" @click="handleSettle(tx)" :disabled="!tx.transaction_id"
                     :title="tx.transaction_id ? t('caisse.actions.settle') : t('caisseScreens.pending_sync')">
            <span class="lg:sr-only">{{ t('caisseScreens.action_settle') }}</span>
          </AppButton>
          <AppButton variant="pharma" :icon="ArrowDownTrayIcon" @click="downloadInvoice(tx)" :disabled="!tx.transaction_id"
                     :title="tx.transaction_id ? t('caisse.actions.download') : t('caisseScreens.pending_sync')">
            <span class="lg:sr-only">{{ t('caisseScreens.action_download') }}</span>
          </AppButton>
          <AppButton v-if="tx.status === 'active'" variant="toxico" :icon="PrinterIcon" @click="printTicketForTransaction(tx.transaction_id)" :disabled="!tx.transaction_id"
                     :title="tx.transaction_id ? t('caisse.actions.reprint_ticket') : t('caisseScreens.pending_sync')">
            <span class="lg:sr-only">{{ t('caisse.actions.reprint_ticket') }}</span>
          </AppButton>
          <AppButton v-if="tx.status === 'active'" variant="danger" :icon="XCircleIcon" @click="openCancelModal(tx)" :disabled="!tx.transaction_id"
                     :title="tx.transaction_id ? t('caisse.actions.cancel') : t('caisseScreens.pending_sync')">
            <span class="lg:sr-only">{{ t('caisse.actions.cancel') }}</span>
          </AppButton>
        </template>
      </ResponsiveTable>

      <div v-if="caisseStore.pagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">{{ t('caisseScreens.page_label', { n: caisseStore.pagination.page, total: caisseStore.pagination.total_pages }) }}</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="t('caisseScreens.prev_page')" @click="goToPage(caisseStore.pagination.page - 1)" :disabled="caisseStore.pagination.page === 1" />
          <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="t('caisseScreens.next_page')" @click="goToPage(caisseStore.pagination.page + 1)" :disabled="caisseStore.pagination.page === caisseStore.pagination.total_pages" />
        </div>
      </div>
    </section>

    <p v-if="actionError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ actionError }}</p>

    <CaisseInvoiceModal v-if="showInvoiceModal" :isSaving="isSavingInvoice" :errorMessage="invoiceError"
                         @close="showInvoiceModal = false" @save="handleCreateInvoice"
                         @discount-requested="() => { caisseStore.fetchTransactions(); fetchPendingApprovalCount(); }" />

    <CaisseInstallmentModal v-if="installmentTx" :remainingDue="Number(installmentTx.amount_due)"
                             :mode="installmentMode" :defaultMethod="installmentTx.payment_method"
                             :isSaving="isSavingInstallment" :errorMessage="installmentError"
                             @close="installmentTx = null" @confirm="handleAddPayment" />

    <CaisseCancelModal v-if="cancellingTx" :isSaving="isCancelling" :errorMessage="cancelError"
                        :label="`Facture ${cancellingTx.transaction_id} : ${formatCurrency(cancellingTx.amount)}`"
                        @close="cancellingTx = null" @confirm="handleCancel" />

    <!-- Detail de la facture : lecture seule -->
    <FullScreenPanel v-if="viewingTx" :title="`${t('caisseScreens.view_title')} : ${viewingTx.patient_name || viewingTx.transaction_id}`" @close="viewingTx = null">
      <p v-if="viewLoading" role="status" class="py-6 text-center text-base text-ink-muted">{{ t('ui.loading') }}</p>
      <p v-else-if="viewError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ viewError }}</p>
      <div v-else class="grid gap-3">
        <h3 class="text-lg font-semibold text-ink">{{ t('caisse.invoice_modal.section_items') }}</h3>
        <ResponsiveTable :columns="itemColumns" :rows="viewingItems" row-key="item_id" :empty-title="t('caisse.invoice_modal.no_lines')" :empty-message="' '">
          <template #cell-label="{ row: item }">{{ item.note || item.item_type }}</template>
          <template #cell-unit_price="{ row: item }">{{ formatCurrency(item.unit_price) }}</template>
          <template #cell-line_total="{ row: item }"><span class="font-semibold">{{ formatCurrency(item.line_total) }}</span></template>
        </ResponsiveTable>
      </div>
      <template #footer>
        <ActionBar>
          <AppButton variant="secondary" @click="viewingTx = null">{{ t('ui.close') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
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
import { useAuthStore } from '@/stores/auth';
import { useConfigStore } from '@/stores/configStore';
import { useToastStore } from '@/stores/toastStore';
import { AppButton, PageHeader, FormField, StatTile, StatusBadge, ResponsiveTable, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { modeLabel } from '@/utils/paymentModes';

const { t } = useI18n();
const caisseStore = useCaisseStore();
const authStore = useAuthStore();
const configStore = useConfigStore();
const route = useRoute();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'date', label: t('caisse.table.date') },
  { key: 'patient', label: t('caisse.table.patient') },
  { key: 'type', label: t('caisse.table.type') },
  { key: 'amount', label: t('caisse.table.total'), align: 'right' },
  { key: 'paid', label: t('caisse.table.paid'), align: 'right' },
  { key: 'due', label: t('caisse.table.due'), align: 'right' },
  { key: 'status', label: t('caisse.table.status') },
]);
const itemColumns = computed(() => [
  { key: 'label', label: t('caisse.table.type') },
  { key: 'quantity', label: t('caisse.invoice_modal.quantity'), align: 'right' },
  { key: 'unit_price', label: t('caisse.invoice_modal.unit_price'), align: 'right' },
  { key: 'line_total', label: t('caisse.invoice_modal.line_total'), align: 'right' },
]);
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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

// Rafraichissement periodique silencieux (liste + KPI) - filet de securite
// si la synchro tarde, et affiche aussi les factures saisies depuis un
// autre poste. Meme cadence que notificationStore (30s).
//
// Suspendu tant qu'une modale caisse est ouverte (retour terrain 2026-09-28,
// question explicite de l'utilisateur) : remplacer caisseStore.transactions
// pendant que la secretaire est en train d'annuler/solder/creer une facture
// ne perd jamais sa saisie (les modales gardent leur propre etat, une
// reference figee au tx cliquee - voir cancellingTx/installmentTx/viewingTx
// plus bas, jamais recalculee depuis la liste live), mais rafraichir la
// LISTE sous ses yeux pendant qu'elle vise un bouton reste une gene/un
// risque de clic sur la mauvaise ligne si l'ordre bouge. On saute juste ce
// tour-la, sans jamais arreter le minuteur - le tour suivant recupere.
const isCaisseBusy = () =>
  showInvoiceModal.value || !!cancellingTx.value || !!installmentTx.value || !!viewingTx.value;

const AUTO_REFRESH_MS = 30000;
let autoRefreshTimer = null;

onMounted(() => {
  // Action rapide de l'accueil du secretariat (?nouveau=1) : ouvre directement la facture. Le parametre est
  // retire de l'adresse SANS navigation (router.replace remonterait la page et fermerait la facture).
  if (route.query.nouveau === '1') {
    showInvoiceModal.value = true;
    window.history.replaceState(window.history.state, '', route.path);
  }
  caisseStore.fetchTransactions();
  fetchPendingApprovalCount();
  autoRefreshTimer = setInterval(() => {
    if (isCaisseBusy()) return;
    caisseStore.fetchTransactions({ silent: true }).catch(() => {});
    fetchPendingApprovalCount();
  }, AUTO_REFRESH_MS);
});

onUnmounted(() => {
  clearInterval(autoRefreshTimer);
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
const toastStore = useToastStore();

// PrinterBridgeGateway.printTicket() leve un message explicite
// "Jeton d'impression non configuré." quand configStore.ticketPrintToken
// est vide (voir PrinterBridgeGateway.js) - un vrai probleme de
// configuration, pas un probleme d'imprimante. Le distinguer evite de
// faire chercher a un administrateur un cable/une imprimante qui n'a
// rien a voir (finding du dernier examen).
const TOKEN_ERROR_MESSAGE = "Jeton d'impression non configuré.";
const describePrintError = (err) => {
  if (err?.message === TOKEN_ERROR_MESSAGE) {
    return "Jeton d'impression non configuré ou invalide : contactez un administrateur.";
  }
  return "Ticket non imprimé : imprimante indisponible. Utilisez le bouton Réimprimer pour réessayer.";
};

// Notification qui disparait seule apres quelques secondes (la facture est deja enregistree ; le bouton Reimprimer
// reste disponible). Memes cas qu'avant : toute tentative d'impression (auto ou reimpression) qui echoue.
const notifyPrintFailure = (err) => {
  toastStore.push(describePrintError(err), 'warning');
};

const printTicketForTransaction = async (transactionId) => {
  try {
    const resp = await CaisseGateway.getTicket(transactionId);
    // ticket_logo_path renvoye par le backend est un chemin fichier sur SON
    // disque (get_ticket_header_context), jamais accessible depuis le poste
    // secretariat qui heberge printer_bridge (meme motif deja documente pour
    // buildLocalTicketData ci-dessous) : Image.open() echoue silencieusement
    // cote pont, le ticket s'imprime mais sans logo. On substitue le cache
    // data URI local, seule forme que printer_bridge peut effectivement lire.
    // payment_method : libelle lisible (le serveur stocke un code, ex. orange_money) ; donnees stockees intactes.
    await PrinterBridgeGateway.printTicket({ ...resp.data, payment_method: resp.data?.payment_method ? modeLabel(resp.data.payment_method) : resp.data?.payment_method, ticket_logo_path: configStore.ticketLogoDataUri || null });
  } catch (err) {
    notifyPrintFailure(err);
    console.error('Erreur impression ticket:', err);
  }
};

// Construit le ticket cote client, sans appel reseau, pour le chemin
// secretaire/PowerSync (ecriture locale - voir caisseStore.js) ou
// transaction_id n'est encore qu'un uuid local non reconnu par le
// backend. Les noms de champs miroir exactement CaisseController
// .build_ticket_data() / CaisseRepository.get_transaction_details_for
// _invoice() (repositories/caisse_repo.py) et le contrat consomme par
// printer_bridge/ticket_renderer.py::render_ticket(), pour que le meme
// rendu fonctionne a l'identique en ligne et hors ligne.
// - discount est toujours null ici : une facture creee hors ligne n'a
//   jamais pu passer par le circuit d'approbation de reduction (appel
//   reseau direct, jamais mis en file d'attente hors ligne - voir
//   DiscountRequestGateway.create), donc aucun risque de faux-negatif.
// - ticket_logo_path utilise le cache configStore.ticketLogoDataUri (data
//   URI base64, rempli au dernier fetchStructureInfo/saveStructureInfo
//   reussi - voir configStore.js::refreshTicketLogoCache) plutot que le
//   chemin fichier serveur renvoye en ligne (get_ticket_header_context),
//   jamais accessible depuis le navigateur. Absent (jamais synchronise en
//   ligne au moins une fois) -> null, ticket_renderer.py traite deja ce cas
//   comme optionnel (en-tete texte seul).
const buildLocalTicketData = (localTransactionId, payload, patientDisplayName) => ({
  transaction_id: localTransactionId,
  patient_name: payload.patient_label || patientDisplayName || '-',
  user_name: authStore.user?.full_name || authStore.user?.username || '',
  paid_at: new Date().toISOString(),
  amount: payload.amount,
  advance_amount: payload.advance_amount,
  remaining: payload.amount - payload.advance_amount,
  payment_method: payload.payment_method ? modeLabel(payload.payment_method) : payload.payment_method, // libelle imprime, le code stocke ne change pas
  items: (payload.items || []).map((i) => ({
    item_name: i.note || i.item_type,
    quantity: i.quantity,
    unit_price: i.unit_price,
    line_total: i.line_total,
  })),
  discount: null,
  // payload.amount est deja le NET (reduction personnel deduite, voir
  // CaisseInvoiceModal.vue) : remaining ci-dessus reste coherent.
  // details: null - le detail par categorie n'est fourni qu'en ligne.
  staff_discount: payload.staff_discount_amount > 0
    ? { amount: payload.staff_discount_amount, details: null }
    : null,
  header: {
    structure_name: configStore.structureInfo.name,
    slogan: configStore.structureInfo.slogan,
    address: configStore.structureInfo.address,
    phone: configStore.structureInfo.phone,
    phone2: configStore.structureInfo.phone2,
    website: configStore.structureInfo.website,
    niu: configStore.structureInfo.niu,
    rccm: configStore.structureInfo.rccm,
    legal_info: configStore.structureInfo.legal_info,
    ticket_logo_path: configStore.ticketLogoDataUri || null,
  },
});

const printLocallyBuiltTicket = async (localTransactionId, payload, patientDisplayName) => {
  try {
    const ticketData = buildLocalTicketData(localTransactionId, payload, patientDisplayName);
    await PrinterBridgeGateway.printTicket(ticketData);
  } catch (err) {
    notifyPrintFailure(err);
    console.error('Erreur impression ticket (local):', err);
  }
};

// --- Creation facture ---
const showInvoiceModal = ref(false);
const isSavingInvoice = ref(false);
const invoiceError = ref('');

const handleCreateInvoice = async (payload, patientDisplayName) => {
  isSavingInvoice.value = true;
  invoiceError.value = '';
  try {
    const result = await caisseStore.createInvoice(payload);
    showInvoiceModal.value = false;
    // caisseStore.createInvoice() a deux formes de retour : le chemin
    // secretaire/PowerSync (ecriture locale, voir caisseStore.js) renvoie
    // { transaction_id: <uuid local> } sans champ status, alors que le
    // chemin en ligne renvoie la reponse serveur reelle ou transaction_id
    // est un entier (voir caisse_schemas.py TransactionResponse). Impression
    // toujours tentee quand la facture est active (jamais conditionnee par
    // la reduction) : id serveur reel -> chemin backend authoritative ;
    // uuid local (pas encore synchronise) -> ticket construit cote client
    // avec les donnees deja en main, pour que l'impression marche aussi
    // bien hors ligne qu'en ligne.
    if (result && result.status !== 'pending_approval' && result.transaction_id) {
      if (Number.isInteger(result.transaction_id)) {
        printTicketForTransaction(result.transaction_id);
      } else {
        // uuid local (chemin secretaire/PowerSync, systematique meme en
        // ligne - voir caisseStore.js::createInvoice). Si le reseau est
        // disponible, on patiente brievement que PowerSync confirme le
        // vrai server_id pour imprimer avec le numero de facture reel et
        // le logo, plutot que de prendre systematiquement le repli local
        // (finding critique du dernier examen : Number.isInteger() seul
        // prenait TOUJOURS la branche locale pour la secretaire). Ceci
        // est deliberement fire-and-forget vis-a-vis du reste de la
        // fonction : ne jamais retarder la fermeture de la modale ni la
        // remise a zero de isSavingInvoice, qui se font juste apres, la
        // facture etant deja enregistree a ce stade.
        printEventualTicket(result.transaction_id, payload, patientDisplayName);
      }
    }
  } catch (err) {
    invoiceError.value = mapErrorToMessage(err);
  } finally {
    isSavingInvoice.value = false;
  }
};

// Attend (best-effort, timeout court) une confirmation de synchronisation
// avant de choisir entre le chemin d'impression serveur (numero de
// facture reel + logo) et le repli local construit cote client. Jamais
// awaited par handleCreateInvoice - void intentionnel.
const printEventualTicket = async (localUuid, payload, patientDisplayName) => {
  if (navigator.onLine) {
    const serverId = await caisseStore.waitForSyncedTransactionId(localUuid);
    if (serverId != null) {
      await printTicketForTransaction(serverId);
      return;
    }
  }
  await printLocallyBuiltTicket(localUuid, payload, patientDisplayName);
};

// Portee des tuiles KPI : le jour meme (local) sans dates choisies, sinon la
// periode choisie (meme regle que caisseStore.updateKpis). Le sous-titre, lui,
// compte les lignes du tableau affiche (defaut 6a).
const kpiScope = computed(() => (caisseStore.filters.startDate || caisseStore.filters.endDate
  ? t('caisseScreens.kpi_scope_period')
  : t('caisseScreens.kpi_scope_today')));

// --- Versement ---
const installmentTx = ref(null);
const isSavingInstallment = ref(false);
const installmentError = ref('');

const installmentMode = ref('installment');

const openInstallmentModal = (tx, mode = 'installment') => {
  installmentMode.value = mode;
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
// Ouvre le panneau de versement pre-rempli (reste du, mode de la facture) :
// la secretaire confirme avant tout encaissement (defaut 3, 2026-10-26).
// Le paiement passe ensuite par caisseStore.addPayment (ecriture locale
// PowerSync pour la secretaire, type SOLDE si tout le reste est verse).
const handleSettle = (tx) => {
  actionError.value = '';
  openInstallmentModal(tx, 'settle');
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
