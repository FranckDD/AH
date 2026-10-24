<!-- src/views/modules/caisse/CashClosure.vue -->
<!-- Cloture de caisse de la secretaire, A L'AVEUGLE : elle compte les especes et recopie le total du releve de
     chaque operateur mobile SANS voir aucun total du systeme. Le serveur ne revele l'attendu et les ecarts
     qu'apres la validation (section du resultat). En ligne seulement, file d'envoi PowerSync vide. -->
<template>
  <div class="grid w-full gap-6">
    <PageHeader :title="t('cashClosure.title')" :subtitle="t('cashClosure.subtitle')">
      <template #actions>
        <router-link to="/secretariat/caisse" :class="linkClass">{{ t('cashClosure.sales_link') }}</router-link>
      </template>
    </PageHeader>

    <p v-if="store.isLoading" role="status" class="text-base text-ink-muted">{{ t('cashClosure.loading') }}</p>
    <p v-if="store.loadError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">
      {{ t('cashClosure.load_error') }}
    </p>
    <p v-if="info" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('warning')">{{ info }}</p>

    <!-- Caisse non initialisee : l'administrateur fixe le depart, la secretaire n'a rien a saisir. -->
    <AppCard v-if="store.status && !store.status.configured" :title="t('cashClosure.not_configured_title')">
      <p class="text-base text-ink">{{ t('cashClosure.not_configured_message') }}</p>
    </AppCard>

    <!-- Comptage a l'aveugle : aucun total du systeme ici. -->
    <AppCard v-else-if="store.status && !store.result" :title="t('cashClosure.form_title')" :subtitle="lastClosedText">
      <form id="cash-closure-form" class="grid gap-5" @submit.prevent="handleSubmit">
        <p class="text-base text-ink-muted">{{ t('cashClosure.form_help') }}</p>

        <fieldset v-for="m in store.status.modes" :key="m.code" class="grid gap-3 rounded-card border border-tone-neutral-border p-4 md:grid-cols-2">
          <legend class="px-1 text-base font-semibold text-ink">{{ modeLabel(m.code) }}</legend>
          <FormField :id="`count-${m.code}`" :label="m.source === 'physical' ? t('cashClosure.field_cash') : t('cashClosure.field_operator', { mode: modeLabel(m.code) })"
                     :help="`${m.source === 'physical' ? t('cashClosure.field_cash_help') : t('cashClosure.field_operator_help')} ${t('cashClosure.amount_format_help')}`"
                     :error="form[m.code].counted !== '' && !normalizeAmount(form[m.code].counted) ? t('cashClosure.amount_invalid') : ''"
                     required v-slot="{ describedBy }">
            <input :id="`count-${m.code}`" v-model="form[m.code].counted" type="text" inputmode="decimal" autocomplete="off" required
                   :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" placeholder="0" />
          </FormField>
          <FormField :id="`comment-${m.code}`" :label="t('cashClosure.comment_label')"
                     :help="requiredComments.has(m.code) ? t('cashClosure.comment_required_help') : t('cashClosure.comment_help')"
                     :required="requiredComments.has(m.code)" v-slot="{ describedBy }">
            <textarea :id="`comment-${m.code}`" v-model="form[m.code].comment" rows="2" :required="requiredComments.has(m.code)"
                      :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
          </FormField>
        </fieldset>

        <p v-if="formError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ formError }}</p>
        <p v-if="blockReason" role="status" class="rounded-control border p-3 text-base" :class="toneClasses('warning')">
          {{ t(blockReason, { n: pending }) }}
        </p>
        <p v-else-if="missingComments.length" role="status" class="rounded-control border p-3 text-base" :class="toneClasses('warning')">
          {{ t('cashClosure.blocked_comments', { modes: missingComments.map(modeLabel).join(', ') }) }}
        </p>
        <p v-else-if="!amountsValid" role="status" class="text-base text-ink-muted">{{ t('cashClosure.blocked_amounts') }}</p>

        <div class="flex justify-end">
          <AppButton type="submit" variant="primary" :disabled="!canSubmit" :loading="store.isSubmitting">
            {{ store.isSubmitting ? t('cashClosure.submitting') : t('cashClosure.submit') }}
          </AppButton>
        </div>
      </form>
    </AppCard>

    <!-- Resultat revele par le serveur apres la validation : seul endroit ou l'attendu est lu. -->
    <section v-if="store.result" class="grid gap-4" :aria-label="t('cashClosure.result_title')">
      <p role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ t('cashClosure.success') }}</p>
      <AppCard :title="t('cashClosure.result_title')" :subtitle="periodText">
        <ResponsiveTable :columns="resultColumns" :rows="store.result.lines" row-key="mode" striped>
          <template #cell-mode="{ row }"><span class="font-semibold">{{ modeLabel(row.mode) }}</span></template>
          <template #cell-opening="{ row }">{{ row.mode === CASH_MODE ? formatAmount(row.opening) : t('cashClosure.not_applicable') }}</template>
          <template #cell-entries="{ row }">{{ formatAmount(row.entries) }}</template>
          <template #cell-exits="{ row }">{{ formatAmount(row.exits) }}</template>
          <template #cell-expected="{ row }">{{ formatAmount(row.expected) }}</template>
          <template #cell-counted="{ row }">{{ row.counted === null ? t('cashClosure.gap_not_counted') : formatAmount(row.counted) }}</template>
          <template #cell-gap="{ row }">
            <StatusBadge :tone="gapTone(row.difference)" :label="gapText(row.difference)" />
          </template>
          <template #cell-comment="{ row }">{{ row.comment || '' }}</template>
        </ResponsiveTable>
        <p v-if="store.result.opening_from_auto" class="mt-3 text-base text-ink-muted">{{ t('cashClosure.opening_from_auto') }}</p>
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
      </AppCard>
      <!-- Demande de regularisation (decidee ensuite par le promoteur ou l'administrateur). -->
      <AppCard :title="t('cashClosure.correction_title')">
        <template #actions>
          <AppButton variant="secondary" :aria-expanded="showCorrection ? 'true' : 'false'" aria-controls="cash-correction-form"
                     @click="showCorrection = !showCorrection">
            {{ showCorrection ? t('cashClosure.correction_hide') : t('cashClosure.correction_toggle') }}
          </AppButton>
        </template>
        <p class="text-base text-ink-muted">{{ t('cashClosure.correction_help') }}</p>
        <form v-if="showCorrection" id="cash-correction-form" class="mt-4 grid gap-4 md:grid-cols-2" @submit.prevent="handleCorrection">
          <FormField id="correction-mode" :label="t('cashClosure.correction_mode')" required v-slot="{ describedBy }">
            <select id="correction-mode" v-model="correction.modeCode" required :aria-describedby="describedBy" :class="fieldClass">
              <option value="" disabled>{{ t('cashClosure.correction_mode_placeholder') }}</option>
              <option v-for="l in store.result.lines" :key="l.mode" :value="l.mode">{{ modeLabel(l.mode) }}</option>
            </select>
          </FormField>
          <FormField id="correction-amount" :label="t('cashClosure.correction_amount')" :help="t('cashClosure.correction_amount_help')"
                     :error="correction.amount !== '' && !normalizeSignedAmount(correction.amount) ? t('cashClosure.correction_amount_invalid') : ''"
                     required v-slot="{ describedBy }">
            <input id="correction-amount" v-model="correction.amount" type="text" inputmode="decimal" autocomplete="off" required
                   :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" placeholder="0" />
          </FormField>
          <div class="md:col-span-2">
            <FormField id="correction-reason" :label="t('cashClosure.correction_reason')" required v-slot="{ describedBy }">
              <textarea id="correction-reason" v-model="correction.reason" rows="2" required
                        :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
            </FormField>
          </div>
          <p v-if="correctionError" role="alert" class="rounded-control border p-3 text-base md:col-span-2" :class="toneClasses('danger')">{{ correctionError }}</p>
          <div class="flex justify-end md:col-span-2">
            <AppButton type="submit" variant="info" :disabled="!canRequestCorrection" :loading="correctionSending">
              {{ correctionSending ? t('cashClosure.correction_submitting') : t('cashClosure.correction_submit') }}
            </AppButton>
          </div>
        </form>
        <p v-if="correctionDone" role="status" class="mt-4 rounded-control border p-3 text-base" :class="toneClasses('success')">{{ correctionDone }}</p>
      </AppCard>

      <div class="flex flex-wrap justify-end gap-3">
        <router-link to="/secretariat/caisse" :class="linkClass">{{ t('cashClosure.sales_link') }}</router-link>
        <router-link to="/secretariat/" :class="linkClass">{{ t('cashClosure.done') }}</router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, AppCard, PageHeader, FormField, ResponsiveTable, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { useCashClosureStore } from '@/stores/cashClosureStore';
import { useConnectionStatus } from '@/composables/useConnectionStatus';
import { db } from '@/powersync-client/client';
import { modeLabel, CASH_MODE } from '@/utils/paymentModes';
import { queueBlockReason, commentRequiredMode, normalizeAmount, normalizeSignedAmount, buildCounts, gapWords,
  closureCancellations, closureAppliedCorrections } from '@/utils/cashClosure';
import { describeServerError } from '@/utils/serverError';

const { t } = useI18n();
const store = useCashClosureStore();
const { state, pending } = useConnectionStatus();

const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const linkClass = 'inline-flex min-h-11 items-center rounded-control border border-tone-neutral-border bg-white px-4 text-base font-medium text-brand-700 hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Saisie par mode : { [code]: { counted, comment } }. Recree a chaque nouveau statut.
const form = reactive({});
const requiredComments = ref(new Set());
const formError = ref('');
const info = ref('');

function resetForm() {
  for (const k of Object.keys(form)) delete form[k];
  for (const m of store.status?.modes || []) form[m.code] = { counted: '', comment: '' };
  requiredComments.value = new Set();
}
watch(() => store.status, resetForm, { immediate: true });

onMounted(() => { store.load(); });

const blockReason = computed(() => queueBlockReason({ state: state.value, pending: pending.value }));
const amountsValid = computed(() => (store.status?.modes || []).every((m) => normalizeAmount(form[m.code]?.counted) !== null));
const missingComments = computed(() => [...requiredComments.value].filter((code) => form[code] && !form[code].comment.trim()));
const canSubmit = computed(() => !blockReason.value && amountsValid.value && missingComments.value.length === 0 && !store.isSubmitting && !submitting.value);

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '');
const lastClosedText = computed(() => (store.status?.last_closed_at
  ? t('cashClosure.last_closed', { date: fmtDate(store.status.last_closed_at) })
  : t('cashClosure.never_closed')));
