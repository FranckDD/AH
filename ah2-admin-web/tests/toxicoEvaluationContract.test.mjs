import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/toxico/ToxicoEvaluationModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : évaluation d'un patient toxicologie (maintenir, avancer ou régresser de phase) ---
check('ToxicoEvaluationModal', view, [
    // interface avec la liste
    'patient: { type: Object, required: true }', "defineEmits(['close', 'save'])", "emit('save',payload);", "emit('close');",
    // état et phases
    "decision: 'MAINTAIN',", "observation: '',", "recommendation: ''", 'props.patient.currentPhase < 4 ? props.patient.currentPhase + 1 : 4', 'props.patient.currentPhase > 1 ? props.patient.currentPhase - 1 : 1',
    "case 'PROGRESS': return nextPhase.value;", "case 'REGRESS': return prevPhase.value;", 'default: return props.patient.currentPhase;',
    // choix de la décision
    "'MAINTAIN'", "'PROGRESS'", "'REGRESS'", "form.decision === 'MAINTAIN'", "form.decision === 'PROGRESS'", "form.decision === 'REGRESS'",
    // saisie : observation obligatoire, plus détaillée pour une régression
    'v-model="form.observation"', 'required', 'maxlength="500"', 'form.observation.length', 'v-model="form.recommendation"', 'maxlength="200"', 'form.recommendation.length',
    "form.observation.length < 10 && form.decision === 'REGRESS'",
    'if (!form.observation.trim()) return false;', "if (form.decision === 'REGRESS' && form.observation.trim().length < 10) return false;",
    // résumé de la décision
    'getDecisionSummary()', 'const getDecisionSummary = () => {', 'props.patient.currentPhase', 'nextPhase.value', 'prevPhase.value',
    // envoi
    'if (!isFormValid.value) {', "Pour une régression, l'observation doit être détaillée (minimum 10 caractères)", "L'observation est obligatoire", 'if (isLoading.value) return;',
    'const dossierId = props.patient.dossier_id || props.patient.id;', 'if (!dossierId) {', 'dossier_id: Number(dossierId),', 'decision: form.decision,', 'observation: form.observation.trim(),',
    'recommendation: form.recommendation?.trim() || null,', 'targetPhase: Number(targetPhase.value)', 'await toxicoStore.submitEvaluation(payload);', 'watch(form, () => {',
    '@click="handleSubmit"', ':disabled="isLoading || !isFormValid"', ':disabled="isLoading"', "@click=\"$emit('close')\"", 'v-if="errorMessage"', '@submit.prevent="handleSubmit"',
    // erreurs serveur
    'if (error.response.status === 422) {', 'error.response.status === 400', 'error.response.status === 401', 'error.response.status === 404', 'else if (error.request) {',
    // clés
    "t('toxico.modal.eval_title')", "t('toxico.modal.decision_label')", "t('toxico.modal.maintain')", "t('toxico.modal.progress')", "t('toxico.modal.regress')",
    "t('toxico.modal.observations')", "t('toxico.modal.recommendations')", "t('toxico.modal.validate_eval')", 't(`toxico.phases.${patient.currentPhase}`)', 'patient.patientName', "t('common.cancel')",
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
test('ToxicoEvaluationModal : panneau accessible, décision en vrais choix, champs étiquetés, barre d actions', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /<FullScreenPanel[^>]*accent/s);
    assert.equal((t.match(/type="radio"/g) || []).length, 3, 'trois choix : maintenir, avancer, régresser');
    assert.match(t, /v-model="form\.decision"/);
    assert.match(t, /<fieldset/);
    assert.match(t, /<legend/);
    assert.doesNotMatch(t, /<div[^>]*@click="form\.decision/s, 'plus de div cliquable');
});

test('ToxicoEvaluationModal : mêmes couleurs de décision qu avant (gris, vert, rouge) avec icône et mot, plus d emoji', () => {
    for (const icon of ['PauseCircleIcon', 'ForwardIcon', 'BackwardIcon']) assert.match(view, new RegExp(icon), icon);
    const t = templateOf(view);
    assert.doesNotMatch(t, /[⏹⏩⏪]|\p{Extended_Pictographic}/u);
    assert.match(view, /toneClasses\('danger'\)/);
    assert.match(t, /toneClasses\('warning'\)|toneClasses\('info'\)|toneClasses\(/);
});

test('ToxicoEvaluationModal : le bouton de validation prend la couleur de la décision (indigo, vert, rouge)', () => {
    assert.match(view, /const submitVariant = computed\(\(\) => \{/);
    assert.match(view, /case 'PROGRESS': return 'success';/);
    assert.match(view, /case 'REGRESS': return 'danger';/);
    assert.match(view, /default: return 'primary';/);
    assert.match(templateOf(view), /<AppButton[^>]*:variant="submitVariant"/s);
    assert.doesNotMatch(view, /submitButtonClass/);
});

test('ToxicoEvaluationModal : avertissement de rechute et résumé annoncés, erreur annoncée', () => {
    const t = templateOf(view);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
});

test('ToxicoEvaluationModal : plus aucun texte français en dur dans le gabarit ni dans le résumé', () => {
    const t = templateOf(view).replace(/\{\{[^}]*\}\}/g, '').replace(/<!--.*?-->/gs, '');
    for (const bad of ['Patient:', 'Phase actuelle', 'Reste Phase', 'Vers Phase', 'Retour Phase', 'Attention :', 'Résumé :', 'Enregistrement...', 'État psychologique', 'Actions à entreprendre', 'Pour une régression']) {
        assert.ok(!t.includes(bad), `texte en dur : ${bad}`);
    }
    assert.doesNotMatch(view, /Le patient (passera|retournera|restera)/);
});

test('ToxicoEvaluationModal : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×]|&times;|\p{Extended_Pictographic}/u);
});

test('clés toxicoScreens (évaluation) en FR et EN', () => {
    const keys = ['eval_subtitle', 'eval_stay', 'eval_to', 'eval_back', 'eval_regress_warning', 'eval_obs_hint', 'eval_obs_placeholder', 'eval_reco_placeholder', 'eval_summary', 'eval_summary_progress',
        'eval_summary_regress', 'eval_summary_maintain', 'saving', 'decision_group'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].toxicoScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.toxicoScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.toxicoScreens.${k}`);
        }
    }
    for (const k of ['eval_summary_progress', 'eval_summary_regress']) for (const locale of ['fr', 'en']) assert.match(msgs[locale].toxicoScreens[k], /\{from\}.*\{to\}/, `${locale} ${k}`);
});
