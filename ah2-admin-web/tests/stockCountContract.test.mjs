// Contrat de l'ecran de comptage du stock (plan 2026-10-24-comptage-stock.md, tache 4) : passerelle, aveugle,
// roles, double clic, textes FR/EN, caracteres interdits, jetons de couleur, dates locales.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const templateOf = (src) => (src.includes('<script') ? src.slice(0, src.indexOf('<script')) : src);
const FORBIDDEN = /[—–…·•→←−✓×]|\p{Extended_Pictographic}/u;
const RAW_COLOR = /\b(?:indigo|emerald|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink|cyan|lime|fuchsia|violet|stone|zinc)-\d{2,3}\b/;

const VIEW = 'src/views/modules/stock/StockCount.vue';
const STORE = 'src/stores/stockCountStore.js';
const GATEWAY = 'src/services/StockCountGateway.js';
const RULES = 'src/utils/stockCount.js';
const REVEAL = 'src/components/stock/StockCountReveal.vue';
const FREQ = 'src/components/stock/StockCountFrequency.vue';
const HISTORY = 'src/components/stock/StockCountHistory.vue';
const FILES = [VIEW, STORE, GATEWAY, RULES, REVEAL, FREQ, HISTORY];

for (const f of FILES) {
    test(`${f} existe`, () => assert.ok(existsSync(new URL(`../${f}`, import.meta.url)), f));
}

// ---------- passerelle ----------
test('passerelle : chemins et corps des routes /stock-counts', () => {
    const src = read(GATEWAY);
    for (const r of [
        "api.post('/stock-counts', { scope })",
        'api.post(`/stock-counts/${id}/submit`, { client_now: clientNow, lines })',
        'api.post(`/stock-counts/${id}/abandon`)',
        "api.get('/stock-counts/status')",
        "api.get('/stock-counts/settings')",
        "api.put('/stock-counts/settings', { interval_days: intervalDays })",
        "api.get('/stock-counts', {",
        'params: clean({ date_from: dateFrom, date_to: dateTo, status, limit, offset, mine })',
        'api.get(`/stock-counts/${id}`)',
    ]) assert.ok(src.includes(r), r);
});

test('regles : quantite entiere >= 0 et <= 10000000, vide = non compte', async () => {
    const { parseCount, MAX_COUNT } = await import('../src/utils/stockCount.js');
    assert.equal(MAX_COUNT, 10000000);
    assert.deepEqual(parseCount(''), { blank: true });
    assert.deepEqual(parseCount('   '), { blank: true });
    assert.deepEqual(parseCount(null), { blank: true });
    assert.deepEqual(parseCount('12'), { value: 12 });
    assert.deepEqual(parseCount(' 0 '), { value: 0 });
    assert.deepEqual(parseCount(7), { value: 7 });
    assert.deepEqual(parseCount('10000000'), { value: 10000000 });
    for (const bad of ['-1', '1.5', '1,5', 'abc', '10000001', '1e3', 2.5]) assert.deepEqual(parseCount(bad), { error: true }, String(bad));
});

test('regles : lignes envoyees = produits saisis seulement, entiers JS, observation si non vide', async () => {
    const { buildLines } = await import('../src/utils/stockCount.js');
    const out = buildLines([{ id: 1 }, { id: 2 }, { id: 3 }], {
        1: { qty: '5', observation: '  ' }, 2: { qty: '', observation: 'x' }, 3: { qty: '0', observation: ' casse ' },
    });
    assert.deepEqual(out, [{ product_id: 1, counted_qty: 5 }, { product_id: 3, counted_qty: 0, observation: 'casse' }]);
    for (const l of out) assert.equal(typeof l.counted_qty, 'number');
    assert.deepEqual(buildLines([{ id: 1 }], { 1: { qty: '1.5' } }), null, 'une saisie invalide bloque tout');
});

test('regles : intervalle entier 1..365', async () => {
    const { parseInterval } = await import('../src/utils/stockCount.js');
    assert.equal(parseInterval('30'), 30);
    assert.equal(parseInterval(365), 365);
    for (const bad of ['0', '366', '2.5', '', 'x']) assert.equal(parseInterval(bad), null, bad);
});

