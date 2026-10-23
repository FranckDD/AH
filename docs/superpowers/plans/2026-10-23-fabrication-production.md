# Fabrication : de l'achat des intrants à l'expédition au centre : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre au responsable de production d'enregistrer les achats d'intrants et les lots de fabrication (consommations, résultats, bilan, coût de revient) jusqu'à l'expédition au centre, où le circuit existant de réception et de contrôle prend le relais sans changement.

**Architecture:** Un module nouveau et isolé, sur le modèle du stock du labo : migration, modèles `fab_*`, règles pures testables (`utils/fabrication_rules.py`), dépôt qui ne commit jamais, contrôleur qui possède la transaction, routeur `/fabrication` à gardes de rôle explicites. L'expédition crée un `production_lots` à l'état `produit` et le relie au lot de Fabrication ; rien d'autre du circuit existant n'est touché. Côté navigateur : passerelle, quatre écrans dans le cadre `MainLayout`, bibliothèque `ui/`, FR et EN.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic (SQL brut idempotent), pytest ; Vue 3 `<script setup>`, Tailwind 4, vue-i18n 11, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-23-fabrication-production-design.md` (lire aussi `2026-10-20-fabrication-reception-avaries-design.md` pour le circuit aval).

## Global Constraints

- **Aucun écran, route ni règle existants ne change.** Seules modifications de l'existant : déclarer le rôle (`role_map`, routeur, menu, fenêtre des utilisateurs, palette), ajouter le rôle aux gardes négatives `deny_roles("StockController")`, enregistrer le routeur dans `main.py`, ajouter le DDL à `ci/schema_only.sql` et le rôle à `ci/seed_application_roles.sql`.
- **Rôle** : `ProductionManager` (casse exacte du `role_name`), canonique `productionmanager`. Lecture : `("ProductionManager", "promoteur", "admin")`. **Écriture : `ProductionManager` seul** ; l'admin et le promoteur sont en lecture seule, sauf `PUT /fabrication/settings` et le seuil d'un intrant, réservés à `admin`. Tout autre rôle : 403 sur toutes les routes.
- **Coûts** : jamais de champ de coût dans une route existante. Les coûts vivent seulement dans `/fabrication/*` (gardé comme ci-dessus). Pas de colonne de coût sur `pharmacy`.
- **Aucun nom de produit ou d'intrant dans le code ni dans les tests** autre que des valeurs générées aléatoirement dans le test.
- **Nombres** : quantités d'intrants `Numeric(12,3)`, bouteilles `Integer`, coûts `Numeric(12,2)` ; calculs en `Decimal`, jamais en `float`.
- **Statuts d'un lot** : `brouillon`, `en_production`, `termine`, `expedie`, `annule`. Tolérance par défaut `2.00` %, délai « trop long » `7` jours, numéro de lot `FAB-AAAA-NNNN`.
- **Texte affiché** : FR et EN sous `fabrication.*`, aucun tiret long, point médian, flèche ni emoji ; jetons de couleur seulement (pas de couleur Tailwind brute) ; texte ≥ 13 px, 14-16 px de base ; cibles ≥ 44 px ; états dits par un mot, jamais par la couleur seule.
- **Pas de commit sans demande** : chaque tâche s'arrête sur un point de contrôle de l'utilisateur. Les étapes « Commit » ci-dessous ne s'exécutent que si l'utilisateur l'a demandé.
- **Migrations** : appliquer la nouvelle migration à la base de développement sans demander, mais vérifier l'état avant (`alembic current`).

## Review Focus

- **Double consommation** : deux lots qui consomment le même achat ne doivent jamais dépasser son restant (verrou `FOR UPDATE`). Test dans la tâche 4.
- **Lot sans contenant ou avec deux contenants** : le passage en production est refusé (422). Tâche 4.
- **Décimaux** : `0.1 + 0.2` litres consommés doit donner exactement `0.300` et un restant exact. Tâche 2.
- **Lot figé** : après expédition, plus d'édition, de retour en arrière ni d'annulation ; l'annulation d'un lot en production rend les quantités aux achats. Tâches 4 et 5.
- **Hors tolérance** : expédier sans justification, ou avec une justification faite d'espaces, est refusé (422) ; la tolérance appliquée est figée dans le lot. Tâche 5.
- **Fuite de coûts ou de droits** : aucun autre rôle n'obtient autre chose que 403 ; aucune route existante ne renvoie un coût. Tâche 7.

---

## File Structure

| Fichier | Rôle |
|---|---|
| `alembic/versions/023_fabrication.py` | tables `fab_*`, rôle `ProductionManager`, ligne de paramètres |
| `models/fabrication.py` | `FabIntrant`, `FabIntrantPurchase`, `FabBatch`, `FabConsumption`, `FabSettings` |
| `utils/fabrication_rules.py` | règles pures : bilan, coût, numérotation, transitions |
| `repositories/fabrication_repo.py` | accès données, ne commit jamais, `lock_purchase()` en `FOR UPDATE` |
| `controller/fabrication_controller.py` | cas d'usage, transaction, audit |
| `api_backend/backend_app/routes/fabrication/` | `fabrication_endpoints.py`, `fabrication_schemas.py`, `__init__.py` |
| `ah2-admin-web/src/services/FabricationGateway.js` | appels `/fabrication/*` |
| `ah2-admin-web/src/views/modules/fabrication/` | `FabIntrants.vue`, `FabLots.vue`, `FabLotDetail.vue`, `FabSuivi.vue` |

---

### Task 1: Rôle, tables et branchement du rôle

**Files:**
- Create: `alembic/versions/023_fabrication.py`, `models/fabrication.py`, `tests/test_fabrication_schema.py`
- Modify: `models/__init__.py` (exporter les modèles), `api_backend/backend_app/security/role_map.py`, les cinq `deny_roles("StockController")` (trouver par `git grep 'deny_roles("StockController")'`), `ci/schema_only.sql`, `ci/seed_application_roles.sql`

**Interfaces:**
- Produces : modèles `FabIntrant(id, name, unit, is_container, alert_threshold, is_active)`, `FabIntrantPurchase(id, intrant_id, supplier, delivery_ref, purchase_date, quantity, unit_cost, remaining_qty, status, cancel_reason)`, `FabBatch(id, batch_number, product_id, status, production_date, producer_name, qty_good, qty_damaged, qty_rejected, liquid_lost, expected_qty, found_qty, missing_qty, missing_pct, tolerance_applied, out_of_tolerance, justification, total_cost, unit_cost, delivery_date, expiry_date, production_lot_id, cancel_reason, created_by, created_at, started_at, finished_at, expedited_at, expedited_by)`, `FabConsumption(id, batch_id, purchase_id, quantity, unit_cost_snapshot, restored_at)`, `FabSettings(id=1, tolerance_pct, stale_days, updated_by, updated_at)` ; constante `PRODUCTIONMANAGER = "productionmanager"` dans `role_map`.

- [ ] **Step 1: Write the failing tests** in `tests/test_fabrication_schema.py` : `test_role_production_manager_exists_and_normalizes` (ligne dans `application_roles`, `normalize_role_name("ProductionManager") == "productionmanager"`), `test_tables_exist_with_checks` (insère une quantité `0` d'achat, une consommation négative, un statut de lot inconnu : chacun lève `IntegrityError`), `test_settings_row_defaults` (`FabSettings` id 1 : tolérance `2.00`, délai `7`), `test_production_manager_denied_where_stockcontroller_is` (reprendre le motif de `tests/test_stockcontroller_deny.py` : chaque route gardée par `deny_roles("StockController")` répond 403 à `ProductionManager`).
- [ ] **Step 2: Run and verify they fail** : `python -m pytest tests/test_fabrication_schema.py -v` : échecs (tables et rôle absents).
- [ ] **Step 3: Write migration 023** (`revision='023_fabrication'`, `down_revision='022_toxico_stays'`), SQL brut idempotent comme `019` : tables, contraintes `CHECK` (quantités `> 0`, `remaining_qty >= 0`, statuts, `tolerance_pct >= 0`), index sur `status`, insertion du rôle et de la ligne `fab_settings(1, 2.00, 7)` ; `downgrade` symétrique. Reporter le DDL dans `ci/schema_only.sql` et le rôle dans `ci/seed_application_roles.sql` (même forme que la ligne `StockController`). Écrire `models/fabrication.py` (mêmes noms de colonnes que les Interfaces). Ajouter `ProductionManager` à `role_map` (constante, ensemble canonique, alias `production_manager`, `responsable_production`). Ajouter `"ProductionManager"` à chaque garde négative.
- [ ] **Step 4: Apply and verify** : `python -m alembic current` puis `python -m alembic upgrade head` sur la base de développement, puis `python -m pytest tests/test_fabrication_schema.py tests/test_stockcontroller_deny.py -v` : tous verts.

---

### Task 2: Règles pures

**Files:**
- Create: `utils/fabrication_rules.py`, `tests/test_fabrication_rules.py`

**Interfaces:**
- Produces :
  - `compute_bilan(expected: int, good: int, damaged: int, rejected: int, tolerance_pct: Decimal) -> dict` renvoie `{"expected", "found", "missing", "missing_pct": Decimal(2 décimales), "out_of_tolerance": bool}` ; lève `ValueError` si `found > expected` ou `expected <= 0`.
  - `compute_cost(consumptions: list[tuple[Decimal, Decimal]], good: int) -> tuple[Decimal, Decimal | None]` : `(total, par bouteille bonne)` ; second élément `None` si `good == 0`.
  - `next_batch_number(last: str | None, year: int) -> str` : `FAB-2026-0001` si `last` est `None` ou d'une autre année, sinon incrémente.
  - `TRANSITIONS: dict[str, set[str]]` : `brouillon→{en_production, annule}`, `en_production→{termine, annule}`, `termine→{en_production, expedie, annule}`, `expedie→{}`, `annule→{}`.

- [ ] **Step 1: Write the failing tests** : bilan 120 attendus, 112+3+2 → `missing == 3`, `missing_pct == Decimal("2.50")`, tolérance `2` → `out_of_tolerance is True` ; même cas tolérance `2.5` → `False` (strictement supérieur) ; 0 manquant → `False` ; `found > expected` lève `ValueError` ; `compute_cost([(Decimal("0.1"), Decimal("10")), (Decimal("0.2"), Decimal("10"))], 3)` → total `Decimal("3.00")`, unitaire `Decimal("1.00")` ; `good == 0` → unitaire `None` ; numérotation (aucun, même année, nouvelle année, mauvais format → `ValueError`) ; chaque transition interdite absente de `TRANSITIONS`.
- [ ] **Step 2: Run and verify they fail** : `python -m pytest tests/test_fabrication_rules.py -v` : `ImportError`.
- [ ] **Step 3: Implement** les trois fonctions et `TRANSITIONS` dans `utils/fabrication_rules.py`, en `Decimal` avec `quantize(Decimal("0.01"))`.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 3: Intrants et achats

**Files:**
- Create: `repositories/fabrication_repo.py`, `controller/fabrication_controller.py`, `api_backend/backend_app/routes/fabrication/__init__.py`, `fabrication_endpoints.py`, `fabrication_schemas.py`, `tests/test_fabrication_intrants.py`
- Modify: `api_backend/backend_app/main.py` (enregistrer `fabrication_endpoints.router`)

**Interfaces:**
- Consumes : modèles et règles des tâches 1 et 2.
- Produces : `FabricationRepository(session)` (méthodes `add`, `get_intrant`, `list_intrants_with_stock`, `get_purchase`, `lock_purchase(id)`, `purchases_for(intrant_id)`) ; `FabricationController(repo, audit_repo, current_user)` avec `create_intrant`, `update_intrant`, `set_threshold(intrant_id, value)` (admin), `list_intrants() -> list[dict]` (chaque élément porte `stock`, somme des `remaining_qty` des achats `actif`, et `below_threshold`), `create_purchase`, `update_purchase`, `cancel_purchase(id, reason)` ; erreurs `FabricationNotFoundError(ValueError)`, `FabricationConflictError` ; constantes de rôles `READERS`, `WRITERS`, `SETTINGS_WRITERS` dans `fabrication_endpoints.py` ; routes `GET/POST /fabrication/intrants`, `PUT /fabrication/intrants/{id}`, `PUT /fabrication/intrants/{id}/threshold`, `GET/POST /fabrication/purchases`, `PUT /fabrication/purchases/{id}`, `POST /fabrication/purchases/{id}/cancel`.

- [ ] **Step 1: Write the failing tests** : créer un intrant puis un achat de `Decimal("60.000")` à `1550.00` → `stock == 60` ; `PUT` d'un achat non consommé réussit, d'un achat dont une consommation existe → 409 ; `cancel` exige un motif non vide (422) et refuse un achat consommé (409) ; quantité `0` ou coût négatif → 422 ; `threshold` : 200 pour `admin`, 403 pour `ProductionManager` ; seuil dépassé → `below_threshold is True` ; chaque création, annulation et correction écrit une ligne d'audit.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** dépôt, contrôleur et routes. Gardes : lecture `READERS`, écriture `WRITERS`, seuil `SETTINGS_WRITERS = ("admin",)`. Le contrôleur commit, le dépôt jamais. Mapper les erreurs comme `lab_stock_endpoints._errors()` (404, 409, 403, 422).
- [ ] **Step 3b:** enregistrer le routeur dans `main.py` avec un commentaire `# prefixe /fabrication`.
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_fabrication_intrants.py -v`.

---

### Task 4: Lots, consommations et transitions jusqu'à « terminé »

**Files:**
- Modify: `repositories/fabrication_repo.py`, `controller/fabrication_controller.py`, `fabrication_endpoints.py`, `fabrication_schemas.py`
- Create: `tests/test_fabrication_batches.py`

**Interfaces:**
- Consumes : tâche 3 (achats, `lock_purchase`), tâche 2 (`TRANSITIONS`, `next_batch_number`).
- Produces : `create_batch(product_id, production_date) -> dict` (numéro généré, statut `brouillon`) ; `replace_consumptions(batch_id, items: list[{"purchase_id", "quantity"}])` (brouillon seulement) ; `start_batch(batch_id)` ; `finish_batch(batch_id, qty_good, qty_damaged, qty_rejected, liquid_lost)` ; `reopen_batch(batch_id)` ; `cancel_batch(batch_id, reason)` ; `get_batch(batch_id) -> dict` avec `consumptions` (provenance : intrant, achat, fournisseur, date, coût), `cost_so_far`. Routes `GET/POST /fabrication/batches`, `GET/PUT /fabrication/batches/{id}`, `POST .../start`, `.../finish`, `.../reopen`, `.../cancel`.

- [ ] **Step 1: Write the failing tests** : `start` sans consommation → 422 ; avec **zéro** ou **deux** consommations d'intrants marqués contenant → 422 ; consommation supérieure au restant d'un achat → 422 ; `start` réussi : le `remaining_qty` des achats diminue de la quantité consommée, `started_at` rempli ; **deux lots sur le même achat** : le second `start` qui dépasserait le restant échoue (409/422) et le restant n'est jamais négatif ; `0.1 + 0.2` litres → restant exact ; `finish` sans résultat (`qty_good` absent) → 422, `found` supérieur à l'attendu → 422 ; `reopen` depuis `termine` autorisé, depuis `expedie` refusé ; `cancel` d'un lot `en_production` **rend** les quantités aux achats et pose `restored_at` ; édition d'un lot non `brouillon` → 409 ; un produit inexistant → 404 ; numéros successifs `FAB-AAAA-0001`, `0002`.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement.** La réservation du stock se fait dans `start_batch` : verrouiller chaque achat concerné avec `lock_purchase` **dans l'ordre croissant des identifiants** (évite les blocages croisés) avant de décrémenter. Le contrôleur lit `TRANSITIONS` pour valider chaque changement d'état. Écrire l'audit à chaque transition.
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_fabrication_batches.py -v`.

---

### Task 5: Bilan, expédition et raccord au circuit existant

**Files:**
- Modify: `repositories/fabrication_repo.py`, `controller/fabrication_controller.py`, `fabrication_endpoints.py`, `fabrication_schemas.py`
- Create: `tests/test_fabrication_ship.py`

**Interfaces:**
- Consumes : tâches 2 et 4 ; modèle existant `ProductionLot` (`models/stock_reception.py`) et sa génération de numéro `LOT-AAAAMMJJ-NNN` : **réutiliser la fonction existante** de création d'un lot de production (la trouver dans `repositories/stock_repo.py`), ne pas dupliquer la numérotation.
- Produces : `get_settings() -> dict`, `update_settings(tolerance_pct, stale_days)` (admin) ; `ship_batch(batch_id, delivery_date, expiry_date=None, justification=None) -> dict` ; routes `GET/PUT /fabrication/settings`, `POST /fabrication/batches/{id}/ship`.

- [ ] **Step 1: Write the failing tests** : `ship` depuis `termine` calcule et **fige** `expected_qty`, `found_qty`, `missing_qty`, `missing_pct`, `tolerance_applied`, `total_cost`, `unit_cost` ; dans la tolérance → réussit sans justification ; **hors tolérance** sans justification, ou justification de seuls espaces → 422, avec une vraie justification → réussit et `out_of_tolerance is True` ; changer ensuite la tolérance globale ne modifie **pas** `tolerance_applied` d'un lot déjà expédié ; l'expédition crée un `ProductionLot` de statut `produit`, `product_id` du lot, `quantity_produced == qty_good`, `producer` égal au nom du compte, et renseigne `production_lot_id` ; `qty_good == 0` → 422 (rien à expédier) ; un lot `expedie` ne peut plus être expédié, rouvert, annulé ni modifié (409) ; `PUT /settings` : 200 pour `admin`, 403 pour `ProductionManager` et `promoteur`, tolérance négative → 422 ; **non-régression du circuit existant** : à partir du `ProductionLot` créé, marquer « livré » puis créer et valider une réception via les fonctions existantes de `stock_repo`/`stock_controller` fait passer le lot à `recu` et augmente le stock du produit de `qty_good`, sans qu'aucun code existant ait été modifié.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement.** Calculer le bilan avec `compute_bilan` (attendu = quantité consommée de l'unique intrant contenant) et le coût avec `compute_cost` sur les `unit_cost_snapshot` des consommations non restituées. Tout dans une seule transaction avec la création du lot de production.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 6: Anomalies, résumé, coût par produit et traçabilité

**Files:**
- Modify: `repositories/fabrication_repo.py`, `controller/fabrication_controller.py`, `fabrication_endpoints.py`
- Create: `tests/test_fabrication_anomalies.py`

**Interfaces:**
- Produces (consommées plus tard par le contrôle quotidien des Rapports) : `list_anomalies() -> list[dict]` où chaque élément est `{"kind": "hors_tolerance" | "intrant_sous_seuil" | "lot_trop_long" | "ecart_expedie_recu", "ref": str, "detail": dict}` ; `summary() -> dict` `{"recent_batches": [...], "counts_by_status": {...}, "anomalies_count": int}` ; `cost_by_product(product_id) -> {"last_unit_cost": Decimal | None, "average_unit_cost": Decimal | None, "batches": int}` (sur les lots expédiés) ; `trace_production_lot(production_lot_id) -> dict | None` (lot de Fabrication, consommations, achats). Routes `GET /fabrication/anomalies`, `GET /fabrication/summary`, `GET /fabrication/products/{id}/cost`, `GET /fabrication/trace/production-lot/{id}`.

- [ ] **Step 1: Write the failing tests** : un lot expédié hors tolérance produit une anomalie `hors_tolerance` ; un intrant dont le stock tombe sous son seuil produit `intrant_sous_seuil` ; un lot `en_production` ou `termine` depuis plus de `stale_days` (créer avec `started_at` antidaté) produit `lot_trop_long`, et un lot expédié n'en produit jamais ; un lot expédié dont la réception existante valide moins de bouteilles bonnes que `qty_good` produit `ecart_expedie_recu` (sans modifier la réception) ; `cost_by_product` : moyenne et dernier coût sur deux lots, `None` sans lot expédié ; `trace_production_lot` d'un lot créé hors Fabrication → `None` (404 côté route) ; aucune anomalie pour un état sain.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** ces requêtes en lecture seule dans le dépôt.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 7: Matrice des rôles et absence de fuite de coûts

**Files:**
- Create: `tests/test_fabrication_roles.py`

**Interfaces:** Consumes : toutes les routes des tâches 3 à 6.

- [ ] **Step 1: Write the tests** (motif de `tests/test_lab_stock_roles.py` : surcharge de `get_current_user`, un tableau `ROUTES` de `(méthode, chemin, corps)`) : pour chaque route, `ProductionManager`, `promoteur`, `admin` reçoivent un code non 403 en **lecture** ; en **écriture** seul `ProductionManager` est accepté (`promoteur`, `admin` → 403) sauf les deux routes d'admin ; `Assistant`, `StockController`, `secretaire`, `medecin`, `nurse`, `laborantin`, `ToxicoManager`, `Psychologist` → 403 partout. Test `test_no_cost_field_in_existing_routes` : `GET /stock/products` et la liste des produits de la pharmacie ne contiennent ni `unit_cost`, ni `total_cost`, ni `cost`. Test `test_real_login_wiring` : deux vraies connexions (limite 5 par minute) vérifient le câblage jeton vers rôle.
- [ ] **Step 2: Run** : `python -m pytest tests/test_fabrication_roles.py -v` : attendu vert ; si une route est trop ouverte, **corriger la garde** dans `fabrication_endpoints.py`, pas le test.
- [ ] **Step 3: Régression ciblée** : `python -m pytest tests/test_stock_receipts.py tests/test_stock_incidents.py tests/test_stock_adjustment_requests.py tests/test_stockcontroller_deny.py -v` : tous verts, **sans modification** de ces fichiers.

---

### Task 8: Passerelle, rôle côté navigateur et menu

**Files:**
- Create: `ah2-admin-web/src/services/FabricationGateway.js`, `ah2-admin-web/tests/fabricationShell.test.mjs`
- Modify: `ah2-admin-web/src/router/index.js` (constante `PRODUCTION_MANAGER: 'ProductionManager'` ; quatre routes enfants de `/dashboard`, voir ci-dessous), `ah2-admin-web/src/components/layout/MainLayout.vue` (constante de rôle, groupe `fabrication`, entrées de menu), `ah2-admin-web/src/design/navPalettes.js` (`productionmanager: 'forest'`), `ah2-admin-web/src/components/users/UserModal.vue` (rôle dans la liste de l'admin et son libellé « Responsable de production »), `ah2-admin-web/src/i18n.js` (`fabrication.menu_*`)

**Interfaces:**
- Produces : `FabricationGateway` avec une méthode par route de l'API (`listIntrants`, `createIntrant`, `setThreshold`, `listPurchases`, `createPurchase`, `updatePurchase`, `cancelPurchase`, `listBatches`, `createBatch`, `getBatch`, `updateBatch`, `startBatch`, `finishBatch`, `reopenBatch`, `cancelBatch`, `shipBatch`, `getSettings`, `updateSettings`, `getAnomalies`, `getSummary`) ; chemins `/dashboard/fabrication-intrants`, `/dashboard/fabrication-lots`, `/dashboard/fabrication-lots/:id` (nom `fabrication-lot`), `/dashboard/fabrication-suivi` ; lecture `[PRODUCTION_MANAGER, PROMOTEUR, ADMIN]`.

- [ ] **Step 1: Write the failing test** `fabricationShell.test.mjs` : les quatre routes existent avec les bons rôles, `PRODUCTION_MANAGER` est présent dans `router/index.js`, `MainLayout.vue` et `UserModal.vue`, la palette du rôle est définie, les clés `fabrication.menu_*` existent en FR et EN, la passerelle expose toutes les méthodes listées.
- [ ] **Step 2: Run and verify it fails** : `node --test ah2-admin-web/tests/fabricationShell.test.mjs`.
- [ ] **Step 3: Implement** passerelle, routes (composants chargés en `import()` dynamique, fichiers créés aux tâches 9 à 11 : créer ici des coquilles vides `<template><div /></template>` pour que la route résolve), menu et enregistrement du rôle.
- [ ] **Step 4: Run** : ce test et `node --test ah2-admin-web/tests/*.test.mjs` : tout vert (les tests de garde des refontes précédentes ne doivent pas échouer ; ajouter les nouveaux fichiers à leurs listes d'autorisation seulement s'ils les protègent).

---

### Task 9: Écran des intrants

**Files:**
- Modify: `ah2-admin-web/src/views/modules/fabrication/FabIntrants.vue`, `ah2-admin-web/src/i18n.js`
- Create: `ah2-admin-web/tests/fabIntrantsContract.test.mjs`

**Interfaces:** Consumes : `FabricationGateway` (tâche 8). Produces : écran de liste des achats et du stock restant par intrant (seuil, badge « sous le seuil » avec texte), panneau `FullScreenPanel` « Nouvel achat » (intrant existant ou nouvel intrant avec unité et case « contenant »), annulation avec motif, réglage du seuil visible seulement pour `admin`.

- [ ] **Step 1: Write the failing contract test** : fige les appels de passerelle utilisés, les conditions de rôle (`canWrite` = `ProductionManager` seul ; seuil : `admin` seul), la présence de `ResponsiveTable` à lignes alternées, d'un `FullScreenPanel`, de champs étiquetés (`FormField`), que « sous le seuil » est dit par du texte, les clés `fabrication.*` citées existent en FR et EN, aucun texte en dur, aucune couleur brute, aucun caractère interdit.
- [ ] **Step 2: Run and verify it fails.**
- [ ] **Step 3: Implement** l'écran avec la bibliothèque `ui/` (modèle : `views/modules/labstock/LabStockProducts.vue`). Les montants s'affichent avec la mise en forme de monnaie déjà utilisée par la caisse.
- [ ] **Step 4: Run and verify it passes**, puis `npx vite build` sans erreur.

---

### Task 10: Liste et fiche d'un lot

**Files:**
- Modify: `FabLots.vue`, `FabLotDetail.vue` (dans `views/modules/fabrication/`), `ah2-admin-web/src/i18n.js`
- Create: `ah2-admin-web/tests/fabLotsContract.test.mjs`, `ah2-admin-web/tests/fabLotDetailContract.test.mjs`

**Interfaces:** Consumes : passerelle. Produces : liste filtrable par statut avec badge d'état (mot et couleur) et création d'un lot (choix d'un produit du catalogue, date) ; fiche conforme à la maquette validée : produit, date, responsable, statut ; tableau des consommations avec provenance et coût ; résultats (bonnes, cassées, rejetées, liquide perdu) ; bloc bilan (attendu, retrouvé, manque en nombre et en %, tolérance, badge « hors tolérance » avec texte) ; bloc coût de revient (total, par bouteille bonne) ; boutons selon le statut : enregistrer, passer en production, terminer, rouvrir, annuler (motif), **valider le bilan et expédier** (champ de justification **obligatoire et visible seulement si hors tolérance**, date de livraison, péremption facultative).

- [ ] **Step 1: Write the failing contract tests** : figent les appels (`startBatch`, `finishBatch`, `reopenBatch`, `cancelBatch`, `shipBatch`), la règle d'affichage du champ de justification (seulement si `out_of_tolerance`) et que le bouton d'expédition reste désactivé tant que la justification est vide dans ce cas, les boutons visibles par statut, les droits (`ProductionManager` seul écrit ; promoteur et admin ne voient aucun bouton d'action), états annoncés (`role="status"`, `role="alert"`), pas de texte en dur ni de couleur brute.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** les deux écrans (tableaux responsives, `FullScreenPanel` pour création et expédition, `StatTile` pour le bilan et le coût).
- [ ] **Step 4: Run and verify they pass**, puis `npx vite build`.

---

### Task 11: Suivi du promoteur, garde-fou et clôture

**Files:**
- Modify: `FabSuivi.vue`, `ah2-admin-web/src/i18n.js`, `docs/superpowers/SUIVI-AVANCEMENT.md`
- Create: `ah2-admin-web/tests/fabSuiviContract.test.mjs`, `ah2-admin-web/tests/refonteFabricationGuard.test.mjs`

**Interfaces:** Consumes : `getSummary`, `getAnomalies`. Produces : écran de lecture : tuiles (lots par statut, anomalies), liste des lots récents, liste des anomalies avec leur nature en toutes lettres, et pour l'admin le réglage de la tolérance et du délai (`updateSettings`).

- [ ] **Step 1: Write the failing tests** : le contrat de `FabSuivi.vue` (lecture seule pour promoteur ; réglages visibles pour `admin` seul) ; le **garde-fou** sur le modèle de `refonteLaboToxicoGuard.test.mjs` : aucune couleur brute, texte ≥ 13 px, aucun caractère interdit, parité FR/EN de `fabrication.*`, usage de `ui/`, **seuls les fichiers prévus ont changé** depuis le commit de départ (liste d'autorisation : fichiers du module, `router/index.js`, `MainLayout.vue`, `navPalettes.js`, `UserModal.vue`, `i18n.js`) et **aucun écran existant** (stock, caisse, labo, toxico) n'est modifié.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** l'écran, puis la section du suivi (ce qui est livré, décisions, résiduels, checklist de vérification par l'utilisateur : créer un achat, un lot, terminer avec une perte hors tolérance, expédier avec justification, voir le lot arriver dans le circuit existant et le valider ; vérifier qu'un compte secrétaire et un compte contrôleur de stock n'ont aucune entrée de menu ni accès).
- [ ] **Step 4: Verification finale** : `node --test ah2-admin-web/tests/*.test.mjs` (tout vert), `npx vite build` (sans erreur), `python -m pytest tests -q` (aucun nouvel échec ; la suite complète dure environ 12 minutes). Reconstruire le `dist` servi par `vite preview` (`npx vite build` dans `ah2-admin-web`).
- [ ] **Step 5: Commit** : seulement si l'utilisateur l'a demandé ; renseigner alors la constante `FIN` du garde-fou avec le hash du dernier commit du lot, dans un commit séparé.
