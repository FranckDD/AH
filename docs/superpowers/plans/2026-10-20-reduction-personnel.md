# Réduction personnel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Appliquer automatiquement, à la caisse, une réduction configurable (par catégorie de produit, seuil sur le total de la facture, taux) aux patients marqués « Personnel », en ligne et hors ligne, avec contrôle serveur.

**Architecture:** Une fonction de calcul pure, écrite en Python et en JS sur un jeu de cas commun (fixture JSON), applique les règles de `staff_discount_rules` aux lignes de la facture. Le poste calcule, le serveur recalcule dans `CaisseController.create_transaction` et rejette tout écart ; `caisse.amount` reste le net dû. `patients.is_staff` s'écrit uniquement via un endpoint dédié réservé admin/promoteur.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (SQL brut) + pytest ; Vue 3 / Pinia / PowerSync ; `node --test` pour les tests JS purs.

**Spec:** `docs/superpowers/specs/2026-10-20-reduction-personnel-design.md`

## Global Constraints

- Catégories (CHECK constraint, valeurs exactes) : `medicament`, `examen`, `consultation`, `carnet`, `autre_soin`.
- `rate_percent` : entier 1..100. `min_invoice_amount` : `Numeric(10,2)` ≥ 0, défaut 0.
- Une seule règle **active** par catégorie : index unique partiel `(category) WHERE is_active`.
- Seuil comparé au **total de la facture** ; taux appliqué aux **seules lignes de la catégorie visée** ; arrondi au centime **une fois** sur la somme.
- Droits : écriture des règles et de `patients.is_staff` = `admin` et `promoteur` uniquement. Lecture des règles = `admin`, `promoteur`, `secretaire`.
- `caisse.amount` = net dû. Brut = Σ `line_total` = `amount + staff_discount_amount`.
- Une réduction manuelle approuvée **remplace** la réduction personnel (`staff_discount_amount` → 0, base = brut). Un refus ne change rien.
- Patient de passage (`patient_id` NULL) : jamais de réduction personnel.
- Type d'article inconnu → catégorie `autre_soin` (jamais d'erreur).
- Rôles réels en base : `admin`, `promoteur`, `secretaire`, `ToxicoManager`, `Psychologist`, `Assistant`… (pas de rôle « manager »). Dans les tests : `create_test_user(db, username, "admin"|"promoteur"|"secretaire", password=...)`.
- Toutes les chaînes UI en FR **et** EN (`ah2-admin-web/src/i18n.js`).
- Migrations Alembic : SQL brut idempotent (`IF NOT EXISTS`), motif de `alembic/versions/017_triage_infirmiere_medecin.py`. CI charge `ci/schema_only.sql` : y reporter le même DDL.
- Ne pas commiter sans accord de l'utilisateur (mémoire projet) : les étapes « Commit » ci-dessous sont à exécuter **seulement si l'utilisateur l'a demandé pour cette session**, sinon les sauter.

## Écarts assumés par rapport au spec (découverts en lisant le code)

1. `patients.is_staff` ne passe **pas** par `PUT/PATCH /patients/{id}` (qui appellent des procédures stockées Postgres `create_patient`/`update_patient`, risque de régression) mais par `PUT /patients/{patient_id}/staff` (admin, promoteur). `PatientUpdate` reste inchangé.
2. `staff_discount_details` est **produit uniquement par le serveur** (le poste n'envoie que `staff_discount_amount`) : un snapshot fourni par le client ne serait pas fiable.
3. La recherche patient de `CaisseInvoiceModal` est **en ligne seulement** aujourd'hui (aucun secours local) : `is_staff` voyage dans la réponse `GET /patients/`, pas dans le stream `patients_lookup`. Seules les **règles** ont un secours hors ligne (même motif que `searchProducts`). Un patient personnel ne peut donc être sélectionné hors ligne que s'il l'a été avant la coupure — limite préexistante, hors périmètre.
4. L'écran des règles est une **vue dédiée** (`/reductions-personnel`), car la route `system-config` exclut `promoteur`.

## Review Focus

- Facture exactement au seuil (`total == min_invoice_amount`) : règle appliquée (comparaison `>=`). Test dans Task 2.
- Règle désactivée entre le calcul local et la synchro : facture rejetée par le serveur, pas corrigée. Test dans Task 5.
- Ligne `Service` (`item_ref_id = 0`, libre) : catégorie `autre_soin`. Test dans Task 2.
- Facture entièrement de catégories sans règle (réduction 0) : `staff_discount_amount = 0`, `staff_discount_details = NULL`. Test dans Task 5.
- Annulation d'une facture personnel : `amount`/`staff_discount_amount` conservés tels quels (aucun recalcul à l'annulation). Test dans Task 5.

