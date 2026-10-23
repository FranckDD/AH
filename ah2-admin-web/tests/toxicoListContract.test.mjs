import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/toxico/ToxicoList.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : liste des patients toxicologie (actifs / sortis, recherche, actions par rôle, fenêtres) ---
check('ToxicoList', view, [
    // droits (reflètent les routes serveur : voir aussi toxicoExport.test.mjs)
    "return authStore.hasRole(['admin', 'ToxicoManager', 'Assistant']);", "return authStore.hasRole(['Psychologist']);", 'return authStore.hasRole(TOXICO_DISCHARGE_ROLES);',
    'v-if="canAdmitPatient"', 'v-if="canEvaluatePatient"', 'v-if="canDischargePatient"',
    // chargement et recherche
    'toxicoStore.fetchToxicoPatients();', 'toxicoStore.fetchDashboardStats();', 'toxicoStore.fetchPsychologists();', ':value="toxicoStore.filters.search"', '@input="handleSearch"',
    'toxicoStore.setSearch(event.target.value);', '}, 500);', "v-if=\"activeTab === 'active'\"",
    // onglets actifs / sortis
    "{ id: 'active', label: 'toxico.discharged.tab_active' }", "{ id: 'discharged', label: 'toxico.discharged.tab_discharged' }", 'role="tablist"', 'role="tab"', ':aria-selected="activeTab === tab.id"', '@click="activeTab = tab.id"',
    "v-if=\"activeTab === 'discharged'\"", ':canReadmit="canAdmitPatient"', '@view="openDossier"', '@readmit="openReadmission"',
    // KPI
    'toxicoStore.totalActive', 'toxicoStore.currentMonthAdmissions', 'toxicoStore.relapseRate', 'toxicoStore.statsByPhase[1] || 0', 'newPatientsThisWeek',
    // lignes
    'toxicoStore.patients', 'row-key="patient_id"', 'p.patientName', 'p.code', 'p.substance', 'p.currentPhase', 'p.relapseCount > 0', 'p.psychologist',
    // actions
    '@click="openPatientDetails(p)"', '@click="openDossier(p)"', '@click="openEvaluation(p)"', '@click="confirmDischarge(p)"', '@click="openNewAdmission"',
    // pagination
    'v-if="toxicoStore.totalActive > 20"', ':disabled="toxicoStore.filters.page === 1"', '@click="toxicoStore.setPage(toxicoStore.filters.page - 1)"', '@click="toxicoStore.setPage(toxicoStore.filters.page + 1)"',
    // fenêtres
    '<ToxicoDossierModal', 'v-if="showDossierModal"', ':patientId="selectedPatientId"', '@close="closeDossierModal"', '@discharged="onDischargedFromDossier"',
    '<ToxicoEvaluationModal', 'v-if="showEvalModal"', ':patient="selectedPatientForEval"', '@close="closeEvalModal"', '@save="handleSaveEvaluation"',
    '<ToxicoAdmissionModal', 'v-if="showAdmissionModal"', ':preselectedPatient="readmitPatient"', '@close="closeAdmission"', '@save="handleAdmission"',
    '<ToxicoPatientDetailsModal', 'v-if="showPatientDetailsModal"', ':patient="selectedPatientForDetails"', '@close="closePatientDetailsModal"', '@open-dossier="openDossierFromDetails"',
    '<ToxicoDischargeModal', 'v-if="showDischargeConfirm && patientToDischarge"', ':dossierId="Number(patientToDischarge.dossier_id || patientToDischarge.id)"',
    ":patientName=\"patientToDischarge.patientName || ''\"", '@close="closeDischarge"', '@discharged="onDischarged"',
    // logique de la page
    'if (!canEvaluatePatient.value) return;', 'patient.dossier_id = patient.id;', "activeTab.value = 'active';", 'toxicoStore.setDischargedPage(1);',
    'await toxicoStore.submitEvaluation(evalData);', 'const detailedPatient = await toxicoStore.getPatientDetails(patientId);', 'readmitPatient.value = toPreselectedPatient(row);',
    "alert(t('toxico.stays.discharge_success'));", 'alert("Impossible de charger les détails.");',
    // clés
    "t('toxico.title')", "t('toxico.new_admission')", "t('toxico.table.patient')", "t('toxico.table.phase')", "t('toxico.table.psy')",
    "t(`toxico.phases.${p.currentPhase}`)", "t('toxico.actions.evaluate')", "t('toxico.stays.discharge_action')", "t(tab.label)", "t('toxico.discharged.tabs_label')",
]);

