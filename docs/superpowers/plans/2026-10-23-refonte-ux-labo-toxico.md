# Refonte UX : laboratoire et toxicologie Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre avec la bibliothèque `ui/` les écrans du laboratoire (cadre, tableau de bord, réception, paillasse, saisie, historique, configuration, détail d'un résultat) et de la toxicologie (tableau de bord, liste des patients et ses sept fenêtres), dans le cadre commun `AppShell` et les palettes de rôle déjà en place.

**Architecture:** même méthode que les lots précédents : test de contrat figé d'abord (vert sur l'ancien code), refonte du gabarit seulement, test vert. Aucune logique, donnée ni règle métier ne change. Les fenêtres intégrées (`fixed inset-0`) deviennent des `FullScreenPanel`.

**Tech Stack:** Vue 3 `<script setup>`, Tailwind 4 (jetons), vue-i18n 11, `src/components/ui/`, `node --test ah2-admin-web/tests/*.test.mjs`, `npx vite build`.

**Périmètre vérifié le 2026-10-23** (état du code, pas de supposition)
- **Déjà migrés, hors lot** : les sept écrans du stock admin, dont `StockControlQueue` (« stock-control complet » est donc déjà livré, lot du 2026-10-22), `MedicalLabResults` (espace médical), les huit écrans du stock du labo.
- **À faire** : `views/modules/labo/` (`LabLayout`, `LabReception`, `LabTechnician`, `LabWorklist`, `LabEntry`, `LabHistory`, `LabConfig`), `components/lab/ResultDetailModal`, `views/dashboards/LabDashboard` et `ToxicoDashboard`, `views/modules/toxico/ToxicoList`, `components/toxico/*` (sept fichiers).
- **Hors lot** : `LabValidation.vue` (écran retiré, fichier conservé), `SyncFailuresView` (déjà migré au secrétariat).

## Global Constraints

- **Aucun changement de comportement** : le `<script>` ne change que pour importer les composants `ui/`, déclarer des colonnes ou une constante de classes (et faire renvoyer une tonalité du thème à une fonction qui renvoyait des classes de couleur). Droits par rôle, routes, appels de passerelle ou de magasin, validations, règles métier, hors ligne et synchronisation restent identiques. `router/index.js` n'est pas modifié.
- **Données** : passerelles (`labGateway`, toxico), magasins, utilitaires et `api.js` ne sont jamais modifiés.
- **Boutons** : variante choisie d'après l'action : `primary` (indigo) pour créer ou enregistrer, `success` (vert) pour valider ou approuver, `info` (bleu ciel) pour consulter ou livrer, `danger` pour supprimer, rejeter ou annuler, `secondary` pour les actions secondaires ; jamais de vert par défaut.
- **Jetons et typographie** : aucune couleur Tailwind brute ni hexadécimal dans un fichier refondu, texte de base 15 à 16 px, jamais sous 13 px, aucun emoji ni caractère typographique dans le texte affiché, états jamais portés par la seule couleur, cibles tactiles d'au moins 44 px.
- **Résultats de laboratoire** : une valeur anormale se distingue par un texte ou un badge (« Anormal »), jamais par la couleur seule.
- **i18n** : tout texte ajouté (et ceux qui étaient en dur) en FR **et** EN sous `labScreens.*` et `toxicoScreens.*` ; parité FR/EN et `i18nMessagesCompile.test.mjs` verts. Les clés existantes (`lab.*`, `toxico.*`) sont réutilisées telles quelles.
- **Contenu réel uniquement**. Pas de commit (l'utilisateur décide). **Une tâche à la fois, point de contrôle de l'utilisateur après chacune.**
- **Méthode par écran** : test de contrat figé d'abord, lancé sur l'ancien code (**vert**), refonte, relance (vert).

## Review Focus

- Un résultat saisi ou validé part avec d'autres valeurs, unités ou identifiants (paillasse, saisie) : la forme de chaque charge envoyée et chaque validation avant envoi sont figées par contrat.
- La recherche de patient interne perd son import des examens prescrits (réception) : le contrat fige l'appariement par nom d'examen et le contenu de la charge.
- Une sortie, une admission ou une évaluation toxicologique perd une condition de rôle ou de phase : les conditions d'affichage et de droits des boutons sont figées.
- Un panneau ne se ferme plus (Échap, focus, bouton) ou perd le focus : tous les panneaux passent par `FullScreenPanel`.
- Le mode hors ligne du laborantin (recherche, médecins, quarantaine) est intact : les chemins de repli du script ne bougent pas.

---

### Task 1: Cadre et tableau de bord du laboratoire (`LabLayout`, `LabDashboard`)
**Files:** `views/modules/labo/LabLayout.vue`, `views/dashboards/LabDashboard.vue`, `src/i18n.js` (`labScreens.*`) ; tests `labLayoutContract.test.mjs`, `labDashboardContract.test.mjs`. Les onglets du cadre deviennent un menu accessible (état courant annoncé), conditions de rôle figées.

### Task 2: Réception (`LabReception`)
Recherche du patient interne, import des examens prescrits, mode externe, prescripteur, panier. Test `labReceptionContract.test.mjs` (appariement des noms, charge envoyée, conditions d'activation de l'envoi, chemin hors ligne des médecins).

### Task 3: Paillasse et liste de travail (`LabTechnician`, `LabWorklist`)
Tests `labTechnicianContract.test.mjs`, `labWorklistContract.test.mjs`. À lire avant : quels écrans sont réellement montés (la liste de travail est-elle encore routée ?).

### Task 4: Saisie et détail d'un résultat (`LabEntry`, `ResultDetailModal`)
Tests `labEntryContract.test.mjs`, `labResultDetailContract.test.mjs` (valeurs, unités, drapeaux anormaux par texte, validation, PDF).

### Task 5: Historique et configuration (`LabHistory`, `LabConfig`)
Tests `labHistoryContract.test.mjs` (filtres, pagination, ouverture d'un dossier groupé), `labConfigContract.test.mjs`.

### Task 6: Tableau de bord et liste toxicologie (`ToxicoDashboard`, `ToxicoList`)
Tests `toxicoDashboardContract.test.mjs`, `toxicoListContract.test.mjs` (droits par rôle, filtres, ouverture des fenêtres, promoteur en lecture et validation de sortie seulement).

### Task 7: Admission et sortie (`ToxicoAdmissionModal`, `ToxicoDischargeModal`)
Tests `toxicoAdmissionContract.test.mjs`, `toxicoDischargeContract.test.mjs` (motif de sortie obligatoire guérison/abandon/exclusion/autre, psychologue choisi à chaque admission, réadmission en phase 1).

### Task 8: Dossier et détail patient (`ToxicoDossierModal`, `ToxicoPatientDetailsModal`)
Tests `toxicoDossierContract.test.mjs`, `toxicoPatientDetailsContract.test.mjs`.

### Task 9: Évaluation, sortis et séjours (`ToxicoEvaluationModal`, `ToxicoDischargedPanel`, `ToxicoStaysTimeline`)
Tests `toxicoEvaluationContract.test.mjs` (psychologue seul peut évaluer), `toxicoDischargedPanelContract.test.mjs`, `toxicoStaysTimelineContract.test.mjs`.

### Task 10: Garde-fou et documentation
`ah2-admin-web/tests/refonteLaboToxicoGuard.test.mjs` (couleurs, tailles, caractères, `ui/`, parité FR/EN de `labScreens` et `toxicoScreens`, périmètre depuis le commit précédent, données intactes), section du suivi, mémoire. Commit seulement à la demande de l'utilisateur ; renseigner `FIN` à ce moment.
