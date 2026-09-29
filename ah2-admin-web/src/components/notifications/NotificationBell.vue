<!-- src/components/notifications/NotificationBell.vue -->
<template>
  <div class="relative">
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

    <!-- Popup bloquant pour une nouvelle demande de reduction -->
    <div v-if="activePopup" class="fixed inset-0 bg-black/30 flex items-center justify-center z-[100]" @click.self="dismissPopup">
      <div class="bg-white rounded-xl shadow-2xl p-6 max-w-sm w-full">
        <h3 class="font-bold text-gray-800 mb-2">{{ labelFor(activePopup) }}</h3>
        <button @click="dismissPopup" class="mt-4 w-full bg-indigo-600 text-white rounded-lg py-2 font-medium hover:bg-indigo-700">
          {{ $t('common.ok') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { BellIcon } from '@heroicons/vue/24/outline';
import { useNotificationStore } from '@/stores/notificationStore';
import { useAuthStore } from '@/stores/auth';
import { CaisseGateway } from '@/services/CaisseGateway';
import { PrinterBridgeGateway } from '@/services/PrinterBridgeGateway';
import router from '@/router';

const notificationStore = useNotificationStore();
const authStore = useAuthStore();
const open = ref(false);
const activePopup = ref(null);
let popupCheckTimer = null;
const printedDecisionIds = new Set(); // evite une double impression si la meme notification est relue

const maybePrintApprovedDiscountTicket = async (n) => {
  if (!authStore.hasRole(['secretaire'])) return;
  if (n.type !== 'discount_decided') return;
  if (n.payload?.status !== 'approved') return;
  if (printedDecisionIds.has(n.id)) return;
  printedDecisionIds.add(n.id);

  try {
    const resp = await CaisseGateway.getTicket(n.payload.transaction_id);
    await PrinterBridgeGateway.printTicket(resp.data);
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
  return n.type;
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
};

const dismissPopup = () => { activePopup.value = null; };

onMounted(() => {
  notificationStore.startPolling();
  popupCheckTimer = setInterval(() => {
    if (!activePopup.value) {
      const next = notificationStore.popNextPopup();
      if (next) activePopup.value = next;
    }
    // Verifie aussi les decisions de reduction fraichement recues,
    // independamment du popup (qui ne se declenche que pour discount_request,
    // jamais discount_decided - voir labelFor)
    notificationStore.notifications.forEach(maybePrintApprovedDiscountTicket);
  }, 1000);
});

onUnmounted(() => {
  notificationStore.stopPolling();
  if (popupCheckTimer) clearInterval(popupCheckTimer);
});
</script>
