<!-- Courbes de croissance (cartes 12 et 13) : 13 semaines ISO. La derniere semaine, si elle est partielle, est
     tracee en pointille et dite en mots. Couleurs : jetons CSS lus a l'execution. Table de donnees pour l'accessibilite. -->
<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Legend, Tooltip } from 'chart.js';
import { formatLocalDate, formatMoney, seriesValues, partialIndex } from '@/utils/reports';

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Legend, Tooltip);

const props = defineProps({
    mode: { type: String, required: true }, // 'people' | 'sales'
    card: { type: Object, required: true },
});
const { t, locale } = useI18n();
const canvas = ref(null);
let chart = null;

const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim();

// [{ key, label, series, money, color }]
const lines = computed(() => {
    const c = props.card || {};
    if (props.mode === 'people') {
        return [
            { key: 'new_patients', label: t('reports.growth.new_patients'), series: c.new_patients?.series || [], color: 'brand-600' },
            { key: 'medical', label: t('reports.growth.medical'), series: c.consultations?.medical || [], color: 'action-600' },
            { key: 'spiritual', label: t('reports.growth.spiritual'), series: c.consultations?.spiritual || [], color: 'tab-spirit' },
        ];
    }
    return [
        { key: 'sales', label: t('reports.growth.sales'), series: c.series || [], money: true, color: 'brand-600' },
        { key: 'previous', label: t('reports.growth.sales_previous'), series: c.sales_previous || [], money: true, color: 'ink-muted' },
    ];
});
const weeks = computed(() => (lines.value[0]?.series || []).map((p) => p.week_start));
const partial = computed(() => partialIndex(lines.value[0]?.series));
const fmt = (line, v) => (line.money ? formatMoney(v) : String(v ?? ''));
const summary = computed(() => lines.value.map((l) => {
    const last = l.series[l.series.length - 1];
    return `${l.label} : ${last ? fmt(l, last.value) : ''}`;
}).join(' ; '));

function draw() {
    if (!canvas.value) return;
    const pIdx = partial.value;
    const data = {
        labels: weeks.value.map((w) => formatLocalDate(w, locale.value)),
        datasets: lines.value.map((l) => {
            const color = token(l.color);
            return {
                label: l.label, data: seriesValues(l.series), borderColor: color, backgroundColor: color,
                tension: 0.25, pointRadius: 3,
                borderDash: l.key === 'previous' ? [2, 3] : undefined,
                // segment vers la semaine partielle : pointille (la serie precedente n'a jamais de semaine partielle)
                segment: { borderDash: (ctx) => (l.key !== 'previous' && pIdx >= 0 && ctx.p1DataIndex === pIdx ? [6, 4] : undefined) },
            };
        }),
    };
    const ink = token('ink-muted');
    const grid = token('tone-neutral-border');
    const options = {
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { labels: { color: ink, font: { size: 13 } } } },
        scales: {
            x: { ticks: { color: ink, font: { size: 13 } }, grid: { color: grid } },
            y: { beginAtZero: true, ticks: { color: ink, font: { size: 13 } }, grid: { color: grid } },
        },
    };
    if (chart) chart.destroy();
    chart = new Chart(canvas.value, { type: 'line', data, options });
}

onMounted(draw);
watch(() => [props.card, locale.value], draw, { deep: false });
onBeforeUnmount(() => { if (chart) chart.destroy(); chart = null; });
</script>

<template>
    <div class="grid gap-2">
        <div class="relative h-64">
            <canvas ref="canvas" role="img" :aria-label="t('reports.growth.aria', { summary })"></canvas>
        </div>
        <p v-if="partial >= 0" class="text-sm text-ink-muted">{{ t('reports.growth.partial_note') }}</p>
        <p v-if="mode === 'sales' && card.previous_period" class="text-sm text-ink-muted">
            {{ t('reports.growth.previous_period', { from: formatLocalDate(card.previous_period.from, locale), to: formatLocalDate(card.previous_period.to, locale) }) }}
        </p>
        <details>
            <summary class="flex min-h-11 cursor-pointer items-center text-base text-ink">{{ t('reports.growth.show_table') }}</summary>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <caption class="sr-only">{{ t(`reports.cards.${mode}`) }}</caption>
                    <thead><tr><th scope="col" class="py-1 pr-2">{{ t('reports.growth.week') }}</th>
                        <th v-for="l in lines" :key="l.key" scope="col" class="py-1 pr-2">{{ l.label }}</th></tr></thead>
                    <tbody>
                        <tr v-for="(w, i) in weeks" :key="w" class="border-t border-tone-neutral-border">
                            <th scope="row" class="py-1 pr-2 font-normal">{{ formatLocalDate(w, locale) }}<span v-if="i === partial"> ({{ t('reports.growth.partial') }})</span></th>
                            <td v-for="l in lines" :key="l.key" class="py-1 pr-2">{{ fmt(l, l.series[i]?.value) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </details>
    </div>
</template>
