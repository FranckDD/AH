<template>
  <div class="space-y-6 w-full">
    
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('stock.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('stock.subtitle') }}</p>
      </div>
      <button 
        @click="openModal(null)"
        class="flex items-center px-6 py-2.5 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 shadow-md shadow-emerald-200 transition font-semibold"
      >
        <PlusIcon class="h-5 w-5 mr-2" />
        {{ t('stock.add_product') }}
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-5 gap-6">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <p class="text-xs font-bold text-gray-500 uppercase">
                {{ isFiltered ? 'VALEUR (SÉLECTION)' : t('stock.kpi.total_value') }}
            </p>
            <p class="text-2xl font-bold text-gray-900 mt-2">
                {{ formatCurrency(stockStore.currentFilteredValue) }}
            </p>
        </div>

        <div class="bg-blue-50 p-6 rounded-2xl shadow-sm border border-blue-100">
            <p class="text-xs font-bold text-blue-600 uppercase">{{ t('stock.kpi.pharma_items') }}</p>
            <p class="text-3xl font-bold text-blue-900 mt-2">{{ stockStore.stats.countPharma }}</p>
        </div>

        <div class="bg-green-50 p-6 rounded-2xl shadow-sm border border-green-100">
            <p class="text-xs font-bold text-green-600 uppercase">{{ t('stock.kpi.natural_items') }}</p>
            <p class="text-3xl font-bold text-green-900 mt-2">{{ stockStore.stats.countNatural }}</p>
        </div>

        <div class="bg-red-50 p-6 rounded-2xl shadow-sm border border-red-100">
            <p class="text-xs font-bold text-red-600 uppercase">{{ t('stock.kpi.low_stock') }}</p>
            <p class="text-3xl font-bold text-red-900 mt-2">{{ stockStore.stats.lowStockAlerts }}</p>
        </div>

        <div class="bg-purple-50 p-6 rounded-2xl shadow-sm border border-purple-100">
            <p class="text-xs font-bold text-purple-600 uppercase">PÉRIMÉS</p>
            <p class="text-3xl font-bold text-purple-900 mt-2">{{ stockStore.stats.expiredCount }}</p>
        </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="p-4 border-b border-gray-100 flex flex-wrap gap-4 items-center justify-between">
            <div class="relative w-full md:w-64">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
                </div>
                <input 
                    v-model.lazy="searchQuery" 
                    type="text" 
                    @keyup.enter="stockStore.fetchStock()"
                    :placeholder="t('common.search_placeholder')" 
                    class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm" 
                />
            </div>
            
            <div class="flex items-center gap-2">
                <select v-model="categoryFilter" class="block w-full md:w-48 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm rounded-lg">
                    <option value="ALL">Toutes Catégories</option>
                    <option value="PHARMA">{{ t('stock.categories.PHARMA') }}</option>
                    <option value="NATUREL">{{ t('stock.categories.NATUREL') }}</option>
                    <option value="MATERIEL">{{ t('stock.categories.MATERIEL') }}</option>
                    <option value="EXPIRED_ONLY">Afficher seulement les périmés</option>
                </select>
                
                <button v-if="isFiltered" @click="resetFilters" class="p-2 text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition" title="Réinitialiser">
                    <span class="text-xs font-bold">✕</span>
                </button>
            </div>
        </div>

        <div v-if="stockStore.isLoading" class="p-10 text-center">
            <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></span>
            <p class="mt-2 text-gray-500">Chargement du stock...</p>
        </div>

        <div v-else class="overflow-x-auto">
            <table class="min-w-full text-left border-collapse">
                <thead>
                    <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                        <th class="px-6 py-3 font-semibold">{{ t('stock.table.product') }}</th>
                        <th class="px-6 py-3 font-semibold">{{ t('stock.table.category') }}</th>
                        <th class="px-6 py-3 font-semibold">{{ t('stock.table.qty') }}</th>
                        <th class="px-6 py-3 font-semibold">{{ t('stock.table.price') }}</th>
                        <th class="px-6 py-3 font-semibold text-right">{{ t('users.table.actions') }}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="prod in stockStore.products" :key="prod.id" class="hover:bg-gray-50 transition" :class="{'bg-red-50/50': getExpiryStatus(prod.expiryDate) === 'EXPIRED' && prod.quantity > 0}">
                        <td class="px-6 py-4">
                            <div class="font-medium text-gray-900">{{ prod.name }}</div>
                            <div v-if="prod.expiryDate" class="text-xs mt-1 flex items-center">
                                <ClockIcon class="h-3 w-3 mr-1" :class="getExpiryStatus(prod.expiryDate) === 'VALID' ? 'text-gray-400' : ''" /> 
                                <span :class="getExpiryColor(prod.expiryDate)">
                                    {{ t('stock.table.expiry') }}: {{ prod.expiryDate }}
                                </span>
                            </div>
                        </td>
                        <td class="px-6 py-4">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border" :class="getCategoryBadge(prod.category)">
                                {{ t(`stock.categories.${prod.category}`) }}
                            </span>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex items-center">
                                <span class="font-bold mr-2" :class="prod.quantity <= prod.minThreshold ? 'text-red-600' : 'text-gray-900'">
                                    {{ prod.quantity }}
                                </span>
                                <span v-if="prod.quantity <= prod.minThreshold" class="bg-red-100 text-red-700 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wide animate-pulse">
                                    BAS
                                </span>
                            </div>
                        </td>
                        <td class="px-6 py-4 text-sm text-gray-600">
                            {{ formatCurrency(prod.price) }}
                        </td>
                        <td class="px-6 py-4 text-right space-x-2">
                            <button @click="openModal(prod)" class="text-indigo-600 hover:text-indigo-900 bg-indigo-50 p-1.5 rounded-lg transition">
                                <PencilSquareIcon class="h-4 w-4" />
                            </button>
                            <button v-if="getExpiryStatus(prod.expiryDate) === 'EXPIRED' && prod.quantity > 0" @click="handleDispose(prod)" class="text-white bg-red-600 hover:bg-red-700 p-1.5 rounded-lg transition shadow-sm" :title="t('stock.actions.dispose')">
                                <ArchiveBoxXMarkIcon class="h-4 w-4" /> 
                            </button>
                            <button @click="confirmDelete(prod)" class="text-red-400 hover:text-red-600 p-1.5 rounded-lg transition">
                                <TrashIcon class="h-4 w-4" />
                            </button>
                        </td>
                    </tr>
                    <tr v-if="stockStore.products.length === 0">
                        <td colspan="5" class="px-6 py-8 text-center text-gray-500 italic">
                            Aucun produit ne correspond à vos critères.
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div v-if="stockStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
            <p class="text-sm text-gray-700">
                Page {{ stockStore.pagination.page }} sur {{ stockStore.pagination.total_pages }}
            </p>
            <div class="flex space-x-2">
                <button @click="goToPage(stockStore.pagination.page - 1)" :disabled="stockStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
                    <ChevronLeftIcon class="h-5 w-5" />
                </button>
                <button @click="goToPage(stockStore.pagination.page + 1)" :disabled="stockStore.pagination.page === stockStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
                    <ChevronRightIcon class="h-5 w-5" />
                </button>
            </div>
        </div>

    </div>

    <ProductModal 
        v-if="showModal" 
        :product="selectedProduct" 
        @close="showModal = false" 
        @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useStockStore } from '@/stores/stockStore';
