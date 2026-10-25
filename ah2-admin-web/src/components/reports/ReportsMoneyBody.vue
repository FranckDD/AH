<!-- Corps des cartes Argent (1 a 5). Montants : chaines du serveur formatees sans flottant. -->
<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { StatusBadge } from '@/components/ui';
import { modeLabel } from '@/utils/paymentModes';
import { formatMoney, formatCount, formatLocalDate } from '@/utils/reports';

const props = defineProps({
    cardId: { type: String, required: true },
    card: { type: Object, required: true },
});
const { t, te, locale } = useI18n();
const c = computed(() => props.card || {});
const tk = (k) => (k && te(k) ? t(k) : k || '');
const reasonLabel = (r) => (r === 'non_precise' ? t('reports.labels.reason_unspecified') : r);
const who = (r) => r.full_name || r.username || `#${r.user_id}`;
</script>

<template>
    <!-- 1. encaisse -->
    <div v-if="cardId === 'collected'" class="grid gap-2">
        <p class="text-2xl font-bold text-ink">{{ formatMoney(c.total) }}</p>
        <dl class="grid gap-1">
            <div v-for="(v, m) in c.by_mode" :key="m" class="flex justify-between gap-3">
                <dt class="text-ink-muted">{{ modeLabel(m) }}</dt><dd class="font-medium">{{ formatMoney(v) }}</dd>
            </div>
        </dl>
        <p class="text-sm text-ink-muted">{{ t('reports.notes.collected') }}</p>
    </div>

    <!-- 2. ecarts de caisse -->
    <div v-else-if="cardId === 'cash_gaps'" class="grid gap-2">
        <p class="text-2xl font-bold text-ink">{{ formatMoney(c.total_abs_gap) }}</p>
        <p class="text-sm text-ink-muted">{{ t('reports.notes.scope_all_modes') }}</p>
        <p v-if="!c.days?.length" class="text-ink-muted">{{ t('reports.labels.no_closure') }}</p>
        <ul v-else class="grid max-h-64 gap-1 overflow-y-auto">
            <li v-for="d in c.days" :key="d.closure_id" class="flex flex-wrap items-center justify-between gap-2 border-b border-tone-neutral-border py-1">
                <span>{{ formatLocalDate(d.business_date, locale) }}
                    <span class="text-sm text-ink-muted">({{ t(`reports.labels.closure_${d.kind === 'auto' ? 'auto' : 'manual'}`) }})</span></span>
                <span class="flex flex-wrap items-center gap-2">
                    <span class="font-medium">{{ d.difference === null ? t('reports.labels.not_counted') : formatMoney(d.difference) }}</span>
                    <StatusBadge v-if="d.comment_missing" tone="warning" :label="t('reports.labels.comment_missing')" />
                </span>
            </li>
        </ul>
    </div>

    <!-- 3. retraits et ventes annulees -->
    <div v-else-if="cardId === 'withdrawals_and_cancellations'" class="grid gap-3">
        <div>
            <p class="font-semibold">{{ t('reports.labels.withdrawals') }}</p>
            <p class="text-xl font-bold">{{ formatMoney(c.withdrawals?.total) }}</p>
            <p class="text-sm text-ink-muted">{{ t('reports.labels.count', { n: formatCount(c.withdrawals?.count ?? 0) }) }}</p>
            <ul class="mt-1 grid gap-0.5">
                <li v-for="(v, r) in c.withdrawals?.by_reason" :key="r" class="flex justify-between gap-3">
                    <span class="text-ink-muted">{{ reasonLabel(r) }}</span><span>{{ formatMoney(v) }}</span>
                </li>
            </ul>
        </div>
        <div>
            <p class="font-semibold">{{ t('reports.labels.cancelled_sales') }}</p>
            <p class="text-sm text-ink-muted">{{ t('reports.labels.count', { n: formatCount(c.cancelled_sales?.count ?? 0) }) }}</p>
            <dl class="grid gap-0.5">
                <div class="flex justify-between gap-3"><dt class="text-ink-muted">{{ t('reports.labels.invoice_total') }}</dt><dd>{{ formatMoney(c.cancelled_sales?.invoice_total) }}</dd></div>
                <div class="flex justify-between gap-3"><dt class="text-ink-muted">{{ t('reports.labels.amount_returned') }}</dt><dd>{{ formatMoney(c.cancelled_sales?.amount_returned) }}</dd></div>
            </dl>
            <ul v-if="c.cancelled_sales?.recent?.length" class="mt-2 grid max-h-48 gap-1 overflow-y-auto text-sm">
                <li v-for="s in c.cancelled_sales.recent" :key="s.transaction_id" class="border-b border-tone-neutral-border py-1">
                    {{ t('reports.labels.cancelled_line', { id: s.transaction_id, who: s.cancelled_by_name || '', amount: formatMoney(s.invoice_amount) }) }}
                    <span v-if="s.justification" class="block text-ink-muted">{{ s.justification }}</span>
                </li>
            </ul>
        </div>
    </div>

    <!-- 4. reductions -->
    <div v-else-if="cardId === 'discounts'" class="grid gap-3">
        <div v-for="part in ['manual', 'staff']" :key="part">
            <p class="font-semibold">{{ t(`reports.labels.discount_${part}`) }}</p>
            <p class="text-xl font-bold">{{ formatMoney(c[part]?.amount) }}</p>
            <p class="text-sm text-ink-muted">{{ t('reports.labels.count', { n: formatCount(c[part]?.count ?? 0) }) }}</p>
            <p class="text-sm text-ink-muted">{{ t('reports.labels.basis', { basis: tk(c[part]?.basis) }) }}</p>
        </div>
    </div>

    <!-- 5. encaisse par secretaire, par jour travaille -->
    <div v-else-if="cardId === 'per_secretary'" class="grid gap-2">
        <p class="text-sm text-ink-muted">{{ t('reports.notes.per_secretary') }}</p>
        <p v-if="!c.rows?.length" class="text-ink-muted">{{ t('reports.labels.no_payment') }}</p>
        <ul v-else class="grid gap-2">
            <li v-for="r in c.rows" :key="r.user_id" class="grid gap-0.5 border-b border-tone-neutral-border pb-2">
                <p class="font-semibold">{{ who(r) }}</p>
                <p>{{ t('reports.labels.collected_total', { amount: formatMoney(r.collected) }) }}</p>
                <p>{{ t('reports.labels.per_worked_day', { amount: formatMoney(r.per_worked_day), n: r.worked_days }) }}</p>
                <p class="text-sm text-ink-muted">{{ t('reports.labels.of_which_cancelled_later', { amount: formatMoney(r.of_which_cancelled_later) }) }}</p>
            </li>
        </ul>
    </div>
</template>
