<!-- src/components/stock/StockCountRequests.vue -->
<!-- Liste simple des demandes d'ajustement issues des comptages : celles du controleur (admin et promoteur : toutes),
     avec l'issue de chacune. Lecture seule. -->
<template>
  <AppCard :title="t('stockCount.my_requests_title')">
    <p v-if="loadError" role="alert" class="mb-3 rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ t('stockCount.my_requests_error') }}</p>
    <ResponsiveTable :columns="columns" :rows="items" row-key="id" :loading="loading"
                     :empty-title="t('stockCount.my_requests_empty')" :empty-message="' '" striped>
      <template #cell-number="{ row }"><span class="font-mono">{{ row.number }}</span></template>
      <template #cell-status="{ row }">
        <StatusBadge :tone="tone(row.status)" :label="t(`stockCount.request_status.${row.status}`)" />
        <span v-if="row.status === 'refuse' && row.decision_note" class="block text-base text-ink-muted">{{ row.decision_note }}</span>
      </template>
      <template #cell-requested="{ row }">{{ formatLocalDateTime(row.requested_at, locale) }}</template>
    </ResponsiveTable>
  </AppCard>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppCard, ResponsiveTable, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { StockCountGateway } from '@/services/StockCountGateway';
import { formatLocalDateTime } from '@/utils/stockCount';

const { t, locale } = useI18n();
const items = ref([]);
const loading = ref(false);
const loadError = ref(false);

const columns = computed(() => [
  { key: 'number', label: t('stockCount.col_request_number') },
  { key: 'product_name', label: t('stockCount.col_product') },
  { key: 'status', label: t('stockCount.col_request_status') },
  { key: 'requested', label: t('stockCount.col_date') },
]);
const tone = (s) => ({ approuve: 'success', refuse: 'danger', en_attente: 'warning' }[s] || 'neutral');

onMounted(async () => {
  loading.value = true;
  try {
    items.value = (await StockCountGateway.myRequests())?.items || [];
  } catch (err) {
    loadError.value = true;
    console.error("Chargement des demandes d'ajustement echoue :", err);
  } finally {
    loading.value = false;
  }
});
</script>
