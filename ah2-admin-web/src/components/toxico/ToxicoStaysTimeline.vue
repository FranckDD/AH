<template>
  <div class="grid gap-4">
    <p v-if="!groups.length" class="py-4 text-center text-base italic text-ink-muted">{{ t('toxico.stays.empty') }}</p>

    <section v-for="g in groups" :key="g.legacy ? 'legacy' : g.stay.stay_number"
             :class="['overflow-hidden rounded-card border-2 bg-white', g.stay?.is_open ? 'border-action-600' : 'border-tone-neutral-border']">
      <!-- En-tete du sejour : empile sous md, en ligne a partir de md -->
      <header :class="['flex flex-col gap-1 px-4 py-3 md:flex-row md:items-center md:justify-between md:gap-3', g.stay?.is_open ? 'bg-action-50' : 'bg-tone-neutral-bg']">
        <template v-if="!g.legacy">
          <div class="flex flex-wrap items-center gap-2">
            <h4 class="text-base font-bold text-ink">{{ t('toxico.stays.stay_n', { n: g.stay.stay_number }) }}</h4>
            <span v-if="g.stay.is_open" class="rounded-full bg-action-600 px-2.5 py-0.5 text-sm font-medium text-white">{{ t('toxico.stays.current') }}</span>
            <StatusBadge v-else tone="neutral" :label="t(dischargeReasonLabelKey(g.stay.discharge_reason))" />
          </div>
          <p class="text-sm text-ink-muted md:text-right">
            {{ [t('toxico.stays.period', { from: formatDate(g.stay.admission_date), to: g.stay.discharge_date ? formatDate(g.stay.discharge_date) : t('toxico.stays.ongoing') }), g.stay.psychologist_name, g.stay.substance].filter(Boolean).join(', ') }}
          </p>
        </template>
        <h4 v-else class="text-base font-bold text-ink-muted">{{ t('toxico.stays.legacy') }}</h4>
      </header>

      <div v-if="!g.legacy && !g.stay.is_open && (g.stay.discharge_note || g.stay.discharged_by_name)"
           class="border-t border-tone-neutral-border px-4 py-2 text-sm text-ink-muted">
        <span v-if="g.stay.discharged_by_name">{{ t('toxico.stays.discharged_by', { name: g.stay.discharged_by_name }) }}</span>
        <span v-if="g.stay.discharge_note" class="block italic md:ml-2 md:inline">« {{ g.stay.discharge_note }} »</span>
      </div>

      <ul v-if="g.items.length" class="divide-y divide-tone-neutral-border border-t border-tone-neutral-border">
        <li v-for="(item, i) in g.items" :key="i" class="flex flex-col gap-1 px-4 py-3 md:flex-row md:items-start md:gap-4">
          <time class="shrink-0 text-sm text-ink-muted md:w-28">{{ formatDate(item.date) }}</time>
          <div class="min-w-0 flex-1">
            <template v-if="item.kind === 'phase'">
              <p class="flex flex-wrap items-center gap-2 text-base font-semibold text-ink">
                {{ t(`toxico.phases.${item.phase}`) }}
                <StatusBadge v-if="item.status" :tone="isFinishedStatus(item.status) ? 'success' : 'info'" :label="phaseStatusKey(item.status) ? t(phaseStatusKey(item.status)) : item.status" />
              </p>
              <p v-if="item.end_date" class="text-sm text-ink-muted">{{ t('toxico.stays.until', { date: formatDate(item.end_date) }) }}</p>
              <p v-if="item.comments" class="break-words text-base text-ink">{{ item.comments }}</p>
            </template>
            <template v-else>
              <p class="flex flex-wrap items-center gap-2 text-base font-semibold text-action-700">
                {{ t('toxicoScreens.eval_line', { evaluation: t('toxico.stays.evaluation'), decision: item.decision, before: item.phase_before, after: item.phase_after }) }}
                <StatusBadge v-if="item.is_relapse" tone="danger" :label="t('toxico.stays.relapse')" />
              </p>
              <p v-if="item.evaluator_name" class="text-sm text-ink-muted">{{ item.evaluator_name }}</p>
              <p class="break-words text-base text-ink">{{ item.observation }}</p>
              <p v-if="item.recommendation" class="break-words text-base text-ink"><span class="font-medium">{{ t('toxico.stays.recommendation') }} :</span> {{ item.recommendation }}</p>
            </template>
          </div>
        </li>
      </ul>
      <p v-else class="border-t border-tone-neutral-border px-4 py-3 text-sm italic text-ink-muted">{{ t('toxico.stays.no_items') }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { groupByStay, dischargeReasonLabelKey, sortNewestFirst, isFinishedStatus, phaseStatusKey } from '@/utils/toxicoStays';
import { formatDateDMY } from '@/utils/localDate';
import { StatusBadge } from '@/components/ui';

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

const formatDate = formatDateDMY;
</script>
