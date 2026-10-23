import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labstock/LabStockReceipts.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : réceptions du stock du labo (liste, détail, annulation par l'admin avec motif) ---
check('LabStockReceipts', view, [
    // droits et chargement
    "const canReceive = computed(() => authStore.hasRole(['StockController', 'promoteur']));", "const canCancel = computed(() => authStore.hasRole(['admin']));", 'v-if="canReceive"', 'to="/dashboard/lab-stock-receipts/new"',
    "const filters = ref({ supplier: '', from: '', to: '' });", 'LabStockGateway.listReceipts({ ...filters.value })', 'onMounted(() => {', "if (route.query.saved) flash(t('labStock.receipt_saved'));", 'load();',
    // filtres
    '@submit.prevent="load"', 'v-model="filters.supplier"', 'maxlength="150"', 'v-model="filters.from"', 'v-model="filters.to"',
    // lignes
    'r.supplier', 'r.invoice_number', "(r.lines || []).length", 'money(r.total_amount)', 'formatDate(r.delivery_date)', 'statusText(r.status)', 'r.created_by_name', "r.status === 'annule'",
    "const statusText = (s) => (s === 'valide' ? t('labStock.receipt_valid') : s === 'annule' ? t('labStock.receipt_cancelled') : (s || '?'));", "const money = formatMoney;",
    // détail
    '@click="openDetail(r.id)"', 'v-if="detail || detailLoading"', 'detailLoading', 'await LabStockGateway.getReceipt(id)', 'detail.supplier', 'detail.invoice_number', 'detail.delivery_date', 'detail.created_by_name', 'detail.status',
    "detail.status === 'annule'", "t('labStock.cancelled_info', { name: detail.cancelled_by_name || '?', reason: detail.cancel_reason || '' })", ':rows="detail.lines || []"', 'ln.product_name', 'ln.packaging',
    'ln.ordered_qty != null', 'num(ln.ordered_qty)', 'num(ln.received_qty)', 'ln.lot_number', 'formatDate(ln.expiry_date)', 'money(ln.unit_price)', 'money(ln.line_total)', 'money(detail.total_amount)',
    '@click="closeDetail"', 'const closeDetail = () => { detail.value = null; };',
    // annulation par l'admin
    "canCancel && detail.status === 'valide'", 'v-model="cancelReason"', 'maxlength="2000"', ':disabled="busy || !cancelReason.trim()"', '@click="cancelReceipt"',
    'if (busy.value || !cancelReason.value.trim()) return;', 'await LabStockGateway.cancelReceipt(detail.value.id, cancelReason.value.trim());', "flash(t('labStock.receipt_cancel_done'));",
    'setTimeout(() => { pageMessage.value = \'\'; }, 5000);',
    // clés
    "t('labStock.receipts_title')", "t('labStock.receipts_subtitle')", "t('labStock.new_receipt')", "t('labStock.col_supplier')", "t('labStock.filter_from')", "t('labStock.filter_to')", "t('labStock.filter_apply')",
    "t('labStock.no_receipts')", "t('labStock.invoice_number')", "t('labStock.delivery_date')", "t('labStock.col_lines')", "t('labStock.receipt_total')", "t('labStock.col_status')", "t('labStock.created_by')",
    "t('labStock.view_detail')", "t('labStock.col_no')", "t('labStock.col_designation')", "t('labStock.col_packaging')", "t('labStock.col_ordered')", "t('labStock.col_received')", "t('labStock.col_lot')",
    "t('labStock.col_expiry')", "t('labStock.col_unit_price')", "t('labStock.col_line_total')", "t('labStock.cancel_reason')", "t('labStock.cancel_receipt')", "t('stockOps.close')",
]);

test('toutes les clés labStock.*, stockOps.* et labStockScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:labStock|stockOps|labStockScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 25);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabStockReceipts : composants ui/, deux tableaux responsives à lignes alternées, statuts en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.equal((templateOf(view).match(/<ResponsiveTable/g) || []).length, 2, 'liste et lignes du détail');
    assert.match(view, /<StatusBadge/);
    assert.match(view, /align: 'right'/);
});

test('LabStockReceipts : détail en panneau, messages annoncés, annulation en rouge, bouton de création par le lien du routeur', () => {
    const t = templateOf(view);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 1);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
    assert.match(t, /variant="danger"/);
    assert.match(t, /<router-link v-if="canReceive"/);
});

test('LabStockReceipts : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});

test('clés labStockScreens (réceptions) en FR et EN', () => {
    const keys = ['receipts_count', 'filters_label'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labStockScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labStockScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labStockScreens.${k}`);
        }
    }
});
