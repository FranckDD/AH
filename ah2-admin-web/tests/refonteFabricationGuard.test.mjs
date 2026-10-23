// Garde-fous durables du module Fabrication (plan 2026-10-23-fabrication-production.md).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const root = new URL('../', import.meta.url);
const repoRoot = fileURLToPath(new URL('../../', import.meta.url));
const read = (p) => readFileSync(new URL(p, root), 'utf8');
const templateOf = (src) => (src.includes('<script') ? src.slice(0, src.indexOf('<script')) : src);

const VIEWS_DIR = 'src/views/modules/fabrication/';
const COMPONENTS_DIR = 'src/components/fabrication/';
const GATEWAY = 'src/services/FabricationGateway.js';

const listVue = (dir) => (existsSync(new URL(dir, root)) ? readdirSync(new URL(dir, root)).filter((f) => f.endsWith('.vue')).map((f) => dir + f) : []);
const FABRICATION = [
    VIEWS_DIR + 'FabIntrants.vue', VIEWS_DIR + 'FabLots.vue', VIEWS_DIR + 'FabLotDetail.vue', VIEWS_DIR + 'FabSuivi.vue',
    ...listVue(COMPONENTS_DIR),
];

// --- (a) couleurs, taille du texte, caracteres, bibliotheque ui/ ---
const RAW_COLOR = /\b(?:indigo|emerald|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink|cyan|lime|fuchsia|violet|stone|zinc)-\d{2,3}\b/;

test('(a) la liste des fichiers du module couvre tout le dossier des vues', () => {
    const onDisk = listVue(VIEWS_DIR).sort();
    for (const f of onDisk) assert.ok(FABRICATION.includes(f), `${f} n'est pas couvert par ce garde-fou`);
});

for (const file of FABRICATION) {
    test(`(a) ${file} : ni hexadecimal ni couleur Tailwind brute`, () => {
        assert.ok(existsSync(new URL(file, root)), `${file} introuvable`);
        const src = read(file);
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, 'couleur hexadecimale en dur');
        assert.doesNotMatch(src, RAW_COLOR, 'couleur Tailwind brute (utiliser les jetons)');
    });

    test(`(a) ${file} : texte jamais inferieur a 13 px`, () => {
        const src = read(file);
        assert.doesNotMatch(src, /text-\[(?:[0-9]|1[0-2])px\]/);
        assert.doesNotMatch(src, /\btext-xs\b/);
    });

    test(`(a) ${file} : aucun caractere typographique d'aspect genere dans le texte affiche`, () => {
        assert.doesNotMatch(templateOf(read(file)).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×]|&times;|&rarr;|\p{Extended_Pictographic}/u);
    });

    test(`(a) ${file} : utilise la bibliotheque ui/ et aucune surcouche en dur`, () => {
        const src = read(file);
        assert.match(src, /@\/components\/ui/);
        assert.doesNotMatch(templateOf(src), /fixed inset-0/);
        assert.doesNotMatch(src, /@apply/);
    });
}

// --- (b) textes : FR et EN identiques ---
function flatten(obj, prefix = '', out = {}) {
    for (const [k, v] of Object.entries(obj)) {
        const key = prefix ? `${prefix}.${k}` : k;
        if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out);
        else out[key] = v;
    }
    return out;
}

test('(b) le francais et l\'anglais exposent exactement les memes cles', () => {
    const msgs = i18n.global.messages.value;
    const fr = Object.keys(flatten(msgs.fr));
    const en = new Set(Object.keys(flatten(msgs.en)));
    assert.deepEqual(fr.filter((k) => !en.has(k)), [], 'cles absentes en anglais');
    assert.equal(fr.length, en.size);
});

test('(b) la zone fabrication existe en FR et EN, memes cles, sans caractere interdit', () => {
    const msgs = i18n.global.messages.value;
    const zones = {};
    for (const locale of ['fr', 'en']) {
        assert.ok(msgs[locale].fabrication, `${locale}.fabrication absente`);
        zones[locale] = flatten(msgs[locale].fabrication);
        for (const [k, v] of Object.entries(zones[locale])) {
            assert.equal(typeof v, 'string', `${locale}.fabrication.${k}`);
            assert.doesNotMatch(v, /[—–…·•→]|\p{Extended_Pictographic}/u, `${locale}.fabrication.${k}`);
        }
    }
    assert.deepEqual(Object.keys(zones.fr).sort(), Object.keys(zones.en).sort());
});

