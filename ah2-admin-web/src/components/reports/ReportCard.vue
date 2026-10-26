<!-- Coque commune d'une carte de Rapports : titre, corps (chiffres), periode et source toujours ecrites.
     Une carte "etat actuel" le dit par un badge en mots au lieu de laisser croire qu'elle couvre la periode. -->
<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { StatusBadge } from '@/components/ui';
import { currentStateOf, formatLocalDate, formatInstant, cardSource } from '@/utils/reports';

const props = defineProps({
    cardId: { type: String, required: true },
    card: { type: Object, default: null },
});
const { t, te, locale } = useI18n();
const state = computed(() => currentStateOf(props.card));
const periodText = computed(() => {
    const p = props.card?.period || {};
    if (!p.from || !p.to) return '';
    return p.from === p.to
        ? formatLocalDate(p.from, locale.value)
        : t('reports.card.period_range', { from: formatLocalDate(p.from, locale.value), to: formatLocalDate(p.to, locale.value) });
});
</script>

<template>
    <article class="flex h-full flex-col gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card"
             :aria-labelledby="`card-${cardId}-title`">
        <header class="flex flex-wrap items-start justify-between gap-2">
            <h3 :id="`card-${cardId}-title`" class="text-base font-semibold text-ink">{{ t(`reports.cards.${cardId}`) }}</h3>
            <StatusBadge v-if="state.current" tone="info"
                         :label="t('reports.card.current_state', { date: formatInstant(state.asOf, locale) })" />
        </header>
        <div class="grow text-base text-ink"><slot /></div>
        <footer class="grid gap-0.5 border-t border-tone-neutral-border pt-2 text-sm text-ink-muted">
            <p v-if="!state.current && periodText">{{ t('reports.card.period', { period: periodText }) }}</p>
            <p v-else-if="state.current">{{ t('reports.card.period_current') }}</p>
            <p>{{ t('reports.card.source', { source: cardSource(cardId, card, t, te) }) }}</p>
        </footer>
    </article>
</template>
