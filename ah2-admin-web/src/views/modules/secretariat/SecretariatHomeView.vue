<template>
  <div class="space-y-8 w-full">

    <div class="flex flex-col md:flex-row md:items-center md:justify-between bg-white p-6 rounded-2xl shadow-xs border border-gray-100">
      <h1 class="text-3xl font-extrabold text-gray-800 tracking-tight">{{ t('secretariat.home.title') }}</h1>

      <div class="mt-4 md:mt-0 flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-3 items-end">
        <div class="flex flex-col">
          <label class="text-xs font-medium text-gray-500 mb-1">{{ t('secretariat.home.period_from') }}</label>
          <input type="date" v-model="homeStore.filters.startDate" @change="applyFilters" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-teal-500 focus:border-teal-500" />
        </div>
        <div class="flex flex-col">
          <label class="text-xs font-medium text-gray-500 mb-1">{{ t('secretariat.home.period_to') }}</label>
          <input type="date" v-model="homeStore.filters.endDate" @change="applyFilters" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-teal-500 focus:border-teal-500" />
        </div>
      </div>
    </div>

    <div v-if="homeStore.isLoading" class="p-10 text-center text-gray-500">{{ t('common.loading') }}</div>

    <template v-else>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard :title="t('secretariat.home.total_paid')" :value="valeurAffichee('totalPaid', formatCurrency(homeStore.stats.totalPaid))" :icon="BanknotesIcon" colorClass="bg-green-50" iconColor="text-green-600" />
        <StatCard :title="t('secretariat.home.total_withdrawn')" :value="valeurAffichee('totalWithdrawn', formatCurrency(homeStore.stats.totalWithdrawn))" :icon="ArrowTrendingDownIcon" colorClass="bg-red-50" iconColor="text-red-600" />
        <StatCard :title="t('secretariat.home.balance')" :value="soldeAffiche" :icon="ArrowTrendingUpIcon" colorClass="bg-blue-50" iconColor="text-blue-600" />
        <StatCard :title="t('secretariat.home.remaining_due')" :value="valeurAffichee('remainingDue', formatCurrency(homeStore.stats.remainingDue))" :icon="ExclamationTriangleIcon" colorClass="bg-orange-50" iconColor="text-orange-600" />
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard :title="t('secretariat.home.critical_stock')" :value="homeStore.stats.criticalStockCount" :icon="CubeIcon" colorClass="bg-red-50" iconColor="text-red-600" />
        <StatCard :title="t('secretariat.home.expiring_stock')" :value="homeStore.stats.expiringStockCount" :icon="ClockIcon" colorClass="bg-amber-50" iconColor="text-amber-600" />
        <StatCard :title="t('secretariat.home.consultations_period')" :value="homeStore.stats.consultationsCount" :icon="SparklesIcon" colorClass="bg-teal-50" iconColor="text-teal-600" />
      </div>

      <div class="bg-white rounded-2xl shadow-xs border border-gray-100 overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
          <CubeIcon class="h-5 w-5 text-red-600" />
          <h3 class="text-sm font-bold text-gray-700 uppercase tracking-wide">{{ t('secretariat.home.critical_stock_table_title') }}</h3>
        </div>
        <div v-if="homeStore.indisponibles.includes('criticalStockItems')" class="px-6 py-6 text-center text-sm text-amber-700 bg-amber-50">
          {{ t('secretariat.home.critical_stock_table_error') }}
        </div>
        <div v-else-if="homeStore.criticalStockItems.length === 0" class="px-6 py-6 text-center text-sm text-gray-400">
          {{ t('secretariat.home.critical_stock_table_empty') }}
        </div>
        <table v-else class="w-full text-sm text-left">
          <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th class="px-6 py-3">{{ t('secretariat.home.critical_stock_table.product') }}</th>
              <th class="px-6 py-3">{{ t('secretariat.home.critical_stock_table.category') }}</th>
              <th class="px-6 py-3 text-right">{{ t('secretariat.home.critical_stock_table.quantity') }}</th>
              <th class="px-6 py-3 text-right">{{ t('secretariat.home.critical_stock_table.threshold') }}</th>
              <th class="px-6 py-3">{{ t('secretariat.home.critical_stock_table.status') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="item in homeStore.criticalStockItems" :key="item.medication_id">
              <td class="px-6 py-3 font-medium text-gray-800">{{ item.drug_name }}</td>
              <td class="px-6 py-3 text-gray-500">{{ item.medication_type }}</td>
              <td class="px-6 py-3 text-right" :class="item.quantity === 0 ? 'text-red-600 font-bold' : 'text-gray-700'">{{ item.quantity }}</td>
              <td class="px-6 py-3 text-right text-gray-400">{{ item.threshold }}</td>
              <td class="px-6 py-3">
                <span class="px-2 py-1 rounded-full text-xs font-bold"
                      :class="item.quantity === 0 ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'">
                  {{ item.quantity === 0 ? t('secretariat.home.critical_stock_table.out_of_stock') : t('secretariat.home.critical_stock_table.low_stock') }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useSecretariatHomeStore } from '@/stores/secretariatHomeStore';
import StatCard from '@/components/dashboard/StatCard.vue';
import {
  BanknotesIcon, ArrowTrendingDownIcon, ArrowTrendingUpIcon,
  ExclamationTriangleIcon, CubeIcon, ClockIcon, SparklesIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const homeStore = useSecretariatHomeStore();

const formatCurrency = (value) => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF', minimumFractionDigits: 0 }).format(value).replace('XOF', 'FCFA');
};

// Meme regle que DashboardOverview.vue::valeurAffichee/soldeAffiche : un bloc
// en echec ne doit jamais s'afficher comme "0 FCFA". Le solde est derive de
// totalPaid ET totalWithdrawn : si l'un des deux est indisponible, le calcul
// a partir d'un 0 par defaut serait un chiffre faux affiche comme reel -
// indisponibilite verifiee AVANT tout formatCurrency, jamais apres.
const valeurAffichee = (nomBloc, valeur) => homeStore.indisponibles.includes(nomBloc) ? 'Indisponible' : valeur;
const soldeAffiche = computed(() =>
    (homeStore.indisponibles.includes('totalPaid') || homeStore.indisponibles.includes('totalWithdrawn'))
        ? 'Indisponible'
        : formatCurrency(homeStore.stats.totalPaid - homeStore.stats.totalWithdrawn)
);

const applyFilters = () => {
  homeStore.setDates(homeStore.filters.startDate, homeStore.filters.endDate);
};

onMounted(() => {
  homeStore.fetchHomeData();
});
</script>
