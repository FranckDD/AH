<template>
  <FullScreenPanel :title="t('caisse.invoice_modal.title')" :subtitle="t('caisseInvoice.subtitle')" wide accent @close="$emit('close')">
    <div class="grid gap-3">
      <div class="grid gap-3 lg:grid-cols-[1fr_17rem]">
        <!-- PATIENT -->
        <FormSection compact :title="t('caisse.invoice_modal.section_patient')">
          <div v-if="!selectedPatient" class="grid gap-2 md:col-span-2 md:grid-cols-[1fr_auto_1fr] md:items-end">
            <FormField id="inv-patient-search" :label="t('caisse.invoice_modal.patient_search_placeholder')" v-slot="{ describedBy }">
              <input id="inv-patient-search" v-model="patientSearchQuery" @input="onPatientSearchInput" type="search" autocomplete="off"
                     :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <p class="text-center text-base text-ink-muted md:pb-2">{{ t('caisse.invoice_modal.or') }}</p>
            <FormField id="inv-patient-label" :label="t('caisse.invoice_modal.patient_label_placeholder')" v-slot="{ describedBy }">
              <input id="inv-patient-label" v-model="patientLabel" type="text" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <ul v-if="patientResults.length" class="max-h-44 divide-y divide-tone-neutral-border overflow-y-auto rounded-control border border-tone-neutral-border md:col-span-3">
              <li v-for="p in patientResults" :key="p.patient_id">
                <button type="button" @click="selectPatient(p)"
                        class="flex min-h-10 w-full items-center gap-2 px-3 py-1.5 text-left text-base text-ink hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600">
                  <span class="font-medium">{{ p.first_name }} {{ p.last_name }}</span>
                  <span class="text-ink-muted">{{ p.code_patient }}</span>
                </button>
              </li>
            </ul>
          </div>
          <div v-else class="flex flex-col gap-2 rounded-control border p-2 sm:flex-row sm:items-center sm:justify-between md:col-span-2" :class="toneClasses('success')">
            <span class="text-base font-semibold">
              {{ selectedPatient.first_name }} {{ selectedPatient.last_name }} ({{ selectedPatient.code_patient }})
            </span>
            <AppButton variant="secondary" @click="selectedPatient = null">{{ t('caisse.invoice_modal.change_patient') }}</AppButton>
          </div>
        </FormSection>

        <!-- Patient retenu -->
        <aside class="grid content-start gap-1 rounded-card border border-tone-neutral-border bg-white p-3">
          <p class="text-base font-semibold text-ink">{{ t('caisseInvoice.patient_selected') }}</p>
          <p v-if="selectedPatient" class="text-base text-ink">{{ selectedPatient.first_name }} {{ selectedPatient.last_name }}<span class="text-ink-muted"> ({{ selectedPatient.code_patient }})</span></p>
          <p v-else-if="patientLabel.trim()" class="text-base text-ink">{{ patientLabel }}</p>
          <p v-else class="text-base text-ink-muted">{{ t('caisseInvoice.patient_none') }}</p>
        </aside>
      </div>

      <div class="grid gap-3 lg:grid-cols-[1fr_17rem] lg:items-start">
        <!-- LIGNES -->
        <FormSection compact :title="t('caisse.invoice_modal.section_items')" :subtitle="t('caisseInvoice.lines_hint')">
          <div class="flex flex-wrap gap-2 md:col-span-2">
            <AppButton variant="pharma" :icon="PlusIcon" @click="addLine('Médicament')">{{ t('caisse.invoice_modal.line_type_pharmacy') }}</AppButton>
            <AppButton variant="spirit" :icon="PlusIcon" @click="addLine('Consultation')">{{ t('caisse.invoice_modal.line_type_consultation') }}</AppButton>
            <AppButton variant="lab" :icon="PlusIcon" @click="addLine('Examen')">{{ t('caisse.invoice_modal.line_type_exam') }}</AppButton>
            <AppButton variant="secondary" :icon="PlusIcon" @click="addLine('Service')">{{ t('caisse.invoice_modal.line_type_service') }}</AppButton>
          </div>

          <p v-if="lines.length === 0" class="rounded-control border px-3 py-2 text-base md:col-span-2" :class="toneClasses('info')">
            {{ t('caisse.invoice_modal.no_lines') }}
          </p>

          <div v-for="(line, idx) in lines" :key="line.key" class="grid gap-2 rounded-control border border-tone-neutral-border p-2 md:col-span-2">
            <div class="grid gap-2 md:grid-cols-[1fr_5rem_7.5rem_7.5rem_auto] md:items-end">
              <div class="min-w-0">
                <p class="text-base font-semibold text-ink">
                  {{ t('caisseInvoice.line_number', { n: idx + 1 }) }} :
                  {{ line.itemType === 'Médicament' ? t('caisse.invoice_modal.line_type_pharmacy')
                     : line.itemType === 'Consultation' ? t('caisse.invoice_modal.line_type_consultation')
                     : line.itemType === 'Examen' ? t('caisse.invoice_modal.line_type_exam')
                     : t('caisse.invoice_modal.line_type_service') }}
                </p>

                <!-- Pharmacie -->
                <template v-if="line.itemType === 'Médicament'">
                  <input v-if="!line.refLabel" v-model="line.searchQuery" @input="onLineSearchInput(line, 'product')" type="search" autocomplete="off"
                         :aria-label="t('caisse.invoice_modal.search_product_placeholder')" :placeholder="t('caisse.invoice_modal.search_product_placeholder')" :class="fieldClass" />
                  <p v-else class="flex min-h-10 items-center text-base font-medium text-ink">{{ line.refLabel }}</p>
                </template>

                <!-- Consultation -->
                <template v-if="line.itemType === 'Consultation'">
                  <input v-if="!line.refLabel" v-model="line.searchQuery" @input="onLineSearchInput(line, 'consultation')" type="search" autocomplete="off"
                         :aria-label="t('caisse.invoice_modal.search_consultation_placeholder')" :placeholder="t('caisse.invoice_modal.search_consultation_placeholder')" :class="fieldClass" />
                  <p v-else class="flex min-h-10 items-center text-base font-medium text-ink">{{ line.refLabel }}</p>
                </template>

                <!-- Examen labo -->
                <template v-if="line.itemType === 'Examen'">
                  <input v-if="!line.refLabel" v-model="line.searchQuery" type="search" autocomplete="off"
                         :aria-label="t('caisse.invoice_modal.search_exam_placeholder')" :placeholder="t('caisse.invoice_modal.search_exam_placeholder')" :class="fieldClass" />
                  <p v-else class="flex min-h-10 items-center text-base font-medium text-ink">{{ line.refLabel }}</p>
                </template>

                <!-- Service libre -->
                <input v-if="line.itemType === 'Service'" v-model="line.label" type="text"
                       :aria-label="t('caisse.invoice_modal.service_label_placeholder')" :placeholder="t('caisse.invoice_modal.service_label_placeholder')" :class="fieldClass" />
              </div>

              <FormField :id="`line-${line.key}-qty`" :label="t('caisse.invoice_modal.quantity')" v-slot="{ describedBy }">
                <input :id="`line-${line.key}-qty`" v-model.number="line.quantity" type="number" min="1" step="1" inputmode="numeric"
                       :disabled="line.itemType === 'Consultation'" :aria-describedby="describedBy" :class="[fieldClass, 'text-right disabled:bg-tone-neutral-bg']" />
              </FormField>
              <!-- Prix verrouille au catalogue pour la secretaire (autre prix : demande de reduction) -->
              <FormField :id="`line-${line.key}-price`" :label="t('caisse.invoice_modal.unit_price')"
                         :help="isPriceLocked(line) && !isPriceUndefined(line) ? t('caisseInvoice.price_locked_help') : ''" v-slot="{ describedBy }">
                <input :id="`line-${line.key}-price`" v-model.number="line.unitPrice" type="number" min="0" step="0.01" inputmode="decimal"
                       :readonly="isPriceLocked(line)" :tabindex="isPriceLocked(line) ? -1 : undefined"
                       :aria-describedby="describedBy" :class="[fieldClass, 'text-right', isPriceLocked(line) ? 'cursor-default bg-tone-neutral-bg text-ink-muted' : '']" />
              </FormField>
              <div class="flex flex-col gap-1.5">
                <span class="text-base font-medium text-ink">{{ t('caisse.invoice_modal.line_total') }}</span>
                <span class="flex min-h-10 items-center justify-end text-base font-bold text-ink">{{ formatCurrency(lineTotal(line)) }}</span>
              </div>
              <AppButton variant="ghost" :icon="TrashIcon" :aria-label="t('caisseInvoice.remove_line')" @click="removeLine(idx)" />
            </div>

            <!-- Resultats de recherche, sous la ligne -->
            <ul v-if="line.itemType === 'Médicament' && line.searchResults.length" class="max-h-40 divide-y divide-tone-neutral-border overflow-y-auto rounded-control border border-tone-neutral-border">
              <li v-for="prod in line.searchResults" :key="prod.medication_id">
                <button type="button" @click="selectProductLine(line, prod)"
                        class="flex min-h-10 w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-base text-ink hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600">
                  <span>{{ prod.drug_name }}</span>
                  <span class="text-ink-muted">{{ prod.quantity }} {{ t('caisse.invoice_modal.in_stock') }}</span>
                </button>
              </li>
            </ul>
            <ul v-if="line.itemType === 'Consultation' && line.searchResults.length" class="max-h-40 divide-y divide-tone-neutral-border overflow-y-auto rounded-control border border-tone-neutral-border">
              <li v-for="cons in line.searchResults" :key="cons.consultation_id">
                <button type="button" @click="selectConsultationLine(line, cons)"
                        class="flex min-h-10 w-full items-center px-3 py-1.5 text-left text-base text-ink hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600">
                  #{{ cons.consultation_id }} : {{ cons.type_consultation || t('caisse.invoice_modal.line_type_consultation') }}
                </button>
              </li>
            </ul>
            <ul v-if="line.itemType === 'Examen' && !line.refLabel && examSearchResults(line).length" class="max-h-40 divide-y divide-tone-neutral-border overflow-y-auto rounded-control border border-tone-neutral-border">
              <li v-for="exam in examSearchResults(line)" :key="exam.id">
                <button type="button" @click="selectExamLine(line, exam)"
                        class="flex min-h-10 w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-base text-ink hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600">
                  <span>{{ exam.nom }}</span>
                  <span class="text-ink-muted">{{ formatCurrency(exam.prix) }}</span>
                </button>
              </li>
            </ul>

            <p v-if="isPriceUndefined(line)" role="alert" class="rounded-control border px-3 py-2 text-base" :class="toneClasses('danger')">
              {{ t('caisseInvoice.price_undefined') }}
            </p>

            <p v-if="line.itemType === 'Médicament' && line.knownStock !== null && Number(line.quantity) > line.knownStock"
               class="rounded-control border px-3 py-2 text-base" :class="toneClasses('warning')">
              {{ t('caisseInvoice.stock_warning', { qty: line.quantity, stock: line.knownStock }) }}
            </p>
          </div>
        </FormSection>

        <!-- Total facture : brut, reduction personnel, net (valeurs deja calculees) -->
        <aside class="grid content-start gap-1 rounded-card border border-tone-success-border bg-tone-success-bg p-3">
          <p class="text-base font-semibold text-tone-success-text">{{ t('caisseInvoice.total_card') }}</p>
          <p class="text-3xl font-bold text-ink">{{ formatCurrency(invoiceTotals.net) }}</p>
          <template v-if="invoiceTotals.staffDiscountAmount > 0">
            <p class="text-base text-ink-muted">{{ t('staffDiscount.gross_total') }} : {{ formatCurrency(invoiceTotals.gross) }}</p>
            <p class="text-base font-semibold text-tone-success-text">{{ t('staffDiscount.invoice_line') }} -{{ formatCurrency(invoiceTotals.staffDiscountAmount) }}</p>
            <p class="text-base font-semibold text-ink">{{ t('staffDiscount.net_total') }}</p>
          </template>
          <p class="mt-1 flex justify-between gap-2 border-t border-tone-success-border pt-2 text-base text-ink">
            <span>{{ t('caisseInvoice.lines_label') }}</span><span class="font-semibold">{{ lines.length }}</span>
          </p>
          <p class="flex justify-between gap-2 text-base text-ink">
            <span>{{ t('caisse.invoice_modal.advance_amount') }}</span><span class="font-semibold">{{ formatCurrency(advanceAmount) }}</span>
          </p>
        </aside>
      </div>

      <!-- PAIEMENT -->
      <FormSection compact :title="t('caisseInvoice.payment_section')">
        <div class="grid gap-3 md:col-span-2 md:grid-cols-3">
          <FormField id="inv-category" :label="t('finance.modal.category')" v-slot="{ describedBy }">
            <select id="inv-category" v-model="transactionType" :aria-describedby="describedBy" :class="fieldClass">
              <option value="CONSULTATION">{{ t('finance.categories.consultation') }}</option>
              <option value="PHARMACY">{{ t('finance.categories.pharmacy') }}</option>
              <option value="HOSPITALIZATION">{{ t('finance.categories.hospitalization') }}</option>
              <option value="LAB">{{ t('finance.categories.lab') }}</option>
              <option value="DETOX">{{ t('finance.categories.detox') }}</option>
              <option value="OTHER">{{ t('finance.categories.other') }}</option>
            </select>
          </FormField>
          <FormField id="inv-method" :label="t('finance.modal.method')" v-slot="{ describedBy }">
            <select id="inv-method" v-model="paymentMethod" :aria-describedby="describedBy" :class="fieldClass">
              <option v-for="m in paymentModes" :key="m.code" :value="m.code">{{ m.label }}</option>
            </select>
          </FormField>
          <FormField id="inv-advance" :label="t('caisse.invoice_modal.advance_amount')" v-slot="{ describedBy }">
            <div class="flex">
              <input id="inv-advance" v-model.number="advanceAmount" type="number" min="0" :max="invoiceTotals.net" step="0.01" inputmode="decimal"
                     :aria-describedby="describedBy" :class="[fieldClass, 'rounded-r-none text-right']" />
              <span class="flex min-h-11 items-center rounded-r-control border border-l-0 border-tone-neutral-border bg-tone-neutral-bg px-3 text-base text-ink-muted lg:min-h-10">{{ t('caisseInvoice.advance_unit') }}</span>
            </div>
          </FormField>
        </div>

        <div class="md:col-span-2">
          <FormField id="inv-note" :label="t('finance.modal.desc')" v-slot="{ describedBy }">
            <textarea id="inv-note" v-model="note" rows="2" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
          </FormField>
        </div>

        <p v-if="staffStatusUnknown" role="alert" class="rounded-control border p-3 text-base md:col-span-2" :class="toneClasses('danger')">
          {{ t('staffDiscount.status_unknown') }}
        </p>
        <p v-if="showRulesUnavailable" role="alert" class="rounded-control border p-3 text-base md:col-span-2" :class="toneClasses('danger')">
          {{ t('staffDiscount.rules_unavailable') }}
        </p>
        <p v-if="showNoRuleApplies" class="rounded-control border p-3 text-base md:col-span-2" :class="toneClasses('warning')">
          {{ t('staffDiscount.no_rule_applies') }}
        </p>
      </FormSection>

      <!-- REDUCTION MANUELLE (secretaire) -->
      <FormSection v-if="authStore.hasRole(['secretaire']) && !pendingDiscountRequest" compact :title="t('caisseInvoice.discount_section')">
        <p v-if="invoiceTotals.staffDiscountAmount > 0" class="rounded-control border p-3 text-base md:col-span-2" :class="toneClasses('warning')">
          {{ t('staffDiscount.manual_replaces_warning') }}
        </p>
        <div class="md:col-span-2">
          <FormField id="inv-manager" :label="t('caisse.invoice_modal.discount_recipient')"
                     :help="Number(advanceAmount) > 0 ? t('caisseInvoice.advance_blocked') : ''" v-slot="{ describedBy }">
            <select id="inv-manager" v-model="selectedManagerId" :aria-describedby="describedBy" :class="fieldClass">
              <option :value="null">{{ t('caisse.invoice_modal.discount_select_placeholder') }}</option>
              <option v-for="m in managers" :key="m.user_id" :value="m.user_id">{{ m.full_name || m.username }}</option>
            </select>
          </FormField>
        </div>
      </FormSection>

      <div v-if="pendingDiscountRequest" class="grid gap-3 rounded-card border p-3" :class="toneClasses('warning')">
        <p class="text-base font-medium">{{ t('caisse.invoice_modal.pending_approval', { name: pendingDiscountRequest.managerName }) }}</p>
        <div class="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
          <FormField id="inv-reassign" :label="t('caisse.invoice_modal.discount_recipient')" v-slot="{ describedBy }">
            <select id="inv-reassign" v-model="selectedManagerId" :aria-describedby="describedBy" :class="fieldClass">
              <option v-for="m in managers" :key="m.user_id" :value="m.user_id">{{ m.full_name || m.username }}</option>
            </select>
          </FormField>
          <AppButton variant="secondary" @click="cancelAndReassign"
                     :disabled="isReassigning || !selectedManagerId || selectedManagerId === pendingDiscountRequest.managerId" :loading="isReassigning">
            {{ isReassigning ? t('caisse.invoice_modal.requesting') : t('caisse.invoice_modal.cancel_reassign') }}
          </AppButton>
        </div>
      </div>

      <p v-if="errorMessage" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ errorMessage }}</p>
      <p v-if="discountRequestError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ discountRequestError }}</p>
    </div>

    <template #footer>
      <!-- Total toujours visible sous lg -->
      <p class="flex items-center justify-between gap-3 border-t border-tone-neutral-border bg-white px-4 py-2 text-base lg:hidden">
        <span class="font-semibold text-ink">{{ t('caisseInvoice.total_card') }}</span>
        <span class="text-xl font-bold text-ink">{{ formatCurrency(invoiceTotals.net) }}</span>
      </p>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" :disabled="isSaving" @click="$emit('close')">{{ t('finance.modal.cancel') }}</AppButton>
        </template>
        <AppButton
          v-if="authStore.hasRole(['secretaire']) && !pendingDiscountRequest"
          variant="spirit"
          @click="handleRequestDiscount"
          :disabled="isSaving || isRequestingDiscount || !isFormValid || !selectedManagerId || Number(advanceAmount) > 0"
          :loading="isRequestingDiscount"
          :title="Number(advanceAmount) > 0 ? t('caisseInvoice.advance_blocked') : ''"
        >
          {{ isRequestingDiscount ? t('caisse.invoice_modal.requesting') : t('caisse.invoice_modal.request_discount') }}
        </AppButton>
        <AppButton @click="handleSubmit" :disabled="isSaving || !isFormValid || !!pendingDiscountRequest" :loading="isSaving">
          {{ isSaving ? t('caisse.cancel_modal.saving') : t('finance.modal.save') }}
        </AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { CaisseGateway } from '@/services/CaisseGateway';
