// Garde-fous durables de la refonte UX du stock admin (plan 2026-10-22-refonte-ux-stock-admin.md).
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
    'src/views/modules/stock/StockReceipts.vue',
    'src/views/modules/stock/ProductionLots.vue',
    'src/views/modules/stock/StockIncidents.vue',
    'src/views/modules/stock/StockMovements.vue',
    'src/views/modules/stock/StockControlQueue.vue',
    'src/views/modules/stock/AdjustmentRequestsAdmin.vue',
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

test('(c) la zone stockAdminScreens existe et n’a ni tiret long ni points de suspension typographiques', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        assert.ok(msgs[locale].stockAdminScreens, `${locale}.stockAdminScreens absente`);
        for (const [k, v] of Object.entries(flatten(msgs[locale].stockAdminScreens))) {
            assert.doesNotMatch(String(v), /[—–…·]/, `${locale}.stockAdminScreens.${k}`);
        }
    }
});

// --- (d) la refonte n'a touché que les fichiers autorisés, jamais les données ni les règles de stock ---
const BASE = '132351c'; // juste avant la Tâche 1 de ce lot
// Dernier commit des Tâches 1 à 4 (57727cb). null = arbre de travail ;
// renseigné pour que les chantiers suivants ne fassent pas échouer ce contrôle.
const FIN = '57727cb';

const AUTORISES = new Set([
    ...REFONDUS,
    'src/i18n.js',
    'src/views/SystemConfig.vue', // protections sur la régénération du jeton d'impression (demande de l'utilisateur, hors lot stock)
]);

const INTERDITS = [
    'src/services/StockOpsGateway.js', 'src/utils/receiptLines.js', 'src/utils/localDate.js', 'src/utils/adjustmentRequest.js', 'src/utils/actorName.js',
    'src/views/modules/stock/StockList.vue', 'src/components/stock/ProductModal.vue', 'src/components/stock/AdjustmentRequestModal.vue',
    'src/router/index.js', 'src/components/layout/MainLayout.vue', 'src/components/layout/AppShell.vue',
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

test('(d) passerelle, règles de stock, écrans déjà refaits, routeur et cadre : intacts', (t) => {
    const modifies = fichiersModifies();
    if (!modifies) return t.skip('git ou commits de la refonte indisponibles');
    assert.deepEqual(INTERDITS.filter((f) => modifies.includes(f)), []);
});

// --- (e) les gestes qui comptent ---
test('(e) la création d’une réception garde ses validations et la forme envoyée ; annuler une réception ou un lot reste confirmé', () => {
    const rec = read('src/views/modules/stock/StockReceipts.vue');
    assert.match(rec, /const chk = validateReceiptLine\(line\);/);
    assert.match(rec, /await StockOpsGateway\.createReceipt\(payload\);/);
    assert.match(rec, /if \(!window\.confirm\(t\('stockOps\.confirm_cancel'\)\)\) return;/);
    assert.match(read('src/views/modules/stock/ProductionLots.vue'), /if \(!window\.confirm\(t\('stockOps\.confirm_cancel'\)\)\) return;/);
    assert.match(read('src/views/modules/stock/StockIncidents.vue'), /if \(!window\.confirm\(t\('stockOps\.confirm_cancel'\)\)\) return;/);
});

test('(e) le contrôle reste interdit sur sa propre saisie et la validation reste confirmée', () => {
    const src = read('src/views/modules/stock/StockControlQueue.vue');
    assert.match(src, /const isMine = \(item\) => myId\.value !== null && item\?\.created_by === myId\.value;/);
    assert.match(src, /const canDecide = computed\(\(\) => !!selected\.value && !isMine\(selected\.value\)\);/);
    assert.match(src, /window\.confirm\(t\('stockControl\.confirm_validate'\)\)/);
    assert.match(src, /if \(!reason\) \{ rejectError\.value = t\('stockOps\.err_reason_required'\); return; \}/);
});

test('(e) l’approbation d’un ajustement reste confirmée et son refus exige un motif', () => {
    const src = read('src/views/modules/stock/AdjustmentRequestsAdmin.vue');
    assert.match(src, /window\.confirm\(t\('stockAdjust\.confirm_approve'\)\)/);
    assert.match(src, /if \(!note\) \{ refuseError\.value = t\('stockAdjust\.err_note_required'\); return; \}/);
});

test('(e) l’historique des mouvements reste en lecture seule', () => {
    const src = read('src/views/modules/stock/StockMovements.vue');
    assert.doesNotMatch(src, /StockOpsGateway\.(create|cancel|validate|reject|update|approve)/);
});