---

### Task 1: Schéma — migration, modèles, CI

**Files:**
- Create: `alembic/versions/018_staff_discount.py`
- Create: `models/staff_discount_rule.py`
- Modify: `models/patient.py` (ajout `is_staff`), `models/caisse.py` (ajout 2 colonnes), `models/__init__.py` (import), `ci/schema_only.sql` (même DDL)
- Test: `tests/test_staff_discount_schema.py`

**Interfaces:**
- Produces: `StaffDiscountRule` (`id`, `category`, `min_invoice_amount: Decimal`, `rate_percent: int`, `is_active: bool`, `created_by`, `created_at`, `updated_by`, `updated_at`) ; `Patient.is_staff: bool` ; `Caisse.staff_discount_amount: Decimal` (défaut 0), `Caisse.staff_discount_details: dict | None` (JSONB).

- [ ] **Step 1: Écrire `tests/test_staff_discount_schema.py`** : (a) insérer deux `StaffDiscountRule(category="medicament", is_active=True)` lève `IntegrityError` (index unique partiel) ; (b) une catégorie `"inconnue"` lève `IntegrityError` (CHECK) ; (c) `rate_percent=0` et `101` lèvent `IntegrityError` ; (d) un `Patient` créé via `create_test_patient` a `is_staff is False` ; (e) une règle inactive + une règle active de même catégorie coexistent.
- [ ] **Step 2: Lancer** `python -m pytest tests/test_staff_discount_schema.py -q` — attendu : échec (modèle/colonnes absents).
- [ ] **Step 3: Écrire la migration `018_staff_discount`** (`revision = '018_staff_discount'`, `down_revision = '017_triage_infirmiere_medecin'`) : `ALTER TABLE patients ADD COLUMN IF NOT EXISTS is_staff boolean NOT NULL DEFAULT false` ; `ALTER TABLE caisse ADD COLUMN IF NOT EXISTS staff_discount_amount numeric(10,2) NOT NULL DEFAULT 0, ADD COLUMN IF NOT EXISTS staff_discount_details jsonb` ; `CREATE TABLE IF NOT EXISTS staff_discount_rules (...)` avec CHECK sur les 5 catégories, CHECK `rate_percent BETWEEN 1 AND 100`, CHECK `min_invoice_amount >= 0`, et `CREATE UNIQUE INDEX IF NOT EXISTS uq_staff_discount_rules_active_category ON staff_discount_rules (category) WHERE is_active`. `downgrade()` inverse. Ajouter les modèles/colonnes SQLAlchemy ; reporter le DDL dans `ci/schema_only.sql`.
- [ ] **Step 4: Appliquer** la migration à la base de dev (`alembic upgrade head`, politique de migration relâchée) puis **vérifier directement** : `SELECT column_name FROM information_schema.columns WHERE table_name IN ('patients','caisse') AND column_name IN ('is_staff','staff_discount_amount','staff_discount_details')` renvoie 3 lignes.
- [ ] **Step 5: Relancer** les tests de Step 1 — attendu : PASS. Lancer aussi `tests/test_caisse.py tests/test_patients.py -q` (non-régression des modèles).
- [ ] **Step 6: Commit** `feat: schema reduction personnel (is_staff, regles, colonnes caisse)`.

---

### Task 2: Calcul pur (Python) + jeu de cas commun

