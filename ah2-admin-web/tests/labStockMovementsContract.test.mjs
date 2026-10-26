import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labstock/LabStockMovements.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : historique des mouvements du stock du labo (filtre produit, limite, libelles) ---
check('LabStockMovements', view, [
    'const LIMIT = 200;', "const TYPES = ['reception', 'comptage', 'annulation_reception'];",
    'LabStockGateway.listMovements({ productId: productId.value ? Number(productId.value) : undefined, limit: LIMIT })',
    'LabStockGateway.listProducts({ includeInactive: true })', 'v-model="productId"', '@change="load"', 'v-for="p in products"', ':value="String(p.id)"',
    'value=""', "t(`labStock.mv_type.${ty}`)", "String(ty || '?')",
    "const signed = (v) => { const n = Number(v ?? 0); return n > 0 ? `+${n}` : String(n); };",
    "const d = new Date(/[zZ]|[+-]\\d\\d:?\\d\\d$/.test(s) ? s : `${s}Z`);", 'return Number.isNaN(d.getTime()) ? s : formatDateTimeDMY(d);',
    "if (m.ref_type === 'receipt' && m.ref_id) return t('labStock.mv_ref_receipt', { id: m.ref_id });",
    "if (m.ref_type === 'count' && m.ref_id) return t('labStock.mv_ref_count', { id: m.ref_id });",
    'rows.value = [];', "pageError.value = describeLabStockError(e, t('stockOps.error_load'));", 'v-if="rows.length >= LIMIT"', "t('labStock.mv_limit_note', { n: LIMIT })",
    "m.product_name || '?'", 'm.created_by_name', 'Number(m.quantity_after)', 'signed(m.change_qty)', 'formatDateTime(m.created_at)', 'refText(m)',
    "t('labStock.mv_title')", "t('labStock.mv_subtitle')", "t('labStock.mv_all_products')", "t('labStock.mv_empty')", "t('labStock.mv_col_date')", "t('labStock.col_product')",
    "t('labStock.mv_col_type')", "t('labStock.mv_col_change')", "t('labStock.mv_col_after')", "t('labStock.mv_col_by')", "t('labStock.mv_col_ref')",
]);

test('toutes les clés labStock.*, stockOps.* et labStockScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:labStock|stockOps|labStockScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 12);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
    for (const ty of ['reception', 'comptage', 'annulation_reception']) {
        for (const locale of ['fr', 'en']) assert.ok(pick(msgs[locale], `labStock.mv_type.${ty}`), `${locale}.labStock.mv_type.${ty}`);
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabStockMovements : composants ui/, tableau responsive à lignes alternées, types en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FormField']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.match(t, /<StatusBadge/);
    assert.doesNotMatch(t, /hidden lg:block|lg:hidden/);
});

test('LabStockMovements : erreur annoncée, filtre étiqueté, quantité signée (le signe porte le sens)', () => {
    const t = templateOf(view);
    assert.match(t, /role="alert"/);
    assert.match(t, /<FormField/);
    assert.match(t, /signed\(m\.change_qty\)/);
});

test('LabStockMovements : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});

test('clés labStockScreens (mouvements) en FR et EN', () => {
    const keys = ['movements_count', 'product_filter'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labStockScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labStockScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labStockScreens.${k}`);
        }
    }
});
