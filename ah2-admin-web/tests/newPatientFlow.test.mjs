import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
    pollPatientCode,
    codeDialogState,
    runsNewPatientFlow,
    patientPrefillFromCreated,
} from '../src/utils/newPatientFlow.js';
import { getPostLoginPath, resolveRootPath } from '../src/utils/postLoginRoute.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

// --- accueil de l'infirmière ---
test('l’infirmière arrive sur la liste des patients, le médecin garde son tableau de bord', () => {
    assert.equal(getPostLoginPath('nurse'), '/medical/patients');
    assert.equal(getPostLoginPath('Nurse'), '/medical/patients');
    assert.equal(resolveRootPath('nurse', true), '/medical/patients');
    assert.equal(getPostLoginPath('medecin'), '/medical/doctors');
    assert.equal(resolveRootPath('medecin', true), '/medical/doctors');
});

test('la page d’accueil de l’infirmière est une route que son rôle peut ouvrir', () => {
    const src = readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8');
    const i = src.indexOf("name: 'medical-patients'");
    assert.ok(i > 0);
    const block = src.slice(i, src.indexOf('}', src.indexOf('meta:', i) + 20) + 1);
    assert.match(block, /roles:\s*\[[^\]]*ROLES\.NURSE/);
});

// --- polling du code ---
function fakeClock() {
    let t = 0;
    return { now: () => t, sleep: async (ms) => { t += ms; } };
}

test('pollPatientCode : renvoie le code dès que le serveur répond', async () => {
    const clock = fakeClock();
    let calls = 0;
    const fetchOnce = async () => (++calls < 3 ? null : { patient_id: 7, code_patient: 'P-0007' });
    const res = await pollPatientCode(fetchOnce, { timeoutMs: 20000, intervalMs: 1000, ...clock });
    assert.deepEqual(res, { patient_id: 7, code_patient: 'P-0007' });
    assert.equal(calls, 3);
});

test('pollPatientCode : abandonne après le délai (null), sans exception', async () => {
    const clock = fakeClock();
    let calls = 0;
    const res = await pollPatientCode(async () => { calls++; return null; }, { timeoutMs: 5000, intervalMs: 1000, ...clock });
    assert.equal(res, null);
    assert.ok(calls >= 5 && calls <= 7, `calls=${calls}`);
});

test('pollPatientCode : une erreur réseau ne casse pas la boucle', async () => {
    const clock = fakeClock();
    let calls = 0;
    const fetchOnce = async () => {
        if (++calls < 3) throw new Error('network');
        return { patient_id: 1, code_patient: 'X' };
    };
    assert.deepEqual(await pollPatientCode(fetchOnce, { timeoutMs: 20000, intervalMs: 1000, ...clock }), { patient_id: 1, code_patient: 'X' });
});

test('pollPatientCode : s’arrête quand le signal est annulé', async () => {
    const clock = fakeClock();
    const ctrl = new AbortController();
    let calls = 0;
    const res = await pollPatientCode(
        async () => { if (++calls === 2) ctrl.abort(); return null; },
        { timeoutMs: 60000, intervalMs: 1000, signal: ctrl.signal, ...clock },
    );
    assert.equal(res, null);
    assert.ok(calls <= 3, `calls=${calls}`);
});

test('pollPatientCode : une réponse sans code est ignorée', async () => {
    const clock = fakeClock();
    let calls = 0;
    const fetchOnce = async () => (++calls < 2 ? { patient_id: 3, code_patient: null } : { patient_id: 3, code_patient: 'P-3' });
    assert.equal((await pollPatientCode(fetchOnce, { timeoutMs: 20000, intervalMs: 1000, ...clock })).code_patient, 'P-3');
});

