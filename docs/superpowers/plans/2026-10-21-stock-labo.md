# Stock du laboratoire — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un module « Stock labo » indépendant de la caisse et de la pharmacie : produits du labo, réception de livraison (fiche fournisseur) saisie et validée en une fois par le contrôleur/promoteur, comptage hebdomadaire, signalement, liste « à commander » avec suivi de commande, alertes (seuil, péremption), notifications et suivi des dépenses.

**Architecture:** Nouvelles tables `lab_stock_*` (migration 021) ; un dépôt `LabStockRepository`, un contrôleur `LabStockController`, un routeur `/lab-stock` avec garde de rôle par route, sur le modèle exact du chantier `/stock` (`controller/stock_controller.py`, `repositories/stock_repo.py`, `api_backend/backend_app/routes/stock/`). Frontend Vue en ligne seulement, mobile d'abord pour la réception et le comptage.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic (SQL brut), pytest sur la vraie base de dev ; Vue 3 + Pinia + vue-i18n, Tailwind.

**Spec:** `docs/superpowers/specs/2026-10-21-stock-labo-design.md` (autorité ; sa section « Choix du concepteur » complète les règles de livraison partielle, annulation, comptage concurrent).

## Global Constraints

- Aucune modification de `pharmacy`, `caisse`, `stock_movements`, ni du chantier `/stock` existant. Tables préfixées `lab_stock_`.
- Rôles (codes utilisés par `role_required`) : `laborantin` (technicienne), `StockController` (contrôleur), `promoteur`, `ToxicoManager` (manager), `admin`. Aucun autre rôle n'a accès. Matrice (constantes du routeur) : LECTURE = laborantin, StockController, promoteur, ToxicoManager, admin ; ÉCRITURE PRODUIT = laborantin, StockController, admin ; RÉCEPTION = StockController, promoteur, admin ; COMPTAGE et SIGNALEMENT = laborantin, admin ; COMMANDE (marquer commandé / modifier la date / annuler une demande) = promoteur, ToxicoManager, admin ; DÉPENSES = promoteur, ToxicoManager, admin ; ANNULER UNE RÉCEPTION = admin seul. Contrôle **côté serveur** ; promoteur et manager ne créent jamais de produit ; le manager ne saisit jamais de réception.
- Toute écriture de `lab_stock_products.quantity` : verrou `with_for_update().populate_existing()` par produit, ordre d'identifiant croissant, jamais < 0 (`LabStockConflictError` → 409) ; helper unique `apply_delta(product_id, delta, movement_type, ref_type, ref_id, user)` qui écrit aussi le mouvement `lab_stock_movements`. Erreurs : `LabStockNotFoundError` → 404, `ValueError` → 422, `PermissionError` → 403, `LabStockConflictError` → 409 (mêmes classes de base que `StockNotFoundError`/`StockConflictError`).
- Valeurs fermées en CHECK dans la migration **et** dans `ci/schema_only.sql` (la CI ne rejoue pas les migrations ; le rôle n'a pas à être semé, ils existent). Migration 021 : `down_revision = '020_adjustment_stock_at_request'`, SQL brut idempotent, motif de `alembic/versions/019_stock_reception_avaries.py`.
- Seuils en constantes du module `utils/lab_stock_rules.py` : `EXPIRY_WARNING_DAYS = 60`, `COUNT_REMINDER_DAYS = 7`. Montants en FCFA, entiers ou décimaux comme `caisse.amount` (suivre son type), aucune taxe.
- Notifications via `NotificationRepository.create(user_id, type, payload)` ; destinataires « promoteur + ToxicoManager » = tous les utilisateurs actifs portant ces rôles (même technique que l'envoi aux admins dans `StockController`). Types : `lab_stock_signal`, `lab_stock_low`, `lab_stock_expiry`, `lab_stock_received`, `lab_stock_count_reminder`. Dédupliquer par `(type, clé)` : ne pas recréer une notification identique non lue.
- Tests : base de dev partagée, fixtures transactionnelles (`db_session`) ; **toute commande pytest sous `timeout 170`**, jamais la suite complète ; connexion limitée à 5/min : **au plus 4 connexions par test** ; Redis (`ah2_redis`) doit tourner ; disque presque plein : aucune copie du dépôt. Pas de commit (l'utilisateur décide). Toutes les chaînes UI en FR **et** EN dans `ah2-admin-web/src/i18n.js`.
- Frontend : en ligne seulement ; **trois mises en page soignées, aucune ne doit paraître étirée ou bâclée** : téléphone (360 px) = cartes empilées, champs numériques `inputmode="numeric"`, boutons ≥ 44 px ; tablette (≥ 768 px) = deux colonnes, saisie confortable au doigt ; PC (≥ 1024 px) = vrais tableaux (lignes de réception en colonnes n° / désignation / conditionnement / qté commandée / qté reçue / lot / péremption / prix unitaire / total, comme la fiche papier), largeur de contenu bornée et alignée sur les autres écrans du projet (mêmes composants, espacements et couleurs que `StockList.vue`). Tailwind : écrire le style mobile par défaut puis `md:` et `lg:`. Pas de `localStorage` pour des données métier.

## Review Focus

- Deux réceptions simultanées (ou réception + comptage) sur le même produit : pas de stock perdu, pas de valeur négative (verrous, ordre croissant). Test dans Task 3 et Task 4.
- Même (fournisseur, n° de facture) saisi deux fois (double clic sur téléphone) : un seul stock ajouté, le second est refusé 409. Test dans Task 3.
- Promoteur ou manager appelant `POST /lab-stock/products` → 403 ; manager appelant `POST /lab-stock/receipts` → 403 ; médecin/infirmier/secrétaire → 403 sur toute route. Test dans Task 2 (matrice rôles × routes).
- `StockController` : ses nouvelles routes marchent, mais il reste refusé partout ailleurs (`tests/test_stockcontroller_deny.py` doit rester vert). Test dans Task 2.
- Produit sans comptage jamais effectué, produit désactivé, lot sans stock, seuil 0 : ni erreur ni fausse alerte. Test dans Task 4.

---

### Task 1: Schéma et modèles

**Files:**
- Create: `alembic/versions/021_lab_stock.py`, `models/lab_stock.py`, `utils/lab_stock_rules.py`
- Modify: `ci/schema_only.sql` (ajouter les 7 tables ; format de fin de ligne du fichier à respecter, édition minimale), `models/__init__.py` si les modèles y sont enregistrés
- Test: `tests/test_lab_stock_schema.py`

**Interfaces:**
- Produces (SQLAlchemy, `Base` de `models/database.py`) : `LabStockProduct(id, name, packaging, alert_threshold>=0, supplier, quantity>=0 default 0, last_counted_at, is_active default true, created_by FK users, created_at)` avec index unique partiel `lower(name) WHERE is_active` ; `LabStockReceipt(id, invoice_number, supplier, delivery_date, total_amount>=0, status IN ('valide','annule'), cancel_reason, created_by, created_at, cancelled_by, cancelled_at)` avec contrainte unique `(lower(supplier), lower(invoice_number))` parmi `status='valide'` (index partiel) ; `LabStockReceiptLine(id, receipt_id FK cascade, product_id FK, ordered_qty NULL>=0, received_qty>0, unit_price>=0, line_total>=0, lot_number NOT NULL, expiry_date NOT NULL, note)` ; `LabStockCount(id, counted_by, counted_at)` ; `LabStockCountLine(id, count_id FK cascade, product_id, previous_qty>=0, counted_qty>=0)` ; `LabStockMovement(id, product_id, change_qty, movement_type IN ('reception','comptage','annulation_reception'), ref_type, ref_id, quantity_after>=0, created_by, created_at)` ; `LabStockRequest(id, product_id, origin IN ('signalement','seuil','peremption'), level IN ('bientot_fini','fini') NULL, status IN ('a_commander','commande','recu','annule'), requested_by NULL, ordered_by NULL, expected_date NULL, closed_by_receipt_id NULL FK, cancel_reason NULL, created_at, ordered_at, closed_at)` avec index unique partiel `(product_id) WHERE status IN ('a_commander','commande')`.
- `utils/lab_stock_rules.py` : `EXPIRY_WARNING_DAYS`, `COUNT_REMINDER_DAYS`.

- [ ] **Step 1: Tests** (`tests/test_lab_stock_schema.py`) : chaque CHECK refuse une valeur hors liste (statut de réception, origine/statut de demande, mouvement, quantité négative, `received_qty = 0`) ; l'index unique partiel refuse une 2e demande ouverte pour un produit mais accepte une nouvelle après `recu`/`annule` ; deux produits actifs au nom identique (casse différente) refusés, un désactivé n'empêche pas la recréation ; doublon (fournisseur, n° de facture) refusé tant que la première est `valide`, accepté si elle est `annule`.
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_lab_stock_schema.py -q -p no:cacheprovider` — attendu : échec (tables absentes).
- [ ] **Step 3: Écrire** la migration 021 (`CREATE TABLE IF NOT EXISTS`, index, CHECK), les modèles et le DDL de `ci/schema_only.sql`. Vérifier `alembic current` = `020_adjustment_stock_at_request (head)` puis `alembic upgrade head` sur la base de dev et confirmer les tables par SQL.
- [ ] **Step 4: Relancer** Step 2 + `timeout 170 python -m pytest tests/test_stock_schema.py -q -p no:cacheprovider` — attendu : PASS.

---

### Task 2: Produits, signalement, demandes (commande) et routeur avec la matrice de rôles

**Files:**
- Create: `repositories/lab_stock_repo.py`, `controller/lab_stock_controller.py`, `api_backend/backend_app/routes/lab_stock/__init__.py`, `.../lab_stock_endpoints.py`, `.../lab_stock_schemas.py`
- Modify: `api_backend/backend_app/main.py` (inclure le routeur, comme `stock_endpoints`)
- Test: `tests/test_lab_stock_products.py`, `tests/test_lab_stock_requests.py`, `tests/test_lab_stock_roles.py`

**Interfaces:**
- Produces repo : `LabStockRepository(session)` avec `get_product(id)`, `lock_products(ids)` (ordre croissant), `apply_delta(...)` (voir Global Constraints), `open_request_for(product_id)`, `add(obj)`, `names(user_ids)` (noms complets en une requête, comme `StockRepository.user_names`), `LabStockConflictError`, `LabStockNotFoundError`.
- Produces controller : `LabStockController(repo, notification_repo, audit_repo, current_user)` (les trois dépôts obligatoires, `TypeError` sinon) ; `create_product(data)` / `update_product(id, data)` (nom, conditionnement, seuil, fournisseur, actif) / `list_products(include_inactive=False)` ; `signal(product_id, level)` → crée la demande `signalement` si aucune ouverte, sinon met à jour son niveau, puis notifie promoteur + ToxicoManager (`lab_stock_signal`) ; `list_requests(status=None)` ; `mark_ordered(request_id, expected_date)` (`a_commander`→`commande`, `ordered_by`, `ordered_at` ; date ≥ aujourd'hui ; 409 si pas `a_commander`) ; `update_expected_date(request_id, expected_date)` (seulement `commande`) ; `cancel_request(request_id, reason)` (motif obligatoire, 409 si pas ouverte). Dictionnaires de réponse avec noms (`created_by_name`, `requested_by_name`, `ordered_by_name`) et, pour une demande, `product_name`, `quantity`, `alert_threshold`.
- Produces routes (préfixe `/lab-stock`, corps stricts `extra=forbid`) : `GET /products`, `POST /products`, `PUT /products/{id}`, `POST /products/{id}/signal` (body `{level}`), `GET /requests?status=`, `POST /requests/{id}/order` (body `{expected_date}`), `PUT /requests/{id}/order` (body `{expected_date}`), `POST /requests/{id}/cancel` (body `{reason}`). Dépendance `get_lab_stock_controller` identique à `get_stock_controller`.

- [ ] **Step 1: Tests** : création/validation de produit (nom vide, seuil négatif, doublon actif → 422/409) ; produit créé avec `quantity = 0` quelle que soit l'entrée ; signalement crée puis met à jour une seule demande ouverte et envoie exactement une notification par destinataire (promoteur et ToxicoManager actifs, pas les inactifs) ; commande : transitions valides et 409 sinon, date passée → 422 ; annulation sans motif → 422 ; **matrice rôles × routes** (`tests/test_lab_stock_roles.py`, motif de `tests/test_stock_endpoints.py`, ≤ 4 connexions : utiliser des jetons forgés/dépendances surchargées comme ce fichier le fait) : chaque route répond 200/201 pour ses rôles autorisés et 403 pour les autres, dont promoteur et ToxicoManager sur `POST /products`, ToxicoManager sur la réception (route ajoutée en Task 3 : ajouter ce cas alors) et medecin/nurse/secretaire/Assistant sur tout ; `tests/test_stockcontroller_deny.py` reste vert.
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_lab_stock_products.py tests/test_lab_stock_requests.py tests/test_lab_stock_roles.py -q -p no:cacheprovider` — attendu : échec.
- [ ] **Step 3: Implémenter** dépôt, contrôleur, schémas, routeur et inclusion dans `main.py` ; audit (`AuditRepository.log_user_action`) sur chaque écriture ; une transaction par action avec rollback sur exception, comme `StockController`.
- [ ] **Step 4: Relancer** Step 2 + `timeout 170 python -m pytest tests/test_stockcontroller_deny.py tests/test_stock_endpoints.py -q -p no:cacheprovider` — attendu : PASS.

---

### Task 3: Réception (saisie + validation en une fois) et annulation

**Files:**
- Modify: `repositories/lab_stock_repo.py`, `controller/lab_stock_controller.py`, `.../lab_stock_endpoints.py`, `.../lab_stock_schemas.py`
- Test: `tests/test_lab_stock_receipts.py`

**Interfaces:**
- Consumes (Task 2) : `apply_delta`, `lock_products`, `open_request_for`, `LabStockController` et ses dictionnaires, notifications.
- Produces controller : `create_receipt(data)` avec `{invoice_number, supplier, delivery_date, lines:[{product_id, ordered_qty?, received_qty, unit_price, lot_number, expiry_date, note?}]}` — au moins une ligne, produits actifs et distincts, quantités > 0, prix ≥ 0, `line_total = received_qty × unit_price`, `total_amount` = somme (le serveur recalcule, ignore tout total fourni) ; refuse (409) un couple (fournisseur, n° de facture) déjà `valide` (comparaison insensible à la casse, espaces rognés) ; dans **une transaction** : verrouille les produits (ordre croissant), `apply_delta(+received_qty, 'reception', 'receipt', id)`, clôt la demande ouverte de chaque produit (`recu`, `closed_by_receipt_id`, `closed_at`), puis si `quantity <= alert_threshold` après réception crée une demande `seuil` ; notifie la/les personne(s) qui ont créé les signalements clos (`lab_stock_received`) ; audit. `get_receipt(id)`, `list_receipts(filters)` (dict avec lignes, `total_amount`, noms), `cancel_receipt(id, reason)` : admin seul (`PermissionError` sinon), motif obligatoire, 409 si déjà annulée ou si un produit n'a plus assez de stock pour retirer la quantité (rien n'est écrit) ; mouvements `annulation_reception` ; les demandes clôturées par cette réception repassent `a_commander` (si le produit a entre-temps une autre demande ouverte, laisser celle-là) ; si le stock ≤ seuil sans demande ouverte, créer une demande `seuil`.
- Produces routes : `POST /receipts` (RÉCEPTION), `GET /receipts?supplier=&from=&to=` et `GET /receipts/{id}` (LECTURE), `POST /receipts/{id}/cancel` (admin, body `{reason}`).

- [ ] **Step 1: Tests** : réception valide augmente exactement les stocks, écrit les mouvements, calcule les totaux côté serveur (total fourni ignoré) ; livraison partielle (stock encore ≤ seuil) → demande clôturée puis nouvelle demande `seuil` ; produit au-dessus du seuil → pas de nouvelle demande ; doublon (fournisseur, facture) → 409 et stock inchangé ; deux produits identiques dans les lignes → 422 ; ligne avec lot ou péremption vide → 422 ; produit inactif/inconnu → 422 ; double soumission parallèle simulée (deuxième appel après le premier dans la même session) → un seul ajout ; annulation : admin OK avec retrait et réouverture des demandes, non-admin → 403, stock insuffisant → 409 sans écriture, double annulation → 409, doublon de facture de nouveau accepté après annulation ; la matrice de rôles de Task 2 est étendue (manager et laborantin → 403 sur `POST /receipts`, promoteur/StockController/admin → 201).
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_lab_stock_receipts.py tests/test_lab_stock_roles.py -q -p no:cacheprovider` — attendu : échec.
- [ ] **Step 3: Implémenter** ci-dessus ; les montants et quantités sont validés avec les assistants `_int`/`_date` du contrôleur de stock (les réutiliser ou les extraire dans un module partagé sans changer leur comportement).
- [ ] **Step 4: Relancer** Step 2 + `timeout 170 python -m pytest tests/test_lab_stock_products.py tests/test_lab_stock_requests.py -q -p no:cacheprovider` — attendu : PASS.

---

### Task 4: Comptage, alertes (seuil, péremption, rappel) et historique

**Files:**
- Modify: `repositories/lab_stock_repo.py`, `controller/lab_stock_controller.py`, `.../lab_stock_endpoints.py`, `.../lab_stock_schemas.py`
- Test: `tests/test_lab_stock_counts_alerts.py`

**Interfaces:**
- Consumes : `apply_delta`, demandes, notifications, `utils/lab_stock_rules.py`.
- Produces controller : `submit_count(lines)` avec `[{product_id, previous_qty, counted_qty}]` (produits actifs, `counted_qty ≥ 0`, `previous_qty` = valeur chargée par l'écran) — par ligne, sous verrou : si `quantity != previous_qty` la ligne est **refusée** (collectée dans `conflicts`) sans rien écrire pour elle ; les autres lignes sont appliquées (`apply_delta(counted − quantity, 'comptage', 'count', id)` même si l'écart est 0, `last_counted_at = now`) ; ensuite pour chaque produit appliqué : si `counted ≤ alert_threshold` et aucune demande ouverte → demande `seuil` + notification `lab_stock_low` (promoteur + manager) ; si `counted > alert_threshold` et une demande ouverte d'origine `seuil` au statut `a_commander` → `annule` (motif « stock remonté ») ; une demande `signalement` ou `commande` n'est jamais touchée. Retourne `{count_id, applied:[…], conflicts:[{product_id, name, expected, actual}]}` (HTTP 200 ; 409 seulement si **toutes** les lignes sont en conflit) ; après le comptage, déclenche aussi les notifications de péremption (ci-dessous) et efface le rappel.
- `get_alerts()` → `{low:[produits ≤ seuil actif, seuil>0 ou stock 0 avec demande ouverte], expiring:[{product_id, product_name, lot_number, expiry_date, days_left, receipt_id}], count_status:{last_counted_at, days_since, reminder_due}}` ; `expiring` = lignes de réceptions `valide` dont `expiry_date − aujourd'hui ≤ EXPIRY_WARNING_DAYS` (déjà périmées incluses, `days_left` négatif) **et** dont le produit a `quantity > 0` et est actif. `reminder_due` vrai si jamais compté avec au moins un produit actif, ou `days_since ≥ COUNT_REMINDER_DAYS`. Les notifications `lab_stock_expiry` (promoteur + manager, une par lot, dédupliquées sur `receipt_line_id`) et `lab_stock_count_reminder` (laborantins actifs, dédupliquée par semaine ISO) sont émises par `get_alerts()` et `submit_count()` au plus une fois.
- `list_movements(product_id=None, limit=200)` avec noms. `GET /lab-stock/alerts` et `GET /lab-stock/movements` (LECTURE), `POST /lab-stock/counts` (COMPTAGE, body `{lines:[…]}`), `GET /lab-stock/counts/status` (LECTURE, retourne `count_status`).

- [ ] **Step 1: Tests** : comptage fixe le stock, trace l'écart (y compris 0) et met `last_counted_at` ; ligne dont `previous_qty` est périmé → conflit renvoyé, stock intact, autres lignes appliquées ; toutes en conflit → 409 ; passage sous le seuil → demande `seuil` + une notification par destinataire, pas de doublon au comptage suivant ; remontée au-dessus du seuil ferme seulement la demande `seuil` non commandée, jamais `signalement`/`commande` ; seuil 0 et stock 0 → pas de fausse alerte `low` sans demande ; lot expirant dans 60 jours et stock > 0 → dans `expiring`, stock 0 ou produit inactif → absent, lot déjà périmé → `days_left < 0` ; rappel dû à 7 jours révolus, jamais compté sans produit → pas de rappel ; notifications d'expiration non répétées ; réception puis comptage concurrent (comptage avec `previous_qty` d'avant la réception) → conflit, stock = valeur de la réception ; rôles : `laborantin`/`admin` seuls sur `POST /counts`.
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_lab_stock_counts_alerts.py tests/test_lab_stock_roles.py -q -p no:cacheprovider` — attendu : échec.
- [ ] **Step 3: Implémenter** ; calculs de dates avec `date.today()` injectable (paramètre `today` du dépôt) pour des tests déterministes.
- [ ] **Step 4: Relancer** Step 2 + `timeout 170 python -m pytest tests/test_lab_stock_receipts.py tests/test_lab_stock_requests.py -q -p no:cacheprovider` — attendu : PASS.

---

### Task 5: Dépenses et historique de prix

**Files:**
- Modify: `repositories/lab_stock_repo.py`, `controller/lab_stock_controller.py`, `.../lab_stock_endpoints.py`
- Test: `tests/test_lab_stock_expenses.py`

**Interfaces:**
- Produces : `expenses(date_from, date_to)` → `{total, by_month:[{month:'AAAA-MM', total}], by_supplier:[{supplier, total}]}` sur les réceptions `valide` (les annulées exclues) classées par `delivery_date` ; `price_history(product_id)` → `[{delivery_date, receipt_id, supplier, unit_price, received_qty}]` triés par date. Routes `GET /lab-stock/expenses?from=&to=` et `GET /lab-stock/products/{id}/price-history` (DÉPENSES : promoteur, ToxicoManager, admin ; les autres → 403). Agrégation en SQL (`GROUP BY`), pas en Python ; période par défaut = 12 derniers mois ; `from > to` → 422.

- [ ] **Step 1: Tests** : totaux par mois et par fournisseur corrects sur plusieurs réceptions, réception annulée exclue, période hors plage → zéros, fournisseurs de casse différente regroupés, historique de prix trié, produit inconnu → 404, rôles (laborantin et StockController → 403).
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_lab_stock_expenses.py -q -p no:cacheprovider` — attendu : échec.
- [ ] **Step 3: Implémenter**.
- [ ] **Step 4: Relancer** Step 2 + `timeout 170 python -m pytest tests/test_lab_stock_receipts.py tests/test_lab_stock_roles.py -q -p no:cacheprovider` — attendu : PASS.

---

### Task 6: Frontend — passerelle, routes, menu, produits, liste « à commander »

**Files:**
- Create: `ah2-admin-web/src/services/LabStockGateway.js`, `ah2-admin-web/src/views/modules/labstock/LabStockProducts.vue`, `.../LabStockRequests.vue`, `ah2-admin-web/src/utils/labStockLabels.js`
- Modify: `ah2-admin-web/src/router/index.js` (routes `lab-stock-*` avec `meta.roles`), `ah2-admin-web/src/components/layout/MainLayout.vue` (entrées de menu par rôle, `NotificationBell` visible pour laborantin et ToxicoManager en plus des rôles actuels), `ah2-admin-web/src/views/LoginView.vue` (redirection d'accueil si besoin), `ah2-admin-web/src/components/notifications/NotificationBell.vue` (libellés des 5 types), `ah2-admin-web/src/i18n.js` (FR+EN)
- Test: `ah2-admin-web/tests/labStockLabels.test.mjs`

**Interfaces:**
- Consumes : routes `/lab-stock/*` de Tasks 2–5 (`products`, `requests`, `alerts`, `counts/status`, `movements`).
- Produces : `LabStockGateway` (une fonction par route, n'envoie que les champs du schéma, motif de `StockOpsGateway`) ; `labStockLabels.js` exporte `requestOriginLabel(origin)`, `requestStatusLabel(status)`, `levelLabel(level)` et `labNotificationLabel(type, payload)` (clé i18n + paramètres, repli sûr pour valeur inconnue) ; menu : `laborantin` → Produits, Comptage, À commander, Alertes ; `StockController` → Réceptions, Produits, À commander, Historique (les routes existantes de `/stock` du contrôleur restent) ; `promoteur` et `ToxicoManager` → À commander, Alertes, Historique, Dépenses (+ Réceptions pour promoteur) ; `admin` → tout. `LabStockProducts.vue` : liste avec recherche, stock coloré (≤ seuil), bouton « Signaler » (laborantin), formulaire de création/modification (rôles d'écriture seulement). `LabStockRequests.vue` : tableau (cartes sur mobile) produit / stock / seuil / origine / statut, « Marquer commandé » (date attendue), modifier la date, annuler avec motif, filtrés par statut.

- [ ] **Step 1: Test node** de `labStockLabels.js` (valeurs connues → clés ; inconnue → repli sans exception) ; lancer `node --test ah2-admin-web/tests/labStockLabels.test.mjs` — attendu : échec.
- [ ] **Step 2: Implémenter** passerelle, libellés, routes avec gardes de rôles (symétriques à `role_required` : `ROLES` existants + ajout de `LABORANTIN`, `PROMOTEUR` si absents), menu, vues, i18n FR+EN, libellés de notifications.
- [ ] **Step 3: Vérifier** `node --test ah2-admin-web/tests/*.test.mjs` et `cd ah2-admin-web && npx vite build` — attendu : tous les tests passent, build OK. Vérification visuelle à 360 px laissée à l'utilisateur.

---

### Task 7: Frontend — réception et comptage (mobile d'abord)

**Files:**
- Create: `ah2-admin-web/src/views/modules/labstock/LabStockReceipts.vue`, `.../LabStockReceiptForm.vue`, `.../LabStockCount.vue`, `ah2-admin-web/src/utils/labReceiptLines.js`, `ah2-admin-web/src/utils/labCount.js`
- Modify: `ah2-admin-web/src/router/index.js`, `ah2-admin-web/src/i18n.js`
- Test: `ah2-admin-web/tests/labReceiptLines.test.mjs`, `ah2-admin-web/tests/labCount.test.mjs`

**Interfaces:**
- Consumes : `LabStockGateway` (Task 6) ; `POST /receipts`, `GET /receipts`, `GET /receipts/{id}`, `POST /receipts/{id}/cancel`, `POST /counts`, `GET /products`.
- Produces : `labReceiptLines.js` — `lineTotal(qty, unitPrice)`, `receiptTotal(lines)`, `validateReceipt(form)` → liste d'erreurs i18n (facture, fournisseur, au moins une ligne, produits distincts, quantité > 0, lot et péremption renseignés), `buildReceiptPayload(form)` (sans total envoyé). `labCount.js` — `buildCountPayload(products, entered)` (seulement les produits dont la saisie est renseignée, `previous_qty` = valeur chargée) et `describeConflicts(resp)`. Écran de réception (cartes sur téléphone, tableau de lignes sur PC, deux colonnes sur tablette) : en-tête (facture, fournisseur avec suggestions des fournisseurs connus, date), « + Ajouter un produit » ouvrant une recherche dans la liste, option « Créer un produit » **visible seulement pour les rôles d'écriture produit**, une carte par ligne avec case de pointage, qté commandée (optionnelle) / reçue, lot, péremption, prix unitaire, total de ligne et total facture en pied, bouton « Valider la réception » désactivé tant que `validateReceipt` signale des erreurs, double clic impossible (bouton verrouillé pendant l'appel), erreur 409 de doublon affichée clairement. Liste des réceptions avec détail, annulation (admin seulement, motif). Écran de comptage : une carte par produit (nom, conditionnement, dernier stock), champ numérique, bouton envoyer ; après l'envoi, les conflits sont listés avec leur nouveau stock et la saisie des produits concernés est conservée pour recomptage ; bandeau de rappel si `reminder_due`.

- [ ] **Step 1: Tests node** : totaux (arrondis entiers), erreurs de validation (une par règle, produits en double, lot vide), payload sans total, `buildCountPayload` n'inclut pas les champs vides, `describeConflicts` — lancer `node --test ah2-admin-web/tests/labReceiptLines.test.mjs ah2-admin-web/tests/labCount.test.mjs` — attendu : échec.
- [ ] **Step 2: Implémenter** utilitaires, vues, routes et i18n FR+EN.
- [ ] **Step 3: Vérifier** `node --test ah2-admin-web/tests/*.test.mjs` et `cd ah2-admin-web && npx vite build` — attendu : PASS. Vérifier aussi dans le code que chaque écran de cette tâche définit les trois niveaux (défaut mobile, `md:`, `lg:`) et que les rapports d'implémentation le disent ; le rendu réel à 360 px, 768 px et 1280 px est laissé à l'utilisateur.

---

### Task 8: Frontend — alertes, historique, dépenses, et recette de bout en bout

**Files:**
- Create: `ah2-admin-web/src/views/modules/labstock/LabStockAlerts.vue`, `.../LabStockMovements.vue`, `.../LabStockExpenses.vue`
- Modify: `ah2-admin-web/src/router/index.js`, `ah2-admin-web/src/i18n.js`, `docs/superpowers/SUIVI-AVANCEMENT.md`
- Test: `ah2-admin-web/tests/labStockExpenses.test.mjs`, `tests/test_lab_stock_end_to_end.py`

**Interfaces:**
- Consumes : `GET /alerts`, `GET /movements`, `GET /expenses`, `GET /products/{id}/price-history`.
- Produces : écran Alertes (stocks bas avec bouton vers la liste « à commander », lots proches de la péremption avec jours restants, rappel de comptage) ; écran Historique des mouvements avec filtre produit ; écran Dépenses (total, par mois en barres simples CSS, par fournisseur, historique du prix d'un produit choisi). `tests/test_lab_stock_end_to_end.py` : scénario complet via le contrôleur et ≤ 4 connexions : création de produit (laborantin) → signalement → liste « à commander » → commandé avec date → réception par le contrôleur → demande close, stock augmenté → comptage sous le seuil → nouvelle demande `seuil` → dépenses et historique de prix cohérents ; plus la vérification que `pharmacy`, `caisse` et `stock_movements` n'ont aucune ligne ajoutée par ce parcours. Mise à jour du suivi : section « Stock labo » (livré, non commité, liste « à tester par vous » : réception sur téléphone à 360 px, comptage, signalement, commande, alertes, dépenses, et accès par rôle).

- [ ] **Step 1: Tests** : node pour les helpers d'agrégation d'affichage des dépenses (barres proportionnelles, mois vides) ; pytest du scénario de bout en bout — lancer `timeout 170 python -m pytest tests/test_lab_stock_end_to_end.py -q -p no:cacheprovider` et `node --test ah2-admin-web/tests/labStockExpenses.test.mjs` — attendu : échec.
- [ ] **Step 2: Implémenter** les trois écrans, routes, i18n FR+EN et le suivi.
- [ ] **Step 3: Vérifier** `timeout 170 python -m pytest tests/test_lab_stock_end_to_end.py tests/test_lab_stock_schema.py tests/test_lab_stock_products.py tests/test_lab_stock_requests.py tests/test_lab_stock_receipts.py tests/test_lab_stock_counts_alerts.py tests/test_lab_stock_expenses.py tests/test_lab_stock_roles.py tests/test_stockcontroller_deny.py -q -p no:cacheprovider` (en deux commandes si la durée dépasse la limite), `node --test ah2-admin-web/tests/*.test.mjs`, `cd ah2-admin-web && npx vite build` — attendu : PASS.
