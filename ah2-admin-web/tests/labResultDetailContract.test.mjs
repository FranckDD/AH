import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/lab/ResultDetailModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : détail d'un résultat de laboratoire (utilisé par l'historique, les résultats médicaux et le dossier patient) ---
check('ResultDetailModal', view, [
    // interface avec les écrans parents
    'result: { type: Object, required: true }', "defineEmits(['close', 'print', 'amend'])", "emit('print', props.result)", "$emit('close')",
    // nom du patient
    'if (r.patient_info?.nom) return r.patient_info.nom;', 'if (r.patient_name) return r.patient_name;', "r.external_patient_info.nom_complet || t('lab.result_modal.external_patient')", "return t('lab.result_modal.anonymous');",
    // statut
    "'pending': t('lab.status.pending')", "'completed': t('lab.status.completed')", "'validated': t('lab.status.validated')", "return map[status] || status || t('lab.result_modal.unknown');",
    "case 'validated'", "case 'completed'",
    // dates
    "if (!date) return t('lab.result_modal.unknown_date');", "dayjs(date).format('DD/MM/YYYY HH:mm')", 'result.test_date || result.created_at',
    // plage de référence
    'rangeLabelForDetail(detail, info?.sexe, info?.age_days ?? null, null)', 'getRange(detail, result.patient_info)',
    // anomalies
    "!!(detail.is_abnormal || detail.flagged || ['H', 'L', 'A'].includes(detail.flag))", "if (interp === 'haut') return t('lab.result_modal.flag_high');", "if (interp === 'bas') return t('lab.result_modal.flag_low');",
    "return t('lab.result_modal.abnormal');", 'isAbnormal(detail)', 'flagLabel(detail)',
    // lignes du tableau
    ':rows="result.details || []"', 'row-key="detail_id"', 'detail.nom || detail.parameter_name', "detail.valeur !== null && detail.valeur !== undefined && detail.valeur !== ''",
    'detail.unite || detail.unit', 'detail.interpretation',
    // informations patient et prescription
    'result.is_external || result.external_patient_info', 'result.patient_info?.sexe || result.patient_sexe', 'result.patient_info?.age', 'result.patient_age',
    'result.medecin_prescripteur || result.prescriber', 'result.examen_nom || result.exam_name', 'result.result_id || result.id', 'v-if="result.code"',
    // notes et impression
    'v-if="result.note || result.comments"', 'result.note || result.comments', 'v-if="result.status !== \'pending\'"', '@click="printPdf"',
    // clés
    "t('lab.result_modal.exam_of')", "t('lab.result_modal.batch')", "t('lab.result_modal.patient_info')", "t('lab.result_modal.type')", "t('lab.result_modal.external')", "t('lab.result_modal.internal')",
    "t('lab.result_modal.sex')", "t('lab.result_modal.not_provided')", "t('lab.result_modal.age')", "t('lab.result_modal.years')", "t('lab.result_modal.prescription')", "t('lab.result_modal.prescriber')",
    "t('lab.result_modal.exam')", "t('lab.result_modal.not_specified')", "t('lab.result_modal.bio_results')", "t('lab.result_modal.param')", "t('lab.result_modal.result')", "t('lab.result_modal.unit')",
    "t('lab.result_modal.ref_values')", "t('lab.result_modal.interpretation')", "t('lab.result_modal.no_params')", "t('lab.result_modal.notes')", "t('lab.result_modal.close')", "t('lab.result_modal.print')",
]);

test('toutes les clés lab.* et labScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 25);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ResultDetailModal : panneau accessible (FullScreenPanel), tableau responsive, statut en badge avec texte, barre d actions', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['FullScreenPanel', 'ResponsiveTable', 'StatusBadge', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.doesNotMatch(t, /<table/);
    assert.match(t, /<FullScreenPanel[^>]*@close="\$emit\('close'\)"/s);
});

test('ResultDetailModal : valeur anormale dite par une icône ET un texte (jamais la couleur seule)', () => {
    for (const icon of ['ArrowUpIcon', 'ArrowDownIcon', 'ExclamationTriangleIcon']) assert.match(view, new RegExp(icon), icon);
    const t = templateOf(view);
    assert.match(t, /flagLabel\(detail\)/);
    assert.doesNotMatch(t, /[🔺🔻✅⚠]|\p{Extended_Pictographic}/u);
});

test('ResultDetailModal : impression en bouton du thème (info), fermeture secondaire', () => {
    const t = templateOf(view);
    assert.match(t, /variant="info"/);
    assert.match(t, /<AppButton[^>]*@click="printPdf"/s);
});

test('ResultDetailModal : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view, /@apply|<style/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
});

test('clés labScreens (détail d un résultat) en FR et EN', () => {
    const keys = ['result_id'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labScreens.${k}`);
        }
    }
});
