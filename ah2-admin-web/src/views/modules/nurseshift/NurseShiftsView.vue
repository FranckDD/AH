<!-- ah2-admin-web/src/views/modules/nurseshift/NurseShiftsView.vue -->
<template>
  <div class="space-y-6 w-full">

    <div class="bg-white p-6 rounded-2xl shadow-xs border border-gray-100">
      <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('nurseShift.title') }}</h1>
      <p class="text-sm text-gray-500">{{ t('nurseShift.subtitle') }}</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      <div class="lg:col-span-2">
        <NurseShiftCalendar :shifts="nurseShiftStore.shifts" @day-click="handleDayClick" @month-change="handleMonthChange" />
      </div>
      <div v-if="selectedDate" class="space-y-2">
        <p v-if="actionError" class="text-sm text-red-600">{{ actionError }}</p>
        <NurseShiftDayPanel
          :date="selectedDate"
          :shifts="selectedDateShifts"
          :available-nurses="nurseShiftStore.activeNurses"
          :can-manage="canManage"
          @close="selectedDate = null"
          @add="handleAdd"
          @remove="handleRemove"
        />
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useNurseShiftStore } from '@/stores/nurseShiftStore';
import { useAuthStore } from '@/stores/auth';
import NurseShiftCalendar from '@/components/nurseshift/NurseShiftCalendar.vue';
import NurseShiftDayPanel from '@/components/nurseshift/NurseShiftDayPanel.vue';

const { t } = useI18n();
const nurseShiftStore = useNurseShiftStore();
const authStore = useAuthStore();

const selectedDate = ref(null);
const currentRange = ref({ start: null, end: null });
const actionError = ref(null);

// medecin toujours autorise ; infirmier seulement si is_head_nurse - le
// backend refuse (403) de toute facon si ce garde frontend etait
// contourne, voir controller/nurse_shift_controller.py::_ensure_can_manage_schedule.
const canManage = computed(() => {
  if (authStore.hasRole(['medecin'])) return true;
  return authStore.hasRole(['nurse']) && !!authStore.user?.is_head_nurse;
});

const selectedDateShifts = computed(() => {
  if (!selectedDate.value) return [];
  return nurseShiftStore.shifts.filter((s) => s.shift_date === selectedDate.value);
});

function handleMonthChange({ start, end }) {
  currentRange.value = { start, end };
  nurseShiftStore.fetchShifts(start, end);
}

function handleDayClick(dateStr) {
  selectedDate.value = dateStr;
  actionError.value = null;
}

async function handleAdd({ shiftType, nurseId }) {
  if (!nurseId) return;
  actionError.value = null;
  try {
    await nurseShiftStore.createShift(selectedDate.value, shiftType, nurseId, currentRange.value.start, currentRange.value.end);
  } catch (err) {
    actionError.value = err.response?.data?.detail || 'Une erreur est survenue.';
  }
}

async function handleRemove(shiftId) {
  actionError.value = null;
  try {
    await nurseShiftStore.deleteShift(shiftId, currentRange.value.start, currentRange.value.end);
  } catch (err) {
    actionError.value = err.response?.data?.detail || 'Une erreur est survenue.';
  }
}

onMounted(() => {
  nurseShiftStore.fetchActiveNurses();
});
</script>
