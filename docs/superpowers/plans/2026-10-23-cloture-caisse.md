# Cloture de caisse : compter l'argent reel, chaque jour : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chaque jour, la caisse est comptee a l'aveugle par mode de paiement, comparee a l'attendu (ouverture + entrees - sorties), figee, notifiee au promoteur et a l'admin, et cloturee automatiquement a 23 h si personne ne l'a fait.

**Architecture:** Un module isole `cash_closure` (migration, modeles, regles pures, depot qui ne commit jamais, controleur qui possede la transaction, routeur a gardes explicites) sur le modele du module Fabrication. Les periodes se calculent sur une nouvelle colonne `received_at timestamptz` posee par la base sur les paiements echelonnes et les retraits. Cote navigateur : passerelle, store, un ecran de cloture pour la secretaire (menu secretariat), un ecran de lecture et de decision pour promoteur/admin, enregistrement du type de notification.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic (SQL brut idempotent), pytest ; Vue 3 `<script setup>`, PowerSync (retrait), vue-i18n 11, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-23-cloture-caisse-design.md` (binding). Faits du code actuel : `.superpowers/recon-cloture-caisse.md` (lire avant toute tache qui touche caisse, retrait ou notifications).

## Global Constraints

- **Ecrans/endpoints existants modifies : seulement** (a) retrait : mode obligatoire (liste officielle) ; (b) formulaires de facture (`CaisseInvoiceModal.vue`) et de paiement echelonne (`CaisseInstallmentModal.vue`) : choix = liste officielle ; (c) enregistrements (menu, routes, i18n, cloche) ; (d) correction de `/settle` et de `PUT /caisse/{id}` si atteignables depuis l'ecran actuel (tache 7). Tout autre changement est un defaut.
- **Liste officielle des modes** (codes stables) : `especes` (libelle Especes, regroupe « Cash », « Espèces », « Especes » sans casse ni accent), `orange_money`, `mtn_money`, `autre_mobile` (regroupe « Mobile Money » et tout nouvel operateur). Table `payment_modes` modifiable par l'admin : desactiver, jamais supprimer. Virement/Cheque ne sont plus proposes.
- **Entrees d'une periode, par mode** : somme de `paiement_echelonne.paid_amount` dont `received_at` est dans `[t0, t1)`, groupee par mode normalise du paiement ; JAMAIS `caisse.advance_amount` (cache de la meme somme : double compte) et JAMAIS les KPI existants de la caisse. Plus : `consultation_spirituel.fr_amount_paid` (tache 8), plus les retraits annules dans la periode mais recus avant (argent rendu au tiroir).
- **Sorties d'une periode, par mode** : retraits actifs dont `received_at` est dans `[t0, t1)` ; plus, pour une vente annulee dans la periode (`caisse.cancelled_at`, UTC naif), la somme de ses paiements echelonnes, aux modes de ces paiements, motif « vente annulee » + justification de l'annulation. Les ventes `pending_approval` ne comptent pas.
- **Periodes chainees** : `[fin de la cloture precedente, moment de la cloture)`, sans trou ni chevauchement. Une cloture manuelle a `period_end = now()` ; une cloture automatique pose `period_end` a 23:00 du jour concerne, heure `Africa/Douala` (fuseau fixe, `zoneinfo`, ajouter `tzdata` aux dependances).
- **Especes** : solde d'ouverture = compte de la cloture precedente (ou attendu si elle etait automatique, avec marqueur), attendu = ouverture + entrees - sorties, compte saisi par la secretaire. **Modes mobiles** : pas de solde d'ouverture ; attendu = entrees - sorties du jour ; la secretaire saisit le total releve chez l'operateur.
- **A l'aveugle** : le serveur ne renvoie ni attendu ni totaux par mode avant la validation du comptage ; apres validation, il renvoie tout ; un comptage valide n'est jamais modifie. Ecart non nul sur un mode : commentaire obligatoire (non vide apres espaces).
- **Une cloture validee est immuable** (trigger ou garde du depot). Corrections = enregistrements de regularisation separes (table propre), approuves par promoteur/admin, sans modifier la cloture d'origine ni le solde d'ouverture suivant.
- **Roles** : `secretaire` cloture ; `promoteur` et `admin` lisent toutes les clotures, decident les corrections, l'admin gere la liste des modes ; tout autre role : 403. Les routes caisse/retrait existantes restent `secretaire`/`admin` (le promoteur n'y est pas : ne pas les elargir, creer des routes propres).
- **Notifications** : une par destinataire (promoteur + chaque admin actif, copier `LabStockRepository.active_user_ids_with_roles`) et par cloture, type `cash_closure`, payload attendu/compte/ecart/auto ; l'anomalie est un marqueur sur la meme notification. Le depot de notifications doit etre cable dans la fabrique du controleur et teste par HTTP.
- **Aucun planificateur n'existe** : cloture automatique rattrapee a la premiere lecture/connexion apres 23 h (jours manques fermes un par un a leur 23 h) + script CLI pour cron. Unicite et verrou contre la double cloture.
- **Texte affiche** : FR et EN sous `cashClosure.*`, aucun tiret long, point median, fleche, points de suspension typographiques ni emoji ; jetons de couleur seulement ; texte >= 13 px ; cibles >= 44 px ; ecart dit par un mot et pas par la couleur seule ; bibliotheque `ui/`.
- **Pas de commit sans demande.** Migrations : verifier `alembic current` puis appliquer sans demander ; ne jamais lancer de commande destructive.

## Review Focus

- **Double compte / compte manquant** d'un paiement ou d'un retrait dans l'attendu d'un mode (avance ecrite a la fois dans la vente et dans le paiement ; vente avec et sans lignes de paiement). Tache 3.
- **Attendu visible avant validation** ou comptage modifiable apres affichage. Tache 5.
- **Double cloture** (manuelle + automatique, deux onglets, deux secretaires) et jour sans aucune cloture apres une panne. Taches 4 et 5.
- **Operation hors ligne synchronisee apres la cloture** : tombe dans la periode suivante sans changer la cloture figee ; cloture manuelle refusee tant qu'il reste des operations non synchronisees sur le poste. Taches 3 et 9.
- **Annulation d'une vente deja cloturee / retrait annule apres cloture** : sortie ou rentree dans la periode de l'annulation, cloture d'origine intacte. Tache 3.
- **Retrait ou vente d'un ancien mode** (Virement, Cheque, Mobile Money, valeur vide) recu de la file de synchronisation : normalise et jamais rejete par un 400 qui bloquerait la file. Tache 6.
- **Fuite de droits** : un role non prevu obtient 403 ; la secretaire ne voit jamais l'attendu avant validation par un autre chemin (liste, detail, notification). Tache 5.

---

## File Structure

| Fichier | Role |
|---|---|
| `alembic/versions/024_cash_closure.py` | `payment_modes`, `cash_closures`, `cash_closure_lines`, `cash_closure_corrections`, colonne `received_at` sur `paiement_echelonne` et `caisse_retrait`, immuabilite |
| `models/cash_closure.py` | `PaymentMode`, `CashClosure`, `CashClosureLine`, `CashClosureCorrection` |
| `utils/cash_rules.py` | modes (normalisation), periodes et limites de 23 h, calcul des lignes, ecart |
| `repositories/cash_closure_repo.py` | requetes d'entrees/sorties, creation, verrou, lecture ; ne commit jamais |
| `controller/cash_closure_controller.py` | cas d'usage, transaction, audit, notifications |
| `api_backend/backend_app/routes/cash_closure/` | `cash_closure_endpoints.py`, `cash_closure_schemas.py`, `__init__.py` |
| `scripts/cash_closure_catchup.py` | CLI de rattrapage (cron) |
| `ah2-admin-web/src/services/CashClosureGateway.js`, `src/stores/cashClosureStore.js`, `src/views/modules/caisse/CashClosure.vue`, `src/views/modules/caisse/CashClosuresReview.vue` | ecrans et acces |

---

### Task 1: Migration, colonnes de reception et modeles

**Files:**
- Create: `alembic/versions/024_cash_closure.py`, `models/cash_closure.py`, `tests/test_cash_closure_schema.py`
- Modify: `models/__init__.py`, `ci/schema_only.sql` (regenerer en suivant la procedure du recon §7 : diff avant d'ecraser), `models/retrait.py` et `models/paiement_echelonne.py` (declarer `received_at` en lecture seule, sans toucher aux defauts existants)

**Interfaces:**
- Produces : `PaymentMode(code PK, label, is_active, sort_order)` seed des 4 codes ; `CashClosure(id, period_start, period_end, business_date, kind 'manual'|'auto', closed_by NULL pour auto, closed_at, opening_cash, expected_cash, counted_cash NULL, difference NULL, opening_from_auto bool, comment, unsynced_ignored bool)` ; `CashClosureLine(id, closure_id, mode_code, source 'physical'|'operator_statement', opening, entries, exits, expected, counted NULL, difference NULL, comment)` ; `CashClosureCorrection(id, closure_id, mode_code, amount_delta, reason, status pending|approved|rejected, requested_by, decided_by, decided_at)` ; `paiement_echelonne.received_at` et `caisse_retrait.received_at` `timestamptz NOT NULL DEFAULT now()` (rempli pour l'historique : `payment_date AT TIME ZONE 'Africa/Lagos'`, `retrait_at AT TIME ZONE 'UTC'`).

- [ ] **Step 1: Write the failing tests** : `test_received_at_defaults_to_now_on_insert` (retrait et paiement inseres sans la colonne ont `received_at` proche de now) ; `test_backfill_uses_correct_timezones` (SQL de remplissage applique a des lignes existantes simulees) ; CHECK : `counted` negatif refuse, `kind` inconnu refuse, `period_end <= period_start` refuse ; unicite : deux clotures de meme `period_end` refusees ; immuabilite : `UPDATE cash_closures SET counted_cash=...` apres insertion leve `IntegrityError` / exception du trigger (sauf champ de mise a jour interdit) ; seed : les 4 codes existent, `especes` actif.
- [ ] **Step 2: Run and verify they fail**
- [ ] **Step 3: Implement migration 024** (`down_revision='023_fabrication'`, SQL brut idempotent comme 019/023 ; trigger `BEFORE UPDATE OR DELETE` qui refuse toute modification des clotures et lignes validees ; downgrade symetrique ne supprimant pas les colonnes `received_at` si des donnees existent est inutile : les retirer proprement) et les modeles ; reporter le DDL dans `ci/schema_only.sql` ; ajouter les 4 modes via la migration ET un fichier de seed CI `ci/seed_payment_modes.sql` charge par le workflow si necessaire (le CI charge schema_only puis seed roles seulement : verifier et completer `ci.yml`).
- [ ] **Step 4: Apply and verify** : `python -m alembic current`, `upgrade head`, puis les tests du fichier.

---

### Task 2: Regles pures

**Files:**
- Create: `utils/cash_rules.py`, `tests/test_cash_rules.py`
- Modify: `requirements*.txt` (ajouter `tzdata`)

**Interfaces:**
- Produces :
  - `normalize_mode(raw: str | None) -> str | None` : code officiel, `None` si vide, `'autre_mobile'` pour « Mobile Money » ou texte contenant « mobile », `'non_classe'` pour une valeur inconnue non vide ; insensible a la casse et aux accents (« Espèces », « especes », « Cash » donnent `especes`, « Virement »/« Chèque » donnent `non_classe`).
  - `closing_time_for(day: date) -> datetime` (timestamptz 23:00 `Africa/Douala`) ; `overdue_days(last_period_end, now) -> list[date]` (jours dont le 23:00 est passe sans cloture, du plus ancien au plus recent).
  - `compute_line(mode, opening, entries, exits, counted) -> dict` : Decimal ; `expected = opening + entries - exits` pour `especes`, `entries - exits` pour les modes mobiles (opening ignore) ; `difference = counted - expected` ou `None`.
  - `require_comment_if_gap(lines) -> None` : leve `ValueError` si un ecart non nul n'a pas de commentaire non vide apres espaces.

- [ ] **Step 1: Write the failing tests** : normalisation (tous les textes reels vus : Espèces, Especes, Cash, Mobile Money, MTN Money, Orange Money, Virement, Chèque, vide, `None`, casse/accents) ; `closing_time_for(date(2026,10,23))` vaut 22:00 UTC ; `overdue_days` (une panne de 3 jours ; aucun retard avant 23:00 ; exactement 23:00) ; `compute_line` especes `100 + 50 - 30 = 120`, mobile ignore `opening`, ecart `-5`, `0.1 + 0.2` exact ; commentaire obligatoire pour ecart non nul, accepte pour ecart nul sans commentaire.
- [ ] **Step 2: Run and verify they fail** : `python -m pytest tests/test_cash_rules.py -v`
- [ ] **Step 3: Implement** en `Decimal` (jamais `float`), fonctions pures sans acces base.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 3: Requetes d'entrees et de sorties (le calcul de l'attendu)

**Files:**
- Create: `repositories/cash_closure_repo.py`, `tests/test_cash_flows.py`

**Interfaces:**
- Consumes : tache 1 (colonnes), tache 2 (`normalize_mode`).
- Produces : `CashClosureRepository(session)` avec `flows(t0, t1) -> dict[str, {"entries": Decimal, "exits": Decimal, "detail": {...}}]` par code de mode normalise (y compris `non_classe`), `cancellations(t0, t1) -> list[dict]` (auteur, montant, justification, vente), `last_closure() -> CashClosure | None`, `pending_unsynced`: hors depot (voir tache 9). Le depot ne commit jamais.

- [ ] **Step 1: Write the failing tests** (via `create_test_transaction`, `create_test_retrait`, et insertion directe de `received_at`) : avance a la creation d'une vente comptee UNE fois (jamais deux : `advance_amount` + ligne de paiement) ; vente avec avance puis versement un autre jour et un autre mode : chaque somme dans sa periode et son mode ; vente `pending_approval` exclue ; retrait actif en sortie, retrait annule dans la meme periode : ni sortie ni rentree, retrait annule apres une periode precedente : rentree dans la periode de l'annulation ; vente annulee dans la periode : sortie egale a la somme de ses paiements, aux modes de ces paiements, avec justification ; vente annulee puis nouvelle facture : les deux se compensent ; mode inconnu (`Virement`) : compartiment `non_classe` ; bornes `[t0, t1)` incluses a gauche, exclues a droite ; ancienne vente de 2025 avec avance et sans ligne de paiement : jamais comptee.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** les requetes (SQLAlchemy Core ou ORM, un seul passage par table). Les colonnes `cancelled_at` (UTC naif) se convertissent avec `AT TIME ZONE 'UTC'`.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 4: Cloture manuelle et automatique, notifications

**Files:**
- Create: `controller/cash_closure_controller.py`, `tests/test_cash_closure_controller.py`
- Modify: `repositories/cash_closure_repo.py`

**Interfaces:**
- Consumes : taches 2 et 3.
- Produces : `CashClosureController(repo, audit_repo, notification_repo, current_user)` avec :
  - `status() -> dict` : etat de la periode en cours sans aucun total (`last_closed_at`, `overdue_days`, `modes` actifs).
  - `submit(counts: list[{"mode": str, "counted": Decimal, "comment": str | None}]) -> dict` : refuse (409) tant qu'une cloture automatique en retard n'est pas rattrapee d'abord ; calcule, verifie les commentaires, cree la cloture `manual` avec `period_end=now()`, notifie, renvoie le detail revele.
  - `auto_close_overdue(now: datetime) -> list[dict]` : ferme chaque jour manque a son 23:00, du plus ancien au plus recent, cloture `auto` (`counted=None`, `opening_from_auto` du suivant = vrai) ; notifie ; idempotente.
  - `get(id)`, `list(filters)` : lecture complete pour promoteur/admin.
  - Verrou : `SELECT ... FOR UPDATE` sur une ligne de controle (ou unicite `period_end`) ; une deuxieme cloture simultanee echoue proprement (409).

- [ ] **Step 1: Write the failing tests** : une cloture manuelle correcte (ouverture 0, entrees/sorties reelles, comptage exact, ecart 0) ; ecart sans commentaire refuse (422) puis accepte avec commentaire ; mode inconnu ou inactif dans le comptage refuse ; tous les modes actifs attendus ; solde d'ouverture = compte de la veille ; apres une cloture auto, ouverture = attendu et `opening_from_auto` ; double soumission : seconde en 409, une seule cloture en base ; panne de 3 jours : `auto_close_overdue` cree 3 clotures a 22:00 UTC de chaque jour, dans l'ordre, rien a recreer au second appel ; notifications : une par destinataire (promoteur + chaque admin actif, aucun autre role), payload sans fuite superflue, marqueur `auto` ; **test par HTTP dans la tache 5** que le depot de notifications est reellement cable ; audit ecrit.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** : le controleur possede la transaction (meme `_tx` que `FabricationController`), le depot ne commit jamais. Une cloture manuelle calcule `t1 = now()` apres avoir pris le verrou.
- [ ] **Step 4: Run and verify they pass.**

---

### Task 5: Endpoints, droits et comptage a l'aveugle

**Files:**
- Create: `api_backend/backend_app/routes/cash_closure/{__init__,cash_closure_endpoints,cash_closure_schemas}.py`, `tests/test_cash_closure_endpoints.py`, `tests/test_cash_closure_roles.py`
- Modify: `api_backend/backend_app/main.py` (enregistrer le routeur, commentaire du prefixe)

**Interfaces:**
- Produces : `GET /cash-closure/status` (secretaire), `POST /cash-closure` (secretaire, corps `{counts:[{mode, counted, comment?}]}` en chaines Decimal), `GET /cash-closure/{id}` et `GET /cash-closure` (secretaire : seulement ses clotures deja validees et seulement apres validation ; promoteur/admin : toutes), `POST /cash-closure/catchup` (secretaire, promoteur, admin : appelle `auto_close_overdue`), `GET/POST/PUT /payment-modes` (lecture : secretaire/promoteur/admin ; ecriture : admin), `POST /cash-closure/{id}/corrections` (secretaire), `GET /cash-closure/corrections` et `POST /cash-closure/corrections/{id}/decide` (promoteur, admin). Chaque route a sa garde `role_required` ; le catch-up est aussi appele par la lecture/connexion (tache 9) et le script CLI (tache 10).

- [ ] **Step 1: Write the failing tests** : `GET /status` ne contient ni attendu ni total par mode (parcourir recursivement la reponse : aucune cle `expected*`, `entries`, `exits`, `opening`) ; `POST` renvoie ensuite les montants reveles ; la meme cloture n'est plus modifiable (aucune route PUT, 405/404) ; une secretaire ne peut pas lire l'attendu d'une cloture avant validation (la periode ouverte n'a pas d'id) ; matrice de roles complete (secretaire, promoteur, admin accedent ce qui leur est prevu ; Assistant, StockController, ProductionManager, medecin, nurse, laborantin, ToxicoManager, Psychologist, SpiritualCounsellor, non authentifie : 403/401 partout), table de routes comparee a celles de l'application (egalite, comme `test_fabrication_roles.py`) ; notifications creees reellement par HTTP pour promoteur et admin ; deux vraies connexions (limite 5 par minute) pour le cablage jeton vers role.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** routes, schemas strictes (`extra=forbid`, Decimal en chaines, pas de `float`), fabrique avec `notification_repo` et `audit_repo` cables (verifier que `get_*_controller` les passe).
- [ ] **Step 4: Run and verify they pass**, plus la regression ciblee `tests/test_caisse.py tests/test_retrait.py tests/test_notifications.py` (aucun fichier existant modifie hors tache 6).

---

### Task 6: Liste officielle des modes et mode obligatoire des retraits

**Files:**
- Modify: `api_backend/backend_app/routes/retrait/retrait_endpoints.py`, `controller/caisse_retrait_controller.py`, endpoints et schemas de creation de vente et de paiement echelonne (`routes/caisse/caisse_schemas.py`, `caisse_endpoints.py`), `tests/test_retrait.py`, `tests/test_caisse.py` (ajouts seulement ; fixtures `create_test_retrait` mises a jour pour fournir un mode)
- Create: `tests/test_payment_modes.py`

**Interfaces:**
- Consumes : `normalize_mode`.
- Produces : un retrait neuf SANS mode (absent, `null`, vide) est refuse (422) ; un mode ancien (« Mobile Money », « Virement », « Chèque », « Cash », « Espèces ») est normalise vers un code officiel (ou `non_classe`), jamais rejete ; meme normalisation pour `caisse.payment_method` et `paiement_echelonne.payment_method` a l'ecriture ; les valeurs stockees deviennent les codes officiels pour les nouvelles ecritures ; l'API de sortie des retraits garde son mapping d'affichage actuel (null → « Espèces » ne s'applique plus aux nouvelles lignes).

- [ ] **Step 1: Write the failing tests** : retrait sans mode → 422 ; avec chacun des 4 codes → 201 et code stocke ; avec « Virement » / « Mobile Money » → 201 normalise (pas de 400) ; vente et paiement echelonne : meme normalisation ; ancien test de retrait sans mode corrige pour fournir un mode (c'est le seul changement de ces anciens tests) ; admin desactive un mode puis une vente dans ce mode est refusee (422) mais un ancien paiement dans ce mode reste lisible.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement** en gardant l'endpoint synchrone de `DossierConnector` compatible (aucun 400 sur une valeur ancienne). Mentionner dans le rapport chaque fichier existant touche.
- [ ] **Step 4: Run and verify they pass**, et la suite `tests/test_retrait.py tests/test_caisse*.py tests/test_discount*.py tests/test_finance_ledger.py` sans nouvel echec.

---

### Task 7: Chemins qui contournent les paiements

**Files:**
- Modify (seulement si le defaut est reel) : `repositories/caisse_repo.py`, `routes/caisse/caisse_endpoints.py` ; Create : `tests/test_caisse_payment_integrity.py`

**Interfaces:** Produces : l'invariant « tout argent encaisse apres la mise en service a une ligne `paiement_echelonne` » ; sinon rapport precis des routes atteignables depuis l'ecran actuel (`ah2-admin-web`, grep des appels).

- [ ] **Step 1: Investigate and write failing tests** : prouver par grep et par test si `POST /caisse/{id}/settle` et `PUT /caisse/{id}` (champs `advance_amount`, `paid_at`) sont appeles par l'interface actuelle ou par la synchronisation hors ligne ; si oui, ecrire des tests montrant qu'une modification du montant paye ne cree pas de ligne de paiement (defaut) ; si non atteignables, un test documentant qu'elles sont refusees ou ignorees pour `advance_amount`.
- [ ] **Step 2: Run and verify** (rouge seulement si defaut reel).
- [ ] **Step 3: Implement le plus petit correctif** : `settle` ecrit une ligne `SOLDE` ; `PUT` ne peut plus changer `advance_amount` ni `paid_at` d'une vente deja encaissee. Annoncer le changement dans le rapport.
- [ ] **Step 4: Run and verify they pass**, plus `tests/test_caisse*.py`.

---

### Task 8: Entree des consultations spirituelles

**Files:** Modify `repositories/cash_closure_repo.py` ; Test `tests/test_cash_flows.py`

**Interfaces:** Produces : `fr_amount_paid` des consultations spirituelles compte comme entree en especes sur la periode ou la ligne a ete enregistree.

- [ ] **Step 1: Investigate** : trouver la table `consultation_spirituel`, comment `fr_amount_paid` est ecrit (une fois ? mis a jour ?), et quelle heure serveur fiable existe (`created_at`/`updated_at`). Si aucune heure fiable ni regle claire (montant modifiable apres coup), s'arreter avec `NEEDS_CONTEXT` en decrivant le probleme au lieu d'inventer.
- [ ] **Step 2: Write the failing tests** : un montant paye cree dans la periode est une entree especes ; un montant modifie plus tard n'altere pas une cloture figee (compte une seule fois, au moment de la saisie).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and verify they pass.**

---

### Task 9: Passerelle, store et ecran de cloture de la secretaire

**Files:**
- Create: `ah2-admin-web/src/services/CashClosureGateway.js`, `src/stores/cashClosureStore.js`, `src/views/modules/caisse/CashClosure.vue`, `tests/cashClosureShell.test.mjs`, `tests/cashClosureContract.test.mjs`
- Modify: `router/index.js` (route `/secretariat/cloture`, role secretaire), `src/layouts/SecretaireLayout.vue` (entree de menu), `src/i18n.js`, `RetraitModal.vue`, `CaisseInvoiceModal.vue`, `CaisseInstallmentModal.vue` (modes de la liste officielle, via un petit module `src/utils/paymentModes.js` nourri par `GET /payment-modes` avec repli sur la liste figee hors ligne), `NotificationBell.vue` (type `cash_closure` : libelle, route de clic, i18n `notifications.*`), `tests/retraitContract.test.mjs` (mis a jour a la liste), guards existants si besoin (jamais affaiblis)

**Interfaces:** Produces : l'ecran affiche d'abord la liste des ventes de la secretaire (existante, lien) et un formulaire de comptage par mode (especes compte, modes mobiles « total du releve operateur ») SANS aucun total du systeme ; apres validation, le tableau par mode (ouverture, entrees, sorties, attendu, compte, ecart en mots) et la liste des annulations de la journee ; **bouton de validation desactive et message tant que des operations locales sont en attente de synchronisation** (utiliser le compteur de file de PowerSync, `uploadQueueStats`/equivalent ; hors ligne la cloture est indisponible) ; appel du rattrapage a l'ouverture de l'ecran.

- [ ] **Step 1: Write the failing tests** (contrat, TDD) : `GET /cash-closure/status` n'est pas confondu avec la revelation ; aucune cle d'attendu n'est lue avant la validation ; le bouton est inactif tant que la file de synchro n'est pas vide ; commentaire obligatoire pour ecart non nul ; chaque nouveau mode apparait dans les trois formulaires ; plus de Virement/Cheque ; textes FR/EN identiques, caracteres interdits, couleurs, taille ; `NotificationBell.vue` connait `cash_closure`.
- [ ] **Step 2: Run and verify they fail** : `node --test tests/cashClosureContract.test.mjs`.
- [ ] **Step 3: Implement** l'ecran avec `ui/` (modele : `views/modules/finance/CaisseList.vue`, `RetraitList.vue`), le store (pas d'ecriture PowerSync : la cloture est en ligne seulement), les trois formulaires, la cloche, le menu et l'i18n.
- [ ] **Step 4: Run and verify they pass**, `node --test tests/*.test.mjs`, `npx vite build`.

---

### Task 10: Ecran promoteur/admin, corrections et script de rattrapage

**Files:**
- Create: `ah2-admin-web/src/views/modules/caisse/CashClosuresReview.vue`, `scripts/cash_closure_catchup.py`, `tests/cashClosureReviewContract.test.mjs`, `tests/test_cash_closure_cli.py`
- Modify: `router/index.js` (`/dashboard/cash-closures`, roles promoteur+admin), `MainLayout.vue` (menu), `src/i18n.js`, `CashClosureGateway.js`

**Interfaces:** Produces : liste filtrable par dates (debut/fin) et par etat (auto/manuelle, avec ecart) ; detail par mode (ouverture, entrees, sorties, attendu, compte, ecart, commentaire, annulations) ; les clotures « non declarees » en evidence ; decision des corrections (promoteur/admin, mot de passe non requis ici) ; gestion de la liste des modes (admin) ; script `python scripts/cash_closure_catchup.py` appelle `auto_close_overdue(now)` via `SessionLocal`, journalise et sort avec un code non nul en cas d'erreur.

- [ ] **Step 1: Write the failing tests** : contrat (filtres de dates locales sans `toISOString`, ecart en mots, lecture seule sauf decision et liste des modes pour admin) ; CLI : appele deux fois ne cree qu'une cloture par jour manque, retour 0 ; erreur de base : code non nul.
- [ ] **Step 2: Run and verify they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and verify they pass**, `npx vite build`.

---

### Task 11: Garde-fou, suivi d'avancement et verification finale

**Files:**
- Create: `ah2-admin-web/tests/clotureCaisseGuard.test.mjs`
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`

**Interfaces:** Produces : garde-fou sur le modele de `refonteFabricationGuard.test.mjs` : aucune couleur brute, texte >= 13 px, caracteres interdits, usage de `ui/`, parite FR/EN de `cashClosure.*`, aucun `toISOString` dans les nouveaux ecrans, et PERIMETRE : `git diff --name-only BASE -- ah2-admin-web` limite aux fichiers prevus (listes de la tache 9 et 10 + tests) avec `BASE` = dernier commit avant ce chantier et `FIN = null` jusqu'au commit.

- [ ] **Step 1: Write the failing test**, voir qu'il echoue sur un fichier hors liste simule.
- [ ] **Step 2: Implement le garde-fou** puis la section du suivi : livre, decisions (liste officielle, vente annulee = sortie, periodes sur heure de reception, rattrapage sans planificateur, aveugle puis revelation, immutabilite), residuels (planificateur reel au chantier 8 ; fuseau du conteneur ; modes mobiles sans solde reporte), liste de verification utilisateur (cloture a l'aveugle avec un ecart, cloture automatique d'un jour oublie, retrait sans mode refuse, vente annulee puis reprise, operation hors ligne puis cloture, notifications promoteur et admin, un compte non prevu n'a ni menu ni acces).
- [ ] **Step 3: Verification finale** : `node --test tests/*.test.mjs`, `npx vite build`, `python -m pytest tests/test_cash_*.py tests/test_payment_modes.py tests/test_caisse*.py tests/test_retrait.py tests/test_notifications.py tests/test_discount*.py tests/test_finance_ledger.py -q` ; la suite complete (~12 minutes) est lancee une fois a la fin.
- [ ] **Step 4: Commit** seulement si l'utilisateur le demande ; renseigner alors `FIN` dans un commit separe.
