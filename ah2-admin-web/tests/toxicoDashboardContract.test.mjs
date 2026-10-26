import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/dashboards/ToxicoDashboard.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : tableau de bord toxicologie (KPI, répartition par phase et substance, charge des psychologues, alertes) ---
check('ToxicoDashboard', view, [
    // chargement
    'toxicoStore.fetchToxicoPatients();', 'onMounted(() => {',
    // KPI
    'toxicoStore.totalActive', 'toxicoStore.relapseRate', 'toxicoStore.statsByPhase[1] || 0', 'toxicoStore.currentMonthAdmissions',
    // répartition par phase
    'v-for="phase in [1, 2, 3, 4]"', 'toxicoStore.statsByPhase[phase] || 0', "t(`toxico.phases.${phase}`)",
    // substances, psychologues
    'v-for="(count, substance) in toxicoStore.statsBySubstance"', 'toxicoStore.statsByPsy', 'row-key="name"', 'psy.name', 'psy.count',
    // alertes
    'toxicoStore.generatedAlerts', 'v-for="alert in toxicoStore.generatedAlerts"', ':key="alert.id"', "alert.type === 'critical'", 'alert.title', 'alert.message',
    // clés
    "t('toxico.dashboard.title')", "t('toxico.dashboard.subtitle')", "t('toxico.dashboard.active_patients')", "t('toxico.dashboard.relapse_rate')", "t('toxico.dashboard.new_this_month')",
    "t('toxico.dashboard.phase_dist')", "t('toxico.dashboard.substance_dist')", "t('toxico.dashboard.psy_workload')", "t('toxico.dashboard.alerts')",
]);

test('toutes les clés toxico.*, common.* et toxicoScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:toxico|toxicoScreens|common)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    for (const p of [1, 2, 3, 4]) used.add(`toxico.phases.${p}`);
    assert.ok(used.size >= 10);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ToxicoDashboard : composants ui/, quatre tuiles colorées, cartes, tableau des psychologues responsive', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'StatTile', 'AppCard', 'ResponsiveTable']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.equal((t.match(/<StatTile/g) || []).length, 4);
    // mêmes couleurs qu'avant : bleu (actifs), rouge (rechute), orange (sevrage), vert (nouveaux)
    for (const tone of ['info', 'danger', 'warning', 'success']) assert.match(t, new RegExp(`tone="${tone}"`), tone);
    assert.doesNotMatch(t, /<table/);
});

test('ToxicoDashboard : le « +N cette semaine » est le calcul réel, plus de valeur ni de statut inventés', () => {
    assert.match(view, /toxicoStore\.newThisWeekCount/); // chiffre global du serveur, repli sur la liste chargee
    assert.doesNotMatch(view, /\+2 cette semaine/);
    assert.doesNotMatch(view, /Service Op[ée]rationnel/);
    assert.doesNotMatch(templateOf(view), /animate-pulse/);
});

test('ToxicoDashboard : phases colorées par les jetons, valeur écrite, barres nommées', () => {
    assert.match(view, /phaseMeta\(phase\)\.bar/);
    assert.match(view, /percentOf\(toxicoStore\.statsByPhase\[phase\], toxicoStore\.totalActive\)/);
    const t = templateOf(view);
    assert.match(t, /role="progressbar"/);
    assert.match(t, /bg-action-/, 'substances et compteur du psychologue gardent l indigo');
});

test('ToxicoDashboard : alertes annoncées, critique rouge et à surveiller orange, avec icône et texte', () => {
    const t = templateOf(view);
    assert.match(t, /role="status"|role="alert"/);
    assert.match(t, /toneClasses\(alert\.type === 'critical' \? 'danger' : 'warning'\)/);
    assert.match(t, /ExclamationCircleIcon/);
    assert.match(t, /ClockIcon/);
});

test('ToxicoDashboard : plus aucun texte français en dur dans le gabarit', () => {
    const t = templateOf(view).replace(/\{\{[^}]*\}\}/g, '').replace(/<!--.*?-->/gs, '');
    for (const bad of ['En Sevrage', 'Nécessitent', 'Psychologue', 'Patients suivis', 'Aucune alerte', ' patients<']) assert.ok(!t.includes(bad), `texte en dur : ${bad}`);
});

test('ToxicoDashboard : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
});

test('clés toxicoScreens (tableau de bord) en FR et EN', () => {
    const keys = ['week_note', 'withdrawal_title', 'withdrawal_note', 'patients_count', 'col_psychologist', 'col_followed', 'no_alerts', 'phase_bar'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].toxicoScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.toxicoScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.toxicoScreens.${k}`);
        }
    }
});
