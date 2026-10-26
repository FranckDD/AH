import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const bell = readFileSync(new URL('../src/components/notifications/NotificationBell.vue', import.meta.url), 'utf8');
const script = bell.slice(bell.indexOf('<script'));

test('libelles FR/EN des ajustements de caisse', () => {
    for (const lang of ['fr', 'en']) {
        for (const key of ['notifications.cash_correction_requested', 'notifications.cash_correction_approved', 'notifications.cash_correction_rejected']) {
            const v = pick(msgs[lang], key);
            assert.equal(typeof v, 'string', `${lang}.${key}`);
            assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(v), key);
        }
    }
});
test('cloche : libelle et clic', () => {
    assert.ok(script.includes("n.type === 'cash_correction_requested'"));
    assert.ok(script.includes("n.type === 'cash_correction_decided'"));
    assert.ok(script.includes("t('notifications.cash_correction_requested'"));
    assert.ok(script.includes("authStore.hasRole(['promoteur', 'admin'])) pushIfRoute('/dashboard/cash-closures')"));
    assert.ok(script.includes("pushIfRoute('/secretariat/cloture')"));
});
