import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/toxico/ToxicoPatientDetailsModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : détails d'un patient toxicologie (identité, contact, admission, tuteur, notes) ---
check('ToxicoPatientDetailsModal', view, [
    // interface avec la liste
    'const props = defineProps({', 'default: () => ({})', "defineEmits(['close', 'open-dossier'])",
    "if (props.patient?.patient_id) {", "emit('open-dossier', props.patient.patient_id);", "emit('close');", '@click="openDossier"', "@click=\"$emit('close')\"", 'v-if="patient"',
    // formats
    "return formatDateDMY(dateString);", "import { formatDateDMY } from '@/utils/localDate';", 'if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {', 'age--;',
    // consentement : chargement authentifie (plus de lien /static public)
    "api.get(`/toxico/dossiers/${dossierId}/consent`, { responseType: 'blob' })", 'URL.createObjectURL', 'URL.revokeObjectURL',
    // identité
    'patient.firstName || patient.first_name', 'patient.lastName || patient.last_name', 'formatDate(patient.dob)', 'calculateAge(patient.dob)', 'patient.mothersName || patient.mothers_name', 'patient.code',
    // contact
    'patient.address', 'patient.contact', 'patient.substance',
    // admission
    'formatDate(patient.admissionDate || patient.admission_date)', 'patient.psychologist', 'patient.currentPhase || 1', 'patient.relapseCount > 0',
    // tuteur et consentement
    'patient.guardianName || patient.guardian_name', 'patient.guardianContact || patient.guardian_contact', 'patient.consentFile || patient.consent_file',
    '@click="openConsent"',
    // notes et pied de page
    'v-if="patient.notes"', 'patient.notes', 'patient?.createdAt || new Date().toISOString()',
]);

// --- Refonte (rouge tant que non refondu) ---
test('ToxicoPatientDetailsModal : panneau accessible, champs en liste de définitions, barre d actions', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['FullScreenPanel', 'StatusBadge', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /<FullScreenPanel[^>]*accent/s);
    assert.match(t, /<dl\b/);
    assert.match(t, /<dt\b/);
    assert.match(t, /<dd\b/);
    assert.doesNotMatch(t, /<label/, 'les intitulés ne sont pas des étiquettes de champ');
});

test('ToxicoPatientDetailsModal : mêmes couleurs de sections qu avant (bleu, vert, indigo, orange) via les jetons, titre toujours écrit', () => {
    const t = templateOf(view);
    for (const cls of ['text-tone-info-text', 'text-tone-success-text', 'text-action-700', 'text-tone-warning-text']) assert.ok(t.includes(cls) || view.includes(cls), cls);
    assert.match(t, /aria-labelledby/);
    assert.match(view, /phaseMeta\(/);
});

test('ToxicoPatientDetailsModal : phase et rechutes dites par un mot, une icône et un nombre (plus d emoji)', () => {
    const t = templateOf(view);
    assert.match(t, /<StatusBadge/);
    assert.match(t, /ExclamationTriangleIcon|<ExclamationTriangleIcon/);
    assert.doesNotMatch(t, /[⚠]|\p{Extended_Pictographic}/u);
});

test('ToxicoPatientDetailsModal : consentement ouvert via fetch authentifie, jamais par un lien /static', () => {
    const t = templateOf(view);
    assert.doesNotMatch(view, /\/static\/|API_BASE_URL/);
    assert.match(view, /noopener/);
    assert.match(t, /min-h-11/);
});

test('ToxicoPatientDetailsModal : plus aucun texte français en dur dans le gabarit', () => {
    const t = templateOf(view).replace(/\{\{[^}]*\}\}/g, '').replace(/<!--.*?-->/gs, '');
    for (const bad of ['Détails du Patient', "Informations d'admission", 'Identité', 'Prénom', 'Date de naissance', 'Code patient', 'Adresse', 'Tuteur légal', 'Télécharger le document',
        'Aucun fichier joint', 'Notes additionnelles', 'Ouvrir le dossier complet', 'Dossier créé le', 'Aucune information']) {
        assert.ok(!t.includes(bad), `texte en dur : ${bad}`);
    }
    assert.doesNotMatch(templateOf(view), /'Non renseign|'Non assign|'Non sp[ée]cifi/);
});

test('ToxicoPatientDetailsModal : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×&]|&times;|\p{Extended_Pictographic}/u);
});

test('clés toxicoScreens (détails du patient) en FR et EN', () => {
    const keys = ['details_modal_title', 'details_modal_subtitle', 'section_identity', 'section_contact', 'section_admission', 'section_guardian', 'section_notes', 'f_firstname', 'f_lastname', 'f_dob', 'f_age',
        'f_mother', 'f_code', 'f_address', 'f_phone', 'f_substance', 'f_admission_date', 'f_psychologist', 'f_status', 'f_guardian_name', 'f_guardian_contact', 'f_consent', 'not_provided', 'not_provided_f',
        'not_assigned', 'not_specified_f', 'file_download', 'file_none', 'file_error', 'no_patient', 'created_on', 'open_full_dossier', 'years', 'close'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].toxicoScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.toxicoScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.toxicoScreens.${k}`);
        }
    }
});
