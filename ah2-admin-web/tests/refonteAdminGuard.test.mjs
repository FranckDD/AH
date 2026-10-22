// Garde-fous durables de la refonte UX de l'admin et du promoteur (plan 2026-10-22-refonte-ux-admin-promoteur.md).
// Ils échouent dès qu'un écran refondu réintroduit une couleur en dur, un texte trop petit, un caractère interdit,
// que le FR et l'EN divergent, qu'un rôle perd sa palette, ou que la refonte déborde sur un fichier « argent »
// ou sur un écran qu'elle n'avait pas le droit de toucher.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const { NAV_PALETTES, paletteForRole } = await import('../src/design/navPalettes.js');

const root = new URL('../', import.meta.url);
const repoRoot = fileURLToPath(new URL('../../', import.meta.url));
const read = (p) => readFileSync(new URL(p, root), 'utf8');
const templateOf = (src) => (src.includes('<script') ? src.slice(0, src.indexOf('<script')) : src);

// Fichiers refondus pour l'admin et le promoteur (le cadre commun et la bibliothèque ui/ ont leurs propres contrôles).
const REFONDUS = [
    'src/components/layout/MainLayout.vue',
    'src/views/dashboards/DashboardOverview.vue',
    'src/views/modules/finance/FinancialList.vue',
    'src/components/finance/FinanceModal.vue',
    'src/views/modules/caisse/DiscountReview.vue',
    'src/views/modules/caisse/StaffDiscountRules.vue',
];

const SANS_COMPOSANT_UI = {
    'src/components/layout/MainLayout.vue': 'enveloppe de configuration (entrées de menu et rôles) : tout le gabarit vit dans AppShell.vue',
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

    test(`(a) ${file} : aucun emoji ni caractère typographique d’aspect généré dans le texte affiché`, () => {
        assert.doesNotMatch(templateOf(read(file)), /[—–…·]|\p{Extended_Pictographic}/u);
    });
}

// --- (b) la bibliothèque ui/ ---
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

const ZONES = ['adminDashboard', 'financeScreens', 'discountReviewScreens', 'staffDiscountScreens'];

test('(c) le français et l’anglais exposent exactement les mêmes clés', () => {
    const msgs = i18n.global.messages.value;
    const fr = Object.keys(flatten(msgs.fr));
    const en = new Set(Object.keys(flatten(msgs.en)));
    assert.deepEqual(fr.filter((k) => !en.has(k)), [], 'clés absentes en anglais');
    assert.equal(fr.length, en.size);
});

test('(c) les zones de texte de l’admin existent et n’ont ni tiret long ni points de suspension typographiques', () => {
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

// --- (d) la refonte n'a touché que les fichiers autorisés, jamais l'argent ni les données ---
const BASE = 'f050a08'; // juste avant la Tâche 1 de l'admin
// Dernier commit des Tâches 1 à 5. null = arbre de travail (tant que ces tâches ne sont pas commitées) ;
// à renseigner avec le hash du commit pour que les chantiers suivants ne fassent pas échouer ce contrôle.
const FIN = null;

const AUTORISES = new Set([
    ...REFONDUS,
    'src/components/layout/AppShell.vue', // sous-menus, séparateur, palette, dégradé (Tâches 1 et 2)
    'src/utils/sidebarMenu.js', // toShellGroups
    'src/design/navPalettes.css', 'src/design/navPalettes.js', // palettes par rôle
    'src/style.css', 'src/utils/ui.js', // jeton rouge plein et boutons en dégradé
    'src/i18n.js',
]);

const INTERDITS = [
    // argent, données, impression
    'src/stores/financialStore.js', 'src/stores/dashboardStore.js', 'src/services/FinanceGateway.js',
    'src/utils/invoiceTotals.js', 'src/utils/staffDiscount.js', 'src/utils/receiptLines.js',
    'src/stores/caisseStore.js', 'src/services/CaisseGateway.js', 'src/services/PrinterBridgeGateway.js',
    'src/services/StaffDiscountGateway.js', 'src/services/DiscountRequestGateway.js',
    // fichiers partagés et écrans des autres espaces
    'src/router/index.js', 'src/components/dashboard/StatCard.vue', 'src/components/notifications/NotificationBell.vue',
    'src/components/common/Modal.vue', 'src/components/common/Pagination.vue',
    'src/components/toxico/ToxicoAdmissionModal.vue', 'src/components/lab/ResultDetailModal.vue',
    'src/views/modules/users/UserManagement.vue', 'src/views/SystemConfig.vue', 'src/views/modules/tech/SystemLogs.vue',
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

test('(d) argent, données, impression et écrans des autres espaces : intacts', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    assert.deepEqual(INTERDITS.filter((f) => modifies.includes(f)), []);
    assert.deepEqual(modifies.filter((f) => f.startsWith('printer_bridge/')), [], 'printer_bridge/ ne doit pas changer');
});

// --- (e) le cadre commun et les palettes par rôle ---
test('(e) MedicalLayout, SecretaireLayout et MainLayout passent tous par AppShell', () => {
    for (const layout of ['MedicalLayout', 'SecretaireLayout', 'MainLayout']) {
        const src = read(`src/components/layout/${layout}.vue`);
        assert.match(src, /import AppShell from '@\/components\/layout\/AppShell\.vue'/, layout);
        assert.match(src, /<AppShell[\s>]/, layout);
    }
});

test('(e) chaque rôle du cadre partagé a une palette de menu valide, un espace différent a une couleur différente', () => {
    const roles = ['admin', 'promoteur', 'laborantin', 'ToxicoManager', 'Psychologist', 'SpiritualCounsellor', 'Assistant', 'StockController'];
    for (const role of roles) {
        const name = paletteForRole(role);
        assert.notEqual(name, 'night', `${role} doit avoir sa propre palette`);
        assert.ok(NAV_PALETTES[name], `${role} : palette ${name} inconnue`);
    }
    assert.equal(paletteForRole('admin'), paletteForRole('promoteur'));
    const espaces = new Set(['admin', 'laborantin', 'ToxicoManager', 'StockController'].map(paletteForRole));
    assert.equal(espaces.size, 4, 'admin, labo, toxico et stock-control ont chacun leur couleur');
    assert.equal(paletteForRole('medecin'), 'night');
});

test('(e) le menu est un dégradé et les boutons pleins aussi (jamais de couleur unie par oubli)', () => {
    assert.match(read('src/components/layout/AppShell.vue'), /bg-linear-to-br from-nav-900 to-nav-700/);
    assert.match(read('src/utils/ui.js'), /primary: '[^']*bg-linear-to-br/);
});
