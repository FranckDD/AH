<template>
  <div class="flex h-full flex-col bg-page">
    <header class="sticky top-0 z-10 flex flex-col gap-3 border-b border-tone-neutral-border bg-white px-4 py-3 shadow-card md:flex-row md:items-center md:justify-between md:px-6">
      <div class="flex items-center gap-3">
        <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-control bg-brand-50 text-brand-700">
          <BeakerIcon class="h-6 w-6" aria-hidden="true" />
        </span>
        <div>
          <h2 class="text-xl font-bold leading-tight text-ink">{{ t('lab.title') }}</h2>
          <p class="text-sm text-ink-muted">{{ t('lab.layout.subtitle') }}</p>
        </div>
      </div>

      <nav :aria-label="t('labScreens.nav_label')" class="flex flex-wrap gap-1">
        <router-link v-for="item in items" :key="item.name" :to="{ name: item.name }" custom v-slot="{ href, navigate, isActive }">
          <a :href="href" @click="navigate" :aria-current="isActive ? 'page' : undefined"
             :class="[
               isActive ? 'border-brand-600 bg-brand-50 font-semibold text-brand-700' : 'border-transparent text-ink-muted hover:bg-tone-neutral-bg hover:text-ink',
               'flex min-h-11 items-center gap-2 rounded-control border-b-4 px-3 text-sm focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600'
             ]">
            <component :is="item.icon" class="h-5 w-5 shrink-0" aria-hidden="true" />
            {{ item.label }}
          </a>
        </router-link>
      </nav>
    </header>

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
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { 
  BeakerIcon, UserGroupIcon, ClockIcon, CogIcon, ExclamationTriangleIcon
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();
const { t } = useI18n();
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

// Un onglet par route reelle, dans l'ordre d'origine ; seuls les onglets autorises sont affiches.
const items = computed(() => [
  { name: 'lab-reception', label: t('lab.nav.reception'), icon: UserGroupIcon, show: canSeeReception.value },
  { name: 'lab-technician', label: t('lab.nav.bench'), icon: BeakerIcon, show: canSeePaillasse.value },
  { name: 'lab-history', label: t('lab.nav.history'), icon: ClockIcon, show: canSeeHistory.value },
  { name: 'lab-sync-failures', label: t('lab.nav.sync_failures'), icon: ExclamationTriangleIcon, show: canSeeSyncFailures.value },
  { name: 'lab-config', label: t('lab.nav.config_short'), icon: CogIcon, show: canConfigure.value },
].filter((i) => i.show));
</script>
<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease-in-out; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
