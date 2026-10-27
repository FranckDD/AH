import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const list = read('../src/views/modules/toxico/ToxicoList.vue');
const dash = read('../src/views/dashboards/ToxicoDashboard.vue');
const modal = read('../src/components/toxico/ToxicoDossierModal.vue');
const panel = read('../src/components/toxico/ToxicoPreviousPanel.vue');
const store = read('../src/stores/toxicoStore.js');
const gateway = read('../src/services/ToxicoGateway.js');
const admission = read('../src/components/toxico/ToxicoAdmissionModal.vue');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : ${needle}`, () => assert.ok(src.includes(needle), `${needle} absent de ${name}`));
    }
}

check('ToxicoList', list, [
    'p.canEvaluate', "{ id: 'previous', label: 'toxico.previous.tab' }", 'authStore.user?.sees_own_toxico_only',
    '<ToxicoPreviousPanel', 'route.query.patient', 'authStore.fetchMe()',
]);
check('ToxicoDashboard', dash, ['v-if="!toxicoStore.isScoped"']);
test('ToxicoDashboard : la carte psy_workload porte le garde isScoped', () => {
    assert.match(dash, /<AppCard v-if="!toxicoStore\.isScoped" :title="t\('toxico\.dashboard\.psy_workload'\)"/);
});
check('ToxicoDossierModal', modal, [
    "patient.accessMode === 'readonly'", 'toxico.transfer.readonly_banner', 'canDischarge', 'canExportDossier',
]);
test('ToxicoDossierModal : lecture seule masque sortie, export et onglets medical/prescriptions', () => {
    assert.match(modal, /const isReadOnly = computed\(\(\) => patient\.value\?\.accessMode === 'readonly'\)/);
    assert.match(modal, /!isReadOnly\.value && !!patient\.value\?\.isActive/);
    assert.match(modal, /!isReadOnly\.value && authStore\.hasRole\(TOXICO_DOSSIER_EXPORT_ROLES\)/);
    assert.match(modal, /hasRole\(\['admin', 'ToxicoManager', 'Psychologist'\]\) && !isReadOnly\.value/);
});
check('ToxicoPreviousPanel', panel, [
    'fetchPrevious', 'setPreviousPage', 'LoadErrorState', 'ResponsiveTable', 'StatusBadge', "emit('view'", 'toxico.previous.empty',
    'toxico.previous.current_psy', 'previousPage <= 1',
]);
test('ToxicoPreviousPanel : pas de bouton clinique (evaluer, sortir, readmettre)', () => {
    assert.doesNotMatch(panel, /evaluate|discharge_action|readmit/);
});
check('toxicoStore', store, ['previous', 'previousTotal', 'previousLoading', 'previousError', 'previousPage', 'fetchPrevious', 'setPreviousPage', 'globalStats.value?.scoped === true', 'isScoped']);
check('ToxicoGateway', gateway, ['listPrevious', "'/toxico/dossiers/previous'"]);
check('ToxicoAdmissionModal', admission, ['prefill.psychologist']);

test('cles toxico.previous.* et toxico.transfer.readonly_banner en FR et EN', () => {
    const keys = ['toxico.previous.tab', 'toxico.previous.empty', 'toxico.previous.current_psy', 'toxico.transfer.readonly_banner'];
    for (const locale of ['fr', 'en']) for (const k of keys) {
        const v = pick(msgs[locale], k);
        assert.equal(typeof v, 'string', `${locale}.${k}`);
        assert.doesNotMatch(v, /[—–…·→]/, `${locale}.${k}`);
    }
});
test('toutes les cles citees par le panneau existent en FR et EN', () => {
    const used = new Set();
    for (const m of panel.matchAll(/['"`(]((?:toxico|toxicoScreens|common|ui)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 4);
    for (const locale of ['fr', 'en']) for (const k of used) assert.equal(typeof pick(msgs[locale], k), 'string', `${locale}.${k}`);
});
test('panneau : jetons du theme, texte >= 13 px', () => {
    assert.doesNotMatch(panel, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(panel, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
});
