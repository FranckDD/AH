<!-- src/components/stock/StockCountHistory.vue -->
<!-- Historique des comptages VALIDES (lecture seule pour tous les roles) : filtres par dates locales et detail
     revele d'un comptage. -->
<template>
  <div class="grid gap-4">
    <AppCard :title="t('stockCount.history_title')">
      <form class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end" @submit.prevent="applyFilters">
        <FormField id="count-date-from" :label="t('stockCount.date_from')" v-slot="{ describedBy }">
          <input id="count-date-from" v-model="dateFrom" type="date" :max="dateTo || todayLocalISO()" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="count-date-to" :label="t('stockCount.date_to')" v-slot="{ describedBy }">
          <input id="count-date-to" v-model="dateTo" type="date" :min="dateFrom || undefined" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <AppButton type="submit" variant="info">{{ t('stockCount.filter_apply') }}</AppButton>
        <AppButton variant="ghost" @click="resetFilters">{{ t('stockCount.filter_reset') }}</AppButton>
      </form>
      <p v-if="filterError" role="alert" class="mb-3 rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ filterError }}</p>
      <p v-if="store.historyError" role="alert" class="mb-3 rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ t('stockCount.history_error') }}</p>

      <ResponsiveTable :columns="columns" :rows="store.history.items" row-key="id" :loading="store.isLoadingHistory"
                       :empty-title="t('stockCount.history_empty')" :empty-message="' '" striped>
        <template #cell-date="{ row }">{{ formatLocalDateTime(row.submitted_at, locale) }}</template>
        <template #cell-by="{ row }">{{ row.started_by_name || '' }}</template>
        <template #cell-lines="{ row }">{{ t('stockCount.lines_summary', { n: row.lines_count ?? 0, g: row.gaps_count ?? 0 }) }}</template>
        <template #actions="{ row }">
          <AppButton variant="secondary" :aria-pressed="detail?.id === row.id ? 'true' : 'false'" @click="selectCount(row)">
            {{ t('stockCount.history_view') }}
          </AppButton>
        </template>
      </ResponsiveTable>
      <nav v-if="store.history.total > 0" class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between" :aria-label="t('stockCount.history_title')">
        <p role="status" class="text-base text-ink-muted">{{ t('stockCount.page_range', rangeText) }}</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :disabled="page <= 1 || store.isLoadingHistory" @click="loadPage(page - 1)">{{ t('stockCount.page_prev') }}</AppButton>
          <AppButton variant="secondary" :disabled="page >= pageCount || store.isLoadingHistory" @click="loadPage(page + 1)">{{ t('stockCount.page_next') }}</AppButton>
        </div>
      </nav>
    </AppCard>

    <StockCountRequests />

    <p v-if="detailError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ detailError }}</p>
    <AppCard v-if="detail" :title="t('stockCount.detail_title', { id: detail.id })"
             :subtitle="t('stockCount.detail_subtitle', { date: formatLocalDateTime(detail.submitted_at, locale), name: detail.started_by_name || '' })">
      <template #actions>
        <AppButton variant="ghost" @click="closeDetail">{{ t('stockCount.close') }}</AppButton>
      </template>
      <StockCountReveal v-if="detail" :count="detail" />
    </AppCard>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, AppCard, FormField, ResponsiveTable } from '@/components/ui';
import StockCountReveal from '@/components/stock/StockCountReveal.vue';
import StockCountRequests from '@/components/stock/StockCountRequests.vue';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import { useStockCountStore, HISTORY_PAGE_SIZE } from '@/stores/stockCountStore';
import { formatLocalDateTime } from '@/utils/stockCount';
import { todayLocalISO } from '@/utils/localDate';
import { describeServerError } from '@/utils/serverError';

const { t, locale } = useI18n();
const authStore = useAuthStore();
const store = useStockCountStore();

const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const dateFrom = ref('');
const dateTo = ref('');
const filterError = ref('');
const detail = ref(null);
const detailError = ref('');

const columns = computed(() => [
  { key: 'date', label: t('stockCount.col_date') },
  { key: 'by', label: t('stockCount.col_by') },
  { key: 'lines', label: t('stockCount.col_lines') },
]);

// Pagination : 50 par page (HISTORY_PAGE_SIZE). Les filtres appliques sont gardes pour changer de page.
const page = ref(1);
const applied = ref({});
const pageCount = computed(() => Math.max(1, Math.ceil(store.history.total / HISTORY_PAGE_SIZE)));
const rangeText = computed(() => {
  const from = store.history.offset + 1;
  return { from, to: store.history.offset + store.history.items.length, total: store.history.total };
});

function loadPage(n) {
  page.value = Math.min(Math.max(1, n), pageCount.value);
  store.loadHistory(applied.value, page.value);
}

function applyFilters() {
  filterError.value = '';
  if (dateFrom.value && dateTo.value && dateFrom.value > dateTo.value) {
    filterError.value = t('stockCount.date_order');
    return;
  }
  page.value = 1;
  applied.value = { dateFrom: dateFrom.value, dateTo: dateTo.value };
  store.loadHistory(applied.value, 1);
}

function resetFilters() {
  dateFrom.value = '';
  dateTo.value = '';
  applyFilters();
}

// Compteur de demandes : seule la reponse du DERNIER detail demande est appliquee (clics rapides).
let detailSeq = 0;
async function selectCount(row) {
  const seq = ++detailSeq;
  detailError.value = '';
  try {
    const out = await store.getDetail(row.id);
    if (seq === detailSeq) detail.value = out;
  } catch (err) {
    if (seq !== detailSeq) return;
    detail.value = null;
    detailError.value = err?.response ? (describeServerError(err, '') || t('stockCount.load_error')) : t('stockCount.network_error');
  }
}

function closeDetail() { detailSeq++; detail.value = null; }

// Poste partage : le detail affiche appartient a l'utilisateur precedent, il est jete au changement.
watch(() => authStore.user?.id ?? null, () => { closeDetail(); detailError.value = ''; resetFilters(); });
onMounted(() => applyFilters());
</script>
