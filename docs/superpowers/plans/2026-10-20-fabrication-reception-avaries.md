# Fabrication, réception et avaries du stock — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter la fabrication (lots), la réception multi-lignes, les avaries et les demandes d'ajustement de la secrétaire au stock de la pharmacie, avec validation par un second compte (nouveau rôle `StockController`, ou `admin` pour les demandes de la secrétaire).

**Architecture:** 5 tables dédiées avec statut ; un `StockController` métier (`controller/stock_controller.py`) appelle un `StockRepository` ; l'effet sur `pharmacy.quantity` n'a lieu qu'à la validation, par mise à jour atomique, avec un `StockMovement` typé ; un nouveau routeur `/stock` (garde de rôle par route) ; le routeur `/pharmacy` reçoit des gardes d'écriture ; frontend Vue (écrans Assistant/admin, contrôleur, demandes de la secrétaire).

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (SQL brut) + pytest ; Vue 3 / Pinia / vue-i18n ; système de notifications existant (`NotificationRepository.create(recipient_user_id, type, payload)`).

**Spec:** `docs/superpowers/specs/2026-10-20-fabrication-reception-avaries-design.md` (source de vérité : les tables, statuts, règles et droits y sont définis ; ce plan ne les répète pas).

## Global Constraints

- Statuts (CHECK, valeurs exactes) : lot `produit|livre|recu|annule` ; réception et avarie `a_controler|valide|rejete` ; demande d'ajustement `en_attente|approuve|refuse|annule` ; origine `fabrication|fournisseur` ; type d'avarie `endommage|perdu|defectueux` ; type de demande `reapprovisionnement|correction`.
- Types de `StockMovement` nouveaux : `reception`, `avarie_endommage`, `avarie_perdu`, `avarie_defectueux` ; les demandes de la secrétaire réutilisent `renew` (réapprovisionnement) et `update` (correction).
- Rôle : `application_roles.role_name = 'StockController'` ; code canonique `stockcontroller`.
- Aucune entrée/sortie de stock avant validation ; **le validateur ≠ l'auteur** (403, y compris pour l'admin) ; rejet/refus : motif obligatoire (422).
- Toute modification de `pharmacy.quantity` à la validation est **atomique** (`UPDATE … SET quantity = quantity + :n` ou `SELECT … FOR UPDATE`), jamais lire-puis-écrire ; le stock ne descend jamais sous 0 (409) ; `stock_status` recalculé (`Pharmacy.update_stock_status`).
- Une opération décidée n'est jamais modifiable ; double validation concurrente → une seule applique l'effet, l'autre 409 (verrouiller la ligne de l'opération avec `FOR UPDATE`).
- Toutes les chaînes UI en FR **et** EN (`ah2-admin-web/src/i18n.js`). Écrans en ligne seulement.
- Migrations Alembic : SQL brut idempotent (`IF NOT EXISTS`), motif de `alembic/versions/018_staff_discount.py` ; reporter le DDL dans `ci/schema_only.sql` (CI le charge ; **fichier en fins de ligne CRLF**, les conserver). Dernière révision à ce jour : `018_staff_discount`.
- Tests : base de dev partagée avec des fixtures transactionnelles ; les tests doivent partir d'un état isolé (ne rien supposer sur les données réelles, comme la fixture `clean_staff_rules` de `tests/conftest.py`). Rôles réels pour `create_test_user(db, username, role_name, password=...)` : `admin`, `Assistant`, `ToxicoManager`, `secretaire`, `StockController` (après la migration).
- Disque presque plein par moments : ne jamais créer de copies/exports du dépôt ni de gros fichiers temporaires ; pas de suite complète dans les sous-agents (tests ciblés seulement).
- Ne pas commiter sans accord de l'utilisateur (mémoire projet) : sauter les étapes « Commit » sauf demande explicite de la session.

## Review Focus

