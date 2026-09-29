<template>
  <div class="space-y-6 w-full">

    <div class="bg-white p-6 rounded-2xl shadow-xs border border-gray-100">
      <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('hospitalization.title') }}</h1>
      <p class="text-sm text-gray-500">{{ t('hospitalization.subtitle') }}</p>
    </div>

    <div class="bg-white rounded-2xl shadow-xs border border-gray-100 overflow-hidden">
      <div v-if="hospitalizationStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></span>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.admitted_since') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.days') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.current_status') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('hospitalization.table.admitted_by') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('appointments.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="stay in hospitalizationStore.current" :key="stay.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <button @click="goToDossier(stay.patient_id)" class="text-sm font-medium text-emerald-700 hover:underline">
                  {{ stay.patient_first_name }} {{ stay.patient_last_name }}
                </button>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(stay.admitted_at) }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ daysSince(stay.admitted_at) }}</td>
              <td class="px-6 py-4 text-sm" :class="statusColorClass(latestStatusOf(stay))">
                {{ latestStatusOf(stay) ? t(`hospitalization.status.${latestStatusOf(stay)}`) : t('hospitalization.no_status_yet') }}
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ stay.admitted_by_name || t('hospitalization.unknown_user') }}</td>
              <td class="px-6 py-4 text-right">
                <button @click="goToDossier(stay.patient_id)" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition">
                  {{ t('appointments.actions.view_dossier') }}
                </button>
              </td>
            </tr>
            <tr v-if="hospitalizationStore.current.length === 0">
              <td colspan="6" class="px-6 py-8 text-center text-gray-500 italic">
                {{ t('hospitalization.empty_list') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import dayjs from 'dayjs';
import { useHospitalizationStore } from '@/stores/hospitalizationStore';

const { t } = useI18n();
const router = useRouter();
const hospitalizationStore = useHospitalizationStore();

function formatDate(d) {
  return dayjs(d).format('DD/MM/YYYY HH:mm');
}
function daysSince(d) {
  return dayjs().diff(dayjs(d), 'day');
}
function latestStatusOf(stay) {
  return stay.status_updates?.length ? stay.status_updates[0].status : null;
}
function statusColorClass(status) {
  if (status === 'AMELIORATION') return 'text-emerald-700 font-medium';
  if (status === 'AGGRAVATION') return 'text-red-700 font-medium';
  return 'text-gray-600';
}
function goToDossier(patientId) {
  router.push(`/medical/patients/${patientId}`);
}

onMounted(() => {
  hospitalizationStore.fetchCurrent();
});
</script>
