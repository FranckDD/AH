<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('consultations.title')" :subtitle="t('consultations.subtitle')">
      <template #actions>
        <AppButton variant="secondary" @click="showExportModal = true">
          {{ t('export.confirm') }}
        </AppButton>
        <AppButton :icon="PlusIcon" @click="openModal(null)">
          {{ t('consultations.new_consultation') }}
        </AppButton>
      </template>
    </PageHeader>

    <div class="relative w-full md:max-w-md">
      <label for="cs-search" class="sr-only">{{ t('consultations.search_placeholder') }}</label>
      <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
      <input
        id="cs-search"
        v-model.lazy="searchQuery"
        @keyup.enter="consultationStore.fetchConsultations()"
        type="text"
        :placeholder="t('consultations.search_placeholder')"
        class="block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white pl-10 pr-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600"
      />
    </div>

    <section class="grid gap-3">
      <ResponsiveTable
        :columns="columns"
        :rows="consultationStore.consultations"
        row-key="consultation_id"
        :loading="consultationStore.isLoading"
        :empty-title="t('consultations.empty')"
        :empty-message="' '"
      >
        <template #cell-patient="{ row: rec }">
          <div class="font-medium text-ink">{{ rec.patient_name || `#${rec.patient_id}` }}</div>
          <div v-if="rec.patient_code" class="text-sm text-ink-muted">{{ rec.patient_code }}</div>
        </template>
        <template #cell-type="{ row: rec }">
          <StatusBadge
            tone="neutral"
            :label="rec.type_consultation === 'Spiritual' ? t('consultations.type_spiritual') : t('consultations.type_family_restoration')"
          />
        </template>
        <template #cell-date="{ row: rec }">{{ (rec.consultation_date || '').slice(0, 10) }}</template>
        <template #actions="{ row: rec }">
          <AppButton variant="secondary" @click="openModal(rec)">{{ t('consultations.actions.edit') }}</AppButton>
          <AppButton variant="danger" @click="handleDelete(rec)">{{ t('consultations.actions.delete') }}</AppButton>
        </template>
      </ResponsiveTable>

      <div class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <AppButton
          variant="secondary"
          :icon="ChevronLeftIcon"
          :aria-label="t('consultationsScreens.prev_page')"
          @click="consultationStore.setPage(consultationStore.pagination.page - 1)"
          :disabled="consultationStore.pagination.page === 1"
        />
        <span class="text-base font-medium text-ink">{{ t('consultationsScreens.page_label', { n: consultationStore.pagination.page }) }}</span>
        <AppButton
          variant="secondary"
          :icon="ChevronRightIcon"
          :aria-label="t('consultationsScreens.next_page')"
          @click="consultationStore.setPage(consultationStore.pagination.page + 1)"
          :disabled="!consultationStore.hasNextPage"
        />
      </div>
    </section>

    <ConsultationModal
      v-if="showModal"
      :consultation="editingConsultation"
      @close="showModal = false"
      @save="handleSave"
    />

    <ExportModal
      v-if="showExportModal"
      :title="t('export.confirm') + ' : ' + t('consultations.title')"
      :formats="[{ value: 'pdf', label: 'PDF' }, { value: 'csv', label: 'CSV' }]"
      :onExport="exportConsultations"
      @close="showExportModal = false"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useConsultationStore } from '@/stores/consultationStore';
import ConsultationModal from '@/components/consultations/ConsultationModal.vue';
import ExportModal from '@/components/common/ExportModal.vue';
import { AppButton, PageHeader, StatusBadge, ResponsiveTable } from '@/components/ui';
import { PlusIcon, MagnifyingGlassIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';
import api from '@/services/api';

const { t } = useI18n();
const consultationStore = useConsultationStore();

// Colonnes du tableau (cartes sous lg).
const columns = computed(() => [
  { key: 'patient', label: t('consultations.table.patient') },
  { key: 'type', label: t('consultations.table.type') },
  { key: 'date', label: t('consultations.table.date') },
]);

const showModal = ref(false);
const editingConsultation = ref(null);
const showExportModal = ref(false);

const searchQuery = computed({
  get: () => consultationStore.filters.search,
  set: (val) => consultationStore.setFilters({ search: val }),
});

function openModal(rec) {
  editingConsultation.value = rec;
  showModal.value = true;
}

async function handleSave(data) {
  try {
    if (editingConsultation.value) {
      await consultationStore.updateConsultation(editingConsultation.value.consultation_id, data);
    } else {
      await consultationStore.createConsultation(data);
    }
    showModal.value = false;
  } catch (err) {
    alert(err.response?.data?.detail || err.message);
  }
}

async function handleDelete(rec) {
  if (!confirm(t('consultations.confirm_delete'))) return;
  try {
    await consultationStore.deleteConsultation(rec.consultation_id);
  } catch (err) {
    alert(err.response?.data?.detail || err.message);
  }
}

const exportConsultations = async ({ format, dateFrom, dateTo }) => {
  const params = {
    format,
    search: consultationStore.filters.search || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };
  const response = await api.get('/cs/export', {
    params,
    responseType: format === 'pdf' ? 'blob' : 'text',
  });
  const blob = format === 'pdf'
    ? new Blob([response.data], { type: 'application/pdf' })
    : new Blob([response.data], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `consultations_export.${format}`;
  link.click();
  window.URL.revokeObjectURL(url);
};

onMounted(() => {
  consultationStore.fetchConsultations();
});
</script>
