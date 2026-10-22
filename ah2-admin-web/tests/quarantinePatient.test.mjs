import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { discardPlan, buildResendPayload, validateNationalIdCorrection } from '../src/utils/quarantinePatient.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/sync/SyncFailuresView.vue', import.meta.url), 'utf8');
const quarantine = readFileSync(new URL('../src/powersync-client/syncQuarantine.js', import.meta.url), 'utf8');

// --- Supprimer l'entrée : ce qui est effacé localement avec le patient refusé ---
test('discardPlan : chaque ligne retenue est effacée dans sa table locale, rien d’autre', () => {
    const plan = discardPlan([
        { kind: 'medical_record', local_id: 'r1' },
        { kind: 'prescription', local_id: 'p1' },
        { kind: 'lab_result', local_id: 'l1' },
        { kind: 'lab_result_detail', local_id: 'd1' },
    ]);
    assert.deepEqual(plan, [
        { table: 'medical_records', id: 'r1' },
        { table: 'prescriptions', id: 'p1' },
        { table: 'lab_results', id: 'l1' },
        { table: 'lab_result_details', id: 'd1' },
    ]);
});

test('discardPlan : types inconnus, patient lui-même et valeurs vides sont ignorés (jamais un nom de table construit)', () => {
    assert.deepEqual(discardPlan([
        { kind: 'patient', local_id: 'u' },
        { kind: 'inconnu; DROP TABLE patients', local_id: 'x' },
        { kind: 'medical_record', local_id: '' },
        { kind: 'medical_record', local_id: null },
        null,
    ]), []);
    assert.deepEqual(discardPlan(undefined), []);
});

// --- Corriger le numéro d'identité : validation et corps de la requête de renvoi ---
test('validateNationalIdCorrection : vide, identique (casse et espaces ignorés), valide', () => {
    assert.deepEqual(validateNationalIdCorrection('CNI1', ''), { ok: false, error: 'empty' });
    assert.deepEqual(validateNationalIdCorrection('CNI1', '   '), { ok: false, error: 'empty' });
    assert.deepEqual(validateNationalIdCorrection('CNI1', undefined), { ok: false, error: 'empty' });
    assert.deepEqual(validateNationalIdCorrection('CNI1', ' cni1 '), { ok: false, error: 'same' });
    assert.deepEqual(validateNationalIdCorrection(null, 'CNI2'), { ok: true });
    assert.deepEqual(validateNationalIdCorrection('CNI1', 'CNI2'), { ok: true });
});

test('buildResendPayload : mêmes champs que l’envoi d’origine, nouveau numéro, même uuid (rejeu sans doublon)', () => {
    const opData = {
        first_name: 'Awa', last_name: 'Ngo', birth_date: '1992-05-01', gender: 'F', national_id: 'CNI1',
        contact_phone: '650000000', assurance: null, residence: 'Yaounde', father_name: '', mother_name: undefined,
    };
    assert.deepEqual(buildResendPayload(opData, '  CNI2 ', 'uuid-1'), {
        first_name: 'Awa', last_name: 'Ngo', birth_date: '1992-05-01', gender: 'F', national_id: 'CNI2',
        contact_phone: '650000000', assurance: null, residence: 'Yaounde', father_name: null, mother_name: null,
        uuid: 'uuid-1',
    });
});

// --- Contrat de l'écran et des fonctions locales ---
test('syncQuarantine : suppression complète du patient refusé dans une seule transaction', () => {
    assert.match(quarantine, /export async function discardQuarantinedPatient\(patientUuid\)/);
    assert.match(quarantine, /discardPlan\(/);
    const fn = quarantine.slice(quarantine.indexOf('export async function discardQuarantinedPatient'));
    assert.match(fn, /db\.writeTransaction/);
    assert.match(fn, /DELETE FROM patients WHERE id = \?/);
    assert.match(fn, /DELETE FROM sync_quarantine WHERE patient_uuid = \? OR \(kind = 'patient' AND local_id = \?\)/);
});

test('SyncFailuresView : bouton de suppression avec confirmation chiffrée', () => {
    assert.match(view, /discardQuarantinedPatient\(g\.patientUuid\)/);
    assert.match(view, /window\.confirm\(t\('syncFailures\.discard_confirm'/);
    assert.match(view, /records: g\.recordCount/);
    assert.match(view, /prescriptions: g\.prescriptionCount/);
    assert.match(view, /@click="handleDiscard\(g\)"/);
});

test('SyncFailuresView : correction du numéro d’identité puis renvoi, le patient existant reçoit ses données retenues', () => {
    assert.match(view, /api\.post\('\/patients\/', buildResendPayload\(/);
    assert.match(view, /reattachToExistingPatient\(g\.patientUuid, /);
    assert.match(view, /validateNationalIdCorrection\(g\.nationalId, /);
    assert.match(view, /v-model="fixIds\[g\.patientUuid\]"/);
    assert.match(view, /@click="handleFix\(g\)"/);
    assert.match(view, /describeServerError\(/);
    // le rattachement par code existant est toujours là
    assert.match(view, /@click="handleReattach\(g\)"/);
});

test('clés syncFailures.* en FR et EN, sans caractère typographique interdit', () => {
    const keys = ['discard_button', 'discard_confirm', 'discard_error', 'discard_done', 'fix_label', 'fix_button', 'fix_done',
        'fix_err_empty', 'fix_err_same', 'fix_failed', 'fix_offline', 'attach_title', 'fix_title'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].syncFailures?.[k];
            assert.equal(typeof v, 'string', `${locale}.syncFailures.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.syncFailures.${k}`);
        }
    }
    assert.match(msgs.fr.syncFailures.discard_confirm, /\{name\}.*\{records\}.*\{prescriptions\}/s);
});

test('le texte du gabarit reste conforme (jetons, texte >= 13 px, caractères)', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view.slice(0, view.indexOf('<script')), /[—–…·]/);
});
