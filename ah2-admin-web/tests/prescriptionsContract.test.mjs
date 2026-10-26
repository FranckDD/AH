import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { endUrgency } from '../src/utils/prescriptionEnd.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const list = read('views/modules/prescriptions/PrescriptionsList.vue');
const modal = read('components/prescriptions/PrescriptionModal.vue');
const patientList = read('components/patients/medical/PrescriptionList.vue');

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Liste : appels du store, lecture seule des consultations passées, actions ---
check('PrescriptionsList', list, [
    'prescriptionStore.fetchPrescriptions()', 'prescriptionStore.fetchExamTypes()',
    'prescriptionStore.setFilters({ searchQuery: val })', 'prescriptionStore.setFilters({ dateFrom: val })',
    'prescriptionStore.setFilters({ dateTo: val })', 'prescriptionStore.setPage(page)',
    'prescriptionStore.updatePrescription(editingPrescription.value.prescription_id, data)',
    'prescriptionStore.createPrescription(data)', 'prescriptionStore.deletePrescription(presc.prescription_id)',
    "confirm(t('prescriptions.confirm_delete'))", 'isPrescriptionEditable(presc)',
    "'medical.readonly.prescription_locked'", "'medical.readonly.badge'",
    ':disabled="!presc.prescription_id"', "'En attente de synchronisation'",
    'presc.is_lab_order', 'presc.lab_exams_list', 'presc.medication', 'presc.dosage', 'presc.frequency',
    'presc.duration', 'presc.start_date', 'presc.end_date', 'presc.prescribed_by_name',
    ':prescription="editingPrescription"', '@save="handleSave"', '@close="closeModal"',
    'prescriptionStore.pagination.total_pages', 'openCreateModal', 'openEditModal(presc)',
]);

// --- Formulaire : chaque champ envoyé, chaque règle ---
check('PrescriptionModal (champs envoyés)', modal, [
    "defineEmits(['close', 'save'])", "emit('save', {",
    'patientId: patientId.value', 'patientUuid: patientUuid.value', 'medicalRecordId: medicalRecordId.value',
    'isLabOrder: form.isLabOrder', "medication: form.isLabOrder ? '' : form.medication",
    "dosage: form.isLabOrder ? '' : form.dosage", "frequency: form.isLabOrder ? '' : form.frequency",
    "duration: form.isLabOrder ? '' : form.duration", 'startDate: form.startDate',
    "endDate: form.isLabOrder ? '' : form.endDate", 'notes: form.notes',
    'labExamsList: form.isLabOrder ? form.labExamsList : []',
]);

check('PrescriptionModal (champs saisis et règles)', modal, [
    'v-model="patientCode"', '@blur="lookupPatient"', 'v-model="form.isLabOrder"', 'v-model="form.medication"',
    'v-model="form.dosage"', 'v-model="form.frequency"', 'v-model="form.duration"', 'v-model="form.endDate"',
    'v-model="form.startDate"', 'v-model="form.notes"', 'v-model="examFilter"', 'v-model="form.labExamsList"',
    ':readonly="isEdit || !!prefilledPatient"', 'v-if="!form.isLabOrder"', 'v-for="exam in filteredExamTypes"',
    "notifyText(t('prescriptions.modal.patient_not_found'))", "notifyText(t('prescriptions.modal.medication_required'))",
    "notifyText(t('prescriptions.modal.exams_required'))", "notifyText(t('prescriptions.modal.date_order_error'))",
    'form.startDate > form.endDate', 'await ensureLookup();', 'prefilledMedicalRecordId', 'type: [Number, String]',
    'props.prefilledPatient', 'setFromExisting(props.prefilledPatient)', 'prescriptionStore.fetchExamTypes()',
    'required', 'type="date"',
]);

check('PrescriptionList (fiche patient)', patientList, [
    'prescriptions: { type: Array', 'presc.medication', 'presc.dosage', 'presc.frequency', 'presc.duration',
    'presc.start_date', 'presc.prescribed_by_name', 'presc.status', 'Aucune prescription enregistrée.',
]);

// --- Ancienneté de la date de fin (urgence de renouvellement) ---
const NOW = new Date(2026, 9, 22, 15, 30);

