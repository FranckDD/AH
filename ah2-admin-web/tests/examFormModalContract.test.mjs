import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const modal = readFileSync(new URL('../src/components/config/ExamFormModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : création et modification d'un examen (aucun changement de forme envoyée ni de verrou du code) ---
check('ExamFormModal', modal, [
    // interface avec l'écran parent
    "defineProps({\n  examen: { type: Object, default: null }\n});".replace(/\n/g, modal.includes('\r\n') ? '\r\n' : '\n'),
    "defineEmits(['close', 'saved'])",
    // formulaire initial et remise à zéro
    'id: null,', "code: '',", "nom: '',", "categorie: '',", 'prix: 0',
    'const isEditing = computed(() => form.id !== null);', 'Object.assign(form, newVal);', 'form.id = null;', "form.code = '';", "form.nom = '';", "form.categorie = '';", 'form.prix = 0;',
    '{ immediate: true }',
    // enregistrement
    'await configStore.saveExamen({ ...form });', "emit('saved');", "emit('close');", 'notifyText(error.message);', '@submit.prevent="handleSave"', ':disabled="configStore.isLoading"',
    // champs : code verrouillé en modification, prix par pas de 100
    'v-model="form.nom"', 'v-model="form.code"', 'v-model="form.categorie"', 'v-model.number="form.prix"', ':disabled="isEditing"', 'type="number"', 'min="0"', 'step="100"', 'required',
    '@click="$emit(\'close\')"',
    // clés
    "t('config.edit')", "t('config.add_exam')", "t('config.table_name')", "t('config.table_code')", "t('config.table_category')", "t('config.table_price')", "t('config.cancel')", "t('config.save')",
]);

test('toutes les clés config.* et configScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of modal.matchAll(/['"`(]((?:config|configScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 7);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ExamFormModal : panneau, champs étiquetés, barre d’actions', () => {
    for (const c of ['FullScreenPanel', 'FormField', 'ActionBar', 'AppButton']) assert.match(modal, new RegExp(`\\b${c}\\b`), c);
    assert.doesNotMatch(templateOf(modal), /fixed inset-0/);
});

test('ExamFormModal : unité FCFA affichée avec le prix et aide sur le code verrouillé', () => {
    const t = templateOf(modal);
    assert.match(t, /FCFA/);
    assert.match(t, /configScreens\.code_locked/);
});

test('ExamFormModal : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(modal, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(modal, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(modal), /[—–…·•]|\p{Extended_Pictographic}/u);
});

test('clé configScreens.code_locked en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        const v = msgs[locale].configScreens?.code_locked;
        assert.equal(typeof v, 'string', `${locale}.configScreens.code_locked`);
        assert.doesNotMatch(v, /[—–…·]/);
    }
});
