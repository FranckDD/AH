<template>
  <div class="space-y-6 w-full">

    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('consultations.title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('consultations.subtitle') }}</p>
      </div>

      <div class="flex items-center gap-3 w-full md:w-auto">
        <input
          v-model.lazy="searchQuery"
          @keyup.enter="consultationStore.fetchConsultations()"
          type="text"
          :placeholder="t('consultations.search_placeholder')"
          class="block w-full md:w-64 px-3 py-2.5 border border-gray-300 rounded-xl bg-gray-50 focus:ring-teal-500 focus:border-teal-500 sm:text-sm"
        />
        <button @click="showExportModal = true" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition">
          {{ t('export.confirm') }}
        </button>
        <button @click="openModal(null)" class="shrink-0 px-4 py-2.5 bg-teal-600 text-white rounded-xl hover:bg-teal-700 text-sm font-semibold">
          {{ t('consultations.new_consultation') }}
        </button>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-xs border border-gray-100 overflow-hidden">
      <div v-if="consultationStore.isLoading" class="p-10 text-center text-gray-500">
        {{ t('common.loading') }}
      </div>
      <table v-else class="min-w-full divide-y divide-gray-100">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{{ t('consultations.table.patient') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{{ t('consultations.table.type') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{{ t('consultations.table.date') }}</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{{ t('consultations.table.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="consultationStore.consultations.length === 0">
            <td colspan="4" class="px-6 py-8 text-center text-gray-400">{{ t('consultations.empty') }}</td>
          </tr>
          <tr v-for="rec in consultationStore.consultations" :key="rec.consultation_id" class="hover:bg-gray-50">
            <td class="px-6 py-4 text-sm text-gray-700">
              <div class="font-medium text-gray-800">{{ rec.patient_name || `#${rec.patient_id}` }}</div>
              <div v-if="rec.patient_code" class="text-xs text-gray-400">{{ rec.patient_code }}</div>
            </td>
            <td class="px-6 py-4 text-sm text-gray-700">
              {{ rec.type_consultation === 'Spiritual' ? t('consultations.type_spiritual') : t('consultations.type_family_restoration') }}
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">{{ (rec.consultation_date || '').slice(0, 10) }}</td>
            <td class="px-6 py-4 text-right text-sm space-x-2">
              <button @click="openModal(rec)" class="text-teal-600 hover:text-teal-800">{{ t('consultations.actions.edit') }}</button>
              <button @click="handleDelete(rec)" class="text-red-500 hover:text-red-700">{{ t('consultations.actions.delete') }}</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <button
          @click="consultationStore.setPage(consultationStore.pagination.page - 1)"
          :disabled="consultationStore.pagination.page === 1"
          class="px-3 py-1 border rounded-sm bg-white disabled:opacity-50"
        >&laquo;</button>
        <span class="text-sm text-gray-500">{{ consultationStore.pagination.page }}</span>
        <button
          @click="consultationStore.setPage(consultationStore.pagination.page + 1)"
          :disabled="!consultationStore.hasNextPage"
          class="px-3 py-1 border rounded-sm bg-white disabled:opacity-50"
        >&raquo;</button>
      </div>
    </div>

    <ConsultationModal
      v-if="showModal"
      :consultation="editingConsultation"
      @close="showModal = false"
      @save="handleSave"
    />

    <ExportModal
      v-if="showExportModal"
      :title="t('export.confirm') + ' — ' + t('consultations.title')"
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
import api from '@/services/api';

const { t } = useI18n();
const consultationStore = useConsultationStore();

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
