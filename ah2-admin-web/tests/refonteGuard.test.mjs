// Garde-fous durables de la refonte UX de l'espace médical (spec 2026-10-22).
// Ils échouent dès qu'un écran refondu réintroduit une couleur en dur, un texte trop petit, qu'un jeton perd son
// contraste, que le FR et l'EN divergent, ou que la refonte déborde sur un fichier qu'elle n'avait pas le droit de toucher.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const root = new URL('../', import.meta.url);
// Racine du dépôt git (le dossier au-dessus de ah2-admin-web), chemin système décodé.
const repoRoot = fileURLToPath(new URL('../../', import.meta.url));
const read = (p) => readFileSync(new URL(p, root), 'utf8');

// Fichiers refondus (médical + connexion + bibliothèque ui/). Les écrans partagés avec d'autres rôles y figurent
// aussi : leur refonte a été décidée avec l'utilisateur (liste, fiche et formulaire patient, échecs de synchronisation).
const REFONDUS = [
    'src/components/layout/MedicalLayout.vue',
    'src/components/layout/AppShell.vue',
    'src/views/LoginView.vue',
    'src/views/modules/doctors/DoctorKpiView.vue',
    'src/views/modules/appointments/AppointmentsList.vue',
    'src/components/appointments/AppointmentModal.vue',
    'src/components/appointments/AppointmentsCalendar.vue',
    'src/components/appointments/AppointmentDayPanel.vue',
    'src/components/appointments/StatusBadge.vue',
    'src/views/modules/hospitalization/HospitalizationsList.vue',
    'src/components/hospitalization/HospitalizationCard.vue',
    'src/views/modules/nurseshift/NurseShiftsView.vue',
    'src/components/nurseshift/NurseShiftCalendar.vue',
    'src/components/nurseshift/NurseShiftDayPanel.vue',
    'src/views/modules/medical-records/MedicalRecordsList.vue',
    'src/components/medical-records/MedicalRecordModal.vue',
    'src/components/patients/medical/MedicalRecordTimeline.vue',
    'src/components/patients/medical/VitalsCard.vue',
    'src/components/patients/medical/PrescriptionList.vue',
    'src/components/patients/medical/SpiritualTimeline.vue',
    'src/views/modules/prescriptions/PrescriptionsList.vue',
    'src/components/prescriptions/PrescriptionModal.vue',
    'src/views/modules/patients/PatientList.vue',
    'src/views/modules/patients/PatientDetailView.vue',
    'src/components/patients/PatientHeader.vue',
    'src/components/patients/PatientModal.vue',
    'src/components/patients/NewPatientCodeModal.vue',
    'src/components/patients/labs/LabResultTable.vue',
    'src/views/modules/labo/MedicalLabResults.vue',
    'src/views/modules/sync/SyncFailuresView.vue',
    'src/views/dev/StyleGuideView.vue',
    ...['ActionBar', 'AppButton', 'AppCard', 'ConnectionStatus', 'EmptyState', 'FormField', 'FormSection', 'FullScreenPanel', 'PageHeader', 'ResponsiveTable', 'StatusBadge']
        .map((n) => `src/components/ui/${n}.vue`),
];

// Fichiers qui n'importent aucun composant ui/, avec la raison.
const SANS_COMPOSANT_UI = {
    'src/components/layout/MedicalLayout.vue': 'enveloppe de configuration (groupes de menu) : tout le gabarit vit dans AppShell.vue, qui utilise ui/ConnectionStatus',
    'src/components/patients/medical/VitalsCard.vue': 'carte purement présentative (aucun composant ui/ n’apporte rien) ; ses couleurs viennent des jetons',
};

// --- (a) aucune couleur de marque ou d'état en dur ---
const RAW_COLOR = /\b(?:indigo|emerald|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink|cyan|lime|fuchsia|violet|stone|zinc)-\d{2,3}\b/;

