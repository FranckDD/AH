<!-- Corps des cartes Produits (6 a 8) et Production (9 a 11). -->
<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { StatusBadge } from '@/components/ui';
import { formatMoney, formatCount, formatInstant } from '@/utils/reports';

const props = defineProps({
    cardId: { type: String, required: true },
    card: { type: Object, required: true },
});
const { t, te, locale } = useI18n();
const c = computed(() => props.card || {});
const tk = (k) => (k && te(k) ? t(k) : k || '');
const batchStatus = (s) => (te(`fabrication.batch_status_${s}`) ? t(`fabrication.batch_status_${s}`) : s);
const countStatus = (s) => (te(`stockCount.status_${s}`) ? t(`stockCount.status_${s}`) : s);
</script>

<template>
    <!-- 6. vendus contre recus -->
    <div v-if="cardId === 'sold_vs_received'" class="grid gap-2">
        <dl class="grid grid-cols-3 gap-2 text-center">
            <div><dt class="text-sm text-ink-muted">{{ t('reports.labels.sold') }}</dt><dd class="text-2xl font-bold">{{ formatCount(c.sold) }}</dd></div>
            <div><dt class="text-sm text-ink-muted">{{ t('reports.labels.received') }}</dt><dd class="text-2xl font-bold">{{ formatCount(c.received) }}</dd></div>
            <div><dt class="text-sm text-ink-muted">{{ t('reports.labels.system_stock') }}</dt><dd class="text-2xl font-bold">{{ formatCount(c.system_stock) }}</dd></div>
        </dl>
        <p class="text-sm text-ink-muted">{{ t('reports.labels.received_detail', { receipts: formatCount(c.received_detail?.receipts ?? 0), reappro: formatCount(c.received_detail?.reapprovisionnement ?? 0) }) }}</p>
        <p class="text-sm text-ink-muted">{{ t('reports.labels.system_stock_now') }}</p>
        <p v-if="c.formula_key" class="text-sm text-ink-muted">{{ tk(c.formula_key) }}</p>
    </div>

    <!-- 7. comptage du stock -->
    <div v-else-if="cardId === 'stock_count'" class="grid gap-2">
        <dl class="grid gap-1">
            <div v-for="(n, s) in c.counts" :key="s" class="flex justify-between gap-3">
                <dt class="text-ink-muted">{{ countStatus(s) }}</dt><dd class="font-semibold">{{ formatCount(n) }}</dd>
            </div>
        </dl>
        <p class="text-sm text-ink-muted">{{ t('reports.labels.interval_days', { n: c.interval_days }) }}</p>
        <p>{{ t('reports.labels.pending_requests', { n: c.pending_requests?.count ?? 0 }) }}
            <span v-if="c.pending_requests?.oldest_days !== null && c.pending_requests?.oldest_days !== undefined" class="text-ink-muted">
                {{ t('reports.labels.oldest_days', { n: c.pending_requests.oldest_days }) }}</span></p>
        <ul v-if="c.products?.length" class="grid max-h-48 gap-1 overflow-y-auto">
            <li v-for="p in c.products" :key="p.product_id" class="flex flex-wrap items-center justify-between gap-2 border-b border-tone-neutral-border py-1">
                <span>{{ p.name }}</span>
                <StatusBadge :tone="p.status === 'jamais_compte' ? 'danger' : 'warning'" :label="countStatus(p.status)" />
            </li>
        </ul>
        <p v-if="c.products_total > (c.products?.length || 0)" class="text-sm text-ink-muted">{{ t('reports.labels.more', { n: c.products_total - c.products.length }) }}</p>
    </div>

    <!-- 8. ruptures et seuils bas -->
    <div v-else-if="cardId === 'low_stock'" class="grid gap-2">
        <p class="text-2xl font-bold">{{ formatCount(c.total) }}</p>
        <p class="text-sm text-ink-muted">{{ tk(c.rule_key) }}</p>
        <p v-if="!c.products?.length" class="text-ink-muted">{{ t('reports.labels.no_low_stock') }}</p>
        <ul v-else class="grid max-h-48 gap-1 overflow-y-auto">
            <li v-for="p in c.products" :key="p.product_id" class="flex flex-wrap justify-between gap-2 border-b border-tone-neutral-border py-1">
                <span>{{ p.name }}</span>
                <span class="flex items-center gap-2">
                    <StatusBadge :tone="Number(p.quantity) <= 0 ? 'danger' : 'warning'" :label="Number(p.quantity) <= 0 ? t('reports.labels.out_of_stock') : t('reports.labels.low')" />
                    <span>{{ t('reports.labels.qty_threshold', { q: p.quantity, s: p.threshold }) }}</span>
                </span>
            </li>
        </ul>
        <p v-if="c.total > (c.products?.length || 0)" class="text-sm text-ink-muted">{{ t('reports.labels.more', { n: c.total - c.products.length }) }}</p>
    </div>

    <!-- 9. etat des lots -->
    <div v-else-if="cardId === 'batches'" class="grid gap-2">
        <dl class="grid gap-1">
            <div v-for="(n, s) in c.counts_by_status" :key="s" class="flex justify-between gap-3">
                <dt class="text-ink-muted">{{ batchStatus(s) }}</dt><dd class="font-semibold">{{ formatCount(n) }}</dd>
            </div>
        </dl>
        <p>{{ t('reports.labels.stale', { n: c.stale_total ?? 0, days: c.stale_days }) }}</p>
        <ul v-if="c.stale?.length" class="grid gap-1 text-sm">
            <li v-for="b in c.stale" :key="b.batch_id">{{ t('reports.labels.stale_line', { n: b.batch_number, status: batchStatus(b.status), days: b.days }) }}</li>
        </ul>
    </div>

    <!-- 10. bouteilles -->
    <div v-else-if="cardId === 'bottles'" class="grid gap-2">
        <dl class="grid gap-1">
            <div class="flex justify-between gap-3"><dt class="text-ink-muted">{{ t('reports.labels.produced') }}</dt><dd class="text-xl font-bold">{{ formatCount(c.produced) }}</dd></div>
            <div class="flex justify-between gap-3"><dt class="text-ink-muted">{{ t('reports.labels.output_sample') }}</dt><dd class="font-semibold">{{ formatCount(c.outputs?.echantillon ?? 0) }}</dd></div>
            <div class="flex justify-between gap-3"><dt class="text-ink-muted">{{ t('reports.labels.output_other') }}</dt><dd class="font-semibold">{{ formatCount(c.outputs?.autre ?? 0) }}</dd></div>
            <div class="flex justify-between gap-3"><dt class="text-ink-muted">{{ t('reports.labels.shipped') }}</dt><dd class="font-semibold">{{ formatCount(c.shipped) }}</dd></div>
        </dl>
    </div>

    <!-- 11. manque et cout de revient -->
    <div v-else-if="cardId === 'loss_and_cost'" class="grid gap-3">
        <div>
            <p class="font-semibold">{{ t('reports.labels.out_of_tolerance', { n: c.out_of_tolerance?.total ?? 0 }) }}</p>
            <p v-if="c.out_of_tolerance?.current_state" class="text-sm text-ink-muted">{{ t('reports.card.current_state', { date: formatInstant(c.out_of_tolerance.as_of, locale) }) }}</p>
            <ul v-if="c.out_of_tolerance?.items?.length" class="grid gap-1 text-sm">
                <li v-for="b in c.out_of_tolerance.items" :key="b.batch_id">{{ t('reports.labels.oot_line', { n: b.batch_number, q: b.missing_qty, pct: b.missing_pct, tol: b.tolerance_applied }) }}</li>
            </ul>
        </div>
        <div>
            <p class="font-semibold">{{ t('reports.labels.period_average_cost') }}</p>
            <p class="text-sm text-ink-muted">{{ t(`reports.scopes.${c.period_average_unit_cost_scope || 'period'}`) }}</p>
            <p class="text-xl font-bold">{{ c.period_average_unit_cost ? formatMoney(c.period_average_unit_cost) : t('reports.labels.none') }}</p>
            <p v-if="c.cost_per_good_bottle?.length" class="mt-2 font-semibold">{{ t('reports.labels.cost_per_good_bottle') }}</p>
            <p v-if="c.cost_per_good_bottle?.length" class="text-sm text-ink-muted">{{ t(`reports.scopes.${c.cost_per_good_bottle_scope || 'all_time'}`) }}</p>
            <ul v-if="c.cost_per_good_bottle?.length" class="mt-1 grid gap-1 text-sm">
                <li v-for="p in c.cost_per_good_bottle" :key="p.product_id">{{ t('reports.labels.cost_line', { name: p.product_name, last: formatMoney(p.last_unit_cost), avg: formatMoney(p.average_unit_cost) }, Number(p.batches) || 0) }}</li>
            </ul>
        </div>
    </div>
</template>
