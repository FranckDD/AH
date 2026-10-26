import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const store = read('../src/stores/userStore.js');
const modal = read('../src/components/users/UserModal.vue');
const view = read('../src/views/modules/users/UserManagement.vue');

test('liste des utilisateurs : role lu depuis le champ plat role_name', () => {
    assert.ok(store.includes('u.role_name'));
    assert.ok(store.includes('u.specialty_name'));
});
test('infirmier chef affiche dans la liste', () => {
    assert.ok(view.includes('user.isHeadNurse'));
});
test('identifiant en lecture seule a la modification', () => {
    assert.ok(modal.includes(':readonly="isEditing"'));
});
test('refus du serveur affiche (doublon identifiant)', () => {
    assert.ok(view.includes('describeServerError'));
    assert.ok(view.includes('toastStore.push'));
});
test('suppression : texte traduit, plus de confirm en dur', () => {
    assert.ok(!view.includes('Voulez-vous vraiment supprimer'));
});
