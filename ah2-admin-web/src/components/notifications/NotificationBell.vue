<!-- src/components/notifications/NotificationBell.vue -->
<template>
  <div class="relative" ref="rootEl">
    <button
      @click="toggleOpen"
      class="relative flex items-center text-gray-600 hover:text-gray-900 transition"
      :title="$t('notifications.title')"
    >
      <BellIcon class="h-6 w-6" />
      <span
        v-if="notificationStore.unreadCount > 0"
        class="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold rounded-full h-4 w-4 flex items-center justify-center"
      >
        {{ notificationStore.unreadCount > 9 ? '9+' : notificationStore.unreadCount }}
      </span>
    </button>

    <div v-if="open" class="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-96 overflow-y-auto">
      <div v-if="notificationStore.notifications.length === 0" class="p-4 text-sm text-gray-400 text-center">
        {{ $t('notifications.empty') }}
      </div>
      <div
        v-for="n in notificationStore.notifications"
        :key="n.id"
        class="p-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer text-sm"
        @click="handleClick(n)"
      >
        <div class="font-medium text-gray-800">{{ labelFor(n) }}</div>
        <div class="text-xs text-gray-400 mt-1">{{ formatDate(n.created_at) }}</div>
      </div>
    </div>

    <!-- Avertissement discret et groupe (type toast Windows) : coin haut-droit,
         se ferme seul, un clic ouvre la liste. -->
    <Teleport to="body">
      <transition name="notif-toast">
        <div
          v-if="toast"
          class="fixed top-24 right-4 w-80 max-w-[calc(100vw-2rem)] bg-white rounded-lg shadow-xl border border-gray-200 border-l-4 border-l-indigo-600 p-3 flex items-start gap-3 cursor-pointer"
          style="z-index: 9999"
          role="status"
          @click.stop="openFromToast"
        >
          <BellIcon class="h-5 w-5 text-indigo-600 shrink-0 mt-0.5" />
          <div class="flex-1 text-sm text-gray-800 min-w-0 break-words">{{ toastText }}</div>
          <button
            class="text-gray-400 hover:text-gray-700 text-lg leading-none min-h-[32px] min-w-[32px]"
            :aria-label="$t('notifications.toast_close')"
            @click.stop="closeToast"
          >&times;</button>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { BellIcon } from '@heroicons/vue/24/outline';
import { useNotificationStore } from '@/stores/notificationStore';
import { useAuthStore } from '@/stores/auth';
import { CaisseGateway } from '@/services/CaisseGateway';
import { PrinterBridgeGateway } from '@/services/PrinterBridgeGateway';
import router from '@/router';
import { useI18n } from 'vue-i18n';
import { stockDecidedLabel, adjustmentKindLabel } from '@/utils/stockNotificationLabels';
import { labNotificationLabel } from '@/utils/labStockLabels';
import { gapWords } from '@/utils/cashClosure';
import { modeLabel } from '@/utils/paymentModes';

const { t } = useI18n();

const notificationStore = useNotificationStore();
const authStore = useAuthStore();
const open = ref(false);
const rootEl = ref(null);
const toast = ref(null); // { count, last }
let toastTimer = null;
let popupCheckTimer = null;
const TOAST_MS = 7000;
const printedDecisionIds = new Set(); // evite une double impression si la meme notification est relue

const maybePrintApprovedDiscountTicket = async (n) => {
  if (!authStore.hasRole(['secretaire'])) return;
  if (n.type !== 'discount_decided') return;
  if (n.payload?.status !== 'approved') return;
  if (printedDecisionIds.has(n.id)) return;
  printedDecisionIds.add(n.id);

  try {
    const resp = await CaisseGateway.getTicket(n.payload.transaction_id);
    // libelle lisible du mode (code stocke, ex. orange_money) ; vide reste vide (pas de ligne Mode)
    const pm = resp.data?.payment_method;
    await PrinterBridgeGateway.printTicket({ ...resp.data, payment_method: pm ? modeLabel(pm) : pm });
  } catch (err) {
    console.error('Impression automatique post-décision échouée:', err);
    // Pas de bandeau ici (composant global monté partout) - l'utilisateur
    // peut toujours reimprimer manuellement depuis CaisseList.vue (Task 11).
  } finally {
    // Marquer lue dans tous les cas (succes ou echec d'impression) : sinon
    // cette notification 'discount_decided' reste indefiniment dans la
    // liste des non-lues (jamais marquee lue ailleurs) et serait
    // re-offerte a l'impression a chaque reload/login, provoquant une
    // reimpression papier a chaque fois (finding critique du dernier
    // examen). printedDecisionIds seul ne suffit pas : c'est un Set en
    // memoire qui se reinitialise a chaque remontage du composant.
    await notificationStore.markRead(n.id);
  }
};

