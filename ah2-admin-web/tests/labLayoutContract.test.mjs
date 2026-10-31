import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labo/LabLayout.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : cadre du laboratoire (menu par rôle, zone des écrans enfants) ---
check('LabLayout', view, [
    // un onglet par route réelle, mêmes droits que meta.roles du routeur
    "const canSeeReception = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager', 'Assistant']));",
    "const canSeePaillasse = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager']));",
    "const canSeeHistory = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager']));",
    "const canSeeSyncFailures = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager']));",
    "const canConfigure = computed(() => authStore.hasRole(['admin', 'laborantin']));",
    "'lab-reception'", "'lab-technician'", "'lab-history'", "'lab-sync-failures'", "'lab-config'",
    // zone des écrans enfants
    '<router-view', '<component :is="Component" />', 'name="fade"',
    // clés
    "t('lab.title')", "t('lab.layout.subtitle')", "t('lab.nav.reception')", "t('lab.nav.bench')", "t('lab.nav.history')", "t('lab.nav.sync_failures')", "t('lab.nav.config_short')",
]);

test('toutes les clés lab.* et labScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 7);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabLayout : menu de navigation nommé, liens avec état courant annoncé, cibles de 44 px', () => {
    const t = templateOf(view);
    assert.match(t, /<nav[^>]*aria-label/);
    assert.match(t, /<router-link/);
    assert.match(t, /aria-current|active-class|exact-active-class/);
    assert.match(t, /min-h-11/);
    assert.doesNotMatch(t, /<button/, 'les onglets sont des liens, pas des boutons');
});

test('LabLayout : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view, /@apply/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
});

test('clés labScreens (cadre) en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        const v = msgs[locale].labScreens?.nav_label;
        assert.equal(typeof v, 'string', `${locale}.labScreens.nav_label`);
        assert.doesNotMatch(v, /[—–…·]/);
    }
});
