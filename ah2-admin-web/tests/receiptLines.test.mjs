import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateReceiptLine, prefillFromLot } from '../src/utils/receiptLines.js';

const line = (o = {}) => ({ qty_expected: 10, qty_good: 0, qty_damaged: 0, qty_lost: 0, qty_defective: 0, ...o });

test('somme nulle refusee', () => {
    const r = validateReceiptLine(line());
    assert.equal(r.ok, false);
    assert.equal(r.error, 'sum_zero');
});

test('somme superieure a l\'attendu refusee', () => {
    const r = validateReceiptLine(line({ qty_good: 8, qty_damaged: 3 }));
    assert.equal(r.ok, false);
    assert.equal(r.error, 'sum_exceeds');
});

test('somme egale a l\'attendu acceptee', () => {
    assert.equal(validateReceiptLine(line({ qty_good: 7, qty_lost: 3 })).ok, true);
});

test('somme inferieure a l\'attendu acceptee', () => {
    assert.equal(validateReceiptLine(line({ qty_good: 4 })).ok, true);
});

test('sans attendu, pas de plafond', () => {
    assert.equal(validateReceiptLine(line({ qty_expected: null, qty_good: 500 })).ok, true);
});

test('valeur negative refusee', () => {
    const r = validateReceiptLine(line({ qty_good: 5, qty_lost: -1 }));
    assert.equal(r.ok, false);
    assert.equal(r.error, 'invalid_qty');
});

test('valeur non entiere refusee', () => {
    assert.equal(validateReceiptLine(line({ qty_good: 1.5 })).ok, false);
    assert.equal(validateReceiptLine(line({ qty_good: 'abc' })).ok, false);
});

test('prefillFromLot reprend produit, attendu et peremption', () => {
    const l = prefillFromLot({ id: 3, product_id: 12, product_name: 'Tisane', quantity_produced: 40, expiry_date: '2027-05-01' });
    assert.equal(l.product_id, 12);
    assert.equal(l.qty_expected, 40);
    assert.equal(l.expiry_date, '2027-05-01');
    assert.equal(l.qty_good, 0);
});
