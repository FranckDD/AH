import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const modal = read('../src/components/users/UserModal.vue');
const store = read('../src/stores/userStore.js');
const auth = read('../src/stores/auth.js');
const list = read('../src/views/modules/users/UserManagement.vue');

test('case cheffe du laboratoire : admin seul et role laborantin seul', () => {
    const m = modal.match(/const showHeadLabField = computed\(\(\) => \{[\s\S]*?\n\}\)/);
    assert.ok(m, 'showHeadLabField manquant');
    assert.ok(m[0].includes("authStore.hasRole(['admin'])"));
    assert.ok(m[0].includes("=== 'laborantin'"));
    assert.ok(modal.includes('v-if="showHeadLabField"'));
    assert.ok(modal.includes('v-model="form.is_head_lab"'));
    assert.ok(modal.includes('if (!showHeadLabField.value) {') && modal.includes('form.is_head_lab = false'));
    assert.ok(modal.includes('is_head_lab: u.isHeadLab || false'));
    assert.match(modal.slice(modal.indexOf('v-if="showHeadLabField"'), modal.indexOf('v-if="showOwnToxicoField"')), /min-h-11/);
    assert.ok(!/text-xs|text-\[1[0-3]px\]/.test(modal.slice(modal.indexOf('v-if="showHeadLabField"'), modal.indexOf('v-if="showOwnToxicoField"'))));
});

test('le drapeau voyage : liste, creation, modification, badge, authStore', () => {
    assert.ok(store.includes('isHeadLab: u.is_head_lab || false'));
    assert.equal(store.split('is_head_lab: formData.is_head_lab').length - 1, 2, 'POST et PUT');
    assert.ok(list.includes('user.isHeadLab'));
    assert.ok(auth.includes('canEditLabCatalogue') && auth.includes('this.user?.is_head_lab'));
});

test('libelles FR / EN presents, ASCII hors accents, sans tiret long', () => {
    for (const k of ['users.modal.is_head_lab', 'users.modal.is_head_lab_hint']) {
        const fr = i18n.global.t(k, {}, { locale: 'fr' });
        const en = i18n.global.t(k, {}, { locale: 'en' });
        assert.notEqual(fr, k); assert.notEqual(en, k); assert.notEqual(fr, en);
        for (const s of [fr, en]) assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(s));
    }
    assert.equal(i18n.global.t('users.modal.is_head_lab', {}, { locale: 'en' }), 'Head of laboratory');
});
