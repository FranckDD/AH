import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { keepsResolvedPatient } from '../src/utils/newPatientFlow.js';

// Defaut nurse-1 (2026-10-26) : patient enregistre hors ligne -> formulaire de mesures a code vide.
// Le panneau met le focus sur le champ code (lecture seule) ; au premier clic ailleurs, @blur appelait
// lookupPatient() avec un code vide, ce qui effacait le patientUuid (« patient introuvable » a l'enregistrement).
test('keepsResolvedPatient : identite fixee + code inchange (meme vide) = on ne relance pas la recherche', () => {
    assert.equal(keepsResolvedPatient({ locked: true, code: '', lockedCode: '' }), true);
    assert.equal(keepsResolvedPatient({ locked: true, code: 'AH2-1', lockedCode: 'AH2-1' }), true);
});

test('keepsResolvedPatient : code modifie ou identite non fixee = recherche normale', () => {
    assert.equal(keepsResolvedPatient({ locked: true, code: 'AH2-2', lockedCode: 'AH2-1' }), false);
    assert.equal(keepsResolvedPatient({ locked: false, code: '', lockedCode: '' }), false);
});

const composable = readFileSync(new URL('../src/composables/usePatientLookup.js', import.meta.url), 'utf8');
const modal = readFileSync(new URL('../src/components/medical-records/MedicalRecordModal.vue', import.meta.url), 'utf8');

test('usePatientLookup : lookupPatient garde l identite fixee par setFromExisting', () => {
    assert.match(composable, /keepsResolvedPatient/);
    assert.match(composable, /locked = true/);
    assert.match(composable, /locked = false/);
});

test('MedicalRecordModal : message honnete sans code', () => {
    assert.match(modal, /medicalRecords\.modal\.code_pending/);
});

test('cle code_pending en FR et EN, ASCII', async () => {
    globalThis.localStorage = { getItem: () => null, setItem: () => {} };
    const { default: i18n } = await import('../src/i18n.js');
    for (const l of ['fr', 'en']) {
        const v = i18n.global.messages.value[l].medicalRecords.modal.code_pending;
        assert.equal(typeof v, 'string');
        assert.doesNotMatch(v, /[–—…·]/);
    }
});
