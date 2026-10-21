# Réadmission des patients toxico (séjours) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un patient toxico sorti du programme (guérison, abandon, exclusion, autre) peut être **réadmis** sans rien perdre de son historique : même dossier réactivé, phase 1, nouveau psychologue choisi à chaque admission, et une **liste de séjours** qui sépare clairement chaque passage.

**Architecture:** On garde la contrainte « un dossier par patient » (`uq_toxico_patient`) : la réadmission **réactive** le dossier existant. Une nouvelle table `toxico_stays` enregistre chaque séjour (dates, psychologue, substance, motif et note de sortie, qui a sorti) ; `toxico_phase_history` et `toxico_evaluations` reçoivent un `stay_id` nullable (rempli au séjour courant, rempli à 1 pour l'existant). Le motif de sortie devient obligatoire.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic (SQL brut), pytest sur la vraie base de dev ; Vue 3 + vue-i18n + Tailwind.

**Spec:** décisions de l'utilisateur du 2026-10-22 (pas de document séparé) : le patient **repart à la phase 1** ; le **psychologue est choisi à chaque admission** (peut être le même) ; le **motif de sortie** est pris en compte parmi `guerison`, `abandon`, `exclusion`, `autre`. Contexte constaté dans le code : `toxico_dossiers.patient_id` est UNIQUE (`uq_toxico_patient`), `discharge()` (`repositories/toxico_repo.py`) ne fait que `is_active = false`, `create_dossier_after_patient_commit` tente d'insérer un 2e dossier (erreur de contrainte → 500), `relapse_count` n'est incrémenté que par une évaluation `REGRESS`, aucun écran de sortie n'existe côté interface (vérifier), `POST /toxico/discharge/{id}` est réservé à `ToxicoManager` et `admin`.

## Global Constraints

- Motifs de sortie (CHECK en base et validation) : exactement `guerison`, `abandon`, `exclusion`, `autre` ; la note est obligatoire pour `autre`, optionnelle sinon. Libellés FR : Guérison, Abandon, Exclusion, Autre ; EN : Recovery, Dropout, Exclusion, Other.
- Un dossier a **au plus un séjour ouvert** (index unique partiel sur `dossier_id` où `discharge_date IS NULL`) ; `(dossier_id, stay_number)` unique ; `stay_number` commence à 1.
- La réadmission : dossier inactif → `is_active = true`, `admission_date` = nouvelle date, `substance` mise à jour, `psychologist_id` = le psychologue choisi (obligatoire, rôle `Psychologist` actif), `current_phase = 1`, nouveau séjour `stay_number = n+1`, nouvelle ligne `toxico_phase_history` phase 1 (« Réadmission — séjour n »), anciennes évaluations/phases **conservées**. `relapse_count` n'est **pas** modifié par la réadmission (il garde son sens : régressions décidées en évaluation) ; le nombre de séjours donne le nombre de retours. Un dossier **actif** reste refusé (« déjà un dossier actif »).
- Migration 022 : `down_revision` = dernière révision (`021_lab_stock`), SQL brut idempotent, motif de `alembic/versions/019_*.py`/`021_lab_stock.py` ; reporter le DDL dans `ci/schema_only.sql` (fins de ligne du fichier à respecter, édition minimale) ; **remplissage de l'existant** : un séjour 1 par dossier (`admission_date`, `psychologist_id`, `substance` du dossier ; si le dossier est inactif : `discharge_date` = date de `updated_at`, `discharge_reason = 'autre'`, note « Sortie antérieure au suivi des motifs ») et `stay_id` = ce séjour sur toutes les lignes existantes de `toxico_phase_history` et `toxico_evaluations`. Appliquer à la base de dev après vérification de `alembic current`.
- Droits inchangés : sortie = `ToxicoManager` + `admin` ; admission/réadmission = les rôles qui admettent aujourd'hui (voir `toxico_endpoint.py`) ; évaluation = `Psychologist` seul (déjà fait). Contrôle côté serveur, tests de matrice.
- Tests : base de dev partagée, fixtures transactionnelles ; **toute commande pytest sous `timeout 170`** ; au plus 4 connexions par test ; Redis (`ah2_redis`) doit tourner ; disque presque plein. Pas de commit. Toutes les chaînes UI en FR **et** EN (`ah2-admin-web/src/i18n.js`).
- Les statistiques du tableau de bord (`currentMonthAdmissions`, `count_dossiers_created_since`) comptent désormais les **séjours commencés** dans la période (réadmissions comprises) ; le cache Redis `toxico:stats:admissions:AAAA-MM` est invalidé aussi à la réadmission.

## Review Focus

- Réadmettre un patient **actif** → refus clair, rien écrit. Test dans Task 2.
- Double clic / deux réadmissions simultanées du même patient : un seul nouveau séjour (index du séjour ouvert, 409 propre). Test dans Task 2.
- Sortie sans motif, avec motif inconnu, ou `autre` sans note → 422 ; sortie d'un dossier déjà sorti → 409. Test dans Task 2.
- Dossier existant avant la migration (actif et inactif) : séjour 1 correct, historique et évaluations rattachés, aucun doublon si la migration est rejouée. Test dans Task 1.
- Le patient réadmis voit tout son historique (évaluations des séjours précédents) et la liste des séjours dans le bon ordre ; le psychologue choisi à la réadmission est celui du séjour courant. Test dans Task 2 et affichage dans Task 3.

---

### Task 1: Schéma des séjours et remplissage de l'existant

**Files:**
- Create: `alembic/versions/022_toxico_stays.py`
- Modify: `models/toxico.py` (modèle `ToxicoStay`, colonnes `stay_id` sur `ToxicoPhaseHistory` et `ToxicoEvaluation`, relation `ToxicoDossier.stays` triée par `stay_number`), `ci/schema_only.sql`, `models/__init__.py` si nécessaire
- Test: `tests/test_toxico_stays_schema.py`

**Interfaces:**
- Produces : `ToxicoStay(id, dossier_id FK cascade, stay_number, admission_date, psychologist_id FK users NULL, substance, discharge_date NULL, discharge_reason NULL CHECK IN ('guerison','abandon','exclusion','autre'), discharge_note NULL, discharged_by FK users NULL, created_at)` ; contrainte CHECK : `discharge_reason` renseigné ssi `discharge_date` renseigné ; `(dossier_id, stay_number)` unique ; index unique partiel « un séjour ouvert par dossier ». `toxico_phase_history.stay_id` et `toxico_evaluations.stay_id` : FK nullable vers `toxico_stays(id)`. Constante `DISCHARGE_REASONS = ('guerison','abandon','exclusion','autre')` dans `models/toxico.py`.

- [ ] **Step 1: Tests** : CHECK du motif, cohérence date/motif, unicité `(dossier_id, stay_number)`, un seul séjour ouvert par dossier (mais deux dossiers peuvent chacun en avoir un), cascade à la suppression d'un dossier ; **remplissage** : sur des lignes insérées « à l'ancienne » (dossier actif et dossier inactif, avec phases et évaluations) exécuter le SQL de remplissage de la migration (le factoriser dans une fonction/constante SQL testable) et vérifier séjour 1, dates, motif `autre` + note pour l'inactif, `stay_id` rattachés, et qu'un second passage ne crée aucun doublon.
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_toxico_stays_schema.py -q -p no:cacheprovider` — attendu : échec.
- [ ] **Step 3: Écrire** migration, modèles, DDL de `ci/schema_only.sql` ; appliquer `alembic upgrade head` sur la base de dev (vérifier `alembic current` avant) puis contrôler le remplissage de l'existant par SQL.
- [ ] **Step 4: Relancer** Step 2 + `timeout 170 python -m pytest tests/test_toxico_admission.py tests/test_toxico_evaluation_roles.py -q -p no:cacheprovider` — attendu : PASS.

---

### Task 2: Sortie avec motif, réadmission, détail et statistiques

**Files:**
- Modify: `repositories/toxico_repo.py`, `controller/toxico_controller.py`, `api_backend/backend_app/routes/toxico/toxico_endpoint.py`, `.../toxico_schema.py`, `.../toxico_mappping.py` (détail du dossier), éventuellement `repositories/patient_repo.py` si le détail patient/dossier y est assemblé
- Test: `tests/test_toxico_readmission.py`

**Interfaces:**
- Consumes (Task 1) : `ToxicoStay`, `DISCHARGE_REASONS`, `stay_id`.
- Produces : `ToxicoRepository.discharge(dossier_id, reason, note, user_id)` — valide (422 via `ValueError` avec messages ; 409 si déjà sorti : lever une `ValueError` distincte ou une classe dédiée mappée en 409), ferme la phase courante (`_close_current_phase`), ferme le séjour ouvert (`discharge_date`, `discharge_reason`, `discharge_note`, `discharged_by`), `is_active = false`, une seule transaction. `create_dossier_after_patient_commit` devient **admission ou réadmission** : s'il n'existe aucun dossier → création + séjour 1 + phase 1 liés (`stay_id`) ; s'il existe un dossier **inactif** → réadmission (règles des Global Constraints, verrou de ligne sur le dossier, `IntegrityError` du séjour ouvert → 409) ; s'il existe un dossier **actif** → erreur « déjà actif ». `process_evaluation` renseigne `stay_id` (séjour ouvert) sur l'évaluation et sur la nouvelle phase. `POST /toxico/discharge/{dossier_id}` reçoit un corps strict `{reason, note?}` (rôles inchangés). Le détail d'un dossier expose `stays` (liste ordonnée : `stay_number`, `admission_date`, `discharge_date`, `discharge_reason`, `discharge_note`, `discharged_by_name`, `psychologist_name`, `substance`, `is_open`) et `current_stay_number` ; chaque évaluation et chaque ligne d'historique de phase expose son `stay_number`. `count_dossiers_created_since` et le compteur de `get_current_month_admissions_count` comptent les séjours commencés (`ToxicoStay.admission_date`/`created_at` dans la période) et la réadmission invalide le cache Redis. Le contrôleur d'admission accepte le rattachement à un patient existant dont le dossier est inactif (chemin `patient_id`), exige `psychologist_id` à chaque admission, et renvoie au front un indicateur `is_readmission` et le `stay_number`.

- [ ] **Step 1: Tests** (`tests/test_toxico_readmission.py`, contrôleur/dépôt et au moins un test HTTP avec surcharge de dépendances) : cycle complet admission → sortie (`autre` + note) → réadmission : même `dossier.id`, `current_phase = 1`, `is_active`, `relapse_count` inchangé, 2 séjours (le 1er fermé avec son motif, le 2e ouvert avec un autre psychologue), évaluations/phases du séjour 1 intactes et rattachées au séjour 1, nouvelle phase 1 rattachée au séjour 2 ; réadmission d'un dossier actif → refus sans rien écrire ; réadmission en double (second appel après le premier) → refus 409, un seul séjour ouvert ; sortie sans motif / motif inconnu / `autre` sans note → 422 ; double sortie → 409 ; motif de chacun des 4 types accepté ; psychologue absent/inactif ou n'ayant pas le rôle → 422 ; détail du dossier : `stays` ordonnés, `stay_number` sur évaluations et phases, `current_stay_number` ; statistiques : une réadmission du mois compte ; matrice de rôles : sortie = ToxicoManager/admin seulement (200 / 403 pour les autres, dont Psychologist), admission = rôles actuels ; `tests/test_toxico_admission.py` et `tests/test_toxico_evaluation_roles.py` restent verts.
- [ ] **Step 2: Lancer** `timeout 170 python -m pytest tests/test_toxico_readmission.py -q -p no:cacheprovider` — attendu : échec.
- [ ] **Step 3: Implémenter** ; réutiliser les patrons existants du module (transactions avec rollback, audit si le module en utilise).
- [ ] **Step 4: Relancer** Step 2 + `timeout 170 python -m pytest tests/test_toxico_admission.py tests/test_toxico_evaluation_roles.py tests/test_stockcontroller_deny.py -q -p no:cacheprovider` — attendu : PASS.

---

### Task 3: Interface — sortie avec motif, réadmission et séjours

**Files:**
- Modify: `ah2-admin-web/src/services/ToxicoGateway.js`, `ah2-admin-web/src/stores/toxicoStore.js`, `ah2-admin-web/src/views/modules/toxico/ToxicoList.vue` (action « Sortie » pour `ToxicoManager`/`admin`, indication « réadmission » à l'admission), le formulaire/modal d'admission toxico existant, la vue détail du dossier, `ah2-admin-web/src/i18n.js`
- Create: `ah2-admin-web/src/components/toxico/ToxicoDischargeModal.vue`, `ah2-admin-web/src/components/toxico/ToxicoStaysTimeline.vue`, `ah2-admin-web/src/utils/toxicoStays.js`
- Test: `ah2-admin-web/tests/toxicoStays.test.mjs`

**Interfaces:**
- Consumes (Task 2) : `POST /toxico/discharge/{id}` `{reason, note?}`, détail dossier avec `stays`, `current_stay_number`, `stay_number` par évaluation/phase, réponse d'admission avec `is_readmission` et `stay_number`.
- Produces : `utils/toxicoStays.js` — `DISCHARGE_REASONS`, `dischargeReasonLabelKey(reason)` (clé i18n, repli sûr pour valeur inconnue), `validateDischarge({reason, note})` (motif obligatoire, note obligatoire si `autre`) → clés d'erreur, `groupByStay(items, stays)` (évaluations/phases regroupées par séjour dans l'ordre chronologique, éléments sans séjour dans un groupe « ancien »). `ToxicoDischargeModal` : choix du motif (4 options), note, validation côté client, bouton verrouillé pendant l'appel, erreurs 409/422 lisibles. `ToxicoStaysTimeline` : un bloc par séjour (« Séjour n · du … au … · Guérison/Abandon/Exclusion/Autre · psychologue »), le séjour en cours marqué, évaluations et phases de chaque séjour dessous ; **mise en page téléphone/tablette/PC soignée** (cartes empilées sous `md`). À l'admission : si le patient rattaché possède un dossier inactif, bandeau « Patient déjà suivi — réadmission, séjour n+1 » et rappel que la phase repart à 1 ; le choix du psychologue reste obligatoire.

- [ ] **Step 1: Test node** : `validateDischarge`, `dischargeReasonLabelKey` (4 motifs + inconnu), `groupByStay` (plusieurs séjours, élément sans séjour) — lancer `node --test ah2-admin-web/tests/toxicoStays.test.mjs` — attendu : échec.
- [ ] **Step 2: Implémenter** utilitaires, composants, branchements, i18n FR+EN ; l'action « Sortie » n'apparaît que pour `ToxicoManager` et `admin` et seulement sur un dossier actif.
- [ ] **Step 3: Vérifier** `node --test ah2-admin-web/tests/*.test.mjs` et `cd ah2-admin-web && npx vite build` (en dernier) — attendu : PASS. Rendu réel laissé à l'utilisateur.
