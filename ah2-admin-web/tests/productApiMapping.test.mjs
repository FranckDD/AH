import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mapProductToApi, parseDosageMg } from '../src/utils/productApi.js';

const base = { name: 'X', category: 'PHARMA', quantity: '5', minThreshold: '2', price: '100', expiryDate: '', forme: 'Comprimé', dosage: '' };

test('peremption vide : null envoye, jamais une chaine vide', () => {
    assert.equal(mapProductToApi(base).expiry_date, null);
    assert.equal(mapProductToApi({ ...base, expiryDate: null }).expiry_date, null);
    assert.equal(mapProductToApi({ ...base, expiryDate: '2027-01-31' }).expiry_date, '2027-01-31');
});
test('dosage envoye en dosage_mg numerique', () => {
    assert.equal(mapProductToApi({ ...base, dosage: '500mg' }).dosage_mg, 500);
    assert.equal(mapProductToApi({ ...base, dosage: '2,5' }).dosage_mg, 2.5);
    assert.equal(mapProductToApi(base).dosage_mg, null);
    assert.equal(parseDosageMg('abc'), null);
});
