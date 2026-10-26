// Ecrans qui appellent le serveur : un echec de chargement (hors ligne, API injoignable) s'affiche comme tel
// avec un bouton Reessayer, jamais comme "0" ou "Aucun ..." (defaut transverse, guides 2026-10-26).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { isLoadFailure } from '../src/utils/loadFailure.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');

test('isLoadFailure : pas de reponse ou 5xx = echec de chargement, un refus 4xx non', () => {
    assert.equal(isLoadFailure({ message: 'Network Error' }), true);
    assert.equal(isLoadFailure({ response: { status: 503 } }), true);
    assert.equal(isLoadFailure({ response: { status: 403 } }), false);
    assert.equal(isLoadFailure({ response: { status: 404 } }), false);
    assert.equal(isLoadFailure(null), false);
});

test('le composant partage existe, est reexporte et n utilise que des jetons', () => {
    assert.match(read('components/ui/index.js'), /LoadErrorState/);
    const c = read('components/ui/LoadErrorState.vue');
    assert.match(c, /loadError\.offline/);
    assert.match(c, /loadError\.retry/);
    assert.match(c, /emit|\$emit\('retry'\)/);
    assert.doesNotMatch(c, /#[0-9a-fA-F]{6}\b|(?:red|green|gray|blue|yellow)-\d{2,3}\b/);
});

test('les textes de l etat d erreur existent en FR et EN', () => {
    const m = i18n.global.messages.value;
    for (const loc of ['fr', 'en']) for (const k of ['offline', 'server', 'retry', 'unavailable']) {
        assert.equal(typeof m[loc].loadError[k], 'string', `${loc}.loadError.${k}`);
    }
});

const SCREENS = [
    ['views/dashboards/DashboardOverview.vue', /LoadErrorState/],
    ['views/modules/patients/PatientList.vue', /LoadErrorState/],
    ['views/modules/toxico/ToxicoList.vue', /LoadErrorState/],
    ['views/dashboards/ToxicoDashboard.vue', /LoadErrorState/],
    ['views/modules/stock/StockList.vue', /LoadErrorState/],
    ['views/modules/labo/MedicalLabResults.vue', /LoadErrorState/],
    ['views/modules/labo/LabHistory.vue', /LoadErrorState/],
    ['views/dashboards/LabDashboard.vue', /LoadErrorState/],
    ['views/modules/doctors/DoctorKpiView.vue', /LoadErrorState/],
];
for (const [file, re] of SCREENS) {
    test(`${file} affiche l etat d erreur partage`, () => assert.match(read(file), re));
}

test('les stores exposent un indicateur d echec au lieu de zeros', () => {
    assert.match(read('stores/toxicoStore.js'), /listLoadFailed[\s\S]*statsLoadFailed|statsLoadFailed[\s\S]*listLoadFailed/);
    assert.match(read('stores/stockStore.js'), /loadFailed/);
    assert.match(read('stores/labStore.js'), /statsFailed[\s\S]*historyFailed/);
    assert.match(read('stores/doctorKpiStore.js'), /pendingFailed/);
    assert.match(read('stores/patientStore.js'), /countsFailed/);
    assert.match(read('stores/dashboardStore.js'), /indisponibles\.value = \[/);
});

test('compteurs d onglets : un tiret quand le chargement a echoue', () => {
    assert.match(read('views/modules/stock/StockControlQueue.vue'), /loadFailed \? '-'/);
});
