<!-- src/views/modules/fabrication/FabIntrants.vue -->
<!-- Intrants et achats. Lecture : ProductionManager, promoteur, admin. Ecriture (achats, annulation) :
     ProductionManager seul. Reglage du seuil d'alerte : admin seul. Les couts sont visibles ici. -->
<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('fabrication.intrants_title')" :subtitle="t('fabrication.intrants_subtitle')">
      <template #actions>
        <AppButton v-if="canWrite" :icon="PlusIcon" @click="openPurchase">{{ t('fabrication.new_purchase') }}</AppButton>
      </template>
    </PageHeader>

    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="isLoading" role="status" class="text-base text-ink-muted">{{ t('stockOps.loading') }}</p>
    <p v-if="pageMessage" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ pageMessage }}</p>

    <AppCard :title="t('fabrication.stock_title')">
      <label class="mb-4 flex min-h-11 items-center gap-3 text-base text-ink">
        <input type="checkbox" v-model="showInactive" class="h-5 w-5 accent-brand-600" @change="loadIntrants" />
        {{ t('fabrication.show_inactive') }}
      </label>
      <ResponsiveTable
        :columns="stockColumns"
        :rows="intrants"
        row-key="id"
        :loading="isLoading"
        :empty-title="t('fabrication.no_intrants')"
        :empty-message="' '"
        striped
      >
        <template #cell-name="{ row: i }">
          <span class="font-medium text-ink">{{ i.name }}</span>
          <StatusBadge v-if="i.is_container" class="ml-2" tone="info" :label="t('fabrication.container_tag')" />
          <StatusBadge v-if="!i.is_active" class="ml-2" tone="neutral" :label="t('fabrication.intrant_inactive')" />
        </template>
        <template #cell-stock="{ row: i }">
          <span class="font-bold" :class="i.below_threshold ? 'text-tone-danger-text' : 'text-ink'">{{ qty(i.stock) }}</span>
        </template>
        <template #cell-threshold="{ row: i }">
          <form v-if="canSetThreshold && editingThresholdId === i.id" class="flex flex-wrap items-end justify-end gap-2" @submit.prevent="saveThreshold(i)">
            <FormField :id="`fab-threshold-${i.id}`" :label="t('fabrication.threshold_label')" v-slot="{ describedBy }">
              <input :id="`fab-threshold-${i.id}`" v-model="thresholdValue" type="number" inputmode="decimal" min="0" step="0.001" required :aria-describedby="describedBy" :class="[fieldClass, 'w-32 text-right']" />
            </FormField>
            <AppButton type="submit" size="sm" variant="info" :disabled="busy" :loading="busy">{{ t('fabrication.threshold_save') }}</AppButton>
            <AppButton size="sm" variant="ghost" :disabled="busy" @click="editingThresholdId = null">{{ t('common.cancel') }}</AppButton>
          </form>
          <template v-else>
            <span>{{ qty(i.alert_threshold) }}</span>
            <AppButton v-if="canSetThreshold" class="ml-2" size="sm" variant="secondary" :icon="PencilSquareIcon" @click="startThreshold(i)">{{ t('fabrication.threshold_edit') }}</AppButton>
          </template>
        </template>
        <template #cell-state="{ row: i }">
          <StatusBadge v-if="i.below_threshold" tone="danger" :label="t('fabrication.below_threshold')" />
          <StatusBadge v-else tone="success" :label="t('fabrication.stock_ok')" />
        </template>
        <template v-if="canWrite" #actions="{ row: i }">
          <div class="flex flex-wrap items-center justify-end gap-2">
            <AppButton v-if="i.editable" size="sm" variant="secondary" :icon="PencilSquareIcon" @click="openEdit(i)">{{ t('fabrication.intrant_edit') }}</AppButton>
            <span v-else class="text-base text-ink-muted">{{ t('fabrication.intrant_locked') }}</span>
            <AppButton size="sm" :variant="i.is_active ? 'danger' : 'success'" @click="openToggle(i)">{{ i.is_active ? t('fabrication.intrant_deactivate') : t('fabrication.intrant_reactivate') }}</AppButton>
          </div>
        </template>
      </ResponsiveTable>
    </AppCard>

    <AppCard :title="t('fabrication.purchases_title')">
      <form class="mb-4 flex flex-wrap items-end gap-4" @submit.prevent="loadPurchases">
        <FormField id="fab-purchases-from" :label="t('fabrication.filter_date_from')" v-slot="{ describedBy }">
          <input id="fab-purchases-from" v-model="dateFrom" type="date" :aria-describedby="describedBy" :class="fieldClass" @change="loadPurchases" />
        </FormField>
        <FormField id="fab-purchases-to" :label="t('fabrication.filter_date_to')" v-slot="{ describedBy }">
          <input id="fab-purchases-to" v-model="dateTo" type="date" :aria-describedby="describedBy" :class="fieldClass" @change="loadPurchases" />
        </FormField>
        <AppButton v-if="dateFrom || dateTo" variant="ghost" @click="resetDates">{{ t('fabrication.filter_reset') }}</AppButton>
      </form>
      <ResponsiveTable
        :columns="purchaseColumns"
        :rows="purchases"
        row-key="id"
        :loading="isLoading"
        :empty-title="t('fabrication.no_purchases')"
        :empty-message="' '"
        striped
      >
        <template #cell-intrant="{ row: p }"><span class="font-medium text-ink">{{ p.intrant_name || '-' }}</span></template>
        <template #cell-supplier="{ row: p }">{{ p.supplier || '-' }}</template>
        <template #cell-delivery_ref="{ row: p }">{{ p.delivery_ref || '-' }}</template>
        <template #cell-date="{ row: p }">{{ formatDate(p.purchase_date) }}</template>
        <template #cell-quantity="{ row: p }">{{ qty(p.quantity) }}</template>
        <template #cell-unit_cost="{ row: p }">{{ formatCurrency(p.unit_cost) }}</template>
        <template #cell-remaining="{ row: p }">{{ p.status === 'actif' ? qty(p.remaining_qty) : qty(0) }}</template>
        <template #cell-status="{ row: p }">
          <StatusBadge v-if="p.status === 'actif'" tone="success" :label="t('fabrication.status_actif')" />
          <StatusBadge v-else tone="neutral" :label="t('fabrication.status_annule')" />
        </template>
        <template v-if="canWrite" #actions="{ row: p }">
          <div class="flex flex-wrap items-center justify-end gap-2">
            <AppButton v-if="canEditPurchase(p)" size="sm" variant="secondary" :icon="PencilSquareIcon" @click="openPurchaseEdit(p)">{{ t('fabrication.edit_purchase') }}</AppButton>
            <AppButton v-if="p.status === 'actif'" size="sm" variant="danger" @click="openCancel(p)">{{ t('fabrication.cancel_purchase') }}</AppButton>
          </div>
        </template>
      </ResponsiveTable>
    </AppCard>

    <!-- Nouvel achat -->
    <FullScreenPanel v-if="purchaseOpen" :title="t('fabrication.purchase_title')" @close="purchaseOpen = false">
      <form id="fab-purchase-form" @submit.prevent="savePurchase" class="grid gap-4">
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>

        <fieldset class="grid gap-2">
          <legend class="text-base font-medium text-ink">{{ t('fabrication.mode_label') }}</legend>
          <label class="flex min-h-11 items-center gap-3 text-base text-ink">
            <input type="radio" v-model="form.mode" value="existing" class="h-5 w-5 accent-brand-600" />
            {{ t('fabrication.mode_existing') }}
          </label>
          <label class="flex min-h-11 items-center gap-3 text-base text-ink">
            <input type="radio" v-model="form.mode" value="new" class="h-5 w-5 accent-brand-600" />
            {{ t('fabrication.mode_new') }}
          </label>
        </fieldset>

        <FormField v-if="form.mode === 'existing'" id="fab-purchase-intrant" :label="t('fabrication.col_intrant')" required v-slot="{ describedBy }">
          <select id="fab-purchase-intrant" v-model="form.intrant_id" required :aria-describedby="describedBy" :class="fieldClass">
            <option :value="null" disabled>{{ t('fabrication.choose_intrant') }}</option>
            <option v-for="i in activeIntrants" :key="i.id" :value="i.id">{{ i.name }} ({{ i.unit }})</option>
          </select>
        </FormField>
        <template v-else>
          <div class="grid gap-4 sm:grid-cols-2">
            <FormField id="fab-intrant-name" :label="t('fabrication.intrant_name')" required v-slot="{ describedBy }">
              <input id="fab-intrant-name" v-model="form.name" type="text" required maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField id="fab-intrant-unit" :label="t('fabrication.intrant_unit')" required v-slot="{ describedBy }">
              <input id="fab-intrant-unit" v-model="form.unit" type="text" required maxlength="20" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
          </div>
          <label class="flex min-h-11 items-center gap-3 text-base text-ink">
            <input type="checkbox" v-model="form.is_container" class="h-5 w-5 accent-brand-600" />
            {{ t('fabrication.intrant_container') }}
          </label>
        </template>

        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="fab-purchase-supplier" :label="t('fabrication.supplier')" v-slot="{ describedBy }">
            <input id="fab-purchase-supplier" v-model="form.supplier" type="text" maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="fab-purchase-ref" :label="t('fabrication.delivery_ref')" v-slot="{ describedBy }">
            <input id="fab-purchase-ref" v-model="form.delivery_ref" type="text" maxlength="100" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <FormField id="fab-purchase-date" :label="t('fabrication.purchase_date')" required v-slot="{ describedBy }">
          <input id="fab-purchase-date" v-model="form.purchase_date" type="date" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="fab-purchase-qty" :label="t('fabrication.quantity')" required v-slot="{ describedBy }">
            <input id="fab-purchase-qty" v-model="form.quantity" type="number" inputmode="decimal" min="0.001" step="0.001" required :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
          <FormField id="fab-purchase-cost" :label="t('fabrication.unit_cost')" required v-slot="{ describedBy }">
            <input id="fab-purchase-cost" v-model="form.unit_cost" type="number" inputmode="decimal" min="0" step="0.01" required :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
          </FormField>
        </div>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="purchaseOpen = false">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-purchase-form" variant="brand" :disabled="busy" :loading="busy">{{ t('stockOps.save') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Modification minimale d'un achat non consomme : cout unitaire, fournisseur, reference -->
    <FullScreenPanel v-if="purchaseEditTarget" :title="t('fabrication.edit_purchase_title')" @close="purchaseEditTarget = null">
      <form id="fab-purchase-edit-form" @submit.prevent="savePurchaseEdit" class="grid gap-4">
        <p class="text-base font-medium text-ink">{{ purchaseEditTarget.intrant_name }} ({{ formatDate(purchaseEditTarget.purchase_date) }})</p>
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="fab-pedit-supplier" :label="t('fabrication.supplier')" v-slot="{ describedBy }">
            <input id="fab-pedit-supplier" v-model="purchaseEditForm.supplier" type="text" maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="fab-pedit-ref" :label="t('fabrication.delivery_ref')" v-slot="{ describedBy }">
            <input id="fab-pedit-ref" v-model="purchaseEditForm.delivery_ref" type="text" maxlength="100" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <FormField id="fab-pedit-cost" :label="t('fabrication.unit_cost')" required v-slot="{ describedBy }">
          <input id="fab-pedit-cost" v-model="purchaseEditForm.unit_cost" type="number" inputmode="decimal" min="0" step="0.01" required :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="purchaseEditTarget = null">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-purchase-edit-form" variant="brand" :disabled="busy" :loading="busy">{{ t('stockOps.save') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Annulation d'un achat -->
    <FullScreenPanel v-if="cancelTarget" :title="t('fabrication.cancel_title')" @close="cancelTarget = null">
      <form id="fab-cancel-form" @submit.prevent="confirmCancel" class="grid gap-4">
        <p class="text-base font-medium text-ink">{{ cancelTarget.intrant_name }} ({{ formatDate(cancelTarget.purchase_date) }})</p>
        <p v-if="modalError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ modalError }}</p>
        <FormField id="fab-cancel-reason" :label="t('fabrication.cancel_reason')" required v-slot="{ describedBy }">
          <textarea id="fab-cancel-reason" v-model="cancelReason" rows="3" required maxlength="500" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
        </FormField>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="cancelTarget = null">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-cancel-form" variant="danger" :disabled="busy" :loading="busy">{{ t('fabrication.cancel_confirm') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Modification d'un intrant encore jamais livre -->
    <FullScreenPanel v-if="editTarget" :title="t('fabrication.intrant_edit_title')" @close="editTarget = null">
      <form id="fab-edit-form" @submit.prevent="saveEdit" class="grid gap-4">
        <p class="text-base text-ink-muted">{{ t('fabrication.intrant_edit_hint') }}</p>
        <p v-if="editError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ editError }}</p>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField id="fab-edit-name" :label="t('fabrication.intrant_name')" required v-slot="{ describedBy }">
            <input id="fab-edit-name" v-model="editForm.name" type="text" required maxlength="150" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="fab-edit-unit" :label="t('fabrication.intrant_unit')" required v-slot="{ describedBy }">
            <input id="fab-edit-unit" v-model="editForm.unit" type="text" required maxlength="20" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <label class="flex min-h-11 items-center gap-3 text-base text-ink">
          <input type="checkbox" v-model="editForm.is_container" class="h-5 w-5 accent-brand-600" />
          {{ t('fabrication.intrant_container') }}
        </label>
      </form>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="editTarget = null">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton type="submit" form="fab-edit-form" variant="brand" :disabled="busy" :loading="busy">{{ t('stockOps.save') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>

    <!-- Confirmation : desactiver ou reactiver un intrant -->
    <FullScreenPanel v-if="toggleTarget" :title="toggleTarget.is_active ? t('fabrication.intrant_deactivate') : t('fabrication.intrant_reactivate')" @close="toggleTarget = null">
      <div class="grid gap-4">
        <p class="text-base font-medium text-ink">{{ toggleTarget.name }} ({{ toggleTarget.unit }})</p>
        <p class="text-base text-ink">{{ toggleTarget.is_active ? t('fabrication.intrant_deactivate_confirm') : t('fabrication.intrant_reactivate_confirm') }}</p>
        <p v-if="editError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ editError }}</p>
      </div>
      <template #footer>
        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="toggleTarget = null">{{ t('stockOps.close') }}</AppButton>
          </template>
          <AppButton :variant="toggleTarget.is_active ? 'danger' : 'success'" :disabled="busy" :loading="busy" @click="confirmToggle">{{ toggleTarget.is_active ? t('fabrication.intrant_deactivate') : t('fabrication.intrant_reactivate') }}</AppButton>
        </ActionBar>
      </template>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { todayLocalISO } from '@/utils/localDate';
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { PlusIcon, PencilSquareIcon } from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { FabricationGateway, describeFabricationError } from '@/services/FabricationGateway';
import { AppButton, AppCard, PageHeader, FormField, StatusBadge, ResponsiveTable, FullScreenPanel, ActionBar } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { classifyQuantity } from '@/utils/fabFormat';

const { t } = useI18n();
const authStore = useAuthStore();

const canWrite = computed(() => authStore.hasRole(['ProductionManager']));
const canSetThreshold = computed(() => authStore.hasRole(['admin']));

const stockColumns = computed(() => [
  { key: 'name', label: t('fabrication.col_intrant') },
  { key: 'unit', label: t('fabrication.col_unit') },
  { key: 'stock', label: t('fabrication.col_stock'), align: 'right' },
  { key: 'threshold', label: t('fabrication.col_threshold'), align: 'right' },
  { key: 'state', label: t('fabrication.col_state') },
]);
const purchaseColumns = computed(() => [
  { key: 'intrant', label: t('fabrication.col_intrant') },
  { key: 'supplier', label: t('fabrication.col_supplier') },
  { key: 'delivery_ref', label: t('fabrication.col_delivery_ref') },
  { key: 'date', label: t('fabrication.col_date') },
  { key: 'quantity', label: t('fabrication.col_quantity'), align: 'right' },
  { key: 'unit_cost', label: t('fabrication.col_unit_cost'), align: 'right' },
  { key: 'remaining', label: t('fabrication.col_remaining'), align: 'right' },
  { key: 'status', label: t('fabrication.col_status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const intrants = ref([]);
const purchases = ref([]);
const isLoading = ref(false);
const pageError = ref('');
const pageMessage = ref('');
const modalError = ref('');
const busy = ref(false);

const purchaseOpen = ref(false);
const cancelTarget = ref(null);
const purchaseEditTarget = ref(null);
const purchaseEditForm = ref({ supplier: '', delivery_ref: '', unit_cost: '' });
const cancelReason = ref('');
const showInactive = ref(false);
const dateFrom = ref('');
const dateTo = ref('');
const editTarget = ref(null);
const editForm = ref({ name: '', unit: '', is_container: false });
const editError = ref('');
const toggleTarget = ref(null);
// un achat n'est accepte que pour un intrant actif
const activeIntrants = computed(() => intrants.value.filter((i) => i.is_active));
const editingThresholdId = ref(null);
const thresholdValue = ref('');
// Intrant cree au cours d'un enregistrement dont l'achat a echoue : reutilise a la reprise (pas de doublon).
let createdIntrantId = null;

const today = () => todayLocalISO();
const emptyForm = () => ({
  mode: 'existing', intrant_id: null, name: '', unit: '', is_container: false,
  supplier: '', delivery_ref: '', purchase_date: today(), quantity: '', unit_cost: '',
});
const form = ref(emptyForm());

const num = (v) => Number(v ?? 0);
const qty = (v) => num(v).toLocaleString('fr-FR', { maximumFractionDigits: 3 });
const formatCurrency = (v) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(num(v)).replace('XOF', 'FCFA');
const formatDate = (v) => (v ? new Date(v).toLocaleDateString('fr-FR') : '-');

let msgTimer = null;
const flash = (msg) => {
  pageMessage.value = msg;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { pageMessage.value = ''; }, 5000);
};
onBeforeUnmount(() => clearTimeout(msgTimer));

const fetchIntrants = () => FabricationGateway.listIntrants({ includeInactive: showInactive.value });
const fetchPurchases = () => FabricationGateway.listPurchases({ dateFrom: dateFrom.value || undefined, dateTo: dateTo.value || undefined });
const datesInvalid = () => !!(dateFrom.value && dateTo.value && dateFrom.value > dateTo.value);

const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    if (datesInvalid()) {
      intrants.value = await fetchIntrants();
      pageError.value = t('fabrication.err_date_range');
      return;
    }
    const [i, p] = await Promise.all([fetchIntrants(), fetchPurchases()]);
    intrants.value = i;
    purchases.value = p;
  } catch (err) {
    pageError.value = describeFabricationError(err, t('fabrication.error_load'));
    console.error('Chargement des intrants echoue :', err);
  } finally {
    isLoading.value = false;
  }
};

const loadIntrants = async () => {
  pageError.value = '';
  try {
    intrants.value = await fetchIntrants();
  } catch (err) {
    pageError.value = describeFabricationError(err, t('fabrication.error_load'));
    console.error('Chargement des intrants echoue :', err);
  }
};

const loadPurchases = async () => {
  pageError.value = '';
  if (datesInvalid()) { pageError.value = t('fabrication.err_date_range'); return; }
  try {
    purchases.value = await fetchPurchases();
  } catch (err) {
    pageError.value = describeFabricationError(err, t('fabrication.error_load'));
    console.error('Chargement des achats echoue :', err);
  }
};

const resetDates = () => { dateFrom.value = ''; dateTo.value = ''; loadPurchases(); };

const openEdit = (i) => {
  pageMessage.value = '';
  editError.value = '';
  editForm.value = { name: i.name, unit: i.unit, is_container: !!i.is_container };
  editTarget.value = i;
};

const saveEdit = async () => {
  editError.value = '';
  const f = editForm.value;
  if (!(f.name || '').trim()) { editError.value = t('fabrication.err_name_required'); return; }
  if (!(f.unit || '').trim()) { editError.value = t('fabrication.err_unit_required'); return; }
  busy.value = true;
  try {
    await FabricationGateway.updateIntrant(editTarget.value.id, {
      name: f.name.trim(), unit: f.unit.trim(), is_container: !!f.is_container,
    });
    editTarget.value = null;
    flash(t('fabrication.intrant_saved'));
    await load();
  } catch (err) {
    // Intrant deja livre : le serveur repond 409 avec son message, affiche tel quel.
    editError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Modification de l\'intrant echouee :', err);
  } finally {
    busy.value = false;
  }
};

const openToggle = (i) => {
  pageMessage.value = '';
  editError.value = '';
  toggleTarget.value = i;
};

const confirmToggle = async () => {
  editError.value = '';
  const target = toggleTarget.value;
  busy.value = true;
  try {
    await FabricationGateway.updateIntrant(target.id, { is_active: !target.is_active });
    toggleTarget.value = null;
    flash(target.is_active ? t('fabrication.intrant_deactivated') : t('fabrication.intrant_reactivated'));
    await load();
  } catch (err) {
    editError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Activation de l\'intrant echouee :', err);
  } finally {
    busy.value = false;
  }
};

const openPurchase = () => {
  pageMessage.value = '';
  modalError.value = '';
  createdIntrantId = null;
  form.value = emptyForm();
  purchaseOpen.value = true;
};

const savePurchase = async () => {
  modalError.value = '';
  const f = form.value;
  let intrantId = f.intrant_id;
  if (f.mode === 'new') {
    if (!(f.name || '').trim()) { modalError.value = t('fabrication.err_name_required'); return; }
    if (!(f.unit || '').trim()) { modalError.value = t('fabrication.err_unit_required'); return; }
  } else if (!intrantId) { modalError.value = t('fabrication.err_intrant_required'); return; }
  if (!f.purchase_date) { modalError.value = t('fabrication.err_date_required'); return; }
  const quantityKind = classifyQuantity(f.quantity);
  if (quantityKind === 'invalid') { modalError.value = t('fabrication.err_quantity_invalid'); return; }
  if (quantityKind === 'zero') { modalError.value = t('fabrication.err_quantity'); return; }
  if (f.unit_cost === '' || !(Number(f.unit_cost) >= 0)) { modalError.value = t('fabrication.err_unit_cost'); return; }
  busy.value = true;
  try {
    if (f.mode === 'new') {
      if (!createdIntrantId) {
        const created = await FabricationGateway.createIntrant({
          name: f.name.trim(), unit: f.unit.trim(), is_container: !!f.is_container,
        });
        createdIntrantId = created.id;
      }
      intrantId = createdIntrantId;
    }
    await FabricationGateway.createPurchase({
      intrant_id: intrantId,
      supplier: (f.supplier || '').trim(),
      delivery_ref: (f.delivery_ref || '').trim(),
      purchase_date: f.purchase_date,
      quantity: f.quantity,
      unit_cost: f.unit_cost,
    });
    purchaseOpen.value = false;
    flash(t('fabrication.purchase_saved'));
    await load();
  } catch (err) {
    modalError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Enregistrement de l\'achat echoue :', err);
  } finally {
    busy.value = false;
  }
};