- Double validation concurrente d'une même réception : le stock n'est ajouté qu'une fois. Test dans Task 2.
- Un `admin` qui a saisi une opération essaie de la valider : 403. Test dans Task 2 (réception), repris pour avarie et demande.
- Validation d'une avarie quand une vente a fait baisser le stock entre-temps : 409 sans effet partiel. Test dans Task 3.
- Réception qui ne renseigne que des quantités endommagées/perdues (qty_good = 0) : validée sans mouvement positif ni erreur. Test dans Task 2.
- Un rôle ayant accès à la route `/stock/...` de lecture mais pas d'écriture (StockController sur la saisie, Assistant sur la validation) : 403 réel côté serveur. Test dans Task 5.

---

### Task 1: Schéma — migration 019, modèles, rôle

**Files:**
- Create: `alembic/versions/019_stock_reception_avaries.py`, `models/stock_reception.py` (modèles `ProductionLot`, `StockReceipt`, `StockReceiptLine`, `StockIncident`, `StockAdjustmentRequest`)
- Modify: `models/__init__.py` (import), `ci/schema_only.sql` (même DDL, **CRLF**), `api_backend/backend_app/security/role_map.py` (constante `STOCKCONTROLLER = "stockcontroller"`, dans `ROLE_CANONICALS`, alias `{"stockcontroller", "stock_controller", "controleur_stock", "contrôleur de stock"}`)
- Test: `tests/test_stock_schema.py`, `tests/test_role_map.py` (ajout)

**Interfaces:**
- Produces: les 5 modèles aux colonnes exactes du spec §1 ; `application_roles` contient `StockController` ; `normalize_role_name("StockController") == "stockcontroller"`.

- [ ] **Step 1: Écrire `tests/test_stock_schema.py`** : (a) chaque CHECK de statut/type rejette une valeur inconnue (`IntegrityError`) ; (b) `quantity_produced = 0` et `qty_good = -1` rejetés ; (c) réception `origin='fabrication'` sans `production_lot_id` rejetée, `origin='fournisseur'` avec lot rejetée (CHECK de cohérence) ; (d) `lot_number` et `receipt_number` uniques ; (e) la suppression d'une réception supprime ses lignes (CASCADE) ; (f) `reapprovisionnement` avec `quantity = 0` rejeté, `correction` avec `quantity = 0` accepté ; (g) la ligne `application_roles` `StockController` existe. Ajouter à `tests/test_role_map.py` l'assertion de normalisation du nouveau rôle.
- [ ] **Step 2: Lancer** `python -m pytest tests/test_stock_schema.py tests/test_role_map.py -q` — attendu : échec.
- [ ] **Step 3: Écrire la migration 019** (`revision = '019_stock_reception_avaries'`, `down_revision = '018_staff_discount'`) : 5 tables du spec (FK, CHECK, uniques, index sur `status` des tables de statut), `INSERT INTO application_roles (role_name) SELECT 'StockController' WHERE NOT EXISTS (…)` (vérifier d'abord les colonnes NOT NULL de `application_roles`), `downgrade()` qui retire les tables (le rôle seulement si aucun utilisateur ne l'utilise). Modèles SQLAlchemy ; DDL dans `ci/schema_only.sql`.
- [ ] **Step 4: Appliquer** `alembic upgrade head` à la base de dev (politique de migration relâchée, autorisation explicite du contrôleur ; `alembic current` doit afficher `018_staff_discount` avant) puis vérifier directement par SQL la présence des 5 tables et de la ligne de rôle.
- [ ] **Step 5: Relancer** les tests de Step 1 + `tests/test_role_required.py -q` — attendu : PASS.
- [ ] **Step 6: Commit** `feat: schema stock (lots, receptions, avaries, demandes) et role StockController`.

---

### Task 2: Lots et réceptions — dépôt et contrôleur

**Files:**
- Create: `repositories/stock_repo.py` (classe `StockRepository`), `controller/stock_controller.py` (classe `StockController` + exceptions `StockConflictError(Exception)`), `tests/test_stock_receipts.py`
- Modify: —

