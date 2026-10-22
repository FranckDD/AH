import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/tech/SystemLogs.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : les deux journaux, leurs colonnes, leur filtre de date et leur pagination ---
check('SystemLogs', view, [
    // chargement et bascule d'onglet
    "const currentTab = ref('ACCESS');", 'auditStore.fetchAccessLogs();', 'auditStore.fetchActionLogs();',
    "if (newTab === 'ACCESS' && auditStore.accessLogs.length === 0) {", "} else if (newTab === 'ACTIONS' && auditStore.actionLogs.length === 0) {",
    "currentTab = 'ACCESS'", "currentTab = 'ACTIONS'", "currentTab === 'ACCESS'",
    // filtre de date par onglet
    "currentTab === 'ACCESS' ? auditStore.accessFilters.dateFrom : auditStore.actionFilters.dateFrom", "handleDateChange($event.target.value, 'dateFrom')",
    'auditStore.setAccessFilters(filters);', 'auditStore.setActionFilters(filters);', "const filters = { [filterKey]: value };",
    // pagination par onglet
    'auditStore.accessPagination', 'auditStore.actionPagination', 'auditStore.setAccessPage(', 'auditStore.setActionPage(', 'auditStore.isLoading',
    // lignes d'accès
    'auditStore.accessLogs', 'formatDate(log.timestamp)', "log.user_name || 'N/A'", 'log.action_type', 'log.ip_address', 'log.details',
    // lignes d'actions
    'auditStore.actionLogs', 'formatDate(act.timestamp)', "act.user_name || act.username || 'N/A'", 'act.resource_type', 'act.action_performed',
    'act.new_values?.details || act.details',
    // badges
    "case 'LOGIN':", "case 'LOGOUT':", "case 'LOGIN_FAILED':", "case 'CREATE':", "case 'UPDATE':", "case 'DELETE':", 'getAccessBadge(log.action_type)', 'getActionBadge(act.action_performed)',
    "if (!timestamp) return 'N/A';",
    // clés
    "t('tech.title')", "t('tech.subtitle')", "t('tech.tabs.access')", "t('tech.tabs.actions')", "t('tech.table.date')", "t('tech.table.user')", "t('tech.table.action')",
    "t('tech.table.ip')", "t('tech.table.details')", "t('tech.table.resource')",
]);

test('toutes les clés tech.*, common.* et techScreens.* citées existent en FR et EN (hors filtre de date historique)', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:tech|common|techScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    used.delete('tech.filter.date_from'); // clé citée avant la refonte mais jamais définie (placeholder d'un champ date, sans effet)
    assert.ok(used.size >= 10);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('SystemLogs : composants ui/, deux tableaux responsives à lignes alternées, badges avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FormField', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.equal((templateOf(view).match(/<ResponsiveTable/g) || []).length, 2, 'un tableau par onglet');
    assert.equal((templateOf(view).match(/\n\s+striped\s*\n/g) || []).length, 2);
    assert.match(view, /<StatusBadge/);
});

test('SystemLogs : onglets accessibles (tablist, tab, aria-selected, tabpanel) et plus de composant Pagination hérité', () => {
    const t = templateOf(view);
    assert.match(t, /role="tablist"/);
    assert.equal((t.match(/role="tab"/g) || []).length, 2);
    assert.match(t, /:aria-selected="currentTab === 'ACCESS'"/);
    assert.match(t, /role="tabpanel"/);
    assert.doesNotMatch(view, /common\/Pagination\.vue/);
});

test('SystemLogs : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·]|\p{Extended_Pictographic}/u);
});

test('les dates des journaux suivent la langue choisie (FR ou EN)', () => {
    assert.match(view, /locale\.value === 'en' \? 'en-GB' : 'fr-FR'/);
});

test('clés techScreens.* en FR et EN', () => {
    const keys = ['date_from', 'tabs_label', 'page_label', 'prev_page', 'next_page', 'empty'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].techScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.techScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.techScreens.${k}`);
        }
    }
});
