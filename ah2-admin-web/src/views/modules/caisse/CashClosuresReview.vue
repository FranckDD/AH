<!-- src/views/modules/caisse/CashClosuresReview.vue -->
<!-- Revue des clotures de caisse (promoteur et admin). LECTURE SEULE, sauf : decision des corrections en
     attente (promoteur/admin), gestion de la liste des modes (admin : libelle, actif, ordre ; jamais de
     creation) et, tant que la caisse n'a pas de depart, son initialisation par l'admin (avec confirmation).
     Les clotures automatiques (non declarees) et les ecarts sont dits par des MOTS, jamais par la seule couleur. -->
<template>
  <div class="grid w-full gap-6">
    <PageHeader :title="t('cashClosure.review_title')" :subtitle="t('cashClosure.review_subtitle')" />

    <p v-if="isAdmin && statusError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ statusError }}</p>

    <!-- Initialisation de la caisse : admin seulement, une seule fois -->
    <AppCard v-if="isAdmin && review.status && !review.status.configured" :title="t('cashClosure.review_start_title')">
      <form class="grid gap-4" @submit.prevent="onStartSubmit">
        <p class="text-base text-ink">{{ t('cashClosure.review_start_help') }}</p>
        <FormField id="start-opening" :label="t('cashClosure.review_start_label')" :help="t('cashClosure.amount_format_help')"
                   :error="openingCash !== '' && !normalizeAmount(openingCash) ? t('cashClosure.amount_invalid') : ''"
                   required v-slot="{ describedBy }">
          <input id="start-opening" v-model="openingCash" type="text" inputmode="decimal" autocomplete="off" required
                 :disabled="confirmingStart" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" placeholder="0" />
        </FormField>
        <div v-if="confirmingStart" role="alert" class="grid gap-3 rounded-control border p-4 text-base" :class="toneClasses('warning')">
          <p>{{ t('cashClosure.review_start_confirm', { amount: formatAmount(normalizeAmount(openingCash)) }) }}</p>
          <p class="font-semibold">{{ t('cashClosure.review_start_confirm_warning') }}</p>
        </div>
        <p v-if="startError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ startError }}</p>
        <div class="flex flex-wrap justify-end gap-3">
          <AppButton v-if="confirmingStart" type="button" variant="ghost" @click="confirmingStart = false">{{ t('cashClosure.review_cancel') }}</AppButton>
          <AppButton type="submit" :variant="confirmingStart ? 'danger' : 'brand'" :disabled="!normalizeAmount(openingCash) || review.busy" :loading="review.busy">
            {{ confirmingStart ? t('cashClosure.review_start_confirm_button') : t('cashClosure.review_start_button') }}
          </AppButton>
        </div>
      </form>
    </AppCard>

    <!-- Corrections en attente -->
    <AppCard :title="t('cashClosure.review_corrections_title')" :subtitle="t('cashClosure.review_corrections_help')">
      <p v-if="review.correctionsError" role="alert" class="text-base" :class="toneClasses('danger')">{{ t('cashClosure.review_corrections_error') }}</p>
      <p v-else-if="!review.corrections.length" class="text-base text-ink-muted">{{ t('cashClosure.review_corrections_empty') }}</p>
      <ul v-else class="grid gap-3">
        <li v-for="c in review.corrections" :key="c.id" class="grid gap-2 rounded-card border border-tone-neutral-border p-4 md:grid-cols-[1fr_auto] md:items-center">
          <div class="grid gap-1 text-base text-ink">
            <p class="font-semibold">{{ t('cashClosure.review_correction_line', { id: c.closure_id, mode: modeLabel(c.mode_code), amount: signedAmount(c.amount_delta) }) }}</p>
            <p>{{ t('cashClosure.review_correction_reason', { reason: c.reason }) }}</p>
            <p class="text-ink-muted">{{ t('cashClosure.review_correction_requested', { date: fmtDateTime(c.requested_at) }) }}</p>
          </div>
          <div class="flex flex-wrap gap-3">
            <AppButton type="button" variant="success" :disabled="review.busy" @click="decide(c.id, true)">{{ t('cashClosure.review_approve') }}</AppButton>
            <AppButton type="button" variant="danger" :disabled="review.busy" @click="decide(c.id, false)">{{ t('cashClosure.review_reject') }}</AppButton>
          </div>
        </li>
      </ul>
      <p v-if="decisionMessage" role="status" class="mt-3 rounded-control border p-3 text-base" :class="toneClasses(decisionTone)">{{ decisionMessage }}</p>
    </AppCard>

    <!-- Filtres et liste -->
    <AppCard :title="t('cashClosure.review_list_title')">
      <form class="grid gap-4 md:grid-cols-4 md:items-end" @submit.prevent="reload">
        <FormField id="ccr-from" :label="t('cashClosure.review_filter_from')" v-slot="{ describedBy }">
          <input id="ccr-from" v-model="dateFrom" type="date" :max="dateTo || undefined" :aria-describedby="describedBy" :class="fieldClass" @change="reload" />
        </FormField>
        <FormField id="ccr-to" :label="t('cashClosure.review_filter_to')" v-slot="{ describedBy }">
          <input id="ccr-to" v-model="dateTo" type="date" :min="dateFrom || undefined" :aria-describedby="describedBy" :class="fieldClass" @change="reload" />
        </FormField>
        <FormField id="ccr-kind" :label="t('cashClosure.review_filter_kind')" v-slot="{ describedBy }">
          <select id="ccr-kind" v-model="kind" :aria-describedby="describedBy" :class="fieldClass" @change="reload">
            <option value="">{{ t('cashClosure.review_kind_all') }}</option>
            <option value="manual">{{ t('cashClosure.review_kind_manual') }}</option>
            <option value="auto">{{ t('cashClosure.review_kind_auto') }}</option>
          </select>
        </FormField>
        <label for="ccr-gap" class="flex min-h-11 items-center gap-3 text-base text-ink">
          <input id="ccr-gap" v-model="onlyGap" type="checkbox" class="h-5 w-5 accent-brand-600" />
          {{ t('cashClosure.review_filter_gap') }}
        </label>
      </form>

      <p v-if="review.isLoading" role="status" class="mt-4 text-base text-ink-muted">{{ t('cashClosure.loading') }}</p>
      <p v-else-if="review.loadError" role="alert" class="mt-4 rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ t('cashClosure.review_load_error') }}</p>
      <p v-else-if="!visibleClosures.length" class="mt-4 text-base text-ink-muted">{{ t('cashClosure.review_empty') }}</p>
      <div v-else class="mt-4">
        <ResponsiveTable :columns="listColumns" :rows="visibleClosures" row-key="id" striped>
          <template #cell-date="{ row }">
            <span class="font-semibold">{{ fmtDay(row.business_date) }}</span>
            <span class="block text-sm text-ink-muted">{{ fmtDateTime(row.closed_at) }}</span>
          </template>
          <template #cell-kind="{ row }">
            <StatusBadge v-if="closureFlags(row).undeclared" tone="warning" :label="t('cashClosure.review_badge_undeclared')" />
            <StatusBadge v-else tone="info" :label="t('cashClosure.review_badge_manual')" />
          </template>
          <template #cell-gap="{ row }">
            <StatusBadge :tone="gapTone(row.difference)" :label="gapText(row.difference)" />
            <StatusBadge v-if="closureFlags(row).withGap && row.difference !== null && Number(row.difference) === 0" class="ml-2" tone="danger" :label="t('cashClosure.review_badge_other_gap')" />
            <StatusBadge v-if="closureFlags(row).commentMissing" class="ml-2" tone="danger" :label="t('cashClosure.review_comment_missing')" />
          </template>
          <template #cell-actions="{ row }">
            <AppButton type="button" variant="secondary" :aria-pressed="review.selected?.id === row.id" @click="review.select(row)">
              {{ t('cashClosure.review_view') }}
            </AppButton>
          </template>
        </ResponsiveTable>
      </div>
    </AppCard>

    <!-- Detail d'une cloture -->
    <AppCard v-if="review.selected" :title="t('cashClosure.review_detail_title', { date: fmtDay(review.selected.business_date) })" :subtitle="detailSubtitle">
      <div class="mb-4 flex flex-wrap gap-2">
        <StatusBadge v-if="selectedFlags.undeclared" tone="warning" :label="t('cashClosure.review_badge_undeclared')" />
        <StatusBadge v-else tone="info" :label="t('cashClosure.review_badge_manual')" />
        <StatusBadge v-if="selectedFlags.commentMissing" tone="danger" :label="t('cashClosure.review_comment_missing')" />
      </div>
      <p v-if="selectedFlags.undeclared" class="mb-4 text-base text-ink">{{ t('cashClosure.review_undeclared_help') }}</p>
      <ResponsiveTable :columns="detailColumns" :rows="review.selected.lines" row-key="mode" striped>
        <template #cell-mode="{ row }"><span class="font-semibold">{{ modeLabel(row.mode) }}</span></template>
        <template #cell-opening="{ row }">{{ row.mode === CASH_MODE ? formatAmount(row.opening) : t('cashClosure.not_applicable') }}</template>
        <template #cell-entries="{ row }">{{ formatAmount(row.entries) }}</template>
        <template #cell-exits="{ row }">{{ formatAmount(row.exits) }}</template>
        <template #cell-expected="{ row }">{{ formatAmount(row.expected) }}</template>
        <template #cell-counted="{ row }">{{ row.counted === null ? t('cashClosure.gap_not_counted') : formatAmount(row.counted) }}</template>
        <template #cell-gap="{ row }"><StatusBadge :tone="gapTone(row.difference)" :label="gapText(row.difference)" /></template>
        <template #cell-comment="{ row }">
          <StatusBadge v-if="row.comment_missing" tone="danger" :label="t('cashClosure.review_comment_missing')" />
          <span v-else>{{ row.comment || '' }}</span>
        </template>
      </ResponsiveTable>
      <p v-if="review.selected.opening_from_auto" class="mt-3 text-base text-ink-muted">{{ t('cashClosure.opening_from_auto') }}</p>
      <p v-if="review.selected.unsynced_ignored" class="mt-3 text-base text-ink-muted">{{ t('cashClosure.review_unsynced_ignored') }}</p>
      <section class="mt-5 grid gap-2" :aria-label="t('cashClosure.cancellations_title')">
        <h3 class="text-base font-semibold text-ink">{{ t('cashClosure.cancellations_title') }}</h3>
        <p v-if="!cancellations.length" class="text-base text-ink-muted">{{ t('cashClosure.cancellations_empty') }}</p>
        <ResponsiveTable v-else :columns="cancelColumns" :rows="cancellations" row-key="key" striped>
          <template #cell-amount="{ row }">{{ formatAmount(row.amount) }}</template>
        </ResponsiveTable>
      </section>
      <section class="mt-5 grid gap-2" :aria-label="t('cashClosure.applied_title')">
        <h3 class="text-base font-semibold text-ink">{{ t('cashClosure.applied_title') }}</h3>
        <p v-if="!appliedCorrections.length" class="text-base text-ink-muted">{{ t('cashClosure.applied_empty') }}</p>
        <ResponsiveTable v-else :columns="appliedColumns" :rows="appliedCorrections" row-key="key" striped>
          <template #cell-mode="{ row }">{{ modeLabel(row.mode) }}</template>
          <template #cell-amount="{ row }">{{ appliedDeltaText(row.amount) }}</template>
        </ResponsiveTable>
      </section>
      <div class="mt-4 flex justify-end">
        <AppButton type="button" variant="ghost" @click="review.select(null)">{{ t('cashClosure.review_close_detail') }}</AppButton>
      </div>
    </AppCard>

    <!-- Modes de paiement : admin seulement ; la liste officielle est fixe (aucune creation) -->
    <AppCard v-if="isAdmin" :title="t('cashClosure.review_modes_title')" :subtitle="t('cashClosure.review_modes_help')">
      <p v-if="modesError" role="alert" class="mb-3 rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modesError }}</p>
      <ul class="grid gap-3">
        <li v-for="m in review.modes" :key="m.code" class="grid gap-3 rounded-card border border-tone-neutral-border p-4 md:grid-cols-[2fr_1fr_auto_auto] md:items-end">
          <FormField :id="`mode-label-${m.code}`" :label="t('cashClosure.review_mode_label', { code: m.code })" v-slot="{ describedBy }">
            <input :id="`mode-label-${m.code}`" v-model="modeForm[m.code].label" type="text" maxlength="100"
                   :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField :id="`mode-order-${m.code}`" :label="t('cashClosure.review_mode_order')" v-slot="{ describedBy }">
            <input :id="`mode-order-${m.code}`" v-model.number="modeForm[m.code].sort_order" type="number" step="1"
                   :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <div class="grid gap-1">
            <label :for="`mode-active-${m.code}`" class="flex min-h-11 items-center gap-3 text-base text-ink">
              <input :id="`mode-active-${m.code}`" v-model="modeForm[m.code].is_active" type="checkbox" class="h-5 w-5 accent-brand-600"
                     :disabled="!canDeactivateMode(m.code)" :aria-describedby="!canDeactivateMode(m.code) ? `mode-lock-${m.code}` : undefined" />
              {{ modeForm[m.code].is_active ? t('cashClosure.review_mode_active') : t('cashClosure.review_mode_inactive') }}
            </label>
            <p v-if="!canDeactivateMode(m.code)" :id="`mode-lock-${m.code}`" class="text-sm text-ink-muted">{{ t('cashClosure.review_mode_cash_locked') }}</p>
          </div>
          <AppButton type="button" variant="info" :disabled="review.busy || !modeChanged(m)" @click="saveMode(m)">{{ t('cashClosure.review_mode_save') }}</AppButton>
        </li>
      </ul>
      <p v-if="modesMessage" role="status" class="mt-3 rounded-control border p-3 text-base" :class="toneClasses('success')">{{ modesMessage }}</p>
    </AppCard>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, AppCard, PageHeader, FormField, ResponsiveTable, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import { useCashClosureReviewStore } from '@/stores/cashClosureStore';
