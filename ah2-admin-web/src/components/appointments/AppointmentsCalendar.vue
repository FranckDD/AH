<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

    <div class="p-4 border-b border-gray-100 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <button
          @click="goToPreviousMonth"
          class="p-2 rounded-lg hover:bg-gray-100 transition"
          :aria-label="t('appointments.calendar.today')"
        >
          <ChevronLeftIcon class="h-5 w-5 text-gray-500" />
        </button>
        <h2 class="text-lg font-bold text-gray-800 w-40 text-center capitalize">
          {{ monthLabel }}
        </h2>
        <button @click="goToNextMonth" class="p-2 rounded-lg hover:bg-gray-100 transition">
          <ChevronRightIcon class="h-5 w-5 text-gray-500" />
        </button>
      </div>
      <button
        @click="goToToday"
        class="px-4 py-1.5 text-sm font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
      >
        {{ t('appointments.calendar.today') }}
      </button>
    </div>

    <div class="grid grid-cols-7 border-b border-gray-100 bg-gray-50">
      <div
        v-for="label in weekdayLabels"
        :key="label"
        class="px-2 py-2 text-center text-xs font-semibold text-gray-500 uppercase"
      >
        {{ label }}
      </div>
    </div>

    <div class="grid grid-cols-7">
      <button
        v-for="day in daysGrid"
        :key="day.dateStr"
        type="button"
        @click="$emit('day-click', day.dateStr)"
        class="min-h-[6.5rem] border-b border-r border-gray-100 p-2 text-left align-top hover:bg-gray-50 transition focus:outline-none focus:bg-emerald-50/50"
        :class="{
          'bg-gray-50/60 text-gray-400': !day.inCurrentMonth,
          'ring-2 ring-inset ring-emerald-500': day.isToday,
        }"
      >
        <div class="text-xs font-semibold mb-1" :class="day.isToday ? 'text-emerald-700' : ''">
          {{ day.dayOfMonth }}
        </div>
        <div class="space-y-1">
          <div
            v-for="appt in day.visibleAppointments"
            :key="appt.id"
            class="text-[11px] leading-tight px-1.5 py-0.5 rounded truncate"
            :class="chipClass(appt.status)"
            :title="`${(appt.appointment_time || '').substring(0, 5)} — ${patientLabel(appt)}`"
          >
            {{ (appt.appointment_time || '').substring(0, 5) }} {{ patientLabel(appt) }}
          </div>
          <div v-if="day.overflowCount > 0" class="text-[11px] text-gray-500 px-1.5">
            +{{ day.overflowCount }} {{ t('appointments.calendar.more') }}
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

const { t, locale } = useI18n();

// dayjs n'a pas de locale globale synchronisee avec vue-i18n ailleurs dans
// ce projet - sans ceci, monthLabel (format('MMMM YYYY')) restait toujours
// en anglais meme quand l'utilisateur choisit le francais (langue par
// defaut de cette application).
watch(
  locale,
  (lang) => dayjs.locale(lang === 'en' ? 'en' : 'fr'),
  { immediate: true }
);

const props = defineProps({
  appointments: {
    type: Array,
    default: () => [],
  },
});

defineEmits(['day-click']);

// Nombre max d'etiquettes de RDV affichees par jour avant de replier en
// "+N de plus" - au-dela, une cellule de calendrier deviendrait illisible
// (contrairement a la liste, pas de defilement possible dans une cellule).
const MAX_VISIBLE_PER_DAY = 3;

const currentMonth = ref(dayjs().startOf('month'));

const monthLabel = computed(() => currentMonth.value.format('MMMM YYYY'));

const weekdayLabels = computed(() => t('appointments.calendar.weekdays_short'));

function goToPreviousMonth() {
  currentMonth.value = currentMonth.value.subtract(1, 'month');
}
function goToNextMonth() {
  currentMonth.value = currentMonth.value.add(1, 'month');
}
function goToToday() {
  currentMonth.value = dayjs().startOf('month');
}

// Regroupe les RDV par date (YYYY-MM-DD) une seule fois par changement de
// jeu de donnees, plutot que de refiltrer le tableau complet pour chacune
// des ~35-42 cellules de la grille.
const appointmentsByDate = computed(() => {
  const map = new Map();
  for (const appt of props.appointments) {
    const dateKey = (appt.appointment_date || '').substring(0, 10);
    if (!dateKey) continue;
    if (!map.has(dateKey)) map.set(dateKey, []);
    map.get(dateKey).push(appt);
  }
  // Tri par heure a l'interieur de chaque jour, une fois pour toutes.
  for (const list of map.values()) {
    list.sort((a, b) => (a.appointment_time || '').localeCompare(b.appointment_time || ''));
  }
  return map;
});

// Grille du mois affiche, semaines commencant le lundi (convention locale),
// completee avec les jours du mois precedent/suivant necessaires pour
// remplir des semaines completes de 7 jours.
const daysGrid = computed(() => {
  const monthStart = currentMonth.value;
  const monthEnd = monthStart.endOf('month');

  // dayjs().day() : 0=dimanche..6=samedi. Conversion en index lundi=0.
  const startOffset = (monthStart.day() + 6) % 7;
  const endOffset = (6 - ((monthEnd.day() + 6) % 7));

  const gridStart = monthStart.subtract(startOffset, 'day');
  const gridEnd = monthEnd.add(endOffset, 'day');

  const today = dayjs().format('YYYY-MM-DD');
  const days = [];
  let cursor = gridStart;
  while (!cursor.isAfter(gridEnd, 'day')) {
    const dateStr = cursor.format('YYYY-MM-DD');
    const dayAppointments = appointmentsByDate.value.get(dateStr) || [];
    days.push({
      dateStr,
      dayOfMonth: cursor.date(),
      inCurrentMonth: cursor.isSame(monthStart, 'month'),
      isToday: dateStr === today,
      visibleAppointments: dayAppointments.slice(0, MAX_VISIBLE_PER_DAY),
      overflowCount: Math.max(0, dayAppointments.length - MAX_VISIBLE_PER_DAY),
    });
    cursor = cursor.add(1, 'day');
  }
  return days;
});

function patientLabel(appt) {
  return [appt.first_name, appt.last_name].filter(Boolean).join(' ') || '—';
}

function chipClass(status) {
  if (status === 'completed') return 'bg-emerald-100 text-emerald-800';
  if (status === 'cancelled') return 'bg-red-100 text-red-800 line-through';
  return 'bg-yellow-100 text-yellow-800';
}
</script>