test('(b) toutes les cles fabrication.* citees par les fichiers du module existent en FR et EN', () => {
    const msgs = i18n.global.messages.value;
    const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
    const used = new Set();
    for (const file of FABRICATION) {
        for (const m of read(file).matchAll(/['"`(]((?:fabrication)\.[a-zA-Z_]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 100, `seulement ${used.size} cles citees`);
    for (const k of used) {
        for (const locale of ['fr', 'en']) assert.equal(typeof pick(msgs[locale], k), 'string', `${locale}.${k} manquante`);
    }
});

// --- (c) perimetre : le chantier n'a touche que les fichiers prevus, aucun ecran existant ---
// BASE : dernier commit AVANT ce chantier. FIN : null = arbre de travail (le chantier n'est pas encore commite).
// Au commit du chantier, renseigner FIN avec le hash du dernier commit du lot (commit separe), pour que les
// chantiers suivants ne fassent pas echouer ce controle ; les fichiers non suivis ne figurent pas dans `git diff`,
// d'ou le controle d'emplacement ci-dessous.
const BASE = '755d4fa';
const FIN = 'dce04c8';

// Fichiers existants que le chantier a le droit de modifier : enregistrement du module et du role seulement.
const AUTORISES = new Set([
    'src/i18n.js',                              // textes fabrication.* et libelles du role
    'src/router/index.js',                      // routes /fabrication
    'src/components/layout/MainLayout.vue',     // entrees de menu du role et du promoteur/admin
    'src/design/navPalettes.js',                // palette de menu du role ProductionManager
    'src/components/users/UserModal.vue',       // le role est proposable a la creation d'un compte
    'src/utils/postLoginRoute.js',              // page d'arrivee du role
]);

function fichiersModifies() {
    try {
        const args = ['-C', repoRoot, 'diff', '--name-only', BASE, ...(FIN ? [FIN] : []), '--', 'ah2-admin-web'];
        const out = execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
        return out.split('\n').filter(Boolean).map((p) => p.replace(/^ah2-admin-web\//, ''));
    } catch {
        return null; // git absent ou commit introuvable (clone superficiel) : controle ignore
    }
}

test('(c) seuls les fichiers d\'enregistrement prevus ont ete modifies (hors tests)', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commit de depart indisponible');
    const hors = modifies.filter((f) => !f.startsWith('tests/') && !AUTORISES.has(f) && !f.startsWith(VIEWS_DIR) && !f.startsWith(COMPONENTS_DIR) && f !== GATEWAY);
    assert.deepEqual(hors, [], `fichiers modifies hors perimetre : ${hors.join(', ')}`);
});

test('(c) aucun ecran, magasin ou service existant (stock, caisse, labo, toxico, pharmacie) n\'est modifie', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commit de depart indisponible');
    const touche = modifies.filter((f) => /^src\/(views|stores|services|components)\//.test(f)
        && f !== GATEWAY && !f.startsWith(VIEWS_DIR) && !f.startsWith(COMPONENTS_DIR)
        && f !== 'src/components/layout/MainLayout.vue' && f !== 'src/components/users/UserModal.vue');
    assert.deepEqual(touche, []);
});

test('(c) les fichiers nouveaux du module vivent tous aux emplacements prevus', () => {
    // `git diff` ignore les fichiers non suivis : on controle l'emplacement directement.
    const out = (() => {
        try {
            return execFileSync('git', ['-C', repoRoot, 'ls-files', '--others', '--exclude-standard', '--', 'ah2-admin-web/src'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
        } catch { return null; }
    })();
    if (out === null) return; // git indisponible
    const nouveaux = out.split('\n').filter(Boolean).map((p) => p.replace(/^ah2-admin-web\//, ''));
    const hors = nouveaux.filter((f) => !f.startsWith(VIEWS_DIR) && !f.startsWith(COMPONENTS_DIR) && f !== GATEWAY);
    assert.deepEqual(hors, [], `fichiers nouveaux hors emplacement : ${hors.join(', ')}`);
});

// --- dates locales : aucune vue Fabrication ne derive une date de toISOString (UTC) ---
for (const file of FABRICATION) {
    test(`(dates) ${file} : pas de toISOString`, () => {
        assert.doesNotMatch(read(file), /toISOString/, 'utiliser todayLocalISO de @/utils/localDate');
    });
}

test('(dates) les dates par defaut de FabIntrants et FabLots viennent de todayLocalISO', () => {
    for (const f of ['FabIntrants.vue', 'FabLots.vue']) {
        const src = read(VIEWS_DIR + f);
        assert.match(src, /import \{ todayLocalISO \} from '@\/utils\/localDate'/);
        assert.match(src, /todayLocalISO\(\)/);
    }
});

test('(intrant desactive) FabLotDetail ne propose pas les achats d un intrant desactive', () => {
    assert.match(read(VIEWS_DIR + 'FabLotDetail.vue'), /intrant_active !== false/);
});

test('(produit) FabLots lit product_name du lot', () => {
    assert.match(read(VIEWS_DIR + 'FabLots.vue'), /b\.product_name/);
});
