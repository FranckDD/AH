<!-- src/components/stock/StockCountReveal.vue -->
<!-- Tableau revele d'un comptage VALIDE (resultat de la validation ou detail de l'historique) : seul endroit
     ou la quantite du systeme et l'ecart sont lus. -->
<template>
  <section class="grid gap-3" :aria-label="t('stockCount.reveal_title')">
    <p role="status" class="rounded-card border p-4 text-base" :class="toneClasses('info')">{{ t('stockCount.reveal_notice') }} {{ t('stockCount.gap_explained') }}</p>
    <ResponsiveTable :columns="columns" :rows="count.lines || []" row-key="product_id"
                     :empty-title="t('stockCount.reveal_empty')" :empty-message="' '" striped>
      <template #cell-product="{ row }">
        <span class="font-semibold">{{ row.product_name }}</span>
        <StatusBadge v-if="row.recount" tone="info" :label="t('stockCount.recount')" class="ml-2" />
        <span v-if="row.observation" class="block text-base text-ink-muted">{{ row.observation }}</span>
      </template>
      <!-- stock du systeme AU MOMENT ou le produit a ete compte (peut etre negatif) -->
      <template #cell-system="{ row }">
        {{ row.stock_at_count ?? row.previous_qty }}
        <span v-if="row.counted_at" class="block text-base text-ink-muted">{{ t('stockCount.counted_at', { time: formatLocalDateTime(row.counted_at, locale) }) }}</span>
      </template>
      <template #cell-counted="{ row }">{{ row.counted_qty }}</template>
      <template #cell-gap="{ row }">
        <!-- stock systeme negatif compte 0 : ecart nul sur la ligne, mais une demande de correction existe -->
        <StatusBadge v-if="row.gap_kind === 'aucun' && row.adjustment_request_id" tone="warning" :label="t('stockCount.gap_negative_system')" />
        <StatusBadge v-else :tone="row.gap_kind === 'aucun' ? 'success' : 'warning'"
                     :label="t(gapKey(row.gap_kind), { n: Math.abs(row.difference) })" />
      </template>
      <template #cell-movements="{ row }">
        {{ movementsKey(row.movements_during) ? t(movementsKey(row.movements_during), { n: row.movements_during, net: signed(row.movements_net) }) : t('stockCount.movements_none') }}
      </template>
      <template #cell-request="{ row }">
        <template v-if="row.adjustment_request_id">
          <router-link v-if="isAdmin" to="/dashboard/stock-adjustment-requests"
                       class="inline-flex min-h-11 items-center font-medium text-brand-700 underline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600">
            {{ t('stockCount.request_created', { id: row.adjustment_request_id }) }}
          </router-link>
          <span v-else>{{ t('stockCount.request_created', { id: row.adjustment_request_id }) }}</span>
          <StatusBadge v-if="row.adjustment_status" class="mt-1 block w-fit" :tone="requestTone(row.adjustment_status)"
                       :label="t(`stockCount.request_status.${row.adjustment_status}`)" />
        </template>
        <span v-else class="text-ink-muted">{{ t('stockCount.request_none') }}</span>
        <span v-for="sid in row.superseded_request_ids || []" :key="sid" class="block text-base text-ink-muted">
          {{ t('stockCount.superseded_request', { id: sid }) }}
        </span>
      </template>
    </ResponsiveTable>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ResponsiveTable, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import { gapKey, movementsKey, formatLocalDateTime } from '@/utils/stockCount';

defineProps({ count: { type: Object, required: true } });

const { t, locale } = useI18n();
// cumul des mouvements apres le comptage, signe explicite (+5, -3, 0)
const signed = (n) => (Number(n) > 0 ? `+${n}` : String(n ?? 0));
const requestTone = (s) => ({ approuve: 'success', refuse: 'danger', en_attente: 'warning' }[s] || 'neutral');
const authStore = useAuthStore();
const isAdmin = computed(() => authStore.hasRole(['admin']));

const columns = computed(() => [
  { key: 'product', label: t('stockCount.col_product') },
  { key: 'system', label: t('stockCount.col_system'), align: 'right' },
  { key: 'counted', label: t('stockCount.col_counted'), align: 'right' },
  { key: 'gap', label: t('stockCount.col_gap') },
  { key: 'movements', label: t('stockCount.col_movements') },
  { key: 'request', label: t('stockCount.col_request') },
]);
</script>
