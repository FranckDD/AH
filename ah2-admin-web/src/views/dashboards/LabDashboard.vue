<template>
  <div class="h-full overflow-y-auto p-4 text-sm md:p-6 [&_table]:text-sm [&_dd]:text-sm">
    <div class="grid w-full gap-6">

      <PageHeader :title="t('lab.dashboard.title')" :subtitle="t('lab.dashboard.subtitle')">
        <template #actions>
          <div role="group" :aria-label="t('labScreens.period_label')" class="flex gap-2">
            <AppButton v-for="p in ['day', 'month', 'year']" :key="p" :variant="currentPeriod === p ? 'primary' : 'secondary'"
                       :aria-pressed="currentPeriod === p" @click="changePeriod(p)">
              {{ t(`lab.dashboard.period_${p}`) }}
            </AppButton>
          </div>
        </template>
      </PageHeader>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <router-link :to="{ name: 'lab-technician' }" :class="tileLink">
          <StatTile :title="t('lab.dashboard.pending')" :value="stats?.pending ?? 0" :note="t('lab.dashboard.pending_hint')" :icon="ClockIcon" tone="warning" />
        </router-link>

        <StatTile :title="t('lab.dashboard.completed')" :value="stats?.completed_today ?? 0" :note="t('lab.dashboard.completed_hint')" :icon="CheckBadgeIcon" tone="success" />

        <router-link :to="{ name: 'lab-history', query: { abnormal: '1', period: currentPeriod } }" :class="tileLink">
          <StatTile :title="t('lab.dashboard.critical')" :value="stats?.critical ?? 0" :note="t('lab.dashboard.critical_hint')" :icon="ExclamationTriangleIcon" tone="danger" alert />
        </router-link>

        <StatTile :title="t('lab.dashboard.total')" :value="stats?.total_month ?? 0" :note="t('lab.dashboard.total_hint')" :icon="ClipboardDocumentListIcon" tone="info" />
      </div>

      <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
        <AppCard class="lg:col-span-2" :title="t('lab.dashboard.recent')">
          <template #actions>
            <router-link :to="{ name: 'lab-technician' }" :class="buttonClasses('info', 'md')">{{ t('lab.dashboard.see_bench') }}</router-link>
          </template>
          <ResponsiveTable
            :columns="columns"
            :rows="passageRows"
            row-key="id"
            :empty-title="t('lab.dashboard.no_pending')"
            :empty-message="' '"
            striped
          >
            <template #cell-patient="{ row: item }">
              <span class="font-semibold">{{ item.patient_name || t('lab.dashboard.unknown_patient') }}</span>
              <span class="block text-sm text-ink-muted">{{ item.code_patient || 'N/A' }}</span>
            </template>
            <template #cell-exam="{ row: item }">
              <span class="flex flex-wrap gap-2">
                <StatusBadge v-for="e in item.exams" :key="e.result_id" :tone="examStatusMeta(e.status).tone"
                             :label="`${e.examen_nom || t('lab.dashboard.col_exam')} : ${t(examStatusMeta(e.status).labelKey)}`" />
              </span>
            </template>
            <template #cell-action="{ row: item }">
              <AppButton @click="goToTechnician(item)">{{ t('lab.dashboard.enter') }}</AppButton>
            </template>
          </ResponsiveTable>
        </AppCard>

        <AppCard :title="t('lab.dashboard.top_exams')">
          <p v-if="!stats?.top_exams || Object.keys(stats.top_exams).length === 0" class="py-4 text-center text-sm text-ink-muted">
            {{ t('lab.dashboard.no_data') }}
          </p>
          <ul v-else class="grid gap-4">
            <li v-for="(count, name) in stats.top_exams" :key="name">
              <div class="mb-1 flex justify-between gap-3 text-sm">
                <span class="min-w-0 break-words text-ink">{{ name }}</span>
                <span class="shrink-0 font-semibold text-ink">{{ count }}</span>
              </div>
              <div class="h-2 w-full overflow-hidden rounded-full bg-tone-neutral-bg" aria-hidden="true">
                <div class="h-2 rounded-full bg-brand-600 transition-all duration-700 ease-out"
                     :style="{ width: (count / (stats.max_exam_count || 1) * 100) + '%' }"></div>
              </div>
            </li>
          </ul>
        </AppCard>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useLabStore } from '@/stores/labStore';
import { AppButton, AppCard, PageHeader, StatTile, StatusBadge, ResponsiveTable } from '@/components/ui';
import { examStatusMeta } from '@/utils/labPassages';
import { buttonClasses } from '@/utils/ui';
import { 
    ClockIcon, CheckBadgeIcon, ExclamationTriangleIcon, 
    ArrowTrendingUpIcon, ClipboardDocumentListIcon 
} from '@heroicons/vue/24/outline';

const router = useRouter();
const { t } = useI18n();
const labStore = useLabStore();

// Dernieres entrees : un patient une seule fois, avec tous les examens de son passage (repli sur l'ancienne liste).
const passageRows = computed(() => {
    const passages = stats.value.recent_passages;
    if (passages && passages.length) {
        return passages.map((p) => ({ ...p, id: p.first_pending_id, key: p.batch_id || `solo-${p.first_pending_id}` }));
    }
    return (stats.value.recent_pending || []).map((r) => ({
        ...r, key: `solo-${r.id}`, exams: [{ result_id: r.id, examen_nom: r.test_type, status: 'pending' }],
    }));
});

// Colonnes des entrees recentes (cartes empilees sous lg) et style des tuiles cliquables.
const columns = computed(() => [
    { key: 'patient', label: t('lab.dashboard.col_patient') },
    { key: 'exam', label: t('lab.dashboard.col_exam') },
    { key: 'action', label: t('lab.dashboard.col_action'), align: 'right' },
]);
const tileLink = 'block rounded-card focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600';

const currentPeriod = ref('month');
let refreshInterval = null;

/**
 * Calcul sécurisé des statistiques. 
 * Garantit que le template a toujours une structure d'objet valide même si l'API échoue.
 */
const stats = computed(() => {
    return labStore.stats || {
        pending: 0,
        completed_today: 0,
        critical: 0,
        total_month: 0,
        recent_pending: [],
        recent_passages: [],
        top_exams: {},
        max_exam_count: 1
    };
});

/**
 * Charge les données depuis le store
 */
const loadData = async () => {
    try {
        await labStore.fetchDashboardStats(currentPeriod.value);
    } catch (error) {
        console.error("Erreur UI Dashboard:", error);
    }
};

/**
 * Change la période de filtrage
 */
const changePeriod = async (period) => {
    currentPeriod.value = period;
    await loadData();
};

onMounted(() => {
    loadData();
    // Rafraîchissement automatique toutes les 5 minutes
    refreshInterval = setInterval(loadData, 300000);
});

onUnmounted(() => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
});

/**
 * Navigation vers la paillasse avec filtre auto
 */
const goToTechnician = (item) => {
    if (item?.id) {
        router.push({ name: 'lab-technician', query: { open: String(item.id) } });
    }
};
</script>