import { LabGateway } from '@/services/labGateway';
import { DiscountRequestGateway } from '@/services/DiscountRequestGateway';
import { StaffDiscountGateway } from '@/services/StaffDiscountGateway';
import { computeInvoiceTotals } from '@/utils/invoiceTotals';
import { useAuthStore } from '@/stores/auth';
import { TrashIcon, PlusIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { usePaymentModes } from '@/utils/paymentModes';

const props = defineProps({
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'save', 'discount-requested']);
const { t } = useI18n();
const authStore = useAuthStore();

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Catalogue des examens (petite table, chargee une fois a l'ouverture puis
// filtree cote client - pas besoin d'un endpoint de recherche dedie comme
// pour les produits pharmacie, dont le volume justifie une recherche serveur
// debattue par page).
const examensCatalogue = ref([]);
onMounted(async () => {
  try {
    const body = await LabGateway.getAllExams();
    examensCatalogue.value = body.data || [];
  } catch (err) {
    console.error('Chargement du catalogue d\'examens echoue :', err);
  }
});
const examSearchResults = (line) => {
  const q = (line.searchQuery || '').trim().toLowerCase();
  if (!q) return examensCatalogue.value;
  return examensCatalogue.value.filter((exam) => (exam.nom || '').toLowerCase().includes(q));
};
const selectExamLine = (line, exam) => {
  line.refId = exam.id;
  line.refLabel = exam.nom;
  line.unitPrice = Number(exam.prix) || 0;
  line.searchResults = [];
};

// --- Demande de réduction (destinataires manager) ---
const managers = ref([]);
const selectedManagerId = ref(null);
onMounted(async () => {
  if (authStore.hasRole(['secretaire'])) {
    try {
      const res = await DiscountRequestGateway.listManagers();
      managers.value = res.data || [];
    } catch (err) {
      console.error('Chargement des managers échoué :', err);
    }
  }
});

// --- Reduction personnel : regles chargees a l'ouverture. null = non
// chargees (hors ligne sans copie locale / erreur) -> un patient Personnel
// ne peut pas etre facture (le serveur rejetterait la remise manquante).
const staffRules = ref(null);
const staffRulesLoading = ref(true);
onMounted(async () => {
  try {
    const rows = await StaffDiscountGateway.list();
    staffRules.value = Array.isArray(rows) ? rows.filter((r) => r.is_active) : null;
  } catch (err) {
    console.error('Chargement des regles de reduction personnel echoue :', err);
  } finally {
    staffRulesLoading.value = false;
  }
});

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value || 0).replace('XOF', 'FCFA');

// --- Patient ---
const patientSearchQuery = ref('');
const patientResults = ref([]);
const selectedPatient = ref(null);
const patientLabel = ref('');
let patientSearchTimeout = null;
const onPatientSearchInput = () => {
  clearTimeout(patientSearchTimeout);
  patientSearchTimeout = setTimeout(async () => {
    const body = await CaisseGateway.searchPatients(patientSearchQuery.value);
    patientResults.value = body.data || [];
  }, 300);
};
const selectPatient = (p) => {
  selectedPatient.value = p;
  patientResults.value = [];
  patientSearchQuery.value = '';
};

// --- Lignes ---
let lineKeySeq = 0;
const lines = ref([]);
const addLine = (itemType) => {
  lines.value.push(reactive({
    key: ++lineKeySeq,
    itemType,
    refId: itemType === 'Service' ? 0 : null,
    refLabel: '',
    label: '',
    searchQuery: '',
    searchResults: [],
    quantity: 1,
    unitPrice: 0,
    knownStock: null,
    // Ligne a prix catalogue : medicament et examen toujours, consultation
    // seulement FamilyRestoration (fixe a la selection) ; Service : libre.
    catalogLine: itemType === 'Médicament' || itemType === 'Examen',
  }));
};

// Prix catalogue verrouille pour tout role autre qu'admin/promoteur (la
// secretaire) : un autre prix passe par la demande de reduction. Le serveur
// applique la meme regle (utils/price_lock.py).
const canEditCatalogPrice = computed(() => authStore.hasRole(['admin', 'promoteur']));
const isPriceLocked = (line) => !canEditCatalogPrice.value && line.catalogLine;
// Prix catalogue 0 ou absent = "prix non defini" : la ligne ne peut pas etre vendue.
const isPriceUndefined = (line) => isPriceLocked(line) && line.refId !== null && !(Number(line.unitPrice) > 0);
const removeLine = (idx) => lines.value.splice(idx, 1);

let lineSearchTimeout = null;
const onLineSearchInput = (line, kind) => {
  clearTimeout(lineSearchTimeout);
  lineSearchTimeout = setTimeout(async () => {
    if (kind === 'product') {
      const body = await CaisseGateway.searchProducts(line.searchQuery);
      line.searchResults = body.data || [];
    } else {
      const body = await CaisseGateway.searchConsultations(line.searchQuery);
      line.searchResults = body.data || [];
    }
  }, 300);
};

const selectProductLine = (line, product) => {
  line.refId = product.medication_id;
  line.refLabel = product.drug_name;
  line.unitPrice = Number(product.price) || 0;
  // Stock localement connu au moment de la selection - purement informatif,
  // jamais une verification/deduction reelle (decision utilisateur
  // 2026-09-23, le serveur reste seule autorite). Peut etre `null` si le
  // champ est absent pour une raison quelconque - pas d'avertissement dans
  // ce cas plutot qu'un faux positif.
  line.knownStock = product.quantity != null ? Number(product.quantity) : null;
  line.searchResults = [];
};

const selectConsultationLine = (line, consultation) => {
  line.refId = consultation.consultation_id;
  line.refLabel = `#${consultation.consultation_id} — ${consultation.type_consultation || ''}`.trim();
  line.quantity = 1;
  line.catalogLine = consultation.type_consultation === 'FamilyRestoration';
  line.unitPrice = Number(consultation.fr_amount_paid) || 0;
  line.searchResults = [];
};

const lineTotal = (line) => (Number(line.quantity) || 0) * (Number(line.unitPrice) || 0);
const totalAmount = computed(() => lines.value.reduce((sum, l) => sum + lineTotal(l), 0));

// --- Paiement ---
const transactionType = ref('CONSULTATION');
// Liste officielle des modes (codes stables, GET /payment-modes, repli hors ligne).
const paymentModes = usePaymentModes();
const paymentMethod = ref('especes');
const advanceAmount = ref(0);
const note = ref('');

// Brut / reduction personnel / net (invariant serveur, voir invoiceTotals.js).
// Patient de passage (sans patient_id) : jamais de reduction.
const invoiceTotals = computed(() => computeInvoiceTotals({
  grossRaw: totalAmount.value,
  lines: lines.value.map((l) => ({ item_type: l.itemType, line_total: lineTotal(l) })),
  isStaff: selectedPatient.value?.is_staff === true,
  rules: staffRules.value,
  advance: advanceAmount.value,
}));
// null = statut Personnel pas encore replique (secours hors ligne) : inconnu,
// jamais traite comme "pas personnel" -> validation bloquee.
const staffStatusUnknown = computed(() => selectedPatient.value?.is_staff === null);
const showRulesUnavailable = computed(() => invoiceTotals.value.rulesMissing && !staffRulesLoading.value);

const isLineComplete = (line) => {
  const qtyOk = Number.isInteger(Number(line.quantity)) && Number(line.quantity) > 0;
  if (isPriceUndefined(line)) return false;
  if (line.itemType === 'Service') return line.label.trim().length > 0 && lineTotal(line) > 0 && qtyOk;
  return line.refId !== null && lineTotal(line) > 0 && qtyOk;
};

// Info non bloquante : patient Personnel, regles chargees, mais aucune ne
// s'applique aux articles -> pas de reduction (evite l'impression de bug).
const showNoRuleApplies = computed(() =>
  selectedPatient.value?.is_staff === true
  && !invoiceTotals.value.rulesMissing
  && !staffRulesLoading.value
  && lines.value.some((l) => isLineComplete(l) && lineTotal(l) > 0)
  && invoiceTotals.value.staffDiscountAmount === 0);

const isFormValid = computed(() => {
  const patientOk = selectedPatient.value || patientLabel.value.trim().length > 0;
  const linesOk = lines.value.length > 0 && lines.value.every(isLineComplete);
  const advanceOk = invoiceTotals.value.advanceOk;
  return patientOk && linesOk && totalAmount.value > 0 && advanceOk && !invoiceTotals.value.rulesMissing && !staffStatusUnknown.value;
});

const buildInvoiceData = () => {
  const payload = {
    amount: invoiceTotals.value.net,
    staff_discount_amount: invoiceTotals.value.staffDiscountAmount,
    advance_amount: Number(advanceAmount.value) || 0,
    payment_method: paymentMethod.value,
    transaction_type: transactionType.value,
    note: note.value?.trim() || null,
    items: lines.value.map((l) => ({
      item_type: l.itemType,
      item_ref_id: l.itemType === 'Service' ? 0 : l.refId,
      unit_price: Number(l.unitPrice) || 0,
      quantity: Number(l.quantity) || 1,
      line_total: lineTotal(l),
      note: l.itemType === 'Service' ? l.label.trim() : (l.refLabel || null),
    })),
  };

  if (selectedPatient.value) {
    payload.patient_id = selectedPatient.value.patient_id;
    payload.patient_label = null;
  } else {
    payload.patient_id = null;
    payload.patient_label = patientLabel.value.trim();
  }

  return payload;
};

// Nom d'affichage du patient pour un usage purement cosmetique cote
// impression (ticket construit localement quand hors ligne, voir
// CaisseList.vue::printTicketForTransaction) - ne fait pas partie du
// payload envoye au backend (buildInvoiceData() reste inchange) pour ne
// pas risquer un champ inattendu cote schema Pydantic.
const resolvedPatientDisplayName = () => {
  if (selectedPatient.value) {
    return `${selectedPatient.value.first_name || ''} ${selectedPatient.value.last_name || ''}`.trim();
  }
  return patientLabel.value.trim();
};

const handleSubmit = () => {
  if (!isFormValid.value) return;
  emit('save', buildInvoiceData(), resolvedPatientDisplayName());
};

// --- Demande de réduction : reste sur place (pas d'emit('save')), affiche
// son propre état "en attente" contrairement au flux normal qui ferme la
// modale via le parent. Appel réseau direct ici (pas d'emit) car l'UX exige
// que la modale reste ouverte et gère son propre état local.
const isRequestingDiscount = ref(false);
const discountRequestError = ref('');
const pendingDiscountRequest = ref(null);

const handleRequestDiscount = async () => {
  if (!isFormValid.value || !selectedManagerId.value || Number(advanceAmount.value) > 0) return;
  isRequestingDiscount.value = true;
  discountRequestError.value = '';
  try {
    const res = await DiscountRequestGateway.create(buildInvoiceData(), selectedManagerId.value);
    const manager = managers.value.find((m) => m.user_id === selectedManagerId.value);
    pendingDiscountRequest.value = { id: res.data.id, managerId: selectedManagerId.value, managerName: manager?.full_name || manager?.username };
    emit('discount-requested');
  } catch (err) {
    discountRequestError.value = err.response?.data?.detail || "Impossible d'envoyer la demande de réduction.";
    console.error('Erreur demande de réduction:', err);
  } finally {
    isRequestingDiscount.value = false;
  }
};

// La réassignation crée une NOUVELLE demande (même transaction_id, toujours
// verrouillée en pending_approval côté serveur). pendingDiscountRequest doit
// donc décrire la nouvelle demande, JAMAIS repasser à null : sinon
// "Enregistrer" et "Demander une réduction" se réactivent et rouvrent la
// double soumission (deuxième transaction pour la même facture).
const isReassigning = ref(false);
const cancelAndReassign = async () => {
  if (isReassigning.value || !pendingDiscountRequest.value || !selectedManagerId.value
      || selectedManagerId.value === pendingDiscountRequest.value.managerId) return;
  isReassigning.value = true;
  discountRequestError.value = '';
  try {
    const newManagerId = selectedManagerId.value;
    const res = await DiscountRequestGateway.cancel(pendingDiscountRequest.value.id, newManagerId);
    const manager = managers.value.find((m) => m.user_id === newManagerId);
    pendingDiscountRequest.value = { id: res.data.id, managerId: newManagerId, managerName: manager?.full_name || manager?.username };
    emit('discount-requested');
  } catch (err) {
    discountRequestError.value = err.response?.data?.detail || "Impossible de réassigner la demande de réduction.";
    console.error('Erreur réassignation demande de réduction:', err);
  } finally {
    isReassigning.value = false;
  }
};
</script>
