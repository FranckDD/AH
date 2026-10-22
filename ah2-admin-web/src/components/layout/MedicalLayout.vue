<template>
  <div class="app-refonte flex w-full h-dvh bg-page">

    <!-- Voile derrière le tiroir (téléphone) -->
    <div
      v-if="isDrawerOpen"
      class="fixed inset-0 z-30 bg-ink/50 md:hidden"
      aria-hidden="true"
      @click="closeDrawer"
    ></div>

    <aside
      id="medical-sidebar"
      :aria-label="t('medicalShell.mainNav')"
      :class="[
        'bg-nav-900 text-nav-text w-72 max-w-[85vw] shrink-0 flex flex-col',
        'fixed inset-y-0 left-0 z-40 transition-all duration-200 ease-in-out',
        'md:static md:z-20 md:translate-x-0',
        isSidebarOpen ? 'md:w-64' : 'md:w-20',
        isDrawerOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <div class="px-4 flex items-center justify-between gap-2 h-16 bg-nav-900 border-b border-nav-800 shrink-0 overflow-hidden">
        <div :class="['flex items-center gap-3 min-w-0', isSidebarOpen ? '' : 'md:hidden']">
          <img
            v-if="configStore.structureInfo.logo_url"
            :src="resolveAssetUrl(configStore.structureInfo.logo_url)"
            class="h-9 w-9 object-contain bg-white rounded-full p-0.5 shrink-0"
            alt="Logo"
          />
          <div v-else class="h-9 w-9 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
            {{ (configStore.structureInfo.name || 'AH').substring(0,2).toUpperCase() }}
          </div>

          <h2 class="text-lg font-bold truncate">{{ configStore.structureInfo.name || 'AH2 Médical' }}</h2>
        </div>

        <!-- Téléphone : fermer le tiroir -->
        <button
          type="button"
          class="md:hidden min-h-11 min-w-11 inline-flex items-center justify-center rounded-control hover:bg-nav-800 focus-visible:outline-2 focus-visible:outline-brand-500"
          :aria-label="t('medicalShell.closeMenu')"
          @click="closeDrawer"
        >
          <XMarkIcon class="h-6 w-6" aria-hidden="true" />
        </button>

        <!-- Tablette / PC : réduire le menu en icônes ou le déployer -->
        <button
          type="button"
          :class="[
            'hidden md:inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-nav-text hover:bg-nav-800 hover:text-white focus-visible:outline-2 focus-visible:outline-brand-500',
            isSidebarOpen ? 'ml-auto' : 'mx-auto'
          ]"
          :aria-label="isSidebarOpen ? t('medicalShell.collapseMenu') : t('medicalShell.expandMenu')"
          :title="isSidebarOpen ? t('medicalShell.collapseMenu') : t('medicalShell.expandMenu')"
          :aria-expanded="isSidebarOpen"
          aria-controls="medical-sidebar"
          @click="toggleSidebar"
        >
          <Bars3CenterLeftIcon v-if="isSidebarOpen" class="h-6 w-6" aria-hidden="true" />
          <Bars3Icon v-else class="h-6 w-6" aria-hidden="true" />
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto py-4 px-3 custom-scrollbar">
        <div v-for="group in menuGroups" :key="group.key" class="mb-5">
          <p :class="['px-3 mb-1 text-sm font-semibold uppercase tracking-wide text-brand-100', isSidebarOpen ? '' : 'md:hidden']">
            {{ t(`medicalShell.sections.${group.key}`) }}
          </p>
          <!-- Menu réduit : un trait remplace l'intertitre -->
          <hr v-if="!isSidebarOpen" class="hidden md:block mx-3 mb-2 border-nav-800" />
          <ul class="space-y-1">
            <li v-for="item in group.items" :key="item.path">
              <router-link
                :to="item.path"
                :aria-current="isActive(item.path) ? 'page' : undefined"
                :title="!isSidebarOpen ? t(item.labelKey) : undefined"
                :class="[
                  'relative flex items-center gap-3 min-h-11 py-2 px-3 rounded-control border-l-4 transition-colors duration-150',
                  isSidebarOpen ? '' : 'md:justify-center',
                  'focus-visible:outline-2 focus-visible:outline-brand-500',
                  isActive(item.path)
                    ? 'bg-nav-800 border-brand-500 font-semibold text-white'
                    : 'border-transparent text-nav-text hover:bg-nav-800 hover:text-white'
                ]"
              >
                <component :is="item.icon" class="h-6 w-6 shrink-0" aria-hidden="true" />
                <span :class="['text-base', isSidebarOpen ? '' : 'md:sr-only']">{{ t(item.labelKey) }}</span>
                <span v-if="item.onlyWhenQuarantine"
                      :class="[
                        'inline-flex items-center justify-center min-w-6 px-1.5 rounded-full text-sm font-bold bg-tone-danger-text text-white',
                        isSidebarOpen ? 'ml-auto' : 'ml-auto md:absolute md:top-0 md:right-0 md:ml-0'
                      ]">
                  {{ quarantineCount }}
                </span>
              </router-link>
            </li>
          </ul>
        </div>
      </nav>
    </aside>

    <div class="flex-1 flex flex-col overflow-hidden w-full min-w-0">

      <header class="bg-white shadow-card px-3 py-2 md:px-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 z-10 relative">

        <div class="flex items-center gap-2 min-w-0">
          <button
            type="button"
            class="md:hidden min-h-11 min-w-11 inline-flex items-center justify-center rounded-control text-ink hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
            :aria-label="t('medicalShell.openMenu')"
            aria-controls="medical-sidebar"
            :aria-expanded="isDrawerOpen"
            @click="isDrawerOpen = true"
          >
            <Bars3Icon class="h-6 w-6" aria-hidden="true" />
          </button>

          <div class="min-w-0">
            <h1 class="text-lg font-semibold text-ink truncate">
              {{ $t('common.welcome') }}, <span class="text-brand-700">{{ displayName }}</span>
              <span class="hidden sm:inline text-sm text-ink-muted ml-2 font-normal">({{ roleLine }})</span>
            </h1>
            <p class="hidden lg:block text-sm text-ink-muted capitalize">{{ todayLabel }}</p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 md:gap-3">
          <ConnectionStatus />

          <div class="flex bg-tone-neutral-bg rounded-control p-1">
            <button
              type="button"
              @click="changeLanguage('fr')"
              :aria-pressed="locale === 'fr'"
              :class="locale === 'fr' ? 'bg-white shadow-card text-ink' : 'text-ink-muted hover:text-ink'"
              class="min-h-9 px-3 rounded-control text-sm font-medium transition-all duration-200 focus-visible:outline-2 focus-visible:outline-brand-600"
            >FR</button>
            <button
              type="button"
              @click="changeLanguage('en')"
              :aria-pressed="locale === 'en'"
              :class="locale === 'en' ? 'bg-white shadow-card text-ink' : 'text-ink-muted hover:text-ink'"
              class="min-h-9 px-3 rounded-control text-sm font-medium transition-all duration-200 focus-visible:outline-2 focus-visible:outline-brand-600"
            >EN</button>
          </div>

          <NotificationBell v-if="authStore.hasRole(['medecin', 'nurse'])" />

          <button
            type="button"
            @click="showAccountModal = true"
            class="min-h-11 min-w-11 inline-flex items-center justify-center rounded-control text-ink-muted hover:text-ink hover:bg-tone-neutral-bg transition focus-visible:outline-2 focus-visible:outline-brand-600"
            :title="$t('common.my_account')"
            :aria-label="$t('common.my_account')"
          >
            <UserCircleIcon class="h-7 w-7" aria-hidden="true" />
          </button>

          <!-- Discret mais visible : bordure + texte, pas de fond rouge plein -->
          <button
            type="button"
            @click="handleLogout"
            class="min-h-11 px-4 rounded-control border border-tone-danger-border text-tone-danger-text text-sm font-semibold hover:bg-tone-danger-bg transition duration-150 focus-visible:outline-2 focus-visible:outline-brand-600"
          >
            {{ $t('common.logout') }}
          </button>
        </div>
      </header>

      <main class="flex-1 overflow-x-hidden overflow-y-auto p-4 md:p-6 bg-page w-full">
        <router-view :key="route.fullPath" />
      </main>

      <AccountModal v-if="showAccountModal" @close="showAccountModal = false" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useConfigStore } from '@/stores/configStore';
