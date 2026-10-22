import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const modal = readFileSync(new URL('../src/components/caisse/CaisseInvoiceModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));
const scriptOf = (src) => src.slice(src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : calculs, validations et forme de la facture envoyée (aucun changement de montant) ---
check('CaisseInvoiceModal (script)', scriptOf(modal), [
    // calculs : tout passe par invoiceTotals
    "import { computeInvoiceTotals } from '@/utils/invoiceTotals';", 'computeInvoiceTotals({', 'grossRaw: totalAmount.value,',
    "lines: lines.value.map((l) => ({ item_type: l.itemType, line_total: lineTotal(l) })),",
    'isStaff: selectedPatient.value?.is_staff === true,', 'rules: staffRules.value,', 'advance: advanceAmount.value,',
    'const lineTotal = (line) => (Number(line.quantity) || 0) * (Number(line.unitPrice) || 0);',
    'lines.value.reduce((sum, l) => sum + lineTotal(l), 0)',
    // validations
    'const staffStatusUnknown = computed(() => selectedPatient.value?.is_staff === null);',
    'invoiceTotals.value.rulesMissing && !staffRulesLoading.value',
    "if (line.itemType === 'Service') return line.label.trim().length > 0 && lineTotal(line) > 0 && qtyOk;",
    'return line.refId !== null && lineTotal(line) > 0 && qtyOk;',
    'Number.isInteger(Number(line.quantity)) && Number(line.quantity) > 0',
    'return patientOk && linesOk && totalAmount.value > 0 && advanceOk && !invoiceTotals.value.rulesMissing && !staffStatusUnknown.value;',
    'const advanceOk = invoiceTotals.value.advanceOk;',
    'selectedPatient.value?.is_staff === true', 'invoiceTotals.value.staffDiscountAmount === 0',
    // forme de la facture envoyée
    'amount: invoiceTotals.value.net,', 'staff_discount_amount: invoiceTotals.value.staffDiscountAmount,',
    'advance_amount: Number(advanceAmount.value) || 0,', 'payment_method: paymentMethod.value,', 'transaction_type: transactionType.value,',
    'note: note.value?.trim() || null,', 'item_type: l.itemType,', "item_ref_id: l.itemType === 'Service' ? 0 : l.refId,",
    'unit_price: Number(l.unitPrice) || 0,', 'quantity: Number(l.quantity) || 1,', 'line_total: lineTotal(l),',
    "note: l.itemType === 'Service' ? l.label.trim() : (l.refLabel || null),",
    'payload.patient_id = selectedPatient.value.patient_id;', 'payload.patient_label = null;', 'payload.patient_id = null;', 'payload.patient_label = patientLabel.value.trim();',
    "emit('save', buildInvoiceData(), resolvedPatientDisplayName());", 'if (!isFormValid.value) return;',
    // recherches
    'CaisseGateway.searchPatients(patientSearchQuery.value)', 'CaisseGateway.searchProducts(line.searchQuery)', 'CaisseGateway.searchConsultations(line.searchQuery)',
    'LabGateway.getAllExams()', 'setTimeout(async () => {', '}, 300);',
    "line.unitPrice = Number(product.price) || 0;", 'line.knownStock = product.quantity != null ? Number(product.quantity) : null;',
    "line.unitPrice = Number(consultation.fr_amount_paid) || 0;", 'line.unitPrice = Number(exam.prix) || 0;',
    // réduction manuelle
    'DiscountRequestGateway.listManagers()', 'DiscountRequestGateway.create(buildInvoiceData(), selectedManagerId.value)',
    'DiscountRequestGateway.cancel(pendingDiscountRequest.value.id, newManagerId)',
    "if (!isFormValid.value || !selectedManagerId.value || Number(advanceAmount.value) > 0) return;",
    "emit('discount-requested');", 'StaffDiscountGateway.list()', 'rows.filter((r) => r.is_active)',
    "defineEmits(['close', 'save', 'discount-requested'])",
    'isSaving: { type: Boolean, default: false },', "errorMessage: { type: String, default: '' },",
]);

check('CaisseInvoiceModal (gabarit)', templateOf(modal), [
    // types de ligne
    "addLine('Médicament')", "addLine('Consultation')", "addLine('Examen')", "addLine('Service')",
    "line.itemType === 'Médicament'", "line.itemType === 'Consultation'", "line.itemType === 'Examen'", "line.itemType === 'Service'",
    '@click="removeLine(idx)"', 'v-for="(line, idx) in lines"',
    // champs de saisie
    'v-model="patientSearchQuery"', '@input="onPatientSearchInput"', '@click="selectPatient(p)"', 'v-model="patientLabel"', '@click="selectedPatient = null"',
    'v-model="line.searchQuery"', "@input=\"onLineSearchInput(line, 'product')\"", "@input=\"onLineSearchInput(line, 'consultation')\"",
    '@click="selectProductLine(line, prod)"', '@click="selectConsultationLine(line, cons)"', '@click="selectExamLine(line, exam)"', 'examSearchResults(line)',
    'v-model="line.label"', 'v-model.number="line.quantity"', 'v-model.number="line.unitPrice"', ':disabled="line.itemType === \'Consultation\'"',
    'formatCurrency(lineTotal(line))', 'line.knownStock !== null && Number(line.quantity) > line.knownStock',
    'v-model="transactionType"', 'v-model="paymentMethod"', 'v-model.number="advanceAmount"', ':max="invoiceTotals.net"', 'v-model="note"',
    'value="CONSULTATION"', 'value="PHARMACY"', 'value="HOSPITALIZATION"', 'value="LAB"', 'value="DETOX"', 'value="OTHER"',
    'value="Espèces"', 'value="Mobile Money"', 'value="Virement"', 'value="Chèque"',
    // montants affichés = valeurs déjà calculées
    'formatCurrency(invoiceTotals.net)', 'formatCurrency(invoiceTotals.gross)', 'formatCurrency(invoiceTotals.staffDiscountAmount)',
    'invoiceTotals.staffDiscountAmount > 0',
    // avertissements
    'v-if="staffStatusUnknown"', 'v-if="showRulesUnavailable"', 'v-if="showNoRuleApplies"', "t('staffDiscount.status_unknown')",
    "t('staffDiscount.rules_unavailable')", "t('staffDiscount.no_rule_applies')", "t('staffDiscount.manual_replaces_warning')",
    "t('staffDiscount.gross_total')", "t('staffDiscount.net_total')", "t('staffDiscount.invoice_line')", 'v-if="errorMessage"', '{{ errorMessage }}',
    // réduction manuelle (secrétaire uniquement)
    "authStore.hasRole(['secretaire']) && !pendingDiscountRequest", 'v-model="selectedManagerId"', 'v-for="m in managers"',
    '@click="handleRequestDiscount"', '@click="cancelAndReassign"', 'v-if="pendingDiscountRequest"', 'v-if="discountRequestError"',
    ':disabled="isReassigning || !selectedManagerId || selectedManagerId === pendingDiscountRequest.managerId"',
    ':disabled="isSaving || isRequestingDiscount || !isFormValid || !selectedManagerId || Number(advanceAmount) > 0"',
    ':disabled="isSaving || !isFormValid || !!pendingDiscountRequest"', '@click="handleSubmit"', '@click="$emit(\'close\')"',
    "t('caisse.invoice_modal.pending_approval', { name: pendingDiscountRequest.managerName })",
]);

test('toutes les clés caisse.*, finance.*, staffDiscount.* et caisseInvoice.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of modal.matchAll(/['"`(]((?:caisse|finance|staffDiscount|caisseInvoice)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size > 25);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte : composants ui/, accessibilité, aucun calcul dans le gabarit (rouge tant que non refondu) ---
test('CaisseInvoiceModal : composants ui/ (panneau, sections, champs, barre d’actions)', () => {
    assert.match(modal, /from '@\/components\/ui'/);
    for (const c of ['FullScreenPanel', 'FormSection', 'FormField', 'ActionBar', 'AppButton']) {
        assert.match(modal, new RegExp(`\\b${c}\\b`), c);
    }
});

test('CaisseInvoiceModal : le total reste visible sous lg (dans la barre du bas)', () => {
    const footer = modal.slice(modal.indexOf('<template #footer>'));
    assert.match(footer, /formatCurrency\(invoiceTotals\.net\)/);
});

test('CaisseInvoiceModal : aucun calcul de montant dans le gabarit', () => {
    const tpl = templateOf(modal);
    assert.doesNotMatch(tpl, /\.reduce\(|Number\([^)]*\)\s*[*+\-/]\s*Number\(/);
    assert.doesNotMatch(tpl, /\*\s*line\.|line\.\w+\s*\*/);
});

test('CaisseInvoiceModal : jetons du thème, texte >= 13 px, aucun caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(modal, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
    assert.doesNotMatch(modal, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(modal), /[—–…·−]/);
});

test('clés caisseInvoice.* en FR et EN', () => {
    const keys = ['subtitle', 'patient_selected', 'patient_none', 'lines_hint', 'lines_count', 'total_card', 'advance_unit', 'stock_warning',
        'advance_blocked', 'remove_line', 'line_number', 'discount_section', 'payment_section', 'lines_label'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].caisseInvoice?.[k];
            assert.equal(typeof v, 'string', `${locale}.caisseInvoice.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.caisseInvoice.${k}`);
        }
    }
});
