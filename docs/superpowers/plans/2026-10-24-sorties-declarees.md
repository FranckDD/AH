# Sorties declarees de la production : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le `ProductionManager` declare, sur un lot termine, les bouteilles sorties avant l'envoi au stock (echantillon ou autre), sans approbation, avec trace complete ; le stock expedie et le bilan du lot en tiennent compte.

**Architecture:** Une table `fab_batch_outputs` (migration 025) rattachee au lot ; la logique vit dans le module Fabrication existant (regles pures, depot, controleur, routes `/fabrication`) ; l'interface etend la fiche du lot et "Suivi et anomalies". Le bilan (`compute_bilan`) ne change pas : les sorties sont des bouteilles BONNES retirees avant expedition, donc `qty_shipped = qty_good - sorties actives`.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic (SQL brut idempotent), pytest ; Vue 3 `<script setup>`, vue-i18n 11, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-24-sorties-declarees-design.md` (binding). Module existant : `docs/superpowers/specs/2026-10-23-fabrication-production-design.md`, code dans `models/fabrication.py`, `utils/fabrication_rules.py`, `repositories/fabrication_repo.py`, `controller/fabrication_controller.py`, `api_backend/backend_app/routes/fabrication/`, `ah2-admin-web/src/views/modules/fabrication/`.

## Global Constraints

