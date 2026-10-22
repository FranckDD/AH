# Refonte UX de l'espace admin et promoteur Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Passer le cadre partagé `MainLayout` (admin, promoteur, laboratoire, toxicologie, stock-control) sur `AppShell` avec une couleur de menu par espace, puis refondre les écrans de décision et d'argent de l'admin et du promoteur : tableau de bord, finance, réductions à valider et règles de réduction du personnel.

**Architecture:** `AppShell` gagne les sous-menus repliables et le séparateur dont `MainLayout` a besoin ; `MainLayout` ne garde que la configuration (entrées de menu et rôles) et délègue tout le gabarit à `AppShell`, avec une palette de menu choisie d'après le rôle. Chaque écran est refondu avec la méthode déjà éprouvée : test de contrat figé d'abord (vert sur l'ancien code), refonte du gabarit seulement, test vert.

**Tech Stack:** Vue 3 `<script setup>`, Tailwind 4 (jetons `brand-*`, `nav-*`, `tone-*`, `tab-*`, `ink-*`), vue-i18n 11, composants `src/components/ui/`, tests `node --test ah2-admin-web/tests/*.test.mjs`, build `npx vite build`.

**Spec:** aucune spec séparée : décisions de l'utilisateur du 2026-10-22 (conversation) : cadre migré **une seule fois pour tous les rôles**, couleurs de menu indépendantes par espace en dégradé, premier groupe d'écrans = « Tableau de bord + Finance » (avec réductions à valider et règles du personnel). Modèle suivi : `plans/2026-10-22-refonte-ux-secretariat.md` et sa section dans `SUIVI-AVANCEMENT.md`.

## Global Constraints

- **Aucun changement de comportement** : dans les vues et composants existants, le `<script>` ne change que pour importer les composants `ui/`, déclarer des colonnes de tableau ou une constante de classes. Droits par rôle, routes, menu par rôle (mêmes entrées pour chaque rôle qu'aujourd'hui), hors ligne, notifications, impression restent identiques. `router/index.js` n'est pas modifié.
- **Argent et données** : `stores/financialStore.js`, `stores/dashboardStore.js`, `services/FinanceGateway.js`, `utils/invoiceTotals.js`, `utils/staffDiscount.js`, `utils/receiptLines.js`, `stores/caisseStore.js`, `services/CaisseGateway.js`, `services/PrinterBridgeGateway.js`, `printer_bridge/` et les appels `/discount-requests/*` ne sont **jamais modifiés** ; les tests existants correspondants restent verts à chaque tâche.
- **Tolérance aux pannes du tableau de bord** : un bloc en échec affiche « Indisponible », jamais 0 (`valeurAffichee`, `soldeAffiche`, `kpiAffiche`, `indisponibles`) ; cette règle est figée par contrat.
- **Portée** : seuls les fichiers listés dans chaque tâche changent. Interdits : `NotificationBell.vue`, `components/dashboard/StatCard.vue` (gardé, on utilise `ui/StatTile.vue`), `components/common/Modal.vue`, `Pagination.vue`, `ToastContainer.vue`, `components/lab/ResultDetailModal.vue`, `ToxicoAdmissionModal.vue` et tous les écrans laboratoire, toxicologie, stock-control, lots, réceptions, avaries et stock du labo (migrés plus tard, mais ils ouvrent déjà dans le nouveau cadre).
- **Jetons et typographie** : aucune couleur Tailwind brute ni hexadécimal dans un fichier refondu, texte de base 15 à 16 px, jamais sous 13 px, aucun caractère typographique (tiret long, points de suspension, point médian) dans le texte affiché, états jamais portés par la seule couleur.
- **Ergonomie** : zones tactiles >= 44 px sous `lg`, libellés au-dessus des champs, focus visible ; 360, 768 et 1280 px ; la plupart des utilisateurs admin travaillent sur ordinateur : montants lisibles.
- **i18n** : tout texte ajouté en FR **et** EN sous des préfixes propres (`adminShell.*`, `adminDashboard.*`, `financeScreens.*`, `discountReviewScreens.*`, `staffDiscountScreens.*`) ; parité FR/EN et `i18nMessagesCompile.test.mjs` restent verts.
- **Contenu réel uniquement** : aucune donnée, statistique ou fonctionnalité inventée (le texte « Support technique : 674 69 79 08 » de l'écran actuel est conservé tel quel).
- **Vérification de chaque tâche** : `node --test ah2-admin-web/tests/*.test.mjs` puis `cd ah2-admin-web && npx vite build` en dernier. Les agents n'ont pas de navigateur : chaque tâche liste les points visuels. **Pas de commit** (l'utilisateur décide).
- **Méthode par écran** : test de contrat figé d'abord (clés i18n, appels de store, événements, conditions de rôle, textes imposés) lancé sur l'ancien code (doit être **vert**), refonte, relance (vert). Les listes de la tâche sont un minimum ; la liste complète est établie par lecture du fichier.

## Review Focus

- Un rôle gagne ou perd une entrée de menu en changeant de cadre (admin voit tout sauf `adminHidden`, groupe réduit à un enfant devenant un lien plat, `onlyWhenQuarantine`, séparateur de « Configuration ») : un test calcule le menu de chaque rôle (admin, promoteur, laborantin, ToxicoManager, Psychologist, SpiritualCounsellor, Assistant, StockController) avec l'ancienne et la nouvelle construction.
- La palette de menu d'un rôle est illisible ou absente (rôle inconnu) : repli sur le bleu nuit, contraste testé pour chaque palette.
- Le laboratoire (cadre imbriqué `LabLayout`), la toxicologie et le stock-control régressent parce qu'ils partagent le cadre : leurs routes s'affichent dans `<router-view :key="route.fullPath">` comme avant, la cloche reste réservée aux mêmes rôles, le jeton d'impression se charge pour admin et promoteur.
- Un chiffre du tableau de bord ou de la finance devient faux ou 0 au lieu de « Indisponible » en cas d'échec d'un bloc ; le solde dérive de recettes ET dépenses.
- La décision d'une réduction (pourcentage, échéance, mot de passe de confirmation, approuver/refuser) perd une condition : les trois appels et la réinitialisation de l'erreur sont figés.

---

### Task 1: AppShell : sous-menus repliables et séparateur

**Files:**
- Modify: `ah2-admin-web/src/components/layout/AppShell.vue`, `ah2-admin-web/src/utils/sidebarMenu.js` (ajout d'une fonction pure), `ah2-admin-web/src/i18n.js` (`adminShell.*`)
- Create: `ah2-admin-web/tests/appShellSubmenu.test.mjs`

**Interfaces:**
- Consumes: la prop `menuGroups` actuelle `[{ key, labelKey, items }]` reste valable pour le médical et le secrétariat (inchangés, leurs tests restent verts tels quels).
- Produces: `toShellGroups(entries, { sectionLabelKey? })` dans `sidebarMenu.js`, transforme la sortie de `buildMenu` en `menuGroups` ; un item peut porter `children: [item]` (sous-menu : un bouton `aria-expanded`, ouvert d'office si la route courante est un enfant, sinon ouvert/fermé au clic ; menu réduit : navigue vers le premier enfant) et `separator: true` (filet au-dessus). `AppShell` expose aussi la prop `palette` (déjà présente).

- [ ] **Step 1: Test** `appShellSubmenu.test.mjs` : `toShellGroups` (lien plat, groupe, groupe à un seul enfant devenu lien, séparateur, entrée vide ignorée), et dans le gabarit d'`AppShell` : `aria-expanded`, `groupContainsPath`, navigation vers le premier enfant quand le menu est réduit, filet `separator`. Les contrats `appShell`, `secretaireLayout`, `connectionStatus` et `refonteGuard`/`refonteSecretariatGuard` restent verts sans modification.
- [ ] **Step 2: Lancer** (rouge), **Step 3: Implémenter** dans `AppShell` (gabarit seulement : une boucle sur les items gère `item.children`), **Step 4: Vérifier** suite et build ; points visuels : médical et secrétariat strictement identiques à avant.

---

### Task 2: MainLayout sur AppShell, palette par rôle (point de contrôle utilisateur ensuite)

**Files:**
- Modify: `ah2-admin-web/src/components/layout/MainLayout.vue`, `ah2-admin-web/src/design/navPalettes.css`, `ah2-admin-web/src/design/navPalettes.js`, `ah2-admin-web/src/i18n.js`
- Create: `ah2-admin-web/tests/mainLayoutContract.test.mjs`, ajout au test `navPalettes.test.mjs`

**Interfaces:**
- Consumes: `AppShell` (Tâche 1) ; `buildMenu` et `groupContainsPath` ; `NotificationBell` (inchangé).
- Produces: `paletteForRole(role)` dans `navPalettes.js` : admin et promoteur → `slate` ; laborantin → `lagoon` ; ToxicoManager, Psychologist, SpiritualCounsellor, Assistant → `ember` ; StockController → `violet` ; rôle inconnu → `night`. Quatre palettes dans `navPalettes.css` (`nav-700`, `nav-800`, `nav-900`) : couleurs de départ ardoise `#334155`/`#1e293b`/`#0f172a`, lagon `#1b6b72`/`#134b52`/`#0b2f34`, braise `#8a4a1f`/`#5e3015`/`#3a1d0d`, violet `#5b3f8c`/`#3f2a63`/`#251840` (à affiner avec l'utilisateur ; le test impose le contraste).

- [ ] **Step 1: Test de contrat** (baseline verte sur l'ancien `MainLayout`) : chaque entrée de `menuItems` (chemin, `labelKey`, rôles, `group`, `adminHidden`, `separator`), `MENU_GROUPS`, `buildMenu(...)` avec `isAdmin: authStore.isAdmin || authStore.hasRole([ROLES.ADMIN])`, la cloche pour `['admin','promoteur','secretaire','Assistant','StockController','laborantin','ToxicoManager']`, `configStore.fetchStructureInfo()`, `configStore.fetchTicketPrintToken()` sous `hasRole([ROLES.ADMIN, ROLES.PROMOTEUR])`, `AccountModal`, bascule FR/EN et déconnexion (présentes dans `AppShell`). Nouveaux : `MainLayout` importe `AppShell`, passe `:palette="paletteForRole(authStore.userRole)"`, n'a plus de couleur Tailwind brute ; `paletteForRole` par rôle ; contraste de chaque palette (texte 4,5:1, ordre 900 < 800 < 700). Mettre à jour `tests/labStockI18nKeys.test.mjs` seulement si son chemin de lecture l'exige.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** : `MainLayout` = configuration + `toShellGroups(menuEntries)` + `<AppShell>` ; ajouter l'intertitre `adminShell.sections.*` seulement si utile (sinon un seul groupe sans titre).
- [ ] **Step 4: Vérifier** suite et build. Points visuels (**tous les rôles**, chaque ligne à 360, 768, 1280 px) : menu de chaque rôle identique à avant, sous-menus Stock et Stock du labo (ouverts d'office sur leurs pages, menu réduit), séparateur avant Configuration, couleur propre à chaque espace, laboratoire avec son cadre imbriqué, cloche, jeton d'impression admin et promoteur, déconnexion.

---

### Task 3: Tableau de bord de l'admin et du promoteur

**Files:**
- Modify: `ah2-admin-web/src/views/dashboards/DashboardOverview.vue`, `ah2-admin-web/src/i18n.js` (`adminDashboard.*`)
- Create: `ah2-admin-web/tests/adminDashboardContract.test.mjs`

**Interfaces:**
- Consumes: `PageHeader`, `StatTile`, `StatusBadge`, `ResponsiveTable`, `FormField`, `AppButton`. `ToxicoAdmissionModal` et `FinanceModal` restent ouverts tels quels (`@close`, `@save` inchangés ; `FinanceModal` est refondue à la Tâche 4).
- Produces: rien pour les tâches suivantes.

- [ ] **Step 1: Test de contrat** (baseline verte) : `dashboardStore.fetchDashboardData()`, `dashboardStore.setDates(today, today)`, filtres `v-model="dashboardStore.filters.startDate"` et `endDate`, `valeurAffichee('income'|'expense'|'toxico'|'users'|'hospitalized', ...)`, `soldeAffiche` (Indisponible si `income` ou `expense` en échec), `dashboardStore.indisponibles.includes('activites')` et son texte, tableau des activités (`item.label`, `item.description`, `formatDate(item.date)`, `formatCurrency(item.amount)`, `item.type === 'INCOME'`, statut `active` ou `Validé`), `$router.push('/dashboard/finance')`, `'/dashboard/users'`, `'/dashboard/toxico'`, `showAdmissionModal`, `showFinanceModal`, `handleFinanceSaved` (appel de `financialStore.addTransaction` avant la fermeture et l'alerte d'échec), `handleAdmissionSaved`, le texte « Support technique : 674 69 79 08 », toutes les clés citées. Nouveaux : composants `ui/`, `StatTile` (tonalités `success`, `danger`, `info`/`warning` pour le solde selon le signe, avec le sens écrit), tableau responsive aux montants alignés à droite, état de chaque bloc écrit en toutes lettres, conformité couleurs et textes.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** (remplacer `StatCard` par `StatTile`, l'en-tête dégradé de « Actions rapides » par une carte `ui/AppCard` aux boutons `AppButton`, sans changer les trois actions), **Step 4: Vérifier** suite et build ; visuel : un bloc en échec affiche « Indisponible », solde négatif, période personnalisée, 360 px.

---

### Task 4: Finance (liste des transactions et formulaire)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/finance/FinancialList.vue`, `ah2-admin-web/src/components/finance/FinanceModal.vue`, `ah2-admin-web/src/i18n.js` (`financeScreens.*`)
- Create: `ah2-admin-web/tests/financeContract.test.mjs`

**Interfaces:**
- Consumes: composants `ui/` comme à la Tâche 3 ; modèle de la liste de la caisse (`CaisseList.vue` : tuiles, filtres étiquetés, `striped`, montants à droite, pagination). `FinanceModal` : événements `close` et `save` et la forme de `transactionData` **inchangés** (partagés avec le tableau de bord).
- Produces: rien.

- [ ] **Step 1: Test de contrat** : `financialStore.fetchTransactions()`, `setFilters`/`setPage` (recherche, catégorie, dates, type `ALL`/`INCOME`/`EXPENSE`), `resetFilters`, `availableCategories`, `kpiAffiche` (Indisponible), `financialStore.totalIncome`, `totalExpenses`, `currentBalance`, `loadError`, pagination, `handleSaveTransaction` (`financialStore.addTransaction`), le statut `Validé`, toutes les clés `finance.*` ; pour `FinanceModal` : validation, bascule de type, forme de `transactionData` et catégories figées par lecture.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** : tuiles recettes (vert), dépenses (rouge), solde ; filtres de type en groupe de boutons à état écrit (`aria-pressed`) ; tableau `striped` ; `FinanceModal` en `FullScreenPanel`. **Step 4: Vérifier** suite et build ; visuel : création d'une recette et d'une dépense, filtres, 360 px.

---

### Task 5: Réductions à valider et règles de réduction du personnel

**Files:**
- Modify: `ah2-admin-web/src/views/modules/caisse/DiscountReview.vue`, `ah2-admin-web/src/views/modules/caisse/StaffDiscountRules.vue`, `ah2-admin-web/src/i18n.js` (`discountReviewScreens.*`, `staffDiscountScreens.*`)
- Create: `ah2-admin-web/tests/discountReviewContract.test.mjs`, `ah2-admin-web/tests/staffDiscountRulesContract.test.mjs`

**Interfaces:**
- Consumes: composants `ui/` ; routes et appels inchangés.
- Produces: rien.

- [ ] **Step 1: Tests de contrat** : `DiscountReview` : `api.get('/discount-requests/pending')`, `api.post(\`/discount-requests/${req.id}/decide\`, { password, refuse, decision_percent, decision_echelonne_deadline })` (pourcentage et échéance nuls si refus), retrait de la demande après décision, erreur par demande, pourcentages `[10, 20, 50, 100]`, champ mot de passe de type `password`, textes `discount_review.*`. `StaffDiscountRules` : lecture et enregistrement des règles par catégorie (appels du `StaffDiscountGateway`), validations (taux entier 1 à 100, montant minimal positif), section des membres du personnel (appels figés par lecture), messages par ligne, `staffDiscount.*`.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** : carte par demande avec montant en gros, patient, demandeur ; pourcentages en groupe `aria-pressed` ; confirmation par mot de passe étiquetée ; Approuver (vert) et Refuser (rouge) en pleine largeur sous 768 px ; règles en tableau responsive, champs étiquetés. **Step 4: Vérifier** suite et build ; visuel : approuver et refuser, mot de passe faux, 360 px.

---

### Task 6: Recette finale et documentation

**Files:**
- Create: `ah2-admin-web/tests/refonteAdminGuard.test.mjs`
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`, mémoire du projet (`project_refonte_ux_admin.md`, lien depuis `project_refonte_ux_secretariat.md`)

**Interfaces:**
- Consumes: tous les éléments précédents.
- Produces: garde-fou durable sur le modèle de `refonteSecretariatGuard.test.mjs` : (a) aucune couleur en dur, texte >= 13 px, aucun caractère interdit dans les fichiers refondus ; (b) `ui/` importé (exceptions écrites : `MainLayout` est une enveloppe de configuration) ; (c) zones i18n présentes en FR et EN ; (d) pour la plage de commits (`BASE` = dernier commit avant la Tâche 1, `FIN` = dernier commit des Tâches 1 à 5, à renseigner au commit), seuls les fichiers autorisés ont changé et argent et données listés dans Global Constraints sont intacts ; (e) `MedicalLayout`, `SecretaireLayout` et `MainLayout` passent tous par `AppShell`, chaque rôle a une palette valide.

- [ ] **Step 1: Test** : écrire le garde-fou, le voir échouer sur une couleur en dur ajoutée volontairement, puis la retirer.
- [ ] **Step 2: Lancer** toute la suite et `npx vite build` (attendu : tout vert).
- [ ] **Step 3: Rédiger** la section du suivi : livré, décisions, rulings, **checklist utilisateur par écran et par largeur (360, 768, 1280 px) en admin et en promoteur**, plus la vérification de chaque rôle du cadre partagé (laborantin, toxico, assistant, stock) ; résiduels ; reste à migrer (administration : utilisateurs, configuration, journaux ; stock admin ; stock du labo ; laboratoire ; toxicologie ; stock-control) ; mise à jour de la mémoire.
