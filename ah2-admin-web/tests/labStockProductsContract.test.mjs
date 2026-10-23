import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labstock/LabStockProducts.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : produits du stock du labo (lecture pour tous, écriture et signalement selon le rôle) ---
check('LabStockProducts', view, [
    // droits
    "const canWrite = computed(() => authStore.hasRole(['laborantin', 'StockController', 'admin']));", "const canSignal = computed(() => authStore.hasRole(['laborantin', 'admin']));",
    'v-if="canWrite"', 'v-if="canSignal && p.is_active"', 'canSignal || canWrite', 'v-if="editingId"',
    // chargement, recherche, produits inactifs
    "LabStockGateway.listProducts({ includeInactive: canWrite.value && includeInactive.value })", 'onMounted(load);', 'v-model="search"', 'v-model="includeInactive"', '@change="load"',
    "[p.name, p.packaging, p.supplier].some((v) => (v || '').toLowerCase().includes(q))", 'if (!q) return products.value;',
    // lignes
    'p.name', 'p.packaging', 'p.supplier', 'num(p.quantity)', 'num(p.alert_threshold)', 'isLow(p)', '!p.is_active', "formatDate(p.last_counted_at) || t('labStock.never')",
    'const isLow = (p) => num(p.quantity) <= num(p.alert_threshold);', 'const num = (v) => Number(v ?? 0);',
    // signalement
    "const LEVELS = ['bientot_fini', 'fini'];", '@click="openSignal(p)"', 'v-if="signalTarget"', 'v-for="lv in LEVELS"', '@click="sendSignal(lv)"', 'labelOf(levelLabel(lv))', '@click="signalTarget = null"',
    'await LabStockGateway.signalProduct(signalTarget.value.id, level);', "flash(t('labStock.signal_sent'));", 'signalTarget.name',
    // création et modification
    '@click="openForm(null)"', '@click="openForm(p)"', 'v-if="formOpen"', '@submit.prevent="saveForm"', 'v-model="form.name"', 'maxlength="150"', 'v-model="form.packaging"', 'maxlength="100"',
    'v-model="form.supplier"', 'v-model.number="form.alert_threshold"', 'min="0"', 'max="1000000"', 'step="1"', 'v-model="form.is_active"', '@click="formOpen = false"', ':disabled="busy"',
    "const name = (f.name || '').trim();", "if (!name) { modalError.value = t('labStock.err_name_required'); return; }", 'if (!Number.isInteger(threshold) || threshold < 0) { modalError.value = t(\'labStock.err_threshold\'); return; }',
    'await LabStockGateway.updateProduct(editingId.value, {', "name, packaging: (f.packaging || '').trim() || null, supplier: (f.supplier || '').trim() || null,", 'alert_threshold: threshold, is_active: f.is_active,',
    'await LabStockGateway.createProduct({', "name, packaging: (f.packaging || '').trim(), supplier: (f.supplier || '').trim(), alert_threshold: threshold,", "flash(t('labStock.product_saved'));",
    'setTimeout(() => { pageMessage.value = \'\'; }, 5000);', 'onBeforeUnmount(() => clearTimeout(msgTimer));',
    // clés
    "t('labStock.products_title')", "t('labStock.products_subtitle')", "t('labStock.add_product')", "t('labStock.edit_product')", "t('common.search_placeholder')", "t('labStock.show_inactive')",
    "t('stockOps.loading')".replace("t('stockOps.loading')", "t('labStock.no_products')"), "t('labStock.col_product')", "t('labStock.col_packaging')", "t('labStock.col_supplier')", "t('labStock.col_stock')",
    "t('labStock.col_threshold')", "t('labStock.col_last_count')", "t('labStock.low')", "t('labStock.inactive')", "t('labStock.signal')", "t('common.edit')", "t('labStock.signal_title')",
    "t('stockOps.close')", "t('labStock.active')", "t('labStock.starts_at_zero')", "t('stockOps.save')",
]);

test('toutes les clés labStock.*, stockOps.*, common.* et labStockScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:labStock|stockOps|common|labStockScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
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
test('LabStockProducts : composants ui/, tableau responsive à lignes alternées, états en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    assert.match(view, /<StatusBadge/);
    assert.match(view, /align: 'right'/);
});

test('LabStockProducts : signalement et saisie en panneau, messages annoncés, boutons par action (jamais de vert par défaut)', () => {
    const t = templateOf(view);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 2, 'signalement et saisie');
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
    assert.match(t, /variant="danger"|'danger'/, 'Fini en rouge');
});

test('LabStockProducts : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});

test('clés labStockScreens (produits) en FR et EN', () => {
    const keys = ['products_count', 'search_label', 'signal_group'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labStockScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labStockScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labStockScreens.${k}`);
        }
    }
});
