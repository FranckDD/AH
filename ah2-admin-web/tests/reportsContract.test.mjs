// Page Rapports (tache 7) : passerelle, magasin, 13 cartes, encadre du controle, tableau, reglages, textes.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const R = await import('../src/utils/reports.js');

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const root = (p) => readFileSync(new URL(`../../${p}`, import.meta.url), 'utf8');
const gateway = read('src/services/ReportsGateway.js');
const store = read('src/stores/reportsStore.js');
const page = read('src/views/modules/reports/Reports.vue');
const compDir = new URL('../src/components/reports/', import.meta.url);
const comps = Object.fromEntries(readdirSync(compDir).filter((f) => f.endsWith('.vue'))
    .map((f) => [f, readFileSync(new URL(f, compDir), 'utf8')]));
const allUi = [page, ...Object.values(comps)].join('\n');
const allSrc = [gateway, store, read('src/utils/reports.js'), allUi].join('\n');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const FORBIDDEN = /[—–…·•→←]|\p{Extended_Pictographic}/u;

// ---------------- passerelle ----------------
test('passerelle : chemins et parametres /reports', () => {
    assert.match(gateway, /api\.get\('\/reports\/overview'/);
    assert.match(gateway, /api\.get\('\/reports\/daily-control'/);
    assert.match(gateway, /api\.get\('\/reports\/products-sold'/);
    assert.match(gateway, /api\.get\('\/reports\/settings'\)/);
    assert.match(gateway, /api\.put\('\/reports\/settings'/);
    for (const p of ['date_from', 'date_to', 'item_type', 'category', 'sort', 'limit', 'offset', 'q']) {
        assert.ok(gateway.includes(p), p);
    }
    assert.match(gateway, /cancelled_sales_threshold: Number\(/);
    assert.match(gateway, /adjustment_pending_days: Number\(/);
    assert.match(gateway, /limit: Number\(/);
    assert.match(gateway, /offset: Number\(/);
});

test('aucune date seule par toISOString', () => {
    assert.doesNotMatch(allSrc, /toISOString/);
});

// ---------------- dates et periode ----------------
test('periode : aujourd hui, 7 jours, 30 jours en jours locaux', () => {
    const now = new Date(2026, 9, 25, 23, 50); // soir local
    assert.deepEqual(R.periodRange('today', now), { from: '2026-10-25', to: '2026-10-25' });
    assert.deepEqual(R.periodRange('7d', now), { from: '2026-10-19', to: '2026-10-25' });
    assert.deepEqual(R.periodRange('30d', now), { from: '2026-09-26', to: '2026-10-25' });
    assert.deepEqual(R.periodRange('custom', now, { from: '2026-10-01', to: '2026-10-03' }),
        { from: '2026-10-01', to: '2026-10-03' });
});

test('periode libre : fin >= debut, 366 jours au plus', () => {
    assert.equal(R.customPeriodError('2026-10-01', '2026-10-03'), '');
    assert.equal(R.customPeriodError('2026-10-04', '2026-10-03'), 'reports.period.err_order');
    assert.equal(R.customPeriodError('', '2026-10-03'), 'reports.period.err_missing');
    assert.equal(R.customPeriodError('2025-01-01', '2026-10-03'), 'reports.period.err_too_long');
    assert.equal(R.customPeriodError('2025-10-03', '2026-10-03'), '');
});

test('date locale lisible sans decalage de fuseau', () => {
    const s = R.formatLocalDate('2026-10-25', 'fr');
    assert.match(s, /25/);
    assert.match(s, /2026/);
    assert.equal(R.formatLocalDate('', 'fr'), '');
});

// ---------------- montants ----------------
test('montants : chaines a 2 decimales, groupement, FCFA, pas de flottant', () => {
    assert.equal(R.formatMoney('0.00'), '0 FCFA');
    assert.equal(R.formatMoney('1500.00'), '1 500 FCFA');
    assert.equal(R.formatMoney('1234567.50'), '1 234 567,50 FCFA');
    assert.equal(R.formatMoney('-2500.05'), '-2 500,05 FCFA');
    assert.equal(R.formatMoney('123456789012345678.99'), '123 456 789 012 345 678,99 FCFA');
    assert.equal(R.formatMoney('10.999'), '10,99 FCFA');
    assert.equal(R.formatMoney(null), '');
    assert.equal(R.formatMoney(undefined), '');
});

// ---------------- 13 cartes ----------------
test('13 cartes en quatre blocs', () => {
    assert.deepEqual(R.CARD_BLOCKS.map((b) => b.key), ['money', 'products', 'production', 'growth']);
    const ids = R.CARD_BLOCKS.flatMap((b) => b.cards);
    assert.equal(ids.length, 13);
    assert.deepEqual(ids, ['collected', 'cash_gaps', 'withdrawals_and_cancellations', 'discounts', 'per_secretary',
        'sold_vs_received', 'stock_count', 'low_stock', 'batches', 'bottles', 'loss_and_cost', 'people', 'sales']);
});

const OVERVIEW = {
    money: Object.fromEntries(['collected', 'cash_gaps', 'withdrawals_and_cancellations', 'discounts', 'per_secretary']
        .map((id) => [id, { id, period: { from: '2026-10-01', to: '2026-10-07' }, source: `src ${id}` }])),
    products: {
        sold_vs_received: { id: 'sold_vs_received', period: { from: 'a', to: 'b' }, source: 's', current_state: false },
        stock_count: { id: 'stock_count', period: { from: 'a', to: 'b' }, source: 's', current_state: true, as_of: '2026-10-25T10:00:00+00:00' },
        low_stock: { id: 'low_stock', period: { from: 'a', to: 'b' }, source: 's', current_state: true, as_of: '2026-10-25T10:00:00+00:00' },
    },
    production: Object.fromEntries(['batches', 'bottles', 'loss_and_cost'].map((id) => [id, { id, period: {}, source: 's' }])),
    growth: Object.fromEntries(['new_patients', 'consultations', 'sales'].map((id) => [id, { id, period: {}, source: `g ${id}` }])),
};

test('cardData : chaque carte retrouve ses donnees, la carte 12 reunit patients et consultations', () => {
    for (const id of R.CARD_BLOCKS.flatMap((b) => b.cards)) {
        const c = R.cardData(OVERVIEW, id);
        assert.ok(c, id);
        assert.ok(c.source, `${id} source`);
    }
    const people = R.cardData(OVERVIEW, 'people');
    assert.equal(people.new_patients.id, 'new_patients');
    assert.equal(people.consultations.id, 'consultations');
    assert.match(people.source, /g new_patients/);
    assert.match(people.source, /g consultations/);
    assert.equal(R.cardData(null, 'collected'), null);
});

test('badge etat actuel : seulement si current_state', () => {
    assert.equal(R.currentStateOf(OVERVIEW.products.stock_count).current, true);
    assert.equal(R.currentStateOf(OVERVIEW.products.stock_count).asOf, '2026-10-25T10:00:00+00:00');
    assert.equal(R.currentStateOf(OVERVIEW.products.sold_vs_received).current, false);
    assert.equal(R.currentStateOf({}).current, false);
});

test('ReportCard : titre, periode, source, badge etat actuel', () => {
    const c = comps['ReportCard.vue'];
    assert.ok(c, 'ReportCard.vue');
    assert.match(c, /reports\.card\.period/);
    assert.match(c, /reports\.card\.source/);
    assert.match(c, /reports\.card\.current_state/);
    assert.match(c, /v-if="state\.current"/);
    assert.match(c, /StatusBadge/);
});

test('page : les 13 cartes passent par ReportCard via CARD_BLOCKS', () => {
    assert.match(allUi, /CARD_BLOCKS/);
    assert.match(allUi, /<ReportCard/);
    for (const id of R.CARD_BLOCKS.flatMap((b) => b.cards)) {
        assert.ok(allUi.includes(`'${id}'`), `corps de la carte ${id}`);
    }
});

test('notes obligatoires des cartes 1, 2, 4, 5', () => {
    for (const k of ['reports.notes.collected', 'reports.notes.scope_all_modes', 'reports.notes.per_secretary',
        'reports.labels.of_which_cancelled_later']) {
        assert.ok(allUi.includes(k), k);
    }
    assert.match(allUi, /basis/);
    assert.match(msgs.fr.reports.notes.collected, /annul/i);
    assert.match(msgs.fr.reports.notes.collected, /retrait/i);
});

// ---------------- encadre du controle ----------------
test('controle du jour : etat en mots', () => {
    assert.equal(R.controlState({ items: [] }), 'nothing');
    assert.equal(R.controlState({ items: [{ key: 'a' }] }), 'watch');
    assert.equal(R.controlState(null), 'nothing');
    assert.equal(msgs.fr.reports.control.empty, 'Rien à signaler pour cette période.');
    const box = comps['ReportsControlBox.vue'];
    for (const k of ['reports.control.title', 'reports.control.empty', 'reports.control.state_watch', 'reports.control.state_nothing',
        'reports.control.already_notified', 'reports.control.recomputed', 'reports.control.current_state', 'reports.control.first_seen',
        'reports.kinds.']) {
        assert.ok(box.includes(k), k);
    }
    assert.match(box, /item\.already_notified_on/);
    assert.match(box, /item\.recomputed/);
    assert.match(box, /item\.current_state/);
    assert.match(box, /router\.push\(item\.link\)/);
});

test('chaque nature d anomalie a un libelle FR et EN', () => {
    const kinds = ['cloture_auto', 'ecart_caisse', 'commentaire_manquant', 'ventes_annulees', 'prix_different', 'sortie_autre',
        'lot_hors_tolerance', 'lot_trop_long', 'ecart_expedie_recu', 'comptage_retard', 'comptage_jamais', 'ajustement_en_attente', 'ajustement_caisse_en_attente', 'intrant_sous_seuil'];
    assert.deepEqual([...R.ANOMALY_KINDS].sort(), [...kinds].sort());
    const ctrl = root('controller/reports_controller.py');
    for (const m of ctrl.matchAll(/"kind": "([a-z_]+)"/g)) {
        if (m[1] !== 'kind') assert.ok(kinds.includes(m[1]) || m[1] === 'hors_tolerance' || m[1] === 'lot_trop_long', m[1]);
    }
    for (const k of kinds) for (const l of ['fr', 'en']) {
        assert.ok(pick(msgs[l], `reports.kinds.${k}`), `${l}.reports.kinds.${k}`);
    }
});

// ---------------- courbes ----------------
test('courbes : chart.js a la carte, jetons lus a l execution, derniere semaine partielle, table accessible', () => {
    const c = comps['ReportsGrowthChart.vue'];
    assert.match(c, /from 'chart\.js'/);
    assert.match(c, /Chart\.register\(/);
    assert.doesNotMatch(c, /registerables/);
    assert.match(c, /getComputedStyle/);
    assert.match(c, /--color-/);
    assert.match(c, /segment/);
    assert.match(c, /<table/);
    assert.match(c, /aria-label/);
    assert.deepEqual(R.seriesValues([{ value: '10.50' }, { value: 3 }]), [10.5, 3]);
    assert.equal(R.partialIndex([{ partial: false }, { partial: true }]), 1);
    assert.equal(R.partialIndex([{ partial: false }]), -1);
});

// ---------------- tableau ----------------
test('tableau vendu par produit : recherche differee, filtres, tri, pagination, etats', () => {
    const c = comps['ReportsProductsTable.vue'];
    assert.match(c, /setTimeout\([^]*300\)/);
    for (const v of ['Medicament', 'Examen', 'Consultation', 'Service']) assert.ok(c.includes(`'${v}'`), v);
    for (const s of ['amount_desc', 'amount_asc', 'quantity_desc', 'quantity_asc', 'name_asc']) assert.ok(c.includes(s), s);
    assert.match(c, /reports\.table\.range/);
    assert.match(c, /amount_basis/);
    assert.match(c, /note_key/);
    assert.match(c, /reports\.states\.retry/);
    assert.match(c, /reports\.table\.empty/);
    assert.equal(R.PAGE_SIZE, 50);
    assert.deepEqual(R.pageRange(0, 50, 120), { from: 1, to: 50, total: 120 });
    assert.deepEqual(R.pageRange(100, 20, 120), { from: 101, to: 120, total: 120 });
    assert.deepEqual(R.pageRange(0, 0, 0), { from: 0, to: 0, total: 0 });
});

test('magasin : propriete par utilisateur et reponses perimees ignorees', () => {
    assert.match(store, /function ensureOwner\(/);
    for (const s of ['overviewSeq', 'tableSeq', 'settingsSeq']) {
        assert.ok(store.includes(`++${s}`), s);
        assert.match(store, new RegExp(`if \\(seq !== ${s}\\) return`), s);
    }
    assert.match(page, /store\.ensureOwner\(/);
    assert.match(page, /watch\(\(\) => authStore\.user\?\.id/);
});

// ---------------- reglages ----------------
test('reglages : admin seulement, bornes, garde en vol, message du serveur', () => {
    assert.match(page, /const isAdmin = computed\(\(\) => authStore\.hasRole\(\['admin'\]\)\)/);
    assert.match(page, /<ReportsSettings v-if="isAdmin"/);
    const s = comps['ReportsSettings.vue'];
    assert.match(s, /if \(saving\.value\) return;/);
    assert.match(s, /describeServerError/);
    assert.deepEqual(R.settingsErrors({ cancelled_sales_threshold: '3', adjustment_pending_days: '3' }), {});
    assert.deepEqual(Object.keys(R.settingsErrors({ cancelled_sales_threshold: '0', adjustment_pending_days: '366' })).sort(),
        ['adjustment_pending_days', 'cancelled_sales_threshold']);
    assert.ok(R.settingsErrors({ cancelled_sales_threshold: '1001', adjustment_pending_days: '1.5' }).adjustment_pending_days);
    assert.deepEqual(R.settingsErrors({ cancelled_sales_threshold: '1000', adjustment_pending_days: '365' }), {});
});

// ---------------- route et menu ----------------
test('route /dashboard/reports pour promoteur et admin, entree de menu', () => {
    const router = read('src/router/index.js');
    assert.match(router, /path: 'reports',\s*name: 'reports',\s*component: \(\) => import\('@\/views\/modules\/reports\/Reports\.vue'\),\s*meta: \{ requiresAuth: true, roles: \[ROLES\.ADMIN, ROLES\.PROMOTEUR\] \}/);
    const layout = read('src/components/layout/MainLayout.vue');
    assert.match(layout, /path: '\/dashboard\/reports',\s*labelKey: 'reports\.menu',/);
});

test('la cloche connait daily_control', () => {
    assert.match(read('src/components/notifications/NotificationBell.vue'), /daily_control/);
});

// ---------------- textes ----------------
const flat = (o, p = '') => Object.entries(o).flatMap(([k, v]) => (v && typeof v === 'object' ? flat(v, `${p}${k}.`) : [[`${p}${k}`, v]]));

test('reports.* : memes cles FR et EN, aucun caractere interdit', () => {
    const fr = flat(msgs.fr.reports).map(([k]) => k).sort();
    const en = flat(msgs.en.reports).map(([k]) => k).sort();
    assert.deepEqual(fr, en);
    for (const l of ['fr', 'en']) for (const [k, v] of flat(msgs[l].reports)) {
        assert.ok(typeof v === 'string' && v, `${l}.${k}`);
        assert.doesNotMatch(v, FORBIDDEN, `${l}.${k}`);
    }
});

test('toutes les cles i18n emises par le serveur existent', () => {
    const ctrl = root('controller/reports_controller.py');
    const keys = new Set([...ctrl.matchAll(/"(reports\.[a-z_.]+[a-z_])"/g)].map((m) => m[1]));
    for (const m of ctrl.matchAll(/_card\(\s*"([a-z_]+)"/g)) keys.add(`reports.cards.${m[1]}`);
    for (const m of ctrl.matchAll(/self\._card\(\s*\n?\s*"([a-z_]+)"/g)) keys.add(`reports.cards.${m[1]}`);
    assert.ok(keys.size >= 20, `cles trouvees : ${keys.size}`);
    for (const k of keys) for (const l of ['fr', 'en']) {
        assert.ok(typeof pick(msgs[l], k) === 'string', `${l}.${k}`);
    }
});

test('pages : texte sans caractere interdit, jetons de couleur seulement, ui/', () => {
    for (const [name, src] of Object.entries({ 'Reports.vue': page, ...comps })) {
        assert.doesNotMatch(src, FORBIDDEN, name);
        assert.doesNotMatch(src, /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/, name);
        assert.doesNotMatch(src, /text-(xs)\b|text-\[1[0-2]px\]/, name);
        assert.doesNotMatch(src, /\b(bg|text|border)-(red|green|blue|yellow|gray|slate|orange|emerald|amber)-\d/, name);
    }
    assert.match(page, /from '@\/components\/ui'/);
    for (const f of Object.keys(comps)) {
        assert.ok(read(`src/components/reports/${f}`).split('\n').length <= 450, f);
    }
    assert.ok(page.split('\n').length <= 450);
    assert.ok(existsSync(new URL('../src/components/reports/ReportsControlBox.vue', import.meta.url)));
});

// ---------------- export PDF (tache 8) ----------------
test('export PDF : passerelle en blob avec la periode', () => {
    assert.match(gateway, /async exportPdf\(dateFrom, dateTo\)/);
    assert.match(gateway, /api\.get\('\/reports\/export\.pdf',\s*\{\s*params: clean\(\{ date_from: dateFrom, date_to: dateTo \}\),\s*responseType: 'blob'/);
});

test('export PDF : bouton ui/, periode choisie, garde en vol, telechargement', () => {
    assert.match(page, /<AppButton[^>]*:loading="exporting"[^>]*@click="exportPdf"/);
    assert.match(page, /t\('reports\.export\.button'\)/);
    assert.match(page, /const \{ from, to \} = period\.value;/);
    assert.match(page, /ReportsGateway\.exportPdf\(from, to\)/);
    assert.match(page, /if \(exporting\.value\) return;/);
    assert.match(page, /finally \{\s*exporting\.value = false;/);
    assert.match(page, /URL\.createObjectURL/);
    assert.match(page, /URL\.revokeObjectURL\(url\)/);
    assert.match(page, /download', `rapports_\$\{from\}_\$\{to\}\.pdf`/);
    assert.doesNotMatch(page, /toISOString/);
});

test('export PDF : erreur blob decodee en texte JSON', () => {
    assert.match(page, /instanceof Blob/);
    assert.match(page, /JSON\.parse\(await data\.text\(\)\)\?\.detail/);
    assert.match(page, /exportError\.value = \(await blobErrorDetail\(err\)\) \|\| t\('reports\.export\.error'\)/);
    assert.match(page, /v-if="exportError" role="alert"/);
});

test('export PDF : cles reports.export.* identiques FR et EN', () => {
    for (const l of ['fr', 'en']) {
        assert.deepEqual(Object.keys(msgs[l].reports.export).sort(), ['button', 'error', 'loading']);
        for (const v of Object.values(msgs[l].reports.export)) assert.doesNotMatch(v, FORBIDDEN);
    }
    assert.equal(msgs.fr.reports.export.button, 'Exporter en PDF');
});

// ---------------- revue finale : liens, jours non controles, portees de la carte 11 ----------------
test('lien Ouvrir : meme regle que la garde du routeur', async () => {
    const roles = (r) => ({ matched: [{}], meta: { roles: r } });
    const adminOnly = roles(['admin']); // /dashboard/finance, /dashboard/stock-adjustment-requests
    const both = roles(['StockController', 'admin', 'promoteur']); // /dashboard/stock-count
    assert.equal(R.linkAllowed(adminOnly, 'promoteur'), false);
    assert.equal(R.linkAllowed(adminOnly, 'admin'), true);
    assert.equal(R.linkAllowed(both, 'promoteur'), true);
    assert.equal(R.linkAllowed(both, 'Admin'), true);
    assert.equal(R.linkAllowed(roles(['promoteur']), 'admin'), true);
    assert.equal(R.linkAllowed({ matched: [], meta: {} }, 'admin'), false);
    const router = read('src/router/index.js');
    for (const p of ['finance', 'stock-adjustment-requests']) {
        const at = router.indexOf(`path: '${p}',
        name:`);
        assert.ok(at > 0, p);
        assert.match(router.slice(at, at + 400), /meta: \{\s*requiresAuth: true,\s*roles: \[ROLES\.ADMIN\]\s*\}/, p);
    }
    const box = comps['ReportsControlBox.vue'];
    assert.match(box, /linkAllowed\(router\.resolve\(item\.link\), authStore\.userRole\)/);
    assert.match(box, /<AppButton v-if="canOpen\(item\)"/);
});

test('jours non controles et portees de la carte 11, champs absents toleres', () => {
    const box = comps['ReportsControlBox.vue'];
    assert.match(box, /reports\.control\.uncontrolled_range/);
    assert.match(box, /Number\(props\.control\?\.uncontrolled_days \|\| 0\)/);
    const body = comps['ReportsStockBody.vue'];
    assert.match(body, /c\.cost_per_good_bottle_scope \|\| 'all_time'/);
    assert.match(body, /c\.period_average_unit_cost_scope \|\| 'period'/);
    assert.equal(msgs.fr.reports.scopes.all_time, 'Cumul sur tous les lots expédiés');
    assert.equal(msgs.fr.reports.scopes.period, 'Moyenne de la période');
    const ctrl = root('controller/reports_controller.py');
    for (const m of ctrl.matchAll(/_scope="([a-z_]+)"/g)) for (const l of ['fr', 'en']) {
        assert.ok(pick(msgs[l], `reports.scopes.${m[1]}`), `${l}.reports.scopes.${m[1]}`);
    }
});
