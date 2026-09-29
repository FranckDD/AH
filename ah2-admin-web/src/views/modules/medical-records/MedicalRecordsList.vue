<template>
  <div class="space-y-6 w-full">

    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('medicalRecords.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('medicalRecords.subtitle') }}</p>
      </div>

      <button
        @click="openCreateModal"
        class="flex items-center px-6 py-2.5 bg-teal-600 text-white rounded-xl hover:bg-teal-700 shadow-md shadow-teal-200 transition font-semibold"
      >
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('medicalRecords.new_record') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-xs border border-gray-100 flex flex-wrap gap-4 items-end">

      <div class="flex-1 min-w-[220px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.search_label') }}</label>
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
          </div>
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('medicalRecords.search_placeholder')"
            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-teal-500 focus:border-teal-500 sm:text-sm"
          >
        </div>
      </div>

      <div class="w-full md:w-44">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.motif_label') }}</label>
        <select v-model="motifFilter" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-hidden focus:ring-teal-500 focus:border-teal-500 sm:text-sm rounded-lg">
          <option value="">{{ t('medicalRecords.motif_all') }}</option>
          <option v-for="m in medicalRecordStore.motifs" :key="m.code" :value="m.code">{{ m.label_fr }}</option>
        </select>
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.severity_label') }}</label>
        <select v-model="severityFilter" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-hidden focus:ring-teal-500 focus:border-teal-500 sm:text-sm rounded-lg">
          <option value="">{{ t('medicalRecords.severity_all') }}</option>
          <option value="low">{{ t('medicalRecords.severity_low') }}</option>
          <option value="medium">{{ t('medicalRecords.severity_medium') }}</option>
          <option value="high">{{ t('medicalRecords.severity_high') }}</option>
        </select>
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.date_from') }}</label>
        <input v-model="dateFrom" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('medicalRecords.date_to') }}</label>
        <input v-model="dateTo" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-xs border border-gray-100 overflow-hidden">

      <div class="p-4 border-b border-gray-100 flex items-center justify-between">
        <div class="text-sm text-gray-500">
          {{ medicalRecordStore.pagination.total }} {{ t('medicalRecords.results_count') }}
        </div>
      </div>

      <div v-if="medicalRecordStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></span>
        <p class="mt-2 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.motif') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.severity') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.diagnosis') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('medicalRecords.table.treatment') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('medicalRecords.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="rec in medicalRecordStore.records" :key="rec.record_id || rec.local_id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900">{{ patientName(rec) }}</div>
                <div class="text-xs text-gray-500">{{ rec.patient?.code_patient }}</div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ (rec.consultation_date || '').substring(0, 10) }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ motifLabel(rec.motif_code) }}</td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 rounded-sm text-xs font-semibold" :class="severityClass(rec.severity)">
                  {{ severityLabel(rec.severity) }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" :title="rec.diagnosis">{{ rec.diagnosis || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" :title="rec.treatment">{{ rec.treatment || '—' }}</td>
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <button
                    @click="openEditModal(rec)"
                    :disabled="!rec.record_id"
                    :title="rec.record_id ? '' : 'En attente de synchronisation'"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('medicalRecords.actions.edit') }}
                  </button>
                  <button
                    @click="handleDelete(rec)"
                    :disabled="!rec.record_id"
                    :title="rec.record_id ? '' : 'En attente de synchronisation'"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('medicalRecords.actions.delete') }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="medicalRecordStore.records.length === 0">
              <td colspan="7" class="px-6 py-8 text-center text-gray-500 italic">
                {{ t('medicalRecords.empty') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="medicalRecordStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">
          {{ t('common.page') }} {{ medicalRecordStore.pagination.page }} / {{ medicalRecordStore.pagination.total_pages }}
        </p>
        <div class="flex space-x-2">
          <button @click="goToPage(medicalRecordStore.pagination.page - 1)" :disabled="medicalRecordStore.pagination.page === 1" class="px-3 py-1 border rounded-sm bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(medicalRecordStore.pagination.page + 1)" :disabled="medicalRecordStore.pagination.page === medicalRecordStore.pagination.total_pages" class="px-3 py-1 border rounded-sm bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>

    </div>

    <MedicalRecordModal
      v-if="showModal"
      :record="editingRecord"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { useI18n } from 'vue-i18n';
import MedicalRecordModal from '@/components/medical-records/MedicalRecordModal.vue';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const medicalRecordStore = useMedicalRecordStore();

onMounted(() => {
  medicalRecordStore.fetchMedicalRecords();
  medicalRecordStore.fetchMotifs();
});

const searchQuery = computed({
  get: () => medicalRecordStore.filters.searchQuery,
  set: (val) => medicalRecordStore.setFilters({ searchQuery: val }),
});

const motifFilter = computed({
  get: () => medicalRecordStore.filters.motifCode,
  set: (val) => medicalRecordStore.setFilters({ motifCode: val }),
});

const severityFilter = computed({
  get: () => medicalRecordStore.filters.severity,
  set: (val) => medicalRecordStore.setFilters({ severity: val }),
});

const dateFrom = computed({
  get: () => medicalRecordStore.filters.dateFrom,
  set: (val) => medicalRecordStore.setFilters({ dateFrom: val }),
});

const dateTo = computed({
  get: () => medicalRecordStore.filters.dateTo,
  set: (val) => medicalRecordStore.setFilters({ dateTo: val }),
});

function goToPage(page) {
  if (page >= 1 && page <= medicalRecordStore.pagination.total_pages) {
    medicalRecordStore.setPage(page);
  }
}

function patientName(rec) {
  const p = rec.patient;
  if (!p) return '—';
  return [p.first_name, p.last_name].filter(Boolean).join(' ');
}

function motifLabel(code) {
  const m = medicalRecordStore.motifs.find((x) => x.code === code);
  return m ? m.label_fr : (code || '—');
}

// Coloration par gravite - port exact de mr_list_view.py (rouge/jaune/vert).
function severityClass(severity) {
  if (severity === 'high') return 'bg-red-100 text-red-700';
  if (severity === 'medium') return 'bg-yellow-100 text-yellow-700';
  if (severity === 'low') return 'bg-emerald-100 text-emerald-700';
  return 'bg-gray-100 text-gray-500';
}

function severityLabel(severity) {
  if (severity === 'high') return t('medicalRecords.severity_high');
  if (severity === 'medium') return t('medicalRecords.severity_medium');
  if (severity === 'low') return t('medicalRecords.severity_low');
  return '—';
}

const showModal = ref(false);
const editingRecord = ref(null);

function openCreateModal() {
  editingRecord.value = null;
  showModal.value = true;
}

function openEditModal(rec) {
  editingRecord.value = rec;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingRecord.value = null;
}

async function handleSave(data) {
  try {
    if (editingRecord.value) {
      await medicalRecordStore.updateMedicalRecord(editingRecord.value.record_id ?? editingRecord.value.local_id, data);
    } else {
      await medicalRecordStore.createMedicalRecord(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement dossier medical:', err);
    alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
  }
}

async function handleDelete(rec) {
  if (!confirm(t('medicalRecords.confirm_delete'))) return;
  try {
    await medicalRecordStore.deleteMedicalRecord(rec.record_id);
  } catch (err) {
    console.error('Erreur suppression dossier medical:', err);
    alert('Erreur lors de la suppression : ' + (err.response?.data?.detail || err.message));
  }
}
</script>