import { useI18n } from 'vue-i18n';
import ProductModal from '@/components/stock/ProductModal.vue';
import { 
    PlusIcon, MagnifyingGlassIcon, PencilSquareIcon, TrashIcon, 
    ClockIcon, ArchiveBoxXMarkIcon, ChevronLeftIcon, ChevronRightIcon 
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const stockStore = useStockStore();

const showModal = ref(false);
const selectedProduct = ref(null);

onMounted(() => {
    // 🟢 CHARGEMENT DES DONNÉES RÉELLES
    stockStore.fetchStock();
    stockStore.fetchStats();
});

// Liaison Store
const searchQuery = computed({
    get: () => stockStore.filters.searchQuery,
    set: (val) => stockStore.setFilters({ searchQuery: val })
});

const categoryFilter = computed({
    get: () => stockStore.filters.categoryFilter,
    set: (val) => stockStore.setFilters({ categoryFilter: val })
});

const isFiltered = computed(() => {
    return stockStore.filters.categoryFilter !== 'ALL' || stockStore.filters.searchQuery !== '';
});

const resetFilters = () => {
    stockStore.setFilters({ categoryFilter: 'ALL', searchQuery: '' });
};

const goToPage = (page) => {
    stockStore.setPage(page);
};

// Formateurs
const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF', minimumFractionDigits: 0 }).format(value).replace('XOF', 'FCFA');
};

const getCategoryBadge = (cat) => {
    switch(cat) {
        case 'PHARMA': return 'bg-blue-50 text-blue-700 border-blue-200';
        case 'NATUREL': return 'bg-green-50 text-green-700 border-green-200';
        case 'MATERIEL': return 'bg-gray-50 text-gray-700 border-gray-200';
        default: return 'bg-gray-50 text-gray-600 border-gray-200';
    }
};

const getExpiryStatus = (dateString) => {
    if (!dateString) return 'VALID';
    const today = new Date();
    const expiry = new Date(dateString);
    const threeMonthsFromNow = new Date();
    threeMonthsFromNow.setMonth(today.getMonth() + 3);
    if (expiry < today) return 'EXPIRED';
    if (expiry < threeMonthsFromNow) return 'SOON';
    return 'VALID';
};

const getExpiryColor = (dateString) => {
    const status = getExpiryStatus(dateString);
    switch (status) {
        case 'EXPIRED': return 'text-red-600 font-bold bg-red-100 px-2 py-1 rounded';
        case 'SOON': return 'text-orange-600 font-bold bg-orange-100 px-2 py-1 rounded';
        default: return 'text-gray-600';
    }
};

// Actions
const handleDispose = async (product) => {
    if (confirm(`Sortir ${product.name} du stock (PÉRIMÉ) ?`)) {
        const updatedProduct = { ...product, quantity: 0 };
        await stockStore.saveProduct(updatedProduct);
    }
};

const openModal = (product) => {
    selectedProduct.value = product ? { ...product } : null;
    showModal.value = true;
};

const handleSave = async (product) => {
    await stockStore.saveProduct(product);
    showModal.value = false;
};

const confirmDelete = async (product) => {
    if(confirm("Supprimer ce produit ?")) {
        await stockStore.deleteProduct(product.id);
    }
};
</script>