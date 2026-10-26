import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/toxico/ToxicoStaysTimeline.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : séjours d'un patient toxicologie (phases et évaluations, séjour en cours, ancien historique) ---
check('ToxicoStaysTimeline', view, [
    // interface
    'stays: { type: Array, default: () => [] }', 'phaseHistory: { type: Array, default: () => [] }', 'evaluations: { type: Array, default: () => [] }',
    // regroupement par séjour
    "...props.phaseHistory.map((p) => ({ ...p, kind: 'phase', date: p.start_date })),", "...props.evaluations.map((e) => ({ ...e, kind: 'eval', date: e.created_at })),",
    'return groupByStay(sortNewestFirst(items), props.stays);', 'const formatDate = formatDateDMY;',
    // séjours
    '!groups.length', 'v-for="g in groups"', ":key=\"g.legacy ? 'legacy' : g.stay.stay_number\"", 'g.stay?.is_open', 'v-if="!g.legacy"', 'g.stay.stay_number', 'g.stay.is_open',
    'g.stay.discharge_reason', 'g.stay.admission_date', 'g.stay.discharge_date', 'g.stay.psychologist_name', 'g.stay.substance', 'g.stay.discharge_note', 'g.stay.discharged_by_name',
    // éléments d'un séjour
    'g.items.length', 'v-for="(item, i) in g.items"', 'formatDate(item.date)', "item.kind === 'phase'", 'item.phase', 'item.status', 'isFinishedStatus(item.status)', 'item.end_date', 'item.comments',
    'item.decision', 'item.phase_before', 'item.phase_after', 'item.is_relapse', 'item.evaluator_name', 'item.observation', 'item.recommendation',
    // clés
    "t('toxico.stays.empty')", "t('toxico.stays.stay_n', { n: g.stay.stay_number })", "t('toxico.stays.current')", "t(dischargeReasonLabelKey(g.stay.discharge_reason))", "t('toxico.stays.ongoing')",
    "t('toxico.stays.legacy')", "t('toxico.stays.discharged_by', { name: g.stay.discharged_by_name })", 't(`toxico.phases.${item.phase}`)', "t('toxico.stays.until', { date: formatDate(item.end_date) })",
    "t('toxico.stays.evaluation')", "t('toxico.stays.relapse')", "t('toxico.stays.recommendation')", "t('toxico.stays.no_items')",
]);

test('toutes les clés toxico.* et toxicoScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:toxico|toxicoScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    for (const k of ['toxico.stays.period']) used.add(k);
    assert.ok(used.size >= 10);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ToxicoStaysTimeline : composants ui/, séjour en cours mis en avant (indigo), états en pastilles avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    assert.match(view, /\bStatusBadge\b/);
    const t = templateOf(view);
    assert.match(t, /<StatusBadge/);
    assert.match(t, /border-action-600/, 'le séjour en cours garde son contour indigo');
    assert.match(t, /bg-action-50/);
    assert.match(t, /tone="danger"|:tone="'danger'"/, 'rechute en rouge');
});

test('ToxicoStaysTimeline : liste sémantique, dates en balises time, séjours titrés', () => {
    const t = templateOf(view);
    assert.match(t, /<time\b/);
    assert.match(t, /<ul\b/);
    assert.match(t, /<h4|<h5|<h3/);
});

test('ToxicoStaysTimeline : la ligne d évaluation n a plus de séparateurs ni de flèche typographiques (texte lisible)', () => {
    const t = templateOf(view);
    assert.doesNotMatch(t.replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×]|\p{Extended_Pictographic}/u);
    assert.match(t, /t\('toxicoScreens\.eval_line'/);
});

test('ToxicoStaysTimeline : jetons du thème, texte >= 13 px', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
});

test('clés toxicoScreens (séjours) en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        const v = msgs[locale].toxicoScreens?.eval_line;
        assert.equal(typeof v, 'string', `${locale}.toxicoScreens.eval_line`);
        assert.match(v, /\{evaluation\}/);
        assert.match(v, /\{decision\}/);
        assert.match(v, /\{before\}/);
        assert.match(v, /\{after\}/);
        assert.doesNotMatch(v, /[—–…·→]/);
    }
});
