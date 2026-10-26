<!-- src/views/modules/fabrication/FabLotDetail.vue -->
<!-- Fiche d'un lot de fabrication. Lecture : ProductionManager, promoteur, admin. Toute action : ProductionManager seul.
     Le bilan (attendu, retrouve, manque, hors tolerance) et le cout viennent du serveur : jamais recalcules ici. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="batch ? batch.batch_number : t('fabrication.batch_title')" :subtitle="t('fabrication.batch_subtitle')">
      <template #actions>
        <AppButton variant="ghost" :icon="ArrowLeftIcon" @click="router.push('/dashboard/fabrication-lots')">{{ t('fabrication.back_to_lots') }}</AppButton>
      </template>
    </PageHeader>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="isLoading" role="status" class="text-base text-ink-muted">{{ t('stockOps.loading') }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <template v-if="batch">
      <!-- En-tete -->
      <AppCard>
        <dl class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div><dt class="text-sm text-ink-muted">{{ t('fabrication.col_batch_number') }}</dt><dd class="text-base font-semibold text-ink">{{ batch.batch_number }}</dd></div>
          <div><dt class="text-sm text-ink-muted">{{ t('fabrication.col_product') }}</dt><dd class="text-base text-ink">{{ batch.product_name || '-' }}</dd></div>
          <div><dt class="text-sm text-ink-muted">{{ t('fabrication.production_date') }}</dt><dd class="text-base text-ink">{{ formatDate(batch.production_date) }}</dd></div>
          <div><dt class="text-sm text-ink-muted">{{ t('fabrication.producer') }}</dt><dd class="text-base text-ink">{{ batch.producer_name || '-' }}</dd></div>
          <div>
            <dt class="text-sm text-ink-muted">{{ t('fabrication.col_status') }}</dt>
            <dd class="flex flex-wrap gap-2">
              <StatusBadge :tone="STATUS_TONES[batch.status] || 'neutral'" :label="t(`fabrication.batch_status_${batch.status}`)" />
            </dd>
          </div>
        </dl>
        <p v-if="batch.status === 'annule' && batch.cancel_reason" class="mt-4 text-base text-ink">{{ t('fabrication.cancel_reason') }} : {{ batch.cancel_reason }}</p>
        <p v-if="batch.production_lot_number" class="mt-4 text-base text-ink">{{ t('fabrication.linked_lot') }} : <span class="font-semibold">{{ batch.production_lot_number }}</span></p>
      </AppCard>

      <!-- Consommations -->
      <AppCard :title="t('fabrication.consumptions_title')">
        <ResponsiveTable
          :columns="consumptionColumns"
          :rows="batch.consumptions || []"
          row-key="id"
          :empty-title="t('fabrication.no_consumptions')"
          :empty-message="' '"
          striped
        >
          <template #cell-intrant="{ row: c }">
            <span class="font-medium text-ink">{{ c.intrant_name }}</span>
            <StatusBadge v-if="c.is_container" class="ml-2" tone="info" :label="t('fabrication.container_tag')" />
          </template>
          <template #cell-quantity="{ row: c }">{{ qty(c.quantity) }} {{ c.unit }}</template>
          <template #cell-provenance="{ row: c }">{{ c.supplier || '-' }}, {{ formatDate(c.purchase_date) }}</template>
          <template #cell-line_cost="{ row: c }">{{ formatCurrency(c.line_cost) }}</template>
        </ResponsiveTable>
        <p class="mt-3 text-right text-base text-ink">{{ t('fabrication.cost_so_far') }} : <span class="font-semibold">{{ formatCurrency(batch.cost_so_far) }}</span></p>

        <!-- Editeur (brouillon seulement) -->
        <div v-if="canWrite && batch.status === 'brouillon'" class="mt-6 grid gap-4 border-t border-tone-neutral-border pt-4">
          <h3 class="text-base font-semibold text-ink">{{ t('fabrication.edit_consumptions') }}</h3>
          <p class="text-base text-ink-muted">{{ t('fabrication.edit_consumptions_help') }}</p>
          <div v-for="(d, idx) in draft" :key="idx" class="grid items-end gap-3 sm:grid-cols-[1fr_10rem_auto]">
            <FormField :id="`fab-draft-purchase-${idx}`" :label="t('fabrication.purchase_label')" v-slot="{ describedBy }">
              <select :id="`fab-draft-purchase-${idx}`" v-model="d.purchase_id" :aria-describedby="describedBy" :class="fieldClass">
                <option :value="null" disabled>{{ t('fabrication.choose_purchase') }}</option>
                <option v-for="p in availablePurchases" :key="p.id" :value="p.id">{{ purchaseLabel(p) }}</option>
              </select>
            </FormField>
            <FormField :id="`fab-draft-qty-${idx}`" :label="t('fabrication.quantity')" v-slot="{ describedBy }">
              <input :id="`fab-draft-qty-${idx}`" v-model="d.quantity" type="text" inputmode="decimal" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
            </FormField>
            <AppButton variant="ghost" :icon="TrashIcon" @click="draft.splice(idx, 1)">{{ t('fabrication.remove_line') }}</AppButton>
          </div>
          <div class="flex flex-wrap gap-3">
            <AppButton variant="secondary" :icon="PlusIcon" @click="draft.push({ purchase_id: null, quantity: '' })">{{ t('fabrication.add_line') }}</AppButton>
          </div>
        </div>
      </AppCard>

      <!-- Resultats -->
      <AppCard v-if="hasResults" :title="t('fabrication.results_title')">
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile :title="t('fabrication.qty_good')" :value="batch.qty_good" tone="success" />
          <StatTile :title="t('fabrication.qty_damaged')" :value="batch.qty_damaged" tone="warning" />
          <StatTile :title="t('fabrication.qty_rejected')" :value="batch.qty_rejected" tone="warning" />
          <StatTile :title="t('fabrication.liquid_lost')" :value="qty(batch.liquid_lost)" tone="neutral" />
        </div>
      </AppCard>

      <!-- Bilan -->
      <AppCard v-if="hasResults && batch.expected_qty != null" :title="t('fabrication.bilan_title')">
        <div class="mb-4 flex flex-wrap gap-2">
          <StatusBadge v-if="batch.out_of_tolerance" tone="danger" :label="t('fabrication.out_of_tolerance')" />
          <StatusBadge v-else tone="success" :label="t('fabrication.within_tolerance')" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile :title="t('fabrication.expected')" :value="batch.expected_qty" />
          <StatTile :title="t('fabrication.found')" :value="batch.found_qty ?? '-'" />
          <StatTile :title="t('fabrication.missing')" :value="batch.missing_qty ?? '-'" :note="batch.missing_pct != null ? `${pct(batch.missing_pct)} %` : ''" :alert="batch.out_of_tolerance" :tone="batch.out_of_tolerance ? 'danger' : 'neutral'" />
          <StatTile :title="t('fabrication.tolerance')" :value="toleranceValue != null ? `${pct(toleranceValue)} %` : '-'" :note="batch.tolerance_applied != null ? t('fabrication.tolerance_frozen') : t('fabrication.tolerance_current')" />
        </div>
        <p v-if="batch.justification" class="mt-4 text-base text-ink">{{ t('fabrication.justification') }} : {{ batch.justification }}</p>
      </AppCard>

      <!-- Cout de revient -->
      <AppCard v-if="batch.total_cost != null" :title="t('fabrication.cost_title')">
        <div class="grid gap-4 sm:grid-cols-2">
          <StatTile :title="t('fabrication.total_cost')" :value="formatCurrency(batch.total_cost)" tone="success" />
          <StatTile v-if="batch.unit_cost != null" :title="t('fabrication.cost_per_bottle')" :value="formatUnitCost(batch.unit_cost)" tone="success" />
        </div>
      </AppCard>

      <!-- Sorties declarees (echantillons, autres). Bilan lu du serveur. Ecriture : ProductionManager, lot termine. -->
      <AppCard v-if="showOutputs" :title="t('fabrication.outputs.title')">
        <p class="mb-4 text-base font-semibold text-ink">{{ t('fabrication.outputs.bilan_line', { good: batch.qty_good, outputs: batch.qty_outputs, shipped: batch.qty_shipped }) }}</p>
        <p v-if="!(batch.outputs || []).length" class="text-base text-ink-muted">{{ t('fabrication.outputs.empty') }}</p>
        <ul v-else class="grid gap-3">
          <li v-for="o in batch.outputs" :key="o.id" class="grid gap-1 rounded-control border border-tone-neutral-border p-3" :class="o.status === 'annulee' ? 'bg-tone-neutral-bg text-ink-muted' : 'text-ink'">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-base font-semibold" :class="o.status === 'annulee' ? 'line-through' : ''">{{ t(`fabrication.outputs.reason.${o.reason}`) }}, {{ o.quantity }}</span>
              <StatusBadge v-if="o.status === 'annulee'" tone="neutral" :label="t('fabrication.outputs.status_annulee')" />
              <span class="ml-auto"></span>
              <AppButton v-if="canDeclare && o.status === 'active'" variant="ghost" :icon="XMarkIcon" :disabled="outputBusy" @click="openCancelOutput(o)">{{ t('fabrication.outputs.cancel') }}</AppButton>
            </div>
            <p v-if="o.note" class="text-base">{{ t('fabrication.outputs.note') }} : {{ o.note }}</p>
            <p class="text-sm">{{ t('fabrication.outputs.declared_by', { name: o.declared_by_name || '-', date: formatDateTime(o.declared_at) }) }}</p>
            <p v-if="o.status === 'annulee'" class="text-sm">{{ t('fabrication.outputs.cancelled_info', { date: formatDateTime(o.cancelled_at), reason: o.cancel_reason || '-' }) }}</p>
          </li>
        </ul>

        <p v-if="canDeclare && allBottlesOut" role="status" class="mt-6 border-t border-tone-neutral-border pt-4 text-base text-ink-muted">{{ t('fabrication.outputs.nothing_to_ship') }}</p>
        <form v-if="canDeclare && !nothingToShip" id="fab-output-form" @submit.prevent="confirmDeclareOutput" class="mt-6 grid gap-4 border-t border-tone-neutral-border pt-4">
          <h3 class="text-base font-semibold text-ink">{{ t('fabrication.outputs.form_title') }}</h3>
          <p v-if="outputError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ outputError }}</p>
          <div class="grid gap-4 sm:grid-cols-2">
            <FormField id="fab-output-reason" :label="t('fabrication.outputs.reason_label')" required v-slot="{ describedBy }">
              <select id="fab-output-reason" v-model="outputForm.reason" required :aria-describedby="describedBy" :class="fieldClass">
                <option value="" disabled>{{ t('fabrication.outputs.choose_reason') }}</option>
                <option value="echantillon">{{ t('fabrication.outputs.reason.echantillon') }}</option>
                <option value="autre">{{ t('fabrication.outputs.reason.autre') }}</option>
              </select>
            </FormField>
            <FormField id="fab-output-qty" :label="t('fabrication.outputs.quantity_label', { max: batch.qty_shipped })" required v-slot="{ describedBy }">
              <input id="fab-output-qty" v-model="outputForm.quantity" type="text" inputmode="numeric" required :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
            </FormField>
          </div>
          <FormField id="fab-output-note" :label="t('fabrication.outputs.note')" :required="outputForm.reason === 'autre'" v-slot="{ describedBy }">
            <textarea id="fab-output-note" v-model="outputForm.note" rows="2" maxlength="2000" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
          </FormField>
          <p v-if="outputForm.reason === 'autre'" class="text-base" :class="outputNoteMissing ? 'text-tone-danger-text' : 'text-ink-muted'">{{ t('fabrication.outputs.note_required_autre') }}</p>
          <p v-else-if="outputForm.reason === 'echantillon'" class="text-base text-ink-muted">{{ t('fabrication.outputs.note_hint_echantillon') }}</p>
          <div class="flex flex-wrap justify-end gap-3">
            <AppButton type="submit" variant="info" :icon="MinusCircleIcon" :disabled="outputBusy || outputBlocked" :loading="outputBusy">{{ t('fabrication.outputs.declare') }}</AppButton>
          </div>
        </form>
      </AppCard>

      <!-- Actions selon le statut (ProductionManager seul) -->
      <div v-if="canWrite && batch.status === 'brouillon'" class="flex flex-wrap justify-end gap-3">
        <AppButton variant="danger" :disabled="busy" @click="openCancel">{{ t('fabrication.cancel_batch') }}</AppButton>
        <AppButton variant="secondary" :icon="CheckIcon" :disabled="busy" :loading="busy" @click="saveDraft()">{{ t('fabrication.save_draft') }}</AppButton>
        <AppButton variant="info" :icon="PlayIcon" :disabled="busy" :loading="busy" @click="startBatch">{{ t('fabrication.start_batch') }}</AppButton>
      </div>
      <div v-if="canWrite && batch.status === 'en_production'" class="flex flex-wrap justify-end gap-3">
        <AppButton variant="danger" :disabled="busy" @click="openCancel">{{ t('fabrication.cancel_batch') }}</AppButton>
        <AppButton variant="brand" :icon="FlagIcon" :disabled="busy" @click="openFinish">{{ t('fabrication.finish_batch') }}</AppButton>
      </div>
      <div v-if="canWrite && batch.status === 'termine'" class="flex flex-wrap justify-end gap-3">
        <AppButton variant="danger" :disabled="busy" @click="openCancel">{{ t('fabrication.cancel_batch') }}</AppButton>
        <AppButton variant="secondary" :icon="ArrowUturnLeftIcon" :disabled="busy" :loading="busy" @click="reopenBatch">{{ t('fabrication.reopen_batch') }}</AppButton>
        <AppButton v-if="batch.qty_good > 0" variant="success" :icon="TruckIcon" :disabled="busy || nothingToShip" @click="openShip">{{ t('fabrication.ship_batch') }}</AppButton>
        <p v-if="allBottlesOut" role="status" class="basis-full text-right text-base text-ink-muted">{{ t('fabrication.outputs.nothing_to_ship') }}</p>
      </div>
    </template>

    <!-- Terminer : saisie des resultats -->
    <FullScreenPanel v-if="finishOpen" :title="t('fabrication.finish_title')" @close="finishOpen = false">
      <form id="fab-finish-form" @submit.prevent="confirmFinish" class="grid gap-4">
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="fab-finish-good" :label="t('fabrication.qty_good')" required v-slot="{ describedBy }">
            <input id="fab-finish-good" v-model="finishForm.qty_good" type="text" inputmode="numeric" required :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
          <FormField id="fab-finish-damaged" :label="t('fabrication.qty_damaged')" v-slot="{ describedBy }">
            <input id="fab-finish-damaged" v-model="finishForm.qty_damaged" type="text" inputmode="numeric" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
          <FormField id="fab-finish-rejected" :label="t('fabrication.qty_rejected')" v-slot="{ describedBy }">
            <input id="fab-finish-rejected" v-model="finishForm.qty_rejected" type="text" inputmode="numeric" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
          <FormField id="fab-finish-lost" :label="t('fabrication.liquid_lost')" v-slot="{ describedBy }">
            <input id="fab-finish-lost" v-model="finishForm.liquid_lost" type="text" inputmode="decimal" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
        </div>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="finishOpen = false">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-finish-form" variant="brand" :disabled="busy" :loading="busy">{{ t('fabrication.finish_confirm') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Annuler le lot -->
    <FullScreenPanel v-if="cancelOpen" :title="t('fabrication.cancel_batch_title')" @close="cancelOpen = false">
      <form id="fab-batch-cancel-form" @submit.prevent="confirmCancel" class="grid gap-4">
        <p v-if="batch && batch.status !== 'brouillon'" class="rounded-control border p-3 text-base" :class="toneClasses('info')">{{ t('fabrication.cancel_restores_stock') }}</p>
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <FormField id="fab-batch-cancel-reason" :label="t('fabrication.cancel_reason')" required v-slot="{ describedBy }">
          <textarea id="fab-batch-cancel-reason" v-model="cancelReason" rows="3" required maxlength="500" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="cancelOpen = false">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-batch-cancel-form" variant="danger" :disabled="busy" :loading="busy">{{ t('fabrication.cancel_confirm') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Annuler une sortie declaree : motif obligatoire -->
    <FullScreenPanel v-if="outputCancelTarget" :title="t('fabrication.outputs.cancel_title')" @close="outputCancelTarget = null">
      <form id="fab-output-cancel-form" @submit.prevent="confirmCancelOutput" class="grid gap-4">
        <p class="text-base text-ink">{{ t('fabrication.outputs.cancel_help', { reason: t(`fabrication.outputs.reason.${outputCancelTarget.reason}`), quantity: outputCancelTarget.quantity }, Number(outputCancelTarget.quantity) || 0) }}</p>
        <p v-if="outputCancelError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ outputCancelError }}</p>
        <FormField id="fab-output-cancel-reason" :label="t('fabrication.outputs.cancel_reason')" required v-slot="{ describedBy }">
          <textarea id="fab-output-cancel-reason" v-model="outputCancelReason" rows="3" required maxlength="500" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="outputCancelTarget = null">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-output-cancel-form" variant="danger" :disabled="outputBusy || !outputCancelReason.trim()" :loading="outputBusy">{{ t('fabrication.outputs.cancel_confirm') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Valider le bilan et expedier -->
    <FullScreenPanel v-if="shipOpen && batch" :title="t('fabrication.ship_title')" @close="shipOpen = false">
      <form id="fab-ship-form" @submit.prevent="confirmShip" class="grid gap-4">
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <p class="text-base text-ink">{{ t('fabrication.ship_help', { good: batch.qty_shipped }, Number(batch.qty_shipped) || 0) }}</p>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="fab-ship-delivery" :label="t('fabrication.delivery_date')" required v-slot="{ describedBy }">
            <input id="fab-ship-delivery" v-model="shipForm.delivery_date" type="date" required :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="fab-ship-expiry" :label="t('fabrication.expiry_date')" v-slot="{ describedBy }">
            <input id="fab-ship-expiry" v-model="shipForm.expiry_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <p v-if="batch.out_of_tolerance" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ t('fabrication.ship_out_of_tolerance', { missing: batch.missing_qty, pct: pct(batch.missing_pct) }, Number(batch.missing_qty) || 0) }}</p>
        <FormField v-if="needsJustification" id="fab-ship-justification" :label="t('fabrication.justification')" required v-slot="{ describedBy }">
          <textarea id="fab-ship-justification" v-model="shipForm.justification" rows="4" required maxlength="5000" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="shipOpen = false">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-ship-form" variant="success" :disabled="busy || shipBlocked" :loading="busy">{{ t('fabrication.ship_confirm') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { classifyQuantity, formatUnitCost, purchaseOptionLabel } from '@/utils/fabFormat';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { PlusIcon, TrashIcon, CheckIcon, PlayIcon, FlagIcon, ArrowUturnLeftIcon, TruckIcon, ArrowLeftIcon, XMarkIcon, MinusCircleIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { FabricationGateway, describeFabricationError } from '@/services/FabricationGateway';
import { AppButton, AppCard, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar, StatTile } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const canWrite = computed(() => authStore.hasRole(['ProductionManager']));

const STATUS_TONES = { brouillon: 'neutral', en_production: 'info', termine: 'warning', expedie: 'success', annule: 'neutral' };
const consumptionColumns = computed(() => [
  { key: 'intrant', label: t('fabrication.col_intrant') },
  { key: 'quantity', label: t('fabrication.col_quantity'), align: 'right' },
  { key: 'provenance', label: t('fabrication.col_provenance') },
  { key: 'line_cost', label: t('fabrication.col_cost'), align: 'right' },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const batch = ref(null);
const purchases = ref([]);
const settings = ref(null);
const draft = ref([]);
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const modalError = ref('');
const busy = ref(false);

const finishOpen = ref(false);
const finishForm = ref({ qty_good: '', qty_damaged: '0', qty_rejected: '0', liquid_lost: '0' });
const cancelOpen = ref(false);
const cancelReason = ref('');
const shipOpen = ref(false);
const shipForm = ref({ delivery_date: '', expiry_date: '', justification: '' });

const batchId = computed(() => Number(route.params.id));
const hasResults = computed(() => !!batch.value && ['termine', 'expedie'].includes(batch.value.status)
  || (!!batch.value && batch.value.status === 'annule' && batch.value.finished_at != null));
const toleranceValue = computed(() => batch.value?.tolerance_applied ?? settings.value?.tolerance_pct ?? null);
// Justification : exigee si le lot est hors tolerance, ou si le serveur la demande a l'expedition
// (tolerance resserree entre la fin et l'expedition : il recalcule avec la tolerance du moment).
const justificationAsked = ref(false);
const needsJustification = computed(() => !!batch.value?.out_of_tolerance || justificationAsked.value);
const shipBlocked = computed(() => !shipForm.value.delivery_date || (needsJustification.value && !(shipForm.value.justification || '').trim()));
const isJustificationRequired = (err) => err?.response?.status === 422 && err?.response?.data?.detail?.code === 'justification_required';

// Achats proposes : actifs avec du restant, plus ceux deja choisis dans le brouillon.
const availablePurchases = computed(() => {
  const chosen = new Set(draft.value.map((d) => d.purchase_id));
  return purchases.value.filter((p) => p.status === 'actif' && p.intrant_active !== false && (Number(p.remaining_qty) > 0 || chosen.has(p.id)));
});

const num = (v) => Number(v ?? 0);
const qty = (v) => num(v).toLocaleString('fr-FR', { maximumFractionDigits: 3 });
const pct = (v) => (v == null ? '-' : String(v));
const formatCurrency = (v) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(num(v)).replace('XOF', 'FCFA');
const formatDate = (v) => (v ? new Date(v).toLocaleDateString('fr-FR') : '-');
const purchaseLabel = (p) => purchaseOptionLabel(p, t, qty, formatDate);

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
    batch.value = await FabricationGateway.getBatch(batchId.value);
    draft.value = (batch.value.consumptions || []).map((c) => ({ purchase_id: c.purchase_id, quantity: String(c.quantity) }));
  } catch (err) {
    pageError.value = describeFabricationError(err, t('fabrication.error_load'));
    console.error('Chargement du lot echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

// Donnees annexes : un echec ne bloque pas la fiche.
const loadSide = async () => {
  const [p, s] = await Promise.allSettled([
    FabricationGateway.listPurchases(),
    FabricationGateway.getSettings(),
  ]);
  if (p.status === 'fulfilled') purchases.value = p.value;
  if (s.status === 'fulfilled') settings.value = s.value;
};

const run = async (fn, successKey, logLabel, { silent = false } = {}) => {
  pageError.value = '';
  pageMessage.value = '';
  busy.value = true;
  try {
    await fn();
    if (!silent) flash(t(successKey));
    return true;
  } catch (err) {
    pageError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error(logLabel, err);
    return false;
  } finally {
    busy.value = false;
  }
};

const draftIsValid = () => {
  for (const d of draft.value) {
    if (!d.purchase_id) { pageError.value = t('fabrication.err_purchase_required'); return false; }
    const kind = classifyQuantity(d.quantity);
    if (kind === 'invalid') { pageError.value = t('fabrication.err_quantity_invalid'); return false; }
    if (kind === 'zero') { pageError.value = t('fabrication.err_quantity'); return false; }
  }
  return true;
};

const saveDraft = async ({ silent = false } = {}) => {
  pageError.value = '';
  draft.value.forEach((d) => { d.quantity = String(d.quantity).trim().replace(',', '.'); });
  if (!draftIsValid()) return false;
  return run(async () => {
    await FabricationGateway.updateBatch(batchId.value, {
      consumptions: draft.value.map((d) => ({ purchase_id: d.purchase_id, quantity: String(d.quantity).trim() })),
    });
    await load();
  }, 'fabrication.draft_saved', 'Enregistrement du brouillon echoue :', { silent });
};

const startBatch = async () => {
  if (!(await saveDraft({ silent: true }))) return;
  await run(async () => {
    await FabricationGateway.startBatch(batchId.value);
    await Promise.all([load(), loadSide()]);
  }, 'fabrication.batch_started', 'Passage en production echoue :');
};

const reopenBatch = () => run(async () => {
  await FabricationGateway.reopenBatch(batchId.value);
  await load();
}, 'fabrication.batch_reopened', 'Reouverture echouee :');

const openFinish = () => {
  modalError.value = '';
  finishForm.value = { qty_good: '', qty_damaged: '0', qty_rejected: '0', liquid_lost: '0' };
  finishOpen.value = true;
};

const toCount = (v) => (/^\d+$/.test(String(v ?? '').trim()) ? Number(String(v).trim()) : null);

const confirmFinish = async () => {
  modalError.value = '';
  const f = finishForm.value;
  const good = toCount(f.qty_good);
  const damaged = toCount(f.qty_damaged || '0');
  const rejected = toCount(f.qty_rejected || '0');
  const lost = String(f.liquid_lost || '0').trim().replace(',', '.');
  if (good === null || damaged === null || rejected === null) { modalError.value = t('fabrication.err_counts'); return; }
  if (!/^\d+(\.\d{1,3})?$/.test(lost)) { modalError.value = t('fabrication.err_liquid_lost'); return; }
  busy.value = true;
  try {
    await FabricationGateway.finishBatch(batchId.value, { qty_good: good, qty_damaged: damaged, qty_rejected: rejected, liquid_lost: lost });
    finishOpen.value = false;
    flash(t('fabrication.batch_finished'));
    await load();
  } catch (err) {
    modalError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Fin du lot echouee :', err);
  } finally {
    busy.value = false;
  }
};

const openCancel = () => {
  modalError.value = '';
  cancelReason.value = '';
  cancelOpen.value = true;
};

const confirmCancel = async () => {
  modalError.value = '';
  const reason = (cancelReason.value || '').trim();
  if (!reason) { modalError.value = t('fabrication.err_reason_required'); return; }
  const restored = batch.value && batch.value.status !== 'brouillon';
  busy.value = true;
  try {
    await FabricationGateway.cancelBatch(batchId.value, reason);
    cancelOpen.value = false;
    flash(t(restored ? 'fabrication.batch_cancelled_restored' : 'fabrication.batch_cancelled'));
    await Promise.all([load(), loadSide()]);
  } catch (err) {
    modalError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Annulation du lot echouee :', err);
  } finally {
    busy.value = false;
  }
};

const openShip = () => {
  modalError.value = '';
  shipForm.value = { delivery_date: '', expiry_date: '', justification: '' };
  justificationAsked.value = false;
  shipOpen.value = true;
};

const confirmShip = async () => {
  modalError.value = '';
  if (shipBlocked.value) {
    modalError.value = t(shipForm.value.delivery_date ? 'fabrication.err_justification' : 'fabrication.err_delivery_date');
    return;
  }
  busy.value = true;
  try {
    await FabricationGateway.shipBatch(batchId.value, {
      delivery_date: shipForm.value.delivery_date,
      expiry_date: shipForm.value.expiry_date || undefined,
      justification: needsJustification.value ? shipForm.value.justification.trim() : undefined,
    });
    shipOpen.value = false;
    flash(t('fabrication.batch_shipped'));
    await load();
  } catch (err) {
    if (isJustificationRequired(err)) justificationAsked.value = true;
    modalError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Expedition du lot echouee :', err);
  } finally {
    busy.value = false;
  }
};

// ---- Sorties declarees ----
// Bilan (qty_good, qty_outputs, qty_shipped) lu du serveur ; la borne de quantite est qty_shipped.
const showOutputs = computed(() => !!batch.value && (['termine', 'expedie'].includes(batch.value.status) || (batch.value.outputs || []).length > 0));
const canDeclare = computed(() => canWrite.value && batch.value?.status === 'termine');
const nothingToShip = computed(() => num(batch.value?.qty_shipped) <= 0);
// Message "tout est sorti" : seulement s'il y avait des bouteilles bonnes ET des sorties (zero bouteille bonne : comportement d'avant).
const allBottlesOut = computed(() => num(batch.value?.qty_good) > 0 && num(batch.value?.qty_outputs) > 0 && nothingToShip.value);
const formatDateTime = (v) => (v ? new Date(v).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '-');

const outputBusy = ref(false);
const outputError = ref('');
const emptyOutputForm = () => ({ reason: '', quantity: '', note: '' });
const outputForm = ref(emptyOutputForm());
const outputNoteMissing = computed(() => outputForm.value.reason === 'autre' && !(outputForm.value.note || '').trim());
const outputBlocked = computed(() => !outputForm.value.reason || !String(outputForm.value.quantity).trim() || outputNoteMissing.value);

const confirmDeclareOutput = async () => {
  if (outputBusy.value) return;
  outputError.value = '';
  const f = outputForm.value;
  if (!['echantillon', 'autre'].includes(f.reason)) { outputError.value = t('fabrication.outputs.err_reason'); return; }
  const raw = String(f.quantity ?? '').trim();
  const q = /^\d+$/.test(raw) ? Number(raw) : 0;
  if (q < 1 || q > num(batch.value.qty_shipped)) {
    outputError.value = t('fabrication.outputs.err_quantity', { max: num(batch.value.qty_shipped) }); return;
  }
  const note = (f.note || '').trim();
  if (outputNoteMissing.value) { outputError.value = t('fabrication.outputs.note_required_autre'); return; }
  outputBusy.value = true;
  try {
    await FabricationGateway.declareOutput(batchId.value, { reason: f.reason, quantity: q, note: note || undefined });
    outputForm.value = emptyOutputForm();
    flash(t('fabrication.outputs.declared'));
    await load();
  } catch (err) {
    outputError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Declaration de sortie echouee :', err);
  } finally {
    outputBusy.value = false;
  }
};

const outputCancelTarget = ref(null);
const outputCancelReason = ref('');
const outputCancelError = ref('');
const openCancelOutput = (o) => {
  outputCancelError.value = '';
  outputCancelReason.value = '';
  outputCancelTarget.value = o;
};

const confirmCancelOutput = async () => {
  if (outputBusy.value) return;
  outputCancelError.value = '';
  const reason = (outputCancelReason.value || '').trim();
  if (!reason) { outputCancelError.value = t('fabrication.outputs.err_cancel_reason'); return; }
  outputBusy.value = true;
  try {
    await FabricationGateway.cancelOutput(batchId.value, outputCancelTarget.value.id, reason);
    outputCancelTarget.value = null;
    flash(t('fabrication.outputs.cancelled'));
    await load();
  } catch (err) {
    outputCancelError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Annulation de sortie echouee :', err);
  } finally {
    outputBusy.value = false;
  }
};

onMounted(loadSide);
onMounted(load);
</script>
