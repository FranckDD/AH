# Onglet Rapports et controle quotidien : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Une page Rapports (promoteur, admin) avec un encadre "Controle du jour", 13 cartes d'indicateurs, un tableau "total vendu par produit", un export PDF, et un controle quotidien de 23 h 30 qui notifie promoteur et admin seulement en cas de nouvelle anomalie.

**Architecture:** Un agregateur de lecture (`ReportsController`) qui compose les sources existantes sans en dupliquer la logique (cloture de caisse, caisse, fabrication, comptage, ajustements, notifications) ; un controle quotidien deterministe (cles d'anomalie stables, instantane stocke par jour, differences avec la veille) lance par un script CLI idempotent avec rattrapage ; une page Vue avec cartes et courbes `chart.js` deja presentes ; un export PDF WeasyPrint avec l'en-tete dynamique du centre.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic (SQL brut idempotent), WeasyPrint ; Vue 3 `<script setup>`, `chart.js`/`vue-chartjs`, vue-i18n 11, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-25-rapports-controle-quotidien-design.md` (binding, y compris sa section "Precisions apres relecture"). Modeles de code a lire : `controller/doctor_dashboard_controller.py` (premier agregateur du projet : un controleur compose des sources de plusieurs routeurs), `controller/cash_closure_controller.py` et `repositories/cash_closure_repo.py` (`flows`, cloture, rattrapage, `catch_up`), `controller/fabrication_controller.py` (`list_anomalies`, `summary`), `controller/stock_count_controller.py` (`status`), `repositories/caisse_repo.py`, `utils/business_time.py`, `scripts/cash_closure_catchup.py`, `docs/superpowers/SUIVI-AVANCEMENT.md` (section "Chantier exports/impressions" pour l'en-tete PDF et le piege de polices WeasyPrint).

## Global Constraints

- **Roles** : `promoteur` et `admin` lisent tout ; `admin` seul modifie les seuils ; tout autre role : 403 ; non authentifie : 401 exactement. Garde `role_required` explicite par route ; table des routes comparee a celles de l'application dans les tests de role.
- **Lecture seule** : aucune route de ce module n'ecrit dans un autre module. Les chiffres viennent des memes requetes ou fonctions que les ecrans d'origine (cloture de caisse, fabrication, comptage) ; un calcul qui diverge de sa source est un defaut.
- **Dates** : jours locaux de Douala (`utils/business_time.py`), bornes en `[debut, fin+1 jour)` converties en UTC naif pour les colonnes naives ; jamais `toISOString` pour une date seule ; periode : jour, 7 jours, 30 jours ou dates libres (fin >= debut, 366 jours maximum, sinon 422).
- **Ventes** : une vente compte au jour local de son paiement (`paid_at`) ; seules les ventes au statut `active` comptent (annulees, remboursees, `pending_approval` exclues).
- **Recu au stock** : receptions validees du circuit de stock plus reapprovisionnements approuves ; les lots de production ne se comptent pas a part (ils entrent par ces receptions).
- **Controle quotidien** : cle d'anomalie stable `nature:reference` ; instantane par date (unique) a 23 h 30 Douala ; notification (une par destinataire : promoteur et chaque admin actif) SEULEMENT s'il existe au moins une cle nouvelle par rapport a l'instantane de la veille (texte "N nouveaux points, M encore ouverts", lien vers la page) ; rappel une fois tous les 7 jours tant qu'un point reste ouvert ; jours passes lus depuis l'instantane, aujourd'hui en direct, jour sans instantane recalcule avec la mention "recalcule" ; l'encadre montre l'union des anomalies de la periode avec leur date de premiere apparition.
- **Anomalies retenues** : caisse (journee sans cloture manuelle, ecart non nul sur un mode, cloture avec "commentaire non fourni") ; ventes (plus de `cancelled_sales_threshold` ventes annulees dans la journee, alerte `price_mismatch`) ; production (sortie declaree `autre`, lot hors tolerance, lot trop long, ecart expedie / recu : lire `FabricationController.list_anomalies`) ; stock (produit jamais compte ou en retard de comptage, demande d'ajustement en attente depuis plus de `adjustment_pending_days` jours). Seuils par defaut 3 et 3, reglables par l'admin ; les seuils de Fabrication restent dans les reglages de Fabrication.
- **Carte 5** : encaisse par secretaire, **par jour reellement travaille** (jours ou le compte a encaisse), jamais par semaine.
- **Textes affiches** : FR et EN sous `reports.*`, aucun tiret long, point median, fleche, points de suspension typographiques ni emoji ; jetons de couleur seulement (y compris les courbes) ; texte >= 13 px ; cibles >= 44 px ; etat dit par un mot et pas par la couleur seule ; bibliotheque `ui/` ; chaque indicateur dans sa propre carte avec sa periode et sa source nommees.
- **Migration** : `down_revision = '027_stock_count_line_times'` (verifier avec `alembic heads`), revision `028_reports_control`, SQL brut idempotent, `python -m alembic current` puis appliquer sans demander, jamais de commande destructive ; DDL reporte dans `ci/schema_only.sql` (bloc ajoute a la main, CRLF, avant la section PUBLICATION).
- **Tests** : Postgres local ; pytest avec `REDIS_URL=redis://localhost:16379/0` ; un seul pytest a la fois ; import de l'application ~2 minutes ; connexion limitee a 5 par minute ; un test qui frappe un endpoint composant plusieurs routeurs doit remplacer `get_db` pour tous (chaque module a sa connexion).
- **Pas de commit sans demande** (regle de l'utilisateur).

## Review Focus

- Un chiffre de carte qui differe de l'ecran d'origine (cloture, fabrication, comptage) sur les memes donnees. Taches 3 et 4.
- Vente annulee, remboursee ou en attente comptee a tort ; vente a cheval sur minuit Douala / UTC ; double compte d'un lot de production dans "recu". Taches 3 et 4.
- Notification chaque soir pour une anomalie qui dure ; notification sans anomalie ; notification en double si le script tourne deux fois ; jour manque rattrape. Tache 5.
- Fuite de droits : tout role hors promoteur/admin 403 ; la secretaire ne voit pas l'ecart de caisse par un autre chemin. Tache 6.
- Periode invalide, trop longue, fin avant debut, produit absent, pagination hors plage : 422 jamais 500. Tache 6.
- Fichier PDF vide, en-tete manquant, polices (sous-ouverture WeasyPrint), periode longue. Tache 8.

---

## File Structure

| Fichier | Role |
|---|---|
| `alembic/versions/028_reports_control.py` | tables `daily_controls`, `report_settings` |
| `models/report.py` (+ `models/__init__.py`) | modeles |
| `utils/report_rules.py` | cles d'anomalie, difference veille / jour, rappel hebdomadaire, jours travailles |
| `repositories/report_repo.py` | requetes de lecture non couvertes par les modules existants |
| `controller/reports_controller.py` | agregateur, controle quotidien, reglages |
| `api_backend/backend_app/routes/reports/` | routes et schemas |
| `scripts/daily_control.py` | CLI du soir (idempotent, rattrapage) |
| `ah2-admin-web/src/services/ReportsGateway.js`, `src/stores/reportsStore.js`, `src/views/modules/reports/Reports.vue` (+ composants) | page |

---

### Task 1: Migration 028 et modeles

**Files:**
- Create: `alembic/versions/028_reports_control.py`, `models/report.py`, `tests/test_report_schema.py`
- Modify: `models/__init__.py`, `ci/schema_only.sql`

**Interfaces:**
- Produces : `DailyControl(id, business_date date UNIQUE, anomalies jsonb NOT NULL default '[]' (liste d'objets {key, kind, ref, label, detail, first_seen}), new_count int, open_count int, computed_at timestamp naif UTC, notified_at timestamp NULL, reminder_sent_at timestamp NULL, recomputed bool default false)` ; `ReportSettings(id smallint PK CHECK id=1, cancelled_sales_threshold int default 3 CHECK 1..1000, adjustment_pending_days int default 3 CHECK 1..365, updated_by FK users NULL, updated_at)` avec une ligne semee. Index sur `business_date`.

- [ ] **Step 1: Write the failing tests** : creation d'un controle ; refus d'un doublon de `business_date` ; seuils hors bornes (0, 1001, 0 jours, 366) ; ligne de reglages unique (`id = 2` refuse) et semee a 3 / 3 ; `anomalies` doit etre un tableau JSON (un objet est refuse par CHECK `jsonb_typeof = 'array'`).
- [ ] **Step 2: Run and verify they fail** : `python -m pytest tests/test_report_schema.py -v`
- [ ] **Step 3: Implement** migration (downgrade symetrique), modeles, bloc DDL de `ci/schema_only.sql` (charge dans une base jetable avec `ON_ERROR_STOP` pour verifier, puis supprimee).
- [ ] **Step 4: Apply and verify** : `alembic current`, `upgrade head`, relancer les tests.

---

### Task 2: Regles pures

**Files:** Create `utils/report_rules.py`, `tests/test_report_rules.py`

**Interfaces:**
- Produces :
  - `anomaly_key(kind: str, ref: str | int) -> str` (`"{kind}:{ref}"`, refuse vide) ; `normalize_anomaly(raw: dict) -> dict` (cles `key, kind, ref, label, detail`).
  - `diff_anomalies(previous_keys: set[str], today: list[dict]) -> dict` renvoie `{new: [...], still_open: [...], resolved_keys: [...]}` ; une anomalie d'une cle deja vue la veille est `still_open`.
  - `should_notify(new: list, still_open: list, last_reminder_at: datetime | None, now: datetime) -> tuple[bool, str | None]` : `(True, "nouveau")` s'il y a au moins une nouvelle ; `(True, "rappel")` s'il n'y a que des points ouverts et que le dernier rappel date de 7 jours ou plus (ou jamais) ; sinon `(False, None)`.
  - `first_seen_map(snapshots: list[dict]) -> dict[str, date]` (premiere date d'apparition de chaque cle sur une suite d'instantanes).
  - `worked_days(payment_dates: list[date]) -> int` (nombre de jours distincts) et `per_worked_day(total: Decimal, days: int) -> Decimal | None` (`None` si 0 jour).
  - `parse_period(date_from, date_to, today) -> tuple[date, date]` (defauts : aujourd'hui ; 366 jours maximum ; `ValueError` sinon).

- [ ] **Step 1: Write the failing tests** : cles ; difference (veille vide, tout nouveau, une resolue, une encore ouverte) ; `should_notify` (une nouvelle, aucune nouvelle et rappel du, rappel recent, rien) ; premiere apparition sur trois jours ; jours travailles (doublons, aucun) ; `per_worked_day` exact en `Decimal` ; periode (defaut, fin avant debut, 367 jours refuses, 366 acceptes).
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** en `Decimal` et sans acces base.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 3: Sources argent et croissance

**Files:** Create `repositories/report_repo.py` (debut), `controller/reports_controller.py` (debut), `tests/test_report_money.py`

**Interfaces:**
- Consumes : Taches 1 et 2 ; `CashClosureRepository.flows` / listes de clotures (`controller/cash_closure_controller.py`), `CaisseRepository`/modeles `Caisse`, `CaisseItem`, `PaiementEchelonne`, `CaisseRetrait`, `DiscountRequest`, `StaffDiscount*`.
- Produces dans `ReportsController(repo_set, current_user)` (lecture seule) : `money(period) -> dict` avec les cartes 1 a 5 : `collected` (total et par mode officiel, depuis les memes entrees que la cloture), `cash_gaps` (par jour : compte, attendu, ecart par mode, type de cloture manuelle/auto, lu depuis les clotures), `withdrawals_and_cancellations` (montants, nombres, motifs), `discounts` (montant et nombre des reductions manuelles approuvees et des reductions automatiques du personnel, separes), `per_secretary` (par compte : encaisse, jours travailles, encaisse par jour travaille) ; `growth(period) -> dict` : `new_patients` et `consultations` par semaine sur 3 mois, `sales` par semaine sur 3 mois avec la periode precedente de meme longueur. Chaque carte porte `period` et `source`.

- [ ] **Step 1: Write the failing tests** (donnees creees avec les fixtures existantes) : l'encaisse par mode est egal a la somme des entrees de `CashClosureRepository.flows` sur la meme periode ; une vente annulee, remboursee ou `pending_approval` n'est jamais comptee ; une vente payee a 23 h 30 UTC compte au lendemain Douala ; ecart de caisse exact lu des clotures ; par secretaire : 2 jours travailles et total 300 donnent 150 par jour travaille, 0 jour donne `None` ; reductions personnel et manuelles separees ; croissance : semaines, periode precedente ; periode vide = zeros et pas d'erreur.
- [ ] **Step 2: Run and verify they fail** : `python -m pytest tests/test_report_money.py -v`.
- [ ] **Step 3: Implement** en reutilisant les fonctions des modules d'origine plutot que des requetes paralleles quand elles existent.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 4: Sources produits, production et stock

**Files:** Modify `repositories/report_repo.py`, `controller/reports_controller.py` ; Test `tests/test_report_products.py`

**Interfaces:**
- Consumes : Taches 1 a 3 ; `FabricationController.summary` / `list_anomalies` / `list_outputs`, `StockCountController.status`, `StockAdjustmentRequest`, `StockReceipt*`, `Pharmacy`, `CaisseItem`.
- Produces : `products(period) -> dict` : carte 6 (`sold`, `received` selon la regle du spec, `system_stock` actuel), carte 7 (comptes en retard, jamais comptes, ecarts en attente d'approbation), carte 8 (produits sous leur seuil : lire la regle de seuil existante dans le module de stock) ; `production(period) -> dict` : carte 9 (lots par statut, lots trop longs), carte 10 (bouteilles produites, sorties declarees par motif, expediees), carte 11 (lots hors tolerance, manque, cout par bouteille bonne) ; `sold_by_product(period, q=None, item_type='Medicament', category=None, sort='amount_desc', limit=50, offset=0) -> {items:[{product_id, name, category, quantity, amount}], total}` (filtrable par nom partiel insensible a la casse et aux accents, par categorie et par type de ligne).

- [ ] **Step 1: Write the failing tests** : vendu contre recu sur un jeu connu (3 receptions validees, 1 rejetee, 1 reapprovisionnement approuve et 1 refuse : seuls les valides comptent ; un lot expedie recu par reception validee compte une fois) ; vente annulee exclue du vendu ; tableau : filtre par nom partiel ("para" trouve "Paracetamol"), par type, tri, pagination et `total` exact, page hors plage vide ; carte 7 : produit jamais compte et produit en retard ; carte 10 : sorties `echantillon` et `autre` separees, sorties annulees exclues ; carte 11 : lot hors tolerance et cout par bouteille identiques a `FabricationController`.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** en reutilisant les controleurs d'origine pour la production et le comptage.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 5: Controle quotidien, reglages et script du soir

**Files:** Modify `controller/reports_controller.py`, `repositories/report_repo.py` ; Create `scripts/daily_control.py`, `tests/test_daily_control.py`, `tests/test_daily_control_cli.py`

**Interfaces:**
- Consumes : Taches 1 a 4 ; notifications existantes (types, payload, `NotificationBell.vue` pour le libelle), `ReportSettings`.
- Produces : `compute_anomalies(day: date) -> list[dict]` (sources du spec : cloture, annulations, `price_mismatch` du jour, sorties `autre`, anomalies de Fabrication, comptage en retard / jamais, demandes d'ajustement en attente au-dela du seuil) ; `run_daily_control(day: date, now) -> dict` (calcule, compare a l'instantane de la veille, ecrit l'instantane de `day` sans doublon, notifie selon `should_notify`, renvoie `{day, new, still_open, notified}`, idempotent : un second appel ne renotifie pas) ; `catch_up(now) -> list[dict]` (rattrape les jours manques depuis le dernier instantane jusqu'a hier, 30 jours maximum, du plus ancien au plus recent, le jour courant seulement apres 23 h 30 Douala) ; `get_control(period) -> {items, recomputed}` (union par cle avec `first_seen`, jours passes lus des instantanes, aujourd'hui en direct) ; `get_settings()` / `set_settings(cancelled_sales_threshold, adjustment_pending_days)` (admin seul, audit, upsert si la ligne a ete supprimee). Notification : type `daily_control`, payload `{business_date, new_count, open_count, reason}` ; libelle FR/EN dans `NotificationBell.vue` ; clic vers `/dashboard/reports`. Script `scripts/daily_control.py` : `SessionLocal`, `catch_up(now UTC)`, journalise, code 0 si rien a faire ou verrou pris (journalise), non nul sur erreur ; un verrou consultatif evite deux executions simultanees.

- [ ] **Step 1: Write the failing tests** : une anomalie nouvelle declenche une notification pour le promoteur et chaque admin actif (et aucun autre role), le second passage du meme jour n'en cree pas ; le lendemain, la meme anomalie encore ouverte ne notifie pas ; rappel a 7 jours ; aucune anomalie : rien, instantane quand meme ecrit ; seuils : 3 ventes annulees = pas d'anomalie, 4 = anomalie ; demande d'ajustement en attente depuis 4 jours = anomalie, 2 jours = non ; cloture automatique de la veille = anomalie "journee sans cloture manuelle" ; rattrapage de 3 jours manques dans l'ordre ; jour sans instantane lu en direct avec `recomputed`; fabrique du controleur cablee (notification reellement creee par HTTP ou via la fabrique) ; script : deux executions, une seule notification, code 0 ; erreur de base : code non nul.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** ; l'instantane est ecrit en une transaction (unicite de `business_date` = garde contre la double execution).
- [ ] **Step 4: Run and verify they pass.**

---

### Task 6: Routes, schemas et droits

**Files:** Create `api_backend/backend_app/routes/reports/{__init__,reports_endpoints,reports_schemas}.py`, `tests/test_reports_endpoints.py`, `tests/test_reports_roles.py` ; Modify `api_backend/backend_app/main.py`

**Interfaces:**
- Consumes : Taches 3 a 5.
- Produces (READERS = promoteur, admin ; SETTINGS_WRITERS = admin) : `GET /reports/overview?date_from&date_to` (cartes 1 a 13), `GET /reports/daily-control?date_from&date_to`, `GET /reports/products-sold?date_from&date_to&q&item_type&category&sort&limit&offset`, `GET /reports/settings`, `PUT /reports/settings` (corps strict `{cancelled_sales_threshold: StrictInt 1..1000, adjustment_pending_days: StrictInt 1..365}`). Chemins fixes avant tout chemin parametre ; periodes invalides 422.

- [ ] **Step 1: Write the failing tests** : parcours HTTP (overview, controle, tableau filtre et pagine, reglages) avec les donnees des taches precedentes ; matrice de roles complete (tous les roles du projet dont `manager`, `Assistant`, `StockController`, `ProductionManager`, `secretaire`, `medecin`, `nurse`, `laborantin`, `ToxicoManager`, `Psychologist`, `SpiritualCounsellor` : 403 ; non authentifie : 401 exactement ; promoteur : lecture oui, `PUT /settings` 403) ; table des routes de l'application egale a celle du test ; periode invalide, 367 jours, limite 201, offset negatif : 422 ; la reponse ne contient aucune donnee hors des modules attendus (pas de cout de fabrication fuite hors des cartes 10 et 11 et du role promoteur/admin) ; une vraie connexion pour le cablage jeton -> role ; remplacer `get_db` pour tous les routeurs composes dans les tests.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** sur le modele de `routes/fabrication` et `routes/doctor_dashboard`.
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_reports_endpoints.py tests/test_reports_roles.py -q` puis la regression `tests/test_cash_*.py tests/test_fabrication_*.py tests/test_stock_count_*.py tests/test_notifications.py -q`.

---

### Task 7: Page Rapports

**Files:**
- Create: `ah2-admin-web/src/services/ReportsGateway.js`, `src/stores/reportsStore.js`, `src/views/modules/reports/Reports.vue` (+ composants dans `src/components/reports/`), `tests/reportsContract.test.mjs`
- Modify: `router/index.js` (`/dashboard/reports`, roles promoteur et admin), `src/components/layout/MainLayout.vue` (entree de menu), `src/components/notifications/NotificationBell.vue` (type `daily_control`), `src/i18n.js`, tests de menu qui figent les entrees (aiguilles legitimes seulement)

**Interfaces:**
- Consumes : Tache 6.
- Produces : la page de la disposition A validee : selecteur de periode (aujourd'hui, 7 jours, 30 jours, dates libres en jours locaux), encadre "Controle du jour" (liste des points en mots avec date de premiere apparition, mention "deja signale" et "recalcule", lien vers l'ecran concerne ; message "Rien a signaler" sinon), 13 cartes en quatre blocs (Argent, Produits, Production, Croissance), chacune avec son titre, son chiffre principal, sa periode et sa source, courbes `chart.js` aux couleurs des jetons (carte 12 et 13), tableau "Total vendu par produit" (recherche, filtre de type et de categorie, tri, pagination), bouton "Exporter en PDF" (tache 8), reglages des deux seuils pour l'admin seul. Etats de chargement, d'erreur et de vide visibles ; protection contre les reponses perimees ; `promoteur` en lecture seule.

- [ ] **Step 1: Write the failing tests** (`reportsContract.test.mjs`) : la passerelle appelle les routes avec les bons parametres (dates locales, pas de `toISOString`) ; 13 cartes presentes, chacune avec sa periode et sa source ; le tableau filtre et pagine ; les reglages sont visibles pour l'admin seulement ; reponses perimees ignorees ; parite FR/EN de `reports.*` ; caracteres interdits ; jetons de couleur ; la cloche connait `daily_control`.
- [ ] **Step 2: Run and verify they fail** : `node --test tests/reportsContract.test.mjs`.
- [ ] **Step 3: Implement** avec `ui/` et `chart.js` (importer seulement les elements utilises pour garder le paquet petit) ; modeles : `views/modules/fabrication/FabSuivi.vue`, `views/modules/caisse/CashClosuresReview.vue`.
- [ ] **Step 4: Run and verify they pass** : le fichier ci-dessus, `node --test tests/*.test.mjs`, `npx vite build` depuis `ah2-admin-web`.

---

### Task 8: Export PDF

**Files:** Modify `api_backend/backend_app/routes/reports/reports_endpoints.py`, `controller/reports_controller.py`, `ah2-admin-web/src/services/ReportsGateway.js`, `src/views/modules/reports/Reports.vue` ; Create `templates/` ou le dossier de gabarits utilise par les autres exports (suivre `exports/impressions`), `tests/test_reports_pdf.py`

**Interfaces:**
- Consumes : Taches 3 a 7 ; `get_pdf_header_context` + `_pdf_header.html` + WeasyPrint (voir le piege de polices note dans le suivi d'avancement).
- Produces : `GET /reports/export.pdf?date_from&date_to` (READERS) renvoyant un PDF (`application/pdf`, nom de fichier avec la periode) : en-tete dynamique du centre, periode, controle du jour, les 13 indicateurs en tableaux (les courbes ne sont pas reprises : chiffres seulement), tableau des produits vendus de la periode (au plus 500 lignes, ordre par montant). Bouton "Exporter en PDF" qui telecharge avec la periode choisie, message d'erreur lisible (rappel : une reponse `blob` en erreur doit etre decodee en texte pour lire le message du serveur).

- [ ] **Step 1: Write the failing tests** : l'appel renvoie 200, un PDF valide (en-tete `%PDF`, relu avec `pypdf` : plusieurs pages possibles, texte contenant le nom du centre, la periode, "Controle du jour" et un chiffre connu) ; periode invalide 422 en JSON ; role non prevu 403 ; periode de 30 jours avec beaucoup de produits ne depasse pas 500 lignes ; le piege de polices : le texte est extractible apres ouverture et ecriture par `pypdf`.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** ; test frontend : le bouton passe la periode, decode l'erreur `blob`.
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_reports_pdf.py -q` et `node --test tests/reportsContract.test.mjs`.

---

### Task 9: Suivi d'avancement et verification finale

**Files:** Modify `docs/superpowers/SUIVI-AVANCEMENT.md`

**Interfaces:** Produces : section "Rapports et controle quotidien : livre, NON COMMITE (2026-10-25)" : livre, decisions (disposition A, 13 cartes, cle d'anomalie, notification seulement pour du nouveau, rappel a 7 jours, instantane a 23 h 30, seuils), residuels, liste de verification utilisateur (ouvrir la page en promoteur et admin, verifier chaque carte contre l'ecran d'origine, creer une anomalie et attendre 23 h 30 ou lancer le script, notification recue une seule fois, rappel, tableau des produits filtre, export PDF, roles non prevus sans acces, reglages reserves a l'admin), et rappel au chantier 8 : planifier `scripts/daily_control.py` a 23 h 30 Douala en plus du rattrapage horaire de la cloture de caisse.

- [ ] **Step 1: Run the complete verification** : `node --test tests/*.test.mjs` et `npx vite build` (depuis `ah2-admin-web`), `python -m pytest tests/test_report_*.py tests/test_reports_*.py tests/test_daily_control*.py -q` puis la suite serveur complete (~20 minutes) une fois.
- [ ] **Step 2: Write the SUIVI section** avec les nombres reels des rapports de tache.
- [ ] **Step 3: Commit** seulement si l'utilisateur le demande.
