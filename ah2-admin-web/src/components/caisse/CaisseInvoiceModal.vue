<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-xs">
    <div class="relative mx-auto w-full max-w-3xl bg-white shadow-xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
      <div class="px-6 py-4 border-b border-gray-100 bg-green-600 rounded-t-2xl flex justify-between items-center shrink-0">
        <h3 class="text-lg font-bold text-white">{{ t('caisse.invoice_modal.title') }}</h3>
        <button @click="$emit('close')" class="text-green-100 hover:text-white transition">
          <span class="text-2xl font-bold">&times;</span>
        </button>
      </div>

      <div class="p-6 overflow-y-auto space-y-6">
        <!-- PATIENT -->
        <div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
          <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">{{ t('caisse.invoice_modal.section_patient') }}</h4>

          <div v-if="!selectedPatient" class="space-y-2">
            <input v-model="patientSearchQuery" @input="onPatientSearchInput" type="text"
                   :placeholder="t('caisse.invoice_modal.patient_search_placeholder')"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500" />
            <ul v-if="patientResults.length" class="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-40 overflow-y-auto">
              <li v-for="p in patientResults" :key="p.patient_id" @click="selectPatient(p)"
                  class="px-3 py-2 hover:bg-green-50 cursor-pointer text-sm">
                <span class="font-medium">{{ p.first_name }} {{ p.last_name }}</span>
                <span class="text-gray-500 ml-2">{{ p.code_patient }}</span>
              </li>
            </ul>
            <div class="flex items-center gap-2 pt-1">
              <span class="text-xs text-gray-400">{{ t('caisse.invoice_modal.or') }}</span>
              <input v-model="patientLabel" type="text" :placeholder="t('caisse.invoice_modal.patient_label_placeholder')"
                     class="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-green-500 focus:border-green-500" />
            </div>
          </div>

          <div v-else class="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-3 py-2">
            <span class="text-sm font-medium text-green-900">
              {{ selectedPatient.first_name }} {{ selectedPatient.last_name }} ({{ selectedPatient.code_patient }})
            </span>
            <button type="button" @click="selectedPatient = null" class="text-xs text-green-700 hover:underline">
              {{ t('caisse.invoice_modal.change_patient') }}
            </button>
          </div>
        </div>

        <!-- LIGNES -->
        <div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
          <div class="flex justify-between items-center mb-3">
            <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider">{{ t('caisse.invoice_modal.section_items') }}</h4>
            <div class="flex gap-2">
              <button type="button" @click="addLine('Médicament')" class="text-xs px-2 py-1 bg-white border border-gray-300 rounded-sm hover:bg-gray-100">
                + {{ t('caisse.invoice_modal.line_type_pharmacy') }}
              </button>
              <button type="button" @click="addLine('Consultation')" class="text-xs px-2 py-1 bg-white border border-gray-300 rounded-sm hover:bg-gray-100">
                + {{ t('caisse.invoice_modal.line_type_consultation') }}
              </button>
              <button type="button" @click="addLine('Examen')" class="text-xs px-2 py-1 bg-white border border-gray-300 rounded-sm hover:bg-gray-100">
                + {{ t('caisse.invoice_modal.line_type_exam') }}
              </button>
              <button type="button" @click="addLine('Service')" class="text-xs px-2 py-1 bg-white border border-gray-300 rounded-sm hover:bg-gray-100">
                + {{ t('caisse.invoice_modal.line_type_service') }}
              </button>
            </div>
          </div>

          <div v-if="lines.length === 0" class="text-sm text-gray-400 italic py-2">
            {{ t('caisse.invoice_modal.no_lines') }}
          </div>

          <div v-for="(line, idx) in lines" :key="line.key" class="bg-white border border-gray-200 rounded-lg p-3 mb-2 space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold uppercase text-gray-500">
                {{ line.itemType === 'Médicament' ? t('caisse.invoice_modal.line_type_pharmacy')
                   : line.itemType === 'Consultation' ? t('caisse.invoice_modal.line_type_consultation')
                   : line.itemType === 'Examen' ? t('caisse.invoice_modal.line_type_exam')
                   : t('caisse.invoice_modal.line_type_service') }}
              </span>
              <button type="button" @click="removeLine(idx)" class="text-red-500 hover:text-red-700">
                <TrashIcon class="h-4 w-4" />
              </button>
            </div>

            <!-- Pharmacie -->
            <div v-if="line.itemType === 'Médicament'">
              <div v-if="!line.refLabel" class="space-y-1">
                <input v-model="line.searchQuery" @input="onLineSearchInput(line, 'product')" type="text"
                       :placeholder="t('caisse.invoice_modal.search_product_placeholder')"
                       class="w-full px-3 py-1.5 border border-gray-300 rounded-sm text-sm" />
                <ul v-if="line.searchResults.length" class="border border-gray-200 rounded-sm divide-y divide-gray-100 max-h-32 overflow-y-auto">
                  <li v-for="prod in line.searchResults" :key="prod.medication_id" @click="selectProductLine(line, prod)"
                      class="px-2 py-1 hover:bg-green-50 cursor-pointer text-sm flex justify-between">
                    <span>{{ prod.drug_name }}</span>
                    <span class="text-gray-500">{{ prod.quantity }} {{ t('caisse.invoice_modal.in_stock') }}</span>
                  </li>
                </ul>
              </div>
              <div v-else class="text-sm font-medium text-gray-800">{{ line.refLabel }}</div>
            </div>

            <!-- Consultation -->
            <div v-if="line.itemType === 'Consultation'">
              <div v-if="!line.refLabel" class="space-y-1">
                <input v-model="line.searchQuery" @input="onLineSearchInput(line, 'consultation')" type="text"
                       :placeholder="t('caisse.invoice_modal.search_consultation_placeholder')"
                       class="w-full px-3 py-1.5 border border-gray-300 rounded-sm text-sm" />
                <ul v-if="line.searchResults.length" class="border border-gray-200 rounded-sm divide-y divide-gray-100 max-h-32 overflow-y-auto">
                  <li v-for="cons in line.searchResults" :key="cons.consultation_id" @click="selectConsultationLine(line, cons)"
                      class="px-2 py-1 hover:bg-green-50 cursor-pointer text-sm">
                    #{{ cons.consultation_id }} — {{ cons.type_consultation || t('caisse.invoice_modal.line_type_consultation') }}
                  </li>
                </ul>
              </div>
              <div v-else class="text-sm font-medium text-gray-800">{{ line.refLabel }}</div>
            </div>

            <!-- Examen labo -->
            <div v-if="line.itemType === 'Examen'">
              <div v-if="!line.refLabel" class="space-y-1">
                <input v-model="line.searchQuery" type="text"
                       :placeholder="t('caisse.invoice_modal.search_exam_placeholder')"
                       class="w-full px-3 py-1.5 border border-gray-300 rounded-sm text-sm" />
                <ul v-if="examSearchResults(line).length" class="border border-gray-200 rounded-sm divide-y divide-gray-100 max-h-32 overflow-y-auto">
                  <li v-for="exam in examSearchResults(line)" :key="exam.id" @click="selectExamLine(line, exam)"
                      class="px-2 py-1 hover:bg-green-50 cursor-pointer text-sm flex justify-between">
                    <span>{{ exam.nom }}</span>
                    <span class="text-gray-500">{{ formatCurrency(exam.prix) }}</span>
                  </li>
                </ul>
              </div>
              <div v-else class="text-sm font-medium text-gray-800">{{ line.refLabel }}</div>
            </div>

            <!-- Service libre -->
            <div v-if="line.itemType === 'Service'">
              <input v-model="line.label" type="text" :placeholder="t('caisse.invoice_modal.service_label_placeholder')"
                     class="w-full px-3 py-1.5 border border-gray-300 rounded-sm text-sm" />
            </div>

            <div class="grid grid-cols-3 gap-2">
              <div>
                <label class="text-xs text-gray-500">{{ t('caisse.invoice_modal.quantity') }}</label>
                <input v-model.number="line.quantity" type="number" min="1" step="1"
                       :disabled="line.itemType === 'Consultation'"
                       class="w-full px-2 py-1 border border-gray-300 rounded-sm text-sm disabled:bg-gray-100" />
              </div>
              <div>
                <label class="text-xs text-gray-500">{{ t('caisse.invoice_modal.unit_price') }}</label>
                <input v-model.number="line.unitPrice" type="number" min="0" step="0.01"
                       class="w-full px-2 py-1 border border-gray-300 rounded-sm text-sm" />
              </div>
              <div>
                <label class="text-xs text-gray-500">{{ t('caisse.invoice_modal.line_total') }}</label>
                <div class="px-2 py-1 text-sm font-semibold">{{ formatCurrency(lineTotal(line)) }}</div>
              </div>
            </div>
            <div v-if="line.itemType === 'Médicament' && line.knownStock !== null && Number(line.quantity) > line.knownStock"
                 class="mt-1 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1">
              Quantité ({{ line.quantity }}) supérieure au stock connu ({{ line.knownStock }}) — la vente reste possible, le serveur vérifiera le stock réel à la synchronisation.
            </div>
          </div>
        </div>

        <!-- PAIEMENT -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.category') }}</label>
            <select v-model="transactionType" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm">
              <option value="CONSULTATION">{{ t('finance.categories.consultation') }}</option>
              <option value="PHARMACY">{{ t('finance.categories.pharmacy') }}</option>
              <option value="HOSPITALIZATION">{{ t('finance.categories.hospitalization') }}</option>
              <option value="LAB">{{ t('finance.categories.lab') }}</option>
              <option value="DETOX">{{ t('finance.categories.detox') }}</option>
              <option value="OTHER">{{ t('finance.categories.other') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.method') }}</label>
            <select v-model="paymentMethod" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm">
              <option value="Espèces">{{ t('finance.payment_methods.cash') }}</option>
              <option value="Mobile Money">{{ t('finance.payment_methods.mobile') }}</option>
              <option value="Virement">{{ t('finance.payment_methods.transfer') }}</option>
              <option value="Chèque">{{ t('finance.payment_methods.check') }}</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('caisse.invoice_modal.advance_amount') }}</label>
            <input v-model.number="advanceAmount" type="number" min="0" :max="totalAmount" step="0.01"
                   class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
          </div>
          <div class="flex flex-col justify-end">
            <span class="text-xs text-gray-500 uppercase font-bold">{{ t('caisse.invoice_modal.total') }}</span>
            <span class="text-2xl font-bold text-gray-900">{{ formatCurrency(totalAmount) }}</span>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.desc') }}</label>
          <textarea v-model="note" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm"></textarea>
        </div>

        <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">
          {{ errorMessage }}
        </div>

        <div v-if="authStore.hasRole(['secretaire']) && !pendingDiscountRequest" class="border-t pt-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('caisse.invoice_modal.discount_recipient') }}</label>
          <select v-model="selectedManagerId" class="block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option :value="null">{{ t('caisse.invoice_modal.discount_select_placeholder') }}</option>
            <option v-for="m in managers" :key="m.user_id" :value="m.user_id">{{ m.full_name || m.username }}</option>
          </select>
        </div>

        <div v-if="pendingDiscountRequest" class="bg-amber-50 border-l-4 border-amber-500 p-3 rounded-sm text-sm text-amber-800">
          <div class="flex items-center justify-between mb-2">
            <span>{{ t('caisse.invoice_modal.pending_approval', { name: pendingDiscountRequest.managerName }) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <select v-model="selectedManagerId" class="flex-1 border border-amber-300 rounded-sm px-2 py-1 text-xs">
              <option v-for="m in managers" :key="m.user_id" :value="m.user_id">{{ m.full_name || m.username }}</option>
            </select>
            <button type="button" @click="cancelAndReassign"
                    :disabled="isReassigning || !selectedManagerId || selectedManagerId === pendingDiscountRequest.managerId"
                    class="text-xs underline text-amber-900 whitespace-nowrap disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed">
              {{ isReassigning ? t('caisse.invoice_modal.requesting') : t('caisse.invoice_modal.cancel_reassign') }}
            </button>
          </div>
        </div>

        <div v-if="discountRequestError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">
          {{ discountRequestError }}
        </div>
      </div>

      <div class="px-6 py-4 border-t border-gray-100 flex justify-end space-x-3 shrink-0">
        <button type="button" @click="$emit('close')" :disabled="isSaving"
                class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition disabled:opacity-50">
          {{ t('finance.modal.cancel') }}
        </button>
        <button
          v-if="authStore.hasRole(['secretaire']) && !pendingDiscountRequest"
          type="button"
          @click="handleRequestDiscount"
          :disabled="isSaving || isRequestingDiscount || !isFormValid || !selectedManagerId || Number(advanceAmount) > 0"
          :title="Number(advanceAmount) > 0 ? 'Aucune avance possible sur une facture soumise à réduction' : ''"
          class="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 font-medium shadow-md transition disabled:opacity-50"
        >
          {{ isRequestingDiscount ? t('caisse.invoice_modal.requesting') : t('caisse.invoice_modal.request_discount') }}
        </button>
        <button type="button" @click="handleSubmit" :disabled="isSaving || !isFormValid || pendingDiscountRequest"
                class="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium shadow-md transition disabled:opacity-50">
          {{ isSaving ? t('caisse.cancel_modal.saving') : t('finance.modal.save') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { CaisseGateway } from '@/services/CaisseGateway';
import { LabGateway } from '@/services/labGateway';
import { DiscountRequestGateway } from '@/services/DiscountRequestGateway';
import { useAuthStore } from '@/stores/auth';
import { TrashIcon } from '@heroicons/vue/24/outline';

const props = defineProps({
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'save', 'discount-requested']);
const { t } = useI18n();
const authStore = useAuthStore();

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
  }));
};
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
  line.unitPrice = Number(consultation.fr_amount_paid) || 0;
  line.searchResults = [];
};

const lineTotal = (line) => (Number(line.quantity) || 0) * (Number(line.unitPrice) || 0);
const totalAmount = computed(() => lines.value.reduce((sum, l) => sum + lineTotal(l), 0));

// --- Paiement ---
const transactionType = ref('CONSULTATION');
const paymentMethod = ref('Espèces');
const advanceAmount = ref(0);
const note = ref('');

const isLineComplete = (line) => {
  const qtyOk = Number.isInteger(Number(line.quantity)) && Number(line.quantity) > 0;
  if (line.itemType === 'Service') return line.label.trim().length > 0 && lineTotal(line) > 0 && qtyOk;
  return line.refId !== null && lineTotal(line) > 0 && qtyOk;
};

const isFormValid = computed(() => {
  const patientOk = selectedPatient.value || patientLabel.value.trim().length > 0;
  const linesOk = lines.value.length > 0 && lines.value.every(isLineComplete);
  const advanceOk = Number(advanceAmount.value) >= 0 && Number(advanceAmount.value) <= totalAmount.value;
  return patientOk && linesOk && totalAmount.value > 0 && advanceOk;
});

const buildInvoiceData = () => {
  const payload = {
    amount: totalAmount.value,
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