const toggleOpen = () => { open.value = !open.value; };

const onDocumentClick = (e) => {
  if (open.value && rootEl.value && !rootEl.value.contains(e.target)) open.value = false;
};
const onKeydown = (e) => { if (e.key === 'Escape') { open.value = false; closeToast(); } };

const closeToast = () => {
  toast.value = null;
  if (toastTimer) { clearTimeout(toastTimer); toastTimer = null; }
};
const showToast = (incoming) => {
  const count = (toast.value ? toast.value.count : 0) + incoming.length;
  toast.value = { count, last: incoming[incoming.length - 1] };
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(closeToast, TOAST_MS);
};
const openFromToast = () => { closeToast(); open.value = true; };
const toastText = computed(() => {
  if (!toast.value) return '';
  return toast.value.count === 1
    ? labelFor(toast.value.last)
    : t('notifications.toast_many', { count: toast.value.count });
});

const labelFor = (n) => {
  if (n.type === 'discount_request') {
    return `${n.payload?.requested_by_name || '?'} demande une réduction (${n.payload?.amount ?? '?'} FCFA)`;
  }
  if (n.type === 'discount_decided') {
    if (n.payload?.status === 'refused') return 'Demande de réduction refusée';
    const pct = n.payload?.decision_percent;
    const deadline = n.payload?.decision_echelonne_deadline;
    const parts = [];
    if (pct) parts.push(`${pct}% accordé`);
    if (deadline) parts.push(`échéance ${new Date(deadline).toLocaleDateString('fr-FR')}`);
    return parts.length ? `Demande de réduction approuvée — ${parts.join(', ')}` : 'Demande de réduction approuvée';
  }
  if (n.type === 'hospitalization_aggravation') {
    return `⚠ Aggravation signalée — ${n.payload?.patient_name || 'patient'} (par ${n.payload?.reported_by_name || '?'})`;
  }
  if (n.type === 'patient_pending_review') {
    return `🩺 Patient en attente — ${n.payload?.patient_name || 'patient'} (${n.payload?.created_by_name || '?'})`;
  }
  if (n.type === 'stock_to_check') {
    const p = n.payload || {};
    const what = p.receipt_id
      ? t('notifications.stock_to_check_receipt', { number: p.receipt_number || '?' })
      : t('notifications.stock_to_check_incident', { product: p.product_name || '?', quantity: p.quantity ?? '?' });
    return t('notifications.stock_to_check', { author: p.created_by_name || '?', what });
  }
  if (n.type === 'stock_adjustment_request') {
    const p = n.payload || {};
    const k = adjustmentKindLabel(p.kind);
    const label = t('notifications.stock_adjustment_request', {
      author: p.requested_by_name || '?', kind: k.key ? t(k.key) : k.raw, product: p.product_name || '?', quantity: p.quantity ?? '?',
    });
    // recomptage : la demande remplace une demande de comptage encore en attente
    return Array.isArray(p.supersedes) && p.supersedes.length
      ? t('notifications.stock_adjustment_supersedes', { label, ids: p.supersedes.join(', ') })
      : label;
  }
  if (n.type === 'stock_count_superseded') {
    // payload : count_id, product_name, superseded_request_ids, counted_by_name
    const p = n.payload || {};
    return t('notifications.stock_count_superseded', {
      author: p.counted_by_name || '?', product: p.product_name || '?',
      ids: (p.superseded_request_ids || []).join(', ') || '?',
    });
  }
  if (n.type === 'stock_decided') {
    const p = n.payload || {};
    const d = stockDecidedLabel(p);
    const decision = t(d.key, d.params);
    return p.reason ? t('notifications.stock_decided_with_reason', { decision, reason: p.reason }) : decision;
  }
  if (typeof n.type === 'string' && n.type.startsWith('lab_stock_')) {
    const l = labNotificationLabel(n.type, n.payload);
    return t(l.key, l.params);
  }
  if (n.type === 'cash_closure') {
    // payload : business_date, expected_cash, counted_cash, difference (chaines), auto, anomaly
    const p = n.payload || {};
    const params = { date: p.business_date || '?', expected: p.expected_cash ?? '?', counted: p.counted_cash ?? '?' };
    const gap = gapWords(p.difference ?? null);
    const label = p.auto
      ? t('notifications.cash_closure_auto', params)
      : t('notifications.cash_closure', { ...params, difference: t(gap.key, { amount: gap.amount ?? '' }) });
    return p.anomaly ? t('notifications.cash_closure_anomaly', { label }) : label;
  }
  if (n.type === 'price_mismatch') {
    // payload : transaction_id, item_type, sent_price, catalog_price (null/0 = non defini), author_name
    const p = n.payload || {};
    const params = { id: p.transaction_id ?? '?', item: p.item_type || '?', sent: p.sent_price ?? '?',
      catalog: p.catalog_price ?? '?', author: p.author_name || '?' };
    return Number(p.catalog_price) > 0
      ? t('notifications.price_mismatch', params)
      : t('notifications.price_mismatch_undefined', params);
  }
  return n.type;
};

