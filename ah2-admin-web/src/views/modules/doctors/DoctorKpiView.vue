<template>
  <div class="grid gap-6 w-full">

    <PageHeader :title="t('doctorKpi.title')" :subtitle="t('doctorKpi.subtitle')" />

    <p v-if="kpiStore.isLoading" class="p-10 text-center text-base text-ink-muted" role="status">
      {{ t('common.loading') }}
    </p>

    <template v-else>

      <div
        v-if="blocks.showLoadError"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 rounded-card border p-4 text-base"
        :class="toneClasses('danger')"
      >
        <span class="font-medium">{{ t('doctorKpi.load_error') }}</span>
        <AppButton variant="secondary" @click="kpiStore.fetchKpiData()">{{ t('ui.retry') }}</AppButton>
      </div>

      <!-- 1. A faire d'abord : les patients dont les parametres ont ete pris et qui attendent un medecin -->
      <AppCard :title="t('doctorKpi.pending_review_title')" :subtitle="t('doctorKpi.queue_help')">
        <p v-if="kpiStore.claimError" role="alert" class="mb-3 text-base font-medium text-tone-danger-text">{{ kpiStore.claimError }}</p>

        <LoadErrorState v-if="blocks.queueState === 'error'" compact @retry="kpiStore.fetchPendingReview()" />

        <EmptyState
          v-else-if="blocks.queueState === 'empty'"
          :title="t('doctorKpi.pending_review_empty')"
          :message="t('doctorKpi.queue_empty_help')"
        />

        <ul v-else class="divide-y divide-tone-neutral-border">
          <li
            v-for="r in kpiStore.pendingReview"
            :key="r.record_id"
            class="flex flex-col gap-3 py-4 md:flex-row md:items-center md:justify-between"
          >
            <div class="min-w-0">
              <router-link
                :to="`/medical/patients/${r.patient_id}`"
                class="text-lg font-semibold text-brand-700 hover:underline focus-visible:outline-2 focus-visible:outline-brand-600"
              >
                {{ r.patient_name }}
              </router-link>
              <p class="text-base text-ink">{{ r.motif_code }}</p>
              <p class="text-sm text-ink-muted">{{ t('doctorKpi.pending_review_by') }} {{ r.created_by_name || '?' }}</p>
            </div>

            <div class="flex flex-col gap-2 md:flex-row md:items-center">
              <StatusBadge
                v-if="waitingLabel(r)"
                :tone="waitingTone(waitingSince(r.consultation_date))"
                :label="waitingLabel(r)"
              />
              <AppButton v-if="blocks.canClaim" @click="handleClaim(r)">
                {{ t('doctorKpi.claim_button') }}
              </AppButton>
            </div>
          </li>
        </ul>
      </AppCard>

      <!-- 2. Acces rapides : ces ecrans ont leurs propres donnees, on y renvoie sans les dupliquer ici -->
      <section :aria-label="t('doctorKpi.quick_title')">
        <h2 class="mb-3 text-lg font-semibold text-ink">{{ t('doctorKpi.quick_title') }}</h2>
        <div class="grid gap-4 sm:grid-cols-3">
          <router-link
            v-for="link in quickLinks"
            :key="link.to"
            :to="link.to"
            class="flex min-h-11 items-center gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600"
          >
            <component :is="link.icon" class="h-6 w-6 shrink-0 text-brand-700" aria-hidden="true" />
            <span class="text-base font-medium text-ink">{{ link.label }}</span>
            <span v-if="link.count !== null" class="ml-auto text-xl font-bold text-ink">{{ link.count }}</span>
          </router-link>
        </div>
      </section>

      <!-- 3. Statistiques de la periode, en bas -->
      <AppCard :title="t('doctorKpi.stats_title')">
        <template #actions>
          <FormField id="kpi-start" :label="t('doctorKpi.period_from')" v-slot="{ describedBy }">
            <input
              id="kpi-start"
              type="date"
              v-model="kpiStore.filters.startDate"
              :aria-describedby="describedBy"
              @change="applyFilters"
              class="min-h-11 rounded-control border border-tone-neutral-border px-3 text-base focus-visible:outline-2 focus-visible:outline-brand-600"
            />
          </FormField>
          <FormField id="kpi-end" :label="t('doctorKpi.period_to')" v-slot="{ describedBy }">
            <input
              id="kpi-end"
              type="date"
              v-model="kpiStore.filters.endDate"
              :aria-describedby="describedBy"
              @change="applyFilters"
              class="min-h-11 rounded-control border border-tone-neutral-border px-3 text-base focus-visible:outline-2 focus-visible:outline-brand-600"
            />
          </FormField>
        </template>

        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div
            v-for="tile in tiles"
            :key="tile.key"
            class="rounded-card border border-tone-neutral-border bg-white p-4"
          >
            <p class="text-sm text-ink-muted">{{ tile.label }}</p>
            <p class="mt-1 text-3xl font-bold text-ink">{{ tile.value }}</p>
            <p v-if="tile.note" class="mt-1 text-sm text-ink-muted">{{ tile.note }}</p>
          </div>
        </div>

        <div class="mt-6 grid gap-6 md:grid-cols-2">
          <div v-if="blocks.showStatusPanel">
            <h3 class="mb-3 text-base font-semibold text-ink">{{ t('doctorKpi.by_status') }}</h3>
            <p v-if="statusBars.length === 0" class="text-base text-ink-muted">{{ t('doctorKpi.no_data') }}</p>
            <div v-else class="space-y-3">
              <div v-for="row in statusBars" :key="row.key" class="flex items-center gap-3">
                <span class="w-28 shrink-0 text-base text-ink">{{ row.label }}</span>
                <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-tone-neutral-bg">
                  <div class="h-2.5 rounded-full bg-brand-600" :style="{ width: row.pct + '%' }"></div>
                </div>
                <span class="w-10 shrink-0 text-right text-base font-semibold text-ink">{{ row.count }}</span>
              </div>
            </div>
          </div>

          <div v-if="blocks.showMotifPanel">
            <h3 class="mb-3 text-base font-semibold text-ink">{{ t('doctorKpi.by_motif') }}</h3>
            <p v-if="motifBars.length === 0" class="text-base text-ink-muted">{{ t('doctorKpi.no_data') }}</p>
            <div v-else class="space-y-3">
              <div v-for="row in motifBars" :key="row.key" class="flex items-center gap-3">
                <span class="w-28 shrink-0 truncate text-base text-ink" :title="row.label">{{ row.label }}</span>
                <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-tone-neutral-bg">
                  <div class="h-2.5 rounded-full bg-brand-600" :style="{ width: row.pct + '%' }"></div>
                </div>
                <span class="w-10 shrink-0 text-right text-base font-semibold text-ink">{{ row.count }}</span>
              </div>
            </div>
          </div>
        </div>
      </AppCard>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useDoctorKpiStore } from '@/stores/doctorKpiStore';