test('regles : ecart et mouvements dits en mots', async () => {
    const { gapKey, movementsKey } = await import('../src/utils/stockCount.js');
    assert.equal(gapKey('plus'), 'stockCount.gap_plus');
    assert.equal(gapKey('moins'), 'stockCount.gap_moins');
    assert.equal(gapKey('aucun'), 'stockCount.gap_none');
    assert.equal(movementsKey(0), null);
    assert.equal(movementsKey(1), 'stockCount.movements_one');
    assert.equal(movementsKey(4), 'stockCount.movements_many');
});

test('regles : dates locales, horodatage serveur avec decalage UTC', async () => {
    const { formatLocalDate, formatLocalDateTime } = await import('../src/utils/stockCount.js');
    assert.equal(formatLocalDate(null), '');
    const d = new Date('2026-10-24T22:30:00+00:00');
    assert.equal(formatLocalDate('2026-10-24T22:30:00+00:00'), d.toLocaleDateString('fr-FR'));
    assert.ok(formatLocalDateTime('2026-10-24T22:30:00+00:00').length > 0);
    // seule exception : instantISO (un instant, pas une date de calendrier)
    assert.equal((read(RULES).match(/toISOString/g) || []).length, 1);
});

// ---------- aveugle ----------
test('aveugle : ni la vue, ni le store, ni la passerelle ne lisent une quantite du systeme', () => {
    for (const f of [VIEW, STORE, GATEWAY, RULES]) {
        assert.doesNotMatch(read(f), /previous_qty|difference|stock_at_request|\.quantity\b|quantity:/, f);
    }
});

test('aveugle : le tableau revele n est affiche que depuis le resultat de validation ou le detail valide', () => {
    const view = templateOf(read(VIEW));
    assert.match(view, /<StockCountReveal v-if="store\.result" :count="store\.result"/);
    const hist = templateOf(read(HISTORY));
    assert.match(hist, /<StockCountReveal v-if="detail" :count="detail"/);
    const reveal = read(REVEAL);
    assert.match(reveal, /previous_qty/);
    assert.match(reveal, /stockCount\.reveal_notice/);
    // le formulaire de comptage ne montre que le nom et le champ
    const form = view.slice(view.indexOf('<form'), view.indexOf('</form>'));
    assert.ok(form.length > 0);
    assert.doesNotMatch(form, /previous|system|difference|stock\b/);
});

test('aveugle : le store ne garde du demarrage que id, date, perimetre et noms des produits', () => {
    const src = read(STORE);
    assert.match(src, /products: \(out\.products \|\| \[\]\)\.map\(\(p\) => \(\{ id: p\.id, name: p\.name \}\)\)/);
});

// ---------- roles ----------
test('roles : comptage reserve a StockController, admin et promoteur en lecture seule', () => {
    const src = read(VIEW);
    assert.match(src, /const canCount = computed\(\(\) => authStore\.hasRole\(\['StockController'\]\)\);/);
    const tpl = templateOf(src);
    assert.match(tpl, /v-if="canCount"/);
    for (const call of ['handleStart', 'handleSubmit', 'handleAbandon']) {
        const at = tpl.indexOf(call);
        assert.ok(at > tpl.indexOf('v-if="canCount"'), `${call} hors de la zone de comptage`);
    }
    assert.doesNotMatch(src, /promoteur/, 'aucune exception promoteur : il n a juste pas canCount');
});

