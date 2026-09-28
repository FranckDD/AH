<template>
  <div class="space-y-6 w-full">

    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('prescriptions.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('prescriptions.subtitle') }}</p>
      </div>

      <button
        @click="openCreateModal"
        class="flex items-center px-6 py-2.5 bg-purple-600 text-white rounded-xl hover:bg-purple-700 shadow-md shadow-purple-200 transition font-semibold"
      >
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('prescriptions.new_prescription') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">

      <div class="flex-1 min-w-[220px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('prescriptions.search_label') }}</label>
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
          </div>
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('prescriptions.search_placeholder')"
            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
          >
        </div>
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('prescriptions.date_from') }}</label>
        <input v-model="dateFrom" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm" />
      </div>

      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('prescriptions.date_to') }}</label>
        <input v-model="dateTo" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm" />
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

      <div class="p-4 border-b border-gray-100 flex items-center justify-between">
        <div class="text-sm text-gray-500">
          {{ prescriptionStore.pagination.total }} {{ t('prescriptions.results_count') }}
        </div>
      </div>

      <div v-if="prescriptionStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></span>
        <p class="mt-2 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.content') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.duration') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.start_date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.end_date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('prescriptions.table.prescriber') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('prescriptions.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="presc in prescriptionStore.prescriptions" :key="presc.prescription_id || presc.local_id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900">{{ patientName(presc) }}</div>
                <div class="text-xs text-gray-500">{{ presc.patient?.code_patient }}</div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">
                <template v-if="presc.is_lab_order">
                  <span class="font-semibold text-purple-800">{{ t('prescriptions.table.lab_order_badge') }}</span>
                  <div class="text-xs text-gray-500">{{ (presc.lab_exams_list || []).join(', ') || '—' }}</div>
                </template>
                <template v-else>
                  <span class="font-semibold text-gray-800">{{ presc.medication }}</span>
                  <div class="text-xs text-gray-500">{{ presc.dosage }} — {{ presc.frequency }}</div>
                </template>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ presc.is_lab_order ? '—' : (presc.duration || '—') }}</td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ presc.start_date }}</td>
              <td class="px-6 py-4 text-sm font-mono">
                <span v-if="!presc.is_lab_order && presc.end_date" class="px-2 py-1 rounded" :class="endDateUrgencyClass(presc)">
                  {{ presc.end_date }}
                </span>
                <span v-else class="text-gray-400">—</span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ presc.prescribed_by_name || '—' }}</td>
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <button
                    @click="openEditModal(presc)"
                    :disabled="!presc.prescription_id"
                    :title="presc.prescription_id ? '' : 'En attente de synchronisation'"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('prescriptions.actions.edit') }}
                  </button>
                  <button
                    @click="handleDelete(presc)"
                    :disabled="!presc.prescription_id"
                    :title="presc.prescription_id ? '' : 'En attente de synchronisation'"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('prescriptions.actions.delete') }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="prescriptionStore.prescriptions.length === 0">
              <td colspan="7" class="px-6 py-8 text-center text-gray-500 italic">
                {{ t('prescriptions.empty') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="prescriptionStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">
          {{ t('common.page') }} {{ prescriptionStore.pagination.page }} / {{ prescriptionStore.pagination.total_pages }}
        </p>
        <div class="flex space-x-2">
          <button @click="goToPage(prescriptionStore.pagination.page - 1)" :disabled="prescriptionStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(prescriptionStore.pagination.page + 1)" :disabled="prescriptionStore.pagination.page === prescriptionStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>

    </div>

    <PrescriptionModal
      v-if="showModal"
      :prescription="editingPrescription"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { usePrescriptionStore } from '@/stores/prescriptionStore';
import { useI18n } from 'vue-i18n';
import PrescriptionModal from '@/components/prescriptions/PrescriptionModal.vue';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const prescriptionStore = usePrescriptionStore();

onMounted(() => {
  prescriptionStore.fetchPrescriptions();
  prescriptionStore.fetchExamTypes();
});

const searchQuery = computed({
  get: () => prescriptionStore.filters.searchQuery,
  set: (val) => prescriptionStore.setFilters({ searchQuery: val }),
});

const dateFrom = computed({
  get: () => prescriptionStore.filters.dateFrom,
  set: (val) => prescriptionStore.setFilters({ dateFrom: val }),
});

const dateTo = computed({
  get: () => prescriptionStore.filters.dateTo,
  set: (val) => prescriptionStore.setFilters({ dateTo: val }),
});

function goToPage(page) {
  if (page >= 1 && page <= prescriptionStore.pagination.total_pages) {
    prescriptionStore.setPage(page);
  }
}

function patientName(presc) {
  const p = presc.patient;
  if (!p) return '—';
  return [p.first_name, p.last_name].filter(Boolean).join(' ');
}

// Coloration "urgence de renouvellement" sur la date de fin - port exact
// de la logique desktop (prescription_list.py) : gris si echue, rouge
// <=3j, orange <=7j, jaune <=14j, vert au-dela. Uniquement pertinent pour
// les prescriptions medicamenteuses (les bons d'examen n'ont pas de date
// de fin, voir le v-if qui encadre l'appel a cette fonction).
function endDateUrgencyClass(presc) {
  const end = new Date(presc.end_date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.floor((end - today) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return 'bg-gray-100 text-gray-500';
  if (diffDays <= 3) return 'bg-red-100 text-red-700 font-semibold';
  if (diffDays <= 7) return 'bg-orange-100 text-orange-700 font-semibold';
  if (diffDays <= 14) return 'bg-yellow-100 text-yellow-700';
  return 'bg-emerald-50 text-emerald-700';
}

const showModal = ref(false);
const editingPrescription = ref(null);

function openCreateModal() {
  editingPrescription.value = null;
  showModal.value = true;
}

function openEditModal(presc) {
  editingPrescription.value = presc;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingPrescription.value = null;
}

async function handleSave(data) {
  try {
    if (editingPrescription.value) {
      await prescriptionStore.updatePrescription(editingPrescription.value.prescription_id, data);
    } else {
      await prescriptionStore.createPrescription(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement prescription:', err);
    alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
  }
}

async function handleDelete(presc) {
  if (!confirm(t('prescriptions.confirm_delete'))) return;
  try {
    await prescriptionStore.deletePrescription(presc.prescription_id);
  } catch (err) {
    console.error('Erreur suppression prescription:', err);
    alert('Erreur lors de la suppression : ' + (err.response?.data?.detail || err.message));
  }
}
</script>