**Files:**
- Create: `utils/staff_discount.py`, `tests/fixtures/staff_discount_cases.json`, `tests/test_staff_discount_calc.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `normalize_item_category(item_type: str) -> str` (retourne l'une des 5 catégories).
  - `compute_staff_discount(lines: list[dict], is_staff: bool, rules: list[dict]) -> dict` avec `lines` = `[{"item_type": str, "line_total": number, "status": "active"?}]`, `rules` = `[{"category": str, "min_invoice_amount": number, "rate_percent": int, "is_active": bool}]`, retour `{"amount": Decimal, "details": list[dict] | None}` où chaque détail = `{"category", "rate_percent", "base", "discount", "min_invoice_amount"}` ; `details` est `None` quand `amount == 0`.

- [ ] **Step 1: Créer `tests/fixtures/staff_discount_cases.json`** : tableau de cas `{name, is_staff, lines, rules, expected_amount, expected_categories}` couvrant exactement : (1) spec : règle `medicament` min 5000 taux 50, lignes 3000 `Vente Médicament` + 4000 `Examens` → 1500 ; (2) total sous le seuil → 0 ; (3) total **égal** au seuil → réduction appliquée ; (4) `is_staff=false` → 0 ; (5) aucune règle active → 0 ; (6) deux règles (médicament 50 %, examen 20 %) sur une facture dépassant leurs seuils → somme des deux ; (7) ligne `status: "cancelled"` ignorée du total et de la base ; (8) type inconnu `"Truc"` et `Service` → catégorie `autre_soin` ; (9) arrondi : 3 lignes de 33.33 à 50 % → 49.995 arrondi une fois à 50.00 (arrondi demi-supérieur) ; (10) variantes de libellé `Sale Medication`, `Médicament`, `Vente Carnet`, `Examen`, `Consultation Spirituel`, `Consultation Médical`, `Désintox` → catégories `medicament, medicament, carnet, examen, consultation, consultation, autre_soin`.
- [ ] **Step 2: Écrire `tests/test_staff_discount_calc.py`** : un test paramétré qui charge la fixture et vérifie `compute_staff_discount(...)["amount"] == Decimal(expected_amount)` et l'ensemble des catégories de `details`, plus un test dédié `test_normalize_item_category_variants` sur le cas (10) et `test_details_none_when_no_discount`.
- [ ] **Step 3: Lancer** — attendu : échec (module absent).
- [ ] **Step 4: Implémenter `utils/staff_discount.py`** : normalisation insensible à la casse et aux accents (`unicodedata`), correspondance par sous-chaîne (`medic`/`medication` → `medicament` ; `carnet`/`booklet` → `carnet` ; `exam` → `examen` ; `consult` → `consultation` ; sinon `autre_soin`) ; calcul en `Decimal`, arrondi `ROUND_HALF_UP` unique sur la somme.
- [ ] **Step 5: Relancer** — attendu : PASS.
- [ ] **Step 6: Commit** `feat: calcul pur de la reduction personnel (python)`.

---

### Task 3: Règles — repo, contrôleur, endpoints

**Files:**
- Create: `repositories/staff_discount_repo.py`, `controller/staff_discount_controller.py`, `api_backend/backend_app/routes/staff_discount/staff_discount_endpoints.py` (+ `__init__.py` si le motif des autres routes l'exige)
- Modify: `api_backend/backend_app/main.py` (inclure le router avec le préfixe `/staff-discount-rules`)
- Test: `tests/test_staff_discount_rules_endpoints.py`

**Interfaces:**
- Consumes: `StaffDiscountRule` (Task 1).
- Produces:
  - `StaffDiscountRepository(session)` : `list_rules() -> list[StaffDiscountRule]`, `list_active_rules() -> list[dict]` (forme attendue par `compute_staff_discount`), `upsert_rule(category, min_invoice_amount, rate_percent, is_active, user_id) -> StaffDiscountRule`.
  - `GET /staff-discount-rules` → `[{"category", "min_invoice_amount": float, "rate_percent": int, "is_active": bool}]` (admin, promoteur, secretaire).
  - `PUT /staff-discount-rules/{category}` body `{min_invoice_amount, rate_percent, is_active}` (admin, promoteur) → règle mise à jour ; 422 si catégorie inconnue, taux hors 1..100 ou seuil < 0.

- [ ] **Step 1: Tests** (`api_client(auth_endpoints, staff_discount_endpoints)`) : `test_put_creates_then_updates_single_rule` (deux PUT sur `medicament` → une seule ligne) ; `test_put_forbidden_for_secretaire` (403) ; `test_get_allowed_for_secretaire` (200) ; `test_put_rejects_invalid_values` (taux 0, 101, seuil −1, catégorie `xyz` → 422) ; `test_put_writes_audit_entry` (ligne `AuditUserAction` avec `resource_type="StaffDiscountRule"`, anciennes et nouvelles valeurs) ; `test_deactivate_then_reactivate_keeps_unique_active_rule`.
- [ ] **Step 2: Lancer** — attendu : échec (404, route absente).
- [ ] **Step 3: Implémenter** repo, contrôleur (validation + audit via `audit_repo.log_user_action`, motif de `DiscountRequestController`) et endpoints ; brancher dans `main.py`.
- [ ] **Step 4: Relancer** — attendu : PASS.
- [ ] **Step 5: Commit** `feat: endpoints des regles de reduction personnel`.

---

### Task 4: `is_staff` — lecture et endpoint dédié

**Files:**
- Modify: `api_backend/backend_app/routes/patients/patients_schemas.py` (`PatientResponse.is_staff: bool = False`), `repositories/patient_repo.py` (inclure `'is_staff'` dans `get_by_id`, `get_by_id_any_status` et tout constructeur de dict renvoyé aux listes), `api_backend/backend_app/routes/patients/patients_endpoints.py` (nouvel endpoint), `controller/patient_controller.py` (`set_staff`)
- Test: `tests/test_patient_is_staff.py`

**Interfaces:**
- Consumes: `Patient.is_staff` (Task 1).
- Produces: `PUT /patients/{patient_id}/staff` body `{"is_staff": bool}` (admin, promoteur) → `{"patient_id": int, "is_staff": bool}` ; `PatientController.set_staff(patient_id: int, is_staff: bool) -> dict` journalise `resource_type="Patient"`, `action_performed="SET_STAFF"`, anciennes/nouvelles valeurs ; `GET /patients/`, `GET /patients/{id}` renvoient `is_staff`.

- [ ] **Step 1: Tests** : `test_admin_and_promoteur_can_set_staff` ; `test_secretaire_medecin_nurse_get_403` ; `test_put_patient_with_is_staff_in_body_does_not_change_it` (le `PUT /patients/{id}` d'une secrétaire avec `is_staff: true` laisse `is_staff` à false — le champ n'est pas dans `PatientUpdate`) ; `test_set_staff_unknown_patient_404` ; `test_get_patients_list_and_detail_expose_is_staff` (valeur reflétée après `PUT .../staff`) ; `test_set_staff_writes_audit`.
- [ ] **Step 2: Lancer** — attendu : échec.
- [ ] **Step 3: Implémenter** : colonne exposée partout où `PatientResponse` est construit (vérifier chaque constructeur de dict de `patient_repo.py` et `mapping.py`), endpoint + `set_staff` (écriture ORM directe de la colonne, pas la procédure stockée).
- [ ] **Step 4: Relancer** + `tests/test_patients.py tests/test_patient_dossier.py -q` (non-régression) — attendu : PASS.
- [ ] **Step 5: Commit** `feat: is_staff sur le patient (endpoint admin/promoteur)`.

---

### Task 4b: Gestion du personnel — recherche/liste minimale (admin, promoteur)

*Ajoutée pendant l'exécution (ruling R5 du ledger) : le `promoteur` n'a accès à aucune page patient (routeur patients et route `PatientDetail` l'excluent) ; sans cette tâche il ne pourrait jamais cocher « Personnel », contrairement à la décision 5 du spec.*

**Files:**
- Modify: `api_backend/backend_app/routes/patients/patients_endpoints.py` (sur le `staff_router` existant de Task 4), `api_backend/backend_app/routes/patients/patients_schemas.py`, `controller/patient_controller.py`, `repositories/patient_repo.py`, `api_backend/backend_app/main.py` (ordre d'inclusion des routeurs)
- Test: `tests/test_patient_staff_lookup.py`

**Interfaces:**
- Consumes: `Patient.is_staff`, `staff_router` (Task 4).
- Produces: `GET /patients/staff-lookup?q=<str>&only_staff=<bool>&limit=<int>` (admin, promoteur) → `[{"patient_id": int, "code_patient": str, "first_name": str, "last_name": str, "is_staff": bool}]` et **rien d'autre** (pas de téléphone, date de naissance, résidence : le promoteur ne doit pas gagner de lecture des données patient). `q` (≥ 2 caractères, `Query(None, min_length=2)`) filtre par prénom/nom/code (ilike) ; `only_staff=true` ne renvoie que les `is_staff` (tri nom de famille) et `q` devient optionnel ; sans `q` ni `only_staff` → 422. `limit` défaut 20, 1..50. Patients supprimés (`is_deleted`) exclus.

- [ ] **Step 1: Tests** : `test_promoteur_and_admin_can_search_by_name_and_code` ; `test_only_staff_lists_only_flagged_patients_sorted_by_last_name` ; `test_response_has_exactly_the_five_fields` (comparer l'ensemble des clés) ; `test_secretaire_medecin_toxicomanager_get_403` ; `test_soft_deleted_patient_excluded` ; `test_no_q_and_not_only_staff_returns_422` ; `test_q_shorter_than_2_returns_422` ; `test_staff_lookup_not_swallowed_by_patient_id_route` (le chemin `/patients/staff-lookup` ne renvoie pas 422 « patient_id » : le `staff_router` doit être inclus **avant** le routeur patients principal dans `main.py`).
- [ ] **Step 2: Lancer** — attendu : échec (404/422).
- [ ] **Step 3: Implémenter** l'endpoint sur `staff_router` (requête ORM limitée aux 5 colonnes) ; vérifier l'ordre d'inclusion dans `main.py`.
- [ ] **Step 4: Relancer** + `tests/test_patient_is_staff.py tests/test_patients.py -q` — attendu : PASS (notamment `GET /patients/{id}` toujours servi par le routeur principal).

---

### Task 5: Contrôle serveur à la création de facture + ticket

**Files:**
- Modify: `controller/caisse_controller.py` (`create_transaction`, `build_ticket_data`), `repositories/caisse_repo.py` (`create_transaction` persiste les 2 colonnes ; `get_transaction_details_for…`/sérialisation détail), `api_backend/backend_app/routes/caisse/caisse_schemas.py` (champ d'entrée `staff_discount_amount: float = 0` ; champs de sortie `staff_discount_amount`, `staff_discount_details`), `printer_bridge/ticket_renderer.py`, `tests/…` du renderer s'il existe
- Test: `tests/test_caisse_staff_discount.py`

**Interfaces:**
- Consumes: `compute_staff_discount` (Task 2), `StaffDiscountRepository.list_active_rules` (Task 3), `Patient.is_staff` (Task 4).
- Produces: `CaisseController.create_transaction(data)` accepte `data["staff_discount_amount"]` (défaut 0) ; invariants : `Σ line_total − staff_discount_amount == amount` ; `staff_discount_amount` doit égaler le recalcul serveur (sinon `ValueError("Réduction personnel incohérente avec les règles en vigueur.")`) ; `caisse.staff_discount_details` = détails serveur ou NULL ; `build_ticket_data(...)["staff_discount"]` = `{"amount": float, "details": list} | None`.

- [ ] **Step 1: Tests** (appels via `POST /caisse/` ou contrôleur selon le motif de `tests/test_caisse.py`) : `test_staff_invoice_with_correct_discount_accepted` (règle médicament 5000/50, patient `is_staff`, 3000+4000 → `staff_discount_amount=1500`, `amount=5500`, `staff_discount_details` non NULL) ; `test_discount_too_high_rejected` ; `test_discount_on_non_staff_patient_rejected` ; `test_discount_without_patient_rejected` ; `test_missing_discount_when_rule_applies_rejected` (le poste envoie 0 alors qu'une règle active s'applique → refusé, pas corrigé) ; `test_rule_deactivated_before_sync_rejected` ; `test_no_matching_rule_stores_zero_and_null_details` ; `test_non_staff_invoice_unchanged` (non-régression : sans réduction, comportement actuel identique) ; `test_cancel_keeps_discount_fields` ; `test_ticket_data_exposes_staff_discount` ; `test_get_transaction_exposes_staff_fields`.
- [ ] **Step 2: Lancer** — attendu : échec.
- [ ] **Step 3: Implémenter** : dans `create_transaction`, remplacer le contrôle `total_calc != data["amount"]` par `total_calc − staff_discount_amount != amount`, puis recalcul serveur (`is_staff` lu via `patient_id`, règles actives) et comparaison **avant** `repo.create_transaction` ; passer les colonnes au repo ; ajouter le bloc `staff_discount` au ticket ; dans `ticket_renderer.py` imprimer, avant `Paye:`, une ligne « Réduction personnel: -X » quand `ticket_data.get("staff_discount")` est présent (bloc voisin du bloc `discount` existant).
- [ ] **Step 4: Relancer** + `tests/test_caisse.py tests/test_caisse_uuid.py tests/test_discount_requests.py tests/test_finance_ledger.py -q` — attendu : PASS.
- [ ] **Step 5: Commit** `feat: controle serveur de la reduction personnel a la facturation`.

---

### Task 6: Interaction avec la réduction manuelle

**Files:**
- Modify: `controller/discount_request_controller.py` (création : `original_amount` = brut ; décision), `repositories/caisse_repo.py` si un helper de brut est utile
- Test: `tests/test_discount_requests_staff.py`

**Interfaces:**
- Consumes: colonnes `staff_discount_*` (Task 1) ; `create_request` calcule aujourd'hui `original_amount=Decimal(str(invoice_data["amount"]))`.
- Produces: `discount_requests.original_amount` = `amount + staff_discount_amount` (brut) ; à l'approbation avec pourcentage : `tx.amount = original_amount × (1 − pct/100)`, `tx.staff_discount_amount = 0`, `tx.staff_discount_details` complété d'une clé `"replaced_by_discount_request": request_id` ; refus/annulation : aucun changement des champs de réduction personnel.

- [ ] **Step 1: Tests** : `test_request_original_amount_is_gross_for_staff_invoice` ; `test_approval_replaces_staff_discount` (amount recalculé sur le brut, `staff_discount_amount == 0`, trace dans details) ; `test_refusal_keeps_staff_discount` ; `test_approval_echeance_only_keeps_staff_discount` (approuvé sans pourcentage → réduction personnel conservée) ; `test_non_staff_request_unchanged` (non-régression).
- [ ] **Step 2: Lancer** — attendu : échec.
- [ ] **Step 3: Implémenter** dans `create_request`/`reassign` (brut) et `decide_request` (remplacement uniquement si `decision_percent` accordé).
- [ ] **Step 4: Relancer** + `tests/test_discount_requests.py -q` — attendu : PASS.
- [ ] **Step 5: Commit** `feat: la reduction manuelle remplace la reduction personnel`.

---

### Task 7: Calcul JS, règles côté client, couches PowerSync

**Files:**
- Create: `ah2-admin-web/src/utils/staffDiscount.js`, `ah2-admin-web/tests/staffDiscount.test.mjs`, `ah2-admin-web/src/services/StaffDiscountGateway.js`
- Modify: `ah2-admin-web/src/powersync-client/AppSchema.js` (colonne `staff_discount_amount: column.text` sur `caisse` ; nouvelle table `staff_discount_rules` locale en lecture seule), `ah2-admin-web/src/powersync-client/client.js` (`db.syncStream('reference_staff_discount_rules')`), `powersync/sync-config.yaml` (stream `reference_staff_discount_rules` + colonne `staff_discount_amount::text AS staff_discount_amount` dans `secretariat_caisse`), `ah2-admin-web/src/powersync-client/DossierConnector.js` (payload du `caisse:PUT`), `ah2-admin-web/src/stores/caisseStore.js` (INSERT local), `ah2-admin-web/src/powersync-client/referenceData.js` (lecture locale des règles)

**Interfaces:**
- Consumes: fixture `tests/fixtures/staff_discount_cases.json` (Task 2) ; `GET /staff-discount-rules` (Task 3).
- Produces:
  - `normalizeItemCategory(itemType: string): string` et `computeStaffDiscount(lines, isStaff, rules): { amount: number, details: object[] | null }` (mêmes entrées/sorties que la version Python, montants en nombres arrondis au centime).
  - `StaffDiscountGateway.list(): Promise<rule[]>` (REST, repli `getStaffDiscountRulesLocal()` pour `secretaire` sur erreur réseau, motif de `CaisseGateway.searchProducts`), `StaffDiscountGateway.save(category, payload)`.
  - Les créations de facture écrivent et envoient `staff_discount_amount`.

- [ ] **Step 1: `ah2-admin-web/tests/staffDiscount.test.mjs`** (`node:test`) : charge la fixture partagée, boucle sur chaque cas et vérifie `computeStaffDiscount(...).amount` et les catégories ; test `normalizeItemCategory` sur les variantes de libellé du cas (10).
- [ ] **Step 2: Lancer** `node --test ah2-admin-web/tests/staffDiscount.test.mjs` — attendu : échec (module absent).
- [ ] **Step 3: Implémenter `staffDiscount.js`** (réplique stricte de `utils/staff_discount.py`, arrondi demi-supérieur via entiers en centimes pour éviter les écarts flottants) ; relancer — attendu : PASS.
- [ ] **Step 4: Couches PowerSync** (4 couches, motif documenté au chantier triage) : `AppSchema.js`, `INSERT` de `caisseStore.createInvoice` (+ colonne `staff_discount_amount`), `DossierConnector.js` `caisse:PUT` (`staff_discount_amount: Number(op.opData.staff_discount_amount || 0)`), payload `CaisseGateway.createInvoice` ; stream de règles en lecture seule — **jamais** de `staff_discount_rules:PUT/PATCH` dans le connecteur.
- [ ] **Step 5: Vérifier** `cd ah2-admin-web && npx vite build` (succès) et, si le service PowerSync tourne, que le YAML est valide (`docker logs powersync-powersync-1` après redémarrage ne montre pas d'erreur de sync-config).
- [ ] **Step 6: Commit** `feat: calcul JS de la reduction personnel et couches PowerSync`.

---

### Task 8: Interface — règles, patient, caisse, ticket, i18n

**Files:**
- Create: `ah2-admin-web/src/views/modules/caisse/StaffDiscountRules.vue`
- Modify: `ah2-admin-web/src/router/index.js` (route `staff-discount-rules`, path `reductions-personnel`, `roles: [ROLES.ADMIN, ROLES.PROMOTEUR]`), `ah2-admin-web/src/components/layout/MainLayout.vue` (entrée de menu, mêmes rôles), `ah2-admin-web/src/components/patients/PatientHeader.vue` (badge « Personnel » + bascule admin/promoteur via `PUT /patients/{id}/staff`), `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue` (ligne « Réduction personnel », total net, `staff_discount_amount` dans `buildInvoiceData`), `ah2-admin-web/src/views/modules/finance/CaisseList.vue` (`buildLocalTicketData` : `staff_discount`), `ah2-admin-web/src/i18n.js` (FR + EN)

**Interfaces:**
- Consumes: `computeStaffDiscount`, `StaffDiscountGateway` (Task 7) ; `selectedPatient.is_staff` (réponse `GET /patients/`, Task 4) ; `authStore.hasRole([...])`.
- Produces: écran de gestion des 5 catégories (montant minimal, taux, actif) ; facture affichant `Réduction personnel −X` et le total net ; ticket local avec `staff_discount: { amount, details }`.

- [ ] **Step 1: i18n** : bloc `staffDiscount` (titre, colonnes, catégories `medicament/examen/consultation/carnet/autre_soin`, messages d'erreur 403/422, badge « Personnel », ligne de facture, avertissement « une réduction manuelle remplacera la réduction personnel ») en FR et EN.
- [ ] **Step 2: Écran des règles** : tableau des 5 catégories pré-affichées (une ligne vide si aucune règle), édition en place, bouton enregistrer par ligne appelant `StaffDiscountGateway.save`, retour d'erreur visible (jamais avalé). **Seconde section « Membres du personnel »** (Task 4b) : liste des patients `is_staff` (`GET /patients/staff-lookup?only_staff=true`), champ de recherche (≥ 2 caractères) pour trouver un patient et le cocher/décocher via `PUT /patients/{id}/staff` — c'est le seul endroit où le `promoteur` peut gérer « Personnel ».
- [ ] **Step 3: `PatientHeader.vue`** : badge « Personnel » en lecture seule si `patient.is_staff` (la bascule vit sur l'écran des règles, Step 2 — pas de seconde bascule ici).
- [ ] **Step 4: `CaisseInvoiceModal.vue`** : `staffDiscount = computed(() => selectedPatient.value?.is_staff ? computeStaffDiscount(linesAsPayload, true, rules) : …0)`, `netAmount = totalAmount − staffDiscount.amount` utilisé pour `payload.amount` et pour la borne de l'avance ; règles chargées à l'ouverture via `StaffDiscountGateway.list()` ; avertissement avant « Demander une réduction » quand `staffDiscount.amount > 0`.
- [ ] **Step 5: `CaisseList.vue`** : `buildLocalTicketData` renseigne `staff_discount` depuis le payload ; ticket en ligne inchangé (le backend fournit le bloc).
- [ ] **Step 6: Vérifier** `cd ah2-admin-web && npx vite build` (succès) puis, avec l'API et le frontend lancés : (a) PUT d'une règle `medicament` 5000/50 par admin ; (b) case Personnel cochée sur un patient de test ; (c) facture 3000 médicaments + 4000 examens → ligne −1500, total 5500 ; (d) même patient décoché → plein tarif ; (e) un compte secrétaire ne voit pas l'écran des règles ; (f) un compte promoteur peut chercher un patient et le marquer « Personnel » depuis l'écran des règles. Consigner le résultat réel (ne pas affirmer sans l'avoir vu).
- [ ] **Step 7: Commit** `feat: interface de la reduction personnel (regles, patient, caisse, ticket)`.

---

### Task 9: Suivi et vérification finale

**Files:**
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md` (nouvelle section du chantier), mémoire projet (`project_backlog_pre_deploiement.md` : item 7 fait)

