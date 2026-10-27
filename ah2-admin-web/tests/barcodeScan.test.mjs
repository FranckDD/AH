import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeScan, applyScanToLines } from '../src/utils/barcodeScan.js';

test('normalizeScan : chiffres propres, espaces internes et texte refuses', () => {
    assert.equal(normalizeScan('10000001\n'), '10000001');
    assert.equal(normalizeScan('  10000001\r\n'), '10000001');
    assert.equal(normalizeScan(' 1000 0001 '), null);
    assert.equal(normalizeScan('abc'), null);
    assert.equal(normalizeScan(''), null);
    assert.equal(normalizeScan(null), null);
    assert.equal(normalizeScan('1234567890123'), null);
    assert.equal(normalizeScan('123456789012'), '123456789012');
});

const A = { medication_id: 1, drug_name: 'Para', price: 500, quantity: 0 };
const B = { medication_id: 2, drug_name: 'Ibu', price: 800, quantity: 7 };

test('applyScanToLines : creation puis incrementation', () => {
    const lines = [];
    const first = applyScanToLines(lines, A);
    assert.equal(first.created, true);
    assert.equal(lines.length, 1);
    assert.equal(first.line.quantity, 1);
    assert.equal(first.line.refId, 1);
    assert.equal(first.line.unitPrice, 500);
    assert.equal(first.line.knownStock, 0);
    assert.equal(first.line.catalogLine, true);
    assert.equal(first.line.itemType, 'Médicament');
    const second = applyScanToLines(lines, A);
    assert.equal(second.created, false);
    assert.equal(second.line, first.line);
    assert.equal(lines.length, 1);
    assert.equal(first.line.quantity, 2);
});

test('applyScanToLines : quantite tapee a 5 puis scan = 6, autre produit = nouvelle ligne', () => {
    const lines = [];
    const { line } = applyScanToLines(lines, A);
    line.quantity = 5;
    applyScanToLines(lines, A);
    assert.equal(line.quantity, 6);
    const other = applyScanToLines(lines, B);
    assert.equal(other.created, true);
    assert.equal(lines.length, 2);
    assert.notEqual(other.line.key, line.key);
});

import { shouldRedirectToScan } from '../src/utils/barcodeScan.js';
test('shouldRedirectToScan : chiffre hors champ seulement', () => {
    assert.equal(shouldRedirectToScan({ key: '5', target: { tagName: 'BODY' } }), true);
    assert.equal(shouldRedirectToScan({ key: '5', target: { tagName: 'DIV' } }), true);
    assert.equal(shouldRedirectToScan({ key: '5', target: { tagName: 'INPUT' } }), false);
    assert.equal(shouldRedirectToScan({ key: '5', target: { tagName: 'TEXTAREA' } }), false);
    assert.equal(shouldRedirectToScan({ key: '5', target: { tagName: 'SELECT' } }), false);
    assert.equal(shouldRedirectToScan({ key: '5', target: { tagName: 'BUTTON' } }), false);
    assert.equal(shouldRedirectToScan({ key: 'a', target: { tagName: 'BODY' } }), false);
    assert.equal(shouldRedirectToScan({ key: 'Enter', target: { tagName: 'BODY' } }), false);
    assert.equal(shouldRedirectToScan({ key: '5', ctrlKey: true, target: { tagName: 'BODY' } }), false);
    assert.equal(shouldRedirectToScan({ key: '5', metaKey: true, target: { tagName: 'BODY' } }), false);
    assert.equal(shouldRedirectToScan({ key: '5', altKey: true, target: { tagName: 'BODY' } }), false);
    assert.equal(shouldRedirectToScan({ key: '5', target: { tagName: 'P', isContentEditable: true } }), false);
});
