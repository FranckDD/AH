<template>
  <div class="space-y-8 w-full">

    <div class="flex flex-col md:flex-row md:items-center md:justify-between bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <div>
        <h1 class="text-3xl font-extrabold text-gray-800 tracking-tight">
          {{ t('doctorKpi.title') }}
        </h1>
        <p class="mt-2 text-gray-500">{{ t('doctorKpi.subtitle') }}</p>
      </div>

      <div class="mt-4 md:mt-0 flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-3 items-end">
        <div class="flex flex-col">
          <label class="text-xs font-medium text-gray-500 mb-1">{{ t('doctorKpi.period_from') }}</label>
          <input
            type="date"
            v-model="kpiStore.filters.startDate"
            @change="applyFilters"
            class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-teal-500 focus:border-teal-500"
          />
        </div>

        <div class="flex flex-col">
          <label class="text-xs font-medium text-gray-500 mb-1">{{ t('doctorKpi.period_to') }}</label>
          <input
            type="date"
            v-model="kpiStore.filters.endDate"
            @change="applyFilters"
            class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-teal-500 focus:border-teal-500"
          />
        </div>
      </div>
    </div>

    <div v-if="kpiStore.isLoading" class="p-10 text-center text-gray-500">
      {{ t('common.loading') }}
    </div>

    <template v-else>
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
        <StatCard
          :title="t('doctorKpi.total_appointments')"
          :value="kpiStore.stats.totalAppointments"
          :icon="CalendarDaysIcon"
          colorClass="bg-teal-50"
          iconColor="text-teal-600"
        />
        <StatCard
          :title="t('doctorKpi.distinct_patients')"
          :value="kpiStore.stats.distinctPatients"
          :icon="UserGroupIcon"
          colorClass="bg-indigo-50"
          iconColor="text-indigo-600"
        />
        <StatCard
          :title="t('doctorKpi.medical_records_total')"
          :value="kpiStore.stats.medicalRecordsCount"
          :icon="ClipboardDocumentListIcon"
          colorClass="bg-amber-50"
          iconColor="text-amber-600"
          :trend="t('doctorKpi.medical_records_note')"
          :trendIsPositive="true"
        />
        <StatCard
          :title="t('doctorKpi.prescriptions_total')"
          :value="kpiStore.stats.prescriptionsCount"
          :icon="ClipboardDocumentListIcon"
          colorClass="bg-rose-50"
          iconColor="text-rose-600"
        />
        <StatCard
          :title="t('doctorKpi.hospitalizations_current')"
          :value="kpiStore.stats.hospitalizationsCurrentCount"
          :icon="ClipboardDocumentListIcon"
          colorClass="bg-sky-50"
          iconColor="text-sky-600"
        />
      </div>

      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4">
          {{ t('doctorKpi.pending_review_title') }}
        </h2>
        <p v-if="kpiStore.claimError" class="text-sm text-red-600 mb-3">{{ kpiStore.claimError }}</p>
        <div v-if="kpiStore.pendingReview.length === 0" class="text-sm text-gray-400">
          {{ t('doctorKpi.pending_review_empty') }}
        </div>
        <div v-else class="divide-y divide-gray-100">
          <div v-for="r in kpiStore.pendingReview" :key="r.record_id" class="py-3 flex items-center justify-between">
            <div>
              <router-link :to="`/medical/patients/${r.patient_id}`" class="font-medium text-teal-700 hover:underline">
                {{ r.patient_name }}
              </router-link>
              <p class="text-xs text-gray-400">{{ r.motif_code }} — {{ t('doctorKpi.pending_review_by') }} {{ r.created_by_name || '?' }}</p>
            </div>
            <button
              v-if="canClaim"
              @click="kpiStore.claimRecord(r.record_id)"
              class="px-3 py-1.5 text-xs font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-700 transition"
            >
              {{ t('doctorKpi.claim_button') }}
            </button>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h2 class="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4">
            {{ t('doctorKpi.by_status') }}
          </h2>
          <div v-if="statusBars.length === 0" class="text-sm text-gray-400">
            {{ t('doctorKpi.no_data') }}
          </div>
          <div v-else class="space-y-3">
            <div v-for="row in statusBars" :key="row.key" class="flex items-center gap-3">
              <span class="w-28 flex-shrink-0 text-sm text-gray-600">{{ row.label }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
                <div class="bg-teal-500 h-2.5 rounded-full" :style="{ width: row.pct + '%' }"></div>
              </div>
              <span class="w-10 flex-shrink-0 text-right text-sm font-semibold text-gray-800">{{ row.count }}</span>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h2 class="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4">
            {{ t('doctorKpi.by_motif') }}
          </h2>
          <div v-if="motifBars.length === 0" class="text-sm text-gray-400">
            {{ t('doctorKpi.no_data') }}
          </div>
          <div v-else class="space-y-3">
            <div v-for="row in motifBars" :key="row.key" class="flex items-center gap-3">
              <span class="w-28 flex-shrink-0 text-sm text-gray-600 truncate" :title="row.label">{{ row.label }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
                <div class="bg-amber-500 h-2.5 rounded-full" :style="{ width: row.pct + '%' }"></div>
              </div>
              <span class="w-10 flex-shrink-0 text-right text-sm font-semibold text-gray-800">{{ row.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDoctorKpiStore } from '@/stores/doctorKpiStore';
import { useAuthStore } from '@/stores/auth';
import StatCard from '@/components/dashboard/StatCard.vue';
import {
  CalendarDaysIcon,
  UserGroupIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const kpiStore = useDoctorKpiStore();
const authStore = useAuthStore();

// La file "Patients en attente" est visible par medecin et nurse (lecture
// partagee voulue), mais claim_review() cote backend est medecin-only : un
// nurse qui cliquerait aurait toujours un 403. On cache donc le bouton pour
// qui n'est pas medecin, meme pattern que
// NurseShiftsView.vue::canManage / authStore.hasRole().
const canClaim = computed(() => authStore.hasRole(['medecin']));

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
