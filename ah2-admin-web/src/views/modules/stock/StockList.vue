<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('stock.title')" :subtitle="t('stock.subtitle')">
      <template #actions>
        <AppButton
          v-if="!isSecretary" @click="openModal(null)"
          :icon="PlusIcon"
        >
          {{ t('stock.add_product') }}
        </AppButton>
      </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatTile
            :title="isFiltered ? 'VALEUR (SÉLECTION)' : t('stock.kpi.total_value')"
            :value="formatCurrency(stockStore.currentFilteredValue)"
        />
        <StatTile :title="t('stock.kpi.pharma_items')" :value="stockStore.stats.countPharma" />
        <StatTile :title="t('stock.kpi.natural_items')" :value="stockStore.stats.countNatural" />
        <StatTile :title="t('stock.kpi.low_stock')" :value="stockStore.stats.lowStockAlerts" :tone="stockStore.stats.lowStockAlerts > 0 ? 'danger' : 'neutral'" :icon="ExclamationTriangleIcon" />
        <StatTile title="PÉRIMÉS" :value="stockStore.stats.expiredCount" :tone="stockStore.stats.expiredCount > 0 ? 'danger' : 'neutral'" :icon="ClockIcon" />
    </div>

    <section class="flex flex-col gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:flex-row md:items-end">
        <div class="relative flex-1 md:max-w-sm">
            <label for="stock-search" class="sr-only">{{ t('common.search_placeholder') }}</label>
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
            <input
                id="stock-search"
                v-model="searchInput"
                type="text"
                @input="onSearchInput"
                @keyup.enter="searchNow"
                :placeholder="t('common.search_placeholder')"
                :class="[fieldClass, 'pl-10']"
            />
        </div>

        <div class="md:w-64">
            <label for="stock-category" class="sr-only">{{ t('stock.table.category') }}</label>
            <select id="stock-category" v-model="categoryFilter" :class="fieldClass">
                <option value="ALL">Toutes Catégories</option>
                <option value="PHARMA">{{ t('stock.categories.PHARMA') }}</option>
                <option value="NATUREL">{{ t('stock.categories.NATUREL') }}</option>
                <option value="MATERIEL">{{ t('stock.categories.MATERIEL') }}</option>
                <option value="EXPIRED_ONLY">Afficher seulement les périmés</option>
            </select>
        </div>

        <AppButton v-if="isFiltered" variant="ghost" :icon="XMarkIcon" @click="resetFilters">
            {{ t('stockScreens.filter_reset') }}
        </AppButton>
    </section>

    <section class="grid gap-3">
        <ResponsiveTable
            :columns="columns"
            :rows="stockStore.products"
            row-key="id"
            :loading="stockStore.isLoading"
            empty-title="Aucun produit ne correspond à vos critères."
            :empty-message="' '"
        >
            <template #cell-product="{ row: prod }">
                <div class="font-medium text-ink">{{ prod.name }}</div>
                <div v-if="prod.expiryDate" class="mt-1 text-sm">
                    <StatusBadge
                        v-if="getExpiryStatus(prod.expiryDate) !== 'VALID'"
                        :tone="getExpiryStatus(prod.expiryDate) === 'EXPIRED' ? 'danger' : 'warning'"
                        :label="`${t('stock.table.expiry')}: ${prod.expiryDate}`"
                    />
                    <span v-else class="text-ink-muted">{{ t('stock.table.expiry') }}: {{ prod.expiryDate }}</span>
                </div>
            </template>

            <template #cell-category="{ row: prod }">
                <StatusBadge :tone="categoryTone(prod.category)" :label="t(`stock.categories.${prod.category}`)" />
            </template>

            <template #cell-qty="{ row: prod }">
                <div class="flex flex-wrap items-center gap-2">
                    <span class="font-bold" :class="prod.quantity <= prod.minThreshold ? 'text-tone-danger-text' : 'text-ink'">
                        {{ prod.quantity }}
                    </span>
                    <StatusBadge v-if="prod.quantity <= prod.minThreshold" tone="danger" label="BAS" />
                </div>
            </template>

            <template #cell-price="{ row: prod }">{{ formatCurrency(prod.price) }}</template>

            <template #actions="{ row: prod }">
                <AppButton v-if="isSecretary" @click="openRequest(prod)" variant="secondary">
                    {{ t('stockAdjust.request_button') }}
                </AppButton>
                <AppButton v-if="!isSecretary" @click="openModal(prod)" variant="secondary" :icon="PencilSquareIcon">
                    {{ t('common.edit') }}
                </AppButton>
                <AppButton v-if="isAdmin && getExpiryStatus(prod.expiryDate) === 'EXPIRED' && prod.quantity > 0" @click="handleDispose(prod)" variant="danger" :icon="ArchiveBoxXMarkIcon" :title="t('stock.actions.dispose')">
                    {{ t('stock.actions.dispose') }}
                </AppButton>
                <AppButton v-if="isAdmin" @click="confirmDelete(prod)" variant="ghost" :icon="TrashIcon">
                    {{ t('common.delete') }}
                </AppButton>
            </template>
        </ResponsiveTable>

        <div v-if="stockStore.pagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
            <p class="text-base text-ink">
                Page {{ stockStore.pagination.page }} sur {{ stockStore.pagination.total_pages }}
            </p>
            <div class="flex gap-2">
                <AppButton
                    variant="secondary"
                    :icon="ChevronLeftIcon"
                    :aria-label="t('stockScreens.prev_page')"
                    @click="goToPage(stockStore.pagination.page - 1)"
                    :disabled="stockStore.pagination.page === 1"
                />
                <AppButton
                    variant="secondary"
                    :icon="ChevronRightIcon"
                    :aria-label="t('stockScreens.next_page')"
                    @click="goToPage(stockStore.pagination.page + 1)"
                    :disabled="stockStore.pagination.page === stockStore.pagination.total_pages"
                />
            </div>
        </div>
    </section>

    <AppCard v-if="isSecretary" :title="t('stockAdjust.my_requests')">
        <template #actions>
            <AppButton variant="ghost" @click="loadMyRequests">{{ t('stockAdjust.refresh') }}</AppButton>
        </template>
        <p v-if="requestsError" role="alert" class="mb-3 rounded-card border p-3 text-base font-medium" :class="toneClasses('danger')">{{ requestsError }}</p>
        <p v-if="requestsLoading" class="text-base text-ink-muted" role="status">{{ t('stockOps.loading') }}</p>
        <EmptyState v-else-if="myRequests.length === 0" :title="t('stockAdjust.no_requests')" />
        <ResponsiveTable
            v-else
            :columns="requestColumns"
            :rows="myRequests"
            row-key="id"
        >
            <template #cell-date="{ row: r }">{{ formatDateTime(r.requested_at) }}</template>
            <template #cell-product="{ row: r }">{{ r.product_name }}</template>
            <template #cell-kind="{ row: r }">{{ t(`stockAdjust.kind.${r.kind}`) }}</template>
            <template #cell-quantity="{ row: r }">{{ r.quantity }}</template>
            <template #cell-reason="{ row: r }"><span class="lg:block lg:max-w-xs">{{ r.reason }}</span></template>
            <template #cell-status="{ row: r }">
                <StatusBadge :tone="requestTone(r.status)" :label="t(`stockAdjust.status.${r.status}`)" />
                <div v-if="r.decision_note" class="mt-1 text-sm text-ink-muted">{{ t('stockAdjust.decision_note') }} : {{ r.decision_note }}</div>
            </template>
            <template #cell-stock_change="{ row: r }">
                <span v-if="r.stock_before !== null && r.stock_before !== undefined">{{ t('stockScreens.stock_change', { before: r.stock_before, after: r.stock_after }) }}</span>
            </template>
            <template #actions="{ row: r }">
                <AppButton v-if="r.status === 'en_attente'" variant="secondary" @click="cancelRequest(r)" :disabled="cancellingId === r.id">
                    {{ t('stockOps.cancel') }}
                </AppButton>
            </template>
        </ResponsiveTable>
    </AppCard>

    <AdjustmentRequestModal
        v-if="requestProduct"
        :product="requestProduct"
        @close="requestProduct = null"
        @created="onRequestCreated"
    />

    <ProductModal :can-edit-quantity="isAdmin"
        v-if="showModal"
        :product="selectedProduct"
        @close="showModal = false"
        @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useStockStore } from '@/stores/stockStore';
