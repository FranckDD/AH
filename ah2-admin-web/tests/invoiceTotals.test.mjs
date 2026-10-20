import { test } from 'node:test';
import assert from 'node:assert/strict';
import { round2, computeInvoiceTotals } from '../src/utils/invoiceTotals.js';

const RULES = [
    { category: 'medicament', min_invoice_amount: 5000, rate_percent: 50, is_active: true },
    { category: 'examen', min_invoice_amount: 0, rate_percent: 10, is_active: false },
];
const LINES = [
    { item_type: 'Sale Medication', line_total: 3000 },
    { item_type: 'Examen', line_total: 4000 },
];

test('round2', () => {
    assert.equal(round2(1.005), 1.01);
    assert.equal(round2(0.1 + 0.2), 0.3);
    assert.equal(round2(5500), 5500);
});

test('staff patient: discount applied, net amount, advance on net', () => {
    const r = computeInvoiceTotals({ grossRaw: 7000, lines: LINES, isStaff: true, rules: RULES, advance: 5500 });
    assert.equal(r.gross, 7000);
    assert.equal(r.staffDiscountAmount, 1500);
    assert.equal(r.net, 5500);
    assert.equal(r.advanceOk, true);
    assert.equal(r.rulesMissing, false);
    const over = computeInvoiceTotals({ grossRaw: 7000, lines: LINES, isStaff: true, rules: RULES, advance: 6000 });
    assert.equal(over.advanceOk, false);
});

test('non-staff / walk-in: no discount', () => {
    const r = computeInvoiceTotals({ grossRaw: 7000, lines: LINES, isStaff: false, rules: RULES, advance: 7000 });
    assert.equal(r.staffDiscountAmount, 0);
    assert.equal(r.net, 7000);
    assert.equal(r.advanceOk, true);
});

test('staff patient without rules: rulesMissing, no discount', () => {
    const r = computeInvoiceTotals({ grossRaw: 7000, lines: LINES, isStaff: true, rules: null, advance: 0 });
    assert.equal(r.rulesMissing, true);
    assert.equal(r.staffDiscountAmount, 0);
    const ok = computeInvoiceTotals({ grossRaw: 7000, lines: LINES, isStaff: false, rules: null, advance: 0 });
    assert.equal(ok.rulesMissing, false);
});

test('gross rounded from raw sum, negative advance invalid', () => {
    const r = computeInvoiceTotals({ grossRaw: 0.1 + 0.2, lines: [], isStaff: false, rules: [], advance: -1 });
    assert.equal(r.gross, 0.3);
    assert.equal(r.advanceOk, false);
});
