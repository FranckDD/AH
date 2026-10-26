import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const g = i18n.global;
const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');

const KEYS = [
    'patients.code_pending', 'medical.none_reported_empty', 'toxicoScreens.observation_required',
    'toxicoScreens.alert_relapse_title', 'toxicoScreens.alert_relapse_message', 'toxicoScreens.alert_late_title',
    'toxicoScreens.alert_late_message', 'toxicoScreens.unknown_patient',
    'hospitalization.err_admit', 'hospitalization.err_status', 'hospitalization.err_discharge',
    'hospitalization.err_history', 'hospitalization.err_letter',
    'patients.types.clinique', 'patients.types.toxico', 'patients.types.spirituel',
];
test('keys exist in FR and EN and EN values are English', () => {
    for (const k of KEYS) for (const l of ['fr', 'en']) assert.ok(g.te(k, l), `${l}:${k}`);
    assert.equal(g.t('patients.types.clinique', {}, { locale: 'en' }).toUpperCase(), 'CLINICAL');
    assert.equal(g.t('patients.types.toxico', {}, { locale: 'en' }).toUpperCase(), 'TOXICOLOGY');
    assert.equal(g.t('patients.types.spirituel', {}, { locale: 'en' }).toUpperCase(), 'SPIRITUAL');
    assert.equal(g.t('patients.code_pending', {}, { locale: 'en' }).toUpperCase(), 'CODE PENDING');
    assert.equal(g.t('medical.none_reported_empty', {}, { locale: 'en' }), 'None reported (empty record)');
    assert.equal(g.t('toxicoScreens.observation_required', {}, { locale: 'en' }), 'Observation required (min 50 characters)');
});

test('no hard-coded French in the touched sources', () => {
    const hosp = read('src/components/hospitalization/HospitalizationCard.vue');
    assert.doesNotMatch(hosp, /"(Erreur|Impossible)[^"]*"/);
    const tox = read('src/stores/toxicoStore.js');
    assert.doesNotMatch(tox, /Rechute critique|Évaluation en retard|Patient Inconnu/);
    assert.doesNotMatch(read('src/services/ToxicoGateway.js'), /Observation requise/);
    assert.doesNotMatch(read('src/stores/patientStore.js'), /'Code en attente'/);
    assert.doesNotMatch(read('src/stores/patientDossierStore.js'), /'Code en attente'/);
    assert.doesNotMatch(read('src/components/toxico/ToxicoPatientDetailsModal.vue'), /toLocaleDateString\('fr-FR'/);
});

test('consultation depuis un rendez-vous : motif preselectionne', () => {
    const modal = read('src/components/medical-records/MedicalRecordModal.vue');
    assert.match(modal, /APPOINTMENT_MOTIF_CODE = 'rendez-vous'/);
    assert.match(modal, /props\.appointmentId[\s\S]{0,120}form\.motifCode[\s\S]{0,200}form\.motifCode = APPOINTMENT_MOTIF_CODE/);
    assert.match(modal, /await medicalRecordStore\.fetchMotifs\(\)/);
});
