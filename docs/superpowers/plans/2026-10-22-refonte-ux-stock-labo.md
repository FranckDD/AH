# Refonte UX : stock du laboratoire (produits, demandes, réceptions, comptage, alertes, mouvements, dépenses) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre avec la bibliothèque `ui/` les huit écrans du stock du laboratoire (`LabStockProducts`, `LabStockRequests`, `LabStockReceipts`, `LabStockReceiptForm`, `LabStockCount`, `LabStockAlerts`, `LabStockMovements`, `LabStockExpenses`), utilisés par le laborantin, le StockController, le promoteur, le ToxicoManager et l'admin, dans le cadre commun `AppShell` (palettes lagon, violet, ardoise et braise selon le rôle).

**Architecture:** même méthode que les lots précédents : test de contrat figé d'abord (vert sur l'ancien code), refonte du gabarit seulement, test vert. Aucune logique, donnée ni règle de stock ne change. Les fenêtres intégrées (saisie, détail, motif de refus) deviennent des `FullScreenPanel`.

**Tech Stack:** Vue 3 `<script setup>`, Tailwind 4 (jetons), vue-i18n 11, `src/components/ui/`, `node --test ah2-admin-web/tests/*.test.mjs`, `npx vite build`.

**Spec:** décision de l'utilisateur du 2026-10-22 : « passons au lot suivant » après le stock admin ; ma proposition était le stock du labo. Modèles : `plans/2026-10-22-refonte-ux-stock-admin.md` et sa section du suivi.

## Global Constraints

- **Aucun changement de comportement** : le `<script>` ne change que pour importer les composants `ui/`, déclarer des colonnes ou une constante de classes (et faire renvoyer une tonalité du thème à une fonction qui renvoyait des classes de couleur). Droits par rôle, routes, appels de la passerelle du stock du labo, validations, règles de stock et messages restent identiques. `router/index.js` n'est pas modifié.
- **Données** : les services et utilitaires du stock du labo (passerelle, validations, formats), `api.js` et les magasins ne sont jamais modifiés.
- **Boutons** (décision du 2026-10-22) : variante choisie d'après l'action : `primary` (indigo) pour créer ou enregistrer, `success` (vert) pour valider ou approuver, `info` (bleu ciel) pour livrer ou consulter, `danger` (rouge) pour supprimer, rejeter ou annuler, `secondary` (contour) pour les actions secondaires ; jamais de vert par défaut.
- **Jetons et typographie** : aucune couleur Tailwind brute ni hexadécimal dans un fichier refondu, texte de base 15 à 16 px, jamais sous 13 px, aucun emoji ni caractère typographique dans le texte affiché, états jamais portés par la seule couleur.
- **i18n** : tout texte ajouté (et ceux qui étaient en dur) en FR **et** EN sous `labStockScreens.*` ; parité FR/EN et `i18nMessagesCompile.test.mjs` verts. Les clés `labStock.*` existantes sont réutilisées telles quelles (`labStockI18nKeys.test.mjs` reste vert).
- **Contenu réel uniquement**. Pas de commit (l'utilisateur décide). **Une tâche à la fois, point de contrôle de l'utilisateur après chacune.**
- **Méthode par écran** : test de contrat figé d'abord, lancé sur l'ancien code (**vert**), refonte, relance (vert).

## Review Focus

- Un comptage, une réception ou une demande envoie des quantités ou des identifiants différents : la forme de chaque charge envoyée et chaque validation avant envoi sont figées par contrat.
- Une action de stock perd sa confirmation ou ses conditions d'affichage (statut, rôle) : le contrat fige chaque condition et chaque `window.confirm`.
- Les statuts ne se distinguent plus que par la couleur : chacun passe par `StatusBadge` avec son texte.
- Un rôle voit un bouton qu'il ne devait pas voir (les écrans sont partagés entre cinq rôles) : les conditions de rôle des gabarits sont figées.

---

### Task 1: Produits (`LabStockProducts`)
**Files:** `ah2-admin-web/src/views/modules/labstock/LabStockProducts.vue`, `src/i18n.js` (`labStockScreens.*`) ; test `labStockProductsContract.test.mjs`. Contrat et points visuels précisés à la lecture du fichier, avant la refonte.

### Task 2: Demandes et liste des réceptions (`LabStockRequests`, `LabStockReceipts`)
Mêmes règles ; tests `labStockRequestsContract.test.mjs` et `labStockReceiptsContract.test.mjs`.

### Task 3: Formulaire de réception (`LabStockReceiptForm`)
Mêmes règles ; test `labStockReceiptFormContract.test.mjs` (charge envoyée et validations figées).

### Task 4: Comptage et alertes (`LabStockCount`, `LabStockAlerts`)
Mêmes règles ; tests `labStockCountContract.test.mjs` et `labStockAlertsContract.test.mjs`.

### Task 5: Mouvements et dépenses (`LabStockMovements`, `LabStockExpenses`)
Mêmes règles ; tests `labStockMovementsContract.test.mjs` et `labStockExpensesContract.test.mjs`.

### Task 6: Garde-fou et documentation
`ah2-admin-web/tests/refonteLabStockGuard.test.mjs` (couleurs, tailles, caractères, `ui/`, parité FR/EN de `labStockScreens`, périmètre depuis le commit précédent, données intactes), section du suivi, mémoire, commit.
