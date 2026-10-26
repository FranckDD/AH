<!-- ah2-admin-web/src/views/modules/nurseshift/NurseShiftsView.vue -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('nurseShift.title')" :subtitle="t('nurseShift.subtitle')" />

    <p
      v-if="nurseShiftStore.error"
      role="alert"
      class="rounded-card border p-4 text-base font-medium"
      :class="toneClasses(nurseShiftStore.offline ? 'warning' : 'danger')"
    >{{ nurseShiftStore.offline ? t('nurseShift.offline_unavailable') : t('nurseShift.load_failed') }}</p>

    <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <NurseShiftCalendar :shifts="nurseShiftStore.shifts" :unavailable="!!nurseShiftStore.error" @day-click="handleDayClick" @month-change="handleMonthChange" />
      </div>
      <div v-if="selectedDate" class="space-y-2">
        <p v-if="actionError" role="alert" class="text-base font-medium text-tone-danger-text">{{ actionError }}</p>
        <NurseShiftDayPanel
          :date="selectedDate"
          :shifts="selectedDateShifts"
          :available-nurses="nurseShiftStore.activeNurses"
          :can-manage="canManage && !nurseShiftStore.error"
          :unavailable="!!nurseShiftStore.error"
          :previous-day-shifts="shiftsOn(-1)"
          :next-day-shifts="shiftsOn(1)"
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
import { PageHeader } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { shiftErrorMessage } from '@/utils/nurseShiftErrors';
import dayjs from 'dayjs';

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

// Creneaux de la veille (-1) ou du lendemain (+1) deja charges, pour la regle de repos apres la nuit
// (le serveur reste l'arbitre si la veille est hors de la plage affichee).
function shiftsOn(offset) {
  if (!selectedDate.value) return [];
  const day = dayjs(selectedDate.value).add(offset, 'day').format('YYYY-MM-DD');
  return nurseShiftStore.shifts.filter((s) => s.shift_date === day);
}

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
    actionError.value = shiftErrorMessage(err, t);
  }
}

async function handleRemove(shiftId) {
  actionError.value = null;
  try {
    await nurseShiftStore.deleteShift(shiftId, currentRange.value.start, currentRange.value.end);
  } catch (err) {
    actionError.value = shiftErrorMessage(err, t);
  }
}

onMounted(() => {
  nurseShiftStore.fetchActiveNurses();
});
</script>