**Interfaces:**
- Consumes: modèles de Task 1 ; `Pharmacy`, `StockMovement` ; `NotificationRepository.create(recipient_user_id, type, payload)` ; `AuditRepository.log_user_action(current_user=…, resource_type=…, action_performed=…, resource_id=…, old_values=…, new_values=…)`.
- Produces: `StockController(repo: StockRepository, notification_repo: NotificationRepository, audit_repo: AuditRepository, current_user)` — **les trois dépendances sont obligatoires** (pas de défaut `None`) — avec :
  - `create_lot(data: dict) -> dict` (`product_id, quantity_produced, production_date, delivery_date?, expiry_date?, producer?`; génère `lot_number` `LOT-AAAAMMJJ-NNN`), `list_lots(status: str | None) -> list[dict]`, `mark_lot_delivered(lot_id: int, delivery_date: date | None) -> dict`, `cancel_lot(lot_id: int) -> dict` (refusé 409 si une réception non rejetée y est liée) ;
  - `create_receipt(data: dict) -> dict` (`origin, production_lot_id?, supplier?, delivery_ref?, received_date, lines: list[{product_id, qty_expected?, qty_good, qty_damaged, qty_lost, qty_defective, lot_number?, expiry_date?}]` ; pour `fabrication`, le lot doit être `livre`, une seule ligne, produit/attendu/péremption préremplis depuis le lot si absents) ; notifie `stock_to_check` (payload `{receipt_id, receipt_number, created_by_name}`) aux utilisateurs actifs de rôle `StockController` et `admin` autres que l'auteur ;
  - `list_receipts(status: str | None, mine_only: bool) -> list[dict]`, `get_receipt(receipt_id: int) -> dict` (avec lignes et noms de produits) ;
  - `update_receipt_lines(receipt_id: int, lines: list[dict]) -> dict` (statut `a_controler` seulement ; audit old/new) ;
  - `validate_receipt(receipt_id: int) -> dict`, `reject_receipt(receipt_id: int, reason: str) -> dict`, `cancel_receipt(receipt_id: int) -> dict` (auteur ou admin ; statut final `rejete` avec motif « annulé par l'auteur ») ;
  - erreurs : `ValueError` → 422, `PermissionError` → 403, `StockConflictError` → 409 (mappées par Task 5).

- [ ] **Step 1: Écrire les tests** (`tests/test_stock_receipts.py`, appels directs du contrôleur sur `db_session`) : (a) création d'un lot, numérotation `LOT-…-001` puis `-002` le même jour ; (b) création d'une réception `fabrication` exige un lot `livre` ; lot `produit`/`recu`/`annule` → `ValueError` ; préremplissage depuis le lot ; (c) réception `fournisseur` multi-lignes ; somme > `qty_expected` rejetée, ligne à somme 0 rejetée, bon sans ligne rejeté ; (d) `validate_receipt` : `pharmacy.quantity` augmente de `Σ qty_good`, un `StockMovement` `reception` par ligne avec `qty_good > 0` (note citant le n° de réception et les avaries), `expiry_date` du produit = la plus proche, lot → `recu`, réception → `valide`, `controlled_by/at`, ligne d'audit ; (e) **review focus** : réception avec `qty_good = 0` partout → validée, aucun mouvement, stock inchangé ; (f) **review focus** : deux appels successifs de `validate_receipt` → le second lève `StockConflictError` et le stock n'a augmenté qu'une fois (et un test qui simule la concurrence en verrouillant la ligne dans une autre session si l'infrastructure de test le permet — sinon l'indiquer) ; (g) l'auteur ne peut pas valider (y compris s'il est `admin`) → `PermissionError` ; un `Assistant` non auteur ne peut pas valider ; (h) `reject_receipt` sans motif → `ValueError`, avec motif : stock inchangé, lot reste `livre` ; (i) `update_receipt_lines` change les quantités, audit contient old/new, refusé hors `a_controler` ; (j) `cancel_receipt` par un tiers non admin → `PermissionError` ; (k) notification `stock_to_check` créée pour un `StockController` actif et pour l'admin, pas pour l'auteur.
- [ ] **Step 2: Lancer** `python -m pytest tests/test_stock_receipts.py -q` — attendu : échec (module absent).
- [ ] **Step 3: Implémenter `StockRepository` et `StockController`** : numérotation par comptage des lots du jour sous verrou ; validation en une seule transaction avec `SELECT … FOR UPDATE` sur la réception puis sur chaque produit, incrément SQL atomique de `quantity`, recalcul du statut, mouvements, audit, notifications ; règle « validateur ≠ auteur » appliquée avant tout effet. Les rôles autorisés sont vérifiés par les endpoints (Task 5) ; le contrôleur vérifie seulement `≠ auteur` et l'état.
- [ ] **Step 4: Relancer** les tests de Step 1 + `tests/test_caisse.py tests/test_discount_requests.py -q` (non-régression des mouvements de stock) — attendu : PASS (hors échec préexistant connu `test_create_transaction_amount_mismatch_returns_400`).
- [ ] **Step 5: Commit** `feat: lots de fabrication et receptions controlees`.

---

### Task 3: Avaries sur le stock en rayon

**Files:**
- Modify: `repositories/stock_repo.py`, `controller/stock_controller.py`
- Test: `tests/test_stock_incidents.py`

**Interfaces:**
- Consumes: Task 2 (patterns, exceptions, notifications).
- Produces: `StockController.create_incident(data: dict) -> dict` (`product_id, kind, quantity, reason, incident_date`) ; `list_incidents(status: str | None, mine_only: bool) -> list[dict]` ; `validate_incident(incident_id: int) -> dict` ; `reject_incident(incident_id: int, reason: str) -> dict` ; `cancel_incident(incident_id: int) -> dict`. Validation : `pharmacy.quantity -= quantity` atomique, 409 `StockConflictError` si `quantity` dépasse le stock au moment de la validation (aucun effet partiel), `StockMovement` `avarie_<kind>` avec `change_qty = −quantity`, `stock_status` recalculé, audit, notification `stock_decided`.

- [ ] **Step 1: Tests** : création → `a_controler`, stock inchangé, notification `stock_to_check` ; validation retire la quantité avec le bon type de mouvement et `change_qty` négatif ; **review focus** : stock 5, avarie de 4 créée, une vente de 3 ramène le stock à 2 puis validation → `StockConflictError`, stock inchangé (2), avarie toujours `a_controler` ; auteur ≠ validateur (y compris admin) ; rejet sans motif → `ValueError` ; `kind` inconnu / `quantity ≤ 0` / motif vide → `ValueError` ; opération déjà décidée → `StockConflictError` ; annulation par l'auteur ; notification `stock_decided` à l'auteur.
- [ ] **Step 2: Lancer** `python -m pytest tests/test_stock_incidents.py -q` — attendu : échec.
- [ ] **Step 3: Implémenter** dans le dépôt et le contrôleur en réutilisant le verrouillage et le recalcul de Task 2 (un seul helper interne pour « appliquer un delta de stock atomiquement avec garde ≥ 0 »).
- [ ] **Step 4: Relancer** Step 1 + `tests/test_stock_receipts.py -q` — attendu : PASS.
- [ ] **Step 5: Commit** `feat: avaries sur le stock avec validation`.

---

### Task 4: Demandes d'ajustement de la secrétaire (approbation admin)

**Files:**
- Modify: `repositories/stock_repo.py`, `controller/stock_controller.py`
- Test: `tests/test_stock_adjustment_requests.py`

**Interfaces:**
- Consumes: Tasks 2-3 (helper de delta atomique, notifications).
- Produces: `StockController.create_adjustment_request(data: dict) -> dict` (`product_id, kind, quantity, reason`) ; `list_adjustment_requests(status: str | None, mine_only: bool) -> list[dict]` ; `approve_adjustment(request_id: int) -> dict` ; `reject_adjustment(request_id: int, note: str) -> dict` ; `cancel_adjustment(request_id: int) -> dict` (la demandeuse, tant que `en_attente`). Approbation : `reapprovisionnement` → `quantity += quantity` + mouvement `renew` ; `correction` → `quantity = quantity` avec mouvement `update` dont `change_qty` = nouvelle − quantité relevée sous verrou à l'approbation ; `stock_before`/`stock_after` renseignés ; notification `stock_decided` à la demandeuse ; notification `stock_adjustment_request` (payload `{request_id, product_name, kind, quantity, requested_by_name}`) à tous les admins actifs à la création.

- [ ] **Step 1: Tests** : création sans effet sur le stock + notifications aux admins ; approbation réapprovisionnement (+N, mouvement `renew`, `stock_before/after`) ; approbation correction (stock final = valeur demandée, `change_qty` = différence au moment de l'approbation après une vente intermédiaire ; 0 autorisé) ; refus sans motif → `ValueError` ; refus avec motif : aucun changement ; demandeuse ≠ approbateur (une secrétaire ne peut pas approuver) ; demande déjà décidée → `StockConflictError` ; quantité invalide (≤ 0 réapprovisionnement, < 0 correction), motif vide, produit inconnu → `ValueError` ; annulation.
- [ ] **Step 2: Lancer** `python -m pytest tests/test_stock_adjustment_requests.py -q` — attendu : échec.
- [ ] **Step 3: Implémenter** (contrôleur + dépôt, même helper atomique).
- [ ] **Step 4: Relancer** Step 1 + `tests/test_stock_incidents.py tests/test_stock_receipts.py -q` — attendu : PASS.
- [ ] **Step 5: Commit** `feat: demandes d'ajustement de stock de la secretaire`.

---

### Task 5: Routeur `/stock`, schémas, câblage, historique des mouvements

**Files:**
- Create: `api_backend/backend_app/routes/stock/__init__.py`, `api_backend/backend_app/routes/stock/stock_endpoints.py`, `api_backend/backend_app/routes/stock/stock_schemas.py`
- Modify: `api_backend/backend_app/main.py` (inclure le routeur ; pas de préfixe en conflit avec `/pharmacy`), `repositories/stock_repo.py` + `controller/stock_controller.py` (`list_movements`)
- Test: `tests/test_stock_endpoints.py`

**Interfaces:**
- Consumes: `StockController` de Tasks 2-4 ; `role_required(*roles)` ; `get_current_user`.
- Produces: routeur `APIRouter(prefix="/stock", tags=["Stock"])` **sans garde globale** ; une fonction d'injection `get_stock_controller(current_user, db) -> StockController` qui construit **réellement** `StockRepository`, `NotificationRepository`, `AuditRepository` ; routes et rôles exactement ceux de la table du spec §3 (lots, réceptions, avaries, demandes d'ajustement, `GET /stock/movements`) ; `StockController.list_movements(product_id: int | None, movement_type: str | None, date_from: date | None, date_to: date | None, page: int, per_page: int) -> dict` avec `{items, total, page, per_page}` (items : produit, type, `change_qty`, note, `created_by`, `created_at`) ; mapping des erreurs : `ValueError` → 422 (ou 400 pour paramètres), `PermissionError` → 403, `StockConflictError` → 409.

- [ ] **Step 1: Tests de bout en bout par vrais appels HTTP** (`api_client(auth_endpoints, stock_endpoints)`) : (a) matrice de droits : pour chacune des routes, `admin`, `Assistant`, `StockController`, `secretaire`, `ToxicoManager`, `medecin` → 200/201 ou 403 conformément au spec (écriture de saisie : Assistant/admin ; validation/rejet/correction : StockController/admin ; demandes : secretaire crée, admin approuve ; lecture des mouvements : StockController/admin/Assistant) ; **review focus** : StockController et secrétaire reçoivent 403 sur la saisie de lot/réception/avarie, Assistant 403 sur validate/reject ; (b) **câblage réel** : création d'une réception par `POST /stock/receipts` crée bien une ligne `Notification` `stock_to_check` pour un contrôleur et l'admin (vérifier en base après coup) ; idem demande d'ajustement → notifications admins ; décision → notification à l'auteur ; (c) auteur = validateur → 403 par HTTP ; double validation → 409 ; stock insuffisant → 409 ; payload invalide → 422 ; (d) `GET /stock/movements` : filtre par produit/type/dates, pagination, contient une vente (type `VENTE`) créée dans le test et un mouvement `reception` ; (e) parcours complet : lot → livré → réception → correction des lignes par le contrôleur → validation → stock et lot corrects.
- [ ] **Step 2: Lancer** `python -m pytest tests/test_stock_endpoints.py -q` — attendu : échec.
- [ ] **Step 3: Implémenter** schémas Pydantic (entrées strictes, quantités entières ≥ 0, dates), endpoints minces appelant le contrôleur, `get_stock_controller` avec les trois dépôts réellement injectés, inclusion dans `main.py`.
- [ ] **Step 4: Relancer** Step 1 + `tests/test_stock_receipts.py tests/test_stock_incidents.py tests/test_stock_adjustment_requests.py tests/test_role_required.py -q` — attendu : PASS.
- [ ] **Step 5: Commit** `feat: routeur /stock et historique des mouvements`.

---

### Task 6: Gardes d'écriture du routeur `/pharmacy`

**Files:**
- Modify: `api_backend/backend_app/routes/pharmacy/pharmacy_endpoints.py`, `controller/pharmacy_controller.py`
- Test: `tests/test_pharmacy_write_guards.py`

**Interfaces:**
- Consumes: `role_required`, `PharmacyController` existant (`create_product`, `update_product`, `renew_stock`, `delete_product`).
- Produces: `POST /pharmacy/{id}/renew` et `DELETE /pharmacy/{id}` : `admin` seul (garde par route en plus de la garde de routeur) ; `PUT /pharmacy/{id}` : rôles `admin`, `Assistant`, `ToxicoManager` (secretaire 403), et si le corps contient `quantity` (clé présente) et que l'utilisateur n'est pas `admin` → 403 « passez par une réception ou une avarie » ; `POST /pharmacy/` : rôles `admin`, `Assistant`, `ToxicoManager` (secretaire 403), `quantity` forcée à 0 pour tout rôle autre qu'`admin` ; lectures inchangées (secretaire incluse, StockController **exclu** du routeur).

- [ ] **Step 1: Tests (HTTP)** : `renew` et `DELETE` : admin 200/204, Assistant/ToxicoManager/secretaire 403 ; `PUT` sans `quantity` par Assistant et ToxicoManager → 200 (prix modifié), avec `quantity` → 403 et stock inchangé, par admin → 200 et un mouvement `update` ; `PUT` par secretaire → 403 ; `POST /pharmacy/` par Assistant avec `quantity: 50` → produit créé avec `quantity == 0` ; par admin avec `quantity: 50` → 50 ; par secretaire → 403 ; `GET /pharmacy/` par secretaire → 200 ; par StockController → 403 ; non-régression : la recherche produit de la caisse (`GET /pharmacy/?term=`) reste ouverte à la secrétaire.
- [ ] **Step 2: Lancer** `python -m pytest tests/test_pharmacy_write_guards.py -q` — attendu : échec.
- [ ] **Step 3: Implémenter** les gardes par route (`dependencies=[Depends(role_required(…))]` ET sémantique : une garde de route s'ajoute à la garde de routeur ; la liste de rôles d'une route ne peut donc qu'être un sous-ensemble du routeur) et le contrôle de la clé `quantity` / le forçage à 0 dans le contrôleur ou l'endpoint (à l'endroit où l'utilisateur courant est disponible).
- [ ] **Step 4: Relancer** Step 1 + `tests/test_caisse.py tests/test_caisse_staff_discount.py -q` — attendu : PASS (hors échec préexistant connu).
- [ ] **Step 5: Commit** `feat: gardes d'ecriture du stock (admin seul pour les quantites)`.

---

### Task 7: Plomberie du rôle `StockController` côté frontend et audit des routes non gardées

**Files:**
- Modify: `ah2-admin-web/src/router/index.js` (`ROLES.STOCK_CONTROLLER = 'StockController'`), `ah2-admin-web/src/views/LoginView.vue` (`getRedirectPath` : `stockcontroller` → `/dashboard/stock-control`), `ah2-admin-web/src/components/layout/MainLayout.vue` (constante de rôle + `NotificationBell` visible pour `StockController` et `Assistant`), `ah2-admin-web/src/components/users/UserModal.vue` (rôle sous `app_admin` + libellé), `ah2-admin-web/src/views/modules/users/UserManagement.vue` si les libellés y sont listés, `ah2-admin-web/src/components/notifications/NotificationBell.vue` (libellés des types `stock_to_check`, `stock_adjustment_request`, `stock_decided`, et navigation au clic vers la bonne page), `ah2-admin-web/src/stores/notificationStore.js` si le démarrage du polling dépend du rôle, `ah2-admin-web/src/i18n.js` (libellé du rôle + libellés de notifications, FR/EN)
- Create: —

**Interfaces:**
- Consumes: `authStore.hasRole([...])`.
- Produces: un compte `StockController` peut être créé dans la gestion des utilisateurs, se connecte, atterrit sur `/dashboard/stock-control` (créée en Task 9 ; pour cette tâche la redirection pointe dessus), voit la cloche de notifications, n'a **aucun** autre élément de menu que ceux de Task 9 ; le rôle n'est dans aucune liste de `roles` existante.

- [ ] **Step 1: Implémenter la plomberie** ci-dessus ; la route `/dashboard/stock-control` est déclarée en Task 9 (ne pas la créer ici ; vérifier seulement que `getRedirectPath` la vise).
- [ ] **Step 2: Audit serveur (lecture seule, ne rien corriger)** : lister dans le rapport les routes FastAPI qui n'ont **aucune** garde `role_required` (authentification seule via `get_current_user`) et qui exposent des données sensibles (patients, caisse, labo, utilisateurs) à n'importe quel compte authentifié — un `StockController` pourrait donc les appeler même si son menu est limité ; donner pour chacune fichier:ligne et méthode. (Ex. connu : `PUT /caisse/{id}` n'a pas de garde de rôle.) C'est un constat pour l'utilisateur, hors périmètre de correction.
- [ ] **Step 3: Vérifier** `cd ah2-admin-web && npx vite build` (succès) ; dire explicitement que le test navigateur n'est pas fait.
- [ ] **Step 4: Commit** `feat: role StockController cote frontend et notifications de stock`.

---

### Task 8: Frontend Assistant/admin — Fabrication, Réceptions, Avaries

**Files:**
- Create: `ah2-admin-web/src/services/StockOpsGateway.js`, `ah2-admin-web/src/views/modules/stock/ProductionLots.vue`, `ah2-admin-web/src/views/modules/stock/StockReceipts.vue`, `ah2-admin-web/src/views/modules/stock/StockIncidents.vue`, `ah2-admin-web/src/utils/receiptLines.js`, `ah2-admin-web/tests/receiptLines.test.mjs`
- Modify: `ah2-admin-web/src/router/index.js` (routes `stock-lots`, `stock-receipts`, `stock-incidents` sous `/dashboard`, rôles `ROLES.ADMIN`, `ROLES.ASSISTANT`), `ah2-admin-web/src/components/layout/MainLayout.vue` (entrées de menu, mêmes rôles), `ah2-admin-web/src/i18n.js` (FR/EN)

**Interfaces:**
- Consumes: routes `/stock/lots`, `/stock/receipts`, `/stock/incidents` (Task 5) ; produits via `GET /pharmacy/` existant.
- Produces: `StockOpsGateway` (une fonction par route du routeur `/stock`) ; `receiptLines.js` exporte `validateReceiptLine(line) -> { ok: boolean, error?: string }` (somme `good+damaged+lost+defective` > 0, ≤ `qty_expected` si renseignée, entiers ≥ 0) et `prefillFromLot(lot) -> line` ; pages : liste + formulaire de saisie des lots (bouton « Marquer livré », « Annuler »), réceptions (choix de l'origine : lot livré → ligne préremplie ; fournisseur → lignes libres avec ajout/suppression, totaux par ligne, statut de chaque bon avec motif de rejet affiché), avaries (produit, type, quantité, motif, date) ; erreurs du serveur (403/409/422) affichées avec leur message, jamais avalées.

- [ ] **Step 1: Test node** `receiptLines.test.mjs` (RED d'abord) : somme nulle refusée ; somme > attendu refusée ; somme = attendu et inférieure acceptées ; valeurs négatives/non entières refusées ; `prefillFromLot` reprend produit, attendu = quantité du lot, péremption.
- [ ] **Step 2: Implémenter** le gateway, l'utilitaire, les 3 pages, routes, menu, i18n ; relancer `node --test ah2-admin-web/tests/*.test.mjs`.
- [ ] **Step 3: Vérifier** `cd ah2-admin-web && npx vite build` ; dire explicitement que le test navigateur n'est pas fait.
- [ ] **Step 4: Commit** `feat: ecrans fabrication, receptions et avaries`.

---

### Task 9: Frontend — contrôleur, demandes d'ajustement (admin et secrétaire)

**Files:**
- Create: `ah2-admin-web/src/views/modules/stock/StockControlQueue.vue` (route `stock-control`), `ah2-admin-web/src/views/modules/stock/StockMovements.vue` (route `stock-movements`), `ah2-admin-web/src/views/modules/stock/AdjustmentRequestsAdmin.vue` (route `stock-adjustment-requests`), `ah2-admin-web/src/components/stock/AdjustmentRequestModal.vue`
- Modify: `ah2-admin-web/src/router/index.js` (routes ci-dessus : `stock-control` et `stock-movements` rôles `StockController`+`admin` (+`Assistant` pour `stock-movements`) ; `stock-adjustment-requests` rôle `admin` seulement), `ah2-admin-web/src/components/layout/MainLayout.vue` (menu : pour `StockController` uniquement « À contrôler » et « Mouvements »), `ah2-admin-web/src/views/modules/stock/StockList.vue` (route secrétaire `/secretariat/stock` : bouton « Demander un réapprovisionnement / une correction » par produit + liste « Mes demandes » ; **masquer** pour cette vue tout bouton d'écriture existant s'il y en a), `ah2-admin-web/src/services/StockOpsGateway.js`, `ah2-admin-web/src/i18n.js` (FR/EN)

**Interfaces:**
- Consumes: routes de Task 5 ; `NotificationBell` (Task 7).
- Produces: file « À contrôler » (réceptions et avaries `a_controler` avec détail, correction inline des quantités d'une réception avant validation, boutons Valider / Rejeter avec champ motif obligatoire ; masquer Valider pour ses propres saisies) ; historique des mouvements (filtres produit/type/période, pagination) ; page admin des demandes (stock actuel affiché, Approuver / Refuser avec motif) ; modal de demande pour la secrétaire (type, quantité, motif ; validation locale : quantité > 0 pour un réapprovisionnement, ≥ 0 pour une correction, motif non vide).

- [ ] **Step 1: Implémenter** les pages, routes, menu, modal, i18n ; ajouter à `ah2-admin-web/tests/` un test node pour toute fonction pure extraite (ex. validation de la demande de la secrétaire).
- [ ] **Step 2: Vérifier** `node --test ah2-admin-web/tests/*.test.mjs` et `cd ah2-admin-web && npx vite build` ; dire explicitement que le test navigateur n'est pas fait et lister ce que l'utilisateur doit tester (parcours complet lot → réception → contrôle, avarie, demande de la secrétaire, compte `StockController` limité à ses 2 pages, URL interdites).
- [ ] **Step 3: Commit** `feat: ecrans controleur, mouvements et demandes d'ajustement`.

---

### Task 10: Suivi et vérification finale

**Files:**
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`, mémoire projet (`project_backlog_pre_deploiement.md` : items 1 et 2 faits)

- [ ] **Step 1: Suite backend complète** : `python -m pytest tests -q -p no:cacheprovider` ; comparer aux 9 échecs préexistants documentés (prescriptions ×7, audit à l'annulation, message de montant) — aucun nouvel échec attendu.
- [ ] **Step 2: Frontend** : `node --test ah2-admin-web/tests/*.test.mjs` et `npx vite build`.
- [ ] **Step 3: Mettre à jour** le suivi (livré, écarts assumés, résultat de l'audit des routes non gardées de Task 7, ce qui n'a pas été vérifié dans un navigateur) et la mémoire.
- [ ] **Step 4: Commit** `docs: suivi fabrication, reception et avaries`.