test('toutes les clés toxico.*, common.* et toxicoScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:toxico|toxicoScreens|common)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    for (const p of [1, 2, 3, 4]) used.add(`toxico.phases.${p}`);
    assert.ok(used.size >= 12);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ToxicoList : composants ui/, en-tête, tuiles colorées, tableau responsive à lignes alternées', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'StatTile', 'ResponsiveTable', 'StatusBadge', 'AppButton', 'FormField']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.equal((t.match(/<StatTile/g) || []).length, 4);
    for (const tone of ['info', 'danger', 'warning', 'success']) assert.match(t, new RegExp(`tone="${tone}"`), tone);
    assert.doesNotMatch(t, /<table/);
});

test('ToxicoList : mêmes teintes de phase qu avant, via les jetons, la phase toujours écrite', () => {
    assert.match(view, /phaseMeta\(p\.currentPhase\)/);
    assert.match(view, /import \{[^}]*phaseMeta[^}]*\} from '@\/utils\/toxicoUi'/);
    const t = templateOf(view);
    assert.match(t, /role="progressbar"/);
    assert.doesNotMatch(t, /animate-pulse/);
    assert.doesNotMatch(t, /[⚠]|\p{Extended_Pictographic}/u);
});

test('ToxicoList : « Évaluer » en indigo (primaire), « Dossier » bleu ciel, « Sortie » rouge, « Détails » contour, boutons compacts avec texte', () => {
    const t = templateOf(view);
    assert.match(t, /<AppButton[^>]*variant="secondary"[^>]*@click="openPatientDetails\(p\)"/s);
    assert.match(t, /<AppButton[^>]*variant="info"[^>]*@click="openDossier\(p\)"/s);
    assert.match(t, /<AppButton[^>]*size="sm"[^>]*@click="openEvaluation\(p\)"/s);
    assert.doesNotMatch(t, /<AppButton[^>]*variant="[a-z]+"[^>]*@click="openEvaluation\(p\)"/s, 'Évaluer garde la variante par défaut (indigo)');
    assert.match(t, /<AppButton[^>]*variant="danger"[^>]*@click="confirmDischarge\(p\)"/s);
});

test('ToxicoList : le calcul « cette semaine » vient de l utilitaire partagé', () => {
    assert.match(view, /newThisWeek\(toxicoStore\.patients\)/);
    assert.match(view, /import \{[^}]*newThisWeek[^}]*\} from '@\/utils\/toxicoUi'/);
});

test('ToxicoList : recherche étiquetée, pagination nommée, états de chargement et vide annoncés', () => {
    const t = templateOf(view);
    assert.match(t, /<FormField/);
    assert.match(t, /<nav\b[\s\S]*?:aria-label/);
    assert.match(t, /:loading="toxicoStore\.isLoading"/);
});

test('ToxicoList : plus aucun texte français en dur dans le gabarit', () => {
    const t = templateOf(view).replace(/\{\{[^}]*\}\}/g, '').replace(/<!--.*?-->/gs, '');
    for (const bad of ['Patients Actifs', 'Admissions (Mois)', 'Taux de Rechute', 'En Sevrage', 'Surveillance accrue', 'Aucun patient trouvé', 'Précédent', 'Suivant', 'Rechutes', 'Détails', 'Dossier<']) {
        assert.ok(!t.includes(bad), `texte en dur : ${bad}`);
    }
});

test('ToxicoList : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
});

test('clés toxicoScreens (liste) en FR et EN', () => {
    const keys = ['followed_count', 'search_label', 'week_note', 'admissions_month', 'admissions_month_note', 'relapse_title', 'withdrawal_title', 'withdrawal_note', 'col_relapses',
        'no_patients', 'details', 'dossier', 'details_title', 'prev', 'next', 'pagination_label', 'relapses_count', 'phase_bar', 'active_patients_title'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].toxicoScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.toxicoScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.toxicoScreens.${k}`);
        }
    }
});
