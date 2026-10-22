# Refonte UX : configuration système Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre avec la bibliothèque `ui/` la page de configuration système (`SystemConfig`, 530 lignes) et le formulaire d'examen (`ExamFormModal`), pages de l'admin et du ToxicoManager qui s'ouvrent déjà dans le cadre commun `AppShell`.

**Architecture:** même méthode que les lots précédents : test de contrat figé d'abord (vert sur l'ancien code), refonte du gabarit seulement, test vert. Aucune logique ni donnée ne change.

**Tech Stack:** Vue 3 `<script setup>`, Tailwind 4 (jetons), vue-i18n 11, `src/components/ui/`, `node --test ah2-admin-web/tests/*.test.mjs`, `npx vite build`.

**Spec:** décision de l'utilisateur du 2026-10-22 : « allons-y avec la config système ». Modèles : `plans/2026-10-22-refonte-ux-utilisateurs-journaux.md` et sa section du suivi.

## Global Constraints

- **Aucun changement de comportement** : le `<script>` ne change que pour importer les composants `ui/`, déclarer des colonnes ou une constante de classes. Droits par rôle, routes, appels (`configStore`), état des sections repliables (`openSections`), envoi en `FormData` de l'identité de la structure et des logos, régénération du jeton d'impression (avec sa confirmation), examens (création, modification, suppression confirmée, filtre), sauvegarde et mode maintenance restent identiques. `router/index.js` n'est pas modifié.
- **Données et impression** : `stores/configStore.js`, `services/api.js`, `services/PrinterBridgeGateway.js` et `printer_bridge/` ne sont jamais modifiés. Le jeton d'impression et le logo du ticket (utilisés par la caisse) gardent exactement leurs appels.
- **Jetons et typographie** : aucune couleur Tailwind brute ni hexadécimal dans un fichier refondu, texte de base 15 à 16 px, jamais sous 13 px, aucun emoji ni caractère typographique dans le texte affiché, états jamais portés par la seule couleur.
- **i18n** : tout texte ajouté (et ceux qui étaient en dur dans la page) en FR **et** EN sous `configScreens.*` ; parité FR/EN et `i18nMessagesCompile.test.mjs` verts.
- **Contenu réel uniquement** : la sauvegarde de la base et le mode maintenance de la page sont aujourd'hui des simulations locales (un délai de 3 s et un drapeau sans appel serveur) : la refonte les garde telles quelles et le signale dans les résiduels, sans rien inventer.
- Pas de commit (l'utilisateur décide) ; **une tâche à la fois, point de contrôle de l'utilisateur après chacune**.
- **Méthode par écran** : test de contrat figé d'abord, lancé sur l'ancien code (**vert**), refonte, relance (vert).

## Review Focus

- Le formulaire de la structure perd un champ ou envoie un champ vide : le contrat fige les onze champs (`name`, `slogan`, `phone`, `phone2`, `email`, `website`, `address`, `city`, `po_box`, `niu`, `rccm`), le `FormData` (`formData.append(key, formStructure.value[key] || '')`, `logo`, `ticket_logo`) et la confirmation avant de régénérer le jeton.
- L'aperçu des logos ou le choix d'un fichier cesse de fonctionner une fois le champ fichier recouvert ou remplacé (`@change="handleLogoUpload"`, `handleTicketLogoUpload`, `URL.createObjectURL`).
- Un accordéon ne s'ouvre plus au clavier ou perd son état par défaut (structure et examens ouverts, prières et général fermés).
- Un examen supprimé sans confirmation, ou le code d'un examen devenu modifiable en édition (il doit rester verrouillé).

---

### Task 1: Page de configuration (`SystemConfig`)

**Files:**
- Modify: `ah2-admin-web/src/views/SystemConfig.vue`, `ah2-admin-web/src/i18n.js` (`configScreens.*`)
- Create: `ah2-admin-web/tests/systemConfigContract.test.mjs`

**Interfaces:**
- Consumes: `PageHeader`, `AppCard`, `FormField`, `ResponsiveTable`, `StatusBadge`, `AppButton`. `ExamFormModal` : prop `examen`, événements `close` et `saved` **inchangés** (refondu à la Tâche 2).
- Produces: rien.

- [ ] **Step 1: Test de contrat** (baseline verte) : tous les appels de `configStore` (`fetchStructureInfo`, `fetchTicketPrintToken`, `fetchExamens`, `fetchPrayerBooks`, `saveStructureInfo`, `regenerateTicketPrintToken`, `deleteExamen`), les quatre sections et leur état initial, les onze champs et leurs types, le `FormData`, les logos (aperçu, `accept="image/*"`, deux gestionnaires), le jeton et sa confirmation, les examens (filtre sur nom, code, catégorie, tableau, ouverture, suppression confirmée), les prières, sauvegarde et maintenance, le format du prix, les clés `config.*` et `users.table.*`. Nouveaux : composants `ui/`, accordéons à bouton `aria-expanded` et panneau, champs étiquetés, tableaux responsives, conformité couleurs et textes.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** : quatre cartes repliables (en-tête = vrai bouton), formulaire de la structure en deux colonnes sur PC avec les logos à gauche (sélecteur de fichier visible et nommé, aperçu), jeton d'impression avec son bouton, tableau des examens avec Modifier et Supprimer, tableau des types de prières, deux blocs d'actions (sauvegarde, maintenance) avec leur état écrit. **Step 4: Vérifier** suite et build ; visuel : chaque section ouverte et fermée au clavier, changement de logo, enregistrement, régénération du jeton, filtre des examens, 360 px.

---

### Task 2: Formulaire d'examen (`ExamFormModal`)

**Files:**
- Modify: `ah2-admin-web/src/components/config/ExamFormModal.vue`, `ah2-admin-web/src/i18n.js`
- Create: `ah2-admin-web/tests/examFormModalContract.test.mjs`

**Interfaces:**
- Consumes: `FullScreenPanel`, `FormField`, `ActionBar`, `AppButton`. Prop `examen`, événements `close` et `saved` **inchangés**.
- Produces: rien.

- [ ] **Step 1: Test de contrat** (baseline verte) : le formulaire initial et la remise à zéro, `isEditing`, la copie de la prop (`Object.assign(form, newVal)`), `configStore.saveExamen({ ...form })`, `emit('saved')` puis `emit('close')`, l'alerte d'erreur, code verrouillé en édition, champs requis, prix (`min="0"`, `step="100"`), clés `config.*`. Nouveaux : panneau, champs étiquetés, unité FCFA, barre d'actions.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter**, **Step 4: Vérifier** suite et build ; visuel : création et modification d'un examen, code verrouillé en modification, 360 px.

---

### Task 3: Garde-fou et documentation

**Files:**
- Create: `ah2-admin-web/tests/refonteConfigGuard.test.mjs`
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`, mémoire (`project_refonte_ux_admin.md`)

**Interfaces:**
- Produces: garde-fou sur le modèle de `refonteUsersLogsGuard.test.mjs` (couleurs, tailles, caractères, `ui/`, parité FR/EN de `configScreens`, périmètre depuis le commit précédent, données intactes : `configStore`, `api.js`, `PrinterBridgeGateway`, `printer_bridge/`).

- [ ] **Step 1: Test** (le voir échouer sur une couleur en dur ajoutée puis retirée), **Step 2: Lancer** suite et build, **Step 3: Rédiger** la section du suivi (livré, rulings, checklist par écran et largeur, résiduels dont la sauvegarde et la maintenance simulées, reste à migrer : stock admin, stock du labo, laboratoire, toxicologie, stock-control) et la mémoire.
