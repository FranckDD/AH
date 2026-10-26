import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labstock/LabStockAlerts.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : alertes du stock du labo (stocks bas, peremptions, rappel de comptage) ---
check('LabStockAlerts', view, [
    // chargement
    'LabStockGateway.getAlerts()', 'data.value = { low: r?.low || [], expiring: r?.expiring || [], count_status: r?.count_status || {} };',
    "pageError.value = describeLabStockError(e, t('stockOps.error_load'));", 'v-else-if="data"', 'onMounted(async () => {',
    // droits et liens
    "const canCount = computed(() => auth.hasRole(['laborantin', 'admin']));", 'v-if="canCount"', 'to="/dashboard/lab-stock-count"', 'to="/dashboard/lab-stock-requests"', 'v-if="data.low.length"',
    // rappel de comptage
    'const countDue = computed(() => !!data.value?.count_status?.reminder_due);',
    "if (st.days_since == null) return t('labStock.count_reminder_never');",
    "return st.reminder_due ? t('labStock.count_reminder', { days: st.days_since }) : t('labStock.alerts_count_ok', { days: st.days_since });",
    // stocks bas
    'v-for="p in data.low"', ':key="p.product_id"', 'p.name', 'p.packaging', 'p.request_status',
    "t('labStock.alerts_request_open', { status: label(requestStatusLabel(p.request_status)) })", "t('labStock.alerts_no_request')",
    "t('labStock.alerts_qty_threshold', { quantity: Number(p.quantity), threshold: Number(p.alert_threshold) })", 'Number(p.quantity) === 0',
    'const label = (l) => (l.key ? t(l.key) : l.raw);',
    // peremptions
    'v-for="e in sortedExpiring"', ':key="e.receipt_line_id"', "e.product_name || '?'", "t('labStock.alerts_lot', { lot: e.lot_number || '?' })", "t('labStock.alerts_expiry_on', { date: formatDate(e.expiry_date) })",
    '[...(data.value?.expiring || [])].sort((a, b) => a.days_left - b.days_left)', 'e.days_left < 0', 'daysText(e.days_left)',
    "const daysText = (d) => (d < 0 ? t('labStock.alerts_expired', { days: -d }) : d === 0 ? t('labStock.alerts_expires_today') : t('labStock.alerts_days_left', { days: d }));",
    "const [y, m, d] = String(v).slice(0, 10).split('-').map(Number);", 'return formatDateDMY(new Date(y, m - 1, d));',
    // clés
    "t('labStock.alerts_title')", "t('labStock.alerts_subtitle')", "t('labStock.alerts_count_title')", "t('labStock.alerts_go_count')", "t('labStock.alerts_low_title')", "t('labStock.alerts_low_empty')",
    "t('labStock.alerts_go_requests')", "t('labStock.alerts_expiring_title')", "t('labStock.alerts_expiring_empty')", "t('stockOps.loading')",
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
test('LabStockAlerts : composants ui/, en-tête de page, liens en boutons du thème, états en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'StatusBadge']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /buttonClasses/);
    const t = templateOf(view);
    assert.match(t, /<StatusBadge/);
    assert.match(t, /buttonClasses\('primary'/, 'aller compter = action principale');
    assert.match(t, /buttonClasses\('info'/, 'consulter les demandes = bleu ciel');
    assert.doesNotMatch(t, /bg-emerald|bg-green/);
});

test('LabStockAlerts : erreur annoncée, chargement annoncé, sections titrées et listes sémantiques', () => {
    const t = templateOf(view);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
    assert.equal((t.match(/<ul\b/g) || []).length, 2, 'stocks bas et peremptions');
    assert.match(t, /aria-labelledby/);
});

test('LabStockAlerts : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});
