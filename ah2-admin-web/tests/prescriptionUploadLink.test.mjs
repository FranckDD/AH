import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolveMedicalRecordLink } from '../src/utils/medicalRecordLink.js';
import { describeServerError } from '../src/utils/serverError.js';

// --- Lien prescription -> consultation à l'envoi (cause de la 422 sur « Prescrire ») ---
// medical_record_id local = uuid (consultation créée dans le même geste) OU identifiant serveur entier
// (consultation déjà synchronisée, ouverte depuis la fiche). Le serveur attend un entier dans medical_record_id
// et une chaîne dans medical_record_uuid : un entier envoyé comme uuid donnait « Input should be a valid string ».
test('consultation déjà synchronisée (entier) : envoyée comme identifiant serveur, jamais comme uuid', () => {
    assert.deepEqual(resolveMedicalRecordLink(123, null), { serverId: 123, uuid: null });
    assert.deepEqual(resolveMedicalRecordLink('123', null), { serverId: 123, uuid: null });
});

test('consultation créée dans le même geste (uuid) : envoyée comme uuid', () => {
    const u = '6f1c0e7e-0d1f-4d34-9a1c-111111111111';
    assert.deepEqual(resolveMedicalRecordLink(u, null), { serverId: null, uuid: u });
});

test('l’identifiant serveur connu localement l’emporte sur l’uuid', () => {
    const u = '6f1c0e7e-0d1f-4d34-9a1c-111111111111';
    assert.deepEqual(resolveMedicalRecordLink(u, 456), { serverId: 456, uuid: null });
});

test('pas de consultation liée : rien n’est envoyé', () => {
    for (const v of [null, undefined, '', 0]) {
        assert.deepEqual(resolveMedicalRecordLink(v, null), { serverId: null, uuid: null }, String(v));
    }
});

test('le résultat respecte les types attendus par le serveur', () => {
    for (const input of [123, '123', '6f1c0e7e-0d1f-4d34-9a1c-111111111111']) {
        const { serverId, uuid } = resolveMedicalRecordLink(input, null);
        assert.ok(serverId === null || Number.isInteger(serverId));
        assert.ok(uuid === null || typeof uuid === 'string');
    }
});

// --- Message d'erreur du serveur : une 422 doit dire quel champ est refusé ---
test('describeServerError : chaîne, liste de validation, vide', () => {
    assert.equal(describeServerError({ response: { data: { detail: 'Conflit en base de données' } } }), 'Conflit en base de données');
    assert.equal(
        describeServerError({ response: { data: { detail: [{ loc: ['body', 'medical_record_uuid'], msg: 'Input should be a valid string' }] } } }),
        'medical_record_uuid : Input should be a valid string',
    );
    assert.equal(
        describeServerError({ response: { data: { detail: [
            { loc: ['body', 'dosage'], msg: 'Field required' },
            { loc: ['body', 'duration'], msg: 'String should have at least 1 character' },
        ] } } }),
        'dosage : Field required ; duration : String should have at least 1 character',
    );
    assert.equal(describeServerError({ response: { data: { detail: [{ msg: 'Value error, liste requise', loc: [] }] } } }), 'Value error, liste requise');
    assert.equal(describeServerError({ response: { status: 500, data: {} } }, 'Echec'), 'Echec');
    assert.equal(describeServerError(null, 'Echec'), 'Echec');
    assert.equal(describeServerError({}, 'Echec'), 'Echec');
});

// --- Le connecteur utilise ces deux fonctions ---
const connector = readFileSync(new URL('../src/powersync-client/DossierConnector.js', import.meta.url), 'utf8');

test('DossierConnector : le lien de consultation passe par resolveMedicalRecordLink', () => {
    assert.match(connector, /resolveMedicalRecordLink\(/);
    assert.doesNotMatch(connector, /medicalRecordUuid = op\.opData\.medical_record_id;/);
});

test('DossierConnector : le refus du serveur est détaillé dans la console et dans le message affiché', () => {
    assert.match(connector, /describeServerError\(/);
    assert.match(connector, /error\?\.response\?\.data/);
});

test('DossierConnector : la modification d’une prescription n’envoie jamais un uuid comme identifiant de consultation', () => {
    assert.match(connector, /patchMedicalRecordId/);
    assert.doesNotMatch(connector, /medicalRecordId: currentPresc\.medical_record_id/);
});
