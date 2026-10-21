import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildCountPayload, describeConflicts, isValidCount } from '../src/utils/labCount.js';

const products = [
    { id: 1, name: 'A', quantity: 5 },
    { id: 2, name: 'B', quantity: '7' },
    { id: 3, name: 'C', quantity: 0 },
];

test('only filled entries, previous_qty = loaded value', () => {
    const lines = buildCountPayload(products, { 1: '4', 2: '', 3: 0 });
    assert.deepEqual(lines, [
        { product_id: 1, previous_qty: 5, counted_qty: 4 },
        { product_id: 3, previous_qty: 0, counted_qty: 0 },
    ]);
});

test('empty and whitespace entries ignored', () => {
    assert.deepEqual(buildCountPayload(products, { 1: '  ', 2: null }), []);
    assert.deepEqual(buildCountPayload(products, {}), []);
});

test('isValidCount', () => {
    assert.equal(isValidCount('3'), true);
    assert.equal(isValidCount(0), true);
    assert.equal(isValidCount('-1'), false);
    assert.equal(isValidCount('1.5'), false);
    assert.equal(isValidCount('x'), false);
});

test('describeConflicts from 200 response', () => {
    const out = describeConflicts({ count_id: 9, applied: [], conflicts: [{ product_id: 2, name: 'B', expected: '7', actual: '9' }] });
    assert.deepEqual(out, [{ product_id: 2, name: 'B', expected: 7, actual: 9 }]);
});

test('describeConflicts from 409 error', () => {
    const err = { response: { status: 409, data: { detail: { message: 'm', conflicts: [{ product_id: 1, name: 'A', expected: 5, actual: 3 }] } } } };
    assert.equal(describeConflicts(err)[0].actual, 3);
    assert.deepEqual(describeConflicts(null), []);
    assert.deepEqual(describeConflicts({ conflicts: [] }), []);
});
