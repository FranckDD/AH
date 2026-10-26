<template>
  <div class="overflow-hidden rounded-card border border-tone-neutral-border bg-white shadow-card">

    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-tone-neutral-border p-3 md:p-4">
      <div class="flex items-center gap-1 md:gap-2">
        <button
          type="button"
          @click="goToPreviousMonth"
          class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-ink-muted hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
          :aria-label="t('appointments.calendar.prev_month')"
        >
          <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
        </button>
        <h2 class="w-40 text-center text-lg font-semibold capitalize text-ink" aria-live="polite">
          {{ monthLabel }}
        </h2>
        <button
          type="button"
          @click="goToNextMonth"
          class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-ink-muted hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
          :aria-label="t('appointments.calendar.next_month')"
        >
          <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
      <AppButton variant="secondary" @click="goToToday">
        {{ t('appointments.calendar.today') }}
      </AppButton>
    </div>

    <div class="grid grid-cols-7 border-b border-tone-neutral-border bg-tone-neutral-bg">
      <div
        v-for="label in weekdayLabels"
        :key="label"
        class="px-1 py-2 text-center text-sm font-semibold text-tone-neutral-text"
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
        :aria-label="dayAriaLabel(day)"
        class="min-h-14 border-b border-r border-tone-neutral-border p-1 text-left align-top transition hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600 md:min-h-26 md:p-2"
        :class="{
          'bg-tone-neutral-bg text-ink-muted': !day.inCurrentMonth,
          'ring-2 ring-inset ring-brand-600': day.isToday,
        }"
      >
        <div class="mb-1 text-sm font-semibold" :class="day.isToday ? 'text-brand-700' : ''">
          {{ day.dayOfMonth }}
        </div>

        <!-- Telephone : un compteur (les etiquettes ne tiennent pas, texte jamais sous 13 px) -->
        <span
          v-if="day.total > 0"
          class="inline-flex min-w-6 items-center justify-center rounded-full border px-1.5 text-sm font-semibold md:hidden"
          :class="toneClasses('info')"
        >{{ day.total }}</span>

        <!-- Tablette et PC : etiquettes par rendez-vous -->
        <div class="hidden space-y-1 md:block">
          <div
            v-for="appt in day.visibleAppointments"
            :key="appt.id"
            class="truncate rounded-control border px-1.5 py-0.5 text-sm leading-tight"
            :class="[toneClasses(chipTone(appt.status)), appt.status === 'cancelled' ? 'line-through' : '']"
            :title="`${(appt.appointment_time || '').substring(0, 5)} ${patientLabel(appt)}`"
          >
            {{ (appt.appointment_time || '').substring(0, 5) }} {{ patientLabel(appt) }}
          </div>
          <div v-if="day.overflowCount > 0" class="px-1.5 text-sm text-ink-muted">
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
import { AppButton } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t, tm, rt, locale } = useI18n();

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

// Tableau de libelles : tm() + rt(), pas t() (qui renverrait la cle brute).
const weekdayLabels = computed(() => tm('appointments.calendar.weekdays_short').map((m) => rt(m)));

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
      total: dayAppointments.length,
      visibleAppointments: dayAppointments.slice(0, MAX_VISIBLE_PER_DAY),
      overflowCount: Math.max(0, dayAppointments.length - MAX_VISIBLE_PER_DAY),
    });
    cursor = cursor.add(1, 'day');
  }
  return days;
});

function patientLabel(appt) {
  return [appt.first_name, appt.last_name].filter(Boolean).join(' ') || '-';
}

// Vert = termine, rouge = annule, orange = en attente (couleur selon le sens).
function chipTone(status) {
  if (status === 'completed') return 'success';
  if (status === 'cancelled') return 'danger';
  return 'warning';
}

// Libelle lu par les lecteurs d'ecran : la date et le nombre de rendez-vous du jour.
function dayAriaLabel(day) {
  const date = dayjs(day.dateStr).format('DD/MM/YYYY');
  return day.total > 0
    ? `${date}, ${t('appointments.calendar.appointments_count', { n: day.total }, day.total)}`
    : date;
}
</script>
