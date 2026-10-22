<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('hospitalization.title')" :subtitle="t('hospitalization.subtitle')" />

    <ResponsiveTable
      :columns="columns"
      :rows="hospitalizationStore.current"
      row-key="id"
      :loading="hospitalizationStore.isLoading"
      :empty-title="t('hospitalization.empty_list')"
      :empty-message="' '"
    >
      <template #cell-patient="{ row: stay }">
        <div class="flex items-center gap-2">
          <!-- Aggravation : icone + texte (badge d'etat), jamais la couleur seule -->
          <ExclamationTriangleIcon
            v-if="latestStatusOf(stay) === 'AGGRAVATION'"
            class="h-5 w-5 shrink-0 text-tone-danger-text"
            aria-hidden="true"
          />
          <button
            type="button"
            @click="goToDossier(stay.patient_id)"
            class="text-left text-base font-semibold text-brand-700 hover:underline focus-visible:outline-2 focus-visible:outline-brand-600"
          >
            {{ stay.patient_first_name }} {{ stay.patient_last_name }}
          </button>
        </div>
      </template>
      <template #cell-admitted="{ row: stay }"><span class="font-mono">{{ formatDate(stay.admitted_at) }}</span></template>
      <template #cell-days="{ row: stay }">{{ daysSince(stay.admitted_at) }}</template>
      <template #cell-status="{ row: stay }">
        <StatusBadge
          :tone="statusTone(latestStatusOf(stay))"
          :label="latestStatusOf(stay) ? t(`hospitalization.status.${latestStatusOf(stay)}`) : t('hospitalization.no_status_yet')"
        />
      </template>
      <template #cell-admitted_by="{ row: stay }">{{ stay.admitted_by_name || t('hospitalization.unknown_user') }}</template>

      <template #actions="{ row: stay }">
        <AppButton variant="secondary" @click="goToDossier(stay.patient_id)">
          {{ t('appointments.actions.view_dossier') }}
        </AppButton>
      </template>
    </ResponsiveTable>

  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import dayjs from 'dayjs';
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline';
import { useHospitalizationStore } from '@/stores/hospitalizationStore';
import { AppButton, PageHeader, StatusBadge, ResponsiveTable } from '@/components/ui';

const { t } = useI18n();
const router = useRouter();
const hospitalizationStore = useHospitalizationStore();

const columns = computed(() => [
  { key: 'patient', label: t('hospitalization.table.patient') },
  { key: 'admitted', label: t('hospitalization.table.admitted_since') },
  { key: 'days', label: t('hospitalization.table.days') },
  { key: 'status', label: t('hospitalization.table.current_status') },
  { key: 'admitted_by', label: t('hospitalization.table.admitted_by') },
]);

function formatDate(d) {
  return dayjs(d).format('DD/MM/YYYY HH:mm');
}
function daysSince(d) {
  return dayjs().diff(dayjs(d), 'day');
}
function latestStatusOf(stay) {
  return stay.status_updates?.length ? stay.status_updates[0].status : null;
}
// Vert = amelioration, rouge = aggravation (alerte), neutre sinon.
function statusTone(status) {
  if (status === 'AMELIORATION') return 'success';
  if (status === 'AGGRAVATION') return 'danger';
  return 'neutral';
}
function goToDossier(patientId) {
  router.push(`/medical/patients/${patientId}`);
}

onMounted(() => {
  hospitalizationStore.fetchCurrent();
});
</script>
