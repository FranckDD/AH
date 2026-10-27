<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('toxico.dashboard.title')" :subtitle="t('toxico.dashboard.subtitle')" />

    <LoadErrorState v-if="toxicoStore.statsLoadFailed" compact @retry="toxicoStore.fetchDashboardStats().catch(() => {})" />

    <!-- Quatre repères : bleu (actifs), rouge (rechute), orange (sevrage), vert (nouveaux du mois) -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatTile :title="t('toxico.dashboard.active_patients')" :value="toxicoStore.statsLoadFailed ? '-' : toxicoStore.totalActive" :note="t('toxicoScreens.week_note', { n: newPatientsThisWeek })"
                :icon="UserGroupIcon" tone="info" />

      <StatTile :title="t('toxico.dashboard.relapse_rate')" :value="toxicoStore.statsLoadFailed ? '-' : `${toxicoStore.relapseRate}%`" :icon="ExclamationTriangleIcon" tone="danger">
        <div class="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-tone-neutral-bg" role="progressbar" :aria-valuenow="toxicoStore.relapseRate" aria-valuemin="0" aria-valuemax="100"
             :aria-label="t('toxico.dashboard.relapse_rate')">
          <div class="h-1.5 rounded-full bg-tone-danger-solid" :style="{ width: toxicoStore.relapseRate + '%' }"></div>
        </div>
      </StatTile>

      <StatTile :title="t('toxicoScreens.withdrawal_title')" :value="toxicoStore.statsLoadFailed ? '-' : toxicoStore.statsByPhase[1] || 0" :note="t('toxicoScreens.withdrawal_note')" :icon="FireIcon" tone="warning" />

      <StatTile :title="t('toxico.dashboard.new_this_month')" :value="toxicoStore.statsLoadFailed ? '-' : toxicoStore.currentMonthAdmissions" :icon="CalendarIcon" tone="success" />
    </div>

    <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
      <AppCard class="lg:col-span-2" :title="t('toxico.dashboard.phase_dist')">
        <ul class="grid gap-5">
          <li v-for="phase in [1, 2, 3, 4]" :key="phase">
            <div class="mb-1 flex items-center justify-between gap-3">
              <span class="text-base font-medium text-ink">{{ t(`toxico.phases.${phase}`) }}</span>
              <span class="text-base font-semibold text-ink">{{ t('toxicoScreens.patients_count', toxicoStore.statsByPhase[phase] || 0) }}</span>
            </div>
            <div class="h-3 w-full overflow-hidden rounded-full bg-tone-neutral-bg" role="progressbar" :aria-valuenow="toxicoStore.statsByPhase[phase] || 0" aria-valuemin="0"
                 :aria-valuemax="toxicoStore.totalActive" :aria-label="t('toxicoScreens.phase_bar', { phase: t(`toxico.phases.${phase}`), n: toxicoStore.statsByPhase[phase] || 0 })">
              <div class="h-3 rounded-full transition-all duration-700 ease-out" :class="phaseMeta(phase).bar"
                   :style="{ width: percentOf(toxicoStore.statsByPhase[phase], toxicoStore.totalActive) + '%' }"></div>
            </div>
          </li>
        </ul>
      </AppCard>

      <AppCard :title="t('toxico.dashboard.substance_dist')">
        <ul class="grid gap-3">
          <li v-for="(count, substance) in toxicoStore.statsBySubstance" :key="substance" class="flex items-center justify-between gap-3 rounded-card bg-tone-neutral-bg p-3">
            <div class="flex min-w-0 items-center gap-3">
              <span class="h-8 w-1.5 shrink-0 rounded-full bg-action-600" aria-hidden="true"></span>
              <span class="break-words text-base font-medium text-ink">{{ substance }}</span>
            </div>
            <span class="shrink-0 rounded-control border border-tone-neutral-border bg-white px-3 py-1 text-base font-semibold text-ink">{{ count }}</span>
          </li>
        </ul>
      </AppCard>
    </div>

    <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
      <AppCard v-if="!toxicoStore.isScoped" :title="t('toxico.dashboard.psy_workload')">
        <ResponsiveTable :columns="columns" :rows="toxicoStore.statsByPsy" row-key="name" striped>
          <template #cell-name="{ row: psy }"><span class="font-medium">{{ psy.name }}</span></template>
          <template #cell-count="{ row: psy }">
            <span class="inline-block rounded-full bg-action-50 px-3 py-1 text-base font-semibold text-action-700">{{ psy.count }}</span>
          </template>
        </ResponsiveTable>
      </AppCard>

      <AppCard :title="t('toxico.dashboard.alerts')">
        <p v-if="toxicoStore.generatedAlerts.length === 0" role="status" class="py-4 text-center text-base text-ink-muted">{{ t('toxicoScreens.no_alerts') }}</p>
        <ul v-else class="grid gap-3">
          <li v-for="alert in toxicoStore.generatedAlerts" :key="alert.id" class="flex items-start gap-3 rounded-card border p-3"
              :class="toneClasses(alert.type === 'critical' ? 'danger' : 'warning')">
            <ExclamationCircleIcon v-if="alert.type === 'critical'" class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <ClockIcon v-else class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <div>
              <p class="text-base font-semibold">{{ alert.title }}</p>
              <p class="mt-1 text-sm">{{ alert.message }}</p>
            </div>
          </li>
        </ul>
      </AppCard>
    </div>

  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue';
import { useToxicoStore } from '@/stores/toxicoStore';
import { useI18n } from 'vue-i18n';
import { AppCard, PageHeader, StatTile, ResponsiveTable, LoadErrorState } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { phaseMeta, percentOf } from '@/utils/toxicoUi';
import {
    UserGroupIcon,
    ExclamationTriangleIcon,
    FireIcon,
    CalendarIcon,
    ExclamationCircleIcon,
    ClockIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const toxicoStore = useToxicoStore();

onMounted(() => {
    toxicoStore.fetchToxicoPatients();
    // tuiles globales (dont Admissions du mois) : sans cet appel elles restaient a 0
    toxicoStore.fetchDashboardStats().catch(() => {});
});

// Nouveaux patients des 7 derniers jours : calcul reel sur la liste chargee (meme calcul que la liste des patients).
const newPatientsThisWeek = computed(() => toxicoStore.newThisWeekCount);

// Colonnes de la charge des psychologues (cartes empilees sous lg).
const columns = computed(() => [
    { key: 'name', label: t('toxicoScreens.col_psychologist') },
    { key: 'count', label: t('toxicoScreens.col_followed'), align: 'right' },
]);
</script>
