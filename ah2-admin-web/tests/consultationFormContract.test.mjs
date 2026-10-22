import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { nextFocusIndex } from '../src/utils/ui.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const modal = read('components/medical-records/MedicalRecordModal.vue');
const list = read('views/modules/medical-records/MedicalRecordsList.vue');
const timeline = read('components/patients/medical/MedicalRecordTimeline.vue');
const vitals = read('components/patients/medical/VitalsCard.vue');
const panelPath = '../src/components/ui/FullScreenPanel.vue';
const panel = existsSync(new URL(panelPath, import.meta.url)) ? readFileSync(new URL(panelPath, import.meta.url), 'utf8') : '';

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Formulaire de consultation : chaque champ envoyé au store, chaque règle de validation ---
const SAVE_FIELDS = [
    'patientId: patientId.value', 'patientUuid: patientUuid.value', 'appointmentId: props.appointmentId',
    'consultationDate: form.consultationDate', 'motifCode: form.motifCode', 'maritalStatus: form.maritalStatus',
    'severity: form.severity', 'bp: form.bp', 'temperature: temp.value', 'weight: weight.value', 'height: height.value',
    'medicalHistory: form.medicalHistory', 'allergies: form.allergies', 'symptoms: form.symptoms',
    'diagnosis: form.diagnosis', 'treatment: form.treatment', 'notes: form.notes',
    'needsDoctorReview: form.needsDoctorReview',
    'assignedDoctorId: form.needsDoctorReview ? (form.assignedDoctorId || null) : null',
];

check('MedicalRecordModal (champs envoyés)', modal, ["defineEmits(['close', 'save'])", "emit('save', {", ...SAVE_FIELDS]);

check('MedicalRecordModal (champs saisis)', modal, [
    'v-model="patientCode"', '@blur="lookupPatient"', 'v-model="form.consultationDate"', 'v-model="form.motifCode"',
    'v-model="form.severity"', 'v-model="form.maritalStatus"', 'v-model="form.bp"', 'v-model="form.temperature"',
    'v-model="form.weight"', 'v-model="form.height"', 'v-model="form.medicalHistory"', 'v-model="form.allergies"',
    'v-model="form.symptoms"', 'v-model="form.diagnosis"', 'v-model="form.treatment"', 'v-model="form.notes"',
    'v-model="form.needsDoctorReview"', 'v-model="form.assignedDoctorId"',
]);

check('MedicalRecordModal (règles)', modal, [
    ':readonly="isEdit || !!prefilledPatient"', 'v-if="!isEdit"', 'v-if="form.needsDoctorReview"',
    "parseVital(form.temperature, 30, 45, 'medicalRecords.modal.temperature_range')",
    "parseVital(form.weight, 0, 1000, 'medicalRecords.modal.weight_range')",
    "parseVital(form.height, 30, 250, 'medicalRecords.modal.height_range')",
    "alert(t('medicalRecords.modal.motif_required'))", "alert(t('medicalRecords.modal.patient_not_found'))",
    'await ensureLookup();', '/doctor-dashboard/doctors', 'defaultNeedsDoctorReview', 'props.prefilledPatient',
    'setFromExisting(props.prefilledPatient)', "form.maritalStatus = rec.marital_status || 'Single'",
    'step="0.1"', 'type="date"', 'maritalOptions', 'severityOptions', 'medicalRecordStore.fetchMotifs()',
]);

// --- Liste du dossier médical : lecture seule des consultations passées, filtres, pagination ---
check('MedicalRecordsList', list, [
    'medicalRecordStore.fetchMedicalRecords()', 'medicalRecordStore.fetchMotifs()',
    'medicalRecordStore.setFilters({ searchQuery: val })', 'medicalRecordStore.setFilters({ motifCode: val })',
    'medicalRecordStore.setFilters({ severity: val })', 'medicalRecordStore.setFilters({ dateFrom: val })',
    'medicalRecordStore.setFilters({ dateTo: val })', 'medicalRecordStore.setPage(page)',
    'medicalRecordStore.updateMedicalRecord(editingRecord.value.record_id ?? editingRecord.value.local_id, data)',
    'medicalRecordStore.createMedicalRecord(data)', 'medicalRecordStore.deleteMedicalRecord(rec.record_id)',
    "confirm(t('medicalRecords.confirm_delete'))", 'isRecordEditable(rec, medicalRecordStore.records)',
    "'medical.readonly.badge'", ':disabled="!rec.record_id"', "'En attente de synchronisation'",
    '@save="handleSave"', '@close="closeModal"', 'medicalRecordStore.pagination.total_pages',
]);

// --- Timeline du dossier patient : mêmes événements, même verrou ---
check('MedicalRecordTimeline', timeline, [
    "defineEmits(['edit', 'prescribe'])", "$emit('edit', record)", "$emit('prescribe', record)",
    "authStore.hasRole(['medecin', 'nurse'])", 'isRecordEditable(record, props.records, { samePatient: true })',
    'v-if="canManage && editable(record)"', 'v-if="!editable(record)"', "'medical.readonly.badge'",
    'record.needs_doctor_review', 'record.reviewed_at', 'record.assigned_doctor_id',
    'record.bp', 'record.weight', 'record.temperature', 'record.allergies', 'record.medical_history', 'record.treatment',
    'record.notes || record.symptoms', 'record.created_by_name', "toLocaleDateString('fr-FR'",
]);

