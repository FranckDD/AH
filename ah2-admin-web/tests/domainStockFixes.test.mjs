// Defauts du stock releves par les guides (2026-10-26) : contrats de source et fonctions pures.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const read = (f) => readFileSync(new URL(`../src/${f}`, import.meta.url), 'utf8');
const msg = (loc, key) => key.split('.').reduce((o, k) => (o == null ? o : o[k]), i18n.global.getLocaleMessage(loc));
const bothLocales = (key) => { assert.ok(msg('fr', key), `fr ${key}`); assert.ok(msg('en', key), `en ${key}`); };

test('notification de decision d ajustement : le controleur va au comptage, la secretaire au stock', () => {
    const bell = read('components/notifications/NotificationBell.vue');
    const block = bell.slice(bell.indexOf("n.type === 'stock_decided'"));
    assert.match(block, /kind === 'adjustment'/);
    assert.match(block, /stock-count/);
    assert.match(block, /\/secretariat\/stock/);
    assert.match(block, /hasRole\(\['StockController'/);
});

test('historique du comptage : issue de chaque demande + liste de mes demandes', () => {
    const reveal = read('components/stock/StockCountReveal.vue');
    assert.match(reveal, /row\.adjustment_status/);
    for (const s of ['en_attente', 'approuve', 'refuse', 'remplace', 'annule']) bothLocales(`stockCount.request_status.${s}`);
    const view = read('views/modules/stock/StockCount.vue');
    assert.match(read('components/stock/StockCountHistory.vue'), /StockCountRequests/);
    assert.match(read('components/stock/StockCountRequests.vue'), /myRequests/);
    bothLocales('stockCount.my_requests_title');
    bothLocales('stockCount.my_requests_empty');
    assert.match(read('services/StockCountGateway.js'), /\/stock-counts\/requests/);
});

test('portee du comptage : le choix « selection » est retire', () => {
    const view = read('views/modules/stock/StockCount.vue');
    assert.doesNotMatch(view, /scope_selection|scope === 'selection'|value="selection"/);
});

test('erreur de correction de ligne : code traduit + produit de la ligne', async () => {
    const { describeStockLineError } = await import('../src/utils/stockLineError.js');
    const t = (k, p) => i18n.global.t(k, p || {}, { locale: 'en' });
    const te = (k) => i18n.global.te(k, 'en');
    const lines = [{ id: 7, product_name: 'Paracetamol' }];
    const err = { response: { data: { detail: { code: 'line_total_increase', line_id: 7, params: { current: 5, requested: 9 }, message: 'Ligne 7 : ...' } } } };
    const out = describeStockLineError(err, lines, t, te);
    assert.ok(out.startsWith('Paracetamol : '), out);
    assert.ok(!/Ligne 7/.test(out), out);
    assert.equal(describeStockLineError({ response: { data: { detail: 'texte' } } }, lines, t, te), '');
    for (const c of ['line_total_increase', 'line_missing', 'qty_negative', 'qty_zero', 'qty_over_expected']) bothLocales(`stockOps.server_err.${c}`);
});

test('ligne de reception : l erreur disparait des que la valeur est corrigee', () => {
    const view = read('views/modules/stock/StockControlQueue.vue');
    assert.match(view, /@input="clearLineError\(l\)"/);
    assert.match(view, /const clearLineError/);
});

test('mouvements : auteur en nom complet', () => {
    assert.match(read('views/modules/stock/StockMovements.vue'), /m\.created_by_name/);
});

test('fenetre produit : libelles traduits', () => {
    const modal = read('components/stock/ProductModal.vue');
    assert.doesNotMatch(modal, /Seuil Alerte|Mettre à jour|Mettre a jour/);
    assert.match(modal, /t\('stock\.modal\.threshold'\)/);
    assert.match(modal, /t\('stock\.modal\.update'\)/);
    assert.doesNotMatch(modal, /label="Dosage/);
});
