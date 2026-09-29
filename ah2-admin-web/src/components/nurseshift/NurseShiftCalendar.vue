<!-- ah2-admin-web/src/components/nurseshift/NurseShiftCalendar.vue -->
<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

    <div class="p-4 border-b border-gray-100 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <button @click="goToPreviousMonth" class="p-2 rounded-lg hover:bg-gray-100 transition">
          <ChevronLeftIcon class="h-5 w-5 text-gray-500" />
        </button>
        <h2 class="text-lg font-bold text-gray-800 w-40 text-center capitalize">{{ monthLabel }}</h2>
        <button @click="goToNextMonth" class="p-2 rounded-lg hover:bg-gray-100 transition">
          <ChevronRightIcon class="h-5 w-5 text-gray-500" />
        </button>
      </div>
      <button @click="goToToday" class="px-4 py-1.5 text-sm font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition">
        {{ t('nurseShift.today') }}
      </button>
    </div>

    <div class="grid grid-cols-7 border-b border-gray-100 bg-gray-50">
      <div v-for="label in weekdayLabels" :key="label" class="px-2 py-2 text-center text-xs font-semibold text-gray-500 uppercase">
        {{ label }}
      </div>
    </div>

    <div class="grid grid-cols-7">
      <button
        v-for="day in daysGrid"
        :key="day.dateStr"
        type="button"
        @click="$emit('day-click', day.dateStr)"
        class="min-h-[7rem] border-b border-r border-gray-100 p-2 text-left align-top hover:bg-gray-50 transition focus:outline-none focus:bg-emerald-50/50"
        :class="{
          'bg-gray-50/60 text-gray-400': !day.inCurrentMonth,
          'ring-2 ring-inset ring-emerald-500': day.isToday,
        }"
      >
        <div class="text-xs font-semibold mb-1" :class="day.isToday ? 'text-emerald-700' : ''">
          {{ day.dayOfMonth }}
        </div>
        <div class="space-y-0.5">
          <div v-for="st in SHIFT_TYPES" :key="st" class="text-[10px] leading-tight truncate">
            <span class="text-gray-400">{{ t(`nurseShift.shift.${st}`) }}:</span>
            <span v-if="day.nursesByShift[st].length" class="text-gray-700"> {{ day.nursesByShift[st].join(', ') }}</span>
            <span v-else class="text-gray-300"> —</span>
          </div>
        </div>
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import 'dayjs/locale/fr';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';
import { SHIFT_TYPES } from '@/stores/nurseShiftStore';

const { t, locale } = useI18n();

const props = defineProps({
  shifts: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(['day-click', 'month-change']);

watch(locale, (lang) => dayjs.locale(lang === 'en' ? 'en' : 'fr'), { immediate: true });

const currentMonth = ref(dayjs().startOf('month'));

const monthLabel = computed(() => currentMonth.value.format('MMMM YYYY'));
const weekdayLabels = computed(() =>
  locale.value === 'en'
    ? ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    : ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
);

function emitMonthRange() {
  emit('month-change', {
    start: currentMonth.value.startOf('month').format('YYYY-MM-DD'),
    end: currentMonth.value.endOf('month').format('YYYY-MM-DD'),
  });
}

function goToPreviousMonth() {
  currentMonth.value = currentMonth.value.subtract(1, 'month');
  emitMonthRange();
}
function goToNextMonth() {
  currentMonth.value = currentMonth.value.add(1, 'month');
  emitMonthRange();
}
function goToToday() {
  currentMonth.value = dayjs().startOf('month');
  emitMonthRange();
}

const shiftsByDate = computed(() => {
  const map = new Map();
  for (const s of props.shifts) {
    if (!map.has(s.shift_date)) map.set(s.shift_date, []);
    map.get(s.shift_date).push(s);
  }
  return map;
});

const daysGrid = computed(() => {
  const monthStart = currentMonth.value;
  const monthEnd = monthStart.endOf('month');
  const startOffset = (monthStart.day() + 6) % 7;
  const endOffset = (6 - ((monthEnd.day() + 6) % 7));
  const gridStart = monthStart.subtract(startOffset, 'day');
  const gridEnd = monthEnd.add(endOffset, 'day');

  const today = dayjs().format('YYYY-MM-DD');
  const days = [];
  let cursor = gridStart;
  while (!cursor.isAfter(gridEnd, 'day')) {
    const dateStr = cursor.format('YYYY-MM-DD');
    const dayShifts = shiftsByDate.value.get(dateStr) || [];
    const nursesByShift = {};
    for (const st of SHIFT_TYPES) {
      nursesByShift[st] = dayShifts.filter((s) => s.shift_type === st).map((s) => s.nurse_name);
    }
    days.push({
      dateStr,
      dayOfMonth: cursor.date(),
      inCurrentMonth: cursor.isSame(monthStart, 'month'),
      isToday: dateStr === today,
      nursesByShift,
    });
    cursor = cursor.add(1, 'day');
  }
  return days;
});

emitMonthRange();
</script>