const periodText = computed(() => (store.result
  ? t('cashClosure.period', { start: fmtDate(store.result.period_start), end: fmtDate(store.result.period_end) })
  : ''));

const formatAmount = (s) => (s === null || s === undefined ? '' : `${Number(s).toLocaleString('fr-FR')} FCFA`);
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

// Annulations de la periode et regularisations appliquees (sections du detail).
const cancellations = computed(() => closureCancellations(store.result));
const appliedCorrections = computed(() => closureAppliedCorrections(store.result));
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

const resultColumns = computed(() => [
  { key: 'mode', label: t('cashClosure.col_mode') },
  { key: 'opening', label: t('cashClosure.col_opening'), align: 'right' },
  { key: 'entries', label: t('cashClosure.col_entries'), align: 'right' },
  { key: 'exits', label: t('cashClosure.col_exits'), align: 'right' },
  { key: 'expected', label: t('cashClosure.col_expected'), align: 'right' },
  { key: 'counted', label: t('cashClosure.col_counted'), align: 'right' },
  { key: 'gap', label: t('cashClosure.col_gap') },
  { key: 'comment', label: t('cashClosure.col_comment') },
]);

// Verrou synchrone : pose AVANT toute attente (la lecture de la file est asynchrone), sinon un double clic
// envoie deux POST et le 409 du second effacerait le resultat revele du premier.
const submitting = ref(false);