import { modeLabel, CASH_MODE } from '@/utils/paymentModes';
import { gapWords, normalizeAmount, localDateISO, closureFlags, canDeactivateMode, formatAmountFcfa,
  closureCancellations, closureAppliedCorrections } from '@/utils/cashClosure';
import { describeServerError } from '@/utils/serverError';

const { t } = useI18n();
const review = useCashClosureReviewStore();
const auth = useAuthStore();
const isAdmin = computed(() => auth.hasRole(['admin']));

const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600 disabled:bg-tone-neutral-bg';

// ---------- filtres (dates LOCALES : 30 derniers jours par defaut) ----------
const today = new Date();
const monthAgo = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30);
const dateFrom = ref(localDateISO(monthAgo));
const dateTo = ref(localDateISO(today));
const kind = ref('');
const onlyGap = ref(false);

function reload() {
  if (dateFrom.value && dateTo.value && dateFrom.value > dateTo.value) return;
  review.load({ dateFrom: dateFrom.value, dateTo: dateTo.value, kind: kind.value });
}

const visibleClosures = computed(() => (onlyGap.value
  ? review.closures.filter((c) => closureFlags(c).withGap)
  : review.closures));
const selectedFlags = computed(() => closureFlags(review.selected));

// ---------- formats ----------
const formatAmount = formatAmountFcfa;
// Annulations de la periode et regularisations appliquees (sections du detail).
const cancellations = computed(() => closureCancellations(review.selected));
const appliedCorrections = computed(() => closureAppliedCorrections(review.selected));
const cancelColumns = computed(() => [
  { key: 'reference', label: t('cashClosure.cancel_col_reference') },
  { key: 'author', label: t('cashClosure.cancel_col_author') },
  { key: 'amount', label: t('cashClosure.cancel_col_amount'), align: 'right' },
  { key: 'justification', label: t('cashClosure.cancel_col_justification') },
]);
const appliedColumns = computed(() => [
  { key: 'mode', label: t('cashClosure.col_mode') },
  { key: 'amount', label: t('cashClosure.applied_col_amount'), align: 'right' },
  { key: 'reason', label: t('cashClosure.applied_col_reason') },
]);
const appliedDeltaText = (v) => {
  const s = String(v ?? '').trim();
  if (!s) return '';
  return s.startsWith('-') ? t('cashClosure.applied_minus', { amount: formatAmount(s.slice(1)) })
    : t('cashClosure.applied_plus', { amount: formatAmount(s.replace(/^\+/, '')) });
};
const signedAmount = (s) => {
  const str = String(s ?? '');
  return str.startsWith('-') ? t('cashClosure.review_delta_minus', { amount: formatAmount(str.slice(1)) })
    : t('cashClosure.review_delta_plus', { amount: formatAmount(str) });
};
const fmtDateTime = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '');
// business_date AAAA-MM-JJ : lue comme date locale (new Date('AAAA-MM-JJ') serait minuit UTC)
const fmtDay = (ymd) => {
  if (!ymd) return '';
  const [y, m, d] = String(ymd).slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
};
const gapText = (difference) => {
  const g = gapWords(difference);
  return t(g.key, { amount: g.amount === null ? '' : formatAmount(g.amount) });
};
const gapTone = (difference) => {
  const g = gapWords(difference);
  if (g.key === 'cashClosure.gap_none') return 'success';
  if (g.key === 'cashClosure.gap_not_counted') return 'neutral';
  return 'danger';
};
const detailSubtitle = computed(() => (review.selected
  ? t('cashClosure.period', { start: fmtDateTime(review.selected.period_start), end: fmtDateTime(review.selected.period_end) })
  : ''));

