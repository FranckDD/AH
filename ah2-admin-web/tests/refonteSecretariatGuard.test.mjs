// Garde-fous durables de la refonte UX du secrétariat (plan 2026-10-22-refonte-ux-secretariat.md).
// Ils échouent dès qu'un écran refondu réintroduit une couleur en dur, un texte trop petit, un caractère interdit,
// que le FR et l'EN divergent, qu'AppShell cesse d'être le cadre commun, ou que la refonte déborde sur un fichier
// « argent » ou sur un fichier qu'elle n'avait pas le droit de toucher.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const root = new URL('../', import.meta.url);
const repoRoot = fileURLToPath(new URL('../../', import.meta.url));
const read = (p) => readFileSync(new URL(p, root), 'utf8');
const templateOf = (src) => (src.includes('<script') ? src.slice(0, src.indexOf('<script')) : src);

// Fichiers refondus pour le secrétariat (les composants ui/ et l'espace médical ont leur propre garde-fou).
const REFONDUS = [
    'src/components/layout/AppShell.vue',
    'src/components/layout/SecretaireLayout.vue',
    'src/components/ui/StatTile.vue',
    'src/views/modules/secretariat/SecretariatHomeView.vue',
    'src/views/modules/stock/StockList.vue',
    'src/components/stock/ProductModal.vue',
    'src/components/stock/AdjustmentRequestModal.vue',
    'src/views/modules/consultations/ConsultationsList.vue',
    'src/components/consultations/ConsultationModal.vue',
    'src/views/modules/caisse/DiscountRequestsHistory.vue',
    'src/views/modules/finance/CaisseList.vue',
    'src/components/caisse/CaisseInvoiceModal.vue',
    'src/components/caisse/CaisseCancelModal.vue',
    'src/components/caisse/CaisseInstallmentModal.vue',
    'src/views/modules/finance/RetraitList.vue',
    'src/components/caisse/RetraitModal.vue',
    'src/views/modules/sync/SyncFailuresView.vue',
];

// Fichiers qui n'importent aucun composant ui/, avec la raison.
const SANS_COMPOSANT_UI = {
    'src/components/layout/SecretaireLayout.vue': 'enveloppe de configuration (groupes de menu) : tout le gabarit vit dans AppShell.vue, qui utilise ui/ConnectionStatus',
    'src/components/layout/AppShell.vue': 'le cadre est lui-même la brique commune ; il embarque ConnectionStatus directement et ne passe pas par l’index ui/',
    'src/components/ui/StatTile.vue': 'composant de la bibliothèque ui/ lui-même',
};

// --- (a) couleurs, taille du texte, caractères ---
const RAW_COLOR = /\b(?:indigo|emerald|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink|cyan|lime|fuchsia|violet|stone|zinc)-\d{2,3}\b/;

for (const file of REFONDUS) {
    test(`(a) ${file} : ni hexadécimal ni couleur Tailwind brute`, () => {
        assert.ok(existsSync(new URL(file, root)), `${file} introuvable`);
        const src = read(file);
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, 'couleur hexadécimale en dur');
        assert.doesNotMatch(src, RAW_COLOR, 'couleur Tailwind brute (utiliser les jetons)');
    });

    test(`(a) ${file} : texte jamais inférieur à 13 px`, () => {
        const src = read(file);
        assert.doesNotMatch(src, /text-\[(?:[0-9]|1[0-2])px\]/);
        assert.doesNotMatch(src, /\btext-xs\b/);
    });

    test(`(a) ${file} : aucun caractère typographique d’aspect généré dans le texte affiché`, () => {
        assert.doesNotMatch(templateOf(read(file)), /[—–…·]/);
    });
}

// --- (b) chaque fichier refondu passe par la bibliothèque ui/ (ou est une exception justifiée) ---
for (const file of REFONDUS) {
    test(`(b) ${file} : utilise un composant ui/ ou figure dans les exceptions justifiées`, () => {
        if (!/@\/components\/ui/.test(read(file))) assert.ok(SANS_COMPOSANT_UI[file], `${file} n'importe aucun composant ui/ et n'est pas une exception listée`);
    });
}

test('(b) chaque exception a une raison écrite', () => {
    for (const [file, raison] of Object.entries(SANS_COMPOSANT_UI)) {
        assert.ok(REFONDUS.includes(file), `${file} n'est pas un fichier refondu`);
        assert.ok(raison.length > 20, `raison trop courte pour ${file}`);
    }
});

// --- (c) textes ajoutés : FR et EN identiques, sans caractère interdit ---
function flatten(obj, prefix = '', out = {}) {
    for (const [k, v] of Object.entries(obj)) {
        const key = prefix ? `${prefix}.${k}` : k;
        if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out);
        else out[key] = v;
    }
    return out;
}

const ZONES = ['secretariatShell', 'secretariatHome', 'stockScreens', 'consultationsScreens', 'discountScreens', 'caisseScreens', 'caisseInvoice', 'retraitScreens', 'syncFailures'];

