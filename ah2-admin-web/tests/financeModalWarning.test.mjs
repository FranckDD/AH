import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const modal = readFileSync(new URL('../src/components/finance/FinanceModal.vue', import.meta.url), 'utf8');

test('le formulaire de transaction avertit qu elle est reelle et entre dans la cloture', () => {
    assert.ok(modal.includes("t('financeScreens.real_money_warning')"));
    for (const l of ['fr', 'en']) {
        const v = msgs[l].financeScreens.real_money_warning;
        assert.ok(/cl.ture|closing/i.test(v), v);
        assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(v));
    }
});
