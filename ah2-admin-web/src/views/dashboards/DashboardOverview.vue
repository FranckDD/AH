<template>
  <div class="space-y-8 w-full">
    
    <div class="flex flex-col md:flex-row md:items-center md:justify-between bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <div>
        <h1 class="text-3xl font-extrabold text-gray-800 tracking-tight">
          {{ $t('dashboard.title') }}
        </h1>
        <p class="mt-2 text-gray-500 flex items-center">
          <span class="inline-block w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
          {{ $t('dashboard.subtitle') }} {{ currentDate }}
        </p>
      </div>
      
      <div class="mt-4 md:mt-0 flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-3 items-end">
        <div class="flex flex-col">
          <label class="text-xs font-medium text-gray-500 mb-1">{{ $t('dashboard.filters.start_date') }}</label>
          <input type="date" v-model="dashboardStore.filters.startDate" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-green-500 focus:border-green-500" />
        </div>

        <div class="flex flex-col">
          <label class="text-xs font-medium text-gray-500 mb-1">{{ $t('dashboard.filters.end_date') }}</label>
          <input type="date" v-model="dashboardStore.filters.endDate" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-green-500 focus:border-green-500" />
        </div>

        <div class="flex space-x-3 mt-auto">
             <button @click="resetToToday" class="flex items-center px-4 py-2 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 border border-gray-200 transition font-medium text-sm">
                <span>🔄 {{ $t('dashboard.actions.refresh') }}</span>
             </button>
            
            <button @click="applyFilters" class="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 shadow-md transition font-medium text-sm">
                <span>🔍 {{ $t('dashboard.filters.apply') }}</span>
            </button>
        </div>
      </div>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      
      <StatCard 
        :title="$t('dashboard.stats.income')" 
        :value="formatCurrency(dashboardStore.stats.income)" 
        :icon="BanknotesIcon" 
        colorClass="bg-green-50"
        iconColor="text-green-600"
        trend="Recettes"
        :trendIsPositive="true"
      />
      
      <StatCard 
        :title="$t('dashboard.stats.withdrawals')" 
        :value="formatCurrency(dashboardStore.stats.withdrawals)" 
        :icon="ArrowTrendingDownIcon" 
        colorClass="bg-red-50"
        iconColor="text-red-600"
        trend="Dépenses"
        :trendIsPositive="false" 
      />

      <StatCard 
        :title="$t('finance.balance')" 
        :value="formatCurrency(dashboardStore.stats.income - dashboardStore.stats.withdrawals)" 
        :icon="dashboardStore.stats.income >= dashboardStore.stats.withdrawals ? ArrowTrendingUpIcon : ArrowTrendingDownIcon" 
        :colorClass="dashboardStore.stats.income >= dashboardStore.stats.withdrawals ? 'bg-blue-50' : 'bg-orange-50'"
        :iconColor="dashboardStore.stats.income >= dashboardStore.stats.withdrawals ? 'text-blue-600' : 'text-orange-600'"
        trend="Solde Période"
        :trendIsPositive="dashboardStore.stats.income >= dashboardStore.stats.withdrawals"
      />

      <StatCard 
        :title="$t('dashboard.stats.patients')" 
        :value="dashboardStore.stats.activePatients" 
        :icon="UserGroupIcon" 
        colorClass="bg-indigo-50"
        iconColor="text-indigo-600"
        trend="Admissions (Mois)"
        :trendIsPositive="true"
      />
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex items-center justify-between">
        <div class="flex items-center">
          <div class="p-3 bg-indigo-50 rounded-xl mr-4">
             <SignalIcon class="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <p class="text-sm text-gray-500 font-medium">{{ $t('dashboard.stats.users_online') }}</p> 
            <p class="text-xl font-bold text-gray-900">{{ dashboardStore.stats.onlineUsers }} inscrits</p>
          </div>
        </div>
      </div>

       <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition" @click="$router.push('/dashboard/toxico')">
        <div class="flex items-center">
          <div class="p-3 bg-red-50 rounded-xl mr-4">
             <ExclamationTriangleIcon class="h-6 w-6 text-red-600" />
          </div>
          <div>
            <p class="text-sm text-gray-500 font-medium">{{ $t('dashboard.stats.alerts') }}</p> 
            <p class="text-xl font-bold text-gray-900">Voir Alertes</p>
          </div>
        </div>
      </div>

       <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex items-center justify-between">
        <div class="flex items-center">
          <div class="p-3 bg-purple-50 rounded-xl mr-4">
             <HomeModernIcon class="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <p class="text-sm text-gray-500 font-medium">{{ $t('dashboard.stats.bed_occupancy') }}</p> 
            <p class="text-xl font-bold text-gray-900">--</p>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      
      <div class="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="p-6 border-b border-gray-100 flex justify-between items-center">
          <h3 class="text-lg font-bold text-gray-900">
            {{ $t('dashboard.table_title', 'Dernières Activités Financières') }}
          </h3>
          <button @click="$router.push('/dashboard/finance')" class="text-sm text-green-600 hover:text-green-700 font-medium">
            Voir tout
          </button>
        </div>
        
        <div class="overflow-x-auto">
          <div v-if="dashboardStore.isLoading" class="p-6 text-center text-gray-500">Chargement...</div>
          
          <table v-else class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                <th class="px-6 py-4 font-semibold">Description</th> 
                <th class="px-6 py-4 font-semibold">Date</th>
                <th class="px-6 py-4 font-semibold text-right">Montant</th>
                <th class="px-6 py-4 font-semibold">Type</th>
                <th class="px-6 py-4 font-semibold">Statut</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="item in dashboardStore.recentActivities" :key="item.id" class="hover:bg-gray-50 transition">
                <td class="px-6 py-4 font-medium text-gray-900">
                    {{ item.label }}
                    <span v-if="item.description && item.description !== item.label" class="block text-xs text-gray-500 font-normal truncate max-w-[200px]">{{ item.description }}</span>
                </td>
                <td class="px-6 py-4 text-gray-500 text-sm">{{ formatDate(item.date) }}</td>
                <td class="px-6 py-4 font-bold text-gray-900 text-right">{{ formatCurrency(item.amount) }}</td>
                <td class="px-6 py-4 text-sm">
                    <span v-if="item.type === 'INCOME'" class="text-green-600 bg-green-50 px-2 py-1 rounded text-xs font-bold">Entrée</span>
                    <span v-else class="text-red-600 bg-red-50 px-2 py-1 rounded text-xs font-bold">Sortie</span>
                </td>
                <td class="px-6 py-4">
                    <span class="h-2 w-2 rounded-full inline-block mr-2" :class="item.status === 'active' || item.status === 'Validé' ? 'bg-green-500' : 'bg-gray-400'"></span>
                    <span class="text-xs text-gray-600">{{ item.status }}</span>
                </td>
              </tr>
              <tr v-if="dashboardStore.recentActivities.length === 0">
                  <td colspan="5" class="px-6 py-4 text-center text-gray-500 italic">Aucune activité récente.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="bg-gradient-to-br from-green-600 to-emerald-800 rounded-2xl shadow-lg p-6 text-white flex flex-col justify-between">
        <div>
          <h3 class="text-xl font-bold mb-2">Actions Rapides</h3>
          <p class="text-green-100 text-sm mb-6">Accès direct aux fonctions clés.</p>
          
          <div class="space-y-3">
            <button @click="$router.push('/dashboard/users')" class="w-full flex items-center p-3 bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-xl transition border border-white/10">
              <UserGroupIcon class="h-5 w-5 mr-3 text-green-200" />
              <span class="font-medium">{{ $t('dashboard.actions.manage_staff') }}</span>
            </button>
            
            <button @click="showAdmissionModal = true" class="w-full flex items-center p-3 bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-xl transition border border-white/10">
              <PlusCircleIcon class="h-5 w-5 mr-3 text-green-200" />
              <span class="font-medium">{{ $t('dashboard.actions.new_admission') }}</span>
            </button>

            <button @click="showFinanceModal = true" class="w-full flex items-center p-3 bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-xl transition border border-white/10">
              <BanknotesIcon class="h-5 w-5 mr-3 text-green-200" />
              <span class="font-medium">{{ $t('dashboard.actions.payment') }}</span>
            </button>
          </div>
        </div>
        
        <div class="mt-8 pt-6 border-t border-white/20 text-center text-xs text-green-200">
          Support technique : 699 99 99 99
        </div>
      </div>

    </div>

    <ToxicoAdmissionModal
        v-if="showAdmissionModal"
        @close="showAdmissionModal = false"
        @save="handleAdmissionSaved"
    />

    <FinanceModal
        v-if="showFinanceModal"
        type="INCOME" 
        @close="showFinanceModal = false"
        @save="handleFinanceSaved"
    />

  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDashboardStore } from '@/stores/dashboardStore'; 
