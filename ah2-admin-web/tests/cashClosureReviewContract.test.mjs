// Contrat de l'ecran promoteur/admin des clotures de caisse (Tache 10) : filtres de dates locales, clotures
// non declarees en evidence par un mot, ecart en mots, lecture seule sauf decision des corrections et panneaux
// admin (modes sans creation, especes non desactivable, initialisation avec confirmation), textes FR/EN.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const templateOf = (src) => (src.includes('<script') ? src.slice(0, src.indexOf('<script')) : src);
const scriptOf = (src) => src.slice(src.indexOf('<script'));
const FORBIDDEN = /[—–…·→←−]|\p{Extended_Pictographic}/u;
const RAW_COLOR = /\b(?:indigo|emerald|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink|cyan|lime|fuchsia|violet|stone|zinc)-\d{2,3}\b/;

const VIEW = 'src/views/modules/caisse/CashClosuresReview.vue';
const GATEWAY = 'src/services/CashClosureGateway.js';
const STORE = 'src/stores/cashClosureStore.js';

const view = existsSync(new URL(`../${VIEW}`, import.meta.url)) ? read(VIEW) : '';
const tpl = templateOf(view);

test('les fichiers existent', () => {
    for (const f of [VIEW, GATEWAY, STORE]) assert.ok(existsSync(new URL(`../${f}`, import.meta.url)), f);
});

// ---------- regles pures ----------
test('localDateISO : date locale AAAA-MM-JJ, sans passer par UTC', async () => {
    const { localDateISO } = await import('../src/utils/cashClosure.js');
    assert.equal(localDateISO(new Date(2030, 0, 5, 23, 59)), '2030-01-05');
    assert.equal(localDateISO(new Date(2030, 11, 31, 0, 1)), '2030-12-31');
});

test('closureFlags : non declaree (auto), ecart, commentaire non fourni', async () => {
    const { closureFlags } = await import('../src/utils/cashClosure.js');
    const auto = { kind: 'auto', lines: [{ mode: 'especes', difference: null, comment: null }] };
    assert.deepEqual(closureFlags(auto), { undeclared: true, withGap: false, commentMissing: false });
    const gap = { kind: 'manual', comment_missing: true, lines: [{ mode: 'especes', difference: '0.00' }, { mode: 'mtn_money', difference: '-500.00', comment_missing: true }] };
    assert.deepEqual(closureFlags(gap), { undeclared: false, withGap: true, commentMissing: true });
    assert.deepEqual(closureFlags({ kind: 'manual', lines: [{ difference: '0' }] }), { undeclared: false, withGap: false, commentMissing: false });
});

test('closureFlags : le commentaire manquant vient du drapeau serveur, jamais du texte', async () => {
    const { closureFlags } = await import('../src/utils/cashClosure.js');
    const c = { kind: 'manual', lines: [{ difference: '-5', comment: 'commentaire non fourni' }] };
    assert.equal(closureFlags(c).commentMissing, false);
    assert.doesNotMatch(read('src/utils/cashClosure.js'), /commentaire non fourni/);
    assert.doesNotMatch(view, /commentaire non fourni|AUTO_COMMENT/);
    assert.match(view, /row\.comment_missing/);
});

test('formatAmountFcfa : decimales gardees, sans Number', async () => {
    const { formatAmountFcfa } = await import('../src/utils/cashClosure.js');
    assert.equal(formatAmountFcfa('1500.50'), '1 500,50 FCFA');
    assert.equal(formatAmountFcfa('1500.00'), '1 500 FCFA');
    assert.equal(formatAmountFcfa('1234567'), '1 234 567 FCFA');
    assert.equal(formatAmountFcfa('-20.05'), '-20,05 FCFA');
    assert.equal(formatAmountFcfa(null), '');
    assert.doesNotMatch(view, /Number\(s\)\.toLocaleString/);
});

test('store de revue : les reponses perimees de load sont ignorees (compteur)', () => {
    const s = read(STORE);
    assert.match(s, /const seq = \+\+loadSeq/);
    assert.match(s, /if \(seq !== loadSeq\) return;/);
});