import { resolveAssetUrl } from '@/services/api';
import AccountModal from '@/components/account/AccountModal.vue';
import NotificationBell from '@/components/notifications/NotificationBell.vue';
import ConnectionStatus from '@/components/ui/ConnectionStatus.vue';
import { useSyncQuarantineCount } from '@/composables/useSyncQuarantineCount';

import {
  CalendarIcon,
  CalendarDaysIcon,
  TagIcon,
  HeartIcon,
  UserGroupIcon,
  ChartBarIcon,
  BeakerIcon,
  Bars3Icon,
  Bars3CenterLeftIcon,
  XMarkIcon,
  UserCircleIcon,
  ExclamationTriangleIcon,
  BuildingOffice2Icon
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();
const configStore = useConfigStore();
const route = useRoute();
const { locale, t } = useI18n();

// Tiroir du menu : utilisé sous md seulement.
const isDrawerOpen = ref(false);
// À partir de md : menu déployé (libellés) ou réduit en icônes, au choix de l'utilisateur.
const isSidebarOpen = ref(true);
const showAccountModal = ref(false);

// Navigation propre a la fenetre medicale (medecin + nurse partagent le
// meme shell, comme DashboardView cote desktop) - pas de filtrage par
// role ici, contrairement a MainLayout.vue : ce shell n'est jamais charge
// par un autre role (garde deja faite par le routeur, meta.roles).
// Etendu au fil des etapes 2-5 du chantier 3 (Prescription, Dossier
// Medical, Patients, Medecins).
// `group` : intertitre de la refonte UX (activity / medical / followup).
const menuItems = [
  {
    path: '/medical/appointments',
    labelKey: 'appointments.title',
    icon: CalendarIcon,
    group: 'activity',
  },
  {
    path: '/medical/prescriptions',
    labelKey: 'prescriptions.title',
    icon: TagIcon,
    group: 'medical',
  },
  {
    path: '/medical/medical-records',
    labelKey: 'medicalRecords.title',
    icon: HeartIcon,
    group: 'medical',
  },
  {
    path: '/medical/patients',
    labelKey: 'patients.title',
    icon: UserGroupIcon,
    group: 'activity',
  },
  {
    path: '/medical/doctors',
    labelKey: 'doctorKpi.title',
    icon: ChartBarIcon,
    group: 'followup',
  },
  {
    path: '/medical/hospitalizations',
    labelKey: 'hospitalization.title',
    icon: BuildingOffice2Icon,
    group: 'activity',
  },
  {
    path: '/medical/nurse-shifts',
    labelKey: 'nurseShift.title',
    icon: CalendarDaysIcon,
    group: 'activity',
  },
  {
    path: '/medical/lab-results',
    labelKey: 'lab.nav.medical_results',
    icon: BeakerIcon,
    group: 'medical',
  },
  {
    path: '/medical/sync-failures',
    labelKey: 'secretariat.nav.sync_failures',
    icon: ExclamationTriangleIcon,
    onlyWhenQuarantine: true,
    group: 'followup',
  },
];

const quarantineCount = useSyncQuarantineCount();
const visibleMenuItems = computed(() =>
  menuItems.filter((item) => !item.onlyWhenQuarantine || quarantineCount.value > 0)
);

// Ordre des intertitres ; un intertitre sans entrée visible n'est pas affiché.
const GROUP_ORDER = ['activity', 'medical', 'followup'];
const menuGroups = computed(() =>
  GROUP_ORDER
    .map((key) => ({ key, items: visibleMenuItems.value.filter((i) => i.group === key) }))
    .filter((g) => g.items.length)
);

// Nom complet (profil) en premier ; l'identifiant reste affiché à côté. Sessions anciennes sans
// full_name en cache : repli sur l'identifiant seul.
const displayName = computed(
  () => authStore.user?.full_name?.trim() || authStore.user?.username || 'Utilisateur'
);
const roleLine = computed(() => {
  const username = authStore.user?.username;
  const hasFullName = !!authStore.user?.full_name?.trim();
  return hasFullName && username ? `${username}, ${authStore.userRole}` : authStore.userRole;
});

const todayLabel = computed(() =>
  new Date().toLocaleDateString(locale.value === 'en' ? 'en-GB' : 'fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
);

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

const closeDrawer = () => {
  isDrawerOpen.value = false;
};

const changeLanguage = (lang) => {
  locale.value = lang;
  localStorage.setItem('lang', lang);
};

const handleLogout = async () => {
  // authStore.logout() nettoie deja l'etat ET redirige vers /login lui-meme
  // (fin de sa propre fonction). L'appeler sans attendre puis naviguer ici
  // en parallele creait une course : ce router.push('/login') s'executait
  // AVANT que logout() n'ait fini de vider authStore.user/token, et le
  // garde de navigation (router/index.js) voyait alors un utilisateur
  // encore "authentifie" naviguant vers /login -> le redirigeait vers
  // /dashboard (regle "deja connecte + va au login = redirection
  // intelligente"), route reservee a l'admin - d'ou un flash "403 Acces
  // Interdit" au moment meme de la deconnexion (bug reel constate en test
  // navigateur). Attendre logout() avant de naviguer (ou simplement ne pas
  // re-naviguer ici du tout) elimine la course.
  await authStore.logout();
};

const isActive = (path) => {
  return route.path.includes(path);
};

// Le tiroir se referme après chaque navigation et par la touche Échap.
watch(() => route.fullPath, closeDrawer);
const onKeydown = (e) => {
  if (e.key === 'Escape') closeDrawer();
};

onMounted(() => {
  configStore.fetchStructureInfo();
  window.addEventListener('keydown', onKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown);
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: var(--color-nav-900);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: var(--color-nav-800);
  border-radius: 2px;
}
</style>
