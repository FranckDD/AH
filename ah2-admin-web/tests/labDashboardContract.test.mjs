import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/dashboards/LabDashboard.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : tableau de bord du laboratoire (période, tuiles cliquables, entrées récentes, examens les plus demandés) ---
check('LabDashboard', view, [
    // chargement et rafraîchissement
    "const currentPeriod = ref('month');", 'await labStore.fetchDashboardStats(currentPeriod.value);', 'refreshInterval = setInterval(loadData, 300000);',
    'clearInterval(refreshInterval);', 'onMounted(() => {', 'onUnmounted(() => {',
    'return labStore.stats || {', 'recent_pending: [],', 'top_exams: {},', 'max_exam_count: 1',
    // période
    "v-for=\"p in ['day', 'month', 'year']\"", '@click="changePeriod(p)"', 'currentPeriod.value = period;', "t(`lab.dashboard.period_${p}`)",
    // tuiles
    "stats?.pending ?? 0", "stats?.completed_today ?? 0", "stats?.critical ?? 0", "stats?.total_month ?? 0",
    "'lab-technician'", "'lab-history'", "abnormal: '1', period: currentPeriod",
    // entrées récentes
    'item.patient_name', 'item.code_patient', 'recent_passages', 'recent_pending', '@click="goToTechnician(item)"',
    "router.push({ name: 'lab-technician', query: { open: String(item.id) } });", 'if (item?.id) {',
    // examens les plus demandés
    'v-for="(count, name) in stats.top_exams"', '(count / (stats.max_exam_count || 1) * 100)', 'Object.keys(stats.top_exams).length === 0',
    // clés
    "t('lab.dashboard.title')", "t('lab.dashboard.subtitle')", "t('lab.dashboard.pending')", "t('lab.dashboard.pending_hint')", "t('lab.dashboard.completed')", "t('lab.dashboard.completed_hint')",
    "t('lab.dashboard.critical')", "t('lab.dashboard.critical_hint')", "t('lab.dashboard.total')", "t('lab.dashboard.total_hint')", "t('lab.dashboard.recent')", "t('lab.dashboard.see_bench')",
    "t('lab.dashboard.col_patient')", "t('lab.dashboard.col_exam')", "t('lab.dashboard.col_action')", "t('lab.dashboard.no_pending')", "t('lab.dashboard.unknown_patient')", "t('lab.dashboard.enter')",
    "t('lab.dashboard.top_exams')", "t('lab.dashboard.no_data')",
]);

test('toutes les clés lab.* et labScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 18);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
    for (const p of ['day', 'month', 'year']) for (const locale of ['fr', 'en']) assert.ok(pick(msgs[locale], `lab.dashboard.period_${p}`), `${locale} period_${p}`);
});

// --- Refonte (rouge tant que non refondu) ---
test('LabDashboard : composants ui/, tuiles de statistique, entrées récentes en tableau responsive', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'StatTile', 'ResponsiveTable', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    assert.equal((templateOf(view).match(/<StatTile/g) || []).length, 4);
});

test('LabDashboard : tuiles cliquables en vrais liens, période en groupe de boutons nommé avec état', () => {
    const t = templateOf(view);
    assert.match(t, /<router-link/);
    assert.match(t, /role="group"/);
    assert.match(t, /aria-pressed/);
    assert.doesNotMatch(t, /\$router\.push/);
    assert.doesNotMatch(t, /@click="\$router/);
});

test('LabDashboard : barres décoratives avec chiffre écrit, pathologiques signalés par le titre et la note', () => {
    const t = templateOf(view);
    assert.match(t, /aria-hidden="true"/);
    assert.match(t, /bg-brand-/);
    assert.match(t, /<StatTile[^>]*lab\.dashboard\.critical/s);
});

test('LabDashboard : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view, /@apply|<style/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→]|&rarr;|\p{Extended_Pictographic}/u);
});

test('clés labScreens (tableau de bord) en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        const v = msgs[locale].labScreens?.period_label;
        assert.equal(typeof v, 'string', `${locale}.labScreens.period_label`);
        assert.doesNotMatch(v, /[—–…·]/);
    }
});
