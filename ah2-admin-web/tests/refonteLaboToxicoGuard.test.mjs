// Garde-fous durables de la refonte UX du laboratoire et de la toxicologie (plan 2026-10-23-refonte-ux-labo-toxico.md).
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

const LABO = [
    'src/views/modules/labo/LabLayout.vue', 'src/views/dashboards/LabDashboard.vue', 'src/views/modules/labo/LabReception.vue', 'src/views/modules/labo/LabTechnician.vue',
    'src/views/modules/labo/LabHistory.vue', 'src/views/modules/labo/LabConfig.vue', 'src/components/lab/ResultDetailModal.vue', 'src/components/lab/LabPassageCard.vue',
    'src/components/lab/LabHistoryPassage.vue',
];
const TOXICO = [
    'src/views/dashboards/ToxicoDashboard.vue', 'src/views/modules/toxico/ToxicoList.vue', 'src/components/toxico/ToxicoAdmissionModal.vue', 'src/components/toxico/ToxicoDischargeModal.vue',
    'src/components/toxico/ToxicoDossierModal.vue', 'src/components/toxico/ToxicoPatientDetailsModal.vue', 'src/components/toxico/ToxicoEvaluationModal.vue',
    'src/components/toxico/ToxicoDischargedPanel.vue', 'src/components/toxico/ToxicoStaysTimeline.vue',
];
const REFONDUS = [...LABO, ...TOXICO];

// Cadre de navigation : n'utilise que les jetons du thème et des liens, aucun composant de la bibliothèque.
const CADRE = new Set(['src/views/modules/labo/LabLayout.vue']);

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
        assert.doesNotMatch(templateOf(read(file)).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×]|&times;|&rarr;|\p{Extended_Pictographic}/u);
    });

    test(`(b) ${file} : utilise la bibliothèque ui/ et plus aucune surcouche en dur`, () => {
        const src = read(file);
        if (!CADRE.has(file)) assert.match(src, /@\/components\/ui/);
        assert.doesNotMatch(templateOf(src), /fixed inset-0/);
        assert.doesNotMatch(src, /@apply/);
    });
}

// --- (b) panneaux : les fenêtres passent toutes par FullScreenPanel (Échap, focus piégé et rendu) ---
const PANNEAUX = [
    'src/components/lab/ResultDetailModal.vue', 'src/components/toxico/ToxicoAdmissionModal.vue', 'src/components/toxico/ToxicoDischargeModal.vue', 'src/components/toxico/ToxicoDossierModal.vue',
    'src/components/toxico/ToxicoPatientDetailsModal.vue', 'src/components/toxico/ToxicoEvaluationModal.vue',
];
for (const file of PANNEAUX) {
    test(`(b) ${file} : s’ouvre dans un FullScreenPanel`, () => {
        assert.match(templateOf(read(file)), /<FullScreenPanel/);
    });
}

test('(b) la fenêtre de sortie reste à côté du dossier, jamais dedans (pièges de focus indépendants)', () => {
    assert.match(templateOf(read('src/components/toxico/ToxicoDossierModal.vue')), /<\/FullScreenPanel>\s*<ToxicoDischargeModal/);
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

test('(c) le français et l’anglais exposent exactement les mêmes clés', () => {
    const msgs = i18n.global.messages.value;
    const fr = Object.keys(flatten(msgs.fr));
    const en = new Set(Object.keys(flatten(msgs.en)));
    assert.deepEqual(fr.filter((k) => !en.has(k)), [], 'clés absentes en anglais');
    assert.equal(fr.length, en.size);
});

for (const zone of ['labScreens', 'toxicoScreens']) {
    test(`(c) la zone ${zone} existe et n’a ni tiret long, ni points de suspension, ni point médian typographiques`, () => {
        const msgs = i18n.global.messages.value;
        for (const locale of ['fr', 'en']) {
            assert.ok(msgs[locale][zone], `${locale}.${zone} absente`);
            for (const [k, v] of Object.entries(flatten(msgs[locale][zone]))) {
                assert.doesNotMatch(String(v), /[—–…·→]/, `${locale}.${zone}.${k}`);
            }
        }
    });
}

test('(c) toutes les clés labScreens.* et toxicoScreens.* citées par ces fichiers existent en FR et EN', () => {
    const msgs = i18n.global.messages.value;
    const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
    const used = new Set();
    for (const file of REFONDUS) {
        for (const m of read(file).matchAll(/['"`(]((?:labScreens|toxicoScreens)\.[a-zA-Z_]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 80, `seulement ${used.size} clés citées`);
    for (const k of used) {
        for (const locale of ['fr', 'en']) assert.equal(typeof pick(msgs[locale], k), 'string', `${locale}.${k} manquante`);
    }
});

// --- (d) la refonte n'a touché que les fichiers autorisés, jamais les données ni les règles métier ---
const BASE = '9e52fd8'; // juste avant la Tâche 1 de ce lot (garde-fou du stock labo)
// Dernier commit de ce lot. null = arbre de travail ; à renseigner au commit
// pour que les chantiers suivants ne fassent pas échouer ce contrôle.
const FIN = null;

// Anciens ecrans orphelins supprimes avec l'accord de l'utilisateur (jamais references : ni route, ni import).
const SUPPRIMES = ['src/views/modules/labo/LabWorklist.vue', 'src/views/modules/labo/LabEntry.vue'];

const AUTORISES = new Set([
    ...REFONDUS,
    ...SUPPRIMES,
    'src/i18n.js',
    'src/style.css',                                // jetons pleins des barres (orange, bleu, vert)
    'src/utils/ui.js',                              // taille de bouton compacte `sm`
    'src/components/ui/FullScreenPanel.vue',        // en-tête teinté (`tone`), focus sans défilement
    'src/utils/labPassages.js', 'src/utils/toxicoUi.js',
    'src/services/labGateway.js', 'src/stores/labStore.js', // PDF du dossier complet, regroupement hors ligne, pagination par passage
]);

// Modifications faites en parallèle, à la demande de l'utilisateur, hors de ce lot (commit 167e6af).
const HORS_LOT = new Set(['src/router/index.js', 'src/views/LoginView.vue', 'src/views/dashboards/DashboardOverview.vue']);

const INTERDITS = [
    'src/services/ToxicoGateway.js', 'src/stores/toxicoStore.js', 'src/utils/toxicoStays.js', 'src/utils/toxicoDischarged.js', 'src/utils/toxicoExport.js',
    'src/services/api.js', 'src/stores/auth.js', 'src/stores/configStore.js',
    'src/components/layout/MainLayout.vue', 'src/components/layout/AppShell.vue',
    'src/views/modules/labo/MedicalLabResults.vue', 'src/views/modules/labo/LabValidation.vue',
    'src/utils/labCount.js', 'src/utils/labReceiptLines.js', 'src/services/LabStockGateway.js',
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

test('(d) magasin et passerelle de la toxicologie, règles métier, droits, cadre et écrans déjà refaits : intacts', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    assert.deepEqual(INTERDITS.filter((f) => modifies.includes(f)), []);
});

test('(d) LabWorklist et LabEntry sont supprimés et plus référencés nulle part', () => {
    for (const f of SUPPRIMES) assert.ok(!existsSync(new URL(f, root)), `${f} existe encore`);
    const grep = (name) => {
        try {
            return execFileSync('git', ['-C', repoRoot, 'grep', '-l', name, '--', 'ah2-admin-web/src'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).split(String.fromCharCode(10)).filter(Boolean);
        } catch { return []; }
    };
    assert.deepEqual(grep('LabWorklist'), []);
    assert.deepEqual(grep('LabEntry'), []);
});
