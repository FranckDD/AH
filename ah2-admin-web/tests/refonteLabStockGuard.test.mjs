// Garde-fous durables de la refonte UX du stock du laboratoire (plan 2026-10-22-refonte-ux-stock-labo.md).
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

const DIR = 'src/views/modules/labstock/';
const REFONDUS = [
    'LabStockProducts.vue', 'LabStockRequests.vue', 'LabStockReceipts.vue', 'LabStockReceiptForm.vue',
    'LabStockCount.vue', 'LabStockAlerts.vue', 'LabStockMovements.vue', 'LabStockExpenses.vue',
].map((f) => DIR + f);

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
        assert.doesNotMatch(templateOf(read(file)), /[—–…·•‹›→]|\p{Extended_Pictographic}/u);
    });

    test(`(b) ${file} : utilise la bibliothèque ui/ et plus aucune surcouche en dur`, () => {
        const src = read(file);
        assert.match(src, /@\/components\/ui/);
        assert.doesNotMatch(templateOf(src), /fixed inset-0/);
    });
}

// --- (c) textes ajoutés : FR et EN identiques, sans caractère interdit ---
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
    assert.deepEqual(fr.filter((k) => !en.has(k)), [], 'clés absentes en anglais');
    assert.equal(fr.length, en.size);
});

test('(c) la zone labStockScreens existe et n’a ni tiret long ni points de suspension typographiques', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        assert.ok(msgs[locale].labStockScreens, `${locale}.labStockScreens absente`);
        for (const [k, v] of Object.entries(flatten(msgs[locale].labStockScreens))) {
            assert.doesNotMatch(String(v), /[—–…·]/, `${locale}.labStockScreens.${k}`);
        }
    }
});

// --- (d) la refonte n'a touché que les fichiers autorisés, jamais les données ni les règles de stock ---
const BASE = '5aa9b88'; // juste avant la Tâche 1 de ce lot
// Dernier commit de ce lot. null = arbre de travail ; à renseigner au commit
// pour que les chantiers suivants ne fassent pas échouer ce contrôle.
const FIN = null;

const AUTORISES = new Set([...REFONDUS, 'src/i18n.js']);

// Modifications faites en parallèle, à la demande de l'utilisateur, hors de ce lot
// (rechargement après erreur de chargement, variante de bouton « brand », connexion, tableau de bord).
const HORS_LOT = new Set([
    'src/router/index.js', 'src/utils/ui.js', 'src/views/LoginView.vue', 'src/views/dashboards/DashboardOverview.vue',
]);

const INTERDITS = [
    'src/services/LabStockGateway.js', 'src/utils/labCount.js', 'src/utils/labReceiptLines.js', 'src/utils/labStockExpenses.js',
    'src/utils/labStockLabels.js', 'src/utils/localDate.js', 'src/services/api.js',
    'src/components/layout/MainLayout.vue', 'src/components/layout/AppShell.vue',
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

test('(d) seuls les fichiers autorisés ont été modifiés par ce lot (hors tests)', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    const hors = modifies.filter((f) => !f.startsWith('tests/') && !AUTORISES.has(f) && !HORS_LOT.has(f));
    assert.deepEqual(hors, [], `fichiers modifiés hors périmètre : ${hors.join(', ')}`);
});

test('(d) passerelle, règles de stock, API, cadre : intacts', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    assert.deepEqual(INTERDITS.filter((f) => modifies.includes(f)), []);
});