const listColumns = computed(() => [
  { key: 'date', label: t('cashClosure.review_col_date') },
  { key: 'kind', label: t('cashClosure.review_col_kind') },
  { key: 'gap', label: t('cashClosure.review_col_cash_gap') },
  { key: 'actions', label: t('cashClosure.review_col_actions') },
]);
const detailColumns = computed(() => [
  { key: 'mode', label: t('cashClosure.col_mode') },
  { key: 'opening', label: t('cashClosure.col_opening'), align: 'right' },
  { key: 'entries', label: t('cashClosure.col_entries'), align: 'right' },
  { key: 'exits', label: t('cashClosure.col_exits'), align: 'right' },
  { key: 'expected', label: t('cashClosure.col_expected'), align: 'right' },
  { key: 'counted', label: t('cashClosure.col_counted'), align: 'right' },
  { key: 'gap', label: t('cashClosure.col_gap') },
  { key: 'comment', label: t('cashClosure.col_comment') },
]);

// ---------- corrections ----------
const decisionMessage = ref('');
const decisionTone = ref('success');
async function decide(id, approve) {
  decisionMessage.value = '';
  try {
    await review.decide(id, approve);
    decisionTone.value = 'success';
    decisionMessage.value = approve ? t('cashClosure.review_approved') : t('cashClosure.review_rejected');
  } catch (err) {
    decisionTone.value = 'danger';
    decisionMessage.value = describeServerError(err, t('cashClosure.review_decide_error'));
    await review.loadCorrections();
  }
}