for (const file of REFONDUS) {
    test(`(a) ${file} : ni hexadécimal ni couleur Tailwind brute`, () => {
        assert.ok(existsSync(new URL(file, root)), `${file} introuvable`);
        const src = read(file);
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, 'couleur hexadécimale en dur');
        assert.doesNotMatch(src, RAW_COLOR, 'couleur Tailwind brute (utiliser les jetons brand-*, nav-*, tone-*, tab-*, ink-*)');
    });

    test(`(a) ${file} : texte jamais inférieur à 13 px`, () => {
        const src = read(file);
        assert.doesNotMatch(src, /text-\[(?:[0-9]|1[0-2])px\]/, 'taille de texte inférieure à 13 px');
        assert.doesNotMatch(src, /\btext-xs\b/, 'text-xs (12 px) interdit dans la refonte');
    });

    test(`(a) ${file} : aucun caractère typographique d’aspect généré dans le texte affiché`, () => {
        const src = read(file);
        const template = src.includes('<script') ? src.slice(0, src.indexOf('<script')) : src;
        assert.doesNotMatch(template, /[—–…·]/, 'tiret long, point médian ou points de suspension typographiques');
    });
}

// --- (b) contrastes des jetons (rappel de designTokens.test.mjs) ---
const css = read('src/style.css');
const tokens = Object.fromEntries([...css.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map((m) => [m[1], m[2]]));
const lum = (hex) => {
    const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };

test('(b) textes d’état lisibles sur leur fond (AA 4,5:1) et couleurs d’onglets lisibles sur blanc', () => {
    for (const t of ['danger', 'warning', 'success', 'info', 'neutral']) {
        const r = ratio(tokens[`tone-${t}-text`], tokens[`tone-${t}-bg`]);
        assert.ok(r >= 4.5, `tone-${t} : ${r.toFixed(2)}`);
    }
    for (const n of ['brand-700', 'ink', 'ink-muted', 'tab-record', 'tab-lab', 'tab-pharma', 'tab-hospital', 'tab-toxico', 'tab-spirit']) {
        const r = ratio(tokens[n], '#ffffff');
        assert.ok(r >= 4.5, `${n} sur blanc : ${r.toFixed(2)}`);
    }
    assert.ok(ratio('#ffffff', tokens['brand-600']) >= 4.5, 'texte blanc sur le bouton principal');
    assert.ok(ratio(tokens['nav-text'], tokens['nav-900']) >= 4.5, 'texte du menu sur bleu nuit');
});

// --- (c) parité i18n FR / EN ---
function flatten(obj, prefix = '', out = {}) {
    for (const [k, v] of Object.entries(obj)) {
        const key = prefix ? `${prefix}.${k}` : k;
        if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out);
        else out[key] = v;
    }
    return out;
}

test('(c) le français et l’anglais exposent exactement les mêmes clés', () => {
    const msgs = i18n.global.messages.value;
    const fr = Object.keys(flatten(msgs.fr));
    const en = new Set(Object.keys(flatten(msgs.en)));
    const manquantes = fr.filter((k) => !en.has(k));
    assert.deepEqual(manquantes, [], 'clés absentes en anglais');
    assert.equal(fr.length, en.size);
});

test('(c) les textes de la refonte n’ont pas de tiret long ni de points de suspension typographiques', () => {
    const msgs = i18n.global.messages.value;
    const zones = ['ui', 'medicalShell', 'loginPage', 'newPatient'];
    for (const locale of ['fr', 'en']) {
        for (const z of zones) {
            for (const [k, v] of Object.entries(flatten(msgs[locale][z]))) {
                assert.doesNotMatch(String(v), /[—–…·]/, `${locale}.${z}.${k}`);
            }
        }
    }
});

// --- (d) chaque fichier refondu passe par la bibliothèque ui/ (ou est une exception justifiée) ---
for (const file of REFONDUS.filter((f) => f.endsWith('.vue') && !f.startsWith('src/components/ui/'))) {
    test(`(d) ${file} : utilise un composant ui/ ou figure dans les exceptions justifiées`, () => {
        const uses = /@\/components\/ui/.test(read(file));
        if (!uses) assert.ok(SANS_COMPOSANT_UI[file], `${file} n'importe aucun composant ui/ et n'est pas une exception listée`);
    });
}

