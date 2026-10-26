import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const view = readFileSync(new URL('../src/views/modules/stock/StockCount.vue', import.meta.url), 'utf8');

test('sous-titre du comptage adapte au role', () => {
    assert.ok(view.includes("canCount ? t('stockCount.subtitle') : t('stockCount.subtitle_review')"));
    for (const l of ['fr', 'en']) {
        const v = msgs[l].stockCount.subtitle_review;
        assert.ok(typeof v === 'string' && v.length > 10, l);
        assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(v));
    }
});
