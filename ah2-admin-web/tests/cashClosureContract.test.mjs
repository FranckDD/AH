// Contrat de la cloture de caisse (Tache 9) : comptage a l'aveugle, file de synchro, commentaire d'ecart,
// liste officielle des modes dans les trois formulaires, textes FR/EN, caracteres interdits, couleurs, cloche.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const templateOf = (src) => (src.includes('<script') ? src.slice(0, src.indexOf('<script')) : src);
const FORBIDDEN = /[—–…·→←−]|\p{Extended_Pictographic}/u;
const RAW_COLOR = /\b(?:indigo|emerald|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink|cyan|lime|fuchsia|violet|stone|zinc)-\d{2,3}\b/;

const VIEW = 'src/views/modules/caisse/CashClosure.vue';
const STORE = 'src/stores/cashClosureStore.js';
const GATEWAY = 'src/services/CashClosureGateway.js';
const MODES = 'src/utils/paymentModes.js';
const RULES = 'src/utils/cashClosure.js';
const FORMS = ['src/components/caisse/RetraitModal.vue', 'src/components/caisse/CaisseInvoiceModal.vue', 'src/components/caisse/CaisseInstallmentModal.vue'];

for (const f of [VIEW, STORE, GATEWAY, MODES, RULES]) {
    test(`${f} existe`, () => assert.ok(existsSync(new URL(`../${f}`, import.meta.url)), f));
}

// ---------- modes de paiement ----------
test('paymentModes : liste figee de repli = les 4 codes officiels, gelee, avec leur source', async () => {
    const m = await import('../src/utils/paymentModes.js');
    assert.deepEqual(m.FALLBACK_PAYMENT_MODES.map((x) => x.code), ['especes', 'orange_money', 'mtn_money', 'autre_mobile']);
    assert.ok(Object.isFrozen(m.FALLBACK_PAYMENT_MODES));
    assert.ok(m.FALLBACK_PAYMENT_MODES.every(Object.isFrozen));
    assert.equal(m.FALLBACK_PAYMENT_MODES[0].source, 'physical');
    assert.ok(m.FALLBACK_PAYMENT_MODES.slice(1).every((x) => x.source === 'operator_statement'));
});

test('paymentModes : normalisation des anciennes valeurs comme le serveur', async () => {
    const { normalizeMode } = await import('../src/utils/paymentModes.js');
    assert.equal(normalizeMode('Espèces'), 'especes');
    assert.equal(normalizeMode('Cash'), 'especes');
    assert.equal(normalizeMode('ESPECES'), 'especes');
    assert.equal(normalizeMode('Mobile Money'), 'autre_mobile');
    assert.equal(normalizeMode('orange_money'), 'orange_money');
    assert.equal(normalizeMode('MTN MoMo'), 'mtn_money');
    assert.equal(normalizeMode('Virement'), 'non_classe');
    assert.equal(normalizeMode(null), null);
    assert.equal(normalizeMode('  '), null);
});

test('paymentModes : modeLabel donne un libelle lisible pour codes, anciennes valeurs et vides', async () => {
    const { modeLabel } = await import('../src/utils/paymentModes.js');
    assert.equal(modeLabel('orange_money'), msgs.fr.paymentModes.orange_money);
    assert.equal(modeLabel('Espèces'), msgs.fr.paymentModes.especes);
    assert.equal(modeLabel('Cash'), msgs.fr.paymentModes.especes);
    assert.equal(modeLabel('Mobile Money'), msgs.fr.paymentModes.autre_mobile);
    assert.equal(modeLabel(null), msgs.fr.paymentModes.non_classe);
    assert.equal(modeLabel('non_classe'), msgs.fr.paymentModes.non_classe);
    assert.equal(modeLabel('Virement'), 'Virement', 'une ancienne valeur inconnue reste lisible telle quelle');
});

test('paymentModes : loadPaymentModes lit GET /payment-modes et retombe sur la liste figee', () => {
    const src = read(MODES);
    assert.match(src, /api\.get\('\/payment-modes'\)/);
    assert.match(src, /catch/);
    assert.match(src, /FALLBACK_PAYMENT_MODES/);
    assert.match(src, /is_active/);
});

