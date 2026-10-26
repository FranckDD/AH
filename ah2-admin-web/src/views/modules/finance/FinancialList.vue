<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('finance.title')" :subtitle="t('financeScreens.subtitle')">
      <template #actions>
        <AppButton :icon="PlusCircleIcon" @click="showModal = true">{{ t('finance.new_transaction') }}</AppButton>
      </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <StatTile :title="t('finance.income')" :value="kpiAffiche(formatCurrency(financialStore.totalIncome))" :icon="ArrowTrendingUpIcon" tone="success" />
      <StatTile :title="t('finance.expense')" :value="kpiAffiche(formatCurrency(financialStore.totalExpenses))" :icon="ArrowTrendingDownIcon" tone="danger" />
      <StatTile :title="t('finance.balance')" :value="kpiAffiche(formatCurrency(financialStore.currentBalance))" :icon="BanknotesIcon" tone="info" />
    </div>

    <section :aria-label="t('financeScreens.search_label')" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:flex lg:flex-wrap lg:items-end">
      <div class="md:col-span-2 lg:min-w-64 lg:flex-1">
        <FormField id="fin-search" :label="t('financeScreens.search_label')" v-slot="{ describedBy }">
          <input id="fin-search" v-model="searchQuery" type="search" :placeholder="t('finance.search_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-56">
        <FormField id="fin-category" :label="t('finance.modal.category')" v-slot="{ describedBy }">
          <select id="fin-category" v-model="categoryFilter" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ t('financeScreens.all_categories') }}</option>
            <option v-for="cat in availableCategories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </FormField>
      </div>
      <div class="lg:w-44">
        <FormField id="fin-from" :label="t('financeScreens.from')" v-slot="{ describedBy }">
          <input id="fin-from" v-model="startDate" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-44">
        <FormField id="fin-to" :label="t('financeScreens.to')" v-slot="{ describedBy }">
          <input id="fin-to" v-model="endDate" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="md:col-span-2 lg:col-span-1">
        <AppButton variant="secondary" @click="resetFilters">{{ t('financeScreens.reset') }}</AppButton>
      </div>
    </section>

    <section class="grid gap-3">
      <div class="flex flex-col gap-3 rounded-card border border-tone-neutral-border bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="grid grid-cols-3 gap-2 sm:flex" role="group" :aria-label="t('financeScreens.type_group')">
          <AppButton :variant="typeFilter === 'ALL' ? 'primary' : 'secondary'" :aria-pressed="typeFilter === 'ALL'" @click="typeFilter = 'ALL'">{{ t('financeScreens.all_types') }}</AppButton>
          <AppButton :variant="typeFilter === 'INCOME' ? 'success' : 'secondary'" :aria-pressed="typeFilter === 'INCOME'" @click="typeFilter = 'INCOME'">{{ t('financeScreens.entries') }}</AppButton>
          <AppButton :variant="typeFilter === 'EXPENSE' ? 'danger' : 'secondary'" :aria-pressed="typeFilter === 'EXPENSE'" @click="typeFilter = 'EXPENSE'">{{ t('financeScreens.exits') }}</AppButton>
        </div>
        <p class="text-base text-ink-muted">
          <span v-if="financialStore.loadError" class="font-medium text-tone-danger-text">{{ t('financeScreens.load_error') }}</span>
          <span v-else>{{ t('financeScreens.results', { n: financialStore.pagination.total }) }}</span>
        </p>
      </div>

      <ResponsiveTable
        :columns="columns"
        :rows="financialStore.transactions"
        row-key="id"
        :loading="financialStore.isLoading"
        :empty-title="t('financeScreens.empty')"
        :empty-message="' '"
        striped
      >
        <template #cell-date="{ row: tx }"><span class="font-mono">{{ tx.date }}</span></template>
        <template #cell-desc="{ row: tx }">
          <span class="font-medium">{{ tx.description }}</span>
          <span class="block text-sm text-ink-muted">{{ modeLabel(tx.paymentMethod) }}</span>
        </template>
        <template #cell-category="{ row: tx }">{{ tx.category }}</template>
        <template #cell-amount="{ row: tx }">
          <span class="font-bold" :class="tx.type === 'INCOME' ? 'text-tone-success-text' : 'text-tone-danger-text'">
            {{ tx.type === 'INCOME' ? '+' : '-' }} {{ formatCurrency(tx.amount) }}
          </span>
        </template>
        <template #cell-status="{ row: tx }">
          <StatusBadge v-if="tx.status === 'Validé'" tone="success" :label="$t('screens.misc.validated')" />
          <StatusBadge v-else tone="warning" :label="String(tx.status ?? '-')" />
        </template>
      </ResponsiveTable>

      <div v-if="financialStore.pagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">{{ t('financeScreens.page_label', { n: financialStore.pagination.page, total: financialStore.pagination.total_pages }) }}</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="t('financeScreens.prev_page')" @click="goToPage(financialStore.pagination.page - 1)" :disabled="financialStore.pagination.page === 1" />
          <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="t('financeScreens.next_page')" @click="goToPage(financialStore.pagination.page + 1)" :disabled="financialStore.pagination.page === financialStore.pagination.total_pages" />
        </div>
      </div>
    </section>

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
import { FinanceGateway } from '@/services/FinanceGateway';
import { useI18n } from 'vue-i18n';
import FinanceModal from '@/components/finance/FinanceModal.vue';
import { AppButton, PageHeader, FormField, StatTile, StatusBadge, ResponsiveTable } from '@/components/ui';
import { modeLabel } from '@/utils/paymentModes';
import { 
    PlusCircleIcon, 
    ArrowTrendingUpIcon, 
    ArrowTrendingDownIcon, 
    BanknotesIcon,
    MagnifyingGlassIcon,
    ChevronLeftIcon,  // 🟢 Ajout icône
    ChevronRightIcon  // 🟢 Ajout icône
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const financialStore = useFinancialStore();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
    { key: 'date', label: t('finance.table.date') },
    { key: 'desc', label: t('finance.table.desc') },
    { key: 'category', label: t('finance.table.category') },
    { key: 'amount', label: t('finance.table.amount'), align: 'right' },
    { key: 'status', label: t('finance.table.status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// --- ETATS ---
const showModal = ref(false);

// Alimentee par les valeurs reellement presentes en base : la saisie
// enregistre des codes anglais ('CONSULTATION') tandis que cette liste
// contenait des libelles francais ('Consultation'), donc le filtre ne
// pouvait jamais correspondre.
const availableCategories = ref([]);

onMounted(async () => {
    financialStore.fetchTransactions();
    try {
        const reponse = await FinanceGateway.fetchCategories();
        availableCategories.value = reponse.data || [];
    } catch (err) {
        console.error('Categories financieres indisponibles:', err);
        availableCategories.value = [];
    }
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

// Meme regle que le tableau de bord (DashboardOverview.vue::valeurAffichee) :
// un KPI en echec ne doit jamais s'afficher comme "0 FCFA", indistinguable
// d'un vrai zero.
const kpiAffiche = (valeurFormatee) => financialStore.kpiError ? 'Indisponible' : valeurFormatee;

const handleSaveTransaction = async (transactionData) => {
    await financialStore.addTransaction(transactionData);
    showModal.value = false;
};
</script>