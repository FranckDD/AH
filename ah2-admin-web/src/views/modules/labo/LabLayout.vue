<template>
  <div class="flex flex-col h-full bg-gray-50">
    <div class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10 shadow-xs">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-indigo-100 rounded-lg">
           <beaker-icon class="w-6 h-6 text-indigo-600" />
        </div>
        <div>
            <h2 class="text-xl font-bold text-gray-800 leading-tight">Laboratoire</h2>
            <p class="text-xs text-gray-500">Gestion des analyses médicales</p>
        </div>
      </div>
      
      <nav class="flex space-x-1 bg-gray-100 p-1 rounded-xl">
        
        <router-link v-if="canSeeReception" :to="{ name: 'lab-reception' }" custom v-slot="{ navigate, isActive }">
          <button @click="navigate" class="nav-btn" :class="isActive ? 'active' : 'inactive'">
            <UserGroupIcon class="w-4 h-4" />
            Réception
          </button>
        </router-link>

        <router-link v-if="canSeePaillasse" :to="{ name: 'lab-technician' }" custom v-slot="{ navigate, isActive }">
          <button @click="navigate" class="nav-btn" :class="isActive ? 'active' : 'inactive'">
            <BeakerIcon class="w-4 h-4" />
            Paillasse
          </button>
        </router-link>



        <router-link v-if="canSeeHistory" :to="{ name: 'lab-history' }" custom v-slot="{ navigate, isActive }">
          <button @click="navigate" class="nav-btn" :class="isActive ? 'active' : 'inactive'">
            <ClockIcon class="w-4 h-4" />
            Historique
          </button>
        </router-link>

        <router-link v-if="canSeeSyncFailures" :to="{ name: 'lab-sync-failures' }" custom v-slot="{ navigate, isActive }">
          <button @click="navigate" class="nav-btn" :class="isActive ? 'active' : 'inactive'">
            <ExclamationTriangleIcon class="w-4 h-4" />
            Échecs sync
          </button>
        </router-link>

        <router-link v-if="canConfigure" :to="{ name: 'lab-config' }" custom v-slot="{ navigate, isActive }">
          <button @click="navigate" class="nav-btn" :class="isActive ? 'active-purple' : 'inactive'">
            <CogIcon class="w-4 h-4" />
            Config
          </button>
        </router-link>
      </nav>
    </div>

    <div class="flex-1 overflow-hidden">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { 
  BeakerIcon, UserGroupIcon, ClipboardDocumentCheckIcon, ClockIcon, CogIcon, ExclamationTriangleIcon
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();
// Chaque onglet reflete exactement les meta.roles de sa route reelle
// (router/index.js) - avant ce correctif, Reception et Paillasse
// s'affichaient sans condition pour tout role atteignant ce shell,
// y compris medecin/nurse (registre L4b, chantier L4b-e) qui n'y ont
// jamais eu acces : cul-de-sac (403 au clic).
const canSeeReception = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager', 'Assistant']));
const canSeePaillasse = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager']));
const canSeeHistory = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager']));
const canSeeSyncFailures = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager']));
const canConfigure = computed(() => authStore.hasRole(['admin', 'manager', 'biologiste']));
</script>

<style scoped>
/* Tailwind v4 : @apply dans un bloc <style> scope necessite une reference
   explicite au theme (plus d'injection implicite comme en v3). */
@reference "../../../style.css";

.nav-btn {
  @apply px-4 py-2 rounded-lg text-sm font-bold transition-all duration-200 flex items-center gap-2;
}
.active {
  @apply bg-white text-indigo-600 shadow-sm;
}
.active-purple {
  @apply bg-white text-purple-600 shadow-sm;
}
.inactive {
  @apply text-gray-500 hover:text-gray-700 hover:bg-gray-200;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease-in-out; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>