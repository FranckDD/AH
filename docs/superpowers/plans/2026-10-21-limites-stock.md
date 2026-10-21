# Limites du chantier stock — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lever trois limites connues du chantier stock : (A) les libellés de lignes de vente qui touchent au stock sont décidés par trois listes incohérentes (vente, modification, annulation) ; (B) une correction d'ajustement écrase les ventes faites entre la demande et l'approbation ; (C) les écrans affichent les auteurs en `#id`.

**Architecture:** A : une seule fonction `touches_stock(item_type)` (réutilise la normalisation de libellés de la réduction personnel) utilisée par la vente, la modification et l'annulation ; B : colonne `stock_at_request` + application de l'écart (compté − stock du système à la demande) au stock actuel ; C : noms complets ajoutés aux réponses de l'API (une requête groupée par liste) et affichés par les écrans.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (SQL brut) + pytest ; Vue 3 / vue-i18n.

**Spec / contexte:** `docs/superpowers/specs/2026-10-20-fabrication-reception-avaries-design.md` (section « Révisions après exécution ») et `docs/superpowers/SUIVI-AVANCEMENT.md` (limites connues du chantier stock). Décisions utilisateur du 2026-10-21 : faire les trois correctifs, dans l'ordre A, B, C.

## Global Constraints

- Toute modification de `pharmacy.quantity` reste **atomique et sous verrou** (`StockRepository.apply_stock_delta`, ou `FOR UPDATE` + `populate_existing` dans `caisse_repo`/`pharmacy_repo`, produits verrouillés par `medication_id` croissant) ; le stock ne descend jamais sous 0 ; le comportement des mouvements `VENTE`, `ANNULATION_VENTE`, `update`, `renew` ne change pas de type ni de signe.
- Libellés réels en base à reconnaître (comptages au 2026-10-21) : « Vente Médicament » (23), « Médicament » (11), « Sale Medication » (3), « Carnet » (5), « Vente Carnet » (4) → touchent au stock ; « Examens », « Examen », « Consultation Spirituel », « Consultation Médical », « Désintox », « Service » → ne touchent PAS au stock ; plus les variantes `medication`, `booklet`, accents/casse.
- Migrations Alembic : SQL brut idempotent, motif de `alembic/versions/019_stock_reception_avaries.py` (dernière révision : `019_stock_reception_avaries`) ; reporter le DDL dans `ci/schema_only.sql` (**fins de ligne CRLF**, pas de réécriture complète du fichier).
- Toutes les chaînes UI en FR **et** EN (`ah2-admin-web/src/i18n.js`).
- Tests : base de dev partagée, fixtures transactionnelles ; **toute commande pytest doit être encadrée par `timeout 170`** ; **la connexion est limitée à 5 par minute** (jamais plus de 4 connexions dans un même test) ; Redis (conteneur `ah2_redis`, port 6379) doit tourner ; disque presque plein : aucune copie du dépôt, pas de suite complète dans les sous-agents.
- Ne pas commiter sans accord de l'utilisateur : sauter les étapes « Commit ».

## Review Focus

