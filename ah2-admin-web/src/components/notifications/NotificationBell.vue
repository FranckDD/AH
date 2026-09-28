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
import router from '@/router';

const notificationStore = useNotificationStore();
const open = ref(false);
const activePopup = ref(null);
let popupCheckTimer = null;

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
  return n.type;
};

const formatDate = (iso) => iso ? new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '';

const handleClick = async (n) => {
  await notificationStore.markRead(n.id);
  open.value = false;
  if (n.type === 'discount_request') {
    router.push({ name: 'discount-review' });
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
  }, 1000);
});

onUnmounted(() => {
  notificationStore.stopPolling();
  if (popupCheckTimer) clearInterval(popupCheckTimer);
});
</script>
