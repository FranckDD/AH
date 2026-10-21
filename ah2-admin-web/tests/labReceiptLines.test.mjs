import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lineTotal, receiptTotal, validateReceipt, buildReceiptPayload, formatMoney } from '../src/utils/labReceiptLines.js';

const TODAY = new Date(2026, 9, 21);
const line = (o = {}) => ({
    product_id: 1, product_name: 'Tube', packaging: 'boite', ordered_qty: '', received_qty: '10',
    lot_number: 'L1', expiry_date: '2027-01-01', unit_price: '1500', checked: true, ...o,
});
const form = (o = {}) => ({ invoice_number: 'F-1', supplier: 'Sup', delivery_date: '2026-10-21', lines: [line()], ...o });

test('lineTotal is exact to the cent and accepts strings', () => {
    assert.equal(lineTotal('3', '12.35'), 37.05);
    assert.equal(lineTotal(2, 1250.5), 2501);
    assert.equal(lineTotal(3, 0.1), 0.3);
    assert.equal(lineTotal('', '100'), 0);
    assert.equal(lineTotal('abc', '100'), 0);
});

test('receiptTotal sums line totals', () => {
    assert.equal(receiptTotal([line(), line({ product_id: 2, received_qty: 1, unit_price: '250' })]), 15250);
    assert.equal(receiptTotal([]), 0);
});

test('valid form has no errors', () => {
    assert.deepEqual(validateReceipt(form(), TODAY), []);
});

test('one error per rule', () => {
    const has = (f, k) => assert.ok(validateReceipt(f, TODAY).includes(k), k);
    has(form({ invoice_number: '  ' }), 'labStock.receipt_err_invoice');
    has(form({ supplier: '' }), 'labStock.receipt_err_supplier');
    has(form({ delivery_date: '' }), 'labStock.receipt_err_date');
    has(form({ delivery_date: '2026-10-25' }), 'labStock.receipt_err_date_future');
    has(form({ lines: [] }), 'labStock.receipt_err_no_lines');
    has(form({ lines: [line(), line()] }), 'labStock.receipt_err_duplicate');
    has(form({ lines: [line({ received_qty: '0' })] }), 'labStock.receipt_err_qty');
    has(form({ lines: [line({ received_qty: '1.5' })] }), 'labStock.receipt_err_qty');
    has(form({ lines: [line({ ordered_qty: '-1' })] }), 'labStock.receipt_err_ordered');
    has(form({ lines: [line({ lot_number: ' ' })] }), 'labStock.receipt_err_lot');
    has(form({ lines: [line({ expiry_date: '' })] }), 'labStock.receipt_err_expiry');
    has(form({ lines: [line({ unit_price: '' })] }), 'labStock.receipt_err_price');
    has(form({ lines: [line({ unit_price: '1.234' })] }), 'labStock.receipt_err_price');
    has(form({ lines: Array.from({ length: 201 }, (_, i) => line({ product_id: i + 1 })) }), 'labStock.receipt_err_too_many');
});

test('tolerates delivery date of tomorrow (timezone)', () => {
    assert.deepEqual(validateReceipt(form({ delivery_date: '2026-10-22' }), TODAY), []);
});

test('errors are not repeated', () => {
    const errs = validateReceipt(form({ lines: [line({ lot_number: '' }), line({ product_id: 2, lot_number: '' })] }), TODAY);
    assert.equal(errs.filter((e) => e === 'labStock.receipt_err_lot').length, 1);
});

test('payload has no total and typed values', () => {
    const p = buildReceiptPayload(form({ invoice_number: ' F-1 ', lines: [line({ ordered_qty: '12' }), line({ product_id: 2 })] }));
    assert.equal(p.invoice_number, 'F-1');
    assert.equal('total_amount' in p, false);
    for (const l of p.lines) {
        assert.equal('line_total' in l, false);
        assert.equal('checked' in l, false);
        assert.equal('product_name' in l, false);
    }
    assert.deepEqual(p.lines[0], {
        product_id: 1, ordered_qty: 12, received_qty: 10, unit_price: 1500, lot_number: 'L1', expiry_date: '2027-01-01',
    });
    assert.equal(p.lines[1].ordered_qty, null);
});

test('receipt total = sum of cent line totals, no drift over 200 lines', () => {
    const lines = Array.from({ length: 200 }, (_, i) => line({ product_id: i + 1, received_qty: 3, unit_price: '0.10' }));
    assert.equal(receiptTotal(lines), 60);
    assert.equal(receiptTotal([line({ received_qty: 3, unit_price: '12.35' }), line({ product_id: 2, received_qty: 7, unit_price: '0.33' })]), 39.36);
});

test('price with more than 2 decimals rejected', () => {
    assert.ok(validateReceipt(form({ lines: [line({ received_qty: 7, unit_price: '0.333' })] }), TODAY).includes('labStock.receipt_err_price'));
});

test('delivery date: today+1 accepted, today+2 rejected (ISO strings)', () => {
    const d = new Date(2026, 11, 31);
    assert.deepEqual(validateReceipt(form({ delivery_date: '2027-01-01' }), d), []);
    assert.ok(validateReceipt(form({ delivery_date: '2027-01-02' }), d).includes('labStock.receipt_err_date_future'));
    assert.deepEqual(validateReceipt(form({ delivery_date: '2026-12-31' }), d), []);
});

test('formatMoney keeps real decimals', () => {
    assert.match(formatMoney(37.05), /37[.,]05 FCFA/);
    assert.doesNotMatch(formatMoney(2501), /[.,]00/);
    assert.match(formatMoney('1500.5'), /[.,]5 FCFA/);
});