import StatCard from '@/components/dashboard/StatCard.vue';

// 🟢 IMPORTS DES MODALES EXISTANTES
// Assurez-vous que les chemins correspondent exactement à votre arborescence
import ToxicoAdmissionModal from '@/components/toxico/ToxicoAdmissionModal.vue';
import FinanceModal from '@/components/finance/FinanceModal.vue'; 
import { useConfigStore } from '@/stores/configStore';

import { 
  BanknotesIcon, UserGroupIcon, HomeModernIcon, 
  ArrowTrendingDownIcon, ArrowTrendingUpIcon, ClockIcon, 
  SignalIcon, PlusCircleIcon, MagnifyingGlassIcon, ExclamationTriangleIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const dashboardStore = useDashboardStore();

// --- ÉTATS LOCAUX ---
const showAdmissionModal = ref(false);
const showFinanceModal = ref(false);

// --- LIFECYCLE ---
onMounted(() => {
    // Charge les données au démarrage
    dashboardStore.fetchDashboardData();
});

// --- ACTIONS UI ---
const applyFilters = () => {
    dashboardStore.fetchDashboardData();
};

const resetToToday = () => {
    const today = new Date().toISOString().substring(0, 10);
    dashboardStore.setDates(today, today);
};

// --- CALLBACKS APRÈS ACTIONS ---
const handleAdmissionSaved = () => {
    showAdmissionModal.value = false;
    alert("Admission enregistrée !");
    // On met à jour le dashboard pour voir la stat "Active Patients" augmenter
    dashboardStore.fetchDashboardData();
};

const handleFinanceSaved = () => {
    showFinanceModal.value = false;
    alert("Transaction enregistrée !");
    // On met à jour le dashboard pour voir les revenus augmenter
    dashboardStore.fetchDashboardData();
};
const configStore = useConfigStore();

onMounted(() => {
    dashboardStore.fetchDashboardData();
    configStore.fetchStructureInfo(); // S'assurer que les infos sont chargées
});

// --- HELPERS D'AFFICHAGE ---
const currentDate = computed(() => {
  return new Date().toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
});

const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value);
};

const formatDate = (dateStr) => {
    if(!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR') + ' ' + date.toLocaleTimeString('fr-FR', {hour: '2-digit', minute:'2-digit'});
    } catch (e) { return dateStr; }
};
</script>