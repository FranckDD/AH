<template>
  <div class="space-y-6 w-full">
    
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('finance.title') }}
        </h1>
        <p class="text-sm text-gray-500">Suivi de la trésorerie en temps réel</p>
      </div>
      
      <button 
        @click="showModal = true"
        class="flex items-center px-6 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 shadow-md shadow-green-200 transition font-semibold"
      >
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('finance.new_transaction') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">
        
        <div class="flex-1 min-w-[200px]">
            <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Recherche</label>
            <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
                </div>
                <input 
                    v-model="searchQuery"
                    type="text" 
                    :placeholder="t('finance.search_placeholder')"
                    class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-green-500 focus:border-green-500 sm:text-sm"
                >
            </div>
        </div>

        <div class="w-full md:w-48">
            <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('finance.modal.category') }}</label>
            <select v-model="categoryFilter" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm rounded-lg">
                <option value="">Toutes les catégories</option>
                <option v-for="cat in availableCategories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
        </div>

        <div class="w-full md:w-40">
            <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Du</label>
            <input v-model="startDate" type="date" class="block w-full pl-3 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
        </div>

        <div class="w-full md:w-40">
            <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Au</label>
            <input v-model="endDate" type="date" class="block w-full pl-3 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
        </div>

        <div>
            <button @click="resetFilters" class="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition h-[38px]">
                Réinitialiser
            </button>
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center">
            <div class="p-3 bg-green-50 rounded-full mr-4">
                <ArrowTrendingUpIcon class="h-8 w-8 text-green-600" />
            </div>
            <div>
                <p class="text-sm text-gray-500 font-medium uppercase">{{ t('finance.income') }}</p>
                <p class="text-2xl font-bold text-gray-900">{{ formatCurrency(financialStore.totalIncome) }}</p>
            </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center">
            <div class="p-3 bg-red-50 rounded-full mr-4">
                <ArrowTrendingDownIcon class="h-8 w-8 text-red-600" />
            </div>
            <div>
                <p class="text-sm text-gray-500 font-medium uppercase">{{ t('finance.expense') }}</p>
                <p class="text-2xl font-bold text-gray-900">{{ formatCurrency(financialStore.totalExpenses) }}</p>
            </div>
        </div>

        <div class="bg-gradient-to-r from-gray-800 to-gray-900 p-6 rounded-2xl shadow-lg text-white flex items-center justify-between">
            <div>
                <p class="text-sm text-gray-400 font-medium uppercase">{{ t('finance.balance') }}</p>
                <p class="text-3xl font-bold text-white">{{ formatCurrency(financialStore.currentBalance) }}</p>
            </div>
            <BanknotesIcon class="h-10 w-10 text-gray-500 opacity-50" />
        </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        
        <div class="p-4 border-b border-gray-100 flex items-center justify-between">
            <div class="flex space-x-2">
                <button @click="typeFilter = 'ALL'" :class="typeFilter === 'ALL' ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600'" class="px-3 py-1 text-sm rounded-lg font-medium transition">Tout</button>
                <button @click="typeFilter = 'INCOME'" :class="typeFilter === 'INCOME' ? 'bg-green-600 text-white' : 'bg-green-50 text-green-700'" class="px-3 py-1 text-sm rounded-lg font-medium transition">Entrées</button>
                <button @click="typeFilter = 'EXPENSE'" :class="typeFilter === 'EXPENSE' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-700'" class="px-3 py-1 text-sm rounded-lg font-medium transition">Sorties</button>
            </div>
            <div class="text-sm text-gray-500">
                {{ financialStore.pagination.total }} transactions trouvées
            </div>
        </div>

        <div v-if="financialStore.isLoading" class="p-10 text-center">
            <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></span>
            <p class="mt-2 text-gray-500">{{ t('common.loading') }}</p>
        </div>

        <div v-else class="overflow-x-auto">
            <table class="min-w-full text-left border-collapse">
                <thead>
                    <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                        <th class="px-6 py-4 font-semibold">{{ t('finance.table.date') }}</th>
                        <th class="px-6 py-4 font-semibold">{{ t('finance.table.desc') }}</th>
                        <th class="px-6 py-4 font-semibold">{{ t('finance.table.category') }}</th>
                        <th class="px-6 py-4 font-semibold text-right">{{ t('finance.table.amount') }}</th>
                        <th class="px-6 py-4 font-semibold">{{ t('finance.table.status') }}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="tx in financialStore.transactions" :key="tx.id" class="hover:bg-gray-50 transition">
                        <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ tx.date }}</td>
                        <td class="px-6 py-4">
                            <div class="text-sm font-medium text-gray-900">{{ tx.description }}</div>
                            <div class="text-xs text-gray-500">{{ tx.paymentMethod }}</div>
                        </td>
                        <td class="px-6 py-4">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                                {{ tx.category }}
                            </span>
                        </td>
                        <td class="px-6 py-4 text-right font-bold text-sm">
                            <span :class="tx.type === 'INCOME' ? 'text-green-600' : 'text-red-600'">
                                {{ tx.type === 'INCOME' ? '+' : '-' }} {{ formatCurrency(tx.amount) }}
                            </span>
                        </td>
                        <td class="px-6 py-4">
                            <span v-if="tx.status === 'Validé'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                <CheckCircleIcon class="h-3 w-3 mr-1" /> Validé
                            </span>
                            <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                <ClockIcon class="h-3 w-3 mr-1" /> {{ tx.status }}
                            </span>
                        </td>
                    </tr>
                    <tr v-if="financialStore.transactions.length === 0">
                        <td colspan="5" class="px-6 py-8 text-center text-gray-500 italic">
                            Aucune transaction trouvée pour ces critères.
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div v-if="financialStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
            <p class="text-sm text-gray-700">
                Page {{ financialStore.pagination.page }} sur {{ financialStore.pagination.total_pages }}
            </p>
            <div class="flex space-x-2">
                <button @click="goToPage(financialStore.pagination.page - 1)" :disabled="financialStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
                    <ChevronLeftIcon class="h-5 w-5" />
                </button>
                <button @click="goToPage(financialStore.pagination.page + 1)" :disabled="financialStore.pagination.page === financialStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
                    <ChevronRightIcon class="h-5 w-5" />
                </button>
            </div>
        </div>

    </div>

    <FinanceModal 
        v-if="showModal" 
        @close="showModal = false" 
        @save="handleSaveTransaction"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useFinancialStore } from '@/stores/financialStore';
