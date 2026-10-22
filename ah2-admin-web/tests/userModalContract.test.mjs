import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const modal = readFileSync(new URL('../src/components/users/UserModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : cascade groupe, rôle, spécialité, forme du compte envoyé (aucun changement de droit ni de donnée) ---
check('UserModal', modal, [
    // interface avec l'écran parent
    "defineEmits(['close', 'save'])", 'userToEdit: Object,', 'applicationRoles: { type: Array, required: true },', 'medicalSpecialties: { type: Array, required: true }',
    // groupes de rôles
    "app_admin: ['admin', 'promoteur', 'Psychologist', 'SpiritualCounsellor', 'ToxicoManager', 'Assistant', 'StockController'],", "app_medical: ['medecin', 'nurse'],",
    "app_secretaire: ['secretaire'],", "app_laborantin: ['laborantin']",
    // formulaire initial
    "postgres_role: 'app_medical',", 'role_id: null,', 'specialty_id: null,', 'is_active: true,', 'is_head_nurse: false',
    // cascade
    'const allowedNames = GROUP_MAPPING[form.postgres_role] || []', 'props.applicationRoles.filter(r => allowedNames.includes(r.role_name))',
    "if (form.postgres_role !== 'app_medical') return false", 'if (!form.role_id) return false', "return name === 'medecin';",
    "return (selectedRole.role_name || '').toLowerCase().trim() === 'nurse'",
    'form.role_id = null', 'form.specialty_id = null', 'if (!showSpecialtyField.value) {', 'if (!showHeadNurseField.value) {', 'form.is_head_nurse = false',
    // libellés de rôles
    "admin: 'Administrateur'", "promoteur: 'Promoteur'", "medecin: 'Médecin'", "nurse: 'Infirmier(e)'", "secretaire: 'Secrétaire'", "laborantin: 'Laborantin'",
    "Psychologist: 'Psychologue'", "SpiritualCounsellor: 'Conseiller Spirituel'", "ToxicoManager: 'Resp. Toxicomanie'", "StockController: 'Contrôleur de stock'",
    // préremplissage en édition et envoi
    'is_head_nurse: u.isHeadNurse || false', 'is_active: u.isActive', 'role_id: u.role_id', 'specialty_id: u.specialty_id', 'postgres_role: u.postgres_role',
    'const payload = { ...form }', 'if (isEditing.value && !form.password) delete payload.password', "emit('save', payload)",
    // champs
    'v-model="form.firstName"', 'v-model="form.lastName"', 'v-model="form.username"', 'v-model="form.email"', 'v-model="form.phone"', 'v-model="form.password"',
    'v-model="form.postgres_role"', '@change="handlePostgresRoleChange"', 'v-model="form.role_id"', '@change="handleRoleChange"', 'v-model="form.specialty_id"',
    'v-model="form.is_head_nurse"', 'v-model="form.is_active"', 'type="email"', 'type="tel"', 'required',
    'value="app_admin"', 'value="app_medical"', 'value="app_secretaire"', 'value="app_laborantin"',
    'v-if="!isEditing"', "showPassword ? 'text' : 'password'", 'showPassword = !showPassword', 'v-if="availableRoles.length"', 'v-if="showSpecialtyField"', 'v-if="showHeadNurseField"',
    'v-for="r in availableRoles"', ':value="r.id || r.role_id"', 'prettyRole(r.role_name)', 'v-for="s in medicalSpecialties"', ':value="s.specialty_id"', '{{ s.name }}',
    '@submit.prevent="handleSubmit"', 'id="userForm"', 'form="userForm"', '@click="$emit(\'close\')"',
    // clés
    "t('users.modal.edit_title')", "t('users.modal.new_title')", "t('users.modal.firstname')", "t('users.modal.lastname')", "t('users.modal.email')", "t('users.modal.phone')",
    "t('users.groups.label')", "t('users.groups.app_admin')", "t('users.groups.app_medical')", "t('users.groups.app_secretaire')", "t('users.groups.app_laborantin')",
    "t('users.table.role')", "t('users.specialty.label')", "t('users.specialty.placeholder')", "t('users.modal.is_head_nurse')", "t('users.modal.is_active')",
    "t('users.modal.cancel')", "t('users.modal.update')", "t('users.modal.create')",
]);

test('toutes les clés users.*, common.* et usersScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of modal.matchAll(/['"`(]((?:users|common|usersScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 15);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('UserModal : panneau, sections, champs étiquetés, barre d’actions', () => {
    for (const c of ['FullScreenPanel', 'FormSection', 'FormField', 'ActionBar', 'AppButton']) assert.match(modal, new RegExp(`\\b${c}\\b`), c);
    assert.doesNotMatch(templateOf(modal), /fixed inset-0/);
});

test('UserModal : mot de passe avec bouton afficher/masquer nommé, interrupteurs en cases étiquetées', () => {
    const t = templateOf(modal);
    assert.match(t, /aria-label="[^"]*"|:aria-label="[^"]*"/);
    assert.match(t, /usersScreens\.show_password/);
    assert.match(t, /usersScreens\.hide_password/);
    assert.match(t, /autocomplete="new-password"/);
    assert.equal((t.match(/type="checkbox"/g) || []).length, 2, 'compte actif et chef infirmier');
    assert.doesNotMatch(t, /sr-only peer/);
});

test('UserModal : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(modal, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(modal, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(modal), /[—–…·•]|\p{Extended_Pictographic}/u);
});

test('clés usersScreens (formulaire) en FR et EN', () => {
    const keys = ['username', 'password', 'new_password_optional', 'identity', 'permissions', 'select_role', 'show_password', 'hide_password'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].usersScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.usersScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.usersScreens.${k}`);
        }
    }
});
