import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/toxico/ToxicoDischargedPanel.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : patients sortis de la toxicologie (filtres, périodes, exports PDF, réadmission, pagination) ---
check('ToxicoDischargedPanel', view, [
    // interface avec la liste
    'defineProps({ canReadmit: { type: Boolean, default: false } });', "defineEmits(['view', 'readmit']);", "$emit('view', row)", "$emit('readmit', row)",
    // filtres
    ':value="store.dischargedFilters.search"', '@input="onSearch"', 'type="search"', ':value="store.dischargedFilters.reason"', "@change=\"store.setDischargedFilters({ reason: $event.target.value })\"",
    'v-for="r in DISCHARGE_REASONS"', 't(dischargeReasonLabelKey(r))', 'type="date"', ':value="dateFrom"', ":value=\"dateTo\"", "@change=\"onDate('from', $event.target.value)\"", "@change=\"onDate('to', $event.target.value)\"",
    // saisie : recherche différée, dates validées localement
    '}, 400);', 'pendingSearch = value;', 'if (dateError.value) store.dischargedFilters.search = value;', 'else store.setDischargedFilters({ search: value });',
    'const dateError = computed(() => dischargedDateRangeError(dateFrom.value, dateTo.value));', 'if (dateError.value) store.clearDischarged();', 'else store.setDischargedFilters({ from: dateFrom.value, to: dateTo.value });',
    "onMounted(() => { if (!dateError.value) store.fetchDischarged(); });", 'onBeforeUnmount(() => clearTimeout(searchTimeout));',
    // états
    'v-if="dateError"', 'store.dischargedLoading', 'store.dischargedError', 'role="alert"', '@click="store.fetchDischarged()"', ':rows="store.discharged"',
    // lignes
    'store.discharged', 'row-key="dossier_id"', 'row.patientName', 'row.code', 'row.last_stay?.discharge_reason', 'row.last_stay?.psychologist_name', 'row.stays_count',
    "const fmt = (d) => (d ? formatDateDMY(d) : '-');", "t('toxico.discharged.stay_dates', { n: row.last_stay.stay_number, from: fmt(row.last_stay.admission_date), to: fmt(row.last_stay.discharge_date) })",
    // motifs de sortie : guérison, abandon, exclusion, autre
    'guerison:', 'abandon:', 'exclusion:', 'autre:',
    // actions et exports
    'v-if="canExportList"', '@click="exportList"', ':disabled="listExporting || !!dateError"', 'v-if="canExportDossier"', '@click="exportRow(row)"', ':disabled="rowExporting === row.patient_id"',
    'v-if="canReadmit"', 'const search = resolveExportSearch(pendingSearch, store.dischargedFilters.search);', 'const params = buildDischargedExportQuery({ ...store.dischargedFilters, search, from: dateFrom.value, to: dateTo.value });',
    'const res = await ToxicoGateway.exportDischargedPdf(params);', 'downloadPdfBlob(res.data, DISCHARGED_EXPORT_FILENAME);', 'const res = await ToxicoGateway.exportDossierPdf(row.patient_id);',
    'downloadPdfBlob(res.data, dossierExportFilename(row.patient_id));', 'exportError.value = exportErrorKey(e);', 'v-if="exportError"', 't(exportError)',
    // pagination
    '!dateError && !store.dischargedLoading && !store.dischargedError && store.dischargedTotal > 0', ':disabled="page <= 1"', 'store.setDischargedPage(page - 1)', ':disabled="page >= Math.max(store.dischargedTotalPages, 1)"',
    'store.setDischargedPage(page + 1)', "t('toxico.discharged.page_of', { page, pages: Math.max(store.dischargedTotalPages, 1), total: store.dischargedTotal }, store.dischargedTotal)",
    // clés
    "t('toxico.discharged.filters.search')", "t('toxico.discharged.filters.search_placeholder')", "t('toxico.discharged.filters.reason')", "t('toxico.discharged.filters.all_reasons')",
    "t('toxico.discharged.filters.from')", "t('toxico.discharged.filters.to')", "t('toxico.export.exporting')", "t('toxico.export.list_pdf')", "t('toxico.export.row_pdf')", "t('toxico.export.dossier_pdf')",
    "t('toxico.discharged.invalid_range_hint')", "t('toxico.discharged.loading')", "t('toxico.discharged.error')", "t('toxico.discharged.retry')", "t('toxico.discharged.empty')",
    "t('toxico.discharged.col.patient')", "t('toxico.discharged.col.stay')", "t('toxico.discharged.col.reason')", "t('toxico.discharged.col.psy')", "t('toxico.discharged.col.stays')",
    "t('toxico.discharged.none')", "t('toxico.discharged.view')", "t('toxico.discharged.readmit')", "t('toxico.discharged.prev')", "t('toxico.discharged.next')", "t('toxico.discharged.pagination')",
]);

test('toutes les clés toxico.* et toxicoScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:toxico|toxicoScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 25);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ToxicoDischargedPanel : composants ui/, filtres étiquetés, un seul tableau responsive à lignes alternées', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['FormField', 'ResponsiveTable', 'StatusBadge', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.doesNotMatch(t, /<table/);
    assert.doesNotMatch(t, /hidden lg:block|lg:hidden/, 'un seul gabarit : le tableau devient des cartes tout seul');
    assert.match(t, /<nav\b[\s\S]*?:aria-label/);
});

test('ToxicoDischargedPanel : mêmes couleurs de motif (vert, orange, rouge, gris) via les tonalités, le motif toujours écrit', () => {
    assert.match(view, /guerison: 'success'/);
    assert.match(view, /abandon: 'warning'/);
    assert.match(view, /exclusion: 'danger'/);
    assert.match(view, /autre: 'neutral'/);
    assert.match(templateOf(view), /<StatusBadge[^>]*reasonTone\(/s);
    assert.doesNotMatch(view, /reasonClass/);
});

test('ToxicoDischargedPanel : actions en boutons compacts avec texte, Voir bleu ciel, PDF contour, Réadmettre vert', () => {
    const t = templateOf(view);
    assert.match(t, /<AppButton[^>]*variant="info"[^>]*@click="\$emit\('view', row\)"/s);
    assert.match(t, /<AppButton[^>]*variant="secondary"[^>]*@click="exportRow\(row\)"/s);
    assert.match(t, /<AppButton[^>]*variant="success"[^>]*@click="\$emit\('readmit', row\)"/s);
    assert.match(t, /size="sm"/);
});

test('ToxicoDischargedPanel : états annoncés (période invalide, chargement, erreur avec réessai, vide)', () => {
    const t = templateOf(view);
    assert.match(t, /role="status"/);
    assert.match(t, /role="alert"/);
    assert.doesNotMatch(t, /animate-spin/);
});

test('ToxicoDischargedPanel : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view.slice(0, view.indexOf('</template>')).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×]|\p{Extended_Pictographic}/u);
    assert.doesNotMatch(view.slice(view.indexOf('const fmt')), /return '—'/, 'le tiret long de fmt est remplacé');
});
