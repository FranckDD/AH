import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/stock/StockReceipts.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : réceptions de stock (création, détail, annulation) ---
check('StockReceipts', view, [
    // chargement et filtre
    "const CHECK_STATUSES = ['a_controler', 'valide', 'rejete'];", 'v-model="statusFilter"', '@change="loadReceipts"', 'v-for="s in CHECK_STATUSES"',
    'StockOpsGateway.listReceipts({ status: statusFilter.value })', 'StockOpsGateway.listLots()', 'StockOpsGateway.listProducts()', 'onMounted(() => { loadLots(); loadReceipts(); });',
    // tableau
     'r.receipt_number', "r.origin === 'fournisseur' ? (r.supplier || '-') : lotLabel(r.production_lot_id)", 'r.received_date', 'badge(r.status)',
    "r.status === 'rejete' && r.reject_reason", 'r.reject_reason', '@click="openDetail(r)"', "r.status === 'a_controler'", '@click="cancelReceipt(r)"', ':disabled="busyId === r.id"',
    ':rows="receipts"',
    // statuts
    "a_controler: 'bg-amber-100 text-amber-800'".replace("'bg-amber-100 text-amber-800'", "").replace(': ', ''), 'valide:', 'rejete:', 'annule:',
    // détail
    'v-if="detail"', 'detail.receipt_number', 'detail.origin', 'detail.received_date', 'detail.supplier', 'detail.delivery_ref', 'detail.status', 'detail.reject_reason', ':rows="detail.lines || []"',
    'l.product_name', "l.qty_expected ?? '-'", 'l.qty_good', 'l.qty_damaged', 'l.qty_lost', 'l.qty_defective', "l.lot_number || '-'", "l.expiry_date || '-'", '@click="detail = null"',
    'StockOpsGateway.getReceipt(r.id)', 'detailError',
    // annulation
    'if (!window.confirm(t(\'stockOps.confirm_cancel\'))) return;', 'StockOpsGateway.cancelReceipt(r.id)', "pageMessage.value = t('stockOps.cancelled');", 'await Promise.all([loadReceipts(), loadLots()]);',
    // formulaire de création
    'v-if="showForm"', '@submit.prevent="submitReceipt"', 'value="fabrication"', 'value="fournisseur"', 'v-model="form.origin"', '@change="onOriginChange"', 'v-model="form.received_date"',
    'v-model.number="form.production_lot_id"', '@change="onLotChange"', 'v-for="lot in deliveredLots"', 'deliveredLots.length === 0', 'v-model="form.supplier"', 'maxlength="150"', 'v-model="form.delivery_ref"', 'maxlength="100"',
    'v-for="(line, i) in form.lines"', 'v-model.number="line.product_id"', 'v-for="p in products"', 'v-model.number="line.qty_expected"', ":disabled=\"form.origin === 'fabrication'\"",
    'v-for="f in QTY_FIELDS"', 'v-model.number="line[f]"', 'lineTotal(line)', 'lineCheck(line).ok', 'lineCheck(line).error', 'v-model="line.lot_number"', 'maxlength="30"', 'v-model="line.expiry_date"',
    'form.lines.splice(i, 1)', '@click="addLine"', "form.origin === 'fournisseur' && form.lines.length > 1", '@click="showForm = false"', ':disabled="saving"',
    // logique de formulaire
    "form.lines = form.origin === 'fournisseur' ? [newLine()] : [];", 'form.production_lot_id = null;', 'const lot = deliveredLots.value.find((l) => l.id === form.production_lot_id);', 'form.lines = lot ? [prefillFromLot(lot)] : [];',
    "lots.value.filter((l) => l.status === 'livre')", 'const addLine = () => form.lines.push(newLine());',
    "Object.assign(form, { origin: 'fabrication', production_lot_id: null, supplier: '', delivery_ref: '', received_date: today(), lines: [] });",
    // validations de la création, dans l'ordre
    "if (!form.received_date) { formError.value = t('stockOps.err_date_required'); return; }", "if (form.origin === 'fabrication' && !form.production_lot_id) { formError.value = t('stockOps.err_lot_required'); return; }",
    "if (form.origin === 'fournisseur' && !form.supplier.trim()) { formError.value = t('stockOps.err_supplier_required'); return; }", "if (form.lines.length === 0) { formError.value = t('stockOps.err_lines_required'); return; }",
    "if (!line.product_id) { formError.value = t('stockOps.err_product_required'); return; }", 'const chk = validateReceiptLine(line);', 'formError.value = t(`stockOps.line_error_${chk.error}`); return;',
    // forme du payload envoyé
    "const fab = form.origin === 'fabrication';", 'production_lot_id: fab ? form.production_lot_id : null,', 'supplier: fab ? null : form.supplier.trim(),', 'delivery_ref: fab ? null : (form.delivery_ref.trim() || null),',
    "qty_expected: typeof l.qty_expected === 'number' ? l.qty_expected : null,", 'qty_good: l.qty_good, qty_damaged: l.qty_damaged, qty_lost: l.qty_lost, qty_defective: l.qty_defective,',
    "lot_number: fab ? null : ((l.lot_number || '').trim() || null),", 'expiry_date: l.expiry_date || null,', 'await StockOpsGateway.createReceipt(payload);', "pageMessage.value = t('stockOps.receipts.created');",
    "import { validateReceiptLine, prefillFromLot, lineTotal, QTY_FIELDS } from '@/utils/receiptLines';",
    // clés
    "$t('stockOps.receipts.title')", "$t('stockOps.all_statuses')", "$t('stockOps.receipts.new')", "$t('stockOps.receipts.empty')", "t('stockOps.col_receipt_number')",
    "t('stockOps.col_origin')", "t('stockOps.col_source')", "$t('stockOps.col_received_date')", "t('stockOps.col_status')", "$t('stockOps.detail')", "$t('stockOps.cancel')",
    "$t('stockOps.reject_reason')", "$t('stockOps.receipts.detail_title')", "$t('stockOps.col_product')", "$t('stockOps.col_expected')", "t('stockOps.col_good')", "t('stockOps.col_damaged')",
    "t('stockOps.col_lost')", "t('stockOps.col_defective')", "$t('stockOps.col_lot_number')", "$t('stockOps.col_expiry')", "$t('stockOps.close')", "$t('stockOps.receipts.choose_lot')",
    "$t('stockOps.receipts.no_delivered_lot')", "$t('stockOps.col_supplier')", "$t('stockOps.col_delivery_ref')", "$t('stockOps.choose_product')", "$t('stockOps.line_total')",
    "$t('stockOps.optional')", "$t('stockOps.remove_line')", "$t('stockOps.add_line')", "$t('stockOps.saving')", "$t('stockOps.save')",
]);

test('toutes les clés stockOps.* et stockAdminScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:stockOps|stockAdminScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 30);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
    // clés construites : états, origines, erreurs de ligne et colonnes de quantités
    for (const locale of ['fr', 'en']) {
        for (const s of ['a_controler', 'valide', 'rejete']) assert.ok(pick(msgs[locale], `stockOps.check_status.${s}`), `${locale}.check_status.${s}`);
        for (const o of ['fabrication', 'fournisseur']) assert.ok(pick(msgs[locale], `stockOps.origin.${o}`), `${locale}.origin.${o}`);
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('StockReceipts : composants ui/, tableau responsive à lignes alternées, statuts en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    assert.match(view, /<StatusBadge/);
});

test('StockReceipts : détail et création en panneau, messages annoncés, plus de surcouche en dur', () => {
    const t = templateOf(view);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 2, 'détail et création');
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
});

test('StockReceipts : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•]|\p{Extended_Pictographic}/u);
});

test('clés stockAdminScreens (réceptions) en FR et EN', () => {
    const keys = ['receipts_count', 'status_filter', 'origin_group', 'lines_title', 'line_number', 'qty_group'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].stockAdminScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.stockAdminScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.stockAdminScreens.${k}`);
        }
    }
});
