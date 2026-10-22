// Garde-fous durables de la refonte UX des comptes et des journaux techniques
// (plan 2026-10-22-refonte-ux-utilisateurs-journaux.md).
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

const REFONDUS = [
    'src/views/modules/users/UserManagement.vue',
    'src/components/users/UserModal.vue',
    'src/views/modules/tech/SystemLogs.vue',
];

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
        assert.doesNotMatch(templateOf(read(file)), /[—–…·•]|\p{Extended_Pictographic}/u);
    });

    test(`(b) ${file} : utilise la bibliothèque ui/`, () => {
        assert.match(read(file), /@\/components\/ui/);
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

test('(c) les zones usersScreens et techScreens existent et n’ont ni tiret long ni points de suspension typographiques', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        for (const z of ['usersScreens', 'techScreens']) {
            assert.ok(msgs[locale][z], `${locale}.${z} absente`);
            for (const [k, v] of Object.entries(flatten(msgs[locale][z]))) {
                assert.doesNotMatch(String(v), /[—–…·]/, `${locale}.${z}.${k}`);
            }
        }
    }
});

// --- (d) la refonte n'a touché que les fichiers autorisés ---
const BASE = '237015c'; // juste avant la Tâche 1 de ce lot
// Dernier commit des Tâches 1 à 3. null = arbre de travail (tant que ces tâches ne sont pas commitées) ;
// à renseigner avec le hash du commit pour que les chantiers suivants ne fassent pas échouer ce contrôle.
const FIN = null;

const AUTORISES = new Set([...REFONDUS, 'src/i18n.js']);

const INTERDITS = [
    'src/stores/userStore.js', 'src/stores/auditStore.js', 'src/services/api.js',
    'src/components/common/Pagination.vue', 'src/router/index.js',
    'src/components/layout/MainLayout.vue', 'src/components/layout/AppShell.vue',
    'src/views/SystemConfig.vue',
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
    const hors = modifies.filter((f) => !f.startsWith('tests/') && !AUTORISES.has(f));
    assert.deepEqual(hors, [], `fichiers modifiés hors périmètre : ${hors.join(', ')}`);
});

test('(d) données, routeur, cadre et écrans des autres lots : intacts', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    assert.deepEqual(INTERDITS.filter((f) => modifies.includes(f)), []);
});

// --- (e) les gestes qui comptent ---
test('(e) la suppression d’un compte reste confirmée et la modification ouvre une copie du compte', () => {
    const src = read('src/views/modules/users/UserManagement.vue');
    assert.match(src, /if \(confirm\(`Voulez-vous vraiment supprimer/);
    assert.match(src, /selectedUser\.value = \{ \.\.\.user \}/);
});

test('(e) le compte envoyé garde sa forme (mot de passe vide retiré en modification)', () => {
    const src = read('src/components/users/UserModal.vue');
    assert.match(src, /if \(isEditing\.value && !form\.password\) delete payload\.password/);
    assert.match(src, /emit\('save', payload\)/);
});
