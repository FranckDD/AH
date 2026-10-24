// Garde-fous durables de la cloture de caisse (plan 2026-10-23-cloture-caisse.md, tache 11).
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

const SCREENS = ['src/views/modules/caisse/CashClosure.vue', 'src/views/modules/caisse/CashClosuresReview.vue'];
const NOUVEAUX = [
    ...SCREENS,
    'src/services/CashClosureGateway.js',
    'src/stores/cashClosureStore.js',
    'src/utils/paymentModes.js',
    'src/utils/cashClosure.js',
];

// --- (a) couleurs, taille du texte, caracteres, bibliotheque ui/ ---
const RAW_COLOR = /\b(?:indigo|emerald|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink|cyan|lime|fuchsia|violet|stone|zinc)-\d{2,3}\b/;
const RAW_FUNC_COLOR = /\b(?:rgba?|hsla?)\(/;
const ARBITRARY_COLOR = /\b(?:bg|text|border|ring|from|to|via|fill|stroke)-\[(?:#|rgb|hsl)/;

for (const file of NOUVEAUX) {
    test(`(a) ${file} : ni hexadecimal ni couleur brute`, () => {
        assert.ok(existsSync(new URL(file, root)), `${file} introuvable`);
        const src = read(file);
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, 'couleur hexadecimale en dur');
        assert.doesNotMatch(src, RAW_COLOR, 'couleur Tailwind brute (utiliser les jetons)');
        assert.doesNotMatch(src, RAW_FUNC_COLOR, 'rgb/hsl en dur');
        assert.doesNotMatch(src, ARBITRARY_COLOR, 'couleur arbitraire Tailwind');
    });

    test(`(a) ${file} : texte jamais inferieur a 13 px`, () => {
        const src = read(file);
        assert.doesNotMatch(src, /text-\[(?:[0-9]|1[0-2])px\]/);
        assert.doesNotMatch(src, /\btext-xs\b/);
    });

    test(`(a) ${file} : aucun caractere typographique d'aspect genere`, () => {
        const src = file.endsWith('.vue')
            ? templateOf(read(file)).replace(/<!--.*?-->/gs, '')
            : read(file).replace(/\/\/.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '');
        assert.doesNotMatch(src, /[—–…·•‹›→✓×]|&times;|&rarr;|\p{Extended_Pictographic}/u);
    });

    test(`(dates) ${file} : pas de toISOString`, () => {
        assert.doesNotMatch(read(file), /toISOString/, 'utiliser une date locale');
    });
}

for (const file of SCREENS) {
    test(`(a) ${file} : utilise la bibliotheque ui/ et aucune surcouche en dur`, () => {
        const src = read(file);
        assert.match(src, /@\/components\/ui/);
        assert.doesNotMatch(templateOf(src), /fixed inset-0/);
        assert.doesNotMatch(src, /@apply/);
    });
}

// --- (b) textes : FR et EN identiques, sans caractere interdit ---
function flatten(obj, prefix = '', out = {}) {
    for (const [k, v] of Object.entries(obj)) {
        const key = prefix ? `${prefix}.${k}` : k;
        if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out);
        else out[key] = v;
    }
    return out;
}

for (const zone of ['cashClosure', 'paymentModes']) {
    test(`(b) ${zone} existe en FR et EN, memes cles, sans caractere interdit`, () => {
        const msgs = i18n.global.messages.value;
        const zones = {};
        for (const locale of ['fr', 'en']) {
            assert.ok(msgs[locale][zone], `${locale}.${zone} absente`);
            zones[locale] = flatten(msgs[locale][zone]);
            assert.ok(Object.keys(zones[locale]).length > 0);
            for (const [k, v] of Object.entries(zones[locale])) {
                assert.equal(typeof v, 'string', `${locale}.${zone}.${k}`);
                assert.doesNotMatch(v, /[—–…·•→]|\p{Extended_Pictographic}/u, `${locale}.${zone}.${k}`);
            }
        }
        assert.deepEqual(Object.keys(zones.fr).sort(), Object.keys(zones.en).sort());
    });
}

test('(b) toutes les cles cashClosure.* et paymentModes.* citees par les fichiers existent en FR et EN', () => {
    const msgs = i18n.global.messages.value;
    const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
    const used = new Set();
    for (const file of NOUVEAUX) {
        for (const m of read(file).matchAll(/['"`(]((?:cashClosure|paymentModes)\.[a-zA-Z_]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 30, `seulement ${used.size} cles citees`);
    for (const k of used) {
        for (const locale of ['fr', 'en']) assert.equal(typeof pick(msgs[locale], k), 'string', `${locale}.${k} manquante`);
    }
});

// --- (c) perimetre : le chantier n'a touche que les fichiers prevus ---
// BASE : dernier commit AVANT ce chantier. FIN : null = arbre de travail (le chantier n'est pas encore commite).
// Au commit du chantier, renseigner FIN avec le hash du dernier commit du lot (commit separe), pour que les
// chantiers suivants ne fassent pas echouer ce controle ; les fichiers non suivis ne figurent pas dans `git diff`,
// d'ou le controle d'emplacement ci-dessous (qui ne tourne que tant que FIN est null).
const BASE = 'b6c6e09';
const FIN = null;

const AUTORISES = new Set([
    'src/i18n.js',                                          // cashClosure.*, paymentModes.*, libelles
    'src/router/index.js',                                  // routes cash-closure, cash-closures
    'src/components/layout/MainLayout.vue',                 // entrees de menu promoteur/admin
    'src/components/layout/SecretaireLayout.vue',           // entree de menu secretaire
    'src/components/caisse/RetraitModal.vue',               // mode obligatoire des retraits
    'src/components/caisse/CaisseInvoiceModal.vue',         // liste officielle des modes
    'src/components/caisse/CaisseInstallmentModal.vue',     // liste officielle des modes
    'src/components/notifications/NotificationBell.vue',    // libelle du mode sur le ticket
    'src/views/modules/finance/CaisseList.vue',             // libelle du mode sur le ticket
    'src/views/modules/finance/FinancialList.vue',          // libelle du mode
    'src/components/finance/FinanceModal.vue',              // liste officielle des modes (saisie manuelle)
    'src/views/modules/finance/RetraitList.vue',            // libelle du mode
    'src/powersync-client/DossierConnector.js',             // retrait refuse : message visible
    'src/views/modules/caisse/DiscountRequestsHistory.vue', // date locale (bug toISOString)
    'src/stores/caisseStore.js',                            // date locale par defaut des filtres
    'src/components/stock/ProductModal.vue',                // prix decimal accepte (step="any"), verrou prix catalogue
    'src/services/FabricationGateway.js',                   // sorties declarees : declarer, annuler, lister
    'src/views/modules/fabrication/FabLotDetail.vue',       // sorties declarees : section de la fiche du lot
    'src/views/modules/fabrication/FabSuivi.vue',           // sorties declarees : panneau du suivi, ecart expedie/recu
]);

// Fonction pure : les fichiers modifies qui sortent de la liste prevue.
export function horsPerimetre(liste) {
    return liste.filter((f) => !f.startsWith('tests/') && !AUTORISES.has(f) && !NOUVEAUX.includes(f));
}

function fichiersModifies() {
    try {
        const args = ['-C', repoRoot, 'diff', '--name-only', BASE, ...(FIN ? [FIN] : []), '--', 'ah2-admin-web'];
        const out = execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
        return out.split('\n').filter(Boolean).map((p) => p.replace(/^ah2-admin-web\//, ''));
    } catch {
        return null; // git absent ou commit introuvable (clone superficiel) : controle ignore
    }
}

test('(c) horsPerimetre rejette un fichier hors liste et accepte la liste prevue', () => {
    assert.deepEqual(horsPerimetre(['src/views/modules/stock/StockList.vue']), ['src/views/modules/stock/StockList.vue']);
    assert.deepEqual(horsPerimetre(['src/i18n.js', 'tests/x.test.mjs', ...NOUVEAUX]), []);
    // sorties declarees : les fichiers Fabrication prevus passent, un autre ecran Fabrication non
    assert.deepEqual(horsPerimetre(['src/views/modules/fabrication/FabSuivi.vue', 'src/views/modules/fabrication/FabLotDetail.vue', 'src/services/FabricationGateway.js']), []);
    assert.deepEqual(horsPerimetre(['src/views/modules/fabrication/FabLots.vue']), ['src/views/modules/fabrication/FabLots.vue']);
});

test('(c) seuls les fichiers prevus ont ete modifies', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commit de depart indisponible');
    const hors = horsPerimetre(modifies);
    assert.deepEqual(hors, [], `fichiers modifies hors perimetre : ${hors.join(', ')}`);
});

test('(c) les fichiers nouveaux vivent tous aux emplacements prevus', () => {
    if (FIN) return; // chantier commite : les fichiers non suivis appartiennent a un chantier suivant
    const out = (() => {
        try {
            return execFileSync('git', ['-C', repoRoot, 'ls-files', '--others', '--exclude-standard', '--', 'ah2-admin-web/src'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
        } catch { return null; }
    })();
    if (out === null) return;
    const nouveaux = out.split('\n').filter(Boolean).map((p) => p.replace(/^ah2-admin-web\//, ''));
    const hors = nouveaux.filter((f) => !NOUVEAUX.includes(f));
    assert.deepEqual(hors, [], `fichiers nouveaux hors emplacement : ${hors.join(', ')}`);
});
