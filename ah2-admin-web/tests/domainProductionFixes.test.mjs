// Defauts Fabrication releves par les guides (2026-10-26) : contrats de source et fonctions pures.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const read = (f) => readFileSync(new URL(`../src/${f}`, import.meta.url), 'utf8');
const msg = (loc, key) => key.split('.').reduce((o, k) => (o == null ? o : o[k]), i18n.global.getLocaleMessage(loc));
const bothLocales = (key) => { assert.ok(msg('fr', key), `fr ${key}`); assert.ok(msg('en', key), `en ${key}`); };

test('cloche : le responsable de production la voit, avec le libelle et le lien de l alerte de seuil', () => {
    assert.match(read('components/layout/MainLayout.vue'), /:bell-roles="\[[^\]]*'ProductionManager'/);
    const bell = read('components/notifications/NotificationBell.vue');
    assert.match(bell, /n\.type === 'fab_intrant_low'/);
    assert.match(bell, /notifications\.fab_intrant_low/);
    assert.match(bell, /\/dashboard\/fabrication-intrants/);
    bothLocales('notifications.fab_intrant_low');
});

test('controle quotidien : le type intrant_sous_seuil est connu de l ecran Rapports', async () => {
    const { ANOMALY_KINDS } = await import('../src/utils/reports.js');
    assert.ok(ANOMALY_KINDS.includes('intrant_sous_seuil'));
    bothLocales('reports.kinds.intrant_sous_seuil');
});

test('quantites : nombre mal forme distingue de zero', async () => {
    const { classifyQuantity, formatUnitCost, purchaseOptionLabel } = await import('../src/utils/fabFormat.js');
    assert.equal(classifyQuantity('12'), 'ok');
    assert.equal(classifyQuantity('12,5'), 'ok');
    assert.equal(classifyQuantity('0'), 'zero');
    assert.equal(classifyQuantity('0.000'), 'zero');
    assert.equal(classifyQuantity(''), 'invalid');
    assert.equal(classifyQuantity('abc'), 'invalid');
    assert.equal(classifyQuantity('-3'), 'invalid');
    assert.equal(classifyQuantity('1.2345'), 'invalid');
    bothLocales('fabrication.err_quantity_invalid');
    for (const f of ['views/modules/fabrication/FabLotDetail.vue', 'views/modules/fabrication/FabIntrants.vue']) {
        assert.match(read(f), /err_quantity_invalid/, f);
    }
    // cout par bouteille : deux decimales (188,24 et non 188)
    assert.match(formatUnitCost(188.24), /188,24/);
    assert.match(formatUnitCost('188.2400'), /188,24/);
    assert.match(formatUnitCost(0), /0,00/);
    assert.match(read('views/modules/fabrication/FabLotDetail.vue'), /formatUnitCost\(batch\.unit_cost\)/);
    // l achat propose en liste montre aussi sa reference de livraison
    const label = purchaseOptionLabel({ intrant_name: 'Miel', supplier: 'Ets X', delivery_ref: 'BL-42', purchase_date: '2026-10-01', remaining_qty: '12.5' }, (k) => k, (v) => String(v), (v) => v);
    assert.match(label, /BL-42/);
    assert.match(label, /Miel/);
});

test('achats : annule = restant a zero, modification minimale d un achat non consomme', () => {
    const view = read('views/modules/fabrication/FabIntrants.vue');
    assert.match(view, /p\.status === 'actif' \? qty\(p\.remaining_qty\) : qty\(0\)/);
    assert.match(view, /FabricationGateway\.updatePurchase\(/);
    assert.match(view, /canEditPurchase\(p\)/);
    assert.match(view, /v-model="purchaseEditForm\.unit_cost"/);
    assert.match(view, /v-model="purchaseEditForm\.supplier"/);
    assert.match(view, /v-model="purchaseEditForm\.delivery_ref"/);
    for (const k of ['edit_purchase', 'edit_purchase_title', 'purchase_updated']) bothLocales(`fabrication.${k}`);
});

test('lots de production du stock : Annuler seulement pour le createur ou l admin, compte sans les annules, pluriel', () => {
    const view = read('views/modules/stock/ProductionLots.vue');
    assert.match(view, /canCancelLot\(lot\)/);
    assert.match(view, /created_by/);
    assert.match(view, /activeLotsCount/);
    assert.doesNotMatch(view, /lots_count', \{ n: lots\.length \}/);
    const t = (k, c) => i18n.global.t(k, c, { locale: 'en' });
    assert.equal(t('stockAdminScreens.lots_count', 1), '1 batch');
    assert.equal(t('stockAdminScreens.lots_count', 4), '4 batches');
    assert.equal(i18n.global.t('stockAdminScreens.lots_count', 1, { locale: 'fr' }), '1 lot');
    bothLocales('stockAdminScreens.lots_cancelled');
});
