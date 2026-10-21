<template>
  <div class="space-y-4">
    <p v-if="!groups.length" class="text-center text-gray-500 py-4 italic">{{ t('toxico.stays.empty') }}</p>

    <section v-for="g in groups" :key="g.legacy ? 'legacy' : g.stay.stay_number"
             :class="['rounded-xl border bg-white shadow-xs overflow-hidden',
                      g.stay?.is_open ? 'border-indigo-300 ring-1 ring-indigo-200' : 'border-gray-200']">
      <!-- En-tete du sejour : empile sous md, en ligne a partir de md -->
      <header :class="['px-4 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-1 md:gap-3',
                       g.stay?.is_open ? 'bg-indigo-50' : 'bg-gray-50']">
        <template v-if="!g.legacy">
          <div class="flex flex-wrap items-center gap-2">
            <h5 class="text-sm font-bold text-gray-900">{{ t('toxico.stays.stay_n', { n: g.stay.stay_number }) }}</h5>
            <span v-if="g.stay.is_open" class="bg-indigo-600 text-white text-xs px-2 py-0.5 rounded-full">{{ t('toxico.stays.current') }}</span>
            <span v-else class="bg-gray-200 text-gray-700 text-xs px-2 py-0.5 rounded-full">{{ t(dischargeReasonLabelKey(g.stay.discharge_reason)) }}</span>
          </div>
          <p class="text-xs text-gray-600 md:text-right">
            {{ t('toxico.stays.period', { from: formatDate(g.stay.admission_date), to: g.stay.discharge_date ? formatDate(g.stay.discharge_date) : t('toxico.stays.ongoing') }) }}
            <span v-if="g.stay.psychologist_name"> · {{ g.stay.psychologist_name }}</span>
            <span v-if="g.stay.substance"> · {{ g.stay.substance }}</span>
          </p>
        </template>
        <h5 v-else class="text-sm font-bold text-gray-700">{{ t('toxico.stays.legacy') }}</h5>
      </header>

      <div v-if="!g.legacy && !g.stay.is_open && (g.stay.discharge_note || g.stay.discharged_by_name)"
           class="px-4 py-2 text-xs text-gray-600 border-t border-gray-100">
        <span v-if="g.stay.discharged_by_name">{{ t('toxico.stays.discharged_by', { name: g.stay.discharged_by_name }) }}</span>
        <span v-if="g.stay.discharge_note" class="block md:inline md:ml-2 italic">« {{ g.stay.discharge_note }} »</span>
      </div>

      <ul v-if="g.items.length" class="divide-y divide-gray-100 border-t border-gray-100">
        <li v-for="(item, i) in g.items" :key="i" class="px-4 py-3 flex flex-col md:flex-row md:items-start gap-1 md:gap-4">
          <time class="text-xs text-gray-400 md:w-28 shrink-0">{{ formatDate(item.date) }}</time>
          <div class="min-w-0 flex-1">
            <template v-if="item.kind === 'phase'">
              <p class="text-sm font-semibold text-gray-900">
                {{ t(`toxico.phases.${item.phase}`) }}
                <span v-if="item.status" :class="['ml-1 text-xs px-2 py-0.5 rounded-full font-normal', isFinishedStatus(item.status) ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800']">{{ item.status }}</span>
              </p>
              <p v-if="item.end_date" class="text-xs text-gray-500">{{ t('toxico.stays.until', { date: formatDate(item.end_date) }) }}</p>
              <p v-if="item.comments" class="text-sm text-gray-600 break-words">{{ item.comments }}</p>
            </template>
            <template v-else>
              <p class="text-sm font-semibold text-purple-800">
                {{ t('toxico.stays.evaluation') }} · {{ item.decision }} ({{ item.phase_before }} → {{ item.phase_after }})
                <span v-if="item.is_relapse" class="ml-1 bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded-full font-normal">{{ t('toxico.stays.relapse') }}</span>
              </p>
              <p v-if="item.evaluator_name" class="text-xs text-gray-500">{{ item.evaluator_name }}</p>
              <p class="text-sm text-gray-600 break-words">{{ item.observation }}</p>
              <p v-if="item.recommendation" class="text-sm text-gray-600 break-words"><span class="font-medium">{{ t('toxico.stays.recommendation') }} :</span> {{ item.recommendation }}</p>
            </template>
          </div>
        </li>
      </ul>
      <p v-else class="px-4 py-3 text-xs text-gray-400 italic border-t border-gray-100">{{ t('toxico.stays.no_items') }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { groupByStay, dischargeReasonLabelKey, sortNewestFirst, isFinishedStatus } from '@/utils/toxicoStays';

const props = defineProps({
  stays: { type: Array, default: () => [] },
  phaseHistory: { type: Array, default: () => [] },
  evaluations: { type: Array, default: () => [] },
});
const { t } = useI18n();

const groups = computed(() => {
  const items = [
    ...props.phaseHistory.map((p) => ({ ...p, kind: 'phase', date: p.start_date })),
    ...props.evaluations.map((e) => ({ ...e, kind: 'eval', date: e.created_at })),
  ];
  // Sejours en ordre chronologique, elements du plus recent au plus ancien (phase en cours en haut).
  return groupByStay(sortNewestFirst(items), props.stays);
});

const formatDate = (d) => {
  if (!d) return '';
  const x = new Date(d);
  return isNaN(x.getTime()) ? d : x.toLocaleDateString();
};
</script>
