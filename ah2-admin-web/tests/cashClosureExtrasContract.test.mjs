// Detail d'une cloture : ventes annulees de la periode et regularisations appliquees, cote secretaire et revue.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const templateOf = (src) => src.slice(0, src.indexOf('<script'));
const FORBIDDEN = /[—–…·→←−•]|\p{Extended_Pictographic}/u;

test('regles : lecture defensive (cles absentes = listes vides)', async () => {
    const { closureCancellations, closureAppliedCorrections } = await import('../src/utils/cashClosure.js');
    assert.deepEqual(closureCancellations({}), []);
    assert.deepEqual(closureCancellations(null), []);
    assert.deepEqual(closureAppliedCorrections({ corrections_applied: null }), []);
});

test('regles : champs des regularisations appliquees (controller _detail)', async () => {
    const { closureAppliedCorrections } = await import('../src/utils/cashClosure.js');
    const out = closureAppliedCorrections({ corrections_applied: [{ id: 3, mode: 'especes', amount_delta: '-500.00', reason: 'erreur' }] });
    assert.deepEqual(out, [{ key: '3', mode: 'especes', amount: '-500.00', reason: 'erreur' }]);
});

test('regles : champs des annulations', async () => {
    const { closureCancellations } = await import('../src/utils/cashClosure.js');
    const [row] = closureCancellations({ cancellations: [{ id: 9, author_name: 'Awa', amount: '2000.00', justification: 'double saisie', reference: 'V-9' }] });
    assert.equal(row.author, 'Awa');
    assert.equal(row.amount, '2000.00');
    assert.equal(row.justification, 'double saisie');
    assert.equal(row.reference, 'V-9');
});

test('regles : forme reelle du detail (controller _detail, cancellations)', async () => {
    const { closureCancellations } = await import('../src/utils/cashClosure.js');
    const [row] = closureCancellations({ cancellations: [{ transaction_id: 'abc-1', cancelled_at: 'x', cancelled_by: 4,
        cancelled_by_name: 'Awa Diop', justification: 'erreur', invoice_amount: '5000.00', amount: '3000.00', by_mode: {} }] });
    assert.deepEqual(row, { key: 'abc-1', author: 'Awa Diop', amount: '3000.00', justification: 'erreur', reference: 'abc-1' });
});

for (const [file, src] of [['CashClosure.vue', 'store.result'], ['CashClosuresReview.vue', 'review.selected']]) {
    test(`${file} : sections annulations et regularisations, avec texte vide`, () => {
        const view = read(`src/views/modules/caisse/${file}`);
        const tpl = templateOf(view);
        for (const k of ['cancellations_title', 'cancellations_empty', 'applied_title', 'applied_empty']) assert.ok(tpl.includes(`t('cashClosure.${k}')`), k);
        assert.match(tpl, /v-if="!cancellations\.length"/);
        assert.match(tpl, /v-if="!appliedCorrections\.length"/);
        assert.ok(view.includes(`closureCancellations(${src})`));
        assert.ok(view.includes(`closureAppliedCorrections(${src})`));
        assert.match(tpl, /appliedDeltaText\(row\.amount\)/);
    });
}

test('CashClosure.vue : les sections sont dans le resultat revele', () => {
    const tpl = templateOf(read('src/views/modules/caisse/CashClosure.vue'));
    assert.ok(tpl.indexOf("t('cashClosure.cancellations_title')") > tpl.indexOf('v-if="store.result"'));
});

test('i18n : cles des sections en FR et EN sans caractere interdit', () => {
    const keys = ['cancellations_title', 'cancellations_empty', 'cancel_col_reference', 'cancel_col_author', 'cancel_col_amount',
        'cancel_col_justification', 'applied_title', 'applied_empty', 'applied_col_amount', 'applied_col_reason', 'applied_plus', 'applied_minus'];
    for (const l of ['fr', 'en']) for (const k of keys) {
        const v = msgs[l].cashClosure[k];
        assert.equal(typeof v, 'string', `${l}.${k}`);
        assert.doesNotMatch(v, FORBIDDEN);
    }
});
