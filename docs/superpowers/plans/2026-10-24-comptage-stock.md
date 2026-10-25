# Comptage physique du stock de la pharmacie : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le `StockController` compte physiquement les produits de la pharmacie a l'aveugle, le systeme revele les ecarts a la validation et cree une demande d'ajustement (`correction`) par ecart, dans le circuit existant approuve par l'admin ; chaque produit doit etre compte au moins tous les 30 jours.

**Architecture:** Un module isole `stock_count` (migration 026, modeles, regles pures, depot, controleur, routeur `/stock-counts`) sur le modele du module Fabrication et de la cloture de caisse. Les demandes d'ajustement sont creees directement dans le depot (la route existante `POST /stock/adjustment-requests` reste reservee a la secretaire et ne change pas). Cote navigateur : passerelle, store, un ecran de comptage et d'historique pour `StockController`/`admin`, lecture pour `promoteur`.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic (SQL brut idempotent), pytest ; Vue 3 `<script setup>`, vue-i18n 11, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-24-comptage-stock-design.md` (binding). Code existant a lire : `controller/stock_controller.py` (`create_adjustment_request`, `approve_adjustment`), `repositories/stock_repo.py`, `models/stock_reception.py` (`StockAdjustmentRequest`), `models/stock_movement.py`, `api_backend/backend_app/routes/stock/stock_endpoints.py`, `ah2-admin-web/src/views/modules/stock/`.

## Global Constraints

- **Roles** : `StockController` et `admin` comptent ; `promoteur` lit seulement ; tout autre role : 403 ; non authentifie : 401. Garde `role_required` explicite sur chaque route ; table des routes comparee a celles de l'application dans les tests de role.
- **A l'aveugle** : aucune reponse avant la validation (demarrage, liste des produits a compter, statut de frequence) ne contient la quantite du systeme ni un ecart ; apres la validation seulement, le detail du comptage les renvoie. Aucun refus de validation ne depend de l'ecart (sinon il le revele) : une observation par ligne est facultative.
- **Un comptage valide ne se modifie ni ne se supprime** (trigger de base + garde du controleur). Un seul comptage `en_cours` par utilisateur.
- **Ecart non nul** : une demande `StockAdjustmentRequest` de type `correction` par ligne, `quantity` = quantite comptee, `stock_at_request` = stock du systeme lu sous verrou produit a la validation, `requested_by` = le compteur, `status` = `en_attente`, motif = l'observation de la ligne ou "Ecart constate au comptage n. {id} : systeme {S}, compte {C}" ; notification existante `stock_adjustment_request` envoyee aux admins (meme charge que la route existante) ; le stock ne change qu'a l'approbation (circuit existant, inchange).
- **Mouvements pendant le comptage** : le comptage a une heure de debut serveur ; a la validation, par ligne, `movements_during` = nombre de lignes `stock_movement` du produit creees depuis ce debut (le revelateur d'ecart l'affiche en toutes lettres).
- **Frequence** : reglage `interval_days` (defaut 30, entier de 1 a 365, modifiable par `admin` seul) ; le statut d'un produit est `jamais_compte`, `en_retard` (dernier comptage valide plus ancien que le reglage) ou `a_jour`, avec le nombre de jours.
- **Pas de notification push** a l'ouverture ni par script (le controle quotidien du morceau 4 previent) ; un rappel visible sur l'ecran suffit.
- **Perimetre** : produits de la table `pharmacy` ; le stock du labo et les intrants de fabrication ne changent pas.
- **Textes affiches** : FR et EN sous `stockCount.*`, aucun tiret long, point median, fleche, points de suspension typographiques ni emoji ; jetons de couleur seulement ; texte >= 13 px ; cibles >= 44 px ; ecart dit par un mot et pas par la couleur seule ; bibliotheque `ui/` ; dates locales (jamais `toISOString`).
- **Migration** : `down_revision = '025_fab_batch_outputs'`, revision `026_stock_counts`, SQL brut idempotent comme 023 a 025 ; `python -m alembic current` puis appliquer sans demander ; jamais de commande destructive ; reporter le DDL dans `ci/schema_only.sql` (bloc ajoute a la main, CRLF conserve).
- **Tests** : Postgres local ; pytest avec `REDIS_URL=redis://localhost:16379/0` ; un seul pytest a la fois ; import de l'application ~2 minutes ; connexion limitee a 5 par minute.
- **Pas de commit sans demande** (regle de l'utilisateur) : aucun commit pendant l'execution ; l'utilisateur dira quand commiter.

## Review Focus

- Fuite avant validation : demarrage, liste de produits, statut de frequence, notification, message d'erreur, aucun ne revele quantite ni ecart. Taches 2 et 3.
- Deux validations simultanees du meme comptage, ou deux comptages `en_cours` du meme utilisateur. Tache 2.
- Produit supprime ou inactif pendant le comptage ; produit absent du comptage soumis ; produit en double dans la soumission ; quantites negatives, `True`, `2.5`, `"2"`, enormes. Tache 2.
- Ecart du a des ventes pendant le comptage : `movements_during` exact ; la demande d'ajustement garde `stock_at_request` lu a la validation. Tache 2.
- Aucune demande creee quand l'ecart est nul ; une seule demande par ligne en ecart ; notification reellement creee pour les admins par HTTP (cablage de la fabrique). Taches 2 et 3.
- Role non prevu 403 sur chaque route, y compris la secretaire (qui demande des ajustements mais ne compte pas). Tache 3.
- Un comptage valide jamais modifiable (UPDATE/DELETE refuses). Tache 1.

---

## File Structure

| Fichier | Role |
|---|---|
| `alembic/versions/026_stock_counts.py` | tables `stock_counts`, `stock_count_lines`, `stock_count_settings`, contraintes, triggers d'immuabilite |
| `models/stock_count.py` (+ `models/__init__.py`) | modeles |
| `utils/stock_count_rules.py` | validation des lignes, statut de frequence |
| `repositories/stock_count_repo.py` | requetes, verrous, creation des demandes d'ajustement |
| `controller/stock_count_controller.py` | cas d'usage, transaction, audit, notifications |
| `api_backend/backend_app/routes/stock_count/` | routeur `/stock-counts`, schemas |
| `ah2-admin-web/src/services/StockCountGateway.js`, `src/stores/stockCountStore.js`, `src/views/modules/stock/StockCount.vue` | ecran et acces |

---

### Task 1: Migration 026 et modeles

**Files:**
- Create: `alembic/versions/026_stock_counts.py`, `models/stock_count.py`, `tests/test_stock_count_schema.py`
- Modify: `models/__init__.py`, `ci/schema_only.sql`

**Interfaces:**
- Produces : `StockCount(id, status 'en_cours'|'valide'|'abandonne' default 'en_cours', started_by FK users.user_id, started_at naive utc default now, submitted_at NULL, scope 'tous'|'selection')` ; `StockCountLine(id, count_id FK stock_counts.id ON DELETE CASCADE, product_id FK pharmacy.medication_id, counted_qty int >= 0, previous_qty int >= 0, difference int, observation text NULL, movements_during int >= 0 default 0, adjustment_request_id FK stock_adjustment_requests.id NULL)`, unique `(count_id, product_id)` ; `StockCountSettings(id smallint PK CHECK id=1, interval_days int default 30 CHECK 1..365, updated_by FK users NULL, updated_at)` avec une ligne semee. Index partiel unique : un seul `en_cours` par `started_by`. Triggers : `UPDATE`/`DELETE` d'une ligne de `stock_count_lines` refuses ; `UPDATE`/`DELETE` d'un `stock_counts` dont l'ancien statut est `valide` ou `abandonne` refuses.

- [ ] **Step 1: Write the failing tests** : creation valide ; refus de `counted_qty` negatif, statut inconnu, portee inconnue, `interval_days` 0 et 366, doublon `(count_id, product_id)`, second comptage `en_cours` du meme utilisateur (accepte pour un autre utilisateur), modification et suppression d'une ligne refusees, modification d'un comptage valide refusee, passage `en_cours` -> `valide` accepte, ligne de reglage unique (`id = 2` refuse), ligne semee a 30.
- [ ] **Step 2: Run and verify they fail** : `python -m pytest tests/test_stock_count_schema.py -v`
- [ ] **Step 3: Implement** migration idempotente (downgrade symetrique), modeles, bloc DDL dans `ci/schema_only.sql` (le charger dans une base vide jetable avec `ON_ERROR_STOP` pour verifier, puis la supprimer).
- [ ] **Step 4: Apply and verify** : `python -m alembic current`, `upgrade head`, relancer les tests du fichier.

---

### Task 2: Regles, depot et controleur

**Files:**
- Create: `utils/stock_count_rules.py`, `repositories/stock_count_repo.py`, `controller/stock_count_controller.py`, `tests/test_stock_count_rules.py`, `tests/test_stock_count_controller.py`

**Interfaces:**
- Consumes : Tache 1 ; `StockAdjustmentRequest`, `StockRepository.lock_product` / `get_product`, `admin_user_ids`, repos d'audit et de notification (meme motif que `StockController.create_adjustment_request`).
- Produces :
  - `validate_counts(lines: list[dict], valid_product_ids: set[int]) -> list[dict]` : chaque ligne `{product_id: int, counted_qty: int >= 0, observation: str | None}` ; refuse doublon, produit inconnu, quantite non entiere (bool, `2.5`, `"2"`, `None`), negative ou > 10 000 000, observation > 1000 caracteres ; liste vide refusee ; entier integral flottant `2.0` accepte comme 2.
  - `frequency_status(last_counted_at: datetime | None, now: datetime, interval_days: int) -> tuple[str, int | None]` : `("jamais_compte", None)`, `("en_retard", jours)`, `("a_jour", jours)` ; le jour `interval_days` exactement est `a_jour`.
  - Controleur `StockCountController(repo, audit_repo, notification_repo, current_user)` : `start(scope: str = "tous") -> dict` (cree le comptage `en_cours`, renvoie `{id, started_at, products: [{id, name, unit?}]}` SANS aucune quantite ; 409 s'il en existe deja un en cours pour cet utilisateur), `submit(count_id, lines) -> dict` (verrouille le comptage et chaque produit compte dans l'ordre croissant des identifiants, lit le stock sous verrou, calcule `difference = counted - previous`, `movements_during`, cree une demande d'ajustement par ecart non nul, enregistre les lignes completes, passe a `valide`, ecrit l'audit, notifie les admins ; renvoie le detail revele), `abandon(count_id)`, `status() -> dict` (par produit : `last_counted_at`, `days_since`, statut de frequence ; `interval_days` ; AUCUNE quantite), `get(count_id)` et `list(filters)` (detail revele seulement pour les comptages valides ; un `StockController` ne voit que les siens, `admin` et `promoteur` tous), `get_settings()`, `set_interval(days)` (admin seul, audit).
  - Erreurs : `StockCountConflictError` (409), `ValueError` (422), `StockCountNotFoundError` (404), `PermissionError` (403).

- [ ] **Step 1: Write the failing tests** : regles pures (valeurs valides, doublon, inconnu, `True`, `2.5`, `"2"`, negatif, vide, `2.0`, observation longue ; statut de frequence : jamais, 29/30/31 jours, intervalle 1) ; controleur : `start` ne renvoie aucune cle contenant `qty`, `quantity`, `stock` (parcours recursif) ; second `start` du meme utilisateur 409 ; `submit` avec ecart : demande `correction` creee avec `quantity` compte, `stock_at_request` = stock sous verrou, `requested_by` = compteur, motif genere sans observation et motif = observation sinon, lignes enregistrees avec `previous_qty`, `difference`, `adjustment_request_id`, notification pour chaque admin ; ecart nul : aucune demande ; `movements_during` : trois mouvements crees apres le debut sont comptes, ceux d'avant non ; produit absent de la soumission non compte ; deux `submit` du meme comptage : le second 409 ; produit supprime ou hors `valid_product_ids` 422 ; apres validation `get` revele les ecarts, avant il n'y en a pas ; `status()` sans quantite et avec les trois statuts ; reglage : admin seul, 0 et 366 refuses ; roles : un `StockController` ne lit pas le comptage d'un autre ; audit ecrit.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** : le controleur possede la transaction (meme `_tx` que `FabricationController`), le depot ne commit jamais ; creer les demandes AVANT les lignes pour renseigner `adjustment_request_id` ; verrous de produits en ordre croissant pour eviter les interblocages ; la fabrique `get_stock_count_controller(db, current_user)` passe `audit_repo` et `notification_repo`.
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_stock_count_rules.py tests/test_stock_count_controller.py tests/test_stock_adjustment_requests.py -q`.

---

### Task 3: Routes, droits et cablage

**Files:**
- Create: `api_backend/backend_app/routes/stock_count/{__init__,stock_count_endpoints,stock_count_schemas}.py`, `tests/test_stock_count_endpoints.py`, `tests/test_stock_count_roles.py`
- Modify: `api_backend/backend_app/main.py` (enregistrer le routeur avec un commentaire de prefixe)

**Interfaces:**
- Consumes : Tache 2.
- Produces : `POST /stock-counts` (demarrer ; COUNTERS = `StockController`, `admin` ; corps `{scope?}`), `POST /stock-counts/{id}/submit` (COUNTERS ; corps `{lines:[{product_id, counted_qty, observation?}]}`, schema strict `extra=forbid`, `StrictInt`), `POST /stock-counts/{id}/abandon` (COUNTERS), `GET /stock-counts/status` (COUNTERS + `promoteur`), `GET /stock-counts` et `GET /stock-counts/{id}` (COUNTERS + `promoteur`), `GET /stock-counts/settings` (COUNTERS + `promoteur`), `PUT /stock-counts/settings` (`admin` seul, corps `{interval_days}`). Chemins fixes (`/status`, `/settings`) declares AVANT `/{id}` ; identifiants bornes `ge=1, le=2**31-1` ; pagination bornee de la liste.

- [ ] **Step 1: Write the failing tests** : parcours HTTP complet (demarrer, soumettre avec un ecart, lire le detail revele, la demande d'ajustement existe et la notification admin aussi, preuve du cablage de la fabrique) ; `GET /status` et la reponse de demarrage sans cle de quantite (parcours recursif) ; matrice de roles complete (StockController, admin, promoteur selon leur droit ; secretaire, Assistant, ProductionManager, manager, medecin, nurse, laborantin, ToxicoManager, Psychologist, SpiritualCounsellor : 403 ; non authentifie : 401 exactement) ; table des routes de l'application egale a celle du test ; entrees invalides 422 jamais 500 (`True`, `2.5`, `"2"`, champ en trop, liste vide, id hors plage) ; erreurs 404/409 ; une vraie connexion pour le cablage jeton -> role (limite 5 connexions par minute).
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** sur le modele de `routes/fabrication` (gardes par route, mapping d'erreurs commun).
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_stock_count_endpoints.py tests/test_stock_count_roles.py tests/test_stock_count_controller.py -q` puis la regression `tests/test_stock_*.py tests/test_notifications.py`.

---

### Task 4: Interface

**Files:**
- Create: `ah2-admin-web/src/services/StockCountGateway.js`, `src/stores/stockCountStore.js`, `src/views/modules/stock/StockCount.vue`, `tests/stockCountContract.test.mjs`
- Modify: `router/index.js` (route `/dashboard/stock-count`, roles `StockController`, `admin`, `promoteur`), `src/components/layout/MainLayout.vue` (entree de menu pour ces roles) et la palette de menu du role si necessaire, `src/i18n.js`

**Interfaces:**
- Consumes : Tache 3 (routes).
- Produces : un ecran avec deux zones. **Comptage** (`StockController`/`admin`) : bouton "Demarrer un comptage", liste des produits SANS quantite du systeme avec un champ entier par produit (recherche par nom, selection de lignes, les produits non saisis ne sont pas comptes), observation facultative par ligne, bouton de validation avec garde contre le double clic ; apres la validation, tableau revele (produit, systeme, compte, ecart dit en mots "en plus"/"en moins"/"aucun ecart", mouvements pendant le comptage dits en toutes lettres, lien vers la demande d'ajustement) ; abandon d'un comptage en cours. **Frequence** (tous les roles autorises) : par produit, dernier comptage (date locale) et mot "Jamais compte" / "En retard" / "A jour", filtre sur les en retard ; reglage des jours pour `admin` seul. **Historique** : liste des comptages valides et detail. `promoteur` : lecture seule, aucun bouton d'ecriture. Textes sous `stockCount.*` FR/EN, memes cles.

- [ ] **Step 1: Write the failing tests** (`stockCountContract.test.mjs`) : la passerelle appelle les routes avec les bons chemins et corps (entiers, pas de chaines) ; aucune cle de quantite du systeme n'est lue ni affichee avant la validation (le gabarit n'affiche `previous_qty`/`difference` que depuis le resultat de la validation) ; controles d'ecriture masques pour `promoteur` et visibles pour `StockController`/`admin` ; le reglage n'est visible que pour `admin` ; double clic protege ; parite FR/EN de `stockCount.*` ; caracteres interdits ; jetons de couleur seulement ; pas de `toISOString`.
- [ ] **Step 2: Run and verify they fail** : `node --test tests/stockCountContract.test.mjs`.
- [ ] **Step 3: Implement** avec `ui/` (modeles : `views/modules/stock/StockList.vue`, `StockControlQueue.vue`) ; mettre a jour les tests de menu qui figent les entrees si besoin (seules les aiguilles legitimes).
- [ ] **Step 4: Run and verify they pass** : le fichier ci-dessus, `node --test tests/*.test.mjs`, `npx vite build` depuis `ah2-admin-web`.

---

### Task 5: Garde-fou, suivi d'avancement et verification finale

**Files:**
- Modify: `ah2-admin-web/tests/clotureCaisseGuard.test.mjs` (liste des fichiers autorises : ajouter les fichiers existants modifies par ce plan, minimal, avec commentaire du chantier), `docs/superpowers/SUIVI-AVANCEMENT.md`

**Interfaces:** Produces : section "Comptage physique du stock : livre, NON COMMITE (2026-10-24)" : livre, decisions (aveugle, pas de refus de validation, demandes d'ajustement par ecart dans le circuit existant, 30 jours reglable, pas de notification push, mouvements pendant le comptage), residuels, liste de verification utilisateur (compter a l'aveugle, ecart cree une demande, l'admin approuve et le stock change, comptage valide non modifiable, produit jamais compte signale, reglage reserve a l'admin, promoteur lecture seule, roles non prevus sans acces).

- [ ] **Step 1: Verify the guard fails on a simulated out-of-list file** (fonction pure `horsPerimetre` du garde-fou) puis ajouter les fichiers prevus.
- [ ] **Step 2: Write the SUIVI section** avec les nombres reels des rapports de tache.
- [ ] **Step 3: Verification finale** : `node --test tests/*.test.mjs`, `npx vite build`, `python -m pytest tests/test_stock_count_*.py tests/test_stock_*.py tests/test_notifications.py -q` ; la suite serveur complete (~30 minutes) une fois a la fin.
- [ ] **Step 4: Commit** seulement si l'utilisateur le demande ; renseigner alors la borne de fin du garde-fou dans un commit separe.
