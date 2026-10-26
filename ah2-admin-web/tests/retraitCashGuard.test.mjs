import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');

test('le magasin verifie les especes en ligne avant la saisie et ignore une verification impossible', () => {
    const s = read('../src/stores/retraitStore.js');
    assert.ok(s.includes('CaisseGateway.checkRetraitCash'));
    assert.ok(s.includes("code = 'OVER_CASH'"));
    assert.ok(read('../src/services/CaisseGateway.js').includes("'/retrait/cash-check'"));
});
test('la liste traduit le refus et montre le motif du serveur en 422', () => {
    const v = read('../src/views/modules/finance/RetraitList.vue');
    assert.ok(v.includes("err.code === 'OVER_CASH'"));
    assert.ok(v.includes("t('retraitScreens.over_cash')"));
    assert.ok(v.includes("if (status === 422) return typeof detail === 'string' && detail"));
});
test('libelles FR et EN', () => {
    for (const l of ['fr', 'en']) assert.ok(msgs[l].retraitScreens.over_cash, l);
});
