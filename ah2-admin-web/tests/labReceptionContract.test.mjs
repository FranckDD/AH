import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labo/LabReception.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : réception du laboratoire (patient interne ou externe, prescripteur, panier, envoi) ---
check('LabReception', view, [
    // initialisation
    'labStore.fetchExams();', 'labStore.clearMessages();', 'fetchDoctors();', "window.addEventListener('click', (e) => {", "if (!e.target.closest('.relative')) {",
    // médecins : serveur puis repli hors ligne du laborantin
    "api.get('/users/doctors')", 'doctors.value = response.data;', "if (!e.response && authStore.hasRole(['laborantin'])) {",
    "SELECT user_id, full_name FROM doctors_lookup ORDER BY full_name", 'specialty_name: null,',
    // recherche
    'debounce(async (val) => {', 'val.trim().length > 1', 'await labStore.searchInternal(val.trim());', '}, 300);', 'labStore.searchResults = [];', 'showResults.value = true;',
    'v-model="searchQuery"', 'v-for="p in labStore.searchResults"', ':key="p.prescription_id ?? `inv-${p.id}`"', '@click="selectInternalPatient(p)"', 'p.nom', 'p.patient_code', 'p.exams_prescribed.length',
    'v-if="showResults"', 'labStore.loading',
    // sélection et import des examens prescrits (appariement par nom)
    'selectedPatient.value = p;', 'cart.value = [];', 'autoImportedCount.value = 0;', 'p.exams_prescribed.forEach(prescribedName => {',
    'normalize(e.nom) === normalize(prescribedName)', "return str ? str.toString().toLowerCase().trim() : '';",
    'const alreadyInCart = cart.value.some(c => c.id === fullExam.id);', 'cart.value.push({ ...fullExam, is_prescribed: true });', 'autoImportedCount.value++;',
    'v-if="autoImportedCount > 0"',
    // modes
    "const mode = ref('internal');", "@click=\"setMode('internal')\"", "@click=\"setMode('external')\"", "mode === 'internal'", 'resetPatient();',
    // patient externe
    'v-model="extForm.full_name"', 'v-model.number="extForm.age"', 'v-model="extForm.gender"', 'value="M"', 'value="F"', "extForm.value = { full_name: '', age: '', gender: 'M' };",
    // prescripteur
    'v-model="selectedDoctorId"', ':value="null"', 'v-for="doc in doctors"', ':key="doc.user_id"', ':value="doc.user_id"', 'doc.full_name', 'doc.specialty_name',
    // panier
    'v-model="selectedExamId"', 'v-for="exam in labStore.exams"', ':key="exam.id"', ':value="exam.id"', '@click="addExamToCart"', ':disabled="!selectedExamId"',
    'const exam = labStore.exams.find(e => e.id === selectedExamId.value);', 'if (!cart.value.find(c => c.id === exam.id)) {', 'cart.value.push({ ...exam, is_prescribed: false });',
    'selectedExamId.value = null;', 'const removeFromCart = (index) => {', 'cart.value.splice(index, 1);', 'item.is_prescribed', 'cart.length > 0',
    // validation et envoi
    'const hasExam = cart.value.length > 0;', "mode.value === 'internal'", '? !!selectedPatient.value', ': (extForm.value.full_name && extForm.value.age);', 'const hasDoctor = !!selectedDoctorId.value;',
    'return hasExam && hasPatient && hasDoctor;', '@click="submitRequest"', ':disabled="!canSubmit || labStore.loading"', 'if (cart.value.length === 0) return;',
    'examen_id: item.id,', 'valeur: null,', "unite: item.unite || ''", 'patient_id: null,', 'origin_prescription_id: null,', 'prescribed_by_id: selectedDoctorId.value,',
    'prescribed_by_name: doc ? doc.full_name : null,', 'external_patient_info: null', 'payload.patient_id = selectedPatient.value.id;',
    'selectedPatient.value.prescription_id || selectedPatient.value.last_prescription_id || null', 'nom: extForm.value.full_name,', "prenom: '',", 'age: extForm.value.age,',
    'sexe: extForm.value.gender,', "telephone: ''", 'await labStore.createBatchRequest(payload);', "notify('alerts.lab_saved', {}, 'success');", "notify('alerts.lab_save_failed');",
    // clés
    "$t('lab.reception.title')", "$t('lab.reception.subtitle')", "$t('lab.reception.section1_title')", "$t('lab.reception.mode_internal')", "$t('lab.reception.mode_external')",
    "$t('lab.reception.search_placeholder')", "$t('lab.reception.no_results')", "$t('lab.reception.patient_internal_label')", "$t('lab.reception.change_patient')",
    "$t('lab.reception.ext_name_label')", "$t('lab.reception.ext_age_label')", "$t('lab.reception.ext_gender_label')", "$t('lab.gender.m')", "$t('lab.gender.f')", "$t('lab.reception.ext_warning')",
    "$t('lab.reception.section2_title')", "$t('lab.reception.select_exam_placeholder')", "$t('lab.reception.add_btn')",
    "'lab.reception.cart_exam_col'", "'lab.reception.cart_action_col'", "$t('lab.reception.cart_empty')", "$t('lab.reception.submit_btn')", 'labStore.successMessage',
]);

test('toutes les clés lab.* et labScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 20);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabReception : composants ui/, en-tête, champs étiquetés, panier en tableau responsive, barre d actions', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'AppCard', 'FormField', 'ResponsiveTable', 'StatusBadge', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
});

test('LabReception : mode en groupe de boutons nommé, résultats de recherche accessibles au clavier, messages annoncés', () => {
    const t = templateOf(view);
    assert.match(t, /role="group"/);
    assert.match(t, /aria-pressed/);
    assert.match(t, /<button[^>]*@click="selectInternalPatient\(p\)"/s, 'chaque résultat est un bouton');
    assert.match(t, /role="status"/);
    assert.doesNotMatch(t, /<div[^>]*@click="selectInternalPatient/s, 'un résultat ne doit plus être un div cliquable');
});

test('LabReception : plus aucun texte français en dur dans le gabarit (tout passe par vue-i18n)', () => {
    const t = templateOf(view).replace(/\{\{[^}]*\}\}/g, '').replace(/<!--.*?-->/gs, '');
    for (const bad of ['Recherche en cours', 'examens prescrits', 'Prescription vide', 'Prescrit par', 'Choisir le prescripteur', 'importés de la prescription']) {
        assert.ok(!t.includes(bad), `texte en dur : ${bad}`);
    }
    assert.doesNotMatch(templateOf(view), /'Médecin'|>Prescrit</);
});

test('LabReception : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view, /<style/);
    assert.doesNotMatch(templateOf(view), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /\.\.\.|-- /);
});

test('clés labScreens (réception) en FR et EN', () => {
    const keys = ['mode_label', 'searching', 'exams_prescribed_count', 'prescription_empty', 'imported_count', 'prescriber_section', 'prescribed_by', 'choose_prescriber', 'prescriber_help',
        'prescribed_badge', 'doctor_default', 'ext_name_placeholder', 'remove', 'cart_table', 'search_label'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labScreens.${k}`);
        }
    }
});
