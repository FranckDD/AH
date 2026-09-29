<!-- ah2-admin-web/src/components/nurseshift/NurseShiftDayPanel.vue -->
<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden h-fit">
    <div class="p-4 border-b border-gray-100 flex items-center justify-between">
      <h3 class="text-sm font-bold text-gray-700">{{ t('nurseShift.day_panel_title') }} {{ formattedDate }}</h3>
      <button @click="$emit('close')" class="p-1 rounded-lg hover:bg-gray-100 transition">
        <XMarkIcon class="h-5 w-5 text-gray-400" />
      </button>
    </div>

    <p v-if="!canManage" class="px-4 pt-3 text-xs text-gray-400 italic">{{ t('nurseShift.read_only_note') }}</p>

    <div class="p-4 space-y-4">
      <div v-for="st in SHIFT_TYPES" :key="st">
        <h4 class="text-xs font-bold text-gray-500 uppercase mb-2">{{ t(`nurseShift.shift.${st}`) }}</h4>

        <div v-if="shiftsFor(st).length === 0" class="text-xs text-gray-400 italic mb-2">
          {{ t('nurseShift.no_assignment') }}
        </div>
        <div v-for="s in shiftsFor(st)" :key="s.id" class="flex items-center justify-between text-sm py-1">
          <span>{{ s.nurse_name }}</span>
          <button v-if="canManage" @click="$emit('remove', s.id)" class="text-xs text-red-600 hover:underline">
            {{ t('nurseShift.remove') }}
          </button>
        </div>

        <div v-if="canManage" class="flex gap-2 mt-1">
          <select v-model="selectedNurseByShift[st]" class="flex-1 px-2 py-1 border border-gray-300 rounded-lg text-xs">
            <option value="" disabled>{{ t('nurseShift.select_nurse') }}</option>
            <option v-for="n in unassignedNursesFor(st)" :key="n.user_id" :value="n.user_id">
              {{ n.full_name }}{{ n.is_head_nurse ? ` (${t('nurseShift.head_nurse_badge')})` : '' }}
            </option>
          </select>
          <button
            @click="handleAdd(st)"
            :disabled="!selectedNurseByShift[st]"
            class="px-3 py-1 text-xs font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ t('nurseShift.add_nurse') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import { SHIFT_TYPES } from '@/stores/nurseShiftStore';

const { t } = useI18n();

const props = defineProps({
  date: {
    type: String,
    required: true,
  },
  shifts: {
    type: Array,
    default: () => [],
  },
  availableNurses: {
    type: Array,
    default: () => [],
  },
  canManage: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['close', 'add', 'remove']);

const selectedNurseByShift = reactive({ MATIN: '', APRES_MIDI: '', NUIT: '' });

const formattedDate = computed(() => dayjs(props.date).format('DD/MM/YYYY'));

function shiftsFor(shiftType) {
  return props.shifts.filter((s) => s.shift_type === shiftType);
}

function unassignedNursesFor(shiftType) {
  const assignedIds = new Set(shiftsFor(shiftType).map((s) => s.nurse_id));
  return props.availableNurses.filter((n) => !assignedIds.has(n.user_id));
}

function handleAdd(shiftType) {
  const nurseId = selectedNurseByShift[shiftType];
  emit('add', { shiftType, nurseId });
  // Reset optimiste : le parent recharge props.shifts apres l'ajout, la
  // liste sera re-filtree au prochain rendu (voir unassignedNursesFor).
  selectedNurseByShift[shiftType] = '';
}
</script>
