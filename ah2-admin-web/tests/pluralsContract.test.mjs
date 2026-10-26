// Pluriels : 1 s'ecrit au singulier en francais ET en anglais (jamais "1 requests", "1 bottles", "1 batches").
import { test } from 'node:test';
import assert from 'node:assert/strict';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const { anomalyLabel } = await import('../src/utils/reports.js');
const g = i18n.global;
const t = (loc) => (k, p, n) => g.t(k, p || {}, n === undefined ? { locale: loc } : { locale: loc, plural: n });

test('demandes : "1 request" / "2 requests" et "1 demande" / "2 demandes"', () => {
    for (const key of ['labStockScreens.requests_count', 'stockAdminScreens.requests_count']) {
        assert.equal(t('en')(key, undefined, 1), '1 request');
        assert.equal(t('en')(key, undefined, 2), '2 requests');
        assert.equal(t('fr')(key, undefined, 1), '1 demande');
        assert.equal(t('fr')(key, undefined, 2), '2 demandes');
    }
});

test('bouteilles de la Fabrication au singulier pour 1', () => {
    assert.match(t('en')('fabrication.outputs.cancel_help', { reason: 'Sample', quantity: 1 }, 1), /output of 1 bottle\./);
    assert.match(t('en')('fabrication.outputs.cancel_help', { reason: 'Sample', quantity: 3 }, 3), /output of 3 bottles\./);
    assert.match(t('fr')('fabrication.outputs.cancel_help', { reason: 'Echantillon', quantity: 1 }, 1), /de 1 bouteille\. La bouteille/);
    assert.match(t('en')('fabrication.ship_help', { good: 1 }, 1), /^1 bottle will/);
    assert.match(t('en')('fabrication.ship_help', { good: 4 }, 4), /^4 bottles will/);
});

test('cout par lot : "1 batch" / "2 batches"', () => {
    const p = { name: 'X', last: '1', avg: '1' };
    assert.match(t('en')('reports.labels.cost_line', p, 1), /\(1 batch\)$/);
    assert.match(t('en')('reports.labels.cost_line', p, 2), /\(2 batches\)$/);
});

test('anomalie sortie autre : 1 bouteille / 3 bouteilles', () => {
    const item = { kind: 'sortie_autre', detail: { quantity: 1, batch_number: 'L1' }, ref: 5 };
    assert.match(anomalyLabel(item, t('en'), (k) => g.te(k, 'en')), /1 bottle on batch L1/);
    item.detail.quantity = 3;
    assert.match(anomalyLabel(item, t('en'), (k) => g.te(k, 'en')), /3 bottles on batch L1/);
});

test('les appels passent le nombre en troisieme argument', async () => {
    const { readFileSync } = await import('node:fs');
    const r = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
    assert.match(r('views/modules/stock/AdjustmentRequestsAdmin.vue'), /requests_count', requests\.length\)/);
    assert.match(r('views/modules/labstock/LabStockRequests.vue'), /requests_count', visible\.length\)/);
    assert.match(r('views/modules/fabrication/FabLotDetail.vue'), /ship_help', \{ good: batch\.qty_shipped \}, Number/);
});