// Un achat se corrige tant qu'il est actif et qu'aucun lot ne l'a consomme (le serveur refuse sinon, avec son message).
const canEditPurchase = (p) => canWrite.value && p.status === 'actif' && num(p.remaining_qty) === num(p.quantity);

const openPurchaseEdit = (p) => {
  pageMessage.value = '';
  modalError.value = '';
  purchaseEditForm.value = { supplier: p.supplier || '', delivery_ref: p.delivery_ref || '', unit_cost: String(num(p.unit_cost)) };
  purchaseEditTarget.value = p;
};

const savePurchaseEdit = async () => {
  modalError.value = '';
  const f = purchaseEditForm.value;
  if (f.unit_cost === '' || !(Number(f.unit_cost) >= 0)) { modalError.value = t('fabrication.err_unit_cost'); return; }
  busy.value = true;
  try {
    await FabricationGateway.updatePurchase(purchaseEditTarget.value.id, {
      supplier: (f.supplier || '').trim(), delivery_ref: (f.delivery_ref || '').trim(), unit_cost: f.unit_cost,
    });
    purchaseEditTarget.value = null;
    flash(t('fabrication.purchase_updated'));
    await load();
  } catch (err) {
    // Achat deja consomme par un lot : le serveur repond 409 avec son message, affiche tel quel.
    modalError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Modification de l\'achat echouee :', err);
  } finally {
    busy.value = false;
  }
};

