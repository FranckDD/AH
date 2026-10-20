import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { computeStaffDiscount, normalizeItemCategory } from '../src/utils/staffDiscount.js';

const here = dirname(fileURLToPath(import.meta.url));
const CASES = JSON.parse(
    readFileSync(resolve(here, '../../tests/fixtures/staff_discount_cases.json'), 'utf-8')
);

for (const c of CASES) {
    test(`fixture: ${c.name}`, () => {
        const res = computeStaffDiscount(c.lines, c.is_staff, c.rules);
        assert.equal(res.amount, Number(c.expected_amount));
        const cats = [...new Set((res.details || []).map((d) => d.category))].sort();
        assert.deepEqual(cats, [...c.expected_categories].sort());
    });
}

test('normalizeItemCategory variants', () => {
    const labels = ['Sale Medication', 'Médicament', 'Vente Carnet', 'Examen',
        'Consultation Spirituel', 'Consultation Médical', 'Désintox'];
    const expected = ['medicament', 'medicament', 'carnet', 'examen',
        'consultation', 'consultation', 'autre_soin'];
    assert.deepEqual(labels.map(normalizeItemCategory), expected);
    assert.equal(normalizeItemCategory('Service'), 'autre_soin');
    assert.equal(normalizeItemCategory('Truc'), 'autre_soin');
    assert.equal(normalizeItemCategory(''), 'autre_soin');
    assert.equal(normalizeItemCategory(null), 'autre_soin');
    assert.equal(normalizeItemCategory(undefined), 'autre_soin');
    assert.equal(normalizeItemCategory('EXAMENS'), 'examen');
});

test('details null when no discount', () => {
    assert.deepEqual(computeStaffDiscount([{ item_type: 'Examen', line_total: 10 }], true, []),
        { amount: 0, details: null });
    const r = computeStaffDiscount([], true,
        [{ category: 'examen', min_invoice_amount: 0, rate_percent: 10, is_active: true }]);
    assert.equal(r.amount, 0);
    assert.equal(r.details, null);
});

// Arrondi UNE seule fois sur la somme: medicament 0.01 a 50% = 0.005,
// examen 0.01 a 50% = 0.005 -> somme brute 0.010 -> 0.01.
// Arrondi par regle aurait donne 0.01 + 0.01 = 0.02.
test('rounding happens once on the sum (two x.xx5 rules)', () => {
    const lines = [
        { item_type: 'Médicament', line_total: 0.01 },
        { item_type: 'Examen', line_total: 0.01 },
    ];
    const rules = [
        { category: 'medicament', min_invoice_amount: 0, rate_percent: 50, is_active: true },
        { category: 'examen', min_invoice_amount: 0, rate_percent: 50, is_active: true },
    ];
    const r = computeStaffDiscount(lines, true, rules);
    assert.equal(r.amount, 0.01);
    assert.deepEqual(r.details.map((d) => d.category).sort(), ['examen', 'medicament']);
});

test('float-noise line total (0.1*3) matches Python', () => {
    const r = computeStaffDiscount([{ item_type: 'Examen', line_total: 0.1 * 3 }], true,
        [{ category: 'examen', min_invoice_amount: 0.3, rate_percent: 100, is_active: true }]);
    assert.equal(r.amount, 0.3);
});

// Variante plus grosse: 1000.01 + 1000.01 a 50% = 500.005 + 500.005 = 1000.01
test('rounding once on sum, larger totals', () => {
    const lines = [
        { item_type: 'Médicament', line_total: 1000.01 },
        { item_type: 'Examen', line_total: 1000.01 },
    ];
    const rules = [
        { category: 'medicament', min_invoice_amount: 2000, rate_percent: 50, is_active: true },
        { category: 'examen', min_invoice_amount: 2000, rate_percent: 50, is_active: true },
    ];
    assert.equal(computeStaffDiscount(lines, true, rules).amount, 1000.01);
});