// --- état de la fenêtre ---
test('codeDialogState : priorité code > hors ligne > en retard > attente', () => {
    assert.equal(codeDialogState({ code: 'P-1', offline: true, timedOut: true }), 'ready');
    assert.equal(codeDialogState({ code: '', offline: true, timedOut: false }), 'offline');
    assert.equal(codeDialogState({ code: null, offline: true, timedOut: true }), 'offline');
    assert.equal(codeDialogState({ code: '', offline: false, timedOut: true }), 'late');
    assert.equal(codeDialogState({ code: '', offline: false, timedOut: false }), 'waiting');
    assert.equal(codeDialogState({}), 'waiting');
    assert.equal(codeDialogState(), 'waiting');
});

// --- qui déclenche le parcours ---
test('runsNewPatientFlow : infirmière seulement, patient créé localement seulement', () => {
    assert.equal(runsNewPatientFlow('nurse', { localUuid: 'u' }), true);
    assert.equal(runsNewPatientFlow('Nurse', { localUuid: 'u' }), true);
    assert.equal(runsNewPatientFlow('medecin', { localUuid: 'u' }), false);
    assert.equal(runsNewPatientFlow('secretaire', { localUuid: 'u' }), false);
    assert.equal(runsNewPatientFlow('nurse', null), false);
    assert.equal(runsNewPatientFlow('nurse', {}), false);
    assert.equal(runsNewPatientFlow(undefined, { localUuid: 'u' }), false);
});

// --- pré-remplissage du formulaire de paramètres ---
test('patientPrefillFromCreated : code connu -> identifiant serveur ; sinon uuid local', () => {
    assert.deepEqual(
        patientPrefillFromCreated({ localUuid: 'u1', patientId: 9, code: 'P-9', firstName: 'Awa', lastName: 'Ngo' }),
        { patientId: 9, patientUuid: null, code: 'P-9', firstName: 'Awa', lastName: 'Ngo' },
    );
    assert.deepEqual(
        patientPrefillFromCreated({ localUuid: 'u1', patientId: null, code: '', firstName: 'Awa', lastName: 'Ngo' }),
        { patientId: null, patientUuid: 'u1', code: '', firstName: 'Awa', lastName: 'Ngo' },
    );
});

// --- contrat des composants ---
const list = readFileSync(new URL('../src/views/modules/patients/PatientList.vue', import.meta.url), 'utf8');
const modal = readFileSync(new URL('../src/components/patients/NewPatientCodeModal.vue', import.meta.url), 'utf8');
const record = readFileSync(new URL('../src/components/medical-records/MedicalRecordModal.vue', import.meta.url), 'utf8');

test('PatientList : le médecin garde le comportement existant (fiche du patient créé)', () => {
    assert.match(list, /router\.push\(`\$\{route\.path\}\/\$\{created\.localUuid\}`\)/);
    assert.match(list, /runsNewPatientFlow\(/);
});

test('la fenêtre du code ne se ferme que par OK (ni clic à côté ni Échap)', () => {
    assert.doesNotMatch(modal, /@click\.self/);
    assert.doesNotMatch(modal, /keydown\.esc|Escape/);
    assert.match(modal, /emit\('ok'/);
});

test('MedicalRecordModal : nouvelle prop facultative, comportement par défaut inchangé', () => {
    assert.match(record, /defaultNeedsDoctorReview:\s*\{\s*type:\s*Boolean,\s*default:\s*false/);
    assert.match(record, /needsDoctorReview:\s*props\.defaultNeedsDoctorReview/);
});

const KEYS = [
    'title', 'patientLabel', 'codeLabel', 'copy', 'copied', 'noteIt', 'waiting', 'offline',
    'late', 'ok', 'saved',
];

test('clés newPatient.* présentes en FR et EN', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        for (const k of KEYS) {
            assert.equal(typeof msgs[locale].newPatient?.[k], 'string', `${locale}.newPatient.${k} manquante`);
        }
    }
    assert.match(msgs.fr.newPatient.offline, /Code attribué à la synchronisation, il apparaîtra dans la liste/);
});
