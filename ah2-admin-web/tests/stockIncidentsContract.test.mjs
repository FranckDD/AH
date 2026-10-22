import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/stock/StockIncidents.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : déclaration et annulation d'avaries de stock ---
check('StockIncidents', view, [
    // chargement et filtre
    "const KINDS = ['endommage', 'perdu', 'defectueux'];", "const CHECK_STATUSES = ['a_controler', 'valide', 'rejete'];", 'v-model="statusFilter"', '@change="loadIncidents"', 'v-for="s in CHECK_STATUSES"',
    'StockOpsGateway.listIncidents({ status: statusFilter.value })', 'StockOpsGateway.listProducts()', 'onMounted(loadIncidents);',
    // tableau
    'inc.incident_date', 'inc.product_name', 'stockOps.kind.${inc.kind}', 'inc.quantity', 'inc.reason', 'badge(inc.status)', "inc.status === 'rejete' && inc.reject_reason", 'inc.reject_reason',
    "inc.status === 'a_controler'", '@click="cancelIncident(inc)"', ':disabled="busyId === inc.id"',
    'incidents.value = (await StockOpsGateway.listIncidents({ status: statusFilter.value })) || [];',
    // formulaire
    'v-if="showForm"', '@submit.prevent="submitIncident"', 'v-model.number="form.product_id"', 'v-for="p in products"', 'v-model="form.kind"', 'v-for="k in KINDS"', 'v-model.number="form.quantity"',
    'min="1"', 'step="1"', 'v-model="form.reason"', 'maxlength="2000"', 'v-model="form.incident_date"', '@click="showForm = false"', ':disabled="saving"',
    "const emptyForm = () => ({ product_id: null, kind: 'endommage', quantity: null, reason: '', incident_date: today() });", 'Object.assign(form, emptyForm());',
    "if (!form.product_id) { formError.value = t('stockOps.err_product_required'); return; }", "if (!Number.isInteger(form.quantity) || form.quantity <= 0) { formError.value = t('stockOps.err_quantity_positive'); return; }",
    "if (!form.reason.trim()) { formError.value = t('stockOps.err_reason_required'); return; }", "if (!form.incident_date) { formError.value = t('stockOps.err_date_required'); return; }",
    'product_id: form.product_id, kind: form.kind, quantity: form.quantity,', 'reason: form.reason.trim(), incident_date: form.incident_date,', 'await StockOpsGateway.createIncident({',
    "pageMessage.value = t('stockOps.incidents.created');",
    // annulation
    "if (!window.confirm(t('stockOps.confirm_cancel'))) return;", 'await StockOpsGateway.cancelIncident(inc.id);', "pageMessage.value = t('stockOps.cancelled');",
    // clés
    "$t('stockOps.incidents.title')", "$t('stockOps.all_statuses')", "$t('stockOps.incidents.new')", "$t('stockOps.incidents.empty')", "t('stockOps.col_date')", "t('stockOps.col_product')", "t('stockOps.col_kind')",
    "t('stockOps.col_quantity')", "t('stockOps.col_reason')", "t('stockOps.col_status')", "$t('stockOps.cancel')", "$t('stockOps.reject_reason')", "$t('stockOps.choose_product')",
    "$t('stockOps.close')", "$t('stockOps.saving')", "$t('stockOps.save')",
]);

test('toutes les clés stockOps.* et stockAdminScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:stockOps|stockAdminScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 15);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
    for (const locale of ['fr', 'en']) {
        for (const kd of ['endommage', 'perdu', 'defectueux']) assert.ok(pick(msgs[locale], `stockOps.kind.${kd}`), `${locale}.kind.${kd}`);
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('StockIncidents : composants ui/, tableau responsive à lignes alternées, statuts en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    assert.match(view, /<StatusBadge/);
});

test('StockIncidents : déclaration en panneau, messages annoncés, plus de surcouche en dur', () => {
    const t = templateOf(view);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 1);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
});

test('StockIncidents : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›]|\p{Extended_Pictographic}/u);
});

test('clé stockAdminScreens.incidents_count en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        const v = msgs[locale].stockAdminScreens?.incidents_count;
        assert.equal(typeof v, 'string', `${locale}.stockAdminScreens.incidents_count`);
        assert.doesNotMatch(v, /[—–…·]/);
    }
});
