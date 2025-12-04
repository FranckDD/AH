<template>
    <div class="flex w-full h-screen bg-gray-50"> 
        
        <aside class="w-64 bg-gray-800 text-white p-4 flex-shrink-0">
            <h2 class="text-xl font-bold mb-6">AH2 Dashboard</h2>
            
            <nav class="space-y-2">
                
                <router-link 
                    to="/dashboard/overview" 
                    class="flex items-center py-2 px-4 rounded transition duration-150"
                    :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/overview'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/overview')}"
                >
                    <HomeIcon class="h-5 w-5 mr-3" />
                    {{ $t('common.dashboard') }}
                </router-link>

                <router-link 
                    to="/dashboard/toxico-dashboard" 
                    class="flex items-center py-2 px-4 rounded transition duration-150"
                    :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/toxico-dashboard'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/toxico-dashboard')}"
                >
                    <ChartBarIcon class="h-5 w-5 mr-3" /> {{ t('toxico.dashboard.title') }}
                </router-link>

                <router-link 
                    to="/dashboard/toxico" 
                    class="flex items-center py-2 px-4 rounded transition duration-150"
                    :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/toxico'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/toxico')}"
                >
                    <BeakerIcon class="h-5 w-5 mr-3" />
                    {{ t('toxico.title') }}
                </router-link>
 

                <router-link 
                    to="/dashboard/finance" 
                    class="flex items-center py-2 px-4 rounded transition duration-150"
                    :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/finance'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/finance')}"
                >
                    <BanknotesIcon class="h-5 w-5 mr-3" />
                    {{ t('finance.title') }}
                </router-link>
                

                <router-link 
                    to="/dashboard/users" 
                    class="flex items-center py-2 px-4 rounded transition duration-150"
                    :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/users'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/users')}"
                >
                    <UsersIcon class="h-5 w-5 mr-3" />
                    {{ $t('common.users') }}
                </router-link>

                <router-link 
                    to="/dashboard/patients" 
                    class="flex items-center py-2 px-4 rounded transition duration-150"
                    :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/patients'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/patients')}"
                >
                    <ClipboardDocumentListIcon class="h-5 w-5 mr-3" />
                    {{ $t('patients.title') }}
                </router-link>
                <router-link 
                    to="/dashboard/stock" 
                    class="flex items-center py-2 px-4 rounded transition duration-150"
                    :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/stock'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/stock')}"
                >
                    <CubeIcon class="h-5 w-5 mr-3" />
                    {{ t('stock.title') }}
                </router-link>

                <router-link 
                    to="/dashboard/logs" 
                    class="flex items-center py-2 px-4 rounded transition duration-150"
                    :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/logs'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/logs')}"
                >
                    <ShieldCheckIcon class="h-5 w-5 mr-3" />
                    {{ t('tech.title') }}
                </router-link>

                <div class="mt-8 pt-4 border-t border-gray-700">
                    <router-link 
                        to="/dashboard/configuration" 
                        class="flex items-center py-2 px-4 rounded transition duration-150"
                        :class="{'bg-gray-700 font-semibold': $route.path.includes('/dashboard/configuration'), 'hover:bg-gray-700': !$route.path.includes('/dashboard/configuration')}"
                    >
                        <CogIcon class="h-5 w-5 mr-3" /> {{ t('config.title') }}
                    </router-link>
                </div>

                </nav>
        </aside>

        <div class="flex-1 flex flex-col overflow-hidden w-full">
            <header class="bg-white shadow-md p-4 flex justify-between items-center">
                
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
                <router-view />
            </main>
        </div>
    </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router'; 
import { useI18n } from 'vue-i18n'; 

// 🟢 CORRECTION 1: Ajout de BanknotesIcon dans l'import
import { 
    HomeIcon, 
    UsersIcon, 
    ClipboardDocumentListIcon,
    BanknotesIcon, // <-- AJOUTÉ
    BeakerIcon, //
    ChartBarIcon,
    CogIcon,
    ShieldCheckIcon,
    CubeIcon
} from '@heroicons/vue/24/outline'; 


const authStore = useAuthStore();
const router = useRouter();
// 🟢 CORRECTION 2: Extraction de 't' pour pouvoir l'utiliser dans le template
const { locale, t } = useI18n(); 

const changeLanguage = (lang) => {
    locale.value = lang;
    localStorage.setItem('lang', lang);
};

const handleLogout = () => {
    authStore.logout();
    router.push('/login');
};
</script>