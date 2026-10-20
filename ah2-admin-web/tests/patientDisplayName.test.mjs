import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolvePatientName } from '../src/utils/patientDisplayName.js';

test('registered patient: first + last name from lookup', () => {
    assert.equal(resolvePatientName({ patient_id: 5, patient_label: null }, { first_name: 'Awa', last_name: 'Diallo' }), 'Awa Diallo');
});
test('registered patient name wins over label', () => {
    assert.equal(resolvePatientName({ patient_id: 5, patient_label: 'Ancien' }, { first_name: 'Awa', last_name: 'Diallo' }), 'Awa Diallo');
});
test('skips empty parts', () => {
    assert.equal(resolvePatientName({ patient_id: 5 }, { first_name: '', last_name: ' Diallo ' }), 'Diallo');
});
test('walk-in: label', () => {
    assert.equal(resolvePatientName({ patient_id: null, patient_label: 'Passant' }, undefined), 'Passant');
});
test('registered but not in lookup: falls back to label then null', () => {
    assert.equal(resolvePatientName({ patient_id: 9, patient_label: 'X' }, undefined), 'X');
    assert.equal(resolvePatientName({ patient_id: 9, patient_label: null }, undefined), null);
});
