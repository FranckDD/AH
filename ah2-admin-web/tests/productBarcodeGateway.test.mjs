import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeBarcode, mapStockRowToProduct, lookupProductByBarcode } from '../src/utils/productBarcodeLookup.js';

const row = { server_id: 7, drug_name: 'Para', quantity: 4, price: '150.00', forme: 'Comprime', dosage_mg: '500.00', barcode: '10000007', has_photo: 1, photo_version: 2 };
const mk = (over = {}) => {
    const calls = { get: 0, getAll: 0 };
    return {
        calls,
        get: async () => { calls.get++; return { data: { medication_id: 7 } }; },
        getAll: async () => { calls.getAll++; return [row]; },
        canFallback: () => true,
        ...over,
    };
};
const netErr = () => { throw new Error('Network Error'); };

test('normalizeBarcode trims and rejects empty / non digits', () => {
    assert.equal(normalizeBarcode(' 10000007 '), '10000007');
    assert.equal(normalizeBarcode(''), null);
    assert.equal(normalizeBarcode('12ab'), null);
    assert.equal(normalizeBarcode(null), null);
});

test('empty or non-digit input: no request at all', async () => {
    const d = mk();
    assert.deepEqual(await lookupProductByBarcode('  ', d), { data: null });
    assert.deepEqual(await lookupProductByBarcode('abc', d), { data: null });
    assert.equal(d.calls.get + d.calls.getAll, 0);
});

test('online success returns server product', async () => {
    assert.deepEqual(await lookupProductByBarcode('10000007', mk()), { data: { medication_id: 7 } });
});

test('404 becomes { data: null }, no local fallback', async () => {
    const d = mk({ get: async () => { throw { response: { status: 404 } }; } });
    assert.deepEqual(await lookupProductByBarcode('10000007', d), { data: null });
    assert.equal(d.calls.getAll, 0);
});

test('offline secretaire reads local table with server-shaped keys', async () => {
    const d = mk({ get: async () => netErr() });
    const { data } = await lookupProductByBarcode('10000007', d);
    assert.deepEqual(data, {
        medication_id: 7, drug_name: 'Para', quantity: 4, price: 150, forme: 'Comprime',
        dosage_mg: 500, barcode: '10000007', has_photo: true, photo_version: 2,
    });
});

test('offline secretaire, unknown code: data null', async () => {
    const d = mk({ get: async () => netErr(), getAll: async () => [] });
    assert.deepEqual(await lookupProductByBarcode('10000007', d), { data: null });
});

test('offline other role: network error propagated', async () => {
    const err = new Error('Network Error');
    const d = mk({ get: async () => { throw err; }, canFallback: () => false });
    await assert.rejects(lookupProductByBarcode('10000007', d), (e) => e === err);
    assert.equal(d.calls.getAll, 0);
});

test('online non-404 error (500) propagates even for secretaire', async () => {
    const err = { response: { status: 500 } };
    const d = mk({ get: async () => { throw err; } });
    await assert.rejects(lookupProductByBarcode('10000007', d), (e) => e === err);
});

test('mapStockRowToProduct: null dosage, no photo', () => {
    const r = mapStockRowToProduct({ ...row, dosage_mg: null, has_photo: 0, photo_version: null });
    assert.equal(r.dosage_mg, null);
    assert.equal(r.has_photo, false);
    assert.equal(r.photo_version, 0);
});

import { photoRequestUrl } from '../src/utils/photoRequestUrl.js';
test('photoRequestUrl : la version est dans l URL et la change quand elle change', () => {
    assert.equal(photoRequestUrl(7, 3), '/pharmacy/7/photo?v=3');
    assert.notEqual(photoRequestUrl(7, 3), photoRequestUrl(7, 4));
    assert.equal(photoRequestUrl(7, undefined), '/pharmacy/7/photo?v=0');
});
