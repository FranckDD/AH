<!-- ah2-admin-web/src/components/nurseshift/NurseShiftCalendar.vue -->
<template>
  <div class="overflow-hidden rounded-card border border-tone-neutral-border bg-white shadow-card">

    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-tone-neutral-border p-3 md:p-4">
      <div class="flex items-center gap-1 md:gap-2">
        <button
          type="button"
          @click="goToPreviousMonth"
          class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-ink-muted hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
          :aria-label="view === 'week' ? t('nurseShift.prev_week') : t('nurseShift.prev_month')"
        >
          <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
        </button>
        <h2 class="min-w-40 text-center text-lg font-semibold capitalize text-ink" aria-live="polite">{{ periodLabel }}</h2>
        <button
          type="button"
          @click="goToNextMonth"
          class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-ink-muted hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
          :aria-label="view === 'week' ? t('nurseShift.next_week') : t('nurseShift.next_month')"
        >
          <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <!-- Semaine (noms complets, lecture facile) ou Mois (vue d'ensemble) -->
        <div class="flex rounded-control bg-tone-neutral-bg p-1" role="group">
          <button
            type="button"
            @click="view = 'week'"
            :aria-pressed="view === 'week'"
            class="min-h-11 rounded-control px-4 text-base font-medium transition focus-visible:outline-2 focus-visible:outline-brand-600 md:min-h-9"
            :class="view === 'week' ? 'bg-white text-ink shadow-card' : 'text-ink-muted hover:text-ink'"
          >{{ t('nurseShift.view_week') }}</button>
          <button
            type="button"
            @click="view = 'month'"
            :aria-pressed="view === 'month'"
            class="min-h-11 rounded-control px-4 text-base font-medium transition focus-visible:outline-2 focus-visible:outline-brand-600 md:min-h-9"
            :class="view === 'month' ? 'bg-white text-ink shadow-card' : 'text-ink-muted hover:text-ink'"
          >{{ t('nurseShift.view_month') }}</button>
        </div>
        <AppButton variant="secondary" @click="goToToday">
          {{ t('nurseShift.today') }}
        </AppButton>
      </div>
    </div>

    <!-- VUE SEMAINE : un jour par ligne, une colonne par rotation, noms complets un par ligne -->
    <div v-if="view === 'week'" data-view="week">
      <div class="hidden border-b border-tone-neutral-border bg-tone-neutral-bg text-base font-semibold text-tone-neutral-text lg:grid lg:grid-cols-[9rem_repeat(3,minmax(0,1fr))]">
        <div class="px-4 py-3">{{ t('nurseShift.day_column') }}</div>
        <div v-for="st in SHIFT_TYPES" :key="st" class="px-4 py-3">{{ t(`nurseShift.shift.${st}`) }}</div>
      </div>

      <button
        v-for="day in weekGrid"
        :key="day.dateStr"
        type="button"
        @click="$emit('day-click', day.dateStr)"
        :aria-label="dayAriaLabel(day)"
        class="grid w-full gap-3 border-b border-tone-neutral-border px-4 py-3 text-left transition last:border-b-0 hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600 lg:grid-cols-[9rem_repeat(3,minmax(0,1fr))]"
        :class="day.isToday ? 'bg-brand-50 ring-2 ring-inset ring-brand-600' : ''"
      >
        <div class="flex flex-wrap items-center gap-2 lg:block">
          <p class="text-base font-semibold capitalize text-ink">{{ day.label }}</p>
          <StatusBadge v-if="day.isToday" tone="info" :label="t('nurseShift.today')" />
        </div>

        <div v-for="st in SHIFT_TYPES" :key="st">
          <p class="mb-1 text-base font-semibold text-ink-muted lg:hidden">{{ t(`nurseShift.shift.${st}`) }}</p>
          <ul v-if="day.nursesByShift[st].length" class="space-y-1">
            <li v-for="name in day.nursesByShift[st]" :key="name" class="text-base font-medium text-ink">{{ name }}</li>
          </ul>
          <p v-else class="text-base text-ink-muted">
            <span aria-hidden="true">{{ unavailable ? '?' : '-' }}</span>
            <span class="sr-only">{{ unavailable ? t('nurseShift.state_unknown') : t('nurseShift.no_assignment') }}</span>
          </p>
        </div>
      </button>
    </div>

    <!-- VUE MOIS : vue d'ensemble (compteur sur telephone, une ligne par rotation des la tablette) -->
    <div v-else data-view="month">
      <div class="grid grid-cols-7 border-b border-tone-neutral-border bg-tone-neutral-bg">
        <div v-for="label in weekdayLabels" :key="label" class="px-1 py-2 text-center text-sm font-semibold text-tone-neutral-text">
          {{ label }}
        </div>
      </div>

      <div class="grid grid-cols-7">
        <button
          v-for="day in daysGrid"
          :key="day.dateStr"
          type="button"
          @click="$emit('day-click', day.dateStr)"
          :aria-label="dayAriaLabel(day)"
          class="min-h-14 border-b border-r border-tone-neutral-border p-1 text-left align-top transition hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600 md:min-h-28 md:p-2"
          :class="{
            'bg-tone-neutral-bg text-ink-muted': !day.inCurrentMonth,
            'ring-2 ring-inset ring-brand-600': day.isToday,
          }"
        >
          <div class="mb-1 text-sm font-semibold" :class="day.isToday ? 'text-brand-700' : ''">
            {{ day.dayOfMonth }}
          </div>

          <!-- Telephone : nombre d'infirmiers du jour (les noms ne tiennent pas, texte jamais sous 13 px) -->
          <span
            v-if="day.total > 0"
            class="inline-flex min-w-6 items-center justify-center rounded-full border px-1.5 text-sm font-semibold md:hidden"
            :class="toneClasses('info')"
          >{{ day.total }}</span>

          <!-- Tablette et PC : une ligne par rotation -->
          <div class="hidden space-y-0.5 md:block">
            <div v-for="st in SHIFT_TYPES" :key="st" class="break-words text-sm leading-tight">
              <span class="text-ink-muted">{{ t(`nurseShift.shift.${st}`) }}:</span>
              <span v-if="day.nursesByShift[st].length" class="text-ink"> {{ day.nursesByShift[st].join(', ') }}</span>
              <span v-else class="text-ink-muted"> {{ unavailable ? '?' : '-' }}</span>
            </div>
          </div>
        </button>
      </div>
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
import { AppButton, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { periodRange, shiftAnchor, weekDays } from '@/utils/nurseShiftRange';

const { t, locale } = useI18n();

const props = defineProps({
  shifts: {
    type: Array,
    default: () => [],
  },
  // Chargement impossible (hors ligne, erreur) : jamais "aucun infirmier", un etat inconnu.
  unavailable: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['day-click', 'month-change']);

watch(locale, (lang) => dayjs.locale(lang === 'en' ? 'en' : 'fr'), { immediate: true });

// 'week' (par defaut : noms complets) ou 'month'. anchor = un jour de la periode affichee.
const view = ref('week');
const anchor = ref(dayjs());

const currentMonth = computed(() => anchor.value.startOf('month'));
const gridRange = computed(() => periodRange(view.value, anchor.value));

const periodLabel = computed(() => {
  if (view.value === 'month') return currentMonth.value.format('MMMM YYYY');
  const start = dayjs(gridRange.value.start);
  const end = dayjs(gridRange.value.end);
  return `${start.format('D MMM')} - ${end.format('D MMM YYYY')}`;
});

const weekdayLabels = computed(() =>
  locale.value === 'en'
    ? ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    : ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
);

// Le parent (re)charge les rotations de la plage affichee : evenement conserve sous son nom d'origine.
function emitMonthRange() {
  emit('month-change', { ...gridRange.value });
}

function goToPreviousMonth() {
  anchor.value = shiftAnchor(view.value, anchor.value, -1);
  emitMonthRange();
}
function goToNextMonth() {
  anchor.value = shiftAnchor(view.value, anchor.value, 1);
  emitMonthRange();
}
function goToToday() {
  anchor.value = dayjs();
  emitMonthRange();
}
// Changer de vue change la plage a charger (semaine ou grille du mois).
watch(view, () => emitMonthRange());

const shiftsByDate = computed(() => {
  const map = new Map();
  for (const s of props.shifts) {
    if (!map.has(s.shift_date)) map.set(s.shift_date, []);
    map.get(s.shift_date).push(s);
  }
  return map;
});

function buildDay(dateStr, monthStart) {
  const dayShifts = shiftsByDate.value.get(dateStr) || [];
  const nursesByShift = {};
  for (const st of SHIFT_TYPES) {
    nursesByShift[st] = dayShifts.filter((s) => s.shift_type === st).map((s) => s.nurse_name);
  }
  const date = dayjs(dateStr);
  return {
    dateStr,
    dayOfMonth: date.date(),
    label: date.format('ddd D MMM'),
    inCurrentMonth: monthStart ? date.isSame(monthStart, 'month') : true,
    isToday: dateStr === dayjs().format('YYYY-MM-DD'),
    nursesByShift,
    total: dayShifts.length,
  };
}

const weekGrid = computed(() => weekDays(gridRange.value.start).map((d) => buildDay(d)));

const daysGrid = computed(() => {
  const monthStart = currentMonth.value;
  const { start, end } = periodRange('month', anchor.value);
  const days = [];
  let cursor = dayjs(start);
  const gridEnd = dayjs(end);
  while (!cursor.isAfter(gridEnd, 'day')) {
    days.push(buildDay(cursor.format('YYYY-MM-DD'), monthStart));
    cursor = cursor.add(1, 'day');
  }
  return days;
});

// Libelle lu par les lecteurs d'ecran : la date et le nombre d'infirmiers planifies.
function dayAriaLabel(day) {
  const date = dayjs(day.dateStr).format('DD/MM/YYYY');
  return day.total > 0
    ? `${date}, ${t('nurseShift.nurses_count', { n: day.total }, day.total)}`
    : date;
}

emitMonthRange();
</script>