import { useAuthStore } from '@/stores/auth';
import { AppButton, AppCard, PageHeader, StatusBadge, EmptyState, FormField, LoadErrorState } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { dashboardBlocks, waitingSince, waitingTone } from '@/utils/doctorDashboardLayout';
import {
  CalendarDaysIcon,
  UserGroupIcon,
  BuildingOffice2Icon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const router = useRouter();
const kpiStore = useDoctorKpiStore();
const authStore = useAuthStore();

// La file "Patients en attente" est visible par medecin et nurse (lecture
// partagee voulue), mais claim_review() cote backend est medecin-only : un
// nurse qui cliquerait aurait toujours un 403. On cache donc le bouton pour
// qui n'est pas medecin (blocks.canClaim).
// Les KPI RDV et prescriptions sont calcules pour l'utilisateur connecte en
// tant que medecin assigne / prescripteur : une infirmiere n'est ni l'un ni
// l'autre, ces cartes seraient toujours a 0, on les cache (blocks.statTiles).
const blocks = computed(() => dashboardBlocks({
  role: authStore.userRole,
  pendingCount: kpiStore.pendingReview.length,
  error: kpiStore.error,
  pendingFailed: kpiStore.pendingFailed,
}));

const tileDefs = computed(() => ({
  totalAppointments: { label: t('doctorKpi.total_appointments'), value: kpiStore.stats.totalAppointments },
  distinctPatients: { label: t('doctorKpi.distinct_patients'), value: kpiStore.stats.distinctPatients },
  medicalRecords: {
    label: t('doctorKpi.medical_records_total'),
    value: kpiStore.stats.medicalRecordsCount,
    note: t('doctorKpi.medical_records_note'),
  },
  prescriptions: { label: t('doctorKpi.prescriptions_total'), value: kpiStore.stats.prescriptionsCount },
  hospitalizations: { label: t('doctorKpi.hospitalizations_current'), value: kpiStore.stats.hospitalizationsCurrentCount },
}));
const tiles = computed(() => blocks.value.statTiles.map((key) => ({ key, ...tileDefs.value[key] })));

const quickLinks = computed(() => [
  { to: '/medical/appointments', label: t('doctorKpi.quick_appointments'), icon: CalendarDaysIcon, count: null },
  {
    to: '/medical/hospitalizations',
    label: t('doctorKpi.quick_hospitalizations'),
    icon: BuildingOffice2Icon,
    count: kpiStore.stats.hospitalizationsCurrentCount,
  },
  { to: '/medical/patients', label: t('doctorKpi.quick_patients'), icon: UserGroupIcon, count: null },
]);

function waitingLabel(record) {
  const w = waitingSince(record.consultation_date);
  if (w.kind === 'today') return t('doctorKpi.waiting_today');
  if (w.kind === 'days') return t('doctorKpi.waiting_days', { n: w.days }, w.days);
  return '';
}

// Apres une prise en charge reussie, on redirige vers le dossier
// consolide du patient (chantier 6) : c'est de la que le medecin met a
// jour la consultation, ajoute une prescription, etc. - reutilise le
// flux deja existant plutot que d'en construire un nouveau. En cas
// d'echec (quelqu'un d'autre a pris le dossier entre-temps), on reste
// sur le dashboard - le message d'erreur est deja affiche par le store.
async function handleClaim(record) {
  const success = await kpiStore.claimRecord(record.record_id);
  if (success) {
    router.push({
      path: `/medical/patients/${record.patient_id}`,
      query: { record: record.record_id },
    });
  }
}

const KNOWN_STATUSES = ['pending', 'completed', 'cancelled'];

function statusLabel(status) {
  return KNOWN_STATUSES.includes(status) ? t(`appointments.status_${status}`) : status;
}

function toBars(dict, labelFn) {
  const entries = Object.entries(dict || {});
  const max = Math.max(1, ...entries.map(([, count]) => count));
  return entries
    .map(([key, count]) => ({
      key,
      label: labelFn ? labelFn(key) : key,
      count,
      pct: Math.round((count / max) * 100),
    }))
    .sort((a, b) => b.count - a.count);
}

const statusBars = computed(() => toBars(kpiStore.stats.countByStatus, statusLabel));
const motifBars = computed(() => toBars(kpiStore.stats.consultationDistribution));

const applyFilters = () => {
  kpiStore.setDates(kpiStore.filters.startDate, kpiStore.filters.endDate);
};

onMounted(() => {
  kpiStore.fetchKpiData();
});
</script>