test('admin : erreur de statut visible, libelle de mode vide refuse', () => {
    assert.match(tpl, /isAdmin && statusError/);
    assert.match(view, /statusError\.value = /);
    assert.match(view, /if \(!f\.label\.trim\(\)\) \{ modesError\.value = t\('cashClosure\.review_mode_label_empty'\)/);
});

test('canDeactivateMode : especes ne peut pas etre desactive', async () => {
    const { canDeactivateMode } = await import('../src/utils/cashClosure.js');
    assert.equal(canDeactivateMode('especes'), false);
    assert.equal(canDeactivateMode('mtn_money'), true);
});

// ---------- passerelle et store ----------
test('passerelle : nouvelles routes sans casser celles de la tache 9', () => {
    const g = read(GATEWAY);
    for (const fn of ['getStatus', 'catchup', 'submit', 'list', 'get', 'start', 'listCorrections', 'decideCorrection', 'listModes', 'updateMode']) {
        assert.match(g, new RegExp(`async ${fn}\\(`), fn);
    }
    assert.match(g, /'\/cash-closure\/start'.*opening_cash/s);
    assert.match(g, /\/cash-closure\/corrections\/\$\{id\}\/decide`, \{ approve/);
    assert.match(g, /api\.put\(`\/payment-modes\/\$\{/);
    assert.doesNotMatch(g, /api\.post\(['`]\/payment-modes/, 'aucune creation de mode');
    assert.doesNotMatch(g, /api\.(delete|patch)\(/);
});

test('store : la cloture de la secretaire reste intacte, la revue a son propre store', () => {
    const s = read(STORE);
    assert.match(s, /defineStore\('cashClosure'/);
    assert.match(s, /defineStore\('cashClosureReview'/);
    assert.doesNotMatch(s, /toISOString/);
});

// ---------- ecran ----------

test('filtres : dates locales (jamais toISOString), type auto/manuelle, avec ecart', () => {
    assert.doesNotMatch(view, /toISOString/);
    assert.match(view, /localDateISO/);
    assert.match(tpl, /type="date"/);
    assert.match(tpl, /value="auto"/);
    assert.match(tpl, /value="manual"/);
    assert.match(tpl, /onlyGap/);
});

test('non declaree et commentaire non fourni dits par un MOT (badge), ecart en mots', () => {
    assert.match(tpl, /cashClosure\.review_badge_undeclared/);
    assert.match(tpl, /cashClosure\.review_comment_missing/);
    assert.match(view, /gapWords/);
});

test('lecture seule : seules ecritures = decision, modes (admin), initialisation (admin)', () => {
    const calls = [...scriptOf(view).matchAll(/review\.(\w+)\(/g)].map((m) => m[1]);
    const writes = calls.filter((c) => !/^(load|loadCorrections|loadModes|loadStatus|select)$/.test(c));
    assert.deepEqual([...new Set(writes)].sort(), ['decide', 'start', 'updateMode']);
    assert.doesNotMatch(view, /CashClosureGateway\.submit|review\.submit/);
});

test('modes : panneau admin seulement, aucun bouton de creation, especes desactivation impossible avec raison', () => {
    assert.match(tpl, /v-if="isAdmin"[^>]*cashClosure\.review_modes_title/);
    assert.doesNotMatch(tpl, /review_mode_add|review_mode_create/);
    assert.match(tpl, /canDeactivateMode/);
    assert.match(tpl, /cashClosure\.review_mode_cash_locked/);
});

test('initialisation : admin et caisse non configuree seulement, avec etape de confirmation', () => {
    assert.match(tpl, /isAdmin && review\.status && !review\.status\.configured/);
    assert.match(tpl, /confirmingStart/);
    assert.match(tpl, /cashClosure\.review_start_confirm_warning/);
    assert.equal(msgs.fr.cashClosure.review_start_confirm_warning.includes('ne pourra plus'), true);
});

test('decision des corrections : approuver / refuser, sans mot de passe', () => {
    assert.match(tpl, /decide\(c\.id, true\)/);
    assert.match(tpl, /decide\(c\.id, false\)/);
    assert.doesNotMatch(tpl, /type="password"/);
});

test('route et menu : /dashboard/cash-closures, promoteur et admin', () => {
    const r = read('src/router/index.js');
    assert.match(r, /path: 'cash-closures',[\s\S]{0,200}CashClosuresReview\.vue[\s\S]{0,120}roles: \[ROLES\.ADMIN, ROLES\.PROMOTEUR\]/);
    const m = read('src/components/layout/MainLayout.vue');
    assert.match(m, /path: '\/dashboard\/cash-closures',[\s\S]{0,150}roles: \[ROLES\.ADMIN, ROLES\.PROMOTEUR\]/);
});

// ---------- textes et style ----------
test('FR/EN : memes cles cashClosure, aucune vide', () => {
    const fr = Object.keys(msgs.fr.cashClosure).sort();
    const en = Object.keys(msgs.en.cashClosure).sort();
    assert.deepEqual(fr, en);
    assert.ok(fr.filter((k) => k.startsWith('review_')).length > 20);
    for (const l of ['fr', 'en']) for (const k of fr) assert.ok(String(msgs[l].cashClosure[k]).trim(), `${l}.${k}`);
});

test('caracteres interdits absents des textes et de l ecran', () => {
    for (const l of ['fr', 'en']) {
        for (const [k, v] of Object.entries(msgs[l].cashClosure)) assert.doesNotMatch(String(v), FORBIDDEN, `${l}.${k}`);
    }
    assert.doesNotMatch(tpl, FORBIDDEN);
});

test('couleurs par jetons, texte >= 13 px, cibles >= 44 px', () => {
    assert.doesNotMatch(view, RAW_COLOR);
    assert.doesNotMatch(tpl, /text-xs\b|text-\[1[0-2]px\]/);
    assert.match(view, /min-h-11/);
    assert.match(view, /@\/components\/ui/);
});