- **Aucune approbation** : une sortie prend effet des la declaration et ne bloque jamais l'expedition.
- **Declaration** : seulement sur un lot au statut `termine` (resultat saisi) et non expedie. Motifs : `echantillon` ou `autre` (ni don ni vente directe). Quantite : entier > 0 (bool, float non entier, chaine : refuses) ; le total des sorties actives d'un lot ne depasse jamais `qty_good`. Note : obligatoire (non vide apres espaces) pour `autre`, facultative pour `echantillon`.
- **Annulation** : avec motif obligatoire, seulement tant que le lot n'est pas expedie ; la sortie reste en historique au statut `annulee` ; rien ne s'efface.
- **Expedition** : quantite envoyee au circuit de stock = `qty_good - sorties actives` ; si le resultat est <= 0, refus clair. Le cout par bouteille reste `total_cost / qty_good` (inchange). `compute_bilan` est inchange.
- **Reouverture** d'un lot (`reopen`) refusee (409) tant qu'une sortie active existe.
- **Roles** : `ProductionManager` ecrit ; `promoteur` et `admin` lisent ; tout autre role : 403 (garde par route, comme le module). Aucune donnee de sortie ni de cout hors des routes `/fabrication`.
- **Trace** : declaration et annulation ecrites dans l'audit existant (`FabBatchOutput`, actions `CREATE` / `CANCEL`), avec auteur, heure, motif, note.
- **Pas de notification** a la declaration (decision utilisateur : ne pas ralentir ni faire de bruit).
- **Textes affiches** : FR et EN sous `fabrication.outputs.*`, aucun tiret long, point median, fleche, points de suspension typographiques ni emoji ; jetons de couleur seulement ; texte >= 13 px ; cibles >= 44 px ; motif dit par un mot ; bibliotheque `ui/` ; dates locales (`todayLocalISO`, jamais `toISOString`).
- **Migration** : `down_revision = '024_cash_closure'`, SQL brut idempotent comme 023/024 ; verifier `python -m alembic current` puis appliquer sans demander ; jamais de commande destructive. Reporter le DDL dans `ci/schema_only.sql` (bloc ajoute a la main, comme 024).
- **Tests** : base locale Postgres ; lancer pytest avec `REDIS_URL=redis://localhost:16379/0` (Redis de secours sur 16379 tant que le port 6379 est reserve par Windows) ; un seul pytest a la fois ; import de l'application ~2 minutes ; connexion limitee a 5 par minute.
- **Pas de commit sans demande** (regle de l'utilisateur).

## Review Focus

- Deux declarations simultanees qui depassent ensemble `qty_good` (le lot est verrouille avec `_locked_batch` ; test avec deux sessions ou verrou explicite). Tache 2.
- Declaration sur un lot non `termine` (brouillon, en production, expedie, annule) ou apres expedition : 409. Tache 2.
- Annulation d'une sortie deja annulee, ou apres expedition : 409 ; sortie annulee jamais comptee. Tache 2.
- Quantites invalides : 0, negatif, `True`, `2.5`, `"2"`, tres grand ; note `autre` vide ou faite d'espaces. Tache 2.
- Expedition quand toutes les bouteilles sont sorties (rien a expedier) et `ecart_expedie_recu` : la comparaison expedie / recu doit utiliser la quantite reellement expediee, sinon fausse anomalie. Tache 3.
- Reouverture d'un lot avec sorties actives. Tache 3.
- Fuite de droits : roles non prevus 403 sur chaque nouvelle route ; la table des routes est comparee a celles de l'application. Tache 4.
- Une sortie declaree par la mauvaise personne : seul `ProductionManager` ecrit, meme `admin` est refuse en ecriture. Tache 4.

---

## File Structure

| Fichier | Role |
|---|---|
| `alembic/versions/025_fab_batch_outputs.py` | table `fab_batch_outputs`, contraintes, index |
| `models/fabrication.py` (+ `models/__init__.py`) | modele `FabBatchOutput` |
| `utils/fabrication_rules.py` | `validate_output(reason, quantity, note, available)` et motifs |
| `repositories/fabrication_repo.py` | requetes des sorties, somme active, liste recente |
| `controller/fabrication_controller.py` | `declare_output`, `cancel_output`, `list_outputs`, champs derives du lot, expedition, reouverture |
| `api_backend/backend_app/routes/fabrication/` | routes et schemas des sorties |
| `ah2-admin-web/src/services/FabricationGateway.js`, `src/views/modules/fabrication/FabLotDetail.vue`, `FabSuivi.vue`, `src/i18n.js` | ecrans et textes |

---

### Task 1: Migration 025 et modele

**Files:**
- Create: `alembic/versions/025_fab_batch_outputs.py`, `tests/test_fabrication_outputs_schema.py`
- Modify: `models/fabrication.py`, `models/__init__.py`, `ci/schema_only.sql`

**Interfaces:**
- Produces : `FabBatchOutput(id, batch_id FK fab_batches.id, reason 'echantillon'|'autre', quantity int, note text NULL, status 'active'|'annulee' default 'active', declared_by FK users.user_id, declared_at timestamp default utcnow, cancelled_by FK users NULL, cancelled_at NULL, cancel_reason text NULL)`. Contraintes : `quantity > 0`, `reason IN (...)`, `status IN (...)`, `reason <> 'autre' OR length(trim(coalesce(note,''))) > 0`, `status <> 'annulee' OR (cancelled_by IS NOT NULL AND length(trim(coalesce(cancel_reason,''))) > 0)`. Index sur `(batch_id)` et `(status)`.

- [ ] **Step 1: Write the failing tests** : creation d'une sortie valide ; refus (IntegrityError) de `quantity` 0 et negative, `reason` inconnu, `autre` sans note ou avec note d'espaces, `status` inconnu, `annulee` sans motif ou sans `cancelled_by` ; cle etrangere vers un lot inexistant refusee ; le statut par defaut est `active`.
- [ ] **Step 2: Run and verify they fail** : `python -m pytest tests/test_fabrication_outputs_schema.py -v`
- [ ] **Step 3: Implement** la migration (idempotente, downgrade symetrique qui supprime la table), le modele (meme style que `FabBatch`) et le bloc DDL dans `ci/schema_only.sql` (le charger dans une base vide avec `ON_ERROR_STOP` pour verifier).
- [ ] **Step 4: Apply and verify** : `python -m alembic current` puis `upgrade head`, relancer les tests du fichier.

---

### Task 2: Regles, depot et controleur (declarer, annuler, lister)

**Files:**
- Modify: `utils/fabrication_rules.py`, `repositories/fabrication_repo.py`, `controller/fabrication_controller.py`
- Test: `tests/test_fabrication_outputs.py`, ajouts a `tests/test_fabrication_rules.py`

**Interfaces:**
- Consumes : Tache 1 (`FabBatchOutput`) ; `_locked_batch`, `_tx`, `_audit`, `FabricationConflictError` du controleur.
- Produces :
  - `OUTPUT_REASONS = ("echantillon", "autre")` et `validate_output(reason, quantity, note, available: int) -> tuple[str, int, str | None]` (leve `ValueError` avec un message clair ; quantite acceptee : `int` non bool, ou `float` integral converti ; sinon refus).
  - Depot : `FabricationRepository.outputs_of(batch_id, include_cancelled=True) -> list[FabBatchOutput]`, `active_output_total(batch_id) -> int`, `recent_outputs(date_from=None, date_to=None, reason=None, limit=200) -> list[tuple[FabBatchOutput, str]]` (avec le numero de lot), `get_output(output_id, lock=False)`.
  - Controleur : `declare_output(batch_id, reason, quantity, note=None) -> dict`, `cancel_output(batch_id, output_id, reason) -> dict`, `list_outputs(date_from=None, date_to=None, reason=None) -> list[dict]`. Le detail d'un lot (`_batch_d(..., with_detail=True)`) gagne `outputs` (liste, annulees comprises), `qty_outputs` (somme des actives) et `qty_shipped` (`qty_good - qty_outputs`). Erreurs : 409 (`FabricationConflictError`) pour un statut interdit ou un depassement, `ValueError` pour une entree invalide, 404 (`FabricationNotFoundError`) si lot/sortie inconnu.

- [ ] **Step 1: Write the failing tests** : regles pures (`validate_output` : valeurs valides ; 0, -1, `True`, `2.5`, `"2"`, `None` refuses ; `autre` sans note ou avec espaces refuse ; `echantillon` sans note accepte ; note tronquee ou trop longue refusee a 2000 caracteres ; depassement de `available` refuse) ; controleur : declaration sur lot `termine` (champs derives exacts : lot `qty_good=100`, sortie 12 -> `qty_outputs=12`, `qty_shipped=88`), plusieurs sorties cumulees, depassement cumule refuse, declaration refusee pour `brouillon`, `en_production`, `expedie`, `annule` (409), annulation avec motif (la somme active baisse, la ligne reste avec statut `annulee`), annulation sans motif refusee, double annulation 409, annulation apres expedition 409, audit ecrit (CREATE puis CANCEL avec auteur), simultanes : deux sessions qui declarent chacune plus de la moitie du reste, une seule reussit.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** en reutilisant `_tx` et `_locked_batch` (verrou du lot avant de lire la somme active) ; la liste recente trie par date decroissante.
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_fabrication_outputs.py tests/test_fabrication_rules.py tests/test_fabrication_batches.py -q`.

---

### Task 3: Expedition, reouverture et anomalies

**Files:**
- Modify: `controller/fabrication_controller.py` (`ship_batch`, `reopen_batch`), `repositories/fabrication_repo.py` (`shipped_vs_received`, tout calcul qui prend `qty_good` comme quantite expediee)
- Test: `tests/test_fabrication_ship.py` (ajouts), `tests/test_fabrication_anomalies.py` (ajouts)

**Interfaces:**
- Consumes : Tache 2 (`active_output_total`, champs derives).
- Produces : `ship_batch` cree le lot de production avec `quantity_produced = qty_good - sorties actives` ; refus clair ("Toutes les bouteilles sont sorties : rien a expedier.", 422) si le resultat est <= 0 ; `reopen_batch` leve `FabricationConflictError` ("Annulez d'abord les sorties declarees.") s'il existe une sortie active ; la comparaison expedie / recu de `list_anomalies` utilise la quantite reellement expediee (`qty_good - sorties actives` au moment de l'expedition, figee : stocker la quantite expediee dans la reponse de `ship_batch` et dans l'audit).

- [ ] **Step 1: Write the failing tests** : lot de 100 bonnes avec sorties 12 + 3 : le lot de production cree a `quantity_produced == 85` ; sans sortie : 100 (comportement inchange) ; toutes les bouteilles sorties : refus 422 et aucun lot de production cree ; sortie annulee non deduite ; `reopen` refuse avec une sortie active, accepte apres annulation ; anomalie `ecart_expedie_recu` : un lot expedie 85 puis recu 85 n'en produit pas, recu 80 en produit une avec `expedie=85` ; `compute_bilan`/manque/tolerance inchanges (meme valeurs qu'avant pour un lot sans sortie et pour un lot avec sorties).
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** : prendre le verrou du lot (deja fait par `_locked_batch`), lire la somme active, calculer la quantite expediee, la passer a `create_production_lot`, la figer dans la sortie ; l'ecart expedie / recu doit lire cette quantite figee (verifier comment `shipped_vs_received` obtient aujourd'hui la quantite expediee et corriger au plus petit).
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_fabrication_ship.py tests/test_fabrication_anomalies.py tests/test_fabrication_batches.py tests/test_fabrication_outputs.py -q`.

---

### Task 4: Routes, schemas et droits

**Files:**
- Modify: `api_backend/backend_app/routes/fabrication/fabrication_endpoints.py` (+ schemas du dossier)
- Test: `tests/test_fabrication_outputs_endpoints.py`, `tests/test_fabrication_roles.py` (ajouts : nouvelles routes dans la matrice et dans la table comparee)

**Interfaces:**
- Consumes : Tache 2 (controleur).
- Produces : `POST /fabrication/batches/{batch_id}/outputs` (WRITERS, 201, corps `{reason, quantity, note?}`, schema strict `extra=forbid`, `quantity` entier strict), `POST /fabrication/batches/{batch_id}/outputs/{output_id}/cancel` (WRITERS, corps `{reason}`), `GET /fabrication/outputs` (READERS, filtres `date_from`, `date_to`, `reason`), et les champs `outputs`, `qty_outputs`, `qty_shipped` dans `GET /fabrication/batches/{id}`. Identifiants de chemin bornes (`ge=1, le=2**31-1`). Codes : 409 conflit, 422 entree invalide, 404 inconnu, 403 role.

- [ ] **Step 1: Write the failing tests** : declaration HTTP complete (201 puis detail du lot avec les champs derives), annulation, liste filtree par dates et motif, matrice de roles sur les 3 nouvelles routes (ProductionManager ecrit ; promoteur et admin lisent mais obtiennent 403 en ecriture ; secretaire, Assistant, StockController, medecin, nurse, laborantin, ToxicoManager, Psychologist, SpiritualCounsellor et non authentifie : 403/401 partout), table des routes de l'application egale a celle du test de roles, entrees invalides (422, jamais 500), identifiant hors plage 422, une vraie connexion pour verifier le cablage jeton -> role (limite 5 connexions par minute).
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** les routes et schemas sur le modele des routes de lots existantes (meme gestion des erreurs).
- [ ] **Step 4: Run and verify they pass** : `python -m pytest tests/test_fabrication_outputs_endpoints.py tests/test_fabrication_roles.py -q`.

---

### Task 5: Interface : fiche du lot

**Files:**
- Modify: `ah2-admin-web/src/services/FabricationGateway.js`, `src/views/modules/fabrication/FabLotDetail.vue`, `src/i18n.js`
- Create: `ah2-admin-web/tests/fabOutputsContract.test.mjs`

**Interfaces:**
- Consumes : Tache 4 (routes).
- Produces : section "Sorties declarees" dans `FabLotDetail.vue` : liste (motif dit par un mot, quantite, note, auteur, date locale, statut "annulee" visible), formulaire de declaration (motif a deux choix, quantite, note ; visible seulement pour `ProductionManager` quand le lot est `termine`), annulation avec motif obligatoire (confirmation), ligne de bilan "Bouteilles bonnes : N, sorties : M, a expedier : K", bouton d'expedition desactive avec message quand `K <= 0`. Garde in-flight sur chaque action, messages d'erreur visibles. Methodes `declareOutput(batchId, payload)`, `cancelOutput(batchId, outputId, reason)`, `listOutputs(params)` dans la passerelle. Textes sous `fabrication.outputs.*`, FR et EN, memes cles.

- [ ] **Step 1: Write the failing tests** (`fabOutputsContract.test.mjs`) : la passerelle appelle les trois routes avec les bons chemins et corps ; le formulaire n'est visible que pour le role d'ecriture et le statut `termine` ; l'annulation exige un motif ; la ligne "a expedier" lit `qty_shipped` du serveur ; parite FR/EN de `fabrication.outputs.*` ; caracteres interdits ; jetons de couleur seulement ; pas de `toISOString`.
- [ ] **Step 2: Run and verify they fail** : `node --test tests/fabOutputsContract.test.mjs`.
- [ ] **Step 3: Implement** sur le modele des sections existantes de `FabLotDetail.vue` (composants `ui/`).
- [ ] **Step 4: Run and verify they pass** : le fichier ci-dessus puis `node --test tests/fabLotDetailContract.test.mjs tests/fabricationShell.test.mjs`.

---

### Task 6: Suivi, garde-fou de perimetre et documentation

**Files:**
- Modify: `ah2-admin-web/src/views/modules/fabrication/FabSuivi.vue`, `ah2-admin-web/tests/clotureCaisseGuard.test.mjs` (liste des fichiers autorises : ajouter les fichiers Fabrication modifies par ce plan, mention du chantier), `docs/superpowers/SUIVI-AVANCEMENT.md`
- Test: `ah2-admin-web/tests/fabSuiviContract.test.mjs` (ajouts)

**Interfaces:**
- Consumes : Taches 4 et 5.
- Produces : panneau "Sorties declarees recentes" dans `FabSuivi.vue` (lecture seule pour tous les roles lecteurs : lot, motif, quantite, note, auteur, date ; filtres de dates et de motif ; les sorties `autre` mises en evidence par un mot) ; section du suivi d'avancement (livre, decisions : pas d'approbation, sorties = bouteilles bonnes retirees avant expedition, pas de notification, residuels et liste de verification utilisateur : declarer un echantillon, depassement refuse, annulation, expedition avec la quantite reduite, reouverture refusee, role non prevu sans acces).

- [ ] **Step 1: Write the failing tests** : le panneau de `FabSuivi.vue` appelle `listOutputs`, filtre par dates locales, met `autre` en evidence par un texte ; le garde-fou accepte les fichiers prevus et rejette un fichier hors liste.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** le panneau, completer la liste du garde-fou, rediger la section du suivi.
- [ ] **Step 4: Verification finale** : `node --test tests/*.test.mjs`, `npx vite build` (depuis `ah2-admin-web`), puis `python -m pytest tests/test_fabrication_*.py tests/test_cash_*.py -q` ; la suite serveur complete (~20 minutes) est lancee une fois a la fin.
- [ ] **Step 5: Commit** seulement si l'utilisateur le demande.