test('endUrgency : échue, aujourd’hui, bientôt, plus tard, invalide', () => {
    assert.deepEqual(endUrgency('2026-10-20', NOW), { kind: 'expired', tone: 'neutral', days: -2 });
    assert.deepEqual(endUrgency('2026-10-22', NOW), { kind: 'today', tone: 'danger', days: 0 });
    assert.deepEqual(endUrgency('2026-10-25', NOW), { kind: 'soon', tone: 'danger', days: 3 });
    assert.deepEqual(endUrgency('2026-10-29', NOW), { kind: 'soon', tone: 'warning', days: 7 });
    assert.deepEqual(endUrgency('2026-11-05', NOW), { kind: 'soon', tone: 'info', days: 14 });
    assert.deepEqual(endUrgency('2026-11-06', NOW), { kind: 'later', tone: 'success', days: 15 });
    assert.deepEqual(endUrgency('2026-10-22T08:00:00', NOW), { kind: 'today', tone: 'danger', days: 0 });
    for (const bad of [null, undefined, '', 'abc']) assert.equal(endUrgency(bad, NOW), null);
});

test('endUrgency : mêmes seuils que l’ancien écran (3, 7 et 14 jours)', () => {
    const t = (offset) => {
        const d = new Date(2026, 9, 22 + offset);
        const s = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        return endUrgency(s, NOW).tone;
    };
    assert.deepEqual([3, 4, 7, 8, 14, 15].map(t), ['danger', 'warning', 'warning', 'info', 'info', 'success']);
});

// --- Clés i18n ---
test('chaque clé prescriptions.* / medical.* citée littéralement existe en FR et EN', () => {
    const used = new Set();
    for (const src of [list, modal, patientList]) {
        for (const m of src.matchAll(/['"`(]((?:prescriptions|medical)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 25);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

test('clés ajoutées en FR et EN, avec pluriel des jours', () => {
    const modalKeys = ['section_patient', 'section_prescription', 'section_dates', 'help_patient_code', 'help_frequency', 'help_duration', 'help_end_date'];
    for (const locale of ['fr', 'en']) {
        for (const k of modalKeys) assert.equal(typeof msgs[locale].prescriptions.modal[k], 'string', `${locale}.modal.${k}`);
        for (const k of ['end_expired', 'end_today', 'end_in_days', 'prev_page', 'next_page']) {
            assert.equal(typeof msgs[locale].prescriptions[k], 'string', `${locale}.${k}`);
        }
    }
    const { t } = i18n.global;
    assert.equal(t('prescriptions.end_in_days', { n: 1 }, { locale: 'fr', plural: 1 }), 'Dans 1 jour');
    assert.equal(t('prescriptions.end_in_days', { n: 3 }, { locale: 'fr', plural: 3 }), 'Dans 3 jours');
    assert.equal(t('prescriptions.end_in_days', { n: 3 }, { locale: 'en', plural: 3 }), 'In 3 days');
});

// --- Refonte ---
test('liste : tableau responsive, badges d’état, composants ui/', () => {
    assert.match(list, /ResponsiveTable/);
    assert.match(list, /StatusBadge/);
    assert.match(list, /@\/components\/ui/);
    assert.match(list, /endUrgency/);
});

test('formulaire : panneau, sections nommées, aide, barre d’actions, Enregistrer principal et Annuler discret', () => {
    assert.match(modal, /FullScreenPanel/);
    assert.match(modal, /FormSection/);
    assert.match(modal, /ActionBar/);
    assert.match(modal, /FormField/);
    assert.match(modal, /type="submit"/);
    assert.match(modal, /variant="ghost"/);
    for (const key of ['section_patient', 'section_prescription', 'section_dates', 'help_frequency', 'help_duration', 'help_end_date']) {
        assert.ok(modal.includes(`prescriptions.modal.${key}`), `${key} non utilisée`);
    }
});

test('aucune couleur de marque ou d’état en dur', () => {
    for (const [name, src] of [['list', list], ['modal', modal], ['patientList', patientList]]) {
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${name}: hexadécimal`);
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/, `${name}: couleur Tailwind brute`);
    }
});

test('texte affiché : ni tiret long, ni point médian, ni points de suspension typographiques', () => {
    for (const [name, src] of [['list', list], ['modal', modal], ['patientList', patientList]]) {
        const template = src.slice(0, src.indexOf('<script'));
        assert.doesNotMatch(template, /[—–…·]/, `${name}: caractère typographique dans le gabarit`);
        assert.doesNotMatch(src.slice(src.indexOf('<script')), /\|\|\s*'[—–]'/, `${name}: repli en tiret long`);
    }
});

test('texte jamais inférieur à 13 px', () => {
    for (const [name, src] of [['list', list], ['modal', modal], ['patientList', patientList]]) {
        assert.doesNotMatch(src, /text-\[(1[0-2]|[0-9])px\]/, name);
        assert.doesNotMatch(src, /text-xs/, name);
    }
});
