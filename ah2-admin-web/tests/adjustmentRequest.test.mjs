import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateAdjustmentRequest } from '../src/utils/adjustmentRequest.js';

const req = (o = {}) => ({ product_id: 1, kind: 'reapprovisionnement', quantity: 5, reason: 'rupture', ...o });

test('reapprovisionnement a 0 refuse', () => {
    const r = validateAdjustmentRequest(req({ quantity: 0 }));
    assert.equal(r.ok, false);
    assert.equal(r.error, 'quantity_positive');
});
test('correction a 0 acceptee', () => {
    assert.equal(validateAdjustmentRequest(req({ kind: 'correction', quantity: 0 })).ok, true);
});
test('quantite negative refusee', () => {
    assert.equal(validateAdjustmentRequest(req({ kind: 'correction', quantity: -1 })).error, 'quantity_invalid');
});
test('quantite non entiere refusee', () => {
    assert.equal(validateAdjustmentRequest(req({ quantity: 2.5 })).error, 'quantity_invalid');
    assert.equal(validateAdjustmentRequest(req({ quantity: null })).error, 'quantity_invalid');
});
test('motif vide refuse', () => {
    assert.equal(validateAdjustmentRequest(req({ reason: '   ' })).error, 'reason_required');
});
test('type inconnu refuse', () => {
    assert.equal(validateAdjustmentRequest(req({ kind: 'x' })).error, 'kind_invalid');
});
test('demande valide', () => {
    assert.deepEqual(validateAdjustmentRequest(req()), { ok: true });
});
