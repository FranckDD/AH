import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const view = readFileSync(new URL('../src/views/modules/caisse/DiscountReview.vue', import.meta.url), 'utf8');

test('refuser est bloque tant qu un pourcentage ou une echeance est choisi (plus d ignorance silencieuse)', () => {
    assert.ok(view.includes('hasApprovalChoice(req)'));
    assert.ok(view.includes(':disabled="hasApprovalChoice(req)"'));
    assert.ok(view.includes('clearChoice(req)'));
});
test('libelles FR et EN', () => {
    for (const l of ['fr', 'en']) for (const k of ['refuse_needs_clear', 'clear_choice']) {
        assert.ok(msgs[l].discountReviewScreens?.[k], `${l}.${k}`);
    }
});