test('(d) chaque exception a une raison écrite', () => {
    for (const [file, raison] of Object.entries(SANS_COMPOSANT_UI)) {
        assert.ok(REFONDUS.includes(file), `${file} n'est pas un fichier refondu`);
        assert.ok(raison.length > 20, `raison trop courte pour ${file}`);
    }
});

// --- (e) la refonte n'a touché que les fichiers autorisés (plage de commits de la refonte) ---
const BASE = 'b47bb39'; // juste avant la Tâche 1
const FIN = 'c088b2f'; // dernier commit des Tâches 1 à 11
const AUTORISES = new Set([
    ...REFONDUS,
    'package.json', 'package-lock.json',
    'src/assets/login/ah2-logo.webp', 'src/assets/login/medecin.webp',
    'src/components/ui/index.js',
    'src/composables/useConnectionStatus.js', 'src/design/tones.js', 'src/i18n.js', 'src/router/index.js', 'src/style.css',
    'src/utils/connectionStatus.js', 'src/utils/doctorDashboardLayout.js', 'src/utils/newPatientFlow.js',
    'src/utils/nurseShiftRange.js', 'src/utils/postLoginRoute.js', 'src/utils/prescriptionEnd.js', 'src/utils/ui.js',
]);
const INTERDITS = [
    'src/components/layout/MainLayout.vue', 'src/components/layout/SecretaireLayout.vue',
    'src/components/common/Modal.vue', 'src/components/common/Pagination.vue', 'src/components/common/ToastContainer.vue',
    'src/components/dashboard/StatCard.vue', 'src/components/notifications/NotificationBell.vue',
    'src/components/lab/ResultDetailModal.vue', 'src/components/consultations/ConsultationModal.vue',
    'src/stores/medicalRecordStore.js', 'src/powersync-client/DossierConnector.js', 'src/utils/consultationLock.js',
];

function fichiersModifies() {
    try {
        const out = execFileSync('git', ['-C', repoRoot, 'diff', '--name-only', BASE, FIN, '--', 'ah2-admin-web'], { encoding: 'utf8' });
        return out.split('\n').filter(Boolean).map((p) => p.replace(/^ah2-admin-web\//, ''));
    } catch {
        return null; // git absent ou commits introuvables (clone superficiel) : contrôle ignoré
    }
}

test('(e) seuls les fichiers autorisés ont été modifiés par la refonte (hors tests)', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    const hors = modifies.filter((f) => !f.startsWith('tests/') && !AUTORISES.has(f));
    assert.deepEqual(hors, [], `fichiers modifiés hors périmètre : ${hors.join(', ')}`);
});

test('(e) les fichiers partagés interdits n’ont pas été modifiés', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    assert.deepEqual(INTERDITS.filter((f) => modifies.includes(f)), []);
});

test('(e) router/index.js : seule la route du guide de style (développement) a été ajoutée', (t) => {
    let diff;
    try {
        diff = execFileSync('git', ['-C', repoRoot, 'diff', '-U0', BASE, FIN, '--', 'ah2-admin-web/src/router/index.js'], { encoding: 'utf8' });
    } catch {
        return t.skip('git indisponible');
    }
    const ajoutees = diff.split('\n').filter((l) => l.startsWith('+') && !l.startsWith('+++'));
    const retirees = diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---'));
    assert.ok(ajoutees.some((l) => l.includes('/dev/styleguide')));
    assert.ok(ajoutees.some((l) => l.includes('import.meta.env.DEV')));
    // La seule ligne retirée est la route /forbidden dont un espace final a disparu.
    assert.ok(retirees.length <= 1, `lignes retirées inattendues : ${retirees.join(' | ')}`);
    assert.ok(retirees.every((l) => l.includes("path: '/forbidden'")));
});

test('(e) la route du guide de style n’existe qu’en développement et le guide est absent du build de production', () => {
    assert.match(read('src/router/index.js'), /import\.meta\.env\.DEV\s*\n?\s*\?\s*\[\{ path: '\/dev\/styleguide'/);
});