for (const f of FORMS) {
    test(`${f} : choix du mode = liste officielle, plus de Virement ni de Cheque`, () => {
        const src = read(f);
        assert.match(src, /from '@\/utils\/paymentModes'/);
        assert.match(src, /usePaymentModes\(\)/);
        assert.match(src, /v-for="m in paymentModes"/);
        assert.match(src, /:value="m\.code"/);
        assert.doesNotMatch(src, /Virement|Chèque|Cheque|payment_methods\.(transfer|check)/);
        assert.doesNotMatch(src, /value="Espèces"|value="Mobile Money"/);
        if (!f.includes('RetraitModal')) assert.match(src, /ref\('especes'\)/, 'especes par defaut');
    });
}

test('RetraitModal : le mode est obligatoire dans le formulaire', () => {
    const src = read(FORMS[0]);
    assert.match(src, /id="retrait-method"[^>]*required/);
    assert.match(src, /const isFormValid = computed\(\(\) => Number\(form\.amount\) > 0 && form\.justification\.trim\(\)\.length > 0 && !!form\.paymentMethod\);/);
});

test('RetraitModal : aucun mode par defaut, premiere option vide « Choisir un mode »', () => {
    const src = read(FORMS[0]);
    assert.match(src, /paymentMethod: '',/);
    assert.match(src, /<option value="" disabled>\{\{ t\('paymentModeChoice\.placeholder'\) \}\}<\/option>/);
    for (const l of ['fr', 'en']) {
        const v = msgs[l].paymentModeChoice?.placeholder;
        assert.equal(typeof v, 'string');
        assert.doesNotMatch(v, FORBIDDEN);
    }
});

