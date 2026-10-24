import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const modal = readFileSync(new URL('../src/components/finance/FinanceModal.vue', import.meta.url), 'utf8');
const tpl = modal.slice(0, modal.indexOf('<script'));
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

test('FinanceModal : liste officielle des modes, valeur = code', () => {
    assert.match(modal, /import \{ usePaymentModes \} from '@\/utils\/paymentModes';/);
    assert.match(modal, /const paymentModes = usePaymentModes\(\);/);
    assert.match(tpl, /<option v-for="m in paymentModes" :key="m\.code" :value="m\.code">\{\{ m\.label \}\}<\/option>/);
});

test('FinanceModal : plus de Virement, Cheque ni ancien texte libre', () => {
    assert.doesNotMatch(modal, /Virement|Chèque|Cheque|Mobile Money|value="Espèces"|payment_methods\./);
});

test('FinanceModal : choix du mode obligatoire, sans defaut', () => {
    assert.match(tpl, /<select id="fin-method" v-model="form\.paymentMethod" required/);
    assert.match(tpl, /<option value="" disabled>\{\{ t\('paymentModeChoice\.placeholder'\) \}\}<\/option>/);
    assert.match(modal, /paymentMethod: '',/);
    assert.match(modal, /if \(!form\.paymentMethod\) \{/);
});

test('cles i18n du mode : FR et EN presentes, ponctuation ASCII', () => {
    const keys = ['paymentModeChoice.placeholder', 'finance.modal.method',
        ...['especes', 'orange_money', 'mtn_money', 'autre_mobile'].map((c) => `paymentModes.${c}`)];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = pick(msgs[locale], k);
            assert.equal(typeof v, 'string', `${locale}.${k}`);
            assert.ok(v.length > 0, `${locale}.${k}`);
            assert.doesNotMatch(v, /[—–·…→←]|\p{Extended_Pictographic}/u, `${locale}.${k}`);
        }
    }
});

test('gabarit : aucun caractere typographique interdit', () => {
    assert.doesNotMatch(tpl, /[—–·…→←]|\p{Extended_Pictographic}/u);
});
