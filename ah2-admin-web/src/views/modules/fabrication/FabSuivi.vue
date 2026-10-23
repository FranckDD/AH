<!-- src/views/modules/fabrication/FabSuivi.vue -->
<!-- Suivi de la fabrication. Lecture : ProductionManager, promoteur, admin. Seul l'admin regle la tolerance et
     le delai d'alerte d'un lot trop long. Les anomalies viennent du serveur (meme source que le futur controle quotidien). -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('fabrication.suivi_title')" :subtitle="t('fabrication.suivi_subtitle')" />

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="isLoading" role="status" class="text-base text-ink-muted">{{ t('stockOps.loading') }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <section class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" :aria-label="t('fabrication.suivi_title')">
      <StatTile
        v-for="s in STATUSES"
        :key="s"
        :title="t(`fabrication.batch_status_${s}`)"
        :value="counts[s] ?? 0"
        :tone="STATUS_TONES[s]"
      />
      <StatTile
        :title="t('fabrication.tile_anomalies')"
        :value="anomaliesCount"
        :note="t('fabrication.tile_anomalies_note')"
        :icon="ExclamationTriangleIcon"
        :tone="anomaliesCount > 0 ? 'danger' : 'success'"
        :alert="anomaliesCount > 0"
      />
    </section>

    <AppCard :title="t('fabrication.recent_title')">
      <ResponsiveTable
        :columns="recentColumns"
        :rows="recentBatches"
        row-key="id"
        :loading="isLoading"
        :empty-title="t('fabrication.no_recent')"
        :empty-message="' '"
        striped
      >
        <template #cell-batch_number="{ row: b }"><span class="font-medium text-ink">{{ b.batch_number }}</span></template>
        <template #cell-production_date="{ row: b }">{{ formatDate(b.production_date) }}</template>
        <template #cell-status="{ row: b }">
          <StatusBadge :tone="STATUS_TONES[b.status] || 'neutral'" :label="t(`fabrication.batch_status_${b.status}`)" />
          <StatusBadge v-if="b.out_of_tolerance" class="ml-2" tone="danger" :label="t('fabrication.out_of_tolerance')" />
        </template>
        <template #actions="{ row: b }">
          <AppButton variant="secondary" :icon="EyeIcon" class="min-h-11" @click="openBatch(b.id)">{{ t('fabrication.open_batch') }}</AppButton>
        </template>
      </ResponsiveTable>
    </AppCard>

    <AppCard :title="t('fabrication.anomalies_title')">
      <EmptyState
        v-if="!isLoading && anomalies.length === 0"
        :title="t('fabrication.no_anomalies')"
        :message="t('fabrication.no_anomalies_message')"
        :icon="CheckCircleIcon"
      />
      <ResponsiveTable
        v-else
        :columns="anomalyColumns"
        :rows="anomalyRows"
        row-key="key"
        :loading="isLoading"
        :empty-title="t('fabrication.no_anomalies')"
        :empty-message="' '"
        striped
      >
        <template #cell-kind="{ row: a }">
          <StatusBadge tone="danger" :label="t(`fabrication.anomaly_kind_${a.kind}`)" />
        </template>
        <template #cell-ref="{ row: a }"><span class="font-medium text-ink">{{ a.ref }}</span></template>
        <template #cell-detail="{ row: a }">{{ detailText(a) }}</template>
        <template #actions="{ row: a }">
          <AppButton v-if="a.detail && a.detail.batch_id" variant="secondary" :icon="EyeIcon" class="min-h-11" @click="openBatch(a.detail.batch_id)">{{ t('fabrication.open_batch') }}</AppButton>
        </template>
      </ResponsiveTable>
    </AppCard>

    <AppCard v-if="canEditSettings" :title="t('fabrication.settings_title')">
      <form class="grid gap-4" @submit.prevent="saveSettings">
        <p class="text-base text-ink-muted">{{ t('fabrication.settings_help') }}</p>
        <p v-if="settingsError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ settingsError }}</p>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="fab-setting-tolerance" :label="t('fabrication.setting_tolerance')" required v-slot="{ describedBy }">
            <input id="fab-setting-tolerance" v-model="settingsForm.tolerance_pct" type="number" inputmode="decimal" min="0" max="100" step="0.01" required :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
          <FormField id="fab-setting-stale" :label="t('fabrication.setting_stale_days')" required v-slot="{ describedBy }">
            <input id="fab-setting-stale" v-model="settingsForm.stale_days" type="number" inputmode="numeric" min="1" max="3650" step="1" required :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
        </div>
        <div>
          <AppButton type="submit" variant="info" class="min-h-11" :disabled="busy" :loading="busy">{{ t('fabrication.settings_save') }}</AppButton>
        </div>
      </form>
    </AppCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { EyeIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { FabricationGateway, describeFabricationError } from '@/services/FabricationGateway';
import { AppButton, AppCard, PageHeader, FormField, StatusBadge, ResponsiveTable, StatTile, EmptyState } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();

// Les reglages ne sont ni affiches ni modifiables pour les autres roles (le serveur refuse aussi).
const canEditSettings = computed(() => authStore.hasRole(['admin']));

const STATUSES = ['brouillon', 'en_production', 'termine', 'expedie', 'annule'];
const STATUS_TONES = { brouillon: 'neutral', en_production: 'info', termine: 'warning', expedie: 'success', annule: 'neutral' };

const recentColumns = computed(() => [
  { key: 'batch_number', label: t('fabrication.col_batch_number') },
  { key: 'production_date', label: t('fabrication.col_date') },
  { key: 'status', label: t('fabrication.col_status') },
]);
const anomalyColumns = computed(() => [
  { key: 'kind', label: t('fabrication.col_kind') },
  { key: 'ref', label: t('fabrication.col_ref') },
  { key: 'detail', label: t('fabrication.col_detail') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const recentBatches = ref([]);
const counts = ref({});
const anomaliesCount = ref(0);
const anomalies = ref([]);
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const settingsError = ref('');
const busy = ref(false);
const settingsForm = ref({ tolerance_pct: '', stale_days: '' });

const anomalyRows = computed(() => anomalies.value.map((a, i) => ({ ...a, key: `${a.kind}-${a.ref}-${i}` })));

const num = (v) => Number(v ?? 0);
const qty = (v) => num(v).toLocaleString('fr-FR', { maximumFractionDigits: 3 });
const formatDate = (v) => (v ? new Date(v).toLocaleDateString('fr-FR') : '-');

// Phrase de detail de chaque nature d'anomalie, avec les valeurs cles du serveur.
const detailText = (a) => {
  const d = a.detail || {};
  const params = {
    hors_tolerance: { missing: qty(d.missing_qty), pct: qty(d.missing_pct), tolerance: qty(d.tolerance_applied) },
    intrant_sous_seuil: { stock: qty(d.stock), threshold: qty(d.alert_threshold), unit: d.unit || '' },
    lot_trop_long: { days: qty(d.days), limit: qty(d.stale_days) },
    ecart_expedie_recu: { shipped: qty(d.qty_good), received: qty(d.received_good), gap: qty(d.gap) },
  }[a.kind];
  return params ? t(`fabrication.anomaly_detail_${a.kind}`, params) : '';
};

const openBatch = (id) => router.push({ name: 'fabrication-lot', params: { id } });

let msgTimer = null;
const flash = (msg) => {
  pageMessage.value = msg;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { pageMessage.value = ''; }, 5000);
};
onBeforeUnmount(() => clearTimeout(msgTimer));

const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    const [summary, list] = await Promise.all([
      FabricationGateway.getSummary(),
      FabricationGateway.getAnomalies(),
    ]);
    recentBatches.value = summary?.recent_batches || [];
    counts.value = summary?.counts_by_status || {};
    anomaliesCount.value = summary?.anomalies_count ?? 0;
    anomalies.value = Array.isArray(list) ? list : [];
    if (canEditSettings.value) {
      const s = await FabricationGateway.getSettings();
      settingsForm.value = { tolerance_pct: s?.tolerance_pct ?? '', stale_days: s?.stale_days ?? '' };
    }
  } catch (err) {
    pageError.value = describeFabricationError(err, t('fabrication.error_load'));
    console.error('Chargement du suivi echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const saveSettings = async () => {
  if (!canEditSettings.value) return;
  settingsError.value = '';
  const tol = Number(settingsForm.value.tolerance_pct);
  const days = Number(settingsForm.value.stale_days);
  if (settingsForm.value.tolerance_pct === '' || !Number.isFinite(tol) || tol < 0 || tol > 100 || !/^\d+([.,]\d{1,2})?$/.test(String(settingsForm.value.tolerance_pct).trim())) {
    settingsError.value = t('fabrication.err_tolerance');
    return;
  }
  if (settingsForm.value.stale_days === '' || !Number.isInteger(days) || days <= 0 || days > 3650) {
    settingsError.value = t('fabrication.err_stale_days');
    return;
  }
  busy.value = true;
  try {
    const saved = await FabricationGateway.updateSettings({ tolerance_pct: tol, stale_days: days });
    settingsForm.value = { tolerance_pct: saved?.tolerance_pct ?? tol, stale_days: saved?.stale_days ?? days };
    flash(t('fabrication.settings_saved'));
    await load();
  } catch (err) {
    settingsError.value = describeFabricationError(err, t('fabrication.error_settings'));
    console.error('Enregistrement des reglages echoue :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(load);
</script>
