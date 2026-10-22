import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/stock/AdjustmentRequestsAdmin.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : demandes d'ajustement de stock (secrétaire vers admin) ---
check('AdjustmentRequestsAdmin', view, [
    // chargement et filtre
    "const STATUSES = ['en_attente', 'approuve', 'refuse', 'annule'];", "const statusFilter = ref('en_attente');", 'v-model="statusFilter"', '@change="load"', 'v-for="s in STATUSES"',
    'StockOpsGateway.listAdjustmentRequests({ status: statusFilter.value })', 'onMounted(load);',
    // lignes
    'formatDateTime(r.requested_at)', 'r.product_name', "r.kind === 'correction' && r.stock_at_request !== null && r.stock_at_request !== undefined", 'r.stock_at_request', 'r.current_quantity',
    "r.status === 'en_attente' && r.current_quantity !== null && r.current_quantity !== undefined", 'stockAdjust.kind.${r.kind}', "r.kind === 'reapprovisionnement' ? '+' : '= '", 'r.quantity', 'r.reason',
    'actorLabel(r.requested_by_name, r.requested_by)', 'badge(r.status)', 'r.decision_note', 'r.stock_before !== null && r.stock_before !== undefined', 'r.stock_before', 'r.stock_after', 'rowErrors[r.id]',
    "r.status === 'en_attente'",
    // approuver
    '@click="approve(r)"', ':disabled="busyId === r.id"', "if (!window.confirm(t('stockAdjust.confirm_approve'))) return;", 'await StockOpsGateway.approveAdjustmentRequest(r.id);',
    "pageMessage.value = t('stockAdjust.approved');", 'rowErrors.value = { ...rowErrors.value, [r.id]: describeStockError(err, t(\'stockOps.error_save\')) };',
    // refuser avec motif obligatoire
    '@click="openRefuse(r)"', 'v-if="refuseTarget"', '@submit.prevent="confirmRefuse"', 'v-model="refuseNote"', 'maxlength="2000"', '@click="refuseTarget = null"', ':disabled="busyId !== null"',
    "if (!note) { refuseError.value = t('stockAdjust.err_note_required'); return; }", 'await StockOpsGateway.rejectAdjustmentRequest(refuseTarget.value.id, note);', "pageMessage.value = t('stockAdjust.refused');",
    'refuseTarget.product_name', 'refuseTarget.kind', 'refuseTarget.quantity',
    // clés
    "$t('stockAdjust.admin_title')", "$t('stockOps.all_statuses')", "$t('stockAdjust.no_requests')", "t('stockOps.col_date')", "t('stockOps.col_product')", "t('stockAdjust.col_kind')",
    "t('stockOps.col_quantity')", "t('stockOps.col_reason')", "t('stockAdjust.requester')", "t('stockOps.col_status')", "$t('stockAdjust.correction_detail', { n: r.quantity, m: r.stock_at_request, k: r.current_quantity ??",
    "$t('stockAdjust.current_stock_n', { n: r.current_quantity })", "$t('stockAdjust.decision_note')", "$t('stockAdjust.col_stock_change')", "$t('stockAdjust.approve')", "$t('stockAdjust.refuse')",
    "$t('stockAdjust.refuse_title')", "$t('stockOps.close')",
]);

test('toutes les clés stockAdjust.*, stockOps.* et stockAdminScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:stockAdjust|stockOps|stockAdminScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 15);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
    for (const locale of ['fr', 'en']) for (const s of ['en_attente', 'approuve', 'refuse', 'annule']) assert.ok(pick(msgs[locale], `stockAdjust.status.${s}`), `${locale}.status.${s}`);
});

// --- Refonte (rouge tant que non refondu) ---
test('AdjustmentRequestsAdmin : composants ui/, tableau responsive à lignes alternées, statuts en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    assert.match(view, /<StatusBadge/);
});

test('AdjustmentRequestsAdmin : refus en panneau, messages annoncés, Approuver plein et Refuser rouge', () => {
    const t = templateOf(view);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 1);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
    assert.match(t, /variant="danger"/);
});

test('AdjustmentRequestsAdmin : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});

test('clés stockAdminScreens (ajustements) en FR et EN', () => {
    const keys = ['requests_count', 'stock_to'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].stockAdminScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.stockAdminScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.stockAdminScreens.${k}`);
        }
    }
});
