<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('secretariat.home.title')" />

    <!-- 1. Actions rapides : le geste le plus frequent en un clic -->
    <section :aria-label="t('secretariatHome.quick_title')">
      <h2 class="mb-3 text-lg font-semibold text-ink">{{ t('secretariatHome.quick_title') }}</h2>
      <div class="grid gap-3 sm:grid-cols-3">
        <router-link to="/secretariat/caisse?nouveau=1" :class="buttonClasses('primary', 'lg')">
          <BanknotesIcon class="h-6 w-6" aria-hidden="true" />
          {{ t('secretariatHome.quick_invoice') }}
        </router-link>
        <router-link to="/secretariat/retrait?nouveau=1" :class="buttonClasses('secondary', 'lg')">
          <ArrowUpTrayIcon class="h-6 w-6" aria-hidden="true" />
          {{ t('secretariatHome.quick_withdrawal') }}
        </router-link>
        <router-link to="/secretariat/patients?nouveau=1" :class="buttonClasses('secondary', 'lg')">
          <UserPlusIcon class="h-6 w-6" aria-hidden="true" />
          {{ t('secretariatHome.quick_patient') }}
        </router-link>
      </div>
    </section>

    <p v-if="homeStore.isLoading" class="p-10 text-center text-base text-ink-muted" role="status">{{ t('common.loading') }}</p>

    <template v-else>

      <!-- 2. Argent de la periode, avec le choix de la periode -->
      <AppCard :title="t('secretariatHome.money_title')">
        <template #actions>
          <FormField id="home-start" :label="t('secretariat.home.period_from')" v-slot="{ describedBy }">
            <input id="home-start" type="date" v-model="homeStore.filters.startDate" @change="applyFilters" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="home-end" :label="t('secretariat.home.period_to')" v-slot="{ describedBy }">
            <input id="home-end" type="date" v-model="homeStore.filters.endDate" @change="applyFilters" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </template>

        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile :title="t('secretariat.home.total_paid')" :value="valeurAffichee('totalPaid', formatCurrency(homeStore.stats.totalPaid))" :icon="BanknotesIcon" tone="success" />
          <StatTile :title="t('secretariat.home.total_withdrawn')" :value="valeurAffichee('totalWithdrawn', formatCurrency(homeStore.stats.totalWithdrawn))" :icon="ArrowTrendingDownIcon" />
          <StatTile :title="t('secretariat.home.balance')" :value="soldeAffiche" :icon="ArrowTrendingUpIcon" tone="info" />
          <StatTile :title="t('secretariat.home.remaining_due')" :value="valeurAffichee('remainingDue', formatCurrency(homeStore.stats.remainingDue))" :icon="ExclamationTriangleIcon" tone="warning" />
        </div>
      </AppCard>

      <!-- 3. Stock et activite -->
      <AppCard :title="t('secretariatHome.stock_title')">
        <div class="grid gap-4 sm:grid-cols-3">
          <StatTile :title="t('secretariat.home.critical_stock')" :value="homeStore.stats.criticalStockCount" :icon="CubeIcon" :tone="homeStore.stats.criticalStockCount > 0 ? 'danger' : 'neutral'" />
          <StatTile :title="t('secretariat.home.expiring_stock')" :value="homeStore.stats.expiringStockCount" :icon="ClockIcon" :tone="homeStore.stats.expiringStockCount > 0 ? 'warning' : 'neutral'" />
          <StatTile :title="t('secretariat.home.consultations_period')" :value="homeStore.stats.consultationsCount" :icon="SparklesIcon" />
        </div>

        <h3 class="mb-3 mt-6 text-base font-semibold text-ink">{{ t('secretariat.home.critical_stock_table_title') }}</h3>
        <p
          v-if="homeStore.indisponibles.includes('criticalStockItems')"
          role="alert"
          class="rounded-card border px-4 py-3 text-base font-medium"
          :class="toneClasses('warning')"
        >
          {{ t('secretariat.home.critical_stock_table_error') }}
        </p>
        <ResponsiveTable
          v-else
          :columns="stockColumns"
          :rows="homeStore.criticalStockItems"
          row-key="medication_id"
          :empty-title="t('secretariat.home.critical_stock_table_empty')"
          :empty-message="' '"
        >
          <template #cell-product="{ row: item }"><span class="font-medium text-ink">{{ item.drug_name }}</span></template>
          <template #cell-category="{ row: item }">{{ item.medication_type }}</template>
          <template #cell-quantity="{ row: item }">
            <span :class="item.quantity === 0 ? 'font-bold text-tone-danger-text' : ''">{{ item.quantity }}</span>
          </template>
          <template #cell-threshold="{ row: item }"><span class="text-ink-muted">{{ item.threshold }}</span></template>
          <template #cell-status="{ row: item }">
            <StatusBadge
              :tone="item.quantity === 0 ? 'danger' : 'warning'"
              :label="item.quantity === 0 ? t('secretariat.home.critical_stock_table.out_of_stock') : t('secretariat.home.critical_stock_table.low_stock')"
            />
          </template>
        </ResponsiveTable>
      </AppCard>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useSecretariatHomeStore } from '@/stores/secretariatHomeStore';
import { PageHeader, AppCard, FormField, StatTile, StatusBadge, ResponsiveTable } from '@/components/ui';
import { buttonClasses } from '@/utils/ui';
import { toneClasses } from '@/design/tones';
import {
  BanknotesIcon, ArrowTrendingDownIcon, ArrowTrendingUpIcon, ArrowUpTrayIcon, UserPlusIcon,
  ExclamationTriangleIcon, CubeIcon, ClockIcon, SparklesIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const homeStore = useSecretariatHomeStore();

// Colonnes du tableau des stocks critiques (cartes sous lg) et style des champs de periode.
const stockColumns = computed(() => [
  { key: 'product', label: t('secretariat.home.critical_stock_table.product') },
  { key: 'category', label: t('secretariat.home.critical_stock_table.category') },
  { key: 'quantity', label: t('secretariat.home.critical_stock_table.quantity'), align: 'right' },
  { key: 'threshold', label: t('secretariat.home.critical_stock_table.threshold'), align: 'right' },
  { key: 'status', label: t('secretariat.home.critical_stock_table.status') },
]);
const fieldClass = 'min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