import { useI18n } from 'vue-i18n';
import ProductModal from '@/components/stock/ProductModal.vue';
import AdjustmentRequestModal from '@/components/stock/AdjustmentRequestModal.vue';
import { useAuthStore } from '@/stores/auth';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { AppButton, AppCard, PageHeader, StatTile, StatusBadge, EmptyState, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { 
    PlusIcon, MagnifyingGlassIcon, PencilSquareIcon, TrashIcon, XMarkIcon, ExclamationTriangleIcon,
    ClockIcon, ArchiveBoxXMarkIcon, ChevronLeftIcon, ChevronRightIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const stockStore = useStockStore();
const authStore = useAuthStore();

// Colonnes des tableaux (cartes sous lg) et style commun des champs.
const columns = computed(() => [
    { key: 'product', label: t('stock.table.product') },
    { key: 'category', label: t('stock.table.category') },
    { key: 'qty', label: t('stock.table.qty') },
    { key: 'price', label: t('stock.table.price') },
]);
const requestColumns = computed(() => [
    { key: 'date', label: t('stockOps.col_date') },
    { key: 'product', label: t('stockOps.col_product') },
    { key: 'kind', label: t('stockAdjust.col_kind') },
    { key: 'quantity', label: t('stockOps.col_quantity') },
    { key: 'reason', label: t('stockOps.col_reason') },
    { key: 'status', label: t('stockOps.col_status') },
    { key: 'stock_change', label: t('stockAdjust.col_stock_change') },
]);
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Droits par role (Task 6 cote serveur) : seul l'admin fixe une quantite,
// supprime ou sort un perime ; la secretaire est en lecture seule et passe
// par une demande d'ajustement.
const isAdmin = computed(() => authStore.hasRole(['admin']));
const isSecretary = computed(() => authStore.hasRole(['secretaire']));

const requestProduct = ref(null);
const myRequests = ref([]);
const requestsLoading = ref(false);
const requestsError = ref('');
const cancellingId = ref(null);

const loadMyRequests = async () => {
    requestsLoading.value = true;
    requestsError.value = '';
    try {
        myRequests.value = (await StockOpsGateway.listAdjustmentRequests({ mineOnly: true })) || [];
    } catch (err) {
        requestsError.value = describeStockError(err, t('stockOps.error_load'));
        console.error('Chargement des demandes echoue :', err);
    } finally {
        requestsLoading.value = false;
    }
};

const openRequest = (prod) => { requestProduct.value = { id: prod.id, name: prod.name, quantity: prod.quantity }; };
const onRequestCreated = async () => {
    requestProduct.value = null;
    await loadMyRequests();
};

const cancelRequest = async (r) => {
    if (!window.confirm(t('stockOps.confirm_cancel'))) return;
    cancellingId.value = r.id;
    requestsError.value = '';
    try {
        await StockOpsGateway.cancelAdjustmentRequest(r.id);
        await loadMyRequests();
    } catch (err) {
        requestsError.value = describeStockError(err, t('stockOps.error_save'));
        console.error('Annulation de la demande echouee :', err);
    } finally {
        cancellingId.value = null;
    }
};

// Orange = en attente, vert = approuve, rouge = refuse, neutre = annule (toujours avec le texte du statut).
const requestTone = (s) => ({
    en_attente: 'warning',
    approuve: 'success',
    refuse: 'danger',
    annule: 'neutral',
}[s] || 'neutral');

const formatDateTime = (v) => (v ? new Date(v).toLocaleString() : '');

const showModal = ref(false);
const selectedProduct = ref(null);

onMounted(() => {
    // 🟢 CHARGEMENT DES DONNÉES RÉELLES
    stockStore.fetchStock();
    stockStore.fetchStats();
    if (isSecretary.value) loadMyRequests();
});

// Liaison Store - recherche en direct (debounce 300ms), meme motif que
// CaisseInvoiceModal.vue::onLineSearchInput (deja en place et fonctionnel
// ailleurs dans le projet). Auparavant v-model.lazy : la recherche ne se
// declenchait qu'au blur/Entree, ce qui se voyait comme un champ casse.
const searchInput = ref(stockStore.filters.searchQuery);
let searchDebounceTimeout = null;

const onSearchInput = () => {
    clearTimeout(searchDebounceTimeout);
    searchDebounceTimeout = setTimeout(() => {
        stockStore.setFilters({ searchQuery: searchInput.value });
    }, 300);
};

const searchNow = () => {
    clearTimeout(searchDebounceTimeout);
    stockStore.setFilters({ searchQuery: searchInput.value });
};

// resetFilters() (ci-dessous) ecrit directement dans le store sans passer
// par searchInput - sans ce watch, le champ garderait visuellement l'ancien
// texte apres un "Reinitialiser".
watch(() => stockStore.filters.searchQuery, (val) => {
    if (val !== searchInput.value) searchInput.value = val;
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

const categoryTone = (cat) => {
    switch(cat) {
        case 'PHARMA': return 'info';
        case 'NATUREL': return 'success';
        default: return 'neutral';
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

// Actions
const handleDispose = async (product) => {
    if (!isAdmin.value) return;
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
    if (isSecretary.value) return;
    await stockStore.saveProduct(product, { canSetQuantity: isAdmin.value });
    showModal.value = false;
};

const confirmDelete = async (product) => {
    if (!isAdmin.value) return;
    if(confirm("Supprimer ce produit ?")) {
        await stockStore.deleteProduct(product.id);
    }
};
</script>