// ---- demande de regularisation (apres la validation) ----
const showCorrection = ref(false);
const correction = reactive({ modeCode: '', amount: '', reason: '' });
const correctionError = ref('');
const correctionDone = ref('');
// Verrou synchrone : un double clic n'envoie qu'une demande.
const correctionSending = ref(false);
const canRequestCorrection = computed(() => !!correction.modeCode && normalizeSignedAmount(correction.amount) !== null
  && correction.reason.trim().length > 0 && !correctionSending.value);

async function handleCorrection() {
  if (correctionSending.value || !canRequestCorrection.value) return;
  correctionSending.value = true;
  correctionError.value = '';
  correctionDone.value = '';
  try {
    await store.requestCorrection({
      modeCode: correction.modeCode,
      amountDelta: normalizeSignedAmount(correction.amount),
      reason: correction.reason.trim(),
    });
    correctionDone.value = t('cashClosure.correction_success');
    correction.modeCode = '';
    correction.amount = '';
    correction.reason = '';
    showCorrection.value = false;
  } catch (err) {
    correctionError.value = err?.response
      ? (describeServerError(err, '') || t('cashClosure.correction_error'))
      : t('cashClosure.network_error');
  } finally {
    correctionSending.value = false;
  }
}

async function handleSubmit() {
  if (submitting.value) return;
  formError.value = '';
  info.value = '';
  if (!canSubmit.value) return;
  submitting.value = true;
  try {
    await doSubmit();
  } finally {
    submitting.value = false;
  }
}

async function doSubmit() {
  // La file peut avoir change depuis la derniere lecture (rafraichie toutes les 5 s) : relue juste avant l'envoi.
  try {
    const stats = await db.getUploadQueueStats();
    if ((stats?.count ?? 0) > 0) {
      formError.value = t('cashClosure.blocked_pending', { n: stats.count });
      return;
    }
  } catch {
    formError.value = t('cashClosure.blocked_queue_unknown');
    return;
  }
  try {
    await store.submit(buildCounts(store.status.modes, form));
  } catch (err) {
    const code = err?.response?.status;
    const detail = describeServerError(err, '');
    if (code === 409) {
      // autre cloture validee entre-temps (autre onglet, cloture automatique) : statut recharge par le store
      info.value = t('cashClosure.conflict_refreshed', { detail });
    } else if (code === 422) {
      const mode = commentRequiredMode(err.response.data?.detail);
      if (mode) {
        requiredComments.value = new Set([...requiredComments.value, mode]);
        formError.value = t('cashClosure.comment_required_step', { mode: modeLabel(mode) });
      } else {
        formError.value = detail || t('cashClosure.submit_error');
      }
    } else if (!err?.response) {
      formError.value = t('cashClosure.network_error');
    } else {
      formError.value = detail || t('cashClosure.submit_error');
    }
  }
}
</script>
