# Refonte UX : stock admin (réceptions, lots, avaries, mouvements, contrôle, ajustements) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre avec la bibliothèque `ui/` les six écrans du stock côté admin, assistant et contrôleur de stock (`StockReceipts`, `ProductionLots`, `StockIncidents`, `StockMovements`, `StockControlQueue`, `AdjustmentRequestsAdmin`), qui s'ouvrent déjà dans le cadre commun `AppShell` (palettes ardoise, braise et violet selon le rôle). `StockList`, `ProductModal` et `AdjustmentRequestModal` sont déjà refaits (secrétariat).

**Architecture:** même méthode que les lots précédents : test de contrat figé d'abord (vert sur l'ancien code), refonte du gabarit seulement, test vert. Aucune logique, donnée ni règle de stock ne change. Les fenêtres intégrées aux écrans (détail, formulaire de création, saisie de refus) deviennent des `FullScreenPanel`.

**Tech Stack:** Vue 3 `<script setup>`, Tailwind 4 (jetons), vue-i18n 11, `src/components/ui/`, `node --test ah2-admin-web/tests/*.test.mjs`, `npx vite build`.

**Spec:** décision de l'utilisateur du 2026-10-22 : « passons à la prochaine tâche » après la configuration système ; ma proposition était le stock admin. Modèles : `plans/2026-10-22-refonte-ux-configuration-systeme.md` et sa section du suivi.

## Global Constraints

- **Aucun changement de comportement** : le `<script>` ne change que pour importer les composants `ui/`, déclarer des colonnes ou une constante de classes (et, comme pour les lots précédents, faire renvoyer une tonalité du thème à une fonction qui renvoyait des classes de couleur). Droits par rôle, routes, appels (`StockOpsGateway`, `StockControlGateway` ou équivalents, `describeStockError`), validations (`validateReceiptLine`, `receiptLines.js`), règles de stock et messages restent identiques. `router/index.js` n'est pas modifié.
- **Données** : `services/StockOpsGateway.js`, `utils/receiptLines.js`, `utils/localDate.js`, `utils/adjustmentRequest.js`, `stores` de stock et `api.js` ne sont jamais modifiés.
- **Jetons et typographie** : aucune couleur Tailwind brute ni hexadécimal dans un fichier refondu, texte de base 15 à 16 px, jamais sous 13 px, aucun emoji ni caractère typographique dans le texte affiché, états jamais portés par la seule couleur.
- **i18n** : tout texte ajouté (et ceux qui étaient en dur) en FR **et** EN sous `stockAdminScreens.*` ; parité FR/EN et `i18nMessagesCompile.test.mjs` verts. Les clés `stockOps.*`, `stockControl.*` et `stockAdjust.*` existantes sont réutilisées telles quelles.
- **Contenu réel uniquement**. Pas de commit (l'utilisateur décide). **Une tâche à la fois, point de contrôle de l'utilisateur après chacune.**
- **Méthode par écran** : test de contrat figé d'abord, lancé sur l'ancien code (**vert**), refonte, relance (vert).

## Review Focus

- Une réception créée avec des quantités qui ne s'additionnent pas, ou un lot de fabrication prérempli à tort : les validations de ligne (`validateReceiptLine`, `lineTotal`, `QTY_FIELDS`, `prefillFromLot`) et la forme du payload de création sont figées.
- Une action de stock perd sa confirmation (annulation d'une réception, validation ou rejet au contrôle) ou ses conditions (statut `a_controler`, rôle) : le contrat fige chaque condition d'affichage et chaque `window.confirm`.
- Les écrans ne distinguent plus les statuts (à contrôler, validé, rejeté, annulé, livré) que par la couleur : chaque statut passe par `StatusBadge` avec son texte.

---

### Task 1: Réceptions (`StockReceipts`)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/stock/StockReceipts.vue`, `ah2-admin-web/src/i18n.js` (`stockAdminScreens.*`)
- Create: `ah2-admin-web/tests/stockReceiptsContract.test.mjs`

**Interfaces:**
- Consumes: `PageHeader`, `ResponsiveTable`, `StatusBadge`, `FullScreenPanel`, `FormField`, `ActionBar`, `AppButton`.
- Produces: rien.

- [ ] **Step 1: Test de contrat** (baseline verte) : filtre de statut, chargement des réceptions et des lots, `onOriginChange`, `onLotChange` (préremplissage), `addLine`, `openForm` (produits chargés une fois), `submitReceipt` (toutes ses validations dans l'ordre et la forme exacte du payload), `openDetail`, `cancelReceipt` avec `window.confirm`, conditions (`r.status === 'a_controler'`, `rejete` + motif), statuts et clés `stockOps.*`. Nouveaux : composants `ui/`, tableau responsive, statuts en badge avec texte, détail et création en panneau, conformité.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** : en-tête avec « Nouvelle réception » et filtre de statut, messages d'erreur et de succès annoncés (`role="alert"` et `role="status"`), tableau responsive, détail en panneau (tableau des lignes à quantités alignées à droite), formulaire de création en panneau large avec l'origine en choix radio étiqueté, lignes en cartes, total de ligne en rouge si invalide avec son message. **Step 4: Vérifier** suite et build ; visuel : création depuis un lot livré et depuis un fournisseur, plusieurs lignes, quantités incohérentes, annulation, détail, 360 px.

---

### Task 2: Lots de fabrication (`ProductionLots`)
Même méthode : contrat (appels de création, de livraison et d'annulation, conditions de statut), puis refonte ; fichiers `ProductionLots.vue`, test `stockLotsContract.test.mjs`. Contrat et points visuels précisés à la lecture du fichier, avant la refonte.

### Task 3: Avaries et mouvements (`StockIncidents`, `StockMovements`)
Même méthode, deux écrans de consultation avec saisie pour les avaries ; tests `stockIncidentsContract.test.mjs` et `stockMovementsContract.test.mjs`.

### Task 4: Contrôle et demandes d'ajustement (`StockControlQueue`, `AdjustmentRequestsAdmin`)
Même méthode ; écrans de décision (valider ou rejeter avec motif, approuver ou refuser un ajustement) : chaque décision et sa confirmation sont figées ; tests `stockControlContract.test.mjs` et `adjustmentRequestsAdminContract.test.mjs`.

### Task 5: Garde-fou et documentation
`ah2-admin-web/tests/refonteStockAdminGuard.test.mjs` (couleurs, tailles, caractères, `ui/`, parité FR/EN de `stockAdminScreens`, périmètre depuis le commit précédent, données intactes), section du suivi, mémoire, commit.
