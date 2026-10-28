import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const view = read('../src/views/modules/users/UserManagement.vue');
const store = read('../src/stores/userStore.js');
const { default: i18n } = await import('../src/i18n.js');

const KEYS = ['unlock', 'locked', 'unlock_confirm', 'unlock_done', 'unlock_failed'];

test('bouton Deverrouiller reserve a l admin et visible seulement si le compte est verrouille', () => {
    assert.ok(view.includes("authStore.hasRole(['admin'])"));
    assert.ok(view.includes('v-if="canUnlock && user.locked"'));
    assert.ok(view.includes('confirmUnlock(user)'));
});

test('le store appelle POST /users/{id}/unlock et lit le drapeau locked', () => {
    assert.ok(store.includes('`/users/${id}/unlock`'));
    assert.ok(store.includes('locked: u.locked === true'));
    assert.ok(store.includes('unlockUser'));
});

test('cles i18n unlock presentes en FR et EN, ASCII sans caracteres typographiques interdits', () => {
    const msgs = i18n.global.messages.value;
    for (const k of KEYS) {
        const fr = msgs.fr.usersScreens[k];
        const en = msgs.en.usersScreens[k];
        assert.ok(fr && en, k);
        for (const v of [fr, en]) assert.ok(!/[\u2013\u2014\u2026\u00b7\u2192\u2190]/.test(v), k);
    }
});