test('tickets : libelle du mode dans les deux chemins d impression, donnees stockees intactes', () => {
    const src = read('src/views/modules/finance/CaisseList.vue');
    // modeLabel seulement si la valeur existe : vide reste vide (le pont n'imprime alors pas de ligne Mode)
    assert.match(src, /printTicket\(\{ \.\.\.resp\.data, payment_method: resp\.data\?\.payment_method \? modeLabel\(resp\.data\.payment_method\) : resp\.data\?\.payment_method,/);
    assert.match(src, /payment_method: payload\.payment_method \? modeLabel\(payload\.payment_method\) : payload\.payment_method,/);
    assert.doesNotMatch(src, /payment_method: modeLabel\(/, 'jamais de modeLabel inconditionnel');
    const bell = read('src/components/notifications/NotificationBell.vue');
    assert.match(bell, /const pm = resp\.data\?\.payment_method;\s*await PrinterBridgeGateway\.printTicket\(\{ \.\.\.resp\.data, payment_method: pm \? modeLabel\(pm\) : pm \}\);/);
    assert.doesNotMatch(bell, /printTicket\(resp\.data\)/);
    assert.match(bell, /import \{ modeLabel \} from '@\/utils\/paymentModes'/);
    assert.match(src, /import \{ modeLabel \} from '@\/utils\/paymentModes'/);
});

test('FinancialList affiche le libelle du mode', () => {
    assert.match(read('src/views/modules/finance/FinancialList.vue'), /modeLabel\(tx\.paymentMethod\)/);
});

test('les listes de retraits affichent le libelle du mode, pas la valeur brute', () => {
    const src = read('src/views/modules/finance/RetraitList.vue');
    assert.match(src, /modeLabel\(r\.payment_method\)/);
});

// ---------- passerelle ----------
test('passerelle : une fonction par route, POST ne transmet que counts et last_closed_at', () => {
    const src = read(GATEWAY);
    for (const r of ["api.get('/cash-closure/status')", "api.post('/cash-closure/catchup')", "api.post('/cash-closure', { counts, last_closed_at: lastClosedAt })",
        "api.get('/cash-closure', {",
        'params: clean({ date_from: dateFrom, date_to: dateTo, kind, limit, offset })', 'api.get(`/cash-closure/${id}`)']) {
        assert.ok(src.includes(r), r);
    }
    assert.doesNotMatch(src, /parseFloat|Number\(/, 'les montants restent des chaines');
});

// ---------- a l'aveugle ----------
test('store : le statut est le seul etat avant validation, aucune cle d\'attendu lue avant le resultat', () => {
    const src = read(STORE);
    const before = src.slice(0, src.indexOf('async function submit'));
    assert.doesNotMatch(before, /expected|difference|entries|exits/);
    assert.match(src, /CashClosureGateway\.catchup\(\)[\s\S]*CashClosureGateway\.getStatus\(\)/, 'rattrapage puis statut');
    assert.doesNotMatch(src, /powersync-client|db\.(execute|writeTransaction|getAll)/, 'aucun acces PowerSync');
});

test('ecran : chaque lecture d\'attendu/ecart est dans la section du resultat revele', () => {
    const tpl = templateOf(read(VIEW));
    const start = tpl.indexOf('v-if="store.result"');
    assert.ok(start > 0, 'section du resultat absente');
    const formStart = tpl.indexOf('<form');
    assert.ok(formStart > 0 && formStart < start, 'le formulaire precede le resultat');
    for (const m of tpl.matchAll(/expected|difference|\.entries|\.exits|opening/g)) {
        assert.ok(m.index > start, `${m[0]} lu hors de la section revelee`);
    }
});

// ---------- file de synchro ----------
test('regles : la cloture est bloquee hors ligne, en erreur, et tant que la file n\'est pas vide', async () => {
    const { queueBlockReason } = await import('../src/utils/cashClosure.js');
    assert.equal(queueBlockReason({ state: 'online', pending: 0 }), null);
    assert.equal(queueBlockReason({ state: 'offline', pending: 0 }), 'cashClosure.blocked_offline');
    assert.equal(queueBlockReason({ state: 'error', pending: 2 }), 'cashClosure.blocked_error');
    assert.equal(queueBlockReason({ state: 'pending', pending: 3 }), 'cashClosure.blocked_pending');
    assert.equal(queueBlockReason({ state: 'syncing', pending: 0 }), 'cashClosure.blocked_pending');
    assert.equal(queueBlockReason({ state: 'online', pending: 1 }), 'cashClosure.blocked_pending');
});

test('ecran : bouton inactif avec message tant que la file bloque, file relue juste avant l\'envoi', () => {
    const src = read(VIEW);
    assert.match(src, /useConnectionStatus\(\)/);
    assert.match(src, /queueBlockReason\(/);
    assert.match(src, /:disabled="!canSubmit"/);
    assert.match(src, /const canSubmit = computed\(\(\) => !blockReason\.value/);
    assert.match(src, /db\.getUploadQueueStats\(\)/);
    assert.match(templateOf(src), /v-if="blockReason"/);
});

// ---------- commentaire d'ecart ----------
test('regles : mode nomme par le refus du serveur (commentaire obligatoire)', async () => {
    const { commentRequiredMode } = await import('../src/utils/cashClosure.js');
    assert.equal(commentRequiredMode("Commentaire obligatoire pour l'ecart du mode especes"), 'especes');
    assert.equal(commentRequiredMode("Commentaire obligatoire pour l'ecart du mode orange_money"), 'orange_money');
    assert.equal(commentRequiredMode('Montant compte (especes) invalide.'), null);
    assert.equal(commentRequiredMode(undefined), null);
});

test('regles : comptage envoye en chaines, commentaire seulement s\'il est non vide', async () => {
    const { buildCounts, normalizeAmount } = await import('../src/utils/cashClosure.js');
    assert.equal(normalizeAmount('1 500,5'), '1500.5');
    assert.equal(normalizeAmount(2000), '2000');
    assert.equal(normalizeAmount('-1'), null);
    assert.equal(normalizeAmount(''), null);
    assert.equal(normalizeAmount('1.234'), null);
    const out = buildCounts([{ code: 'especes' }, { code: 'mtn_money' }],
        { especes: { counted: '1000', comment: '  ' }, mtn_money: { counted: 0, comment: ' manque ' } });
    assert.deepEqual(out, [{ mode: 'especes', counted: '1000' }, { mode: 'mtn_money', counted: '0', comment: 'manque' }]);
});

test('regles : ecart dit en mots', async () => {
    const { gapWords } = await import('../src/utils/cashClosure.js');
    assert.deepEqual(gapWords('500.00'), { key: 'cashClosure.gap_over', amount: '500.00' });
    assert.deepEqual(gapWords('-250'), { key: 'cashClosure.gap_under', amount: '250' });
    assert.deepEqual(gapWords('0.00'), { key: 'cashClosure.gap_none', amount: '0' });
    assert.deepEqual(gapWords(null), { key: 'cashClosure.gap_not_counted', amount: null });
});

test('ecran : etape de commentaire apres un refus 422, envoi bloque tant qu\'un commentaire exige manque', () => {
    const src = read(VIEW);
    assert.match(src, /commentRequiredMode\(/);
    assert.match(src, /requiredComments/);
    assert.match(src, /cashClosure\.comment_required_step/);
    assert.match(src, /missingComments/);
});

test('double envoi : verrou synchrone pose avant toute attente, relache en finally', () => {
    const src = read(VIEW);
    const body = src.slice(src.indexOf('async function handleSubmit()'), src.indexOf('async function doSubmit()'));
    assert.match(body, /if \(submitting\.value\) return;/);
    const set = body.indexOf('submitting.value = true;');
    assert.ok(set > 0 && set < body.indexOf('await'), 'verrou pose avant le premier await');
    assert.match(body, /finally \{\s*submitting\.value = false;/);
    assert.match(src, /!store\.isSubmitting && !submitting\.value\)/);
});

test('store : un 409 ne recharge pas (et n efface pas) un resultat deja revele', () => {
    assert.match(read(STORE), /if \(err\?\.response\?\.status === 409 && !result\.value\) await load\(\);/);
});

test('aide de format des montants sous les champs de comptage', () => {
    assert.match(read(VIEW), /cashClosure\.amount_format_help/);
    for (const l of ['fr', 'en']) assert.match(msgs[l].cashClosure.amount_format_help, /^[ -~]+$/, 'ASCII');
});

test('ecran : 409 = statut recharge et information', () => {
    const src = read(VIEW) + read(STORE);
    assert.match(src, /409/);
    assert.match(src, /cashClosure\.conflict_refreshed/);
});

// ---------- textes, couleurs, tailles ----------
const flatten = (obj, prefix = '') => Object.entries(obj).flatMap(([k, v]) => (v && typeof v === 'object' ? flatten(v, `${prefix}${k}.`) : [[`${prefix}${k}`, v]]));

for (const ns of ['cashClosure', 'paymentModes']) {
    test(`i18n : ${ns}.* identiques en FR et EN, non vides, sans caractere interdit`, () => {
        const fr = flatten(msgs.fr[ns] || {});
        const en = flatten(msgs.en[ns] || {});
        assert.ok(fr.length >= 5, `${ns} FR vide`);
        assert.deepEqual(fr.map(([k]) => k).sort(), en.map(([k]) => k).sort());
        for (const [k, v] of [...fr, ...en]) {
            assert.equal(typeof v, 'string', k);
            assert.ok(v.trim(), k);
            assert.doesNotMatch(v, FORBIDDEN, `${ns}.${k}`);
        }
    });
}

test('i18n : toutes les cles cashClosure.* citees existent en FR et EN', () => {
    const pick = (o, p) => p.split('.').reduce((x, k) => x?.[k], o);
    const used = new Set();
    for (const f of [VIEW, RULES, STORE]) for (const m of read(f).matchAll(/['"`]((?:cashClosure|paymentModes)\.[a-z_]+)['"`]/g)) used.add(m[1]);
    assert.ok(used.size > 10);
    for (const k of used) for (const l of ['fr', 'en']) assert.equal(typeof pick(msgs[l], k), 'string', `${l}.${k}`);
});

test('i18n : notifications.cash_closure* en FR et EN sans caractere interdit', () => {
    for (const k of ['cash_closure', 'cash_closure_auto', 'cash_closure_anomaly']) {
        for (const l of ['fr', 'en']) {
            const v = msgs[l].notifications[k];
            assert.equal(typeof v, 'string', `${l}.${k}`);
            assert.doesNotMatch(v, FORBIDDEN);
        }
    }
});

for (const f of [VIEW, STORE, GATEWAY, MODES, RULES, ...FORMS]) {
    test(`${f} : jetons de couleur, texte >= 13 px, aucun caractere interdit`, () => {
        const src = read(f);
        assert.doesNotMatch(src, RAW_COLOR);
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/);
        assert.doesNotMatch(src, /\btext-xs\b|text-\[(?:[0-9]|1[0-2])px\]/);
        assert.doesNotMatch(f.endsWith('.vue') ? templateOf(src) : src, FORBIDDEN);
    });
}

test('ecran : bibliotheque ui/, cibles >= 44 px pour les champs', () => {
    const src = read(VIEW);
    assert.match(src, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'AppButton', 'FormField', 'ResponsiveTable', 'AppCard']) assert.match(src, new RegExp(`\\b${c}\\b`), c);
    assert.match(src, /min-h-11/);
});

// ---------- cloche ----------
test('NotificationBell connait cash_closure : libelle i18n et route reservee promoteur/admin', () => {
    const src = read('src/components/notifications/NotificationBell.vue');
    assert.match(src, /n\.type === 'cash_closure'/);
    assert.match(src, /notifications\.cash_closure_auto/);
    assert.match(src, /notifications\.cash_closure_anomaly/);
    assert.match(src, /authStore\.hasRole\(\['promoteur', 'admin'\]\)\) pushIfRoute\('\/dashboard\/cash-closures'\)/);
});
