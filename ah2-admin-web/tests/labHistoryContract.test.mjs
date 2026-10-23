import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labo/LabHistory.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : historique du laboratoire (recherche, statut, anomalies, pagination, détail, PDF) ---
check('LabHistory', view, [
    // filtres de départ (arrivée depuis le tableau de bord : ?abnormal=1&period=month)
    "const PERIODS = ['day', 'month', 'year'];", "abnormal: route.query.abnormal === '1',", 'period: PERIODS.includes(route.query.period) ? route.query.period : null,', 'page: 1,', 'limit: 15',
    // chargement
    'if (q.length === 1) return;', 'await store.fetchPaginatedHistory({', 'search: q.length >= 2 ? q : null,', "status: filters.value.status || null,", 'abnormal: filters.value.abnormal ? true : null,',
    'period: filters.value.abnormal ? filters.value.period : null', 'onMounted(() => {', 'fetchData();',
    // recherche et filtres
    'v-model="filters.query"', '@input="handleSearch"', 'v-model="filters.status"', '@change="handleFilterChange"', 'value=""', 'value="pending"', 'value="completed"',
    'debounce(() => {', '}, 400);', 'filters.value.page = 1;',
    // anomalies seules
    'v-if="filters.abnormal"', '@click="clearAbnormal"', 'filters.value.abnormal = false;', 'filters.value.period = null;', 'v-if="filters.period"', 't(`lab.dashboard.period_${filters.period}`)',
    // rafraîchir
    '@click="refresh"', "filters.value.query = '';", "filters.value.status = '';",
    // lignes
    'store.paginatedHistory.items', // actions
    "const detail = await store.fetchResultDetail(item.result_id);", 'selectedResult.value = detail;', 'const filename = `Resultat_${item.result_id}.pdf`;', 'await store.downloadPDF(item.result_id, filename);', '<ResultDetailModal', ':result="selectedResult"', '@close="selectedResult = null"', '@print="downloadPdf"',
    // vide et pagination
    'groupHistory(store.paginatedHistory.items)', 'groupPassagesByDay(passages.value)', 'v-for="day in days"', ':key="day.key"',
    '<LabHistoryPassage v-for="passage in day.passages"', ':key="passage.key"', ':passage="passage"', '@view="openView"', '@pdf="downloadPdf"', '@pdf-batch="downloadBatchPdf"',
    'await store.downloadBatchPDF(passage.batch_id,', "import LabHistoryPassage from '@/components/lab/LabHistoryPassage.vue';",
    "const detail = await store.fetchResultDetail(item.result_id);", ':key="passage.key"', 'group: true', 'store.loading && store.paginatedHistory.items.length === 0', 'store.paginatedHistory.items.length === 0', 'v-if="store.paginatedHistory.total_pages > 0"', '@click="prevPage"', ':disabled="filters.page === 1"', '@click="nextPage"',
    ':disabled="filters.page >= store.paginatedHistory.total_pages"', 'if (filters.value.page < store.paginatedHistory.total_pages) {', 'filters.value.page++;', 'if (filters.value.page > 1) {', 'filters.value.page--;',
    "t('labScreens.history_passages', { n: passages.length, total: store.paginatedHistory.total_items })",
    "t('lab.history_view.page', { current: store.paginatedHistory.current_page, total: store.paginatedHistory.total_pages })",
    // clés
    "t('lab.history_view.search_ph')", "t('lab.history_view.all_statuses')", "t('lab.status.pending')", "t('lab.history_view.completed_tech')", "t('lab.history_view.clear_abnormal')",
    "t('lab.history_view.abnormal_only')", "t('lab.history_view.refresh')", "t('lab.history_view.empty')", "t('lab.history_view.empty_hint')", "t('lab.history_view.prev')", "t('lab.history_view.next')",
]);

test('toutes les clés lab.* et labScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 14);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabHistory : composants ui/, une carte par passage patient, statuts en badge avec texte, champs étiquetés', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'FormField', 'EmptyState', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.doesNotMatch(t, /<table/);
    assert.match(t, /<LabHistoryPassage/);
});

test('LabHistory : actions par ligne en boutons avec texte (jamais une icône seule), pagination nommée', () => {
    const t = templateOf(view);
    assert.match(t, /<h2[^>]*>\{\{ dayLabel\(day\.key\) \}\}/);
    assert.match(t, /<nav\b[\s\S]*?:aria-label/);
});

test('LabHistory : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view, /@apply|<style/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
    assert.doesNotMatch(templateOf(view), />\s*\|\s*</);
});

test('clés labScreens (historique) en FR et EN', () => {
    const keys = ['history_search', 'status_filter', 'pagination_label'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labScreens.${k}`);
        }
    }
});
