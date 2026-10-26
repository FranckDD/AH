import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const review = read('../src/views/modules/caisse/DiscountReview.vue');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : la décision d'une réduction (pourcentage, échéance, mot de passe, approuver ou refuser) ---
check('DiscountReview', review, [
    "api.get('/discount-requests/pending')", 'pending.value = res.data || [];', 'onMounted(fetchPending);',
    'api.post(`/discount-requests/${req.id}/decide`, {', "password: passwordInput[req.id] || '',", 'refuse,',
    'decision_percent: refuse ? null : (selectedPercent[req.id] || null),', 'decision_echelonne_deadline: refuse ? null : (selectedDeadline[req.id] || null),',
    'pending.value = pending.value.filter((r) => r.id !== req.id);', "errorFor[req.id] = '';",
    "errorFor[req.id] = describeServerError(err, 'Erreur lors de la décision.');",
    'v-for="pct in [10, 20, 50, 100]"', '@click="selectedPercent[req.id] = pct"', 'selectedPercent[req.id] === pct',
    'v-model="selectedDeadline[req.id]"', 'type="date"', 'v-model="passwordInput[req.id]"', 'type="password"',
    '@click="submitDecision(req, false)"', '@click="submitDecision(req, true)"',
    'formatCurrency(req.original_amount)', 'formatDate(req.created_at)', 'req.patient_label', 'req.items_summary', "req.requested_by_name || '?'", 'v-for="req in pending"',
    "new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(v || 0).replace('XOF', 'FCFA')",
    "$t('discount_review.title')", "$t('discount_review.empty')", "$t('discount_review.unknown_patient')", "$t('discount_review.requested_by', { name: req.requested_by_name || '?' })",
    "$t('discount_review.echelonne_deadline')", "$t('discount_review.password_confirm')", "$t('discount_review.approve')", "$t('discount_review.refuse')",
]);

test('toutes les clés discount_review.* et discountReviewScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of review.matchAll(/['"`(]((?:discount_review|discountReviewScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 8);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('DiscountReview : composants ui/, pourcentages en groupe à état écrit, champs étiquetés', () => {
    assert.match(review, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'AppCard', 'FormField', 'AppButton']) assert.match(review, new RegExp(`\\b${c}\\b`), c);
    assert.match(review, /aria-pressed/);
    assert.match(review, /role="alert"/);
    assert.match(review, /autocomplete="current-password"/);
});

test('DiscountReview : Approuver (plein) et Refuser (rouge) sont deux boutons distincts', () => {
    const t = templateOf(review);
    assert.match(t, /variant="danger"[^>]*@click="submitDecision\(req, true\)"|@click="submitDecision\(req, true\)"[^>]*variant="danger"/s);
});

test('DiscountReview : jetons du thème, texte >= 13 px, aucun caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(review, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
    assert.doesNotMatch(review, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(review), /[—–…·]|\p{Extended_Pictographic}/u);
});

test('clés discountReviewScreens.* en FR et EN', () => {
    const keys = ['percent_label', 'percent_group', 'password_help'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].discountReviewScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.discountReviewScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.discountReviewScreens.${k}`);
        }
    }
});