const openCancel = (p) => {
  pageMessage.value = '';
  modalError.value = '';
  cancelReason.value = '';
  cancelTarget.value = p;
};

const confirmCancel = async () => {
  modalError.value = '';
  const reason = (cancelReason.value || '').trim();
  if (!reason) { modalError.value = t('fabrication.err_reason_required'); return; }
  busy.value = true;
  try {
    await FabricationGateway.cancelPurchase(cancelTarget.value.id, reason);
    cancelTarget.value = null;
    flash(t('fabrication.purchase_cancelled'));
    await load();
  } catch (err) {
    // Achat deja consomme : le serveur repond 409 avec son message, affiche tel quel.
    modalError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Annulation de l\'achat echouee :', err);
  } finally {
    busy.value = false;
  }
};

const startThreshold = (i) => {
  pageMessage.value = '';
  pageError.value = '';
  thresholdValue.value = String(num(i.alert_threshold));
  editingThresholdId.value = i.id;
};

const saveThreshold = async (i) => {
  pageError.value = '';
  if (thresholdValue.value === '' || !(Number(thresholdValue.value) >= 0)) { pageError.value = t('fabrication.err_threshold'); return; }
  busy.value = true;
  try {
    await FabricationGateway.setThreshold(i.id, thresholdValue.value);
    editingThresholdId.value = null;
    flash(t('fabrication.threshold_saved'));
    await load();
  } catch (err) {
    pageError.value = describeFabricationError(err, t('fabrication.error_save'));
    console.error('Reglage du seuil echoue :', err);
  } finally {
    busy.value = false;
  }
};

onMounted(load);
</script>
