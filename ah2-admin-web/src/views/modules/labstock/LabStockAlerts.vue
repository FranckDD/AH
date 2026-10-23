<!-- src/views/modules/labstock/LabStockAlerts.vue -->
<!-- Alertes du stock labo : rappel de comptage, stocks bas, peremptions. Acces : READERS. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('labStock.alerts_title')" :subtitle="t('labStock.alerts_subtitle')" />

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="isLoading" role="status" class="p-10 text-center text-base text-ink-muted">{{ t('stockOps.loading') }}</p>

    <template v-else-if="data">
      <!-- rappel de comptage -->
      <section aria-labelledby="lab-alerts-count" class="flex flex-col gap-3 rounded-card border p-4 shadow-card md:flex-row md:items-center md:justify-between"
               :class="countDue ? toneClasses('warning') : 'border-tone-neutral-border bg-white'">
        <div>
          <h2 id="lab-alerts-count" class="text-lg font-semibold">{{ t('labStock.alerts_count_title') }}</h2>
          <p class="text-base" :class="countDue ? '' : 'text-ink-muted'">{{ countText }}</p>
        </div>
        <router-link v-if="canCount" to="/dashboard/lab-stock-count" :class="[buttonClasses('primary', 'md'), 'w-full md:w-auto']">
          {{ t('labStock.alerts_go_count') }}
        </router-link>
      </section>

      <div class="grid items-start gap-6 md:grid-cols-2">
        <!-- stocks bas -->
        <section aria-labelledby="lab-alerts-low" class="grid gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
          <h2 id="lab-alerts-low" class="flex items-center gap-2 text-lg font-semibold text-ink">
            {{ t('labStock.alerts_low_title') }}
            <StatusBadge :tone="data.low.length ? 'warning' : 'neutral'" :label="String(data.low.length)" />
          </h2>
          <p v-if="!data.low.length" class="py-4 text-center text-base text-ink-muted">{{ t('labStock.alerts_low_empty') }}</p>
          <ul v-else class="divide-y divide-tone-neutral-border">
            <li v-for="p in data.low" :key="p.product_id" class="flex flex-col gap-2 py-3 sm:flex-row sm:items-start sm:justify-between">
              <div class="min-w-0">
                <p class="break-words text-base font-medium text-ink">{{ p.name }}</p>
                <p v-if="p.packaging" class="text-base text-ink-muted">{{ p.packaging }}</p>
                <p class="mt-1 text-base" :class="p.request_status ? 'text-tone-info-text' : 'text-ink-muted'">
                  {{ p.request_status ? t('labStock.alerts_request_open', { status: label(requestStatusLabel(p.request_status)) }) : t('labStock.alerts_no_request') }}
                </p>
              </div>
              <StatusBadge class="shrink-0 self-start" :tone="Number(p.quantity) === 0 ? 'danger' : 'warning'"
                           :label="t('labStock.alerts_qty_threshold', { quantity: Number(p.quantity), threshold: Number(p.alert_threshold) })" />
            </li>
          </ul>
          <router-link v-if="data.low.length" to="/dashboard/lab-stock-requests" :class="[buttonClasses('info', 'md'), 'w-full']">
            {{ t('labStock.alerts_go_requests') }}
          </router-link>
        </section>

        <!-- peremptions -->
        <section aria-labelledby="lab-alerts-expiring" class="grid gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
          <h2 id="lab-alerts-expiring" class="flex items-center gap-2 text-lg font-semibold text-ink">
            {{ t('labStock.alerts_expiring_title') }}
            <StatusBadge :tone="data.expiring.length ? 'danger' : 'neutral'" :label="String(data.expiring.length)" />
          </h2>
          <p v-if="!data.expiring.length" class="py-4 text-center text-base text-ink-muted">{{ t('labStock.alerts_expiring_empty') }}</p>
          <ul v-else class="divide-y divide-tone-neutral-border">
            <li v-for="e in sortedExpiring" :key="e.receipt_line_id" class="flex flex-col gap-2 py-3 sm:flex-row sm:items-start sm:justify-between"
                :class="e.days_left < 0 ? 'rounded-control bg-tone-danger-bg px-2' : ''">
              <div class="min-w-0">
                <p class="break-words text-base font-medium" :class="e.days_left < 0 ? 'text-tone-danger-text' : 'text-ink'">{{ e.product_name || '?' }}</p>
                <p class="text-base text-ink-muted">{{ t('labStock.alerts_lot', { lot: e.lot_number || '?' }) }}</p>
                <p class="text-base text-ink-muted">{{ t('labStock.alerts_expiry_on', { date: formatDate(e.expiry_date) }) }}</p>
              </div>
              <StatusBadge class="shrink-0 self-start" :tone="daysTone(e.days_left)" :label="daysText(e.days_left)" />
            </li>
          </ul>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { requestStatusLabel } from '@/utils/labStockLabels';
import { PageHeader, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { buttonClasses } from '@/utils/ui';

const { t } = useI18n();
const auth = useAuthStore();
const data = ref(null);
const isLoading = ref(false);
const pageError = ref('');

const canCount = computed(() => auth.hasRole(['laborantin', 'admin']));
const label = (l) => (l.key ? t(l.key) : l.raw);
const formatDate = (v) => {
  if (!v) return '?';
  const [y, m, d] = String(v).slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString();
};
const sortedExpiring = computed(() => [...(data.value?.expiring || [])].sort((a, b) => a.days_left - b.days_left));
const countDue = computed(() => !!data.value?.count_status?.reminder_due);
const countText = computed(() => {
  const st = data.value?.count_status || {};
  if (st.days_since == null) return t('labStock.count_reminder_never');
  return st.reminder_due ? t('labStock.count_reminder', { days: st.days_since }) : t('labStock.alerts_count_ok', { days: st.days_since });
});
const daysText = (d) => (d < 0 ? t('labStock.alerts_expired', { days: -d }) : d === 0 ? t('labStock.alerts_expires_today') : t('labStock.alerts_days_left', { days: d }));
const daysTone = (d) => (d <= 15 ? 'danger' : 'warning');

onMounted(async () => {
  isLoading.value = true;
  try {
    const r = await LabStockGateway.getAlerts();
    data.value = { low: r?.low || [], expiring: r?.expiring || [], count_status: r?.count_status || {} };
  } catch (e) {
    pageError.value = describeLabStockError(e, t('stockOps.error_load'));
  } finally {
    isLoading.value = false;
  }
});
</script>
