# Refonte UX de l'espace secrétariat : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Appliquer à l'espace du rôle `secretaire` (accueil, patients, stock, caisse, retraits, consultations spirituelles, historique des réductions) le même système de design que l'espace médical, **sans changer aucun comportement métier**, en commençant par factoriser le cadre (menu et barre du haut) pour que les prochains espaces (admin, labo, toxico, stock) le réutilisent.

**Architecture:** Un cadre partagé `AppShell.vue` extrait de `MedicalLayout.vue` (qui devient une fine enveloppe de configuration, rendu inchangé), puis `SecretaireLayout.vue` construit de la même façon. Ensuite migration écran par écran avec la bibliothèque `src/components/ui/` existante (+ une tuile de statistique `StatTile`), chaque écran protégé par un test de contrat figé avant modification. La caisse et les retraits (argent, hors ligne, impression du ticket) sont traités en dernier, avec des contrats renforcés.

**Tech Stack:** Vue 3.5, Tailwind 4 (jetons `@theme` de `src/style.css`), vue-i18n 11, Heroicons, PowerSync, tests `node --test`, `vite build`.

**Spec:** pas de spec séparée : les décisions de cadrage sont celles de la section « Décisions » ci-dessous (réponses de l'utilisateur du 2026-10-22). Méthode, composants et règles de référence : `docs/superpowers/specs/2026-10-22-refonte-ux-medical-design.md`, `docs/superpowers/plans/2026-10-22-refonte-ux-medical.md` et la section « Refonte UX de l'espace médical : livrée » de `docs/superpowers/SUIVI-AVANCEMENT.md`.

## Décisions (utilisateur, 2026-10-22)

- **Accueil** : bandeau d'**actions rapides** en haut (Nouvelle facture, Nouveau retrait, Ajouter un patient), puis les statistiques et les alertes de stock dessous. La secrétaire arrive toujours sur l'accueil (pas de changement de page d'arrivée).
- **Ordre** : la **caisse en dernier**. Cadre, accueil, stock, consultations et historique des réductions d'abord ; point de contrôle et test d'utilisation avec la secrétaire ; puis caisse, facture et retraits.
- **Écrans partagés** avec d'autres rôles : refondus **une seule fois pour tous** (même choix que pour les écrans patient du médical). Concernés : `StockList` (admin, ToxicoManager, Assistant), `ProductModal`, `AdjustmentRequestModal`, `DiscountRequestsHistory` (admin, promoteur).
- Règles déjà décidées et à respecter : pas de tiret long, point médian ni points de suspension typographiques dans les textes affichés ; couleurs d'état = sens (rouge urgent, orange attention, vert fait, bleu info) ; une seule couleur d'action principale (teal) ; bouton de réduction du menu conservé ; planning et libellés lisibles.

## Global Constraints

- **Aucun changement de comportement** : dans les vues et composants existants, le `<script>` ne change que pour importer les composants `ui/`, déclarer des colonnes de tableau ou une constante de classes, et (Tâche 3) lire un paramètre d'URL `nouveau`. Toute autre modification de logique est listée dans le rapport de la tâche et justifiée. Droits par rôle, routes, hors ligne (PowerSync), impression du ticket, calculs de montants, réductions et notifications restent identiques. `router/index.js` n'est modifié que si une tâche le dit.
- **Argent** : `utils/invoiceTotals.js`, `utils/staffDiscount.js`, `utils/receiptLines.js`, `stores/caisseStore.js`, `services/CaisseGateway.js`, `services/PrinterBridgeGateway.js` et le dossier `printer_bridge/` ne sont **jamais modifiés** ; les tests `invoiceTotals`, `staffDiscount`, `receiptLines` restent verts à chaque tâche.
- **Portée** : seuls les fichiers listés dans chaque tâche changent. Interdits : `MainLayout.vue`, `StatCard.vue` (garder et ne pas modifier : on crée `ui/StatTile.vue`), `NotificationBell.vue`, `components/common/Modal.vue`, `Pagination.vue`, `ToastContainer.vue`, `components/lab/ResultDetailModal.vue`, les écrans labo, toxico, stock-control, lots, réceptions, avaries et finance admin (`FinancialList.vue`), `stores/medicalRecordStore.js`, `powersync-client/DossierConnector.js`.
- **Jetons et typographie** : mêmes règles que le plan médical (jetons `brand-*`, `nav-*`, `tone-*`, `ink-*`, aucune couleur Tailwind brute ni hexadécimal dans un fichier refondu, texte de base 15 à 16 px, jamais sous 13 px, police Inter locale). Nouveaux jetons seulement si une tâche le dit.
- **Ergonomie et adaptabilité** : zones tactiles >= 44 px sous `lg`, libellés au-dessus des champs, astérisque sur les champs obligatoires, états jamais portés par la seule couleur, focus visible ; téléphone 360 px (cartes), tablette 768 px (deux colonnes), PC 1280 px (tableaux). La secrétaire travaille surtout sur ordinateur et tablette : vérifier la lisibilité des montants.
- **i18n** : tout texte ajouté en FR **et** EN sous des préfixes propres (`secretariatShell.*`, `secretariatHome.*`, `ui.*`) ; les textes déjà en dur dans un écran restent tels quels sauf ceux que la tâche touche ; le test `i18nMessagesCompile.test.mjs` et la parité FR/EN restent verts.
- **Contenu réel uniquement** : aucune donnée, statistique ou fonctionnalité inventée.
- **Vérification de chaque tâche** : `node --test ah2-admin-web/tests/*.test.mjs` puis `cd ah2-admin-web && npx vite build` en dernier (aucun avertissement nouveau). Les agents n'ont pas de navigateur : chaque tâche liste les points visuels à regarder. **Pas de commit** (l'utilisateur décide). Disque C: presque plein : aucune copie du dépôt, aucune image > 100 Ko.
- **Méthode par écran** : écrire d'abord un test de contrat figé (clés i18n, appels de store, événements, conditions de rôle, textes imposés), le lancer sur l'ancien code (doit être **vert**), refondre, relancer (vert). Les points de contrôle de chaque tâche ci-dessous nomment ce qui doit y figurer au minimum ; la liste complète est établie par lecture du fichier.

## Review Focus

- Une secrétaire perd silencieusement une action en changeant le gabarit (nouvelle facture, annulation, versement, réimpression du ticket, nouveau retrait, demande d'ajustement de stock) : un test par écran compare les actions avant et après.
- Un écran partagé change de droits par inversion de condition : sur `StockList` (`isAdmin`, `isSecretary`, `!isSecretary`), le bouton « Demander un ajustement » reste réservé à la secrétaire et les boutons de modification, suppression et mise au rebut restent réservés aux autres rôles ; test par rôle sur les conditions.
- Un montant ou une réduction change d'un centime à cause du gabarit de facture (lignes, arrondi, réduction personnel, réduction manuelle) : les tests `invoiceTotals`, `staffDiscount`, `receiptLines` restent verts et un contrat fige les appels de calcul de `CaisseInvoiceModal`.
- Le hors ligne et l'impression se dégradent : boutons grisés avec « En attente de synchronisation » tant qu'une facture n'a pas d'identifiant serveur, avertissement « statut du personnel non synchronisé » avant validation, message d'erreur d'impression de `CaisseList` ; contrat sur ces textes et ces conditions.
- Le cadre partagé régresse l'espace médical (entrée de menu, badge de quarantaine, cloche réservée, tiroir, bouton de réduction) : le contrat existant de `MedicalLayout` est repris sur `AppShell` + configuration et doit rester vert tel quel.

## Phases et points de contrôle

Phase 1 = Tâches 1 et 2 (cadre). Phase 2 = Tâches 3 à 6 (accueil, stock, consultations, historique des réductions). **Point de contrôle utilisateur et test d'utilisation avec la secrétaire après la Tâche 6** (protocole produit à la Tâche 6). Phase 3 = Tâches 7 à 9 (caisse, facture, retraits). Tâche 10 = recette finale.

---

### Task 1: Cadre partagé `AppShell` (menu, barre du haut), espace médical inchangé

**Files:**
- Create: `ah2-admin-web/src/components/layout/AppShell.vue`, `ah2-admin-web/tests/appShell.test.mjs`
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue` (devient une enveloppe de configuration), `ah2-admin-web/tests/connectionStatus.test.mjs` (le contrat du gabarit lit désormais `MedicalLayout.vue` **et** `AppShell.vue`)

**Interfaces:**
- Produces: `AppShell` avec les props `menuGroups: Array<{ key: string, labelKey: string, items: Array<{ path: string, labelKey: string, icon: Component, onlyWhenQuarantine?: boolean }> }>`, `bellRoles: string[]` (rôles qui voient `NotificationBell`), `brandFallback: string` (nom affiché sans `structureInfo.name`), `sidebarId: string` ; un slot `default` (le contenu, à la place de `<router-view>` : par défaut `<router-view :key="route.fullPath" />`). Il porte tout ce que `MedicalLayout` portait : tiroir sous 768 px, bouton de réduction en icônes, nom complet et rôle, date, `ConnectionStatus`, langue FR/EN, cloche, compte (`AccountModal`), déconnexion, badge de quarantaine, `.app-refonte`.
- Consumes: `ConnectionStatus`, `useSyncQuarantineCount`, `useConfigStore`, `authStore`, clés `medicalShell.*` (conservées sous ce nom pour l'espace médical ; l'enveloppe passe `labelKey` complets).

- [ ] **Step 1: Test** `tests/appShell.test.mjs` : lit `AppShell.vue` et vérifie la présence de chaque comportement figé (liste ci-dessous) ; lit `MedicalLayout.vue` et vérifie qu'il importe `AppShell`, déclare les 9 entrées (chemins et `labelKey` identiques à `tests/connectionStatus.test.mjs`) réparties en `activity`, `medical`, `followup`, passe `bellRoles` = `['medecin', 'nurse']` et ne contient plus de gabarit de menu. Comportements figés dans `AppShell` : `changeLanguage`, `localStorage.setItem('lang'`, `<NotificationBell`, `AccountModal`, `await authStore.logout()`, `<ConnectionStatus`, `resolveAssetUrl`, `fetchStructureInfo`, `toggleSidebar`, `Bars3CenterLeftIcon`, `medicalShell.collapseMenu`, `medicalShell.expandMenu`, `isDrawerOpen`, `Escape`, `displayName`, `onlyWhenQuarantine`, `useSyncQuarantineCount`. Premier lancement : échec.
- [ ] **Step 2: Lancer** `node --test ah2-admin-web/tests/appShell.test.mjs`, attendu : échec (fichier absent).
- [ ] **Step 3: Implémenter** `AppShell.vue` en déplaçant le gabarit et le script de `MedicalLayout.vue` sans les modifier, en remplaçant uniquement la liste d'entrées, la condition de la cloche (`authStore.hasRole(bellRoles)`) et le nom de repli par les props ; le groupe sans entrée visible reste masqué ; `MedicalLayout.vue` ne garde que la configuration et `<AppShell ... />`.
- [ ] **Step 4: Reprendre le contrat existant** : dans `connectionStatus.test.mjs`, les tests qui lisent `MedicalLayout.vue` lisent le texte concaténé `MedicalLayout.vue` + `AppShell.vue` (mêmes needles, aucune supprimée).
- [ ] **Step 5: Vérifier** toute la suite puis `npx vite build` ; `git diff` de `MedicalLayout.vue` ne change aucun chemin, libellé ni droit. **Rapport** : tableau avant et après des entrées du menu médical (aucune perdue).

---

### Task 2: Cadre du secrétariat

**Files:**
- Modify: `ah2-admin-web/src/components/layout/SecretaireLayout.vue` (enveloppe de configuration autour de `AppShell`), `ah2-admin-web/src/i18n.js` (clés `secretariatShell.sections.*` FR et EN)
- Create: `ah2-admin-web/tests/secretaireLayout.test.mjs`

**Interfaces:**
- Consumes (Task 1): `AppShell` (props ci-dessus).
- Produces: groupes `home` (Accueil), `patients` (Patients), `cash` (Caisse, Retraits, Historique des réductions), `stock` (Stock), `follow` (Consultations spirituelles, Échecs de synchronisation avec `onlyWhenQuarantine`). Chemins et `labelKey` **identiques** à l'existant : `/secretariat/`, `/secretariat/patients`, `/secretariat/stock`, `/secretariat/caisse`, `/secretariat/retrait`, `/secretariat/consultations`, `/secretariat/discount-history`, `/secretariat/sync-failures` avec `secretariat.nav.home`, `patients`, `stock`, `caisse`, `retrait`, `consultations`, `discount_history`, `sync_failures`. `bellRoles` = `['admin', 'promoteur', 'secretaire']` (valeur actuelle, à ne pas réduire).

- [ ] **Step 1: Test** : les 8 chemins et leurs `labelKey` sont présents, la cloche garde les trois rôles, l'entrée des échecs de synchronisation reste conditionnée à la quarantaine, les clés `secretariatShell.sections.{home,patients,cash,stock,follow}` existent en FR et EN sans caractère typographique interdit. Baseline des chemins verte sur l'ancien layout ; le reste échoue.
- [ ] **Step 2: Lancer** le test, attendu : échec sur les clés et l'import de `AppShell`.
- [ ] **Step 3: Implémenter** l'enveloppe et les clés ; aucun changement de droit.
- [ ] **Step 4: Vérifier** suite et build. Points visuels : menu avec intertitres, bouton de réduction, tiroir à 360 px, badge de quarantaine, cloche, l'espace médical identique.

---

### Task 3: Accueil du secrétariat (actions rapides, statistiques, alertes de stock)

**Files:**
- Create: `ah2-admin-web/src/components/ui/StatTile.vue`, `ah2-admin-web/tests/secretariatHome.test.mjs`
- Modify: `ah2-admin-web/src/components/ui/index.js` (réexport), `ah2-admin-web/src/views/modules/secretariat/SecretariatHomeView.vue`, `ah2-admin-web/src/views/modules/patients/PatientList.vue` (ouverture du formulaire si `?nouveau=1`), `ah2-admin-web/src/i18n.js` (`secretariatHome.*`, `ui.*` si besoin)

**Interfaces:**
- Produces: `StatTile` : props `title: string`, `value: string | number`, `note?: string`, `icon?: Component`, `tone?: 'neutral' | 'danger' | 'warning' | 'success' | 'info'` (défaut `neutral`, tonalité de l'icône seulement, jamais le texte), slot `default` facultatif sous la valeur ; utilise les jetons ; texte >= 14 px. Contrat pour `PatientList` : si `route.query.nouveau === '1'` au montage, appelle `openCreateModal()` puis `router.replace({ query: {} })` ; sans ce paramètre, aucun changement.
- Consumes: `PageHeader`, `AppButton`, `AppCard`, `ResponsiveTable`, `EmptyState`, `StatusBadge`, `homeStore` (inchangé).

- [ ] **Step 1: Test de contrat** (`secretariatHome.test.mjs`), baseline verte avant refonte : `homeStore.fetchStats` (ou l'appel existant du montage), `homeStore.filters.startDate` et `endDate` liés à `applyFilters`, `valeurAffichee('totalPaid'`, `valeurAffichee('totalWithdrawn'`, `soldeAffiche`, `valeurAffichee('remainingDue'`, `homeStore.stats.criticalStockCount`, `expiringStockCount`, `consultationsCount`, `homeStore.indisponibles.includes('criticalStockItems')`, `criticalStockItems`, les clés `secretariat.home.*` utilisées. Nouveaux : trois actions rapides avec liens exacts `/secretariat/caisse?nouveau=1`, `/secretariat/retrait?nouveau=1`, `/secretariat/patients?nouveau=1` ; aucune action rapide ne s'affiche sans droit (l'écran n'est joignable que par `secretaire`) ; `StatTile` existe, est réexporté et n'utilise aucune couleur brute ; `PatientList` contient `route.query.nouveau`.
- [ ] **Step 2: Lancer** : baseline verte, les cinq tests nouveaux échouent.
- [ ] **Step 3: Implémenter** `StatTile` ; refondre l'accueil dans l'ordre « à faire d'abord » : actions rapides (`AppButton` grands, icônes), carte « argent » (encaissé, retraits, solde, reste dû, valeurs dégradées inchangées via `valeurAffichee`), alertes de stock (`StatTile` rouge et orange + tableau des stocks critiques en `ResponsiveTable`), consultations de la période ; filtres de période conservés avec libellés au-dessus. Ajouter la lecture de `?nouveau=1` dans `PatientList` (seule modification de script autorisée hors imports).
- [ ] **Step 4: Vérifier** suite et build. Points visuels : actions rapides à 360, 768, 1280 px ; état « indisponible » d'un bloc ; ouverture directe du formulaire patient depuis l'accueil.

---

### Task 4: Stock (liste, produit, demande d'ajustement), écran partagé

**Files:**
- Modify: `ah2-admin-web/src/views/modules/stock/StockList.vue`, `ah2-admin-web/src/components/stock/ProductModal.vue`, `ah2-admin-web/src/components/stock/AdjustmentRequestModal.vue`, `ah2-admin-web/src/i18n.js` (ajouts)
- Create: `ah2-admin-web/tests/stockScreensContract.test.mjs`

**Interfaces:**
- Consumes: `ResponsiveTable`, `StatusBadge`, `FormField`, `FormSection`, `FullScreenPanel`, `ActionBar`, `AppButton`, `PageHeader`, `EmptyState`. Props et événements des deux modales **inchangés** (`can-edit-quantity`, `close`, `save`, demande d'ajustement).
- Produces: aucune API nouvelle.

- [ ] **Step 1: Test de contrat** (baseline verte) : `const isAdmin = computed(() => authStore.hasRole(['admin']))`, `const isSecretary = computed(() => authStore.hasRole(['secretaire']))`, `v-if="isSecretary" @click="openRequest(prod)"` (demande d'ajustement réservée à la secrétaire), `v-if="!isSecretary" @click="openModal(prod)"`, `v-if="isAdmin" @click="confirmDelete(prod)"`, la mise au rebut `handleDispose` (admin, produit périmé en stock), `stockStore.saveProduct(product, { canSetQuantity: isAdmin.value })`, `:can-edit-quantity="isAdmin"`, `if (!isAdmin.value) return;` aux deux endroits, la recherche en ligne de `onLineSearchInput` du modèle de la caisse si référencée, toutes les clés `stock.*` citées. Nouveaux : composants `ui/` importés, aucune couleur brute, aucun texte < 13 px, pas de caractère typographique interdit dans le gabarit.
- [ ] **Step 2: Lancer** : baseline verte, nouveaux tests en échec.
- [ ] **Step 3: Implémenter** : tableau (cartes sous `lg`) avec badge de statut de péremption par `StatusBadge` (échu rouge, proche orange, ok vert, avec texte), quantité mise en évidence, actions selon le rôle exactement comme avant ; modales en `FullScreenPanel` + `FormSection` + `ActionBar`.
- [ ] **Step 4: Vérifier** suite et build. Points visuels **en secrétaire, admin et assistant** (écran partagé) : bouton de demande d'ajustement seulement pour la secrétaire, modification et suppression pour les autres, mise au rebut pour l'admin.

---

### Task 5: Consultations spirituelles du secrétariat

**Files:**
- Modify: `ah2-admin-web/src/views/modules/consultations/ConsultationsList.vue`, `ah2-admin-web/src/components/consultations/ConsultationModal.vue`, `ah2-admin-web/src/i18n.js` (ajouts)
- Create: `ah2-admin-web/tests/consultationsScreensContract.test.mjs`

**Interfaces:**
- Consumes: mêmes composants `ui/` que la Tâche 4 + `ExportModal` (inchangé, partagé). `ConsultationModal` n'est utilisé que par ce rôle : modification autorisée.
- Produces: aucune API nouvelle.

- [ ] **Step 1: Test de contrat** (baseline verte) : appels `consultationStore.*` utilisés (liste, création, mise à jour, suppression, export), `v-model.lazy="searchQuery"` avec `@keyup.enter`, événements `close` et `save` de la modale, champs envoyés, règles de validation et messages, clés `consultations.*` citées. Nouveaux : composants `ui/`, tableau responsive, couleurs et textes conformes.
- [ ] **Step 2: Lancer** puis **Step 3: Implémenter** (tableau, filtres lisibles, modale en panneau à sections) puis **Step 4: Vérifier** suite et build ; points visuels à 360, 768, 1280 px ; aucun changement d'export.

---

### Task 6: Historique des réductions (écran partagé) et protocole de test avec la secrétaire

**Files:**
- Modify: `ah2-admin-web/src/views/modules/caisse/DiscountRequestsHistory.vue`, `ah2-admin-web/src/i18n.js` (ajouts)
- Create: `ah2-admin-web/tests/discountHistoryContract.test.mjs`, `docs/superpowers/usability-test-protocol-secretariat.md`

**Interfaces:**
- Consumes: `ResponsiveTable`, `StatusBadge`, `FormField`, `AppButton`, `PageHeader`.
- Produces: protocole d'une page : 5 tâches types pour la secrétaire (se connecter et trouver l'accueil ; chercher un patient ; vérifier un stock critique ; demander un ajustement de stock ; consulter l'historique des réductions), grille d'observation, consignes (ne pas aider, penser à voix haute), modèle de synthèse. Les tâches de caisse n'y figurent pas (Phase 3).

- [ ] **Step 1: Test de contrat** (baseline verte) : appels du store ou de l'API de la page, présélections de période (`periodPresets`, `applyPreset`), `goToPage`, filtres, clés `discount_history.*`. Nouveaux : composants `ui/`, pastilles de période en boutons avec `aria-pressed`, statuts approuvé, refusé, en attente par `StatusBadge` (texte), conformité des couleurs et textes ; le protocole contient « Tâche 1 » à « Tâche 5 », « Grille d'observation », « Modèle de synthèse ».
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** et rédiger le protocole, **Step 4: Vérifier** suite et build. **Point de contrôle : l'utilisateur vérifie les phases 1 et 2 dans le navigateur (en secrétaire, et en admin, promoteur, assistant pour les écrans partagés) et fait le test d'utilisation avant la Tâche 7.**

---

### Task 7: Caisse (liste des factures, annulation, versement, détail)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/finance/CaisseList.vue`, `ah2-admin-web/src/components/caisse/CaisseCancelModal.vue`, `ah2-admin-web/src/components/caisse/CaisseInstallmentModal.vue`, `ah2-admin-web/src/i18n.js` (ajouts)
- Create: `ah2-admin-web/tests/caisseListContract.test.mjs`

**Interfaces:**
- Consumes: `ResponsiveTable`, `StatusBadge`, `FullScreenPanel`, `FormField`, `ActionBar`, `AppButton`, `PageHeader`. Props et événements de `CaisseCancelModal` (`isSaving`, `errorMessage`, `close`, `save`) et `CaisseInstallmentModal` (`remainingDue`, `close`, `save`) **inchangés**.
- Produces: lecture de `route.query.nouveau === '1'` dans `CaisseList` : ouvre la facture (`showInvoiceModal = true`) puis `router.replace({ query: {} })` (seule modification de script autorisée hors imports et colonnes).

- [ ] **Step 1: Test de contrat renforcé** (baseline verte) : `printTicketForTransaction(tx.transaction_id)` sous `v-if="tx.status === 'active'"`, `printError` et son texte, le titre « En attente de synchronisation » quand `!tx.transaction_id`, `openViewModal`, `openInstallmentModal` sous `tx.status === 'active' && Number(tx.amount_due) > 0`, `openCancelModal` sous `tx.status === 'active'`, `handleCreateInvoice`, la gestion de `isSavingInvoice`/`invoiceError`, la lecture de réduction personnel et de réduction manuelle dans la liste (`staff_discount_amount`), les appels `caisseStore.*`, `refreshAfterSync`, filtres et pagination, toutes les clés `caisse.*` citées, ainsi que `tests/invoiceTotals.test.mjs`, `staffDiscount.test.mjs`, `receiptLines.test.mjs` verts. Nouveaux : composants `ui/`, montants alignés à droite et en police lisible, statuts (active, annulée, payée, reste dû) par `StatusBadge` avec texte, `route.query.nouveau`.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** : tableau responsive (cartes sous `lg`), reste dû en orange avec le montant écrit, facture annulée barrée et badge « annulée », boutons dans l'ordre Voir, Verser, Réimprimer, Annuler (danger) ; modales d'annulation et de versement en panneau avec aide sous les champs ; la zone de détail (aujourd'hui une surcouche noire) devient un `FullScreenPanel` en lecture seule.
- [ ] **Step 4: Vérifier** suite et build. Points visuels : en ligne et hors ligne, facture non synchronisée (boutons grisés), réimpression du ticket, erreur d'impression, montants à 360 px.

---

### Task 8: Facture (formulaire de facture de la caisse)

**Files:**
- Modify: `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue`, `ah2-admin-web/src/i18n.js` (ajouts)
- Create: `ah2-admin-web/tests/caisseInvoiceContract.test.mjs`

**Interfaces:**
- Consumes: `FullScreenPanel`, `FormSection`, `FormField`, `ActionBar`, `AppButton`, `StatusBadge`. Props (`isSaving`, `errorMessage`) et événements (`close`, `save`) **inchangés** ; la forme de l'objet envoyé par `save` est figée par le test.
- Produces: sections Patient, Articles, Réduction, Paiement, avec un récapitulatif fixe du total visible en bas sur téléphone (dans la barre d'actions).

- [ ] **Step 1: Test de contrat renforcé** (baseline verte) : tous les appels de calcul de `invoiceTotals` et `staffDiscount` et `receiptLines` utilisés, la recherche de patient (en ligne et secours hors ligne), `onLineSearchInput`, le blocage de validation quand `is_staff` est `null` avec l'avertissement « connectez-vous une fois pour terminer la synchronisation », le bandeau `showNoRuleApplies`, la demande de réduction manuelle et son contrôle de montant, les validations avant `emit('save', ...)` et les champs de la facture (liste figée par lecture), les types de ligne (« Médicament », « Carnet », examens, consultation, autre soin), toutes les clés citées. Nouveaux : `FullScreenPanel`, `FormSection`, `ActionBar`, couleurs et textes conformes, aucun calcul de montant dans le gabarit.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter** en ne déplaçant que des blocs de gabarit : le tableau des lignes devient des cartes sous `lg`, chaque ligne garde ses champs et ses suppressions ; le total net, la réduction et le reste à payer restent les valeurs déjà calculées.
- [ ] **Step 4: Vérifier** suite et build. Points visuels : facture d'un patient du personnel (bandeau et ligne de réduction), facture avec réduction manuelle, saisie hors ligne puis ticket, 20 lignes d'articles à 360 px, total toujours visible.

---

### Task 9: Retraits

**Files:**
- Modify: `ah2-admin-web/src/views/modules/finance/RetraitList.vue`, `ah2-admin-web/src/components/caisse/RetraitModal.vue`, `ah2-admin-web/src/i18n.js` (ajouts)
- Create: `ah2-admin-web/tests/retraitContract.test.mjs`

**Interfaces:**
- Consumes: composants `ui/` comme ci-dessus ; `CaisseCancelModal` (refondu à la Tâche 7). `RetraitModal` : props `isSaving`, `errorMessage` ; événements `close`, `save` inchangés.
- Produces: lecture de `route.query.nouveau === '1'` dans `RetraitList` (ouvre `showCreateModal`), même règle que la Tâche 7.

- [ ] **Step 1: Test de contrat** (baseline verte) : `retraitStore` ou appels existants, `openCancelModal(r)` sous `r.status === 'active'`, `handleCreate`, messages d'erreur, filtres, pagination, clés `retrait.*`. Nouveaux : composants `ui/`, tableau responsive, statuts par `StatusBadge`, `route.query.nouveau`, conformité couleurs et textes.
- [ ] **Step 2: Lancer**, **Step 3: Implémenter**, **Step 4: Vérifier** suite et build ; points visuels à 360, 768, 1280 px, création puis annulation d'un retrait.

---

### Task 10: Recette finale et documentation

**Files:**
- Create: `ah2-admin-web/tests/refonteSecretariatGuard.test.mjs`
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`, mémoire du projet (`project_refonte_ux_medical.md` renvoie vers la suite et une fiche courte pour le secrétariat)

**Interfaces:**
- Consumes: tous les éléments précédents.
- Produces: garde-fou durable du secrétariat, sur le modèle de `refonteGuard.test.mjs` : (a) aucune couleur en dur, texte >= 13 px, pas de caractère typographique interdit dans les fichiers refondus listés ; (b) tous les fichiers refondus importent `ui/` (exceptions justifiées par écrit) ; (c) parité FR et EN ; (d) pour la plage de commits de ce chantier (BASE = dernier commit avant la Tâche 1, FIN = dernier commit de la Tâche 9, constantes à renseigner), seuls les fichiers autorisés ont changé et les fichiers « argent » listés dans Global Constraints sont **intacts** ; (e) un contrôle que `AppShell` est utilisé par `MedicalLayout` et `SecretaireLayout`.

- [ ] **Step 1: Test** : écrire le garde-fou, le voir échouer sur une couleur en dur ajoutée volontairement, puis la retirer.
- [ ] **Step 2: Lancer** toute la suite et `npx vite build` (attendu : tout vert).
- [ ] **Step 3: Rédiger** la section du suivi : livré, décisions, rulings, **checklist à vérifier par l'utilisateur par écran et par largeur (360, 768, 1280 px)** avec une ligne par écran du secrétariat, plus les écrans partagés à revoir en admin, promoteur, assistant et toxico ; résiduels ; ce qu'il reste à migrer (admin, promoteur, laboratoire, toxicologie, stock-control) ; mise à jour de la mémoire.
