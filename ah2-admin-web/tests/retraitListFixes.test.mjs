import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const pick = (o, path) => path.split('.').reduce((x, k) => x?.[k], o);
const list = read('../src/views/modules/finance/RetraitList.vue');
const modal = read('../src/components/caisse/CaisseCancelModal.vue');

test('categories traduites dans la liste des retraits', () => {
    assert.ok(list.includes('categoryLabel(r.category)'));
    assert.ok(list.includes("finance.categories."));
});
test('dialogue d annulation specifique au retrait', () => {
    assert.ok(modal.includes('props.title') || modal.includes(':title="title || '));
    assert.ok(list.includes(':title="t(\'retraitScreens.cancel_title\')"'));
    assert.ok(list.includes(':help="t(\'retraitScreens.cancel_help\')"'));
});
test('libelles FR et EN', () => {
    for (const l of ['fr', 'en']) for (const k of ['retraitScreens.cancel_title', 'retraitScreens.cancel_help']) {
        const v = pick(msgs[l], k);
        assert.ok(typeof v === 'string' && v.length > 0, `${l}.${k}`);
    }
    assert.ok(!/facture|invoice/i.test(pick(msgs.fr, 'retraitScreens.cancel_help') + pick(msgs.en, 'retraitScreens.cancel_help')));
});
