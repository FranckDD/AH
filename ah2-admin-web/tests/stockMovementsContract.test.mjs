import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/stock/StockMovements.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : historique en lecture seule des mouvements de stock ---
check('StockMovements', view, [
    // types, pagination, chargement
    "const MOVEMENT_TYPES = ['VENTE', 'ANNULATION_VENTE', 'initial', 'update', 'renew', 'reception',", "'avarie_endommage', 'avarie_perdu', 'avarie_defectueux'];", 'const PER_PAGE = 50;',
    'const today = todayLocalISO();', 'Math.max(1, Math.ceil(total.value / PER_PAGE))',
    'StockOpsGateway.listMovements({', 'productId: filters.productId, movementType: filters.movementType,', 'dateFrom: filters.dateFrom, dateTo: filters.dateTo, page: page.value, perPage: PER_PAGE,',
    'items.value = data?.items || [];', 'total.value = data?.total || 0;', 'StockOpsGateway.listStockProducts()', 'if (!pageError.value) pageError.value = describeStockError(err, t(\'stockOps.error_products\'));',
    // filtres
    '@submit.prevent="applyFilters"', 'v-model="productSearch"', 'v-model="filters.productId"', 'v-for="p in visibleProducts"', 'v-model="filters.movementType"', 'v-for="mt in MOVEMENT_TYPES"',
    'v-model="filters.dateFrom"', 'v-model="filters.dateTo"', ':max="today"', '@click="resetFilters"',
    "String(p.name).toLowerCase().includes(q) || String(p.id) === q", 'visibleProducts.value.length === 1', 'filters.productId = visibleProducts.value[0].id;',
    "Object.assign(filters, { productId: null, movementType: '', dateFrom: '', dateTo: '' });", 'const goTo = (p) => { page.value = p; load(); };',
    // tableau
    ':rows="items"', 'row-key="movement_id"', 'formatDateTime(m.created_at)', "m.product_name || ('#' + m.product_id)", 'movementLabel(m.movement_type)', "m.change_qty > 0 ? '+' : ''", 'm.change_qty', 'm.note', "m.created_by || ''",
    "te(`stockControl.movement.${mt}`) ? t(`stockControl.movement.${mt}`) : mt", 'm.change_qty > 0', 'm.change_qty < 0',
    // pagination
    'totalPages > 1', '@click="goTo(page - 1)"', '@click="goTo(page + 1)"', ':disabled="page <= 1"', ':disabled="page >= totalPages"',
    // clés
    "$t('stockControl.movements_title')", "$t('stockControl.product_search')", "$t('stockControl.all_products')", "$t('stockControl.all_types')", "$t('stockControl.date_from')", "$t('stockControl.date_to')",
    "$t('stockControl.reset')", "$t('stockControl.apply')", "$t('stockControl.no_movements')", "t('stockOps.col_date')", "t('stockOps.col_product')", "t('stockControl.movement_type')",
    "t('stockOps.col_quantity')", "t('stockControl.note')", "t('stockControl.author')", "$t('stockControl.page_of', { page, total: totalPages })",
]);

test('toutes les clés stockControl.*, stockOps.* et stockAdminScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:stockControl|stockOps|stockAdminScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 15);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('StockMovements : composants ui/, tableau responsive à lignes alternées, quantités à droite', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'FormField', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    assert.match(view, /align: 'right'/);
});

test('StockMovements : entrée et sortie distinguées par un signe écrit, pas seulement par la couleur', () => {
    assert.match(view, /m\.change_qty > 0 \? '\+' : ''/);
    assert.match(templateOf(view), /text-tone-success-text/);
    assert.match(templateOf(view), /text-tone-danger-text/);
});

test('StockMovements : pagination par boutons nommés, erreur annoncée', () => {
    const t = templateOf(view);
    assert.match(t, /aria-label/);
    assert.match(t, /role="alert"/);
});

test('StockMovements : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›]|\p{Extended_Pictographic}/u);
});

test('clés stockAdminScreens (mouvements) en FR et EN', () => {
    const keys = ['movements_count', 'prev_page', 'next_page', 'filters_label'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].stockAdminScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.stockAdminScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.stockAdminScreens.${k}`);
        }
    }
});
