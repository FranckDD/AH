// Garde-fous durables de la refonte UX de la configuration système
// (plan 2026-10-22-refonte-ux-configuration-systeme.md).
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
    'src/views/SystemConfig.vue',
    'src/components/config/ExamFormModal.vue',
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

test('(c) la zone configScreens existe et n’a ni tiret long ni points de suspension typographiques', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        assert.ok(msgs[locale].configScreens, `${locale}.configScreens absente`);
        for (const [k, v] of Object.entries(flatten(msgs[locale].configScreens))) {
            assert.doesNotMatch(String(v), /[—–…·]/, `${locale}.configScreens.${k}`);
        }
    }
});

// --- (d) la refonte n'a touché que les fichiers autorisés, jamais les données ni l'impression ---
const BASE = '45deaa4'; // juste avant la Tâche 1 de ce lot
// Dernier commit des Tâches 1 à 2 (a76f1b3). null = arbre de travail ;
// renseigné pour que les chantiers suivants ne fassent pas échouer ce contrôle.
const FIN = 'a76f1b3';

const AUTORISES = new Set([...REFONDUS, 'src/i18n.js']);

const INTERDITS = [
    'src/stores/configStore.js', 'src/services/api.js', 'src/services/PrinterBridgeGateway.js',
    'src/router/index.js', 'src/components/layout/MainLayout.vue', 'src/components/layout/AppShell.vue',
    'src/views/modules/users/UserManagement.vue', 'src/views/modules/tech/SystemLogs.vue',
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

test('(d) données, impression, routeur et cadre : intacts', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    assert.deepEqual(INTERDITS.filter((f) => modifies.includes(f)), []);
    assert.deepEqual(modifies.filter((f) => f.startsWith('printer_bridge/')), [], 'printer_bridge/ ne doit pas changer');
});

// --- (e) les gestes qui comptent ---
test('(e) régénérer le jeton d’impression reste confirmé, et l’identité de la structure part en FormData avec les deux logos', () => {
    const src = read('src/views/SystemConfig.vue');
    assert.match(src, /Régénérer le jeton invalidera l'ancien pour tous les services pont locaux déjà configurés\. Continuer \?/);
    assert.match(src, /await configStore\.regenerateTicketPrintToken\(\)/);
    assert.match(src, /const formData = new FormData\(\)/);
    assert.match(src, /formData\.append\('logo', logoFile\.value\)/);
    assert.match(src, /formData\.append\('ticket_logo', ticketLogoFile\.value\)/);
});

test('(e) un examen n’est supprimé qu’après confirmation et son code reste verrouillé en modification', () => {
    assert.match(read('src/views/SystemConfig.vue'), /if\(confirm\(t\('config\.delete_confirmation'\)/);
    assert.match(read('src/components/config/ExamFormModal.vue'), /:disabled="isEditing"/);
});

test('(e) les quatre sections repliables gardent leur état initial (structure et examens ouverts)', () => {
    const src = read('src/views/SystemConfig.vue');
    assert.match(src, /structure: true,/);
    assert.match(src, /exams: true,/);
    assert.match(src, /prayers: false,/);
    assert.match(src, /general: false/);
});