- Une vente éditée dont une ligne `Vente Médicament` change de quantité : le stock suit (aujourd'hui la modification ignore ce libellé). Test dans Task 1.
- Annulation d'une vente contenant « Sale Medication » et « Vente Carnet » : stock remis. Test dans Task 1.
- Demande de correction créée alors que le stock du système vaut 13, comptage 10, 3 ventes avant l'approbation : le stock final vaut 7, pas 10. Test dans Task 2.
- Demande de correction antérieure à la migration (`stock_at_request` NULL) : ancien comportement absolu conservé. Test dans Task 2.
- Utilisateur supprimé ou sans nom : l'écran retombe sur `#id`, sans erreur. Test dans Task 3.

---

### Task 1: Une seule règle « cette ligne touche au stock »

**Files:**
- Create: `utils/item_types.py`
- Modify: `repositories/caisse_repo.py` (création de vente, modification de vente, annulation de vente : remplacer les trois listes de libellés)
- Test: `tests/test_stock_item_types.py`

**Interfaces:**
- Consumes: `utils.staff_discount.normalize_item_category(item_type: str) -> str` (catégories `medicament`, `examen`, `consultation`, `carnet`, `autre_soin`).
- Produces: `touches_stock(item_type: str | None) -> bool` — vrai ssi la catégorie normalisée est `medicament` ou `carnet` ; `None`/vide → faux ; jamais d'exception.

- [ ] **Step 1: Écrire les tests** (`tests/test_stock_item_types.py`) : (a) fonction pure : les 7 libellés qui touchent au stock (« Vente Médicament », « Médicament », « Sale Medication », « medication », « Vente Carnet », « Carnet », « booklet ») → vrai ; « Examens », « Examen », « Consultation Spirituel », « Consultation Médical », « Désintox », « Service », `None`, `""` → faux ; (b) via le contrôleur/dépôt de caisse (motif de `tests/test_caisse.py` : création par le contrôleur, un produit de test avec stock connu) pour chacun des libellés « Vente Médicament », « Sale Medication » et « Vente Carnet » : la **création** retire la quantité, la **modification** (quantité de la ligne 2 → 5) ajuste le stock du bon écart, l'**annulation** remet tout le stock et écrit un mouvement `ANNULATION_VENTE` ; (c) une ligne « Examen » ne change jamais le stock dans ces trois opérations.
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_stock_item_types.py -q -p no:cacheprovider` — attendu : échec (module absent / libellés non reconnus).
- [ ] **Step 3: Implémenter** `utils/item_types.py::touches_stock` et brancher les trois endroits de `caisse_repo.py` (y compris le pré-verrouillage trié des produits de la modification, qui doit utiliser la même fonction pour décider quelles lignes verrouiller) sans toucher à l'arithmétique ni aux types de mouvements.
- [ ] **Step 4: Relancer** Step 1 + `timeout 170 python -m pytest tests/test_caisse.py tests/test_stock_write_locks.py tests/test_caisse_staff_discount.py -q -p no:cacheprovider` — attendu : PASS (hors échec préexistant connu `test_create_transaction_amount_mismatch_returns_400`).

---

### Task 2: La correction applique l'écart, pas une valeur absolue

**Files:**
- Create: `alembic/versions/020_adjustment_stock_at_request.py`
- Modify: `models/stock_reception.py` (`StockAdjustmentRequest.stock_at_request`), `ci/schema_only.sql` (CRLF), `controller/stock_controller.py` (création et approbation d'une demande), `repositories/stock_repo.py` si nécessaire, `ah2-admin-web/src/views/modules/stock/AdjustmentRequestsAdmin.vue`, `ah2-admin-web/src/i18n.js`
- Test: `tests/test_stock_adjustment_requests.py` (conversion + ajouts)

**Interfaces:**
- Consumes: `StockController.create_adjustment_request`, `approve_adjustment`, `StockRepository.apply_stock_delta(product_id, delta, movement_type, note, user, allow_negative=False)` et `set_stock_quantity` existants.
- Produces: colonne `stock_adjustment_requests.stock_at_request integer NULL` ; à la création d'une demande, `stock_at_request` = quantité du produit lue à cet instant (lecture fraîche) ; à l'approbation d'une `correction` : si `stock_at_request` n'est pas NULL, `delta = quantity − stock_at_request` appliqué au stock **actuel** sous verrou (`StockConflictError` si le résultat serait < 0), mouvement `update` avec `change_qty = delta` (0 autorisé et tracé), `stock_before`/`stock_after` renseignés comme avant ; sinon (NULL, demandes antérieures) l'ancien comportement absolu. `_adjustment_dict` expose `stock_at_request`.

- [ ] **Step 1: Tests** : (a) scénario du Review Focus (système 13, comptage 10 → écart −3, 3 ventes validées avant l'approbation → stock final 7, `stock_before` = 10, `stock_after` = 7, mouvement `update` de −3) ; (b) demande créée sans aucune vente intermédiaire : stock final = valeur comptée ; (c) écart positif (comptage au-dessus du système) ; (d) résultat négatif (écart plus grand que le stock actuel) → `StockConflictError`, rien d'écrit ; (e) ligne antérieure avec `stock_at_request` NULL (insérer la ligne directement) → comportement absolu inchangé ; (f) `reapprovisionnement` inchangé ; (g) le dictionnaire de la demande expose `stock_at_request` ; (h) **convertir** les tests existants qui supposaient l'approbation absolue après une vente intermédiaire, en listant dans le rapport chaque test converti et pourquoi.
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_stock_adjustment_requests.py -q -p no:cacheprovider` — attendu : échec.
- [ ] **Step 3: Migration 020** (`revision = '020_adjustment_stock_at_request'`, `down_revision = '019_stock_reception_avaries'`, `ALTER TABLE … ADD COLUMN IF NOT EXISTS stock_at_request integer`), modèle, DDL CI ; appliquer à la base de dev avec `alembic upgrade head` après avoir vérifié `alembic current` = `019_stock_reception_avaries` (autorisation explicite du contrôleur) et vérifier la colonne par SQL.
- [ ] **Step 4: Implémenter** le calcul à la création et à l'approbation (un seul verrou produit ; pas de lecture puis écriture hors verrou) ; frontend : `AdjustmentRequestsAdmin.vue` affiche pour une correction « Quantité comptée : N · Stock du système à la demande : M · Stock actuel : K », libellés FR/EN ; relancer les tests de Step 1 + `timeout 170 python -m pytest tests/test_stock_incidents.py tests/test_stock_receipts.py tests/test_stock_schema.py -q -p no:cacheprovider`, `node --test ah2-admin-web/tests/*.test.mjs`, `cd ah2-admin-web && npx vite build`.

---

### Task 3: Noms complets à la place de `#id`

**Files:**
- Modify: `controller/stock_controller.py` (dictionnaires `_lot_dict`, `_receipt_dict`, `_incident_dict`, `_adjustment_dict`), `repositories/stock_repo.py` (recherche groupée des noms), `ah2-admin-web/src/views/modules/stock/ProductionLots.vue`, `StockReceipts.vue`, `StockIncidents.vue`, `StockControlQueue.vue`, `AdjustmentRequestsAdmin.vue`, `ah2-admin-web/src/components/stock/AdjustmentRequestModal.vue` ou `StockList.vue` si la section « Mes demandes » affiche un auteur
- Test: `tests/test_stock_actor_names.py`, `ah2-admin-web/tests/actorName.test.mjs`

**Interfaces:**
- Consumes: colonnes `created_by`, `controlled_by`, `requested_by`, `decided_by` (FK `users.user_id`), `users.full_name`.
- Produces: champs ajoutés aux dictionnaires : lots `created_by_name` ; réceptions et avaries `created_by_name`, `controlled_by_name` ; demandes `requested_by_name`, `decided_by_name` ; valeur = `full_name` de l'utilisateur, `None` si l'identifiant est NULL ou l'utilisateur introuvable ; résolution **en une requête groupée par liste** (pas de N+1) via une méthode du dépôt ; frontend : `ah2-admin-web/src/utils/actorName.js` exporte `actorLabel(name, id) -> string` (nom si présent, sinon `#id`, sinon `—`).

- [ ] **Step 1: Tests backend** : chaque dictionnaire expose le nom correct pour l'auteur et le contrôleur ; identifiant NULL → `None` ; utilisateur absent → `None` ; une liste de 5 éléments d'auteurs différents exécute au plus une requête de noms (compter les requêtes SQL avec un écouteur `before_cursor_execute`) ; test node de `actorLabel` (nom, `#id`, `—`) — RED d'abord.
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_stock_actor_names.py -q -p no:cacheprovider` et `node --test ah2-admin-web/tests/actorName.test.mjs` — attendu : échec.
- [ ] **Step 3: Implémenter** la résolution groupée et l'ajouter à tous les chemins qui produisent ces dictionnaires (création, liste, lecture, décision) ; remplacer dans les écrans chaque affichage `#{{ … }}` d'un utilisateur par `actorLabel(…)` ; les mouvements de stock affichent déjà `created_by` (nom d'utilisateur) : ne pas y toucher.
- [ ] **Step 4: Relancer** Step 2 + `timeout 170 python -m pytest tests/test_stock_receipts.py tests/test_stock_incidents.py tests/test_stock_adjustment_requests.py -q -p no:cacheprovider`, `node --test ah2-admin-web/tests/*.test.mjs`, `cd ah2-admin-web && npx vite build`.
