<!-- src/views/modules/reports/Reports.vue -->
<!-- Rapports (promoteur et admin, lecture seule) : disposition A validee sur maquette. En haut l'encadre
     "Controle du jour", puis 13 cartes en quatre blocs (Argent, Produits, Production, Croissance), une carte par
     indicateur avec sa periode et sa source, puis le tableau "Total vendu par produit". L'admin regle en plus les
     deux seuils du controle. Periode : jours LOCAUX (aujourd'hui, 7 jours, 30 jours, dates libres). -->
<template>
  <div class="grid w-full gap-6">
    <PageHeader :title="t('reports.title')" :subtitle="t('reports.subtitle')" />

    <AppCard :title="t('reports.period.title')">
      <div class="flex flex-col gap-3">
        <div role="group" :aria-label="t('reports.period.title')" class="flex flex-wrap gap-2">
          <AppButton v-for="p in PRESETS" :key="p" :variant="preset === p ? 'brand' : 'brandOutline'"
                     :aria-pressed="preset === p ? 'true' : 'false'" @click="choose(p)">{{ t(`reports.period.${p}`) }}</AppButton>
        </div>
        <form v-if="preset === 'custom'" class="flex flex-col gap-3 sm:flex-row sm:items-end" novalidate @submit.prevent="applyCustom">
          <FormField id="rp-from" :label="t('reports.period.from')" v-slot="{ describedBy }">
            <input id="rp-from" v-model="customFrom" type="date" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="rp-to" :label="t('reports.period.to')" v-slot="{ describedBy }">
            <input id="rp-to" v-model="customTo" type="date" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <AppButton type="submit" variant="primary">{{ t('reports.period.apply') }}</AppButton>
        </form>
        <p v-if="periodError" role="alert" class="text-base text-tone-danger-text">{{ t(periodError) }}</p>
        <p class="text-base text-ink-muted" role="status">{{ periodLabel }}</p>
        <div class="flex flex-wrap items-center gap-3">
          <AppButton variant="secondary" :loading="exporting" :disabled="!period.from || !period.to"
                     @click="exportPdf">{{ exporting ? t('reports.export.loading') : t('reports.export.button') }}</AppButton>
          <p v-if="exportError" role="alert" class="text-base text-tone-danger-text">{{ exportError }}</p>
        </div>
      </div>
    </AppCard>

    <ReportsControlBox :control="store.overview?.control || null" :loading="store.overviewLoading && !store.overview"
                       :error="store.overviewError" @retry="reload" />

    <p v-if="store.overviewLoading && store.overview" role="status" class="text-base text-ink-muted">{{ t('reports.states.refreshing') }}</p>

    <template v-if="store.overview">
      <section v-for="block in CARD_BLOCKS" :key="block.key" class="grid gap-3" :aria-labelledby="`block-${block.key}`">
        <h2 :id="`block-${block.key}`" class="text-xl font-semibold text-ink">{{ t(`reports.blocks.${block.key}`) }}</h2>
        <div :class="block.key === 'growth' ? 'grid gap-4 xl:grid-cols-2' : 'grid gap-4 md:grid-cols-2 xl:grid-cols-3'">
          <template v-for="id in block.cards" :key="id">
            <ReportCard v-if="cardData(store.overview, id)" :card-id="id" :card="cardData(store.overview, id)">
              <ReportsMoneyBody v-if="block.key === 'money'" :card-id="id" :card="cardData(store.overview, id)" />
              <ReportsStockBody v-else-if="block.key === 'products' || block.key === 'production'" :card-id="id" :card="cardData(store.overview, id)" />
              <ReportsGrowthChart v-else :mode="id" :card="cardData(store.overview, id)" />
            </ReportCard>
          </template>
        </div>
      </section>
    </template>
    <div v-else-if="store.overviewLoading" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-hidden="true">
      <div v-for="n in 6" :key="n" class="h-40 animate-pulse rounded-card border border-tone-neutral-border bg-tone-neutral-bg"></div>
    </div>
    <EmptyState v-else-if="!store.overviewError" :title="t('reports.states.empty')" />

    <ReportsProductsTable v-if="period.from && period.to" :key="`table-${authStore.user?.id ?? 'none'}`" :period="period" />

    <ReportsSettings v-if="isAdmin" :key="`settings-${authStore.user?.id ?? 'none'}`" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, AppCard, EmptyState, FormField, PageHeader } from '@/components/ui';
import ReportCard from '@/components/reports/ReportCard.vue';
import ReportsControlBox from '@/components/reports/ReportsControlBox.vue';
import ReportsMoneyBody from '@/components/reports/ReportsMoneyBody.vue';
import ReportsStockBody from '@/components/reports/ReportsStockBody.vue';
import ReportsGrowthChart from '@/components/reports/ReportsGrowthChart.vue';
import ReportsProductsTable from '@/components/reports/ReportsProductsTable.vue';
import ReportsSettings from '@/components/reports/ReportsSettings.vue';
import { useAuthStore } from '@/stores/auth';
import { useReportsStore } from '@/stores/reportsStore';
import { ReportsGateway } from '@/services/ReportsGateway';
import { CARD_BLOCKS, cardData, periodRange, customPeriodError, formatLocalDate } from '@/utils/reports';

const { t, locale } = useI18n();
const authStore = useAuthStore();
const store = useReportsStore();
const isAdmin = computed(() => authStore.hasRole(['admin']));

const PRESETS = ['today', '7d', '30d', 'custom'];
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const preset = ref('today');
const period = ref(periodRange('today'));
const customFrom = ref(period.value.from);
const customTo = ref(period.value.to);
const periodError = ref('');

const periodLabel = computed(() => (period.value.from === period.value.to
  ? t('reports.period.showing_day', { date: formatLocalDate(period.value.from, locale.value) })
  : t('reports.period.showing_range', { from: formatLocalDate(period.value.from, locale.value), to: formatLocalDate(period.value.to, locale.value) })));

function choose(p) {
  preset.value = p;
  periodError.value = '';
  if (p !== 'custom') period.value = periodRange(p);
}

function applyCustom() {
  periodError.value = customPeriodError(customFrom.value, customTo.value);
  if (periodError.value) return;
  period.value = periodRange('custom', new Date(), { from: customFrom.value, to: customTo.value });
}

// Export PDF de la periode affichee (dates locales AAAA-MM-JJ deja construites, aucune conversion UTC).
const exporting = ref(false);
const exportError = ref('');

async function blobErrorDetail(err) {
  const data = err?.response?.data;
  if (data instanceof Blob) {
    try {
      const detail = JSON.parse(await data.text())?.detail;
      return typeof detail === 'string' ? detail : '';
    } catch {
      return '';
    }
  }
  return typeof data?.detail === 'string' ? data.detail : '';
}

async function exportPdf() {
  if (exporting.value) return;
  exporting.value = true;
  exportError.value = '';
  const { from, to } = period.value;
  try {
    const blob = await ReportsGateway.exportPdf(from, to);
    const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `rapports_${from}_${to}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    exportError.value = (await blobErrorDetail(err)) || t('reports.export.error');
  } finally {
    exporting.value = false;
  }
}

function reload() {
  store.loadOverview(period.value);
}

watch(period, reload);
watch(() => authStore.user?.id, (id) => {
  store.ensureOwner(id);
  reload();
});
// Avant le montage des enfants : le tableau charge des son montage, apres le changement de proprietaire.
store.ensureOwner(authStore.user?.id);
onMounted(reload);
</script>
