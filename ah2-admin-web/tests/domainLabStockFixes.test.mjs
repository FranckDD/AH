// Defauts labo / stock labo releves par les guides (2026-10-26) : contrats de source et fonctions pures.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const read = (f) => readFileSync(new URL(`../src/${f}`, import.meta.url), 'utf8');
const msg = (loc, key) => i18n.global.getLocaleMessage(loc)[key.split('.')[0]] && key.split('.').slice(1)
    .reduce((o, k) => (o == null ? o : o[k]), i18n.global.getLocaleMessage(loc)[key.split('.')[0]]);
const bothLocales = (key) => { assert.ok(msg('fr', key), `fr ${key}`); assert.ok(msg('en', key), `en ${key}`); };

test('paillasse : retour apres Save/Validate (message) et liste rafraichie', () => {
    const view = read('views/modules/labo/LabTechnician.vue');
    assert.match(view, /useToastStore/);
    assert.match(view, /t\('lab\.technician\.draft_saved'\)/);
    assert.match(view, /t\('lab\.technician\.validated_ok'\)/);
    bothLocales('lab.technician.draft_saved');
    bothLocales('lab.technician.validated_ok');
    const store = read('stores/labStore.js');
    const save = store.slice(store.indexOf('async saveValues'), store.indexOf('async amendResult') > 0 ? store.indexOf('// Correction d\'un resultat valide') : undefined);
    assert.match(save, /fetchPaillasseList\(\)/);
});

test('reception du stock labo : toutes les lignes doivent etre pointees', async () => {
    const { validateReceipt } = await import('../src/utils/labReceiptLines.js');
    const line = (o = {}) => ({ product_id: 1, received_qty: '10', lot_number: 'L1', expiry_date: '2027-01-01', unit_price: '1500', checked: true, ...o });
    const form = (lines) => ({ invoice_number: 'F-1', supplier: 'S', delivery_date: '2026-10-21', lines });
    const today = new Date(2026, 9, 21);
    assert.deepEqual(validateReceipt(form([line()]), today), []);
    assert.ok(validateReceipt(form([line(), line({ product_id: 2, checked: false })]), today).includes('labStock.receipt_err_unchecked'));
    bothLocales('labStock.receipt_err_unchecked');
});

test('alertes de peremption : quantite recue du lot et stock actuel du produit', () => {
    const view = read('views/modules/labstock/LabStockAlerts.vue');
    assert.match(view, /e\.received_qty/);
    assert.match(view, /e\.product_quantity/);
    bothLocales('labStock.alerts_lot_stock');
});
