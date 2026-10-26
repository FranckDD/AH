import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const view = readFileSync(new URL('../src/views/modules/caisse/CashClosuresReview.vue', import.meta.url), 'utf8');

test('liste des clotures : l heure de cloture est montree', () => {
    assert.ok(view.includes('fmtDateTime(row.closed_at)'));
});
test('sous-titre des clotures : plus de Lecture seule puisque le promoteur decide', () => {
    for (const l of ['fr', 'en']) assert.ok(!/lecture seule|read only/i.test(msgs[l].cashClosure.review_subtitle), l);
});
