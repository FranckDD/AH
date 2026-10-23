import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labstock/LabStockRequests.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : demandes « à commander » du stock du labo (commander, modifier la date, annuler) ---
check('LabStockRequests', view, [
    // droits et chargement
    "const canOrder = computed(() => authStore.hasRole(['promoteur', 'ToxicoManager', 'admin']));", "const STATUSES = ['a_commander', 'commande', 'recu', 'annule'];", "const statusFilter = ref('open');",
    'LabStockGateway.listRequests()', 'onMounted(load);', '<template v-if="isOpen(r)">', 'v-if="canOrder"',
    // filtre
    'v-model="statusFilter"', 'value="open"', 'value="all"', 'v-for="s in STATUSES"', 'labelOf(requestStatusLabel(s))',
    "if (f === 'all') return requests.value;", "if (f === 'open') return requests.value.filter(isOpen);", 'return requests.value.filter((r) => r.status === f);',
    "const isOpen = (r) => r.status === 'a_commander' || r.status === 'commande';", 'const isLow = (r) => num(r.quantity) <= num(r.alert_threshold);',
    // lignes
    'r.product_name', 'r.packaging', 'r.supplier', 'num(r.quantity)', 'num(r.alert_threshold)', 'isLow(r)', 'originText(r)', 'badge(r.status)', 'r.cancel_reason', 'formatDate(r.expected_date)',
    "const lv = r.level ? labelOf(levelLabel(r.level)) : '';", 'return lv ? `${base} (${lv})` : base;',
    // actions
    "r.status === 'a_commander'", "r.status === 'commande'", '@click="openOrder(r, false)"', '@click="openOrder(r, true)"', '@click="openCancel(r)"',
    // commander ou modifier la date
    'v-if="orderTarget"', '@submit.prevent="confirmOrder"', 'v-model="orderDate"', ':min="today"', 'required', '@click="orderTarget = null"', ':disabled="busy"', 'orderIsEdit ? t(\'labStock.edit_date\') : t(\'labStock.mark_ordered\')',
    "if (!orderDate.value) { modalError.value = t('labStock.err_date_required'); return; }", "if (orderDate.value < today) { modalError.value = t('labStock.err_date_past'); return; }",
    'await LabStockGateway.updateExpectedDate(orderTarget.value.id, orderDate.value);', 'await LabStockGateway.markOrdered(orderTarget.value.id, orderDate.value);', "flash(t('labStock.order_saved'));",
    "orderDate.value = isEdit && r.expected_date ? String(r.expected_date).slice(0, 10) : '';",
    // annuler avec motif
    'v-if="cancelTarget"', '@submit.prevent="confirmCancel"', 'v-model="cancelReason"', 'maxlength="2000"', '@click="cancelTarget = null"',
    "if (!reason) { modalError.value = t('labStock.err_reason_required'); return; }", 'await LabStockGateway.cancelRequest(cancelTarget.value.id, reason);', "flash(t('labStock.request_cancelled'));",
    'setTimeout(() => { pageMessage.value = \'\'; }, 5000);', 'onBeforeUnmount(() => clearTimeout(msgTimer));',
    // clés
    "t('labStock.requests_title')", "t('labStock.requests_subtitle')", "t('labStock.filter_open')", "t('labStock.filter_all')", "t('labStock.no_requests')", "t('labStock.col_product')", "t('labStock.col_stock')",
    "t('labStock.col_threshold')", "t('labStock.col_origin')", "t('labStock.col_status')", "t('labStock.col_expected')", "t('labStock.mark_ordered')", "t('labStock.edit_date')", "t('labStock.cancel_request')",
    "t('labStock.cancel_reason')", "t('stockOps.close')", "t('stockOps.save')",
]);

test('toutes les clés labStock.*, stockOps.* et labStockScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:labStock|stockOps|labStockScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 18);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabStockRequests : composants ui/, tableau responsive à lignes alternées, statuts en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    assert.match(view, /<StatusBadge/);
});

test('LabStockRequests : commande et annulation en panneau, messages annoncés, boutons par action (jamais de vert par défaut)', () => {
    const t = templateOf(view);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 2, 'commande et annulation');
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
    assert.match(t, /variant="danger"/);
    assert.match(t, /variant="info"/);
});

test('LabStockRequests : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});

test('clés labStockScreens (demandes) en FR et EN', () => {
    const keys = ['requests_count', 'status_filter'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labStockScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labStockScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labStockScreens.${k}`);
        }
    }
});
