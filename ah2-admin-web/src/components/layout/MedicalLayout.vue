<template>
  <div class="flex w-full h-screen bg-gray-50">

    <aside
      :class="[
        'bg-slate-800 text-white flex-shrink-0 transition-all duration-300 ease-in-out flex flex-col z-20',
        isSidebarOpen ? 'w-64' : 'w-20'
      ]"
    >
      <div class="p-4 flex items-center justify-between h-16 bg-slate-900 overflow-hidden">
        <div v-if="isSidebarOpen" class="flex items-center space-x-2 min-w-0">
          <img
            v-if="configStore.structureInfo.logo_url"
            :src="resolveAssetUrl(configStore.structureInfo.logo_url)"
            class="h-8 w-8 object-contain bg-white rounded-full p-0.5 flex-shrink-0"
            alt="Logo"
          />
          <div v-else class="h-8 w-8 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-xs flex-shrink-0">
            {{ (configStore.structureInfo.name || 'AH').substring(0,2).toUpperCase() }}
          </div>

          <h2 class="text-lg font-bold truncate">{{ configStore.structureInfo.name || 'AH2 Médical' }}</h2>
        </div>

        <button
          @click="toggleSidebar"
          :class="[
            'p-1 rounded hover:bg-slate-700 text-gray-400 hover:text-white transition-colors',
            isSidebarOpen ? 'ml-auto' : 'mx-auto'
          ]"
        >
          <Bars3CenterLeftIcon v-if="isSidebarOpen" class="h-6 w-6" />
          <Bars3Icon v-else class="h-6 w-6" />
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto py-4 space-y-2 px-2 custom-scrollbar">
        <router-link
          v-for="item in visibleMenuItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'flex items-center py-2 px-3 rounded transition duration-150 group',
            isActive(item.path)
              ? 'bg-slate-700 font-semibold text-white'
              : 'text-gray-400 hover:bg-slate-700 hover:text-white'
          ]"
          :title="!isSidebarOpen ? t(item.labelKey) : ''"
        >
          <component
            :is="item.icon"
            class="h-6 w-6 flex-shrink-0"
            :class="isSidebarOpen ? 'mr-3' : 'mx-auto'"
          />
          <span v-if="isSidebarOpen" class="whitespace-nowrap transition-opacity duration-200">
            {{ t(item.labelKey) }}
          </span>
          <span v-if="item.onlyWhenQuarantine && isSidebarOpen"
                class="ml-auto inline-flex items-center justify-center min-w-[1.25rem] px-1.5 rounded-full text-xs font-bold bg-red-600 text-white">
            {{ quarantineCount }}
          </span>
        </router-link>
      </nav>
    </aside>

    <div class="flex-1 flex flex-col overflow-hidden w-full">

      <header class="bg-white shadow-md p-4 flex justify-between items-center z-10">

        <h1 class="text-lg font-semibold text-gray-800">
          {{ $t('common.welcome') }}, <span class="text-emerald-600">{{ authStore.user?.username || 'Utilisateur' }}</span>
          <span class="text-xs text-gray-400 ml-2 font-normal">({{ authStore.userRole }})</span>
        </h1>

        <div class="flex items-center space-x-4">
          <div class="flex bg-gray-100 rounded-lg p-1">
            <button
              @click="changeLanguage('fr')"
              :class="locale === 'fr' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >FR</button>
            <button
              @click="changeLanguage('en')"
              :class="locale === 'en' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >EN</button>
          </div>

          <button
            @click="showAccountModal = true"
            class="flex items-center text-gray-600 hover:text-gray-900 text-sm font-medium transition"
            :title="$t('common.my_account')"
          >
            <UserCircleIcon class="h-6 w-6" />
          </button>

          <button
            @click="handleLogout"
            class="bg-red-500 hover:bg-red-600 text-white text-sm font-semibold py-2 px-4 rounded transition duration-150"
          >
            {{ $t('common.logout') }}
          </button>
        </div>
      </header>

      <main class="flex-1 overflow-x-hidden overflow-y-auto p-6 bg-gray-100 w-full">
        <router-view :key="route.fullPath" />
      </main>

      <AccountModal v-if="showAccountModal" @close="showAccountModal = false" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useConfigStore } from '@/stores/configStore';
import { resolveAssetUrl } from '@/services/api';
import AccountModal from '@/components/account/AccountModal.vue';
import { useSyncQuarantineCount } from '@/composables/useSyncQuarantineCount';

import {
  CalendarIcon,
  TagIcon,
  HeartIcon,
  UserGroupIcon,
  ChartBarIcon,
  BeakerIcon,
  Bars3Icon,
  Bars3CenterLeftIcon,
  UserCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();
const configStore = useConfigStore();
const route = useRoute();
const { locale, t } = useI18n();

const isSidebarOpen = ref(true);
const showAccountModal = ref(false);

// Navigation propre a la fenetre medicale (medecin + nurse partagent le
// meme shell, comme DashboardView cote desktop) - pas de filtrage par
// role ici, contrairement a MainLayout.vue : ce shell n'est jamais charge
// par un autre role (garde deja faite par le routeur, meta.roles).
// Etendu au fil des etapes 2-5 du chantier 3 (Prescription, Dossier
// Medical, Patients, Medecins).
const menuItems = [
  {
    path: '/medical/appointments',
    labelKey: 'appointments.title',
    icon: CalendarIcon,
  },
  {
    path: '/medical/prescriptions',
    labelKey: 'prescriptions.title',
    icon: TagIcon,
  },
  {
    path: '/medical/medical-records',
    labelKey: 'medicalRecords.title',
    icon: HeartIcon,
  },
  {
    path: '/medical/patients',
    labelKey: 'patients.title',
    icon: UserGroupIcon,
  },
  {
    path: '/medical/doctors',
    labelKey: 'doctorKpi.title',
    icon: ChartBarIcon,
  },
  {
    path: '/medical/lab-results',
    labelKey: 'lab.nav.medical_results',
    icon: BeakerIcon,
  },
  {
    path: '/medical/sync-failures',
    labelKey: 'secretariat.nav.sync_failures',
    icon: ExclamationTriangleIcon,
    onlyWhenQuarantine: true,
  },
];

const quarantineCount = useSyncQuarantineCount();
const visibleMenuItems = computed(() =>
  menuItems.filter((item) => !item.onlyWhenQuarantine || quarantineCount.value > 0)
);

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
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

onMounted(() => {
  configStore.fetchStructureInfo();
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: #1e293b;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 2px;
}
</style>
