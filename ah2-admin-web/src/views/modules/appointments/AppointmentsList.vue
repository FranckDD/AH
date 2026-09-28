<template>
  <div class="space-y-6 w-full">

    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('appointments.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('appointments.subtitle') }}</p>
      </div>

      <button
        @click="openCreateModal"
        class="flex items-center px-6 py-2.5 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 shadow-md shadow-emerald-200 transition font-semibold"
      >
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('appointments.new_appointment') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">

      <div class="flex-1 min-w-[220px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('appointments.search_label') }}</label>
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
          </div>
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('appointments.search_placeholder')"
            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
          >
        </div>
      </div>

      <div class="w-full md:w-48">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('appointments.status_label') }}</label>
        <select v-model="statusFilter" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm rounded-lg">
          <option value="ALL">{{ t('appointments.status_all') }}</option>
          <option v-for="s in appointmentStatuses" :key="s" :value="s">{{ t(`appointments.status_${s}`) }}</option>
        </select>
      </div>

      <div class="w-full md:w-44">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('appointments.date_label') }}</label>
        <select v-model="dateMode" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm rounded-lg">
          <option value="ALL">{{ t('appointments.date_all') }}</option>
          <option value="TODAY">{{ t('appointments.date_today') }}</option>
          <option value="CUSTOM">{{ t('appointments.date_custom') }}</option>
        </select>
      </div>

      <div v-if="dateMode === 'CUSTOM'" class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('appointments.date_custom') }}</label>
        <input v-model="customDate" type="date" class="block w-full pl-3 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm" />
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

      <div class="p-4 border-b border-gray-100 flex items-center justify-between">
        <div class="text-sm text-gray-500">
          {{ appointmentStore.appointments.length }} {{ t('appointments.results_count') }}
        </div>
      </div>

      <div v-if="appointmentStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></span>
        <p class="mt-2 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.phone') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.doctor') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.time') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.reason') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.status') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('appointments.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="appt in appointmentStore.appointments" :key="appt.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900">{{ patientName(appt) }}</div>
                <div class="text-xs text-gray-500">{{ appt.code_patient }}</div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ appt.contact_phone || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ appt.doctor_full_name || appt.doctor_username || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ appt.appointment_date }}</td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ (appt.appointment_time || '').substring(0, 5) }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ appt.reason || '—' }}</td>
              <td class="px-6 py-4">
                <StatusBadge :status="appt.status" />
              </td>
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <!--
                    Bouton "Accepter" volontairement omis (contrairement au
                    client desktop) - voir docs/superpowers/SUIVI-AVANCEMENT.md,
                    registre C4. Non touché par ce chantier.
                  -->
                  <button
                    v-if="appt.status === 'pending'"
                    @click="appointmentStore.completeAppointment(appt.server_id)"
                    :disabled="!appt.server_id"
                    :title="!appt.server_id ? t('appointments.pending_sync') : ''"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('appointments.actions.complete') }}
                  </button>
                  <button
                    v-if="appt.status === 'pending'"
                    @click="appointmentStore.cancelAppointment(appt.server_id)"
                    :disabled="!appt.server_id"
                    :title="!appt.server_id ? t('appointments.pending_sync') : ''"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('appointments.actions.cancel') }}
                  </button>
                  <button
                    v-if="appt.status === 'pending'"
                    @click="voirDossier(appt)"
                    :disabled="!appt.patient_id"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('appointments.actions.view_dossier') }}
                  </button>
                  <button
                    v-if="appt.status === 'pending'"
                    @click="demarrerConsultation(appt)"
                    :disabled="!appt.patient_id || !appt.server_id"
                    :title="!appt.server_id ? t('appointments.pending_sync') : ''"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('appointments.actions.start_consultation') }}
                  </button>
                  <button
                    @click="openEditModal(appt)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
                  >
                    {{ t('appointments.actions.edit') }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="appointmentStore.appointments.length === 0">
              <td colspan="8" class="px-6 py-8 text-center text-gray-500 italic">
                {{ t('appointments.empty') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>

    <AppointmentModal
      v-if="showModal"
      :appointment="editingAppointment"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAppointmentStore, APPOINTMENT_STATUSES } from '@/stores/appointmentStore';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import StatusBadge from '@/components/appointments/StatusBadge.vue';
import AppointmentModal from '@/components/appointments/AppointmentModal.vue';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const appointmentStore = useAppointmentStore();
const appointmentStatuses = APPOINTMENT_STATUSES;
const router = useRouter();

function voirDossier(appt) {
  router.push(`/medical/patients/${appt.patient_id}`);
}

function demarrerConsultation(appt) {
  router.push(`/medical/patients/${appt.patient_id}?appointmentId=${appt.server_id}`);
}

onMounted(() => {
  appointmentStore.startWatchingAppointments();
  appointmentStore.fetchSpecialties();
});

const searchQuery = computed({
  get: () => appointmentStore.filters.searchQuery,
  set: (val) => appointmentStore.setFilters({ searchQuery: val }),
});

const statusFilter = computed({
  get: () => appointmentStore.filters.status,
  set: (val) => appointmentStore.setFilters({ status: val }),
});

const dateMode = computed({
  get: () => appointmentStore.filters.dateMode,
  set: (val) => appointmentStore.setFilters({ dateMode: val }),
});

const customDate = computed({
  get: () => appointmentStore.filters.customDate,
  set: (val) => appointmentStore.setFilters({ customDate: val }),
});

function patientName(appt) {
  return [appt.first_name, appt.last_name].filter(Boolean).join(' ') || '—';
}

const showModal = ref(false);
const editingAppointment = ref(null);

function openCreateModal() {
  editingAppointment.value = null;
  showModal.value = true;
}

function openEditModal(appt) {
  editingAppointment.value = appt;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingAppointment.value = null;
}

async function handleSave(data) {
  try {
    if (editingAppointment.value) {
      await appointmentStore.updateAppointment(editingAppointment.value.id, data);
    } else {
      await appointmentStore.createAppointment(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement rendez-vous:', err);
    alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
  }
}
</script>
