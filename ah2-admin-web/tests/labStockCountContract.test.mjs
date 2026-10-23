import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labstock/LabStockCount.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : comptage hebdomadaire du stock du labo (saisie, validation, envoi, conflits) ---
check('LabStockCount', view, [
    // chargement et état
    'LabStockGateway.listProducts()', 'LabStockGateway.countStatus()', 'onMounted(load);', 'loadStatus();',
    "import { buildCountPayload, describeConflicts, isValidCount } from '@/utils/labCount';",
    "const blank = (v) => v === undefined || v === null || String(v).trim() === '';",
    'const invalid = (id) => !blank(entered[id]) && !isValidCount(entered[id]);',
    'const isConflict = (id) => conflicts.value.some((c) => c.product_id === id);',
    'const st = computed(() => status.value?.count_status ?? status.value ?? {});',
    'const reminderDue = computed(() => !!st.value.reminder_due);',
    'const daysSince = computed(() => st.value.days_since ?? null);',
    // recherche et compteurs
    'v-model="search"', "[p.name, p.packaging].some((v) => (v || '').toLowerCase().includes(q))",
    'const filledCount = computed(() => products.value.filter((p) => !blank(entered[p.id])).length);',
    'const hasInvalid = computed(() => products.value.some((p) => invalid(p.id)));',
    // saisie
    'v-model="entered[p.id]"', 'type="number"', 'min="0"', 'step="1"', 'inputmode="numeric"',
    // rappel et conflits
    'v-if="reminderDue"', "daysSince == null ? t('labStock.count_reminder_never') : t('labStock.count_reminder', { days: daysSince })",
    'v-if="conflicts.length"', "t('labStock.count_conflict_line', { name: c.name, expected: c.expected, actual: c.actual })", "t('labStock.count_conflicts_title')",
    // envoi
    '@click="submit"', ':disabled="busy || !filledCount || hasInvalid"', "busy ? t('labStock.submitting') : t('labStock.submit_count')",
    'v-if="hasInvalid"', "t('labStock.count_err_invalid')",
    'if (busy.value || hasInvalid.value) return;', 'const lines = buildCountPayload(products.value, entered);', 'if (!lines.length) return;',
    'const resp = await LabStockGateway.submitCount(lines);', 'conflicts.value = describeConflicts(resp);',
    'keepOnly(new Set(conflicts.value.map((c) => c.product_id)));', "flash(t('labStock.count_saved', { n: (resp?.applied || []).length }));",
    'err?.response?.status === 409 ? describeConflicts(err) : []',
    "pageError.value = describeLabStockError(err, t('stockOps.error_save'));",
    "for (const k of Object.keys(entered)) if (!ids.has(Number(k))) delete entered[k];",
    'try { await loadProducts(); } catch (err)',
    'setTimeout(() => { pageMessage.value = \'\'; }, 6000);', 'onBeforeUnmount(() => clearTimeout(msgTimer));',
    // clés
    "t('labStock.count_title')", "t('labStock.count_subtitle')", "t('labStock.count_last', { date: lastCountText })", "t('labStock.count_filled', { n: filledCount, total: products.length })",
    "t('labStock.no_products')", "t('labStock.col_product')", "t('labStock.col_packaging')", "t('labStock.last_stock')", "t('labStock.col_last_count')", "t('labStock.counted_qty')",
    "t('labStock.never')", "t('common.search_placeholder')",
]);

test('toutes les clés labStock.*, stockOps.*, common.* et labStockScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:labStock|stockOps|common|labStockScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 15);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabStockCount : composants ui/, un seul gabarit de saisie (tableau responsive), barre d actions', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.equal((t.match(/v-model="entered\[p\.id\]"/g) || []).length, 1, 'la saisie ne doit plus etre dupliquee');
    assert.doesNotMatch(t, /hidden lg:block|lg:hidden/);
});

test('LabStockCount : messages annoncés, champ invalide relié à son message, conflit en badge avec texte', () => {
    const t = templateOf(view);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
    assert.match(t, /aria-invalid/);
    assert.match(t, /<StatusBadge[^>]*count_conflict_badge/s);
    assert.match(t, /type="submit"|@click="submit"/);
    assert.doesNotMatch(t, /variant="success"/, 'envoyer un comptage est une action principale, pas une validation');
});

test('LabStockCount : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});

test('clés labStockScreens (comptage) en FR et EN', () => {
    const keys = ['count_conflict_badge', 'count_table', 'count_input_label'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labStockScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labStockScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labStockScreens.${k}`);
        }
    }
});