check('VitalsCard', vitals, ['label: { type: String, required: true }', 'value:', 'unit:', 'date:', 'icon:', 'colorClass:', 'iconColor:']);

// --- Panneau plein écran ---
test('FullScreenPanel existe et est réexporté', () => {
    assert.ok(panel.length > 0, 'FullScreenPanel.vue manquant');
    assert.match(read('components/ui/index.js'), /FullScreenPanel/);
});

test('FullScreenPanel : fermeture par bouton et Échap, focus piégé, aucun avertissement de saisie inventé', () => {
    assert.match(panel, /Escape/);
    assert.match(panel, /emit\('close'\)/);
    assert.match(panel, /Tab/);
    assert.match(panel, /nextFocusIndex/);
    assert.match(panel, /aria-modal="true"/);
    assert.match(panel, /role="dialog"/);
    assert.doesNotMatch(panel, /beforeunload|unsaved|confirm\(/i);
});

test('FullScreenPanel : plein écran sous lg, grande fenêtre centrée à partir de lg', () => {
    assert.match(panel, /inset-0/);
    assert.match(panel, /lg:max-w-/);
    assert.match(panel, /lg:rounded-card/);
});

test('nextFocusIndex : boucle dans les deux sens', () => {
    assert.equal(nextFocusIndex(0, 3, false), 1);
    assert.equal(nextFocusIndex(2, 3, false), 0);
    assert.equal(nextFocusIndex(0, 3, true), 2);
    assert.equal(nextFocusIndex(1, 3, true), 0);
    assert.equal(nextFocusIndex(-1, 3, false), 0);
    assert.equal(nextFocusIndex(-1, 3, true), 2);
    assert.equal(nextFocusIndex(0, 0, false), -1);
    assert.equal(nextFocusIndex(5, 3, false), 0);
});

// --- Refonte : sections nommées repliables, barre d'actions, composants ui/ ---
test('formulaire en sections nommées repliables avec barre d’actions fixe', () => {
    assert.match(modal, /FullScreenPanel/);
    assert.match(modal, /FormSection/);
    assert.match(modal, /ActionBar/);
    for (const key of ['section_patient', 'section_consultation', 'section_vitals', 'section_history', 'section_exam', 'section_diagnosis', 'section_notes', 'section_triage']) {
        assert.ok(modal.includes(`medicalRecords.modal.${key}`), `${key} non utilisée`);
    }
    assert.ok((modal.match(/collapsible/g) || []).length >= 3, 'les sections longues doivent être repliables');
});

test('libellés au-dessus des champs, astérisque sur les champs obligatoires, aide sous les champs difficiles', () => {
    assert.match(modal, /<FormField[^>]*required/);
    for (const k of ['help_bp', 'help_temperature', 'help_weight', 'help_height']) {
        assert.ok(modal.includes(`medicalRecords.modal.${k}`), `${k} non affichée`);
    }
});

test('Enregistrer est le bouton principal, Annuler est discret', () => {
    assert.match(modal, /type="submit"/);
    assert.match(modal, /variant="ghost"/);
});

test('clés ajoutées présentes en FR et EN', () => {
    const modalKeys = ['section_patient', 'section_history', 'section_exam', 'section_diagnosis', 'help_patient_code', 'help_bp', 'help_temperature', 'help_weight', 'help_height'];
    for (const locale of ['fr', 'en']) {
        for (const k of modalKeys) assert.equal(typeof msgs[locale].medicalRecords.modal[k], 'string', `${locale}.modal.${k}`);
        for (const k of ['prev_page', 'next_page']) assert.equal(typeof msgs[locale].medicalRecords[k], 'string', `${locale}.${k}`);
    }
});

test('chaque clé citée littéralement dans les écrans existe en FR et EN', () => {
    const used = new Set();
    for (const src of [modal, list, timeline, vitals]) {
        for (const m of src.matchAll(/['"`(]((?:medicalRecords|medical)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 20);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

test('aucune couleur de marque ou d’état en dur dans les écrans refondus', () => {
    for (const [name, src] of [['modal', modal], ['list', list], ['timeline', timeline], ['panel', panel]]) {
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${name}: hexadécimal`);
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange)-\d{2,3}\b/, `${name}: couleur Tailwind brute`);
    }
});

test('texte affiché : ni tiret long, ni point médian, ni points de suspension typographiques', () => {
    for (const [name, src] of [['modal', modal], ['list', list], ['timeline', timeline], ['vitals', vitals], ['panel', panel]]) {
        const template = src.slice(0, src.indexOf('<script'));
        assert.doesNotMatch(template, /[—–…·]/, `${name}: caractère typographique dans le gabarit`);
    }
    for (const locale of ['fr', 'en']) {
        assert.doesNotMatch(msgs[locale].medical.readonly.badge, /[—–…·]/);
        assert.doesNotMatch(msgs[locale].medicalRecords.modal.assign_doctor_hint, /[—–…·]/);
    }
});

test('texte jamais inférieur à 13 px dans la timeline et la carte de constantes', () => {
    for (const [name, src] of [['timeline', timeline], ['vitals', vitals]]) {
        assert.doesNotMatch(src, /text-\[(1[0-2]|[0-9])px\]/, name);
        assert.doesNotMatch(src, /text-xs/, name);
    }
});

test('les écrans utilisent la bibliothèque ui/', () => {
    for (const [name, src] of [['modal', modal], ['list', list], ['timeline', timeline]]) {
        assert.match(src, /@\/components\/ui/, `${name}: aucun composant ui/ importé`);
    }
});