// Navigation par chemin : les pages stock sont creees dans d'autres taches, on
// ne pousse que si une route correspondante existe (sinon on ne fait rien).
const pushIfRoute = (path) => {
  // Le routeur a un catch-all (redirect /dashboard) : on l'exclut explicitement.
  const matched = router.resolve(path).matched;
  if (matched.length > 0 && !matched.some((m) => m.path.includes(':pathMatch'))) router.push(path);
};

const formatDate = (iso) => iso ? new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '';

const handleClick = async (n) => {
  await notificationStore.markRead(n.id);
  open.value = false;
  if (n.type === 'discount_request') {
    router.push({ name: 'discount-review' });
  }
  if (n.type === 'hospitalization_aggravation' && n.payload?.patient_id) {
    router.push(`/medical/patients/${n.payload.patient_id}`);
  }
  if (n.type === 'patient_pending_review' && n.payload?.patient_id) {
    router.push(`/medical/patients/${n.payload.patient_id}`);
  }
  if (n.type === 'stock_to_check') {
    pushIfRoute('/dashboard/stock-control');
  }
  if (n.type === 'stock_adjustment_request' || n.type === 'stock_count_superseded') {
    pushIfRoute('/dashboard/stock-adjustment-requests');
  }
  if (typeof n.type === 'string' && n.type.startsWith('lab_stock_')) {
    // Seules les pages existantes sont jointes (pushIfRoute ignore les autres).
    if (n.type === 'lab_stock_signal' || n.type === 'lab_stock_low') pushIfRoute('/dashboard/lab-stock-requests');
    else if (n.type === 'lab_stock_expiry') pushIfRoute('/dashboard/lab-stock-alerts');
    else if (n.type === 'lab_stock_count_reminder') pushIfRoute('/dashboard/lab-stock-count');
    else if (n.type === 'lab_stock_received') pushIfRoute('/dashboard/lab-stock-products');
  }
  if (n.type === 'cash_closure') {
    // Ecran de revue des clotures (promoteur/admin) ; les autres roles ne recoivent pas ce type.
    if (authStore.hasRole(['promoteur', 'admin'])) pushIfRoute('/dashboard/cash-closures');
  }
  if (n.type === 'price_mismatch') {
    // Journal financier unifie (ventes caisse comprises) : admin seulement ; le
    // promoteur n'a pas de liste des ventes, il ne navigue pas.
    if (authStore.hasRole(['admin'])) pushIfRoute('/dashboard/finance');
  }
  if (n.type === 'stock_decided') {
    const kind = n.payload?.kind;
    if (kind === 'receipt') pushIfRoute('/dashboard/stock-receipts');
    else if (kind === 'incident') pushIfRoute('/dashboard/stock-incidents');
    else if (kind === 'adjustment') pushIfRoute('/secretariat/stock');
  }
};

onMounted(() => {
  document.addEventListener('click', onDocumentClick);
  document.addEventListener('keydown', onKeydown);
  notificationStore.startPolling();
  popupCheckTimer = setInterval(() => {
    const incoming = notificationStore.popAllPopups();
    if (incoming.length) showToast(incoming);
    // Verifie aussi les decisions de reduction fraichement recues,
    // independamment du popup (qui ne se declenche que pour discount_request,
    // jamais discount_decided - voir labelFor)
    notificationStore.notifications.forEach(maybePrintApprovedDiscountTicket);
  }, 1000);
});

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick);
  document.removeEventListener('keydown', onKeydown);
  closeToast();
  notificationStore.stopPolling();
  if (popupCheckTimer) clearInterval(popupCheckTimer);
});
</script>

<style scoped>
.notif-toast-enter-active, .notif-toast-leave-active { transition: transform 0.25s ease, opacity 0.25s ease; }
.notif-toast-enter-from, .notif-toast-leave-to { transform: translateX(110%); opacity: 0; }
</style>
