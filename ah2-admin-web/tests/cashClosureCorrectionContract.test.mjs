// Demande de regularisation par la secretaire (POST /cash-closure/{id}/corrections), depuis le resultat revele.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const templateOf = (src) => src.slice(0, src.indexOf('<script'));
const FORBIDDEN = /[—–…·→←−•]|\p{Extended_Pictographic}/u;

const VIEW = read('src/views/modules/caisse/CashClosure.vue');
const GATEWAY = read('src/services/CashClosureGateway.js');
const STORE = read('src/stores/cashClosureStore.js');

test('passerelle : requestCorrection envoie exactement mode_code, amount_delta, reason', () => {
    assert.ok(GATEWAY.includes('api.post(`/cash-closure/${closureId}/corrections`, {'));
    assert.ok(GATEWAY.includes('mode_code: modeCode, amount_delta: amountDelta, reason,'));
});

test('store : requestCorrection vise la cloture revelee', () => {
    assert.match(STORE, /async function requestCorrection\(\{ modeCode, amountDelta, reason \}\)/);
    assert.match(STORE, /CashClosureGateway\.requestCorrection\(result\.value\.id,/);
    assert.match(STORE, /isRequestingCorrection, requestCorrection/);
});

test('regles : montant signe non nul en chaine', async () => {
    const { normalizeSignedAmount } = await import('../src/utils/cashClosure.js');
    assert.equal(normalizeSignedAmount('-1 500,5'), '-1500.5');
    assert.equal(normalizeSignedAmount('+200'), '200');
    assert.equal(normalizeSignedAmount('300'), '300');
    assert.equal(normalizeSignedAmount('0'), null);
    assert.equal(normalizeSignedAmount('-0.00'), null);
    assert.equal(normalizeSignedAmount('abc'), null);
    assert.equal(normalizeSignedAmount('1.234'), null);
    assert.equal(normalizeSignedAmount(''), null);
});

test('ecran : formulaire repliable SEULEMENT dans la section du resultat revele', () => {
    const tpl = templateOf(VIEW);
    const start = tpl.indexOf('v-if="store.result"');
    const form = tpl.indexOf('id="cash-correction-form"');
    assert.ok(start > 0 && form > start, 'formulaire dans le resultat');
    assert.match(tpl, /<form v-if="showCorrection" id="cash-correction-form"/);
    assert.match(tpl, /v-for="l in store\.result\.lines"/);
    assert.match(tpl, /:aria-expanded=/);
    for (const id of ['correction-mode', 'correction-amount', 'correction-reason']) assert.match(tpl, new RegExp(`id="${id}"[^>]*required`), id);
});

test('ecran : verrou d\'envoi synchrone, messages de succes et d\'erreur', () => {
    const body = VIEW.slice(VIEW.indexOf('async function handleCorrection()'), VIEW.indexOf('async function handleSubmit()'));
    assert.match(body, /if \(correctionSending\.value \|\| !canRequestCorrection\.value\) return;/);
    assert.ok(body.indexOf('correctionSending.value = true;') < body.indexOf('await'), 'verrou avant le premier await');
    assert.match(body, /finally \{\s*correctionSending\.value = false;/);
    assert.match(body, /normalizeSignedAmount\(correction\.amount\)/);
    assert.match(body, /correction\.reason\.trim\(\)/);
    assert.match(body, /cashClosure\.correction_success/);
    assert.match(body, /describeServerError\(err/);
    assert.match(VIEW, /:disabled="!canRequestCorrection"/);
    assert.match(templateOf(VIEW), /v-if="correctionError" role="alert"/);
    assert.match(templateOf(VIEW), /v-if="correctionDone" role="status"/);
});

test('i18n : cles de regularisation en FR et EN, sans caractere interdit, phrase sur la periode suivante', () => {
    const keys = ['correction_title', 'correction_toggle', 'correction_hide', 'correction_help', 'correction_mode', 'correction_mode_placeholder',
        'correction_amount', 'correction_amount_help', 'correction_amount_invalid', 'correction_reason', 'correction_submit',
        'correction_submitting', 'correction_success', 'correction_error'];
    for (const l of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[l].cashClosure[k];
            assert.equal(typeof v, 'string', `${l}.${k}`);
            assert.doesNotMatch(v, FORBIDDEN, `${l}.${k}`);
        }
    }
    assert.match(msgs.fr.cashClosure.correction_help, /comptée dans la période suivante/);
});
