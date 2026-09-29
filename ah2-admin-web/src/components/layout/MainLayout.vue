<template>
  <div class="flex w-full h-screen bg-gray-50">

    <aside 
      :class="[
        'bg-gray-800 text-white shrink-0 transition-all duration-300 ease-in-out flex flex-col z-20',
        isSidebarOpen ? 'w-64' : 'w-20'
      ]"
    >
      <div class="p-4 flex items-center justify-between h-16 bg-gray-900 overflow-hidden">
        <div v-if="isSidebarOpen" class="flex items-center space-x-2 min-w-0">
           <img 
            v-if="configStore.structureInfo.logo_url"
            :src="resolveAssetUrl(configStore.structureInfo.logo_url)"
            class="h-8 w-8 object-contain bg-white rounded-full p-0.5 shrink-0" 
            alt="Logo"
          />
          <div v-else class="h-8 w-8 rounded-full bg-green-600 flex items-center justify-center font-bold text-xs shrink-0">
            {{ (configStore.structureInfo.name || 'AH').substring(0,2).toUpperCase() }}
          </div>
          
          <h2 class="text-lg font-bold truncate">{{ configStore.structureInfo.name || 'AH2 Dashboard' }}</h2>
        </div>

        <button 
          @click="toggleSidebar" 
          :class="[
            'p-1 rounded-sm hover:bg-gray-700 text-gray-400 hover:text-white transition-colors',
            isSidebarOpen ? 'ml-auto' : 'mx-auto'
          ]"
        >
          <Bars3CenterLeftIcon v-if="isSidebarOpen" class="h-6 w-6" />
          <Bars3Icon v-else class="h-6 w-6" />
        </button>
      </div>
      
      <nav class="flex-1 overflow-y-auto py-4 space-y-2 px-2 custom-scrollbar">
        
        <template v-for="item in filteredMenu" :key="item.path">
            
            <div v-if="item.separator" class="mt-8 pt-4 border-t border-gray-700 mx-2"></div>

            <router-link 
              :to="item.path" 
              :class="[
                'flex items-center py-2 px-3 rounded-sm transition duration-150 group',
                isActive(item.path)
                  ? 'bg-gray-700 font-semibold text-white' 
                  : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              ]"
              :title="!isSidebarOpen ? t(item.labelKey) : ''"
            >
              <component 
                :is="item.icon" 
                class="h-6 w-6 shrink-0" 
                :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" 
              />
              
              <span v-if="isSidebarOpen" class="whitespace-nowrap transition-opacity duration-200">
                {{ t(item.labelKey) }}
              </span>
            </router-link>

        </template>

      </nav>
    </aside>

    <div class="flex-1 flex flex-col overflow-hidden w-full">
      
      <header class="bg-white shadow-md p-4 flex justify-between items-center z-10">
        
        <h1 class="text-lg font-semibold text-gray-800">
          {{ $t('common.welcome') }}, <span class="text-green-600">{{ authStore.user?.username || 'Utilisateur' }}</span>
          <span class="text-xs text-gray-400 ml-2 font-normal">({{ authStore.userRole }})</span>
        </h1>
        
        <div class="flex items-center space-x-4">
          <div class="flex bg-gray-100 rounded-lg p-1">
            <button 
              @click="changeLanguage('fr')"
              :class="locale === 'fr' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >FR</button>
            <button 
              @click="changeLanguage('en')"
              :class="locale === 'en' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >EN</button>
          </div>

          <NotificationBell v-if="authStore.hasRole(['admin', 'promoteur', 'secretaire'])" />

          <button
            @click="showAccountModal = true"
            class="flex items-center text-gray-600 hover:text-gray-900 text-sm font-medium transition"
            :title="$t('common.my_account')"
          >
            <UserCircleIcon class="h-6 w-6" />
          </button>

          <button
            @click="handleLogout"
            class="bg-red-500 hover:bg-red-600 text-white text-sm font-semibold py-2 px-4 rounded-sm transition duration-150"
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
import { ref, onMounted, computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n'; 
import { useConfigStore } from '@/stores/configStore';
import { resolveAssetUrl } from '@/services/api';
import AccountModal from '@/components/account/AccountModal.vue';
import NotificationBell from '@/components/notifications/NotificationBell.vue';

// J'ai ajouté ExclamationCircleIcon pour Toxico, pour laisser BeakerIcon au Labo
import {
  HomeIcon, UsersIcon, ClipboardDocumentListIcon, BanknotesIcon,
  BeakerIcon, ChartBarIcon, CogIcon, ShieldCheckIcon, CubeIcon,
  Bars3Icon, Bars3CenterLeftIcon, ExclamationCircleIcon, UserCircleIcon,
  CheckBadgeIcon, ClockIcon
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();
const configStore = useConfigStore();
const route = useRoute();
const { locale, t } = useI18n();

const isSidebarOpen = ref(true);
const showAccountModal = ref(false);

// --- 1. DÉFINITION DES RÔLES (Constantes) ---
const ROLES = {
  ADMIN: 'admin',
  PSYCHOLOGIST: 'Psychologist',
  SPIRITUAL: 'SpiritualCounsellor',
  TOXICO_MANAGER: 'ToxicoManager',
  ASSISTANT: 'Assistant',
  LABORANTIN: 'laborantin', // ✅ Ajout du rôle laborantin
  PROMOTEUR: 'promoteur'
};

// --- 2. STRUCTURE DU MENU (Data Driven) ---
const menuItems = [
  {
    path: '/dashboard/overview',
    labelKey: 'common.dashboard',
    icon: HomeIcon,
    roles: [ROLES.ADMIN] 
  },
  {
    path: '/dashboard/toxico-dashboard',
    labelKey: 'toxico.dashboard.title',
    icon: ChartBarIcon,
    roles: [ROLES.PSYCHOLOGIST, ROLES.SPIRITUAL, ROLES.TOXICO_MANAGER, ROLES.ASSISTANT]
  },
  {
    path: '/dashboard/toxico',
    labelKey: 'toxico.title',
    icon: ExclamationCircleIcon, // 🔄 Changement d'icône pour éviter doublon avec Labo
    roles: [ROLES.PSYCHOLOGIST, ROLES.SPIRITUAL, ROLES.TOXICO_MANAGER, ROLES.ASSISTANT]
  },
  // 🟢 AJOUT MODULE LABORATOIRE 🟢
  {
    path: '/dashboard/labo', // Pointe vers le layout ou la page par défaut du labo
    labelKey: 'labo.title',  // ⚠️ Pense à ajouter 'labo.title': 'Laboratoire' dans tes fichiers i18n
    icon: BeakerIcon,        // L'icône "Tube à essai" convient parfaitement ici
    // Visible pour : Laborantin et ToxicoManager (en plus de l'Admin implicite)
    roles: [ROLES.LABORANTIN, ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/finance',
    labelKey: 'finance.title',
    icon: BanknotesIcon,
    roles: [ROLES.ADMIN]
  },
  {
    path: '/dashboard/discount-review',
    labelKey: 'discount_review.title',
    icon: CheckBadgeIcon,
    roles: [ROLES.ADMIN, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/discount-history',
    labelKey: 'discount_history.title',
    icon: ClockIcon,
    roles: [ROLES.ADMIN, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/users',
    labelKey: 'common.users',
    icon: UsersIcon,
    roles: [ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/patients',
    labelKey: 'patients.title',
    icon: ClipboardDocumentListIcon,
    roles: [ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/stock',
    labelKey: 'stock.title',
    icon: CubeIcon,
    roles: [ROLES.TOXICO_MANAGER, ROLES.ASSISTANT]
  },
  {
    path: '/dashboard/logs',
    labelKey: 'tech.title',
    icon: ShieldCheckIcon,
    roles: [ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/configuration',
    labelKey: 'config.title',
    icon: CogIcon,
    separator: true,
    roles: [ROLES.TOXICO_MANAGER]
  }
];

// --- 3. FILTRAGE INTELLIGENT (Computed) ---
const filteredMenu = computed(() => {
    // Si ADMIN, on retourne tout (Super User)
    if (authStore.isAdmin || authStore.hasRole([ROLES.ADMIN])) {
        return menuItems;
    }

    // Sinon, on filtre selon le tableau 'roles' de chaque item
    return menuItems.filter(item => {
        if (!item.roles) return false;
        // La condition magique : est-ce que mon rôle est dans la liste autorisée ?
        return authStore.hasRole(item.roles);
    });
});

// --- HELPER FONCTIONS ---
const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value;
};

const changeLanguage = (lang) => {
    locale.value = lang;
    localStorage.setItem('lang', lang);
};

// authStore.logout() nettoie deja l'etat ET redirige vers /login lui-meme -
// voir MedicalLayout.vue pour le detail de la course que ca evite.
const handleLogout = async () => {
    await authStore.logout();
};

const isActive = (path) => {
    return route.path.includes(path);
};

onMounted(() => {
    configStore.fetchStructureInfo();
    // Seuls admin/promoteur peuvent atteindre un ecran caisse/finance
    // depuis ce shell (voir router/index.js) - on evite un appel/403
    // inutile en console pour les autres roles (medecin, nurse,
    // laborantin, ...) qui ne declenchent jamais d'impression.
    if (authStore.hasRole([ROLES.ADMIN, ROLES.PROMOTEUR])) {
        configStore.fetchTicketPrintToken();
    }
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: #1f2937; 
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #374151; 
  border-radius: 2px;
}
</style>