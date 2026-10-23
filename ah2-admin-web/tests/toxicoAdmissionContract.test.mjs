import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/toxico/ToxicoAdmissionModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));
const scriptOf = (src) => src.slice(src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : admission (et réadmission) d'un patient toxicologie ---
check('ToxicoAdmissionModal', view, [
    // interface avec la liste
    "defineEmits(['close', 'save'])", 'preselectedPatient: { type: Object, default: null }',
    "emit('save', { isReadmission: !!result?.is_readmission, stayNumber: result?.stay_number ?? null });", "emit('close');",
    // recherche d'un patient existant
    'v-model="searchQuery"', '@input="onSearchInput"', 'v-for="p in searchResults"', ':key="p.patient_id"', '@click="selectExistingPatient(p)"', '@click="startNewPatient"',
    'v-if="!showNewPatientForm && !selectedExistingPatient"', 'v-if="selectedExistingPatient"', '@click="clearExistingPatient"', 'selectedPatientLabel',
    'searchResults.value = await toxicoStore.searchExistingPatients(searchQuery.value);', 'if (searchQuery.value.trim().length < 2) {', '}, 300);',
    // état du dossier toxico du patient (réadmission)
    "dossierCheck === 'loading'", "dossierCheck === 'readmission'", "dossierCheck === 'active'", "dossierCheck === 'error'", '@click="checkToxicoDossier(selectedExistingPatient.patient_id)"',
    "dossierCheck.value = res.data?.isActive ? 'active' : 'readmission';", "dossierCheck.value = e?.response?.status === 404 ? 'none' : 'error';",
    "t('toxico.stays.readmission_banner', { n: nextStayNumber })", "t('toxico.stays.readmission_phase_reset')", "t('toxico.stays.readmission_min_date', { date: lastDischargeDate })",
    "t('toxico.stays.already_active')", "t('toxico.stays.checking')", "t('toxico.stays.check_failed')", "t('toxico.stays.retry')",
    'if (props.preselectedPatient?.patient_id) selectExistingPatient(props.preselectedPatient);',
    // champs
    'v-model="form.admissionDate"', ':max="today"', ':min="minAdmissionDate || undefined"', 'v-model="form.substance"', 'value="Alcool"', 'value="Cannabis"', 'value="Opioïdes"', 'value="Cocaïne"',
    'value="Polytoxicomanie"', 'value="Autre"', 'v-model="form.psychologist"', ':value="null" disabled selected', 'v-for="psy in psychologistsList"', ':key="psy.id"', ':value="psy.id"', 'psy.name',
    'v-if="showNewPatientForm"', 'v-model="form.firstName"', 'v-model="form.lastName"', 'v-model="form.dob"', 'v-model="form.mothersName"', 'v-model="form.address"', 'v-model="form.contact"',
    'v-model="form.guardianName"', 'v-model="form.guardianContact"', 'accept=".pdf,.jpg,.png"', '@change="handleFileUpload"', 'v-model="form.notes"',
    // validation du formulaire
    'const isFormValid = computed(() => {', "const dossierOk = !selectedExistingPatient.value || ['none', 'readmission'].includes(dossierCheck.value);",
    'form.firstName.trim() && form.lastName.trim() && form.dob && form.mothersName.trim()', 'form.guardianName.trim() &&', 'form.guardianContact.trim();',
    ':disabled="isLoading || !isFormValid"', '@submit.prevent="handleSubmit"', ':disabled="isLoading"',
    // règles d'envoi
    'if (!isFormValid.value) {', 'if (admissionDate > todayDate) {', "t('toxico.stays.errors.admission_before_discharge', { date: lastDischargeDate.value })", 'if (dobDate > todayDate) {', 'if (dobDate > admissionDate) {',
    'if (isLoading.value) return;', 'psychologist: parseInt(form.psychologist, 10),', 'payload.patientId = selectedExistingPatient.value.patient_id;', 'payload.firstName = form.firstName.trim();',
    'payload.mothersName = form.mothersName.trim();', 'const result = await toxicoStore.addPatient(payload);', 'if (file.size > 5 * 1024 * 1024) {', 'watch(form, () => {',
    // erreurs serveur
    'if (error.response.status === 422) {', 'error.response.status === 409', 'apiErrorMessage(error, t(\'toxico.stays.already_active\'))', 'error.response.status === 400', 'error.response.status === 401', 'else if (error.request) {',
    'v-if="errorMessage"',
    // clés
    "t('toxico.admission.title')", "t('toxico.admission.section_patient')", "t('toxico.admission.date')", "t('toxico.admission.substance')", "t('toxico.admission.psychologist')",
    "t('toxico.admission.firstname')", "t('toxico.admission.lastname')", "t('toxico.admission.dob')", "t('toxico.admission.mothers_name')", "t('toxico.admission.address')", "t('toxico.admission.contact')",
    "t('toxico.admission.section_guardian')", "t('toxico.admission.guardian_name')", "t('toxico.admission.guardian_contact')", "t('toxico.admission.consent_file')",
    "t('toxico.admission.upload_placeholder')", "t('toxico.admission.notes')", "t('toxico.admission.cancel')", "t('toxico.admission.submit')",
    "t('toxico.substances.alcohol')", "t('toxico.substances.cannabis')", "t('toxico.substances.opioids')", "t('toxico.substances.cocaine')", "t('toxico.substances.poly')",
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
test('ToxicoAdmissionModal : panneau accessible, sections, champs étiquetés, barre d actions', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['FullScreenPanel', 'FormSection', 'FormField', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /<FullScreenPanel[^>]*accent/s, 'en-tête coloré');
    assert.match(t, /form="toxico-admission-form"/);
});

test('ToxicoAdmissionModal : résultats de recherche en vrais boutons, bannières annoncées (réadmission orange, déjà actif rouge)', () => {
    const t = templateOf(view);
    assert.match(t, /<button[^>]*@click="selectExistingPatient\(p\)"/s);
    assert.doesNotMatch(t, /<li[^>]*@click="selectExistingPatient/s);
    assert.match(t, /role="status"/);
    assert.match(t, /role="alert"/);
    assert.match(t, /toneClasses\('warning'\)/);
    assert.match(t, /toneClasses\('danger'\)/);
});

test('ToxicoAdmissionModal : la date de naissance a bien son minimum de 10 ans (maxDateFormatted, plus un objet Date)', () => {
    assert.match(templateOf(view), /:max="maxDateFormatted"/);
    assert.doesNotMatch(templateOf(view), /:max="maxDate"/);
    assert.match(scriptOf(view), /const maxDateFormatted = maxDate\.toISOString\(\)\.split\('T'\)\[0\];/);
});

test('ToxicoAdmissionModal : plus aucun texte français en dur dans le gabarit (tout passe par vue-i18n)', () => {
    const t = templateOf(view).replace(/\{\{[^}]*\}\}/g, '').replace(/<!--.*?-->/gs, '');
    for (const bad of ['Rechercher un patient existant', 'Recherche...', 'Nouveau patient', 'Changer', 'Sélectionner', 'Nom de jeune fille', 'Numéro de téléphone', "jusqu'à 5MB", 'Notes supplémentaires', 'Traitement...']) {
        assert.ok(!t.includes(bad), `texte en dur : ${bad}`);
    }
    assert.doesNotMatch(t, />Autre</);
});

test('ToxicoAdmissionModal : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×]|&times;|\p{Extended_Pictographic}/u);
});

test('clés toxicoScreens (admission et sortie) en FR et EN', () => {
    const keys = ['search_existing', 'searching', 'new_patient', 'change_patient', 'select_placeholder', 'substance_other', 'mothers_name_placeholder', 'phone_placeholder', 'file_hint',
        'notes_placeholder', 'processing', 'search_results', 'patient_meta'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].toxicoScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.toxicoScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.toxicoScreens.${k}`);
        }
    }
});
