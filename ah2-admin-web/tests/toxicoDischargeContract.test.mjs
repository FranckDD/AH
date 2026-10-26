import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/toxico/ToxicoDischargeModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : sortie d'un patient toxicologie (motif obligatoire, note, confirmation) ---
check('ToxicoDischargeModal', view, [
    // interface avec la liste
    'dossierId: { type: Number, required: true }', "patientName: { type: String, default: '' }", "defineEmits(['close', 'discharged'])", "emit('discharged');",
    // motif : guérison / abandon / exclusion / autre
    'v-for="r in DISCHARGE_REASONS"', ':key="r"', 'type="radio"', 'name="discharge-reason"', ':value="r"', 'v-model="reason"', 't(dischargeReasonLabelKey(r))', 'reason === r',
    // note : obligatoire pour « autre »
    "reason === 'autre'", 'v-model="note"', ':maxlength="NOTE_MAX_LENGTH"', "t('toxico.stays.note_label')", "t('toxico.stays.optional')", "t('toxico.stays.note_placeholder')",
    // validation et envoi
    'const errors = validateDischarge({ reason: reason.value, note: note.value, date: dischargeDate.value, minDate: props.minDate, today });', 'if (errors.length) { errorKey.value = errors[0]; return; }', 'if (isSubmitting.value) return;',
    'await toxicoStore.dischargePatient(props.dossierId, { reason: reason.value, note: note.value, date: dischargeDate.value });', 'watch([reason, note, dischargeDate], () => { errorKey.value = \'\'; serverError.value = \'\'; });',
    "const errorText = computed(() => serverError.value || (errorKey.value ? t(errorKey.value) : ''));",
    // fermeture : jamais pendant l'envoi
    'if (!isSubmitting.value) emit(\'close\');', ':disabled="isSubmitting"', '@submit.prevent="submit"',
    // erreurs serveur
    "status === 409 ? t('toxico.stays.errors.conflict')", "status === 422 ? t('toxico.stays.errors.invalid')", "status === 403 ? t('toxico.stays.errors.forbidden')", "t('toxico.stays.errors.generic')",
    'serverError.value = apiErrorMessage(e, fallback);', 'v-if="errorText"', 'role="alert"',
    // clés
    "t('toxico.stays.discharge_title')", "t('toxico.stays.reason_label')", "t('toxico.stays.discharge_warning')", "t('toxico.stays.cancel')", "t('toxico.stays.submitting')", "t('toxico.stays.confirm')",
]);

test('toutes les clés toxico.* et toxicoScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:toxico|toxicoScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 8);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ToxicoDischargeModal : panneau accessible, en-tête rouge, champs étiquetés, barre d actions', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /<FullScreenPanel[^>]*tone="danger"/s, 'la sortie garde son en-tête rouge');
    assert.match(t, /@close="close"/);
});

test('ToxicoDischargeModal : « Confirmer la sortie » en rouge, motifs en choix avec texte, avertissement et erreur annoncés', () => {
    const t = templateOf(view);
    assert.match(t, /<AppButton[^>]*variant="danger"[^>]*type="submit"|<AppButton[^>]*type="submit"[^>]*variant="danger"/s);
    assert.match(t, /<fieldset/);
    assert.match(t, /<legend/);
    assert.match(t, /toneClasses\('warning'\)/);
    assert.match(t, /toneClasses\('danger'\)/);
    assert.match(t, /role="alert"/);
    assert.match(t, /min-h-11/);
});

test('ToxicoDischargeModal : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×]|&times;|\p{Extended_Pictographic}/u);
});
