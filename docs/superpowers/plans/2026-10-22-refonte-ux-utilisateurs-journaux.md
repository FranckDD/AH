# Refonte UX : gestion des utilisateurs et journaux techniques Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre avec la bibliothèque `ui/` la liste des comptes (`UserManagement`), le formulaire de compte (`UserModal`) et les journaux techniques (`SystemLogs`), écrans de l'admin (et du ToxicoManager) qui s'ouvrent déjà dans le cadre commun `AppShell`.

**Architecture:** même méthode que les lots précédents : test de contrat figé d'abord (vert sur l'ancien code), refonte du gabarit seulement, test vert. Aucune logique ni donnée ne change.

**Tech Stack:** Vue 3 `<script setup>`, Tailwind 4 (jetons), vue-i18n 11, `src/components/ui/`, `node --test ah2-admin-web/tests/*.test.mjs`, `npx vite build`.

**Spec:** décision de l'utilisateur du 2026-10-22 : lot « Utilisateurs + Journaux ». Modèles : `plans/2026-10-22-refonte-ux-admin-promoteur.md` et sa section du suivi.

## Global Constraints

- **Aucun changement de comportement** : le `<script>` ne change que pour importer les composants `ui/`, déclarer des colonnes ou une constante de classes. Droits par rôle, routes, appels (`userStore`, `auditStore`, `/users/roles`, `/users/specialties`), cascade groupe, rôle, spécialité, case infirmier en chef, forme du compte envoyé et pagination restent identiques. `router/index.js` n'est pas modifié.
- **Données** : `stores/userStore.js`, `stores/auditStore.js`, `services/api.js` ne sont jamais modifiés. `components/common/Pagination.vue` n'est pas modifié (il n'est plus utilisé par `SystemLogs` mais reste dans le dépôt).
- **Jetons et typographie** : aucune couleur Tailwind brute ni hexadécimal dans un fichier refondu, texte de base 15 à 16 px, jamais sous 13 px, aucun emoji ni caractère typographique (tiret long, points de suspension, point médian) dans le texte affiché, états jamais portés par la seule couleur. Les puces de masquage « •••••••• » du champ mot de passe sont retirées.
- **i18n** : tout texte ajouté en FR **et** EN sous `usersScreens.*` et `techScreens.*` ; parité FR/EN et `i18nMessagesCompile.test.mjs` verts.
- **Contenu réel uniquement** ; pas de commit (l'utilisateur décide) ; une tâche à la fois, **point de contrôle de l'utilisateur après chacune**.
- **Méthode par écran** : test de contrat figé d'abord, lancé sur l'ancien code (**vert**), refonte, relance (vert).

## Review Focus

- La forme du compte envoyé à `save` change (mot de passe vide supprimé en édition, `is_head_nurse` remis à faux hors infirmier, spécialité remise à nul hors médecin) : le contrat fige `handleSubmit`, `handleRoleChange` et `handlePostgresRoleChange`.
- La suppression d'un compte perd sa confirmation (`confirm(...)` avant `userStore.deleteUser`) ou la modification d'un compte ouvre le mauvais compte (copie `{ ...user }`).
- Les journaux affichent la mauvaise colonne (les deux onglets ont des colonnes différentes) ou perdent le filtre de date par onglet ; la bascule d'onglet ne recharge plus les journaux vides.

---

### Task 1: Liste des comptes (`UserManagement`)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/users/UserManagement.vue`, `ah2-admin-web/src/i18n.js` (`usersScreens.*`)
- Create: `ah2-admin-web/tests/userManagementContract.test.mjs`

**Interfaces:**
- Consumes: `PageHeader`, `ResponsiveTable`, `StatusBadge`, `FormField`, `AppButton`. `UserModal` : props `userToEdit`, `application-roles`, `medical-specialties`, événements `close` et `save` **inchangés** (refondu à la Tâche 2).
- Produces: rien.

- [ ] **Step 1: Test de contrat** (baseline verte) : `userStore.fetchUsers()`, `userStore.setFilters({ search: val })`, `userStore.setPage(page)`, `api.get('/users/roles')`, `api.get('/users/specialties')` et leur lecture tolérante, `openAddModal`, `openEditModal` (copie `{ ...user }`), `closeModal`, `handleSaveUser` (`updateUser` si `userData.id`, sinon `addUser`), `confirmDelete` avec `confirm(...)` puis `userStore.deleteUser(user.id)`, champs `user.firstName`, `lastName`, `username`, `roleName`, `specialtyName`, `postgres_role`, `email`, `phone`, `isActive`, couleur par rôle (admin, médecin, infirmier, secrétaire, laborantin, psychologue ou toxico), pagination, clés `users.*`. Nouveaux : composants `ui/`, tableau responsive, rôle et statut en `StatusBadge` avec texte, actions avec nom accessible, conformité couleurs et textes.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** : en-tête avec « Nouveau compte », recherche étiquetée, tableau (cartes sous `lg`) avec initiales, rôle, spécialité, contact, statut ; boutons Modifier (secondaire) et Supprimer (danger) avec texte sur les cartes et nom accessible sur PC. **Step 4: Vérifier** suite et build ; visuel : recherche, création, modification, suppression avec confirmation, 360 px.

---

### Task 2: Formulaire de compte (`UserModal`)

**Files:**
- Modify: `ah2-admin-web/src/components/users/UserModal.vue`, `ah2-admin-web/src/i18n.js`
- Create: `ah2-admin-web/tests/userModalContract.test.mjs`

**Interfaces:**
- Consumes: `FullScreenPanel`, `FormSection`, `FormField`, `ActionBar`, `AppButton`. Props `userToEdit`, `applicationRoles`, `medicalSpecialties`, événements `close` et `save` et la forme du compte envoyé **inchangés**.
- Produces: rien.

- [ ] **Step 1: Test de contrat** (baseline verte) : `GROUP_MAPPING`, le formulaire initial, `availableRoles`, `showSpecialtyField` (groupe médical et rôle `medecin`), `showHeadNurseField` (rôle `nurse`), `handlePostgresRoleChange`, `handleRoleChange`, `prettyRole`, préremplissage en édition, `handleSubmit` (mot de passe supprimé si vide en édition), champs `required`, interrupteurs actif et infirmier en chef, clés `users.*`. Nouveaux : panneau, champs étiquetés, interrupteurs accessibles (`role="switch"` ou case native étiquetée), mot de passe avec bouton afficher/masquer nommé.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter**, **Step 4: Vérifier** suite et build ; visuel : création puis modification, cascade groupe puis rôle puis spécialité, mot de passe, 360 px.

---

### Task 3: Journaux techniques (`SystemLogs`)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/tech/SystemLogs.vue`, `ah2-admin-web/src/i18n.js` (`techScreens.*`)
- Create: `ah2-admin-web/tests/systemLogsContract.test.mjs`

**Interfaces:**
- Consumes: `PageHeader`, `ResponsiveTable`, `StatusBadge`, `FormField`, `AppButton`. `Pagination.vue` n'est plus utilisé : les commandes de page de la liste des comptes sont reprises.
- Produces: rien.

- [ ] **Step 1: Test de contrat** (baseline verte) : `auditStore.fetchAccessLogs()`, `fetchActionLogs()`, `setAccessPage`, `setActionPage`, `setAccessFilters`, `setActionFilters`, filtre de date par onglet (`handleDateChange`), recharge d'un onglet vide au changement, colonnes de chaque onglet, `getAccessBadge` (LOGIN, LOGOUT, LOGIN_FAILED), `getActionBadge` (CREATE, UPDATE, DELETE), `act.new_values?.details || act.details`, clés `tech.*`. Nouveaux : onglets accessibles (`role="tablist"`, `aria-selected`), tableaux responsives, badges avec texte, conformité.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter**, **Step 4: Vérifier** suite et build ; visuel : les deux onglets, filtre de date, pagination, 360 px, dates selon la langue.

---

### Task 4: Garde-fou et documentation

**Files:**
- Create: `ah2-admin-web/tests/refonteUsersLogsGuard.test.mjs`
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`, mémoire (`project_refonte_ux_admin.md`)

**Interfaces:**
- Produces: garde-fou sur le modèle de `refonteAdminGuard.test.mjs` (couleurs, tailles, caractères, `ui/`, parité FR/EN des zones `usersScreens` et `techScreens`, périmètre depuis le commit précédent, données intactes : `userStore`, `auditStore`, `api.js`, `Pagination.vue`).

- [ ] **Step 1: Test** (le voir échouer sur une couleur en dur ajoutée puis retirée), **Step 2: Lancer** suite et build, **Step 3: Rédiger** la section du suivi (livré, rulings, checklist par écran et largeur, résiduels, reste à migrer : configuration système, stock admin, stock du labo, laboratoire, toxicologie, stock-control) et la mémoire.