// ---------- modes (admin) ----------
const modeForm = reactive({});
const modesError = ref('');
const modesMessage = ref('');
watch(() => review.modes, (rows) => {
  for (const k of Object.keys(modeForm)) delete modeForm[k];
  for (const m of rows) modeForm[m.code] = { label: m.label, is_active: m.is_active, sort_order: m.sort_order };
}, { immediate: true });

function modeChanged(m) {
  const f = modeForm[m.code];
  return !!f && (f.label.trim() !== m.label || f.is_active !== m.is_active || f.sort_order !== m.sort_order);
}

async function saveMode(m) {
  modesError.value = '';
  modesMessage.value = '';
  const f = modeForm[m.code];
  if (!f.label.trim()) { modesError.value = t('cashClosure.review_mode_label_empty'); return; }
  const data = {};
  if (f.label.trim() !== m.label) data.label = f.label.trim();
  if (f.is_active !== m.is_active) data.is_active = f.is_active;
  if (f.sort_order !== m.sort_order) {
    if (!Number.isInteger(f.sort_order)) { modesError.value = t('cashClosure.review_mode_order_invalid'); return; }
    data.sort_order = f.sort_order;
  }
  if (!canDeactivateMode(m.code)) delete data.is_active;
  if (!Object.keys(data).length) return;
  try {
    await review.updateMode(m.code, data);
    modesMessage.value = t('cashClosure.review_mode_saved', { mode: f.label.trim() || m.code });
  } catch (err) {
    modesError.value = describeServerError(err, t('cashClosure.review_mode_error'));
  }
}

// ---------- initialisation (admin, une fois) ----------
const openingCash = ref('');
const confirmingStart = ref(false);
const startError = ref('');
const statusError = ref('');
async function onStartSubmit() {
  startError.value = '';
  const amount = normalizeAmount(openingCash.value);
  if (!amount) return;
  if (!confirmingStart.value) { confirmingStart.value = true; return; }
  try {
    await review.start(amount);
    confirmingStart.value = false;
  } catch (err) {
    startError.value = describeServerError(err, t('cashClosure.review_start_error'));
    confirmingStart.value = false;
    try { await review.loadStatus(); } catch { /* le message d'erreur suffit */ }
  }
}

onMounted(async () => {
  reload();
  review.loadCorrections();
  if (isAdmin.value) {
    try { await review.loadStatus(); } catch (err) {
      console.error('Statut de caisse indisponible:', err);
      statusError.value = describeServerError(err, t('cashClosure.review_status_error'));
    }
    try { await review.loadModes(); } catch (err) { modesError.value = describeServerError(err, t('cashClosure.review_mode_error')); }
  }
});
</script>
