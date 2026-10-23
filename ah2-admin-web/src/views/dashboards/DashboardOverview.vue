<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="$t('dashboard.title')" :subtitle="`${$t('dashboard.subtitle')} ${currentDate}`" />

    <!-- Periode -->
    <section :aria-label="$t('adminDashboard.filters')" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:flex lg:flex-wrap lg:items-end">
      <div class="lg:w-48">
        <FormField id="dash-start" :label="$t('dashboard.filters.start_date')" v-slot="{ describedBy }">
          <input id="dash-start" type="date" v-model="dashboardStore.filters.startDate" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-48">
        <FormField id="dash-end" :label="$t('dashboard.filters.end_date')" v-slot="{ describedBy }">
          <input id="dash-end" type="date" v-model="dashboardStore.filters.endDate" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="flex flex-col gap-2 md:col-span-2 md:flex-row lg:ml-auto">
        <AppButton variant="brandOutline" :icon="ArrowPathIcon" @click="resetToToday">{{ $t('dashboard.actions.refresh') }}</AppButton>
        <AppButton variant="brand" :icon="MagnifyingGlassIcon" @click="applyFilters">{{ $t('dashboard.filters.apply') }}</AppButton>
      </div>
    </section>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatTile
        :title="$t('dashboard.stats.income')"
        :value="valeurAffichee('income', formatCurrency(dashboardStore.stats.income))"
        :note="$t('adminDashboard.income_note')"
        :icon="BanknotesIcon"
        tone="success"
      />

      <StatTile
        :title="$t('dashboard.stats.withdrawals')"
        :value="valeurAffichee('expense', formatCurrency(dashboardStore.stats.withdrawals))"
        :note="$t('adminDashboard.expense_note')"
        :icon="ArrowTrendingDownIcon"
        tone="danger"
      />

      <StatTile
        :title="$t('finance.balance')"
        :value="soldeAffiche"
        :note="$t('adminDashboard.balance_note')"
        :icon="dashboardStore.stats.income >= dashboardStore.stats.withdrawals ? ArrowTrendingUpIcon : ArrowTrendingDownIcon"
        :tone="dashboardStore.stats.income >= dashboardStore.stats.withdrawals ? 'info' : 'warning'"
      />

      <StatTile
        :title="$t('dashboard.stats.patients')"
        :value="valeurAffichee('toxico', dashboardStore.stats.toxicoAdmissionsThisMonth)"
        :note="$t('adminDashboard.toxico_note')"
        :icon="UserGroupIcon"
      />
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <StatTile
        :title="$t('dashboard.stats.users_online')"
        :value="valeurAffichee('users', `${dashboardStore.stats.onlineUsers} inscrits`)"
        :icon="SignalIcon"
      />

      <button type="button"
              class="flex min-h-11 items-start justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-4 text-left shadow-card transition hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
              @click="$router.push('/dashboard/toxico')">
        <span class="min-w-0">
          <span class="block text-sm font-medium text-ink-muted">{{ $t('dashboard.stats.alerts') }}</span>
          <span class="mt-1 block text-2xl font-bold text-ink">{{ $t('adminDashboard.see_alerts') }}</span>
        </span>
        <span :class="['flex h-11 w-11 shrink-0 items-center justify-center rounded-control border', toneClasses('danger')]">
          <ExclamationTriangleIcon class="h-6 w-6" aria-hidden="true" />
        </span>
      </button>

      <StatTile
        :title="$t('dashboard.stats.bed_occupancy')"
        :value="valeurAffichee('hospitalized', dashboardStore.stats.hospitalizedCount)"
        :icon="HomeModernIcon"
      />
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">

      <AppCard class="lg:col-span-2" :title="$t('dashboard.table_title', 'Dernières Activités Financières')">
        <template #actions>
          <AppButton variant="brandOutline" @click="$router.push('/dashboard/finance')">{{ $t('adminDashboard.see_all') }}</AppButton>
        </template>

        <ResponsiveTable
          :columns="activityColumns"
          :rows="dashboardStore.recentActivities"
          row-key="id"
          :loading="dashboardStore.isLoading"
          :empty-title="dashboardStore.indisponibles.includes('activites') ? 'Activités indisponibles (erreur de chargement).' : 'Aucune activité récente.'"
          :empty-message="' '"
          striped
        >
          <template #cell-label="{ row: item }">
            <span class="font-medium">{{ item.label }}</span>
            <span v-if="item.description && item.description !== item.label" class="block max-w-xs truncate text-sm font-normal text-ink-muted">{{ item.description }}</span>
          </template>
          <template #cell-date="{ row: item }">{{ formatDate(item.date) }}</template>
          <template #cell-amount="{ row: item }"><span class="font-bold">{{ formatCurrency(item.amount) }}</span></template>
          <template #cell-type="{ row: item }">
            <StatusBadge v-if="item.type === 'INCOME'" tone="success" :label="$t('adminDashboard.entry')" />
            <StatusBadge v-else tone="danger" :label="$t('adminDashboard.sortie')" />
          </template>
          <template #cell-status="{ row: item }">
            <StatusBadge :tone="item.status === 'active' || item.status === 'Validé' ? 'success' : 'neutral'" :label="String(item.status ?? '-')" />
          </template>
        </ResponsiveTable>
      </AppCard>

      <AppCard :title="$t('adminDashboard.quick_actions')" :subtitle="$t('adminDashboard.quick_actions_help')">
        <div class="grid gap-3">
          <AppButton variant="brandOutline" :icon="UserGroupIcon" @click="$router.push('/dashboard/users')">{{ $t('dashboard.actions.manage_staff') }}</AppButton>
          <AppButton variant="brandOutline" :icon="PlusCircleIcon" @click="showAdmissionModal = true">{{ $t('dashboard.actions.new_admission') }}</AppButton>
          <AppButton variant="brand" :icon="BanknotesIcon" @click="showFinanceModal = true">{{ $t('dashboard.actions.payment') }}</AppButton>
        </div>
        <p class="mt-5 border-t border-tone-neutral-border pt-4 text-center text-base text-ink-muted">Support technique : 674 69 79 08</p>
      </AppCard>

    </div>

    <ToxicoAdmissionModal
        v-if="showAdmissionModal"
        @close="showAdmissionModal = false"
        @save="handleAdmissionSaved"
    />

    <FinanceModal
        v-if="showFinanceModal"
        @close="showFinanceModal = false"
        @save="handleFinanceSaved"
    />

  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDashboardStore } from '@/stores/dashboardStore'; 
