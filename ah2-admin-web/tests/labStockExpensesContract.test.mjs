import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labstock/LabStockExpenses.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : depenses du stock du labo (periode, mois, fournisseurs, historique de prix) ---
check('LabStockExpenses', view, [
    "import { formatMoney } from '@/utils/labReceiptLines';", "import { buildMonthBars, monthLabel } from '@/utils/labStockExpenses';",
    'LabStockGateway.expenses({ from: from.value, to: to.value })', 'LabStockGateway.priceHistory(Number(productId.value))', 'LabStockGateway.listProducts({ includeInactive: true })',
    'data.value = { total: r?.total ?? 0, from: r?.from, to: r?.to, by_month: r?.by_month || [], by_supplier: r?.by_supplier || [] };',
    "if (!from.value && r?.from) from.value = String(r.from).slice(0, 10);", "if (!to.value && r?.to) to.value = String(r.to).slice(0, 10);",
    "const bars = computed(() => (data.value ? buildMonthBars(data.value.by_month, data.value.from, data.value.to) : []));",
    "const [y, m, d] = String(v).slice(0, 10).split('-').map(Number);", 'return formatDateDMY(new Date(y, m - 1, d));',
    '@submit.prevent="load"', 'v-model="from"', 'v-model="to"', 'type="date"', ':disabled="isLoading"', 'v-model="productId"', '@change="loadPrices"',
    'if (!productId.value) return;', 'v-if="productId && !priceLoading && !priceError"', 'v-if="!prices.length"',
    "priceError.value = describeLabStockError(e, t('stockOps.error_load'));", "pageError.value = describeLabStockError(e, t('stockOps.error_load'));",
    'v-if="isLoading && !data"', 'v-if="data"', 'v-for="b in bars"', 'bars.some((b) => !b.empty)', 'b.pct', 'monthLabel(b.month, locale)', 'formatMoney(b.total)',
    'v-for="s in data.by_supplier"', 'formatMoney(s.total)', 'formatMoney(data.total)', "t('labStock.ex_period', { from: formatDate(data.from), to: formatDate(data.to) })",
    'formatDate(h.delivery_date)', 'h.supplier', "t('labStock.mv_ref_receipt', { id: h.receipt_id })", 'Number(h.received_qty)', 'formatMoney(h.unit_price)', 'prices.value.map((h, i) => ({ ...h, key: i }))', ':rows="priceRows"',
    "t('labStock.ex_title')", "t('labStock.ex_subtitle')", "t('labStock.ex_from')", "t('labStock.ex_to')", "t('labStock.ex_apply')", "t('labStock.ex_total')", "t('labStock.ex_by_month')",
    "t('labStock.ex_by_supplier')", "t('labStock.ex_empty')", "t('labStock.ex_price_title')", "t('labStock.ex_price_choose')", "t('labStock.ex_price_empty')",
    "t('labStock.ex_col_date')", "t('labStock.ex_col_supplier')", "t('labStock.ex_col_receipt')", "t('labStock.ex_col_qty')", "t('labStock.ex_col_price')",
]);

test('toutes les clés labStock.*, stockOps.* et labStockScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:labStock|stockOps|labStockScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 20);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabStockExpenses : composants ui/, total en tuile, historique de prix en tableau responsive', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'StatTile', 'ResponsiveTable', 'FormField', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.doesNotMatch(t, /hidden lg:block|lg:hidden/);
});

test('LabStockExpenses : erreurs annoncées, champs étiquetés, barres mensuelles avec montant écrit et nom accessible', () => {
    const t = templateOf(view);
    assert.equal((t.match(/role="alert"/g) || []).length >= 2, true, 'erreur de periode et erreur de prix');
    assert.match(t, /<FormField/);
    assert.match(t, /role="img"|role="progressbar"|aria-hidden="true"/, 'la barre est decorative ou nommee');
    assert.match(t, /bg-brand-/);
});

test('LabStockExpenses : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→×]|\p{Extended_Pictographic}/u);
});

test('clés labStockScreens (dépenses) en FR et EN', () => {
    const keys = ['expenses_period_label', 'prices_count', 'product_filter'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labStockScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labStockScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labStockScreens.${k}`);
        }
    }
});
