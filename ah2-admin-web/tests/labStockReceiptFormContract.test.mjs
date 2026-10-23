import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labstock/LabStockReceiptForm.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : saisie d'une réception du stock du labo (fiche papier) : la charge envoyée et ses validations sont figées ---
check('LabStockReceiptForm', view, [
    // droits et imports de calcul
    "const canCreateProduct = computed(() => authStore.hasRole(['laborantin', 'StockController', 'admin']));", 'v-if="canCreateProduct"',
    "import { lineTotal, receiptTotal, validateReceipt, buildReceiptPayload, MAX_RECEIPT_LINES, formatMoney } from '@/utils/labReceiptLines';",
    'const total = computed(() => receiptTotal(form.value.lines));', 'const errors = computed(() => validateReceipt(form.value));', 'const checkedCount = computed(() => form.value.lines.filter((l) => l.checked).length);',
    'money(lineTotal(ln.received_qty, ln.unit_price))', 'money(total)',
    // formulaire initial
    "const form = ref({ invoice_number: '', supplier: '', delivery_date: today(), lines: [] });", 'return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, \'0\')}-${String(d.getDate()).padStart(2, \'0\')}`;',
    // en-tête
    'v-model="form.invoice_number"', 'maxlength="100"', 'v-model="form.supplier"', 'maxlength="150"', 'list="lab-suppliers"', 'id="lab-suppliers"', 'v-for="s in suppliers"', 'v-model="form.delivery_date"',
    'const all = [...knownSuppliers.value, ...products.value.map((p) => p.supplier)];', "return [...new Set(all.filter((s) => s && s.trim()).map((s) => s.trim()))].sort();",
    // chargement
    'products.value = await LabStockGateway.listProducts();', 'knownSuppliers.value = (await LabStockGateway.listReceipts()).map((r) => r.supplier);', 'onMounted(load);',
    // lignes
    ':rows="form.lines"', 'v-model="ln.checked"', 'v-model="ln.ordered_qty"', 'v-model="ln.received_qty"', 'v-model="ln.lot_number"', 'maxlength="50"', 'v-model="ln.expiry_date"', 'v-model="ln.unit_price"',
    'min="0"', 'min="1"', 'step="1"', 'step="0.01"', '@click="removeLine(form.lines.indexOf(ln))"', 'ln.product_name', 'ln.packaging', 'form.lines.length >= MAX_RECEIPT_LINES', '@click="openPicker"',
    'const removeLine = (i) => { form.value.lines.splice(i, 1); };', "ordered_qty: '', received_qty: '', lot_number: '', expiry_date: '', unit_price: '', checked: false,",
    "if (!form.value.supplier && p.supplier) form.value.supplier = p.supplier;", 'product_id: p.id, product_name: p.name, packaging: p.packaging || \'\',',
    // choix d'un produit
    'v-if="pickerOpen"', 'ref="pickerInput"', 'v-model="pickerSearch"', 'v-for="p in pickable"', '@click="addLine(p)"', '@click="pickerOpen = false"', '@click="openCreate"', 'pickerInput.value?.focus();',
    ".filter((p) => p.is_active !== false && !used.has(p.id))", "[p.name, p.packaging, p.supplier].some((v) => (v || '').toLowerCase().includes(q))", '!pickable.length',
    // création rapide d'un produit
    'v-if="createOpen"', '@submit.prevent="createProduct"', 'v-model="newProduct.name"', 'v-model="newProduct.packaging"', 'v-model.number="newProduct.alert_threshold"', '@click="createOpen = false"', ':disabled="creating"',
    "if (!name) { modalError.value = t('labStock.err_name_required'); return; }", "if (!Number.isInteger(threshold) || threshold < 0) { modalError.value = t('labStock.err_threshold'); return; }",
    'await LabStockGateway.createProduct({', "supplier: (form.value.supplier || '').trim(), alert_threshold: threshold,", 'products.value.push(p);', 'createOpen.value = false;', 'newProduct.value = { name: pickerSearch.value.trim(), packaging: \'\', alert_threshold: 0 };',
    // envoi : verrou anti double envoi, doublon de facture
    '@click="submit"', ':disabled="errors.length > 0 || busy"', 'if (busy.value || errors.value.length) return;', 'await LabStockGateway.createReceipt(buildReceiptPayload(form.value));',
    "router.push({ path: '/dashboard/lab-stock-receipts', query: { saved: r?.id || 1 } });", 'if (err?.response?.status === 409) duplicateError.value = msg;', 'else pageError.value = msg;', "window.scrollTo({ top: 0, behavior: 'smooth' });",
    'v-if="duplicateError"', "touched.value = true;", 'errors.length && touched',
    // retour
    'to="/dashboard/lab-stock-receipts"',
    // clés
    "t('labStock.receipt_form_title')", "t('labStock.receipt_form_subtitle')", "t('labStock.back_to_receipts')", "t('labStock.duplicate_invoice_title')", "t('labStock.invoice_number')", "t('labStock.col_supplier')",
    "t('labStock.delivery_date')", "t('labStock.receipt_lines')", "t('labStock.add_line')", "t('labStock.no_lines')", "t('labStock.checked')", "t('labStock.remove_line')", "t('labStock.col_ordered')",
    "t('labStock.col_received')", "t('labStock.col_lot')", "t('labStock.col_expiry')", "t('labStock.col_unit_price')", "t('labStock.col_line_total')", "t('labStock.receipt_total')",
    "t('labStock.checked_count', { n: checkedCount, total: form.lines.length })", "t('labStock.submitting')", "t('labStock.submit_receipt')", "t('labStock.search_product')",
    "t('labStock.no_match')", "t('stockOps.close')", "t('labStock.create_product')", "t('labStock.col_product')", "t('labStock.col_packaging')", "t('labStock.col_threshold')", "t('stockOps.save')",
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
test('LabStockReceiptForm : composants ui/, lignes en tableau responsive, choix du produit et création en panneau', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 2, 'choix du produit et création');
    assert.equal((t.match(/<ResponsiveTable/g) || []).length, 1);
    assert.doesNotMatch(t, /fixed inset-0/);
});

test('LabStockReceiptForm : champs étiquetés, erreurs annoncées, doublon de facture visible, total toujours visible', () => {
    const t = templateOf(view);
    assert.match(t, /role="alert"/);
    assert.match(t, /sticky bottom-0/);
    assert.match(t, /aria-label/);
    assert.match(t, /variant="danger"/, 'retrait d’une ligne');
});

test('LabStockReceiptForm : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
});

test('clés labStockScreens (formulaire de réception) en FR et EN', () => {
    const keys = ['invoice_header', 'picker_title', 'lines_table'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labStockScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labStockScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labStockScreens.${k}`);
        }
    }
});