import { useI18n } from 'vue-i18n';
import FinanceModal from '@/components/finance/FinanceModal.vue';
import { 
    PlusCircleIcon, 
    ArrowTrendingUpIcon, 
    ArrowTrendingDownIcon, 
    BanknotesIcon,
    MagnifyingGlassIcon,
    CheckCircleIcon,
    ClockIcon,
    ChevronLeftIcon,  // 🟢 Ajout icône
    ChevronRightIcon  // 🟢 Ajout icône
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const financialStore = useFinancialStore();

// --- ETATS ---
const showModal = ref(false);

const availableCategories = [
    'Consultation', 'Pharmacie', 'Hospitalisation','Examens' ,'Laboratoire', 
    'Salaires', 'Matériel', 'Factures','Detox', 'Autre'
];

onMounted(() => {
    financialStore.fetchTransactions();
});

// 🟢 COMPUTED PROPERTIES POUR LES FILTRES (GET/SET vers le Store)
// Ces computed permettent d'utiliser v-model tout en déclenchant l'action du store
const searchQuery = computed({
    get: () => financialStore.filters.searchQuery,
    set: (val) => financialStore.setFilters({ searchQuery: val })
});

const categoryFilter = computed({
    get: () => financialStore.filters.category,
    set: (val) => financialStore.setFilters({ category: val })
});

const typeFilter = computed({
    get: () => financialStore.filters.type,
    set: (val) => financialStore.setFilters({ type: val })
});

const startDate = computed({
    get: () => financialStore.filters.startDate,
    set: (val) => financialStore.setFilters({ startDate: val })
});

const endDate = computed({
    get: () => financialStore.filters.endDate,
    set: (val) => financialStore.setFilters({ endDate: val })
});

// 🟢 ACTIONS PAGINATION
const goToPage = (page) => {
    financialStore.setPage(page);
};

const resetFilters = () => {
    financialStore.setFilters({ searchQuery: '', category: '', type: 'ALL', startDate: '', endDate: '' });
};

const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value).replace('XOF', 'FCFA');
};

const handleSaveTransaction = async (transactionData) => {
    await financialStore.addTransaction(transactionData);
    showModal.value = false;
};
</script>