<template>
    <div class="flex w-full h-screen bg-gray-50"> 
        
        <!-- SIDEBAR -->
        <!-- Correction : Fusion des classes pour éviter l'erreur de parsing -->
        <aside 
            :class="[
                'bg-gray-800 text-white flex-shrink-0 transition-all duration-300 ease-in-out flex flex-col z-20',
                isSidebarOpen ? 'w-64' : 'w-20'
            ]"
        >
            <!-- ENTÊTE SIDEBAR -->
            <div class="p-4 flex items-center justify-between h-16 bg-gray-900 overflow-hidden">
                <div v-if="isSidebarOpen" class="flex items-center space-x-2 min-w-0">
                    <img 
                        v-if="configStore.structureInfo.logo_url" 
                        :src="configStore.structureInfo.logo_url" 
                        class="h-8 w-8 object-contain bg-white rounded-full p-0.5 flex-shrink-0" 
                        alt="Logo"
                    />
                    <div v-else class="h-8 w-8 rounded-full bg-green-600 flex items-center justify-center font-bold text-xs flex-shrink-0">
                        {{ (configStore.structureInfo.name || 'AH').substring(0,2).toUpperCase() }}
                    </div>
                    
                    <h2 class="text-lg font-bold truncate">{{ configStore.structureInfo.name || 'AH2 Dashboard' }}</h2>
                </div>

                <button 
                    @click="toggleSidebar" 
                    :class="[
                        'p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors',
                        isSidebarOpen ? 'ml-auto' : 'mx-auto'
                    ]"
                >
                    <Bars3CenterLeftIcon v-if="isSidebarOpen" class="h-6 w-6" />
                    <Bars3Icon v-else class="h-6 w-6" />
                </button>
            </div>
            
            <!-- NAVIGATION -->
            <nav class="flex-1 overflow-y-auto py-4 space-y-2 px-2 custom-scrollbar">
                
                <router-link 
                    to="/dashboard/overview" 
                    :class="[
                        'flex items-center py-2 px-3 rounded transition duration-150 group',
                        route.path.includes('/dashboard/overview') 
                            ? 'bg-gray-700 font-semibold text-white' 
                            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    ]"
                    :title="!isSidebarOpen ? $t('common.dashboard') : ''"
                >
                    <HomeIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" />
                    <span v-if="isSidebarOpen" class="whitespace-nowrap transition-opacity duration-200">
                        {{ $t('common.dashboard') }}
                    </span>
                </router-link>

                <router-link 
                    to="/dashboard/toxico-dashboard" 
                    :class="[
                        'flex items-center py-2 px-3 rounded transition duration-150 group',
                        route.path.includes('/dashboard/toxico-dashboard') 
                            ? 'bg-gray-700 font-semibold text-white' 
                            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    ]"
                    :title="!isSidebarOpen ? t('toxico.dashboard.title') : ''"
                >
                    <ChartBarIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" /> 
                    <span v-if="isSidebarOpen">{{ t('toxico.dashboard.title') }}</span>
                </router-link>

                <router-link 
                    to="/dashboard/toxico" 
                    :class="[
                        'flex items-center py-2 px-3 rounded transition duration-150 group',
                        (route.path.includes('/dashboard/toxico') && !route.path.includes('/dashboard/toxico-dashboard'))
                            ? 'bg-gray-700 font-semibold text-white' 
                            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    ]"
                    :title="!isSidebarOpen ? t('toxico.title') : ''"
                >
                    <BeakerIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" />
                    <span v-if="isSidebarOpen">{{ t('toxico.title') }}</span>
                </router-link>
    
                <router-link 
                    to="/dashboard/finance" 
                    :class="[
                        'flex items-center py-2 px-3 rounded transition duration-150 group',
                        route.path.includes('/dashboard/finance') 
                            ? 'bg-gray-700 font-semibold text-white' 
                            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    ]"
                    :title="!isSidebarOpen ? t('finance.title') : ''"
                >
                    <BanknotesIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" />
                    <span v-if="isSidebarOpen">{{ t('finance.title') }}</span>
                </router-link>
                
                <router-link 
                    to="/dashboard/users" 
                    :class="[
                        'flex items-center py-2 px-3 rounded transition duration-150 group',
                        route.path.includes('/dashboard/users') 
                            ? 'bg-gray-700 font-semibold text-white' 
                            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    ]"
                    :title="!isSidebarOpen ? $t('common.users') : ''"
                >
                    <UsersIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" />
                    <span v-if="isSidebarOpen">{{ $t('common.users') }}</span>
                </router-link>

                <router-link 
                    to="/dashboard/patients" 
                    :class="[
                        'flex items-center py-2 px-3 rounded transition duration-150 group',
                        route.path.includes('/dashboard/patients') 
                            ? 'bg-gray-700 font-semibold text-white' 
                            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    ]"
                    :title="!isSidebarOpen ? $t('patients.title') : ''"
                >
                    <ClipboardDocumentListIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" />
                    <span v-if="isSidebarOpen">{{ $t('patients.title') }}</span>
                </router-link>

                <router-link 
                    to="/dashboard/stock" 
                    :class="[
                        'flex items-center py-2 px-3 rounded transition duration-150 group',
                        route.path.includes('/dashboard/stock') 
                            ? 'bg-gray-700 font-semibold text-white' 
                            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    ]"
                    :title="!isSidebarOpen ? t('stock.title') : ''"
                >
                    <CubeIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" />
                    <span v-if="isSidebarOpen">{{ t('stock.title') }}</span>
                </router-link>

                <router-link 
                    to="/dashboard/logs" 
                    :class="[
                        'flex items-center py-2 px-3 rounded transition duration-150 group',
                        route.path.includes('/dashboard/logs') 
                            ? 'bg-gray-700 font-semibold text-white' 
                            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    ]"
                    :title="!isSidebarOpen ? t('tech.title') : ''"
                >
                    <ShieldCheckIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" />
                    <span v-if="isSidebarOpen">{{ t('tech.title') }}</span>
                </router-link>

                <div class="mt-8 pt-4 border-t border-gray-700">
                    <router-link 
                        to="/dashboard/configuration" 
                        :class="[
                            'flex items-center py-2 px-3 rounded transition duration-150 group',
                            route.path.includes('/dashboard/configuration') 
                                ? 'bg-gray-700 font-semibold text-white' 
                                : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                        ]"
                        :title="!isSidebarOpen ? t('config.title') : ''"
                    >
                        <CogIcon class="h-6 w-6 flex-shrink-0" :class="isSidebarOpen ? 'mr-3' : 'mx-auto'" /> 
                        <span v-if="isSidebarOpen">{{ t('config.title') }}</span>
                    </router-link>
                </div>

            </nav>
        </aside>

        <div class="flex-1 flex flex-col overflow-hidden w-full">
            <header class="bg-white shadow-md p-4 flex justify-between items-center z-10">
                
                <h1 class="text-lg font-semibold text-gray-800">
                    {{ $t('common.welcome') }}, <span class="text-green-600">{{ authStore.user?.username || 'Utilisateur' }}</span>
                </h1>
                
                <div class="flex items-center space-x-4">
                    
                    <div class="flex bg-gray-100 rounded-lg p-1">
                        <button 
                            @click="changeLanguage('fr')"
                            :class="locale === 'fr' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
                            class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
                        >
                            FR
                        </button>
                        <button 
                            @click="changeLanguage('en')"
                            :class="locale === 'en' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
                            class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
                        >
                            EN
                        </button>
                    </div>

                    <button 
                        @click="handleLogout"
                        class="bg-red-500 hover:bg-red-600 text-white text-sm font-semibold py-2 px-4 rounded transition duration-150"
                    >
                        {{ $t('common.logout') }} 
                    </button>
                </div>
            </header>

            <main class="flex-1 overflow-x-hidden overflow-y-auto p-6 bg-gray-100 w-full">
                <!-- key unique pour forcer le re-rendu -->
                <router-view :key="route.fullPath" />
            </main>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n'; 
import { useConfigStore } from '@/stores/configStore';

import { 
    HomeIcon, UsersIcon, ClipboardDocumentListIcon, BanknotesIcon, 
    BeakerIcon, ChartBarIcon, CogIcon, ShieldCheckIcon, CubeIcon,
    Bars3Icon, Bars3CenterLeftIcon 
} from '@heroicons/vue/24/outline'; 

const authStore = useAuthStore();
const configStore = useConfigStore();
const router = useRouter();
const route = useRoute();
const { locale, t } = useI18n(); 

const isSidebarOpen = ref(true);

const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value;
};

const changeLanguage = (lang) => {
    locale.value = lang;
    localStorage.setItem('lang', lang);
};

const handleLogout = () => {
    authStore.logout();
    router.push('/login');
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
  background: #1f2937; 
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #374151; 
  border-radius: 2px;
}
</style>