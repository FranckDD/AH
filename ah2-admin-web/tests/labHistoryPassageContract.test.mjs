import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/lab/LabHistoryPassage.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(src.indexOf('<template>'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : une ligne de l'historique = un passage patient (dossier) ; examens dépliables ---
check('LabHistoryPassage', view, [
    // identité du patient une seule fois
    'passage.patient_name', 'passage.patient_sexe', 'passage.patient_age', 'passage.is_external', "dayjs(props.passage.test_date).format('HH:mm')",
    // état global et anomalies dits par un mot, une icône et un nombre
    't(passage.status.labelKey, passage.status.params)', 'passage.abnormalCount > 0', "t('labScreens.abnormal_count', passage.abnormalCount)", 'ExclamationTriangleIcon',
    // un seul examen : actions directes comme avant ; plusieurs : dépliage + PDF du dossier complet
    'const isMulti = computed(() => props.passage.exams.length > 1);', "$emit('view', passage.exams[0])", "$emit('pdf', passage.exams[0])", "passage.exams[0].status !== 'pending'",
    "$emit('pdf-batch', passage)", 'isMulti.value && !!props.passage.batch_id && hasPrintable(props.passage)', "defineEmits(['view', 'pdf', 'pdf-batch', 'amend'])",
    ':aria-expanded="open"', ':aria-controls="panelId"', 'v-if="isMulti && open"',
    // examens du dossier
    'v-for="res in passage.exams"', ':key="res.result_id"', "$emit('view', res)", "$emit('pdf', res)", "res.status !== 'pending'", 'res.examen_nom', 'res.result_id', 'res.code', 'res.nb_anormaux > 0',
    "examStatusMeta(status)", 't(statusMeta(res.status).labelKey)', 'statusMeta(res.status).tone',
    // clés
    "t('lab.result_modal.external')", "t('lab.history_view.view_details')", "t('lab.history_view.download_pdf')", "t('labScreens.pdf_batch')", "t('labScreens.show_exams')", "t('labScreens.hide_exams')",
    "t('labScreens.exams_count', { n: passage.exams.length })",
]);

test('toutes les clés citées par la ligne de passage existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    for (const k of ['labScreens.passage_partial', 'labScreens.exams_preview_more', 'lab.status.pending', 'lab.status.completed']) used.add(k);
    assert.ok(used.size >= 12);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
            assert.doesNotMatch(String(v), /[—–…·]/, `${locale}.${k}`);
        }
    }
});

test('le pluriel des anomalies est correct en FR et EN (un, plusieurs)', () => {
    for (const locale of ['fr', 'en']) {
        const forms = String(pick(msgs[locale], 'labScreens.abnormal_count')).split('|').map((x) => x.trim());
        assert.equal(forms.length, 2, locale);
        assert.ok(forms[0].includes('{n}') && forms[1].includes('{n}'), locale);
    }
});

test('LabHistoryPassage : composants ui/, boutons avec texte, dépliage accessible, anomalies jamais par la couleur seule', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['AppButton', 'StatusBadge']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.match(t, /variant="info"/, 'seul le PDF du dossier complet reste un bouton plein');
    assert.match(t, /size="sm"/, 'actions repetees sur chaque ligne : compactes');
    assert.equal((t.match(/variant="info"/g) || []).length, 1, 'un seul bouton plein par ligne');
    assert.match(t, /<ExclamationTriangleIcon[^>]*aria-hidden="true"/);
    assert.match(t, /border-l-tone-danger-solid/, 'repère visuel du dossier avec anomalies, en plus de l icône et du nombre');
    assert.doesNotMatch(t, /<div[^>]*@click/s);
});

test('LabHistoryPassage : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
});