- [ ] **Step 1: Suite complète du backend** : `python -m pytest tests -q` ; comparer aux échecs préexistants documentés (9 connus + 1 flaky) — aucun nouvel échec attendu.
- [ ] **Step 2: Build frontend** `cd ah2-admin-web && npx vite build` et `node --test ah2-admin-web/tests/staffDiscount.test.mjs`.
- [ ] **Step 3: Mettre à jour** `SUIVI-AVANCEMENT.md` (livré, écarts assumés ci-dessus, limite hors ligne de la recherche patient, vérifications faites et non faites) et la mémoire.
- [ ] **Step 4: Commit** `docs: suivi du chantier reduction personnel`.

---

## Addendum (2026-10-20, après la revue finale) — lever les résiduels listés au suivi

L'utilisateur a demandé de corriger les résiduels « non corrigés » de la revue finale : (a) badge « Personnel » absent de la liste des patients, (b) badge absent du dossier chargé hors ligne, (c) recherche patient de la caisse en ligne seulement, (d) facture PDF sans ligne de réduction.

### Task 10: Badge dans la liste, badge hors ligne, recherche patient de la caisse hors ligne

**Files:**
- Modify: `powersync/sync-config.yaml` (streams `clinical_patients` et `patients_lookup` : colonne `is_staff`), `ah2-admin-web/src/powersync-client/AppSchema.js` (tables locales `patients` et `patients_lookup` : `is_staff: column.integer`), `ah2-admin-web/src/stores/patientDossierStore.js` (chemin `loadDossierFromLocalDb` : `is_staff: !!row.is_staff`), `ah2-admin-web/src/services/CaisseGateway.js` (`searchPatients` : secours local), `ah2-admin-web/src/views/modules/patients/PatientList.vue` (+ `patientStore.js` si le mapping des lignes l'exige), `ah2-admin-web/src/i18n.js` si une chaîne manque
- Test: `ah2-admin-web/tests/caisseSearchLocal.test.mjs` si une fonction pure est extraite (ex. `buildLocalPatientSearch`)

**Interfaces:**
- Consumes: `patients_lookup` (local : `patient_id, code_patient, first_name, last_name, contact_phone`), `authStore.hasRole`, motif de secours de `CaisseGateway.searchProducts` (garde `!err.response && hasRole(['secretaire'])`).
- Produces: `CaisseGateway.searchPatients(query)` renvoie `{ data: [{patient_id, code_patient, first_name, last_name, is_staff}] }` dans les deux chemins (REST et secours local, `LIKE` insensible à la casse sur nom/prénom/code, 8 résultats max) ; `is_staff` booléen partout côté UI ; badge « Personnel » dans les lignes de `PatientList.vue` (même libellé i18n que l'en-tête du dossier).

- [ ] **Step 1**: sync + schéma : `is_staff` dans les deux streams (`patients.is_staff` comme booléen existant ; alias `AS patients_lookup` déjà présent) et dans `AppSchema.js` ; redémarrer le conteneur PowerSync (`docker compose restart powersync` depuis `powersync/`) et lire les logs (autorisé) ; consigner le résultat réel.
- [ ] **Step 2**: `patientDossierStore.js` chemin hors ligne : exposer `is_staff` ; `CaisseGateway.searchPatients` : secours local réservé au rôle `secretaire` sur erreur réseau (jamais pour un autre rôle : l'erreur doit se propager) ; test node `node:test` de la fonction de recherche locale si extraite.
- [ ] **Step 3**: badge dans `PatientList.vue` (lecture seule, aucune bascule).
- [ ] **Step 4**: `cd ah2-admin-web && npx vite build` + `node --test ah2-admin-web/tests/*.test.mjs` ; dire explicitement que la vérification navigateur n'est PAS faite.

### Task 11: Facture PDF — ligne de réduction personnel

**Files:**
- Modify: `repositories/caisse_repo.py` (`generate_invoice_pdf_content`), `utils/invoice_pdf_generator.py`, le gabarit `invoice_template.html` (localiser son chemin réel), `api_backend/backend_app/utils/templates/` si c'est là
- Test: `tests/test_invoice_pdf_staff_discount.py`

**Interfaces:**
- Consumes: `caisse.staff_discount_amount` / `staff_discount_details` (net = `caisse.amount`).
- Produces: quand `staff_discount_amount > 0`, le PDF affiche `Prix normal` (Σ lignes = amount + réduction), `Réduction personnel −X` et `TOTAL FACTURE` = montant net ; sans réduction le PDF reste identique à aujourd'hui.

- [ ] **Step 1**: tests : contexte de rendu avec réduction (Prix normal = net + réduction, ligne réduction présente, total = net) ; sans réduction aucune ligne ajoutée (non-régression) ; une facture dont la réduction manuelle a remplacé la réduction personnel (montant 0) n'affiche pas de ligne personnel. Si le rendu PDF réel (WeasyPrint) est testable dans l'environnement, extraire le texte et vérifier ; sinon tester le dictionnaire de contexte et le HTML rendu.
- [ ] **Step 2**: implémenter ; relancer `tests/test_invoice_pdf_staff_discount.py` et les tests PDF/caisse existants.

### Addendum 2 (2026-10-20, après validation des limites restantes)

**Task 12 (backend) — facture personnel : modification refusée.** Décision utilisateur : option « refuser, annuler puis recréer ». `CaisseController.update_transaction` refuse (ValueError, même mécanisme que le verrou de réduction manuelle) toute modification contenant `items`, `patient_id` ou `amount` quand `staff_discount_amount > 0` sur la facture stockée (message FR clair : annuler et recréer la facture). Les autres champs (note…) restent modifiables ; une facture SANS réduction stockée garde le comportement R6 actuel (recalcul serveur si on lui associe un patient personnel). Les tests de Task 5 qui supposaient qu'un PUT recalcule une facture personnel sont convertis en tests de refus.

**Task 13 (frontend) — liste des factures + statut « inconnu ».** (a) La liste et le détail d'une facture affichent « Réduction personnel −X » sous le montant quand `staff_discount_amount > 0` (donnée déjà fournie par l'API et la table locale `caisse`). (b) Distinction « pas personnel » / « statut non synchronisé » : le secours local de `CaisseGateway.searchPatients` conserve `is_staff: null` quand la colonne locale est NULL (au lieu de `false`), et `CaisseInvoiceModal.vue` bloque la validation avec un avertissement visible FR+EN (« statut personnel non synchronisé : connectez-vous une fois pour terminer la synchronisation ») quand `selectedPatient.is_staff === null`. Les résultats REST gardent un booléen.

