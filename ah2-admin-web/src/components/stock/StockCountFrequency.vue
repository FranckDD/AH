<!-- src/components/stock/StockCountFrequency.vue -->
<!-- Frequence de comptage : par produit, dernier comptage (date locale), jours ecoules et statut dit en mots.
     Aucune quantite du systeme. Le reglage du nombre de jours est reserve a l'admin. -->
<template>
  <div class="grid gap-4">
    <p v-if="store.frequencyError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ t('stockCount.frequency_error') }}</p>

    <div v-if="store.frequency" class="grid gap-3 sm:grid-cols-3">
      <StatTile :title="t('stockCount.status_jamais_compte')" :value="store.frequency.counts?.jamais_compte ?? 0" tone="danger" />
      <StatTile :title="t('stockCount.status_en_retard')" :value="store.frequency.counts?.en_retard ?? 0" tone="warning" />
      <StatTile :title="t('stockCount.status_a_jour')" :value="store.frequency.counts?.a_jour ?? 0" tone="success" />
    </div>

    <AppCard v-if="store.frequency" :title="t('stockCount.frequency_title')"
             :subtitle="t('stockCount.interval_current', { n: store.frequency.interval_days })">
      <form v-if="canSetInterval" class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end" @submit.prevent="saveInterval">
        <FormField id="count-interval" :label="t('stockCount.interval_label')" :help="t('stockCount.interval_help')"
                   :error="interval !== '' && parseInterval(interval) === null ? t('stockCount.interval_invalid') : ''" v-slot="{ describedBy }">
          <input id="count-interval" v-model="interval" type="text" inputmode="numeric" autocomplete="off"
                 :aria-describedby="describedBy" :class="[fieldClass, 'w-32 text-right']" />
        </FormField>
        <AppButton type="submit" variant="info" :disabled="saving || parseInterval(interval) === null" :loading="saving">
          {{ t('stockCount.interval_save') }}
        </AppButton>
      </form>
      <p v-if="intervalError" role="alert" class="mb-3 rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ intervalError }}</p>
      <p v-if="intervalDone" role="status" class="mb-3 rounded-control border p-3 text-base" :class="toneClasses('success')">{{ intervalDone }}</p>

      <label class="mb-3 flex min-h-11 items-center gap-2 text-base text-ink">
        <input v-model="lateOnly" type="checkbox" class="h-5 w-5" />
        {{ t('stockCount.filter_late') }}
      </label>
      <ResponsiveTable :columns="columns" :rows="rows" row-key="product_id"
                       :empty-title="t('stockCount.frequency_empty')" :empty-message="' '" striped>
        <template #cell-name="{ row }"><span class="font-medium">{{ row.name }}</span></template>
        <template #cell-last="{ row }">{{ row.last_counted_at ? formatLocalDate(row.last_counted_at, locale) : t('stockCount.never') }}</template>
        <template #cell-days="{ row }">{{ row.days_since === null || row.days_since === undefined ? '' : t('stockCount.days', { n: row.days_since }) }}</template>
        <template #cell-status="{ row }">
          <StatusBadge :tone="STATUS_TONES[row.status] || 'neutral'" :label="t(`stockCount.status_${row.status}`)" />
        </template>
      </ResponsiveTable>
    </AppCard>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, AppCard, FormField, ResponsiveTable, StatTile, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import { useStockCountStore } from '@/stores/stockCountStore';
import { parseInterval, formatLocalDate } from '@/utils/stockCount';
import { describeServerError } from '@/utils/serverError';

const { t, locale } = useI18n();
const authStore = useAuthStore();
const store = useStockCountStore();

const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const STATUS_TONES = { jamais_compte: 'danger', en_retard: 'warning', a_jour: 'success' };

const canSetInterval = computed(() => authStore.hasRole(['admin']));
const lateOnly = ref(false);
const interval = ref('');
const intervalError = ref('');
const intervalDone = ref('');
const saving = ref(false);

watch(() => store.frequency?.interval_days, (n) => { if (n) interval.value = String(n); }, { immediate: true });

const rows = computed(() => (store.frequency?.products || [])
  .filter((p) => !lateOnly.value || p.status !== 'a_jour'));

const columns = computed(() => [
  { key: 'name', label: t('stockCount.col_product') },
  { key: 'last', label: t('stockCount.col_last') },
  { key: 'days', label: t('stockCount.col_days'), align: 'right' },
  { key: 'status', label: t('stockCount.col_status') },
]);

async function saveInterval() {
  if (saving.value) return;
  const days = parseInterval(interval.value);
  if (days === null) return;
  saving.value = true;
  intervalError.value = '';
  intervalDone.value = '';
  try {
    await store.saveInterval(days);
    intervalDone.value = t('stockCount.interval_saved');
  } catch (err) {
    intervalError.value = err?.response ? (describeServerError(err, '') || t('stockCount.save_error')) : t('stockCount.network_error');
  } finally {
    saving.value = false;
  }
}
</script>
