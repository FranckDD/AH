import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/users/UserManagement.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : ce que l'écran fait aujourd'hui (aucun changement de droit, d'appel ni de données) ---
check('UserManagement', view, [
    // chargement : comptes puis listes de référence pour le formulaire
    'userStore.fetchUsers();', "api.get('/users/roles')", "api.get('/users/specialties')",
    'Array.isArray(rolesRes.data) ? rolesRes.data : rolesRes.data.data || rolesRes.data', 'Array.isArray(specsRes.data) ? specsRes.data : specsRes.data.data || specsRes.data',
    // recherche et pagination
    'userStore.filters.search', 'userStore.setFilters({ search: val })', 'v-model="searchQuery"', 'userStore.setPage(page)',
    'userStore.pagination.total', 'userStore.pagination.total_pages', 'goToPage(userStore.pagination.page - 1)', 'goToPage(userStore.pagination.page + 1)',
    'userStore.isLoading', 'userStore.users',
    // lignes
    'user.firstName', 'user.lastName', 'user.username', 'user.roleName', 'user.specialtyName', "user.specialtyName !== '-'", 'user.postgres_role', 'user.email', 'user.phone', 'user.isActive',
    // couleur par rôle (admin, médecin, infirmier, secrétaire, laborantin, psychologue/toxico)
    "r.includes('admin') || r.includes('directeur')", "r.includes('medecin') || r.includes('médecin') || r.includes('doctor')", "r.includes('nurse') || r.includes('infirmier')",
    "r.includes('secretaire') || r.includes('secrétaire')", "r.includes('laborantin') || r.includes('bio')", "r.includes('psy') || r.includes('toxico')",
    // actions : création, modification (copie), suppression confirmée
    '@click="openAddModal"', 'openEditModal(user)', 'confirmDelete(user)', 'selectedUser.value = { ...user };', 'selectedUser.value = null;', 'showModal.value = true;', 'showModal.value = false;',
    'if (userData.id) {', 'await userStore.updateUser(userData);', 'await userStore.addUser(userData);',
    "if (confirm(t('usersScreens.delete_confirm', { name: `${user.firstName} ${user.lastName}` }))) {", 'await userStore.deleteUser(user.id);',
    // modale
    '<UserModal', ':userToEdit="selectedUser"', ':application-roles="applicationRoles"', ':medical-specialties="medicalSpecialties"', '@close="closeModal"', '@save="handleSaveUser"',
    // clés (la colonne des actions est désormais l'en-tête masqué ui.actions du tableau commun)
    "t('users.title')", "t('users.search_placeholder')", "t('users.add_new')", "t('users.table.employee')", "t('users.table.role')", "t('users.table.contact')",
    "t('users.table.status')", "t('users.modal.edit_title')", "t('common.delete')",
    'v-if="user.seesOwnToxicoOnly"', "t('users.modal.sees_own_toxico_only')",
]);

test('toutes les clés users.*, common.* et usersScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:users|common|usersScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 8);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('UserManagement : composants ui/, tableau responsive à lignes alternées, rôle et statut en badge avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FormField', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\n\s+striped\s*\n/);
    assert.match(view, /<StatusBadge/);
});

test('UserManagement : actions accessibles (Modifier secondaire, Supprimer danger, nom sur chaque bouton)', () => {
    const t = templateOf(view);
    assert.match(t, /variant="danger"/);
    assert.match(t, /usersScreens\.edit/);
    assert.match(t, /usersScreens\.delete_user/);
});

test('UserManagement : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·]|\p{Extended_Pictographic}/u);
});

test('clés usersScreens.* en FR et EN', () => {
    const keys = ['count', 'search_label', 'active', 'inactive', 'edit', 'delete_user', 'empty', 'empty_help', 'page_label', 'prev_page', 'next_page'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].usersScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.usersScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.usersScreens.${k}`);
        }
    }
});
