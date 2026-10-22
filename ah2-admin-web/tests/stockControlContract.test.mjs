import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/stock/StockControlQueue.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : file « à contrôler » (réceptions et avaries), corrections, validation, rejet ---
check('StockControlQueue', view, [
    // chargement
    "const TABS = ['receipts', 'incidents'];", "const tab = ref('receipts');", 'StockOpsGateway.listReceipts({ status: \'a_controler\' })', 'StockOpsGateway.listIncidents({ status: \'a_controler\' })',
    'const [r, i] = await Promise.all([', 'receipts.value = r || [];', 'incidents.value = i || [];', 'onMounted(loadAll);', '@click="loadAll"',
    'const again = receipts.value.find((x) => x.id === selected.value.id);', 'if (again) selectReceipt(again); else { selected.value = null; editLines.value = []; }',
    // onglets
    'v-for="tb in TABS"', '@click="tab = tb"', "tab === tb", "tab === 'receipts'", "tb === 'receipts' ? receipts.length : incidents.length", 'stockControl.tab_${tb}',
    // droits : jamais contrôler sa propre saisie
    'const myId = computed(() => authStore.user?.id ?? null);', 'const isMine = (item) => myId.value !== null && item?.created_by === myId.value;',
    'const canDecide = computed(() => !!selected.value && !isMine(selected.value));', 'isMine(r)', 'isMine(inc)', 'v-if="canDecide"', 'v-if="!canDecide"',
    // réceptions : liste et détail
    '@click="selectReceipt(r)"', "selected?.id === r.id", "r.receipt_number || ('#' + r.id)", 'r.received_date', 'stockOps.origin.${r.origin}', 'r.lines.length', 'v-if="!selected"',
    'selected.supplier', 'selected.delivery_ref', 'selected.received_date', "actorLabel(selected.created_by_name, selected.created_by)", 'editLines.value = r.lines.map((l) => ({ ...l }));', 'lineErrors.value = [];',
    'QTY_FIELDS', 'v-model.number="l[f]"', 'min="0"', 'step="1"', 'lineTotal(l)', "l.qty_expected ??", 'l.product_name', 'l.lot_number', 'l.expiry_date', 'lineErrors[',
    'stockOps.line_error_${lineErrors[',
    // corrections
    'const linesDirty = computed(() => {', 'QTY_FIELDS.some((f) => l[f] !== selected.value.lines[i]?.[f])', 'v-if="linesDirty"', '@click="saveLines"',
    'lineErrors.value = editLines.value.map((l) => {', 'const res = validateReceiptLine(l);', 'return lineErrors.value.every((e) => !e);',
    'await StockOpsGateway.updateReceiptLines(selected.value.id, changed);', "pageMessage.value = t('stockControl.corrections_saved');",
    // validation
    '@click="validateReceipt"', '@click="validateIncident(inc)"', "if (!window.confirm(t('stockControl.confirm_validate'))) return;", 'if (linesDirty.value) await pushCorrections();',
    'await StockOpsGateway.validateReceipt(selected.value.id);', 'await StockOpsGateway.validateIncident(inc.id);', "pageMessage.value = t('stockControl.validated');",
    // rejet
    "@click=\"openReject('receipt', selected)\"", "@click=\"openReject('incident', inc)\"", 'rejectTarget.value = { kind, id: item.id };', 'v-if="rejectTarget"', '@submit.prevent="confirmReject"', 'v-model="rejectReason"', 'maxlength="2000"',
    '@click="rejectTarget = null"', "if (!reason) { rejectError.value = t('stockOps.err_reason_required'); return; }", 'await StockOpsGateway.rejectReceipt(id, reason);', 'await StockOpsGateway.rejectIncident(id, reason);',
    "pageMessage.value = t('stockControl.rejected');", ':disabled="busy"',
    // avaries
    'inc.incident_date', 'inc.product_name', 'stockOps.kind.${inc.kind}', 'inc.quantity', 'inc.reason', "actorLabel(inc.created_by_name, inc.created_by)",
    // clés
    "$t('stockControl.title')", "$t('stockControl.refresh')", "$t('stockOps.loading')", "$t('stockControl.empty_receipts')", "$t('stockControl.lines')", "$t('stockControl.own_entry')", "$t('stockControl.select_hint')",
    "$t('stockOps.col_origin')", "$t('stockOps.col_supplier')", "$t('stockOps.col_delivery_ref')", "$t('stockOps.col_received_date')", "$t('stockControl.entered_by')", "t('stockOps.col_product')",
    "t('stockOps.col_expected')", "t('stockOps.line_total')", "$t('stockControl.own_entry_help')", "$t('stockControl.save_corrections')", "$t('stockControl.reject')", "$t('stockControl.validate')",
    "$t('stockControl.empty_incidents')", "t('stockOps.col_date')", "t('stockOps.col_kind')", "t('stockOps.col_quantity')", "t('stockOps.col_reason')", "$t('stockControl.reject_title')",
    "$t('stockOps.reject_reason')", "$t('stockOps.close')",
]);

test('toutes les clés stockControl.*, stockOps.* et stockAdminScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:stockControl|stockOps|stockAdminScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 25);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
    for (const locale of ['fr', 'en']) for (const tb of ['receipts', 'incidents']) assert.ok(pick(msgs[locale], `stockControl.tab_${tb}`), `${locale}.tab_${tb}`);
});

// --- Refonte (rouge tant que non refondu) ---
test('StockControlQueue : composants ui/, onglets accessibles, tableaux responsives, motif de rejet en panneau', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.match(t, /role="tablist"/);
    assert.equal((t.match(/role="tab"/g) || []).length, 1, 'un bouton généré par onglet (v-for)');
    assert.match(t, /:aria-selected="tab === tb"/);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 1);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
});

test('StockControlQueue : valider (plein) et rejeter (rouge) sont des boutons distincts, la sélection est annoncée', () => {
    const t = templateOf(view);
    assert.match(t, /variant="danger"/);
    assert.match(t, /aria-pressed|aria-current/);
});

test('StockControlQueue : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});

test('clés stockAdminScreens (contrôle) en FR et EN', () => {
    const keys = ['tabs_label', 'receipts_list_label'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].stockAdminScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.stockAdminScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.stockAdminScreens.${k}`);
        }
    }
});
