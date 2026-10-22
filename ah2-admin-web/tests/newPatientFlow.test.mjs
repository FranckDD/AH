import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
    pollPatientCode,
    codeDialogState,
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
    assert.match(list, /showsCodeDialog\(/);
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

// --- Secrétaire : le code s'affiche aussi, mais jamais le formulaire de paramètres (action médicale) ---
import { showsCodeDialog, goesToVitalsAfterCode, shouldRefreshAfterSync } from '../src/utils/newPatientFlow.js';

test('showsCodeDialog : infirmière et secrétaire voient le code d’un patient qu’elles viennent de créer', () => {
    assert.equal(showsCodeDialog('nurse', { localUuid: 'u' }), true);
    assert.equal(showsCodeDialog('Nurse', { localUuid: 'u' }), true);
    assert.equal(showsCodeDialog('secretaire', { localUuid: 'u' }), true);
    assert.equal(showsCodeDialog('medecin', { localUuid: 'u' }), false);
    assert.equal(showsCodeDialog('admin', { localUuid: 'u' }), false);
    assert.equal(showsCodeDialog('secretaire', null), false);
    assert.equal(showsCodeDialog('secretaire', {}), false);
    assert.equal(showsCodeDialog(undefined, { localUuid: 'u' }), false);
});

test('goesToVitalsAfterCode : seule l’infirmière enchaîne sur le formulaire de paramètres (pas la secrétaire)', () => {
    assert.equal(goesToVitalsAfterCode('nurse'), true);
    assert.equal(goesToVitalsAfterCode('Nurse'), true);
    assert.equal(goesToVitalsAfterCode('secretaire'), false);
    assert.equal(goesToVitalsAfterCode('medecin'), false);
    assert.equal(goesToVitalsAfterCode(undefined), false);
});

// --- Liste : recharger quand un patient « en attente » vient d'être confirmé par le serveur ---
test('shouldRefreshAfterSync : recharge quand le nombre de patients en attente diminue', () => {
    assert.equal(shouldRefreshAfterSync(1, 0), true);
    assert.equal(shouldRefreshAfterSync(3, 2), true);
    assert.equal(shouldRefreshAfterSync(0, 0), false);
    assert.equal(shouldRefreshAfterSync(0, 1), false); // un nouveau patient en attente : rien à recharger
    assert.equal(shouldRefreshAfterSync(2, 2), false);
    assert.equal(shouldRefreshAfterSync(null, 0), false); // premier relevé : pas de comparaison
    assert.equal(shouldRefreshAfterSync(undefined, 1), false);
});

test('PatientList : le code s’affiche aussi pour la secrétaire, et la liste se recharge quand l’envoi aboutit', () => {
    assert.match(list, /showsCodeDialog\(authStore\.userRole, created\)/);
    assert.match(list, /goesToVitalsAfterCode\(authStore\.userRole\)/);
    assert.match(list, /shouldRefreshAfterSync\(/);
    assert.match(list, /db\.watch\(/);
    assert.match(list, /signal: watchController\.signal/);
    assert.match(list, /watchController\.abort\(\)/);
});

test('PatientList : la secrétaire n’ouvre jamais le formulaire de paramètres (MedicalRecordModal derrière le test de rôle)', () => {
    const onOk = list.slice(list.indexOf('const onCodeOk'), list.indexOf('const handleRecordSave'));
    assert.match(onOk, /if \(!goesToVitalsAfterCode\(authStore\.userRole\)\)/);
    assert.ok(onOk.indexOf('goesToVitalsAfterCode') < onOk.indexOf('recordPrefill.value ='), 'le test de rôle doit précéder l’ouverture du formulaire');
});

// --- Patient refusé par le serveur (doublon de numéro d'identité) : la fenêtre doit le dire ---
import { quarantineReason } from '../src/utils/newPatientFlow.js';

test('codeDialogState : un patient refusé n’a jamais de code, la fenêtre le dit au lieu d’attendre', () => {
    assert.equal(codeDialogState({ code: '', rejected: true }), 'rejected');
    assert.equal(codeDialogState({ code: '', rejected: true, offline: true, timedOut: true }), 'rejected');
    assert.equal(codeDialogState({ code: 'P-1', rejected: true }), 'ready'); // un code reçu l'emporte toujours
    assert.equal(codeDialogState({ code: '', rejected: false, offline: true }), 'offline');
});

test('quarantineReason : texte du serveur, liste de validation, vide', () => {
    assert.equal(quarantineReason('Un patient avec le même national_id existe déjà.'), 'Un patient avec le même national_id existe déjà.');
    assert.equal(
        quarantineReason(JSON.stringify([{ loc: ['body', 'birth_date'], msg: 'Input should be a valid date' }])),
        'birth_date : Input should be a valid date',
    );
    assert.equal(quarantineReason(JSON.stringify([{ loc: ['body', 'a'], msg: 'x' }, { loc: ['body', 'b'], msg: 'y' }])), 'a : x ; b : y');
    assert.equal(quarantineReason(''), '');
    assert.equal(quarantineReason(null), '');
    assert.equal(quarantineReason(undefined), '');
    assert.equal(quarantineReason('[pas du json'), '[pas du json');
});

test('NewPatientCodeModal : surveille la quarantaine du patient et le signale (sans rester sur « en attente »)', () => {
    assert.match(modal, /sync_quarantine/);
    assert.match(modal, /kind = 'patient' AND local_id = \?/);
    assert.match(modal, /db\.watch\(/);
    assert.match(modal, /rejected:\s*rejected\.value|rejected: rejected\.value/);
    assert.match(modal, /controller\.abort\(\)/);
    assert.match(modal, /failuresPath/);
    assert.match(modal, /dialogState === 'rejected'/);
});

test('PatientList : un patient refusé ne déclenche jamais le formulaire de paramètres et la liste est rechargée', () => {
    const onOk = list.slice(list.indexOf('const onCodeOk'), list.indexOf('const handleRecordSave'));
    assert.match(onOk, /rejected/);
    assert.ok(onOk.indexOf('rejected') < onOk.indexOf('recordPrefill.value ='), 'le refus doit être testé avant d’ouvrir le formulaire');
    assert.match(list, /:failuresPath="failuresPath"/);
    assert.match(list, /\/secretariat\/sync-failures/);
    assert.match(list, /\/medical\/sync-failures/);
});

test('clés newPatient.* du refus en FR et EN', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        for (const k of ['title_rejected', 'rejected', 'rejected_unknown', 'rejected_help', 'see_failures']) {
            assert.equal(typeof msgs[locale].newPatient[k], 'string', `${locale}.newPatient.${k}`);
            assert.doesNotMatch(msgs[locale].newPatient[k], /[—–…·]/);
        }
    }
    assert.match(msgs.fr.newPatient.rejected, /\{reason\}/);
});
