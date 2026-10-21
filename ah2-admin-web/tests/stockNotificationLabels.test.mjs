import { test } from 'node:test';
import assert from 'node:assert/strict';
import { stockDecidedLabel, adjustmentKindLabel } from '../src/utils/stockNotificationLabels.js';

const COMBOS = [
    ['receipt', 'valide'], ['receipt', 'rejete'],
    ['incident', 'valide'], ['incident', 'rejete'],
    ['adjustment', 'approuve'], ['adjustment', 'refuse'],
];

for (const [kind, status] of COMBOS) {
    test(`stock_decided ${kind}/${status} -> dedicated key`, () => {
        const r = stockDecidedLabel({ kind, status, number: 'X-1' });
        assert.equal(r.key, `notifications.stock_decided_${kind}_${status}`);
        assert.deepEqual(r.params, { number: 'X-1' });
    });
}

test('unknown status falls back to generic key with raw status, no key path', () => {
    const r = stockDecidedLabel({ kind: 'adjustment', status: 'weird', number: 'AJU-3' });
    assert.equal(r.key, 'notifications.stock_decided_other');
    assert.deepEqual(r.params, { number: 'AJU-3', status: 'weird' });
});

test('missing payload fields do not throw', () => {
    assert.equal(stockDecidedLabel(undefined).key, 'notifications.stock_decided_other');
    assert.deepEqual(stockDecidedLabel({}).params, { number: '?', status: '?' });
});

test('adjustment kind labels with raw fallback', () => {
    assert.equal(adjustmentKindLabel('reapprovisionnement').key, 'notifications.adjustment_kind_reapprovisionnement');
    assert.equal(adjustmentKindLabel('correction').key, 'notifications.adjustment_kind_correction');
    assert.deepEqual(adjustmentKindLabel('zzz'), { key: null, raw: 'zzz' });
    assert.deepEqual(adjustmentKindLabel(undefined), { key: null, raw: '?' });
});