test('roles : reglage de la frequence visible pour admin seul', () => {
    const src = read(FREQ);
    assert.match(src, /const canSetInterval = computed\(\(\) => authStore\.hasRole\(\['admin'\]\)\);/);
    const tpl = templateOf(src);
    const at = tpl.indexOf('v-if="canSetInterval"');
    assert.ok(at > 0);
    assert.ok(tpl.indexOf('saveInterval') > at, 'le bouton est dans le bloc admin');
    assert.doesNotMatch(templateOf(read(HISTORY)), /@click="(?!select|load|close|apply|reset)/, 'historique : lecture seule');
});

test('router et menu : /dashboard/stock-count pour StockController, admin, promoteur', () => {
    const r = read('src/router/index.js');
    assert.match(r, /path: 'stock-count',\s*name: 'stock-count',\s*component: \(\) => import\('@\/views\/modules\/stock\/StockCount\.vue'\),\s*meta: \{ requiresAuth: true, roles: \[ROLES\.STOCK_CONTROLLER, ROLES\.ADMIN, ROLES\.PROMOTEUR\] \}/);
    const m = read('src/components/layout/MainLayout.vue');
    assert.match(m, /path: '\/dashboard\/stock-count',\s*group: 'stock',\s*labelKey: 'stockCount\.menu',\s*icon: \w+,\s*roles: \[ROLES\.STOCK_CONTROLLER, ROLES\.ADMIN, ROLES\.PROMOTEUR\]/);
});

// ---------- double clic ----------
for (const [file, fn, flag] of [
    [VIEW, 'handleStart', 'starting'], [VIEW, 'handleSubmit', 'submitting'], [VIEW, 'handleAbandon', 'abandoning'],
    [FREQ, 'saveInterval', 'saving'],
]) {
    test(`double clic : ${fn} verrouille avant tout await et relache en finally`, () => {
        const src = read(file);
        const start = src.indexOf(`async function ${fn}(`);
        assert.ok(start > 0, fn);
        const body = src.slice(start, src.indexOf('\n}\n', start));
        assert.match(body, new RegExp(`if \\(${flag}\\.value\\) return;`));
        const set = body.indexOf(`${flag}.value = true;`);
        assert.ok(set > 0 && set < body.indexOf('await'), 'verrou pose avant le premier await');
        assert.match(body, new RegExp(`finally \\{\\s*${flag}\\.value = false;`));
    });
}

test('validation inactive sans ligne saisie, erreurs du serveur affichees telles quelles', () => {
    const src = read(VIEW);
    assert.match(src, /const canSubmit = computed\(\(\) => !submitting\.value && lines\.value !== null && lines\.value\.length > 0\);/);
    assert.match(templateOf(src), /:disabled="!canSubmit"/);
    assert.match(src, /describeServerError\(/);
    assert.match(src, /409/);
    assert.match(src, /window\.confirm\(t\('stockCount\.abandon_confirm'\)\)/);
});

// ---------- textes, couleurs, dates ----------
const flatten = (obj, prefix = '') => Object.entries(obj).flatMap(([k, v]) => (v && typeof v === 'object' ? flatten(v, `${prefix}${k}.`) : [[`${prefix}${k}`, v]]));

test('i18n : stockCount.* identiques en FR et EN, non vides, sans caractere interdit', () => {
    const fr = flatten(msgs.fr.stockCount || {});
    const en = flatten(msgs.en.stockCount || {});
    assert.ok(fr.length >= 20);
    assert.deepEqual(fr.map(([k]) => k).sort(), en.map(([k]) => k).sort());
    for (const [k, v] of [...fr, ...en]) {
        assert.equal(typeof v, 'string', k);
        assert.ok(v.trim(), k);
        assert.doesNotMatch(v, FORBIDDEN, k);
    }
    assert.equal(msgs.fr.stockCount.reveal_notice, "Les écarts ont été transmis à l'admin pour approbation. Le stock ne change qu'après son accord.");
});

test('i18n : toutes les cles stockCount.* citees existent en FR et EN', () => {
    const pick = (o, p) => p.split('.').reduce((x, k) => x?.[k], o);
    const used = new Set();
    for (const f of FILES) for (const m of read(f).matchAll(/['"`](stockCount\.[a-z_]+)['"`]/g)) used.add(m[1]);
    assert.ok(used.size > 20);
    for (const k of used) for (const l of ['fr', 'en']) assert.equal(typeof pick(msgs[l], k), 'string', `${l}.${k}`);
});

for (const f of FILES) {
    test(`${f} : jetons de couleur, texte >= 13 px, aucun caractere interdit, pas de toISOString`, () => {
        const src = read(f);
        assert.doesNotMatch(src, RAW_COLOR);
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b|\b(?:rgba?|hsla?)\(/);
        assert.doesNotMatch(src, /\btext-xs\b|text-\[(?:[0-9]|1[0-2])px\]/);
        assert.doesNotMatch(f.endsWith('.vue') ? templateOf(src).replace(/<!--.*?-->/gs, '') : src.replace(/\/\/.*$/gm, ''), FORBIDDEN);
        // seule exception : instantISO dans les regles (un instant UTC, verifie plus bas)
        if (f !== RULES) assert.doesNotMatch(src, /toISOString/);
    });
}

test('ecrans : bibliotheque ui/, cibles >= 44 px', () => {
    for (const f of [VIEW, REVEAL, FREQ, HISTORY]) assert.match(read(f), /from '@\/components\/ui'/, f);
    for (const f of [VIEW, FREQ, HISTORY]) assert.match(read(f), /min-h-11/, f);
    assert.match(templateOf(read(FREQ)), /StatusBadge/, 'statut dit par un badge avec un mot');
});

// ---------- poste partage et reprise apres 409 (revue, tour 1) ----------
// Le store est charge avec une passerelle factice (copie temporaire, l'alias @ n'existe pas sous node).
import { writeFileSync, unlinkSync } from 'node:fs';
async function loadStoreWith(fake) {
    const tmp = new URL(`./.tmp-stockCountStore-${process.pid}-${Math.random().toString(36).slice(2)}.mjs`, import.meta.url);
    const src = read(STORE).replace("import { StockCountGateway } from '@/services/StockCountGateway';", 'const StockCountGateway = globalThis.__fakeStockCountGateway;')
        .replace("from '@/utils/stockCount'", "from '../src/utils/stockCount.js'");
    globalThis.__fakeStockCountGateway = fake;
    writeFileSync(tmp, src);
    try {
        const { createPinia, setActivePinia } = await import('pinia');
        setActivePinia(createPinia());
        const mod = await import(tmp.href);
        return mod.useStockCountStore();
    } finally { unlinkSync(tmp); }
}

test('poste partage : rien de l utilisateur A ne reste quand B se connecte', async () => {
    const fake = {
        start: async () => ({ id: 7, started_at: '2026-10-24T08:00:00+00:00', scope: 'tous', products: [{ id: 1, name: 'A', quantity: 99 }] }),
        submit: async () => ({ id: 7, lines: [{ product_id: 1, previous_qty: 99 }] }),
        getStatus: async () => ({ interval_days: 30, counts: {}, products: [] }),
        list: async () => ({ items: [{ id: 3 }], total: 1 }),
    };
    const store = await loadStoreWith(fake);
    store.ensureOwner(1);
    await store.start('tous');
    assert.deepEqual(store.open.products, [{ id: 1, name: 'A' }], 'aucune quantite gardee du demarrage');
    await store.submit([{ product_id: 1, counted_qty: 3 }]);
    await store.loadHistory();
    await store.loadFrequency();
    assert.ok(store.result && store.frequency && store.history.items.length);
    store.ensureOwner(1);
    assert.ok(store.result, 'meme utilisateur : rien n est jete');
    store.ensureOwner(2);
    assert.equal(store.open, null);
    assert.equal(store.result, null);
    assert.equal(store.frequency, null);
    assert.deepEqual(store.history, { items: [], total: 0, limit: 50, offset: 0 });
    assert.equal(store.owner, 2);
    // comptage ouvert par B puis C sur le meme poste
    await store.start('tous');
    assert.ok(store.open);
    store.ensureOwner(3);
    assert.equal(store.open, null);
});

test('409 a la validation ou a l abandon : comptage oublie, message garde, reprise sans recharger', async () => {
    const src = read(VIEW);
    assert.match(src, /async function recoverFromConflict\(\) \{\s*store\.forgetOpen\(\);\s*await resumeOpen\(\);\s*\}/);
    for (const fn of ['handleSubmit', 'handleAbandon']) {
        const body = src.slice(src.indexOf(`async function ${fn}(`), src.indexOf('\n}\n', src.indexOf(`async function ${fn}(`)));
        assert.match(body, /pageError\.value = errorText\([^)]*\);\s*if \(err\?\.response\?\.status === 409\) await recoverFromConflict\(\);/, fn);
    }
    const store = await loadStoreWith({ start: async () => ({ id: 9, products: [] }) });
    await store.start('tous');
    store.forgetOpen();
    assert.equal(store.open, null);
});

test('poste partage : l ecran revalide le proprietaire au montage et au changement d utilisateur', () => {
    const src = read(VIEW);
    assert.match(src, /store\.ensureOwner\(myId\.value\);/);
    assert.match(src, /watch\(myId, syncOwner\);\s*onMounted\(syncOwner\);/);
    const hist = read(HISTORY);
    assert.match(hist, /watch\(\(\) => authStore\.user\?\.id \?\? null, \(\) => \{ closeDetail\(\);/);
});

test('historique : seule la reponse du dernier detail demande est appliquee', () => {
    const src = read(HISTORY);
    assert.match(src, /const seq = \+\+detailSeq;/);
    assert.match(src, /if \(seq === detailSeq\) detail\.value = out;/);
});

test('revele : stock systeme negatif compte 0 = libelle dedie, pas "Aucun ecart"', () => {
    const src = templateOf(read(REVEAL));
    assert.match(src, /v-if="row\.gap_kind === 'aucun' && row\.adjustment_request_id"[^>]*stockCount\.gap_negative_system/);
    assert.match(msgs.fr.stockCount.gap_negative_system, /négatif/);
});

test('dates : langue active de vue-i18n', async () => {
    const { formatLocalDate } = await import('../src/utils/stockCount.js');
    const iso = '2026-10-24T22:30:00+00:00';
    assert.equal(formatLocalDate(iso, 'en'), new Date(iso).toLocaleDateString('en-GB'));
    assert.equal(formatLocalDate(iso, 'fr'), new Date(iso).toLocaleDateString('fr-FR'));
    for (const f of [VIEW, FREQ, HISTORY]) assert.doesNotMatch(read(f), /formatLocal(Date|DateTime)\([^)]*[^e]\)\s*[}:]/, f);
});

// ---------- recomptage et demandes remplacees (revue finale) ----------
test('revele : mot Recomptage et demande remplacee', () => {
    const tpl = templateOf(read(REVEAL));
    assert.match(tpl, /v-if="row\.recount"[^>]*stockCount\.recount/);
    assert.match(tpl, /v-for="sid in row\.superseded_request_ids \|\| \[\]"/);
    assert.match(tpl, /stockCount\.superseded_request', \{ id: sid \}/);
    assert.equal(msgs.fr.stockCount.recount, 'Recomptage');
    assert.equal(msgs.fr.stockCount.superseded_request, 'Demande n. {id} remplacée');
    assert.equal(msgs.en.stockCount.recount, 'Recount');
});

test('notifications : stock_count_superseded et mention supersedes en FR et EN', () => {
    const bell = read('src/components/notifications/NotificationBell.vue');
    assert.match(bell, /n\.type === 'stock_count_superseded'/);
    assert.match(bell, /t\('notifications\.stock_count_superseded'/);
    assert.match(bell, /p\.supersedes/);
    assert.match(bell, /t\('notifications\.stock_adjustment_supersedes'/);
    assert.match(bell, /n\.type === 'stock_adjustment_request' \|\| n\.type === 'stock_count_superseded'/);
    for (const l of ['fr', 'en']) {
        for (const k of ['stock_count_superseded', 'stock_adjustment_supersedes']) {
            const v = msgs[l].notifications[k];
            assert.equal(typeof v, 'string', `${l}.${k}`);
            assert.doesNotMatch(v, FORBIDDEN, `${l}.${k}`);
        }
        assert.match(msgs[l].notifications.stock_count_superseded, /\{author\}.*\{product\}.*\{ids\}/);
        assert.match(msgs[l].notifications.stock_adjustment_supersedes, /\{label\}.*\{ids\}/);
    }
});

// ---------- tour 3 : heure de comptage par ligne, pagination, reprise mine=true ----------
test('regles : instantISO = seul usage de toISOString, pour un instant UTC', async () => {
    const { instantISO } = await import('../src/utils/stockCount.js');
    const d = new Date(Date.UTC(2026, 9, 24, 8, 1, 2));
    assert.equal(instantISO(d), '2026-10-24T08:01:02.000Z');
    const src = read(RULES);
    assert.match(src, /export function instantISO\(d = new Date\(\)\) \{\s*return d\.toISOString\(\);/);
});

test('regles : counted_at envoye par ligne quand une heure a ete relevee', async () => {
    const { buildLines } = await import('../src/utils/stockCount.js');
    const out = buildLines([{ id: 1 }, { id: 2 }], {
        1: { qty: '4', countedAt: '2026-10-24T08:01:02.000Z' }, 2: { qty: '2', countedAt: null },
    });
    assert.deepEqual(out, [{ product_id: 1, counted_qty: 4, counted_at: '2026-10-24T08:01:02.000Z' }, { product_id: 2, counted_qty: 2 }]);
});

test('ecran : heure relevee a la validation du champ, effacee si vide, jamais de quantite', () => {
    const src = read(VIEW);
    assert.match(templateOf(src), /@change="commitQty\(p\.id\)"/);
    assert.match(src, /function commitQty\(id\) \{[\s\S]*?parseCount\(entry\.qty\)[\s\S]*?entry\.countedAt = parsed\.blank \|\| parsed\.error \? null : instantISO\(\);/);
    assert.match(src, /form\[p\.id\] = \{ qty: '', observation: '', showObs: false, countedAt: null \}/);
});

test('revele : stock au moment du comptage, mouvements apres le comptage avec cumul, explication', () => {
    const src = read(REVEAL);
    assert.match(src, /row\.stock_at_count \?\? row\.previous_qty/);
    assert.match(src, /movements_net/);
    assert.match(msgs.fr.stockCount.movements_many, /après le comptage/);
    assert.match(msgs.fr.stockCount.movements_many, /cumul \{net\}/);
    assert.match(msgs.fr.stockCount.gap_explained, /au moment où vous avez compté le produit/);
    assert.match(src, /stockCount\.gap_explained/);
    for (const l of ['fr', 'en']) assert.doesNotMatch(JSON.stringify(msgs[l].stockCount), /pendant le comptage|during the count/);
});

test('passerelle et reprise : mine=true, plus de page de 200 filtree', () => {
    const g = read(GATEWAY);
    assert.ok(g.includes('params: clean({ date_from: dateFrom, date_to: dateTo, status, limit, offset, mine })'));
    const s = read(STORE);
    assert.match(s, /StockCountGateway\.list\(\{ status: 'en_cours', mine: true, limit: 1 \}\)/);
    assert.doesNotMatch(s, /started_by === myId|limit: 200/);
});

test('historique pagine : 50 par page, precedent/suivant, page remise a 1 par les filtres', async () => {
    const pages = [];
    const store = await loadStoreWith({
        list: async (p) => { pages.push(p); return { items: [{ id: p.offset + 1 }], total: 120, limit: p.limit, offset: p.offset }; },
    });
    await store.loadHistory({ dateFrom: '2026-10-01' }, 2);
    assert.deepEqual(pages.at(-1), { dateFrom: '2026-10-01', status: 'valide', limit: 50, offset: 50 });
    assert.deepEqual(store.history, { items: [{ id: 51 }], total: 120, limit: 50, offset: 50 });
    const h = read(HISTORY);
    assert.match(h, /:disabled="page <= 1 \|\| store\.isLoadingHistory"/);
    assert.match(h, /:disabled="page >= pageCount \|\| store\.isLoadingHistory"/);
    assert.match(h, /stockCount\.page_range/);
    assert.match(h, /function applyFilters\(\) \{[\s\S]*?page\.value = 1;/);
    assert.match(msgs.fr.stockCount.page_range, /\{from\} à \{to\} sur \{total\}/);
});
// ---------- tour 4 : horloge du navigateur (client_now) ----------
test('validation : le corps porte client_now, instant ISO pris au moment de l envoi', async () => {
    assert.ok(read(GATEWAY).includes('api.post(`/stock-counts/${id}/submit`, { client_now: clientNow, lines })'));
    const sent = [];
    const store = await loadStoreWith({
        start: async () => ({ id: 5, products: [] }),
        submit: async (id, lines, clientNow) => { sent.push({ id, lines, clientNow }); return { id, lines: [] }; },
        getStatus: async () => ({}),
    });
    await store.start('tous');
    const before = Date.now();
    await store.submit([{ product_id: 1, counted_qty: 2 }]);
    const { clientNow } = sent[0];
    assert.equal(typeof clientNow, 'string');
    assert.match(clientNow, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    assert.ok(Math.abs(Date.parse(clientNow) - before) < 5000);
    assert.match(read(STORE), /StockCountGateway\.submit\(open\.value\.id, lines, instantISO\(\)\)/);
    assert.doesNotMatch(read(STORE), /toISOString/);
});