import { AppButton, AppCard, PageHeader, FormField, StatTile, StatusBadge, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';

// 🟢 IMPORTS DES MODALES EXISTANTES
// Assurez-vous que les chemins correspondent exactement à votre arborescence
import ToxicoAdmissionModal from '@/components/toxico/ToxicoAdmissionModal.vue';
import FinanceModal from '@/components/finance/FinanceModal.vue'; 
import { useConfigStore } from '@/stores/configStore';
import { useFinancialStore } from '@/stores/financialStore';

import { 
  BanknotesIcon, UserGroupIcon, HomeModernIcon, 
  ArrowTrendingDownIcon, ArrowTrendingUpIcon, ClockIcon, 
  SignalIcon, PlusCircleIcon, MagnifyingGlassIcon, ExclamationTriangleIcon, ArrowPathIcon
} from '@heroicons/vue/24/outline';

const { t, locale } = useI18n();

// Colonnes du tableau des activites (cartes empilees sous lg) et style commun des champs.
const activityColumns = computed(() => [
  { key: 'label', label: t('adminDashboard.col_description') },
  { key: 'date', label: t('adminDashboard.col_date') },
  { key: 'amount', label: t('adminDashboard.col_amount'), align: 'right' },
  { key: 'type', label: t('adminDashboard.col_type') },
  { key: 'status', label: t('adminDashboard.col_status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const dashboardStore = useDashboardStore();
const financialStore = useFinancialStore();

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

// FinanceModal n'enregistre RIEN par elle-meme : elle emet 'save' avec les
// donnees du formulaire et laisse le parent les persister (c'est ce que fait
// FinancialList.vue::handleSaveTransaction). Ce gestionnaire se contentait
// d'afficher "Transaction enregistree !" puis de rafraichir - la saisie etait
// donc perdue en silence, l'utilisateur croyant l'avoir enregistree.
// On passe par le store (et non par le gateway directement) car c'est lui qui
// aiguille entre recette et depense selon data.type : la modale laisse
// l'utilisateur changer de type, y compris depuis ce raccourci.
const handleFinanceSaved = async (transactionData) => {
    try {
        await financialStore.addTransaction(transactionData);
    } catch (err) {
        alert("Échec de l'enregistrement : la transaction n'a pas été enregistrée.");
        return;
    }
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
// Les dates suivent la langue choisie (FR/EN) ; les montants gardent le format FCFA.
const dateLocale = computed(() => (locale.value === 'en' ? 'en-GB' : 'fr-FR'));
const currentDate = computed(() => {
  return new Date().toLocaleDateString(dateLocale.value, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
});

const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value);
};

// Un bloc en echec doit afficher son indisponibilite, jamais 0 : un zero
// est un chiffre, et un chiffre faux est pire qu'une absence de chiffre.
const valeurAffichee = (nomBloc, valeur) =>
    dashboardStore.indisponibles.includes(nomBloc) ? 'Indisponible' : valeur;

// Le solde derive de income ET withdrawals : si l'un des deux est
// indisponible, le solde calcule a partir d'un 0 par defaut serait un
// chiffre faux affiche comme s'il etait reel. Indisponible si l'un OU
// l'autre a echoue.
const soldeAffiche = computed(() => {
    if (dashboardStore.indisponibles.includes('income') || dashboardStore.indisponibles.includes('expense')) {
        return 'Indisponible';
    }
    return formatCurrency(dashboardStore.stats.income - dashboardStore.stats.withdrawals);
});

const formatDate = (dateStr) => {
    if(!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString(dateLocale.value) + ' ' + date.toLocaleTimeString(dateLocale.value, {hour: '2-digit', minute:'2-digit'});
    } catch (e) { return dateStr; }
};
</script>