test('(c) le français et l’anglais exposent exactement les mêmes clés', () => {
    const msgs = i18n.global.messages.value;
    const fr = Object.keys(flatten(msgs.fr));
    const en = new Set(Object.keys(flatten(msgs.en)));
    assert.deepEqual(fr.filter((k) => !en.has(k)), [], 'clés absentes en anglais');
    assert.equal(fr.length, en.size);
});

test('(c) les zones de texte du secrétariat existent et n’ont ni tiret long ni points de suspension typographiques', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        for (const z of ZONES) {
            assert.ok(msgs[locale][z], `${locale}.${z} absente`);
            for (const [k, v] of Object.entries(flatten(msgs[locale][z]))) {
                assert.doesNotMatch(String(v), /[—–…·]/, `${locale}.${z}.${k}`);
            }
        }
    }
});

// --- (d) la refonte n'a touché que les fichiers autorisés, et jamais l'argent ni l'impression ---
const BASE = 'da31771'; // juste avant la Tâche 1 du secrétariat
// Dernier commit des Tâches 1 à 9 (a79235f). null = arbre de travail ;
// renseigné pour que les chantiers suivants ne fassent pas échouer ce contrôle.
const FIN = 'a79235f';

const AUTORISES = new Set([
    ...REFONDUS,
    'src/components/ui/index.js', 'src/components/ui/FormSection.vue', 'src/components/ui/FullScreenPanel.vue', 'src/components/ui/ResponsiveTable.vue',
    'src/components/layout/MedicalLayout.vue', // reprise sur AppShell (Tâche 1)
    'src/components/patients/NewPatientCodeModal.vue', 'src/views/modules/patients/PatientList.vue', 'src/utils/newPatientFlow.js', // code du patient créé par la secrétaire
    'src/powersync-client/syncQuarantine.js', 'src/utils/quarantinePatient.js', // suppression et correction du numéro d'identité en quarantaine
    'src/components/common/ToastContainer.vue', 'src/stores/toastStore.js', // notification d'échec d'impression du ticket (demande de l'utilisateur)
    'src/i18n.js', 'src/utils/ui.js',
]);

const INTERDITS = [
    'src/utils/invoiceTotals.js', 'src/utils/staffDiscount.js', 'src/utils/receiptLines.js',
    'src/stores/caisseStore.js', 'src/services/CaisseGateway.js', 'src/services/PrinterBridgeGateway.js',
    'src/components/layout/MainLayout.vue', 'src/components/dashboard/StatCard.vue', 'src/components/notifications/NotificationBell.vue',
    'src/components/common/Modal.vue', 'src/components/common/Pagination.vue', 'src/components/lab/ResultDetailModal.vue',
    'src/stores/medicalRecordStore.js', 'src/powersync-client/DossierConnector.js',
];

function fichiersModifies() {
    try {
        const args = ['-C', repoRoot, 'diff', '--name-only', BASE, ...(FIN ? [FIN] : []), '--', 'ah2-admin-web', 'printer_bridge'];
        const out = execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
        return out.split('\n').filter(Boolean).map((p) => p.replace(/^ah2-admin-web\//, ''));
    } catch {
        return null; // git absent ou commits introuvables (clone superficiel) : contrôle ignoré
    }
}

test('(d) seuls les fichiers autorisés ont été modifiés par la refonte (hors tests)', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    const hors = modifies.filter((f) => !f.startsWith('tests/') && !AUTORISES.has(f));
    assert.deepEqual(hors, [], `fichiers modifiés hors périmètre : ${hors.join(', ')}`);
});

test('(d) argent, impression et fichiers partagés interdits : intacts', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    assert.deepEqual(INTERDITS.filter((f) => modifies.includes(f)), []);
    assert.deepEqual(modifies.filter((f) => f.startsWith('printer_bridge/')), [], 'printer_bridge/ ne doit pas changer');
});

// --- (e) le cadre commun ---
test('(e) MedicalLayout et SecretaireLayout passent tous deux par AppShell', () => {
    for (const layout of ['src/components/layout/MedicalLayout.vue', 'src/components/layout/SecretaireLayout.vue']) {
        const src = read(layout);
        assert.match(src, /import AppShell from '@\/components\/layout\/AppShell\.vue'/, layout);
        assert.match(src, /<AppShell\b/, layout);
    }
});

test('(e) les écrans refondus de la caisse gardent le panneau et les composants ui/ (pas de retour aux anciennes surcouches)', () => {
    for (const f of ['src/components/caisse/CaisseInvoiceModal.vue', 'src/components/caisse/CaisseCancelModal.vue',
        'src/components/caisse/CaisseInstallmentModal.vue', 'src/components/caisse/RetraitModal.vue']) {
        assert.match(read(f), /FullScreenPanel/, f);
        assert.doesNotMatch(templateOf(read(f)), /fixed inset-0/, `${f} : surcouche en dur`);
    }
});
