import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/stock/ProductionLots.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : lots de fabrication (création, livraison, annulation) ---
check('ProductionLots', view, [
    // chargement et filtre
    "const LOT_STATUSES = ['produit', 'livre', 'recu', 'annule'];", 'v-model="statusFilter"', '@change="loadLots"', 'v-for="s in LOT_STATUSES"',
    'StockOpsGateway.listLots(statusFilter.value)', 'StockOpsGateway.listProducts()', 'onMounted(loadLots);',
    // tableau
    'lot.lot_number', 'lot.product_name', 'lot.quantity_produced', "lot.production_date || '-'", "lot.delivery_date || '-'", "lot.expiry_date || '-'", "lot.producer || '-'",
    'badge(lot.status)', "lot.status === 'produit'", "lot.status === 'produit' || lot.status === 'livre'", '@click="openDeliver(lot)"', '@click="cancelLot(lot)"', ':disabled="busyId === lot.id"',
    ':rows="lots"'.replace(':rows="lots"', 'lots.value = (await StockOpsGateway.listLots(statusFilter.value)) || [];'),
    // formulaire de création
    'v-if="showForm"', '@submit.prevent="submitLot"', 'v-model.number="form.product_id"', 'v-for="p in products"', 'v-model.number="form.quantity_produced"', 'min="1"', 'step="1"',
    'v-model="form.production_date"', 'v-model="form.delivery_date"', 'v-model="form.expiry_date"', 'v-model="form.producer"', 'maxlength="150"', '@click="showForm = false"', ':disabled="saving"',
    'const emptyForm = () => ({ product_id: null, quantity_produced: null, production_date: today(), delivery_date: \'\', expiry_date: \'\', producer: \'\' });', 'Object.assign(form, emptyForm());',
    "if (!form.product_id) { formError.value = t('stockOps.err_product_required'); return; }",
    "if (!Number.isInteger(form.quantity_produced) || form.quantity_produced <= 0) { formError.value = t('stockOps.err_quantity_positive'); return; }",
    "if (!form.production_date) { formError.value = t('stockOps.err_date_required'); return; }",
    'delivery_date: form.delivery_date || null,', 'expiry_date: form.expiry_date || null,', 'producer: form.producer.trim() || null,', 'await StockOpsGateway.createLot(payload);',
    "pageMessage.value = t('stockOps.lots.created');",
    // livraison
    'v-if="deliverLot"', '@submit.prevent="submitDeliver"', 'v-model="deliverDate"', '@click="deliverLot = null"', 'deliverLot.lot_number', 'deliverDate.value = today();',
    'await StockOpsGateway.deliverLot(deliverLot.value.id, deliverDate.value || null);', "pageMessage.value = t('stockOps.lots.delivered');", 'deliverError',
    // annulation
    "if (!window.confirm(t('stockOps.confirm_cancel'))) return;", 'await StockOpsGateway.cancelLot(lot.id);', "pageMessage.value = t('stockOps.cancelled');",
    // clés
    "$t('stockOps.lots.title')", "$t('stockOps.all_statuses')", "$t('stockOps.lots.new')", "$t('stockOps.lots.empty')", "t('stockOps.col_lot_number')", "t('stockOps.col_product')",
    "t('stockOps.col_quantity_produced')", "t('stockOps.col_production_date')", "t('stockOps.col_delivery_date')", "t('stockOps.col_expiry')", "t('stockOps.col_producer')", "t('stockOps.col_status')",
    "$t('stockOps.lots.mark_delivered')", "$t('stockOps.cancel')", "$t('stockOps.choose_product')", "$t('stockOps.optional')", "$t('stockOps.close')", "$t('stockOps.saving')", "$t('stockOps.save')", "$t('stockOps.confirm')",
]);

test('toutes les clés stockOps.* et stockAdminScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:stockOps|stockAdminScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 20);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
    for (const locale of ['fr', 'en']) {
        for (const s of ['produit', 'livre', 'recu', 'annule']) assert.ok(pick(msgs[locale], `stockOps.lot_status.${s}`), `${locale}.lot_status.${s}`);
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ProductionLots : composants ui/, tableau responsive à lignes alternées, statuts en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    assert.match(view, /<StatusBadge/);
});

test('ProductionLots : création et livraison en panneau, messages annoncés, plus de surcouche en dur', () => {
    const t = templateOf(view);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 2, 'création et livraison');
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
});

test('ProductionLots : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•]|\p{Extended_Pictographic}/u);
});

test('clé stockAdminScreens.lots_count en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        const v = msgs[locale].stockAdminScreens?.lots_count;
        assert.equal(typeof v, 'string', `${locale}.stockAdminScreens.lots_count`);
        assert.doesNotMatch(v, /[—–…·]/);
    }
});
