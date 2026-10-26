// Defauts toxicologie releves par les guides (2026-10-26) : contrats de source et fonctions pures.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const read = (f) => readFileSync(new URL(`../src/${f}`, import.meta.url), 'utf8');
const msg = (loc, key) => key.split('.').reduce((o, k) => (o == null ? o : o[k]), i18n.global.getLocaleMessage(loc));
const bothLocales = (key) => { assert.ok(msg('fr', key), `fr ${key}`); assert.ok(msg('en', key), `en ${key}`); };

test('tableau de bord toxico : charge les statistiques (tuile Admissions du mois)', () => {
    assert.match(read('views/dashboards/ToxicoDashboard.vue'), /fetchDashboardStats\(\)/);
});

test('tuiles de suivi : chiffres globaux, independants de la recherche', () => {
    const store = read('stores/toxicoStore.js');
    assert.match(store, /globalStats/);
    assert.match(store, /listTotal/);
    const list = read('views/modules/toxico/ToxicoList.vue');
    assert.match(list, /toxicoStore\.activeTotal/);
    assert.match(list, /toxicoStore\.listTotal > 20/);
    assert.doesNotMatch(list, /:value="toxicoStore\.totalActive"/);
});

test('admission : champ sexe obligatoire pour un nouveau patient, envoye au serveur', () => {
    const modal = read('components/toxico/ToxicoAdmissionModal.vue');
    assert.match(modal, /v-model="form\.gender"/);
    assert.match(modal, /sex: ''|gender: ''/);
    assert.match(modal, /form\.gender/);
    assert.match(modal, /payload\.gender = form\.gender/);
    assert.match(read('services/ToxicoGateway.js'), /formData\.append\('gender'/);
    bothLocales('toxico.admission.sex');
    bothLocales('toxico.admission.sex_male');
    bothLocales('toxico.admission.sex_female');
});

test('admission : confirmation par un toast de succes', () => {
    const list = read('views/modules/toxico/ToxicoList.vue');
    assert.match(list, /useToastStore/);
    assert.match(list, /toast\.push\([\s\S]{0,200}'success'\)/);
    assert.doesNotMatch(list, /alert\("Admission valid/);
});

test('readmission : substance et tuteur repris du sejour precedent', async () => {
    const { readmissionPrefill } = await import('../src/utils/toxicoStays.js');
    const dossier = { substance: 'Cannabis', guardianName: 'Mme Z', guardianContact: '699', stays: [{ stay_number: 1, is_open: false, substance: 'Opioïdes' }] };
    assert.deepEqual(readmissionPrefill(dossier), { substance: 'Opioïdes', guardianName: 'Mme Z', guardianContact: '699' });
    assert.deepEqual(readmissionPrefill({ substance: 'Cannabis', stays: [] }), { substance: 'Cannabis', guardianName: '', guardianContact: '' });
    assert.deepEqual(readmissionPrefill(null), {});
    assert.match(read('components/toxico/ToxicoAdmissionModal.vue'), /readmissionPrefill\(/);
});

test('sortie : date de sortie choisissable (pas future, pas avant l admission)', async () => {
    const { validateDischarge } = await import('../src/utils/toxicoStays.js');
    const ok = { reason: 'guerison', note: '', date: '2026-10-20', minDate: '2026-10-01', today: '2026-10-26' };
    assert.deepEqual(validateDischarge(ok), []);
    assert.deepEqual(validateDischarge({ ...ok, date: '2026-10-27' }), ['toxico.stays.errors.date_future']);
    assert.deepEqual(validateDischarge({ ...ok, date: '2026-09-30' }), ['toxico.stays.errors.date_before_admission']);
    assert.deepEqual(validateDischarge({ reason: 'guerison' }), []);
    bothLocales('toxico.stays.errors.date_future');
    bothLocales('toxico.stays.errors.date_before_admission');
    bothLocales('toxico.stays.discharge_date');
    const modal = read('components/toxico/ToxicoDischargeModal.vue');
    assert.match(modal, /v-model="dischargeDate"/);
    assert.match(modal, /:max="today"/);
    assert.match(read('services/ToxicoGateway.js'), /discharge_date/);
});

test('suivi d un patient sorti : le statut de sortie est affiche', async () => {
    const { dischargeSummary } = await import('../src/utils/toxicoStays.js');
    const patient = { isActive: false, stays: [
        { stay_number: 1, is_open: false, discharge_date: '2026-08-01', discharge_reason: 'abandon' },
        { stay_number: 2, is_open: false, discharge_date: '2026-10-01', discharge_reason: 'guerison', discharge_note: 'ok', discharged_by_name: 'Dr X' }] };
    assert.deepEqual(dischargeSummary(patient), { date: '2026-10-01', reason: 'guerison', note: 'ok', by: 'Dr X' });
    assert.equal(dischargeSummary({ isActive: true, stays: [] }), null);
    const modal = read('components/toxico/ToxicoDossierModal.vue');
    assert.match(modal, /dischargeSummary\(/);
    bothLocales('toxico.stays.discharged_on');
});

test('menu : plus d entree Utilisateurs pour le responsable toxico (ecriture refusee par le serveur)', () => {
    const layout = read('components/layout/MainLayout.vue');
    const block = layout.slice(layout.indexOf("path: '/dashboard/users'"), layout.indexOf("path: '/dashboard/patients'"));
    assert.doesNotMatch(block, /TOXICO_MANAGER/);
    assert.match(block, /ROLES\.ADMIN/);
    const router = read('router/index.js');
    const route = router.slice(router.indexOf("path: 'users'"), router.indexOf('// 6. Gestion du Stock'));
    assert.doesNotMatch(route, /TOXICO_MANAGER/);
});

test('statuts de phase traduits, dates jj/mm/aaaa, pluriels', async () => {
    const { phaseStatusKey } = await import('../src/utils/toxicoStays.js');
    assert.equal(phaseStatusKey('En cours'), 'toxico.stays.phase_status.in_progress');
    assert.equal(phaseStatusKey('Terminé'), 'toxico.stays.phase_status.finished');
    assert.equal(phaseStatusKey('Interrompu'), 'toxico.stays.phase_status.interrupted');
    assert.equal(phaseStatusKey('Autre chose'), null);
    for (const k of ['in_progress', 'finished', 'interrupted']) bothLocales(`toxico.stays.phase_status.${k}`);
    const { formatDateDMY } = await import('../src/utils/localDate.js');
    assert.equal(formatDateDMY('2026-10-05'), '05/10/2026');
    assert.equal(formatDateDMY('2026-10-05T23:30:00'), '05/10/2026');
    assert.equal(formatDateDMY(''), '');
    assert.equal(formatDateDMY('pas une date'), 'pas une date');
    for (const f of ['components/toxico/ToxicoStaysTimeline.vue', 'components/toxico/ToxicoDischargedPanel.vue', 'components/toxico/ToxicoDossierModal.vue', 'components/toxico/ToxicoAdmissionModal.vue']) {
        assert.doesNotMatch(read(f), /toLocaleDateString\(\)/, f);
    }
    assert.match(read('components/toxico/ToxicoStaysTimeline.vue'), /phaseStatusKey\(/);
    // pluriels : « 1 patient » / « 2 patients »
    const t = (k, c) => i18n.global.t(k, c, { locale: 'en' });
    assert.equal(t('toxicoScreens.followed_count', 1), '1 patient followed');
    assert.equal(t('toxicoScreens.followed_count', 3), '3 patients followed');
    assert.equal(i18n.global.t('toxico.discharged.page_of', { page: 1, pages: 1, total: 1 }, { plural: 1, locale: 'en' }), 'Page 1 of 1 (1 patient)');
    assert.match(read('views/modules/toxico/ToxicoList.vue'), /followed_count', toxicoStore\.listTotal\)/);
});
