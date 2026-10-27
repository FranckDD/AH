# Psychologues : vue limitee et transfert d'un patient : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L'admin peut limiter un psychologue a ses seuls patients de toxicologie, l'admin et le responsable de toxicologie peuvent transferer un patient d'un psychologue a un autre avec un motif obligatoire, et seul le psychologue referent peut evaluer.

**Architecture:** Un booleen `users.sees_own_toxico_only` (modele `is_head_nurse`) devient un `ToxicoScope` construit une seule fois par `ToxicoController` ; un unique filtre `ToxicoRepository.scope_clause(scope)` est applique par toutes les requetes de liste, de stats, d'export et de detail, plus un calcul d'acces `full / readonly / none` pour les acces directs. Un transfert est une ligne de la nouvelle table `toxico_psychologist_transfers` ecrite avec le changement de referent (dossier + sejour ouvert) et la notification dans une seule transaction du depot. Le front ajoute la case dans la fiche du compte, le bouton et la fenetre de transfert, l'onglet lecture seule et les entrees d'historique.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic (SQL brut idempotent), WeasyPrint ; Vue 3 `<script setup>`, Pinia, vue-i18n 11, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-27-psychologues-vue-limitee-transfert-design.md` (approuve le 2026-10-27, binding). Code a lire : `repositories/toxico_repo.py`, `controller/toxico_controller.py`, `api_backend/backend_app/routes/toxico/toxico_endpoint.py` et `toxico_schema.py`, `controller/patient_dossier_controller.py`, `controller/hospitalization_controller.py::_notify_team_of_aggravation` (motif de notification, mais le transfert ne l'avale pas), `alembic/versions/016_nurse_shifts.py` et `tests/test_users_update.py` (parcours `is_head_nurse`), `tests/test_stock_count_roles.py` (table de routes derivee de l'application).

## Global Constraints

- **Reglage** : colonne `users.sees_own_toxico_only boolean NOT NULL DEFAULT false` ; version simple uniquement (pas de liste de patients ou de psychologues autorises) ; par defaut desactive = comportement actuel ; ignore pour tout role autre que `Psychologist` (comme `is_head_nurse` hors infirmier).
- **Referent** : `toxico_dossiers.psychologist_id` ; le transfert change le referent du dossier ET celui du sejour ouvert ; les sejours clos gardent leur psychologue ; `toxico_evaluations.created_by` n'est jamais reecrit ; jamais de suppression.
- **Qui transfere** : `ToxicoManager` et `admin` seulement. Un psychologue (meme referent), le promoteur et tous les autres roles : 403.
- **Cible** : compte actif de role `Psychologist` uniquement (pas `RESPONSIBLE_ROLES`) ; patient sans referent ou dont le referent n'est pas psychologue : premier referent accepte ; cible = referent actuel : refuse (409) ; patient sorti : transfert possible (dossier seul, `stay_id` NULL) ; **motif obligatoire** (non vide apres `strip`, 1000 caracteres max).
- **Transaction unique** : ligne de transfert + referent du dossier + referent du sejour ouvert + notification ; si la notification echoue, rien n'est ecrit. Un seul `commit` dans le depot (`NotificationRepository.create` ne fait qu'un `flush`).
- **Date du transfert** : `utils/business_time.py::business_now()` (Douala, naif) ; affichage jj/mm/aaaa.
- **Evaluer** : seul le psychologue referent du dossier, TOUJOURS (reglage active ou non) ; referent vide ou non psychologue : aucun psychologue ne peut evaluer ; admin et responsable n'evaluent pas (inchange, `role_required("Psychologist")`). Refus : 403 `{code: "not_referent", message}`.
- **Psychologue limite** : listes (actifs et sortis), recherche, compteurs et stats du tableau de bord, detail, dossier consolide (bloc toxicologie seulement), consentement et exports PDF/Excel ne montrent que les dossiers dont il est le referent actuel ; stats : `byPsychologist` vide et ligne "Non assigne" masquee ; patient sans referent visible de l'admin et du responsable seulement ; acces direct hors perimetre : 404 (jamais un indice d'existence).
- **Lecture seule** : onglet "Patients suivis auparavant" = dossiers dont il n'est plus referent mais ou un transfert, un sejour ou une evaluation est a son nom ; le detail montre l'historique complet, sans export, sans consentement, sans onglets medical/prescriptions ; toute ecriture est refusee par le serveur.
- **Notification** : type `toxico_transfer`, au nouveau psychologue seulement (l'ancien n'est pas notifie) ; libelle FR+EN dans `NotificationBell.vue`, clic vers le dossier.
- **Migration** : `down_revision = '031_lab_param_order'` (verifier `alembic heads`), revision `032_psychologist_scope_transfers`, SQL brut idempotent, appliquee a la base de dev sans demander (jamais de commande destructive), DDL reporte a la main dans `ci/schema_only.sql` (CRLF, bloc ajoute en fin de fichier comme les blocs 022+).
- **Erreurs visibles** : `detail = {code, message}` pour les refus nouveaux, traduits via `serverErrors.<code>` (`serverErrorLocalize.js`).
- **UI** : jetons de couleur seulement, texte >= 13 px, cibles >= 44 px, cles FR/EN identiques, ponctuation ASCII dans tout texte affiche (ni tiret long ou demi-cadratin, ni points de suspension typographiques, ni point median, ni fleche), dates jj/mm/aaaa, `authStore.hasRole()` pour tout controle de role, bibliotheque `ui/`.
- **Tests** : Postgres de dev partage, UN seul pytest a la fois, `REDIS_URL=redis://localhost:16379/0` (voir la note des tests de cloture ; `redis://localhost:6379/0` si c'est l'instance lancee), import de l'application ~2 min, 5 connexions reelles par minute max ; front : `cd ah2-admin-web && node --test tests/*.test.mjs`, `VITE_API_URL=http://127.0.0.1:8000 npx vite build`. Chaque test est ecrit AVANT le code et son echec constate.
- **Commits** : une etape "Commit" par tache, a n'executer que si le proprietaire a demande des commits (sinon laisser l'arbre modifie et passer a la tache suivante).

## Review Focus

- **Cache Redis des admissions du mois** (`toxico:stats:admissions:YYYY-MM`) : un psychologue limite recevrait le total global, ou ecrirait son chiffre dans la cle globale. Test Tache 3.
- **Portes laterales** hors de `/toxico/patients` : consentement, export PDF du dossier, `/patients/{id}/dossier` (+ export PDF/Excel), `/patients/{id}/dossier/recent` livrent un dossier hors perimetre. Test Tache 4.
- **Referent vide, non psychologue, ou ancien referent** apres transfert (fenetre ouverte avant le transfert) : doit etre 403 et ne rien ecrire ; le bouton Evaluer ne s'affiche que pour le referent. Tests Tache 5.
- **Atomicite et cas limites du transfert** : notification en echec, motif d'espaces, cible inactive ou non psychologue, meme referent, patient sorti (pas de sejour ouvert), premier referent (`from` NULL), A -> B -> A (A redevient referent : il quitte l'onglet "suivis auparavant"). Tests Tache 6 et 4.
- **Drapeau perdu en route** (piege deja vu avec `is_head_nurse`) : POST qui l'ignore, PUT/`GET /users` qui ne le rendent pas, auto-promotion par `PUT /auth/profile`, case qui reste cochee quand on change le role vers un non-psychologue. Tests Taches 2 et 7.

---

## File Structure

| Fichier | Role |
|---|---|
| `alembic/versions/032_psychologist_scope_transfers.py` | colonne `users.sees_own_toxico_only`, table `toxico_psychologist_transfers` |
| `models/toxico.py`, `models/user.py`, `models/__init__.py` | `ToxicoPsychologistTransfer`, relation `ToxicoDossier.transfers`, colonne du compte |
| `repositories/toxico_repo.py` | `ToxicoScope`, `scope_for_user`, `scope_clause`, acces `full/readonly/none`, "suivis auparavant", `transfer_dossier`, `get_referent_id` |
| `controller/toxico_controller.py` | scope du controleur, serialisation (`accessMode`, `transfers`, `psychologistId`), `transfer_dossier`, referent-only |
| `api_backend/backend_app/routes/toxico/toxico_endpoint.py`, `toxico_schema.py` | routes `POST /dossiers/{id}/transfer`, `GET /dossiers/previous`, mappage des refus |
| `controller/patient_dossier_controller.py`, `routes/patient_dossier/patient_dossier_endpoint.py` | limite du bloc toxicologie, `recent`, exports |
| `routes/admin/users_*.py`, `mapping.py`, `controller/user_controller.py`, `routes/auth/auth_endpoints.py` | parcours du drapeau |
| `ah2-admin-web/src/...` | `UserModal.vue`, `userStore.js`, `UserManagement.vue`, `ToxicoTransferModal.vue` (nouveau), `ToxicoPreviousPanel.vue` (nouveau), `ToxicoList.vue`, `ToxicoDossierModal.vue`, `ToxicoStaysTimeline.vue`, `ToxicoDashboard.vue`, `toxicoStore.js`, `ToxicoGateway.js`, `utils/toxicoStays.js`, `utils/toxicoExport.js`, `NotificationBell.vue`, `i18n.js` |
| `docs/user-guides/src/{toxico-1,toxico-2,psychologist-1,admin-1}/guide.md` + PDF | texte seulement |

Verifie dans le code actuel : aucune route de `/patients` n'est ouverte au role `Psychologist` (`/patients/`, `/patients/toxicology`), donc les seules portes toxicologie d'un psychologue sont `/toxico/*` et `/patients/{id}/dossier*`.

---

### Task 1: Migration 032, modele des transferts, colonne du compte

**Files:**
- Create: `alembic/versions/032_psychologist_scope_transfers.py`, `tests/test_toxico_transfer_schema.py`
- Modify: `models/toxico.py`, `models/user.py`, `models/__init__.py` (import de `ToxicoPsychologistTransfer`), `ci/schema_only.sql`

**Interfaces:**
- Produces : `User.sees_own_toxico_only = Column(Boolean, nullable=False, default=False, server_default="false")` ; `ToxicoPsychologistTransfer(id, dossier_id FK toxico_dossiers.id ON DELETE CASCADE NOT NULL, from_psychologist_id FK users NULL, to_psychologist_id FK users NOT NULL, decided_by FK users NOT NULL, decided_at timestamp NOT NULL (sans defaut : fourni par l'application), reason text NOT NULL, stay_id FK toxico_stays ON DELETE SET NULL NULL)` ; relations `dossier`, `from_psychologist`, `to_psychologist`, `decider` ; `ToxicoDossier.transfers = relationship(..., back_populates="dossier", order_by="desc(ToxicoPsychologistTransfer.decided_at), desc(ToxicoPsychologistTransfer.id)")` (sans `cascade="delete-orphan"` : le depot ne supprime jamais). CHECK `length(btrim(reason)) > 0` et `from_psychologist_id IS DISTINCT FROM to_psychologist_id` ; index sur `dossier_id`, `from_psychologist_id`, `to_psychologist_id`.

- [ ] **Step 1: Write the failing tests** (`tests/test_toxico_transfer_schema.py`, `db_session`) : `test_transfer_row_can_be_inserted`; `test_blank_reason_is_refused` (`"   "` leve `IntegrityError`); `test_from_equal_to_is_refused`; `test_to_psychologist_is_required`; `test_new_user_defaults_to_not_limited` (`create_test_user(...).sees_own_toxico_only is False` apres flush/refresh); `test_schema_only_sql_mirrors_migration` (le texte de `ci/schema_only.sql` contient `toxico_psychologist_transfers` et `sees_own_toxico_only`).
- [ ] **Step 2: Run to verify failure** : `python -m pytest tests/test_toxico_transfer_schema.py -v` -> FAIL (import / colonne absente).
- [ ] **Step 3: Implement** modele, migration (upgrade `ADD COLUMN IF NOT EXISTS` + `CREATE TABLE/INDEX IF NOT EXISTS` ; downgrade symetrique), puis `python -m alembic heads` (une seule tete `032_...`), `python -m alembic current`, `python -m alembic upgrade head` sur la base de dev, puis le bloc DDL dans `ci/schema_only.sql` (le charger dans une base jetable avec `ON_ERROR_STOP` pour verifier, puis la supprimer).
- [ ] **Step 4: Run to verify pass** : meme commande -> PASS.
- [ ] **Step 5: Commit** `feat: migration 032 - drapeau psychologue limite et table des transferts`

---

### Task 2: Le drapeau traverse tout le circuit des comptes (backend)

**Files:**
- Modify: `api_backend/backend_app/routes/admin/users_schemas.py` (`UserCreate`, `UserUpdate`, `UserOut` : `sees_own_toxico_only`, `Optional[bool] = None` a l'ecriture, `bool = False` en sortie), `routes/admin/mapping.py::normalize_user_data` (`get_field(raw, "sees_own_toxico_only") or False`), `routes/admin/users_endpoint.py` (`_USER_AUDIT_FIELDS`), `controller/user_controller.py` (kwarg de `create_user` : `data.get('sees_own_toxico_only') or False` ; ajout a la liste blanche de `update_user`), `routes/auth/auth_endpoints.py::get_me` (`"sees_own_toxico_only": bool(getattr(current_user, ...))`)
- Test: `tests/test_users_update.py`

**Interfaces:**
- Consumes : colonne de la Tache 1.
- Produces : `GET /auth/me` -> `sees_own_toxico_only: bool` ; `GET /users/`, `GET /users/{id}`, `POST`, `PUT` echangent `sees_own_toxico_only`. `SelfProfileUpdate` reste inchange (le drapeau n'y est pas).

- [ ] **Step 1: Write the failing tests** (a la suite de `test_create_user_with_head_nurse_checked_persists_flag`, memes helpers) : `test_create_psychologist_with_sees_own_toxico_only_persists_flag` (POST -> 201, corps `True`, relu par `GET /users/{id}` `True`) ; `test_update_user_sets_and_clears_sees_own_toxico_only` (PUT `True` puis `False`, `is_active` inchange) ; `test_list_users_returns_the_flag` (`GET /users/?search=<nom>` rend la cle) ; `test_flag_defaults_to_false_on_create_without_it` ; `test_flag_is_in_audit_snapshot` (`"sees_own_toxico_only" in users_endpoint._USER_AUDIT_FIELDS` et `_user_snapshot(user)` la contient) ; `test_self_profile_cannot_set_the_flag` (psychologue connecte, `PUT /auth/profile {"full_name": "X", "sees_own_toxico_only": false}` sur un compte limite : flag toujours `True` en base) ; `test_auth_me_exposes_the_flag`.
- [ ] **Step 2: Run to verify failure** : `python -m pytest tests/test_users_update.py -v -k "toxico_only or flag"` -> FAIL (`KeyError` / cle absente).
- [ ] **Step 3: Implement** les six points de contact ci-dessus (rien dans `UserBase`, comme `is_head_nurse`).
- [ ] **Step 4: Run to verify pass** : `python -m pytest tests/test_users_update.py -v` -> PASS (anciens tests inclus).
- [ ] **Step 5: Commit** `feat: drapeau sees_own_toxico_only dans le circuit des comptes`

---

### Task 3: Perimetre des listes, recherche, sortis, stats et exports de liste

**Files:**
- Modify: `repositories/toxico_repo.py`, `controller/toxico_controller.py`, `routes/toxico/toxico_endpoint.py` (aucun changement de signature de route : tout passe par le controleur)
- Test: `tests/test_toxico_scope_lists.py`

**Interfaces:**
- Consumes : Taches 1-2.
- Produces (dans `repositories/toxico_repo.py`) :
  - `class ToxicoScope(NamedTuple): own_psychologist_id: Optional[int] = None` avec propriete `is_limited -> bool` ; `UNRESTRICTED_SCOPE = ToxicoScope()`.
  - `scope_for_user(user) -> ToxicoScope` (ORM ou dict) : limite SSI le role canonique (`normalize_role_name`) est `psychologist` ET `sees_own_toxico_only` vrai ; sinon `UNRESTRICTED_SCOPE`.
  - `ToxicoRepository.scope_clause(self, scope: ToxicoScope) -> ColumnElement[bool]` : `ToxicoDossier.psychologist_id == scope.own_psychologist_id` si limite, `true()` sinon. **Seul** endroit qui encode la regle.
  - `search_dossiers(..., scope: ToxicoScope = UNRESTRICTED_SCOPE)`, `search_discharged_dossiers(..., scope=...)`, `active_stats(self, scope=...) -> dict` (`by_psychologist == {}` si limite), `count_dossiers_created_since(self, start_date, end_date=None, scope=...)` (jointure sur `ToxicoDossier` pour filtrer les sejours).
  - `class ToxicoForbiddenError(ValueError)` et `class ToxicoNotFoundError(ValueError)` (utilises Taches 4-5) ; `ToxicoValidationError` et `ToxicoConflictError` recoivent un `code: Optional[str] = None` optionnel (`__init__(self, message, code=None)`, attribut `.code`), sans changer les appels existants.
  - `ToxicoController.scope: ToxicoScope` fixe dans `__init__` ; `get_dashboard_stats()` ajoute `"scoped": bool` ; `get_current_month_admissions_count()` ne lit ni n'ecrit Redis quand `scope.is_limited`.

- [ ] **Step 1: Write the failing tests** (`tests/test_toxico_scope_lists.py`, fixtures du style de `test_toxico_discharged_list.py` : psychologues `psy_a` limite, `psy_b`, un dossier de A, un de B, un sans referent, un sorti de A, un sorti de B) :
  - `test_scope_for_user` : psychologue + drapeau -> `ToxicoScope(user_id)` ; psychologue sans drapeau, `ToxicoManager`/`admin`/`Assistant`/`SpiritualCounsellor` avec drapeau `True` -> `UNRESTRICTED_SCOPE` ; utilisateur de type `dict`.
  - `test_limited_psychologist_list_shows_only_own_active_patients` (`GET /toxico/patients` : `total == 1`, aucun nom de B ni du dossier sans referent) ; `test_limited_search_cannot_find_other_patients` (`search=<nom de B>` -> 0) ; `test_unrestricted_psychologist_sees_all` (3 dossiers actifs du marqueur) ; `test_toxico_manager_and_admin_see_unassigned_dossier`.
  - `test_limited_discharged_list_and_export_only_own` (`GET /toxico/dossiers/discharged` et `/discharged/export` : le dossier sorti de B absent ; un dossier sorti dont le DERNIER sejour est a A mais dont le referent est desormais B est absent).
  - `test_limited_stats_are_own_only_and_hide_psychologist_split` (`GET /toxico/stats/dashboard` : `activeTotal == 1`, `byPsychologist == []`, `scoped is True`, `byPhase`/`bySubstance`/`relapseRate` calcules sur ses dossiers) ; `test_unrestricted_stats_keep_split_and_scoped_false`.
  - `test_limited_month_admissions_ignore_and_do_not_poison_redis_cache` : poser `redis_client.set("toxico:stats:admissions:<YYYY-MM>", 99)` ; le psychologue limite recoit son propre compte (pas 99) ; la cle vaut toujours 99 ensuite ; un `ToxicoManager` recoit 99.
  - `test_other_roles_unchanged_by_flag` (promoteur/Assistant/SpiritualCounsellor : memes listes qu'avant).
- [ ] **Step 2: Run to verify failure** : `python -m pytest tests/test_toxico_scope_lists.py -v` -> FAIL (`ImportError: ToxicoScope`).
- [ ] **Step 3: Implement** les signatures ci-dessus ; `scope_clause` ajoute le predicat a chaque requete ; le cache du comptage mensuel est contourne quand `is_limited` (calcul direct).
- [ ] **Step 4: Run to verify pass** : meme commande puis `python -m pytest tests/test_toxico_discharged_list.py tests/test_toxico_domain_fixes.py tests/test_toxico_exports.py -v` (non-regression) -> PASS.
- [ ] **Step 5: Commit** `feat: perimetre du psychologue limite sur listes, stats et exports de liste`

---

### Task 4: Acces direct (plein / lecture seule / refuse), "suivis auparavant", dossier consolide

**Files:**
- Modify: `repositories/toxico_repo.py`, `controller/toxico_controller.py`, `routes/toxico/toxico_endpoint.py`, `routes/toxico/toxico_schema.py`, `controller/patient_dossier_controller.py`, `routes/patient_dossier/patient_dossier_endpoint.py`
- Test: `tests/test_toxico_scope_access.py`, `tests/test_toxico_scope_roles.py`

**Interfaces:**
- Consumes : Tache 3.
- Produces :
  - `ToxicoRepository.involvement_clause(self, user_id: int) -> ColumnElement[bool]` : dossier dont le referent n'est PAS `user_id` ET (un transfert `from_psychologist_id = user_id` OU un sejour `psychologist_id = user_id` OU une evaluation `created_by = user_id`).
  - `ToxicoRepository.get_dossier_access(self, dossier_id: int, scope: ToxicoScope) -> Literal['full','readonly','none']` ('full' si non limite et dossier existant ; 'none' si dossier absent) ; `get_dossier_full(self, patient_id: int, scope: ToxicoScope = UNRESTRICTED_SCOPE) -> Optional[ToxicoDossier]` (None si 'none').
  - `ToxicoRepository.list_previously_followed(self, user_id: int, search: Optional[str] = None, page: int = 1, per_page: int = 20) -> Tuple[List[ToxicoDossier], int]` (patient et referent charges).
  - `ToxicoController.access_for_dossier(dossier_id) -> str`, `access_for_patient(patient_id) -> str`, `list_previously_followed(search, page, per_page) -> dict` ; `serialize_dossier_details(dossier)` ajoute `"accessMode"` (`'full'|'readonly'`) et `"psychologistId"` (int ou None) ; `get_dossier_details(patient_id)` applique le scope (None si refuse).
  - Route `GET /toxico/dossiers/previous` (`role_required("Psychologist")`, declaree AVANT les routes `/dossiers/{dossier_id}/...`), schemas `ToxicoPreviousItem {patient_id, dossier_id, patientName, code, substance, isActive, psychologist}` et `ToxicoPreviousListResponse {data, total, page, per_page}`.
  - Regles de route : `GET /toxico/patients/{id}` -> 404 si 'none', corps complet avec `accessMode: 'readonly'` si lecture seule ; `GET /toxico/patients/{id}/export` -> 404 si 'none', **403 `{code:"read_only_access"}`** si 'readonly' ; `GET /toxico/dossiers/{id}/consent` -> memes regles ; `GET /patients/{id}/dossier` : le bloc `dossier_toxico` est RETIRE de la reponse (cle absente) pour un psychologue limite quand le dossier est hors perimetre, present (avec `accessMode`) en lecture seule, `flags` inchange ; `GET /patients/{id}/dossier/export` (PDF et Excel) : bloc retire sauf acces 'full' ; `GET /patients/{id}/dossier/recent` -> 403 pour un psychologue limite sans acces 'full'.

- [ ] **Step 1: Write the failing tests** (`tests/test_toxico_scope_access.py`) : `test_direct_detail_of_other_patient_is_404_for_limited_psychologist` (et le meme 404 que pour un id inexistant) ; `test_detail_of_own_patient_is_full` (`accessMode == "full"`) ; `test_previously_followed_list_has_patients_with_transfer_stay_or_evaluation_by_me` (trois dossiers, un par cause, plus un dossier jamais touche -> absent) ; `test_current_referent_is_not_in_previously_followed` (A -> B -> A : A redevient referent, quitte la liste) ; `test_readonly_detail_shows_full_history_but_marks_readonly` (evaluations, sejours et phases presents ; la cle `transfers` est ajoutee et testee en Tache 6) ; `test_readonly_export_and_consent_are_403_and_foreign_are_404` ; `test_consolidated_dossier_drops_toxico_block_outside_scope_but_keeps_flags` ; `test_consolidated_dossier_other_domains_still_served` ; `test_dossier_export_pdf_and_excel_omit_toxico_block_for_limited_psychologist` ; `test_dossier_recent_404_for_limited_psychologist_outside_scope_200_inside` ; `test_unrestricted_psychologist_and_other_roles_keep_full_access`. Fixtures : lignes `ToxicoPsychologistTransfer` inserees directement. `tests/test_toxico_scope_roles.py` : `test_routes_table_covers_router` (table des routes `GET /toxico/dossiers/previous` derivee de `app.routes`, ici avec la route de la Tache 6 ajoutee a la table dans la Tache 6) et matrice : `previous` -> 200 pour `Psychologist` seul, 403 pour tous les autres roles, 401 sans jeton.
- [ ] **Step 2: Run to verify failure** : `python -m pytest tests/test_toxico_scope_access.py tests/test_toxico_scope_roles.py -v` -> FAIL.
- [ ] **Step 3: Implement** les signatures ci-dessus. `PatientDossierController.get_full_dossier` retire `dossier_toxico` quand `self.toxico_ctrl.scope.is_limited` et que la valeur est `None` (meme patron que `est_medical_seul`) ; `get_recent_activity` leve `ToxicoForbiddenError` si `scope.is_limited` et `toxico_ctrl.access_for_patient(patient_id) != 'full'` (l'endpoint traduit en 403) ; `export_patient_dossier` retire `dossier_toxico` si son `accessMode != 'full'`. Les endpoints traduisent `ToxicoForbiddenError` en 403 et `ToxicoNotFoundError` en 404 AVANT leurs `except ValueError` existants (les deux sont des `ValueError`).
- [ ] **Step 4: Run to verify pass** : memes tests, puis `python -m pytest tests/test_patient_dossier.py tests/test_patient_dossier_recent.py tests/test_dossier_export.py tests/test_toxico_consent.py -v` -> PASS.
- [ ] **Step 5: Commit** `feat: acces direct limite, lecture seule des patients suivis auparavant, dossier consolide`

---

### Task 5: Seul le psychologue referent evalue

**Files:**
- Modify: `repositories/toxico_repo.py` (`get_referent_id`), `controller/toxico_controller.py` (`submit_evaluation`, `map_dossier_to_list_item` : `canEvaluate`, `psychologistId`), `routes/toxico/toxico_endpoint.py` (`submit_evaluation` : `except ToxicoForbiddenError` -> 403 `{code, message}`), `routes/toxico/toxico_schema.py` (`ToxicoPatientListItem.canEvaluate: bool = False`, `psychologistId: Optional[int] = None`)
- Test: `tests/test_toxico_referent_evaluation.py` ; ajuster `tests/test_toxico_readmission.py::test_http_evaluation_sur_dossier_sorti_409` si son psychologue n'est pas le referent du dossier cree (le referent doit etre le psychologue connecte pour atteindre le 409)

**Interfaces:**
- Consumes : Tache 3 (`ToxicoForbiddenError`, `code`).
- Produces : `ToxicoRepository.get_referent_id(self, dossier_id: int) -> Optional[int]` (leve `ValueError("Dossier introuvable")` si absent) ; la verification vit dans `ToxicoController.submit_evaluation` (pas dans `process_evaluation`, appele directement par d'autres tests avec des utilisateurs arbitraires) : `if referent_id != user_id: raise ToxicoForbiddenError("Seul le psychologue referent de ce dossier peut ajouter une evaluation.", code="not_referent")`, evaluee AVANT le 409 "dossier sorti".

- [ ] **Step 1: Write the failing tests** : `test_non_referent_psychologist_gets_403_not_referent_and_nothing_written` (`detail == {"code": "not_referent", "message": ...}`, 0 evaluation) ; `test_referent_psychologist_can_evaluate` (200) ; `test_referent_is_required_even_when_flag_is_off` (psychologue non limite non referent -> 403) ; `test_dossier_without_referent_cannot_be_evaluated_by_any_psychologist` ; `test_dossier_whose_referent_is_not_a_psychologist_cannot_be_evaluated` (referent `ToxicoManager`) ; `test_old_referent_is_refused_after_referent_changed` (UPDATE direct de `psychologist_id` vers `psy_b` : `psy_a` 403, `psy_b` 200) ; `test_readonly_psychologist_cannot_evaluate` ; `test_admin_and_toxico_manager_still_403_by_role` ; `test_list_item_can_evaluate_only_for_referent` (`canEvaluate` vrai uniquement sur les dossiers du psychologue connecte pour un psychologue non limite qui voit tout ; faux pour admin/responsable).
- [ ] **Step 2: Run to verify failure** : `python -m pytest tests/test_toxico_referent_evaluation.py -v` -> FAIL.
- [ ] **Step 3: Implement** comme decrit ; `canEvaluate = (role psychologue) and d.psychologist_id == mon user_id`.
- [ ] **Step 4: Run to verify pass** : meme commande, puis `python -m pytest tests/test_toxico_evaluation_roles.py tests/test_toxico_readmission.py tests/test_toxico_exports.py tests/test_pdf_signatures.py -v` -> PASS.
- [ ] **Step 5: Commit** `feat: seul le psychologue referent peut evaluer`

---

### Task 6: Transfert d'un patient (depot, controleur, route, notification, historique, PDF)

**Files:**
- Modify: `repositories/toxico_repo.py`, `controller/toxico_controller.py` (aussi `serialize_dossier_details` : `transfers`), `routes/toxico/toxico_endpoint.py` (route + `_build_dossier_pdf_context` : `transfers`), `routes/toxico/toxico_schema.py`, `api_backend/backend_app/utils/templates/toxico_dossier_export_template.html` (section "Changements de psychologue" si la liste est non vide)
- Test: `tests/test_toxico_transfer.py` ; completer la table de `tests/test_toxico_scope_roles.py`

**Interfaces:**
- Consumes : Taches 1, 3 (erreurs a `code`), `NotificationRepository(session).create`, `business_now()`.
- Produces :
  - `ToxicoRepository.transfer_dossier(self, dossier_id: int, to_psychologist_id: int, reason: str, decided_by: int) -> ToxicoPsychologistTransfer`. Algorithme (un seul `commit`, `rollback` sur toute exception, rien n'est avale) : `reason.strip()` vide ou > 1000 -> `ToxicoValidationError(code="transfer_reason_required")` ; verrou `with_for_update()` du dossier (absent -> `ToxicoNotFoundError`) ; cible = utilisateur actif de role `Psychologist` exactement, sinon `ToxicoValidationError(code="transfer_target_invalid")` ; cible == referent actuel -> `ToxicoConflictError(code="transfer_same_referent")` ; `stay = get_open_stay(...)` ; ecrire `from_psychologist_id = dossier.psychologist_id`, `stay_id = stay.id if stay else None`, `decided_at = business_now()` ; mettre a jour `dossier.psychologist_id` et `stay.psychologist_id` ; notification `type="toxico_transfer"`, destinataire la cible, `payload = {dossier_id, patient_id, patient_name, from_name (ou null), decided_by_name}` ; `commit`.
  - `ToxicoController.transfer_dossier(self, dossier_id: int, to_psychologist_id: int, reason: str) -> dict` (retourne la ligne serialisee) ; la serialisation du detail ajoute `"transfers": [{"id", "decided_at", "from_name", "to_name", "decided_by_name", "reason", "stay_number"}]`, du plus recent au plus ancien (noms lus des relations, jamais reecrits ailleurs).
  - `POST /toxico/dossiers/{dossier_id}/transfer`, `dependencies=[Depends(role_required("ToxicoManager", "admin"))]`, corps `ToxicoTransferRequest(BaseModel, extra="forbid") {to_psychologist_id: int, reason: str = Field(max_length=1000)}`, reponse 200 `{"message": "Patient transféré.", "transfer": <ligne>}` ; erreurs : 404 `Dossier introuvable`, 422/409 avec `detail = {"code", "message"}`.
  - Cibles du menu : l'endpoint existant `GET /toxico/psychologists` (inchange ; la liste est en cache Redis 1 h, la validation serveur fait foi).

- [ ] **Step 1: Write the failing tests** (`tests/test_toxico_transfer.py`) :
  - `test_transfer_changes_dossier_and_open_stay_only` (sejours clos gardent leur psychologue ; `stay_id` = sejour ouvert ; `from` = ancien referent) ; `test_transfer_of_discharged_patient_changes_dossier_only` (`stay_id is None`, aucun sejour modifie) ; `test_transfer_gives_first_referent_when_none` (`from_psychologist_id is None`) ; `test_transfer_from_non_psychologist_referent_allowed` (referent `ToxicoManager`).
  - `test_transfer_records_douala_time` (`decided_at` a moins d'une minute de `business_now()`, pas de l'UTC).
  - `test_transfer_notifies_new_psychologist_only` (1 notification `toxico_transfer` pour la cible avec les cles du payload, aucune pour l'ancien) ; `test_transfer_commits_once` (espion sur `db.commit` : un seul appel ; la notification est lisible apres) ; `test_transfer_is_atomic_when_notification_fails` (`NotificationRepository.create` patche pour lever : referents inchanges, aucune ligne de transfert).
  - Validations : `test_blank_reason_is_422_transfer_reason_required` (`"   "`) ; `test_reason_over_1000_chars_rejected` ; `test_target_must_be_active_psychologist` (inactif, `ToxicoManager`, `medecin`, inexistant -> 422 `transfer_target_invalid`) ; `test_transfer_to_current_referent_is_409` ; `test_unknown_dossier_is_404`.
  - `test_evaluations_keep_their_author_after_transfer` (`evaluator_name` de l'ancien, `created_by` inchange) ; `test_detail_lists_transfers_newest_first_with_names_and_reason` ; `test_chain_a_to_b_to_a` (deux lignes, `from` de la seconde = cible de la premiere) ; `test_pdf_context_lists_transfers` (`_build_dossier_pdf_context(detail)["transfers"]` : date jj/mm/aaaa, de, vers, par, motif).
  - Roles : table de `test_toxico_scope_roles.py` completee avec `("POST", "/toxico/dossiers/{dossier_id}/transfer")` : 200 pour `ToxicoManager` et `admin` seulement ; 403 pour `Psychologist` (meme referent), `promoteur`, `SpiritualCounsellor`, `Assistant`, `medecin`, `nurse`, `secretaire`, `laborantin`, `StockController` ; 401 sans jeton ; `test_real_login_wiring` (2 vraies connexions : jeton responsable accepte, jeton psychologue refuse).
- [ ] **Step 2: Run to verify failure** : `python -m pytest tests/test_toxico_transfer.py tests/test_toxico_scope_roles.py -v` -> FAIL.
- [ ] **Step 3: Implement** les signatures ci-dessus. Les erreurs a `code` sont rendues `detail={"code": e.code, "message": str(e)}`.
- [ ] **Step 4: Run to verify pass** : memes tests, puis tout `python -m pytest tests -k toxico -v` -> PASS.
- [ ] **Step 5: Commit** `feat: transfert d'un patient entre psychologues (table, route, notification, historique, PDF)`

---

### Task 7: Fiche du compte : la case "ne voit que ses patients" (front)

**Files:**
- Modify: `ah2-admin-web/src/components/users/UserModal.vue`, `src/stores/userStore.js`, `src/views/modules/users/UserManagement.vue`, `src/i18n.js`
- Test: `ah2-admin-web/tests/userModalContract.test.mjs` (etendre), `ah2-admin-web/tests/userManagementContract.test.mjs` (etendre)

**Interfaces:**
- Consumes : champ `sees_own_toxico_only` des routes `/users` (Tache 2).
- Produces : `form.sees_own_toxico_only` ; `showOwnToxicoField` (computed : role selectionne `Psychologist`, comparaison en minuscules comme `showHeadNurseField`) ; `userStore` expose `seesOwnToxicoOnly` par ligne et l'envoie dans `addUser` ET `updateUser` ; i18n `users.modal.sees_own_toxico_only` et `users.modal.sees_own_toxico_only_hint`.

| Cle | FR | EN |
|---|---|---|
| `users.modal.sees_own_toxico_only` | Ne voit que ses propres patients de toxicologie | Sees only their own toxicology patients |
| `users.modal.sees_own_toxico_only_hint` | Si la case est cochée, ce psychologue ne voit que les patients dont il est le référent actuel. | When ticked, this psychologist sees only the patients they currently follow. |

- [ ] **Step 1: Write the failing tests** : dans le contrat de `UserModal` ajouter les aiguilles `'sees_own_toxico_only: false'` (formulaire initial), `'v-model="form.sees_own_toxico_only"'`, `'v-if="showOwnToxicoField"'`, `'if (!showOwnToxicoField.value) {'` + `'form.sees_own_toxico_only = false'` (le changement vers un autre role decoche), `'sees_own_toxico_only: u.seesOwnToxicoOnly || false'` (edition), `"t('users.modal.sees_own_toxico_only')"` ; nouveau test `test_user_store_sends_flag_on_create_and_update` (le source de `userStore.js` contient `sees_own_toxico_only: formData.sees_own_toxico_only` deux fois et `seesOwnToxicoOnly: u.sees_own_toxico_only || false`) ; `UserManagement.vue` contient `v-if="user.seesOwnToxicoOnly"` et la cle i18n ; parite FR/EN des 2 cles.
- [ ] **Step 2: Run to verify failure** : `cd ah2-admin-web && node --test tests/userModalContract.test.mjs tests/userManagementContract.test.mjs` -> FAIL.
- [ ] **Step 3: Implement** : case sous `showHeadNurseField` (meme markup, `h-5 w-5`, ligne >= 44 px) avec le texte d'aide en `text-sm text-ink-muted` ; pastille de texte dans la colonne role de `UserManagement.vue` sur le modele de `isHeadNurse`.
- [ ] **Step 4: Run to verify pass** : memes tests, puis `node --test tests/*.test.mjs` -> PASS.
- [ ] **Step 5: Commit** `feat(web): case psychologue limite dans la fiche du compte`

---

### Task 8: Ecrans toxicologie : evaluer = referent, stats limitees, onglet "suivis auparavant", lecture seule (front)

**Files:**
- Modify: `src/services/ToxicoGateway.js`, `src/stores/toxicoStore.js`, `src/views/modules/toxico/ToxicoList.vue`, `src/views/dashboards/ToxicoDashboard.vue`, `src/components/toxico/ToxicoDossierModal.vue`, `src/utils/toxicoStays.js` (`readmissionPrefill`), `src/components/toxico/ToxicoAdmissionModal.vue` (prefill du psychologue), `src/i18n.js`
- Create: `src/components/toxico/ToxicoPreviousPanel.vue`
- Test: `tests/toxicoListContract.test.mjs` (mettre a jour les aiguilles changees : `v-if="canEvaluatePatient && p.canEvaluate"`), `tests/toxicoDashboardContract.test.mjs`, `tests/toxicoDossierContract.test.mjs`, `tests/toxicoStays.test.mjs`, nouveau `tests/toxicoScopeUiContract.test.mjs`

**Interfaces:**
- Consumes : `canEvaluate`, `accessMode`, `psychologistId`, `scoped`, `GET /toxico/dossiers/previous` (Taches 3-5), `GET /auth/me` -> `sees_own_toxico_only` (Tache 2).
- Produces : `ToxicoGateway.listPrevious(params: {page, per_page}) -> Promise<{data:{data,total,page,per_page}}>` ; store : `previous`, `previousTotal`, `previousLoading`, `previousError`, `previousPage`, `fetchPrevious()`, `setPreviousPage(n)`, computed `isScoped` (`globalStats?.scoped === true`) ; `readmissionPrefill(dossier)` ajoute `psychologist: dossier.psychologistId ?? null` (la readmission repropose le referent actuel) ; onglet `{ id: 'previous', label: 'toxico.previous.tab' }` visible si `authStore.hasRole(['Psychologist']) && !!authStore.user?.sees_own_toxico_only` (la liste appelle `authStore.fetchMe().catch(() => {})` au montage pour ne pas dependre d'un drapeau perime) ; `ToxicoList.vue` lit `route.query.patient` au montage et ouvre ce dossier (lien de la notification, Tache 9).

| Cle | FR | EN |
|---|---|---|
| `toxico.previous.tab` | Patients suivis auparavant | Previously followed patients |
| `toxico.previous.empty` | Aucun patient suivi auparavant. | No previously followed patients. |
| `toxico.previous.current_psy` | Référent actuel | Current psychologist |
| `toxico.transfer.readonly_banner` | Consultation en lecture seule : vous avez suivi ce patient, mais il n'est plus sous votre responsabilité. | Read-only view: you followed this patient, but they are no longer under your care. |

- [ ] **Step 1: Write the failing tests** : `toxicoStays.test.mjs` : `readmissionPrefill({psychologistId: 7, ...}).psychologist === 7` et `null` si absent ; `toxicoScopeUiContract.test.mjs` (source) : liste -> aiguilles `p.canEvaluate`, `{ id: 'previous', label: 'toxico.previous.tab' }`, `authStore.user?.sees_own_toxico_only`, `<ToxicoPreviousPanel`, `route.query.patient`, `authStore.fetchMe()` ; tableau de bord -> la carte `toxico.dashboard.psy_workload` porte `v-if="!toxicoStore.isScoped"` ; modale dossier -> `patient.accessMode === 'readonly'` masque `canDischarge`, `canExportDossier` et les onglets medical/prescriptions, et affiche `toxico.transfer.readonly_banner` ; panneau -> appelle `fetchPrevious`, bouton ouvrant le dossier, pagination precedent/suivant, etat vide, `LoadErrorState` ; parite FR/EN de toutes les cles citees (modele de `toxicoListContract`) ; absence des caracteres interdits (test `forbiddenCharsUserText` existant).
- [ ] **Step 2: Run to verify failure** : `cd ah2-admin-web && node --test tests/toxicoStays.test.mjs tests/toxicoScopeUiContract.test.mjs tests/toxicoListContract.test.mjs` -> FAIL.
- [ ] **Step 3: Implement** les points ci-dessus. Le panneau reutilise `ResponsiveTable`, `StatusBadge`, `AppButton`, `LoadErrorState` (colonnes : patient + code, statut actif/sorti, referent actuel ; action : voir le dossier). Pas de bouton d'action clinique en lecture seule.
- [ ] **Step 4: Run to verify pass** : `node --test tests/*.test.mjs`, puis `VITE_API_URL=http://127.0.0.1:8000 npx vite build` sans erreur.
- [ ] **Step 5: Commit** `feat(web): evaluer reserve au referent, stats limitees, onglet lecture seule`

---

### Task 9: Bouton et fenetre de transfert, historique, cloche (front)

**Files:**
- Create: `src/components/toxico/ToxicoTransferModal.vue`
- Modify: `src/services/ToxicoGateway.js`, `src/stores/toxicoStore.js`, `src/utils/toxicoStays.js`, `src/utils/toxicoExport.js`, `src/views/modules/toxico/ToxicoList.vue`, `src/components/toxico/ToxicoDossierModal.vue`, `src/components/toxico/ToxicoStaysTimeline.vue`, `src/components/notifications/NotificationBell.vue`, `src/utils/serverErrorLocalize.js` (rien si les codes passent par `serverErrors.<code>`), `src/i18n.js`
- Test: `tests/toxicoStays.test.mjs`, `tests/toxicoExport.test.mjs`, nouveau `tests/toxicoTransferContract.test.mjs`

**Interfaces:**
- Consumes : `POST /toxico/dossiers/{id}/transfer`, `detail.transfers`, notification `toxico_transfer`.
- Produces :
  - `TOXICO_TRANSFER_ROLES = ['admin', 'ToxicoManager']` (`utils/toxicoExport.js`, miroir de la garde serveur).
  - `validateTransfer({ toPsychologistId, currentPsychologistId, reason }) -> string[]` (`utils/toxicoStays.js`) : cles d'erreur `toxico.transfer.errors.target_required`, `.same_referent`, `.reason_required` (apres `trim`), `.reason_too_long` (> 1000) ; vide si valide.
  - `transferItems(transfers, stays) -> Array<{kind:'transfer', date, stay_number, from_name, to_name, decided_by_name, reason}>` : `stay_number` du transfert, sinon celui du dernier sejour (un transfert de patient sorti s'affiche sous le dernier sejour, jamais dans le groupe "ancien").
  - `ToxicoGateway.transferDossier(dossierId: number, { to_psychologist_id: number, reason: string })` ; store `transferDossier(dossierId, { toPsychologistId, reason })` qui recharge liste et stats.
  - `ToxicoTransferModal.vue` : props `dossierId: Number`, `patientName: String`, `currentPsychologistId: Number|null`, `currentPsychologistName: String`; emits `close`, `transferred`; liste deroulante des psychologues SANS le referent actuel (store `psychologists`), zone de motif obligatoire ; erreurs serveur via `apiErrorMessage`.
  - Bouton "Transferer" : colonne d'actions de la liste active (`v-if="canTransferPatient"` = `authStore.hasRole(TOXICO_TRANSFER_ROLES)`) et pied de `ToxicoDossierModal` (actif ou sorti, jamais en lecture seule). Clic cloche `toxico_transfer` : `pushIfRoute('/dashboard/toxico?patient=' + n.payload.patient_id)` (verifier le chemin reel de la route `toxico` avec `router.resolve`).

| Cle | FR | EN |
|---|---|---|
| `toxico.transfer.action` | Transférer | Transfer |
| `toxico.transfer.title` | Transférer le patient | Transfer the patient |
| `toxico.transfer.current` | Référent actuel : {name} | Current psychologist: {name} |
| `toxico.transfer.no_referent` | Aucun référent | No psychologist assigned |
| `toxico.transfer.target_label` | Nouveau psychologue référent | New responsible psychologist |
| `toxico.transfer.target_placeholder` | Choisir un psychologue | Choose a psychologist |
| `toxico.transfer.reason_label` | Motif du transfert | Reason for the transfer |
| `toxico.transfer.reason_placeholder` | Expliquez pourquoi ce patient change de psychologue | Explain why this patient changes psychologist |
| `toxico.transfer.submit` / `submitting` / `cancel` | Confirmer le transfert / Transfert en cours / Annuler | Confirm the transfer / Transfer in progress / Cancel |
| `toxico.transfer.success` | Patient transféré à {name}. | Patient transferred to {name}. |
| `toxico.transfer.errors.target_required` | Choisissez le nouveau psychologue. | Choose the new psychologist. |
| `toxico.transfer.errors.same_referent` | Ce psychologue est déjà le référent du patient. | This psychologist already follows the patient. |
| `toxico.transfer.errors.reason_required` | Le motif est obligatoire. | The reason is required. |
| `toxico.transfer.errors.reason_too_long` | Le motif ne peut pas dépasser 1000 caractères. | The reason cannot exceed 1000 characters. |
| `toxico.transfer.history_label` | Changement de psychologue | Psychologist change |
| `toxico.transfer.history_line` | De {from} vers {to}, décidé par {by} | From {from} to {to}, decided by {by} |
| `toxico.transfer.history_reason` | Motif : {reason} | Reason: {reason} |
| `notifications.toxico_transfer` | {by} vous a transféré le patient {patient} | {by} transferred the patient {patient} to you |
| `serverErrors.not_referent` | Seul le psychologue référent de ce dossier peut ajouter une évaluation. | Only the responsible psychologist of this file can add an evaluation. |
| `serverErrors.transfer_target_invalid` | Le psychologue choisi est introuvable, inactif ou n'a pas le rôle de psychologue. | The chosen psychologist was not found, is inactive or does not have the psychologist role. |
| `serverErrors.transfer_same_referent` | Ce psychologue est déjà le référent du patient. | This psychologist already follows the patient. |
| `serverErrors.transfer_reason_required` | Le motif du transfert est obligatoire. | The reason for the transfer is required. |
| `serverErrors.read_only_access` | Ce dossier est en lecture seule pour vous. | This file is read-only for you. |

- [ ] **Step 1: Write the failing tests** : `toxicoExport.test.mjs` : `TOXICO_TRANSFER_ROLES` egale exactement `['admin','ToxicoManager']` ; `toxicoStays.test.mjs` : `validateTransfer` (quatre cas d'erreur + valide), `transferItems` (transfert avec sejour -> son sejour ; sans sejour -> dernier sejour ; liste vide) ; `toxicoTransferContract.test.mjs` (source) : la modale (props, emits, `validateTransfer`, `apiErrorMessage`, `min-h-11`, pas de `v-if` sur le role a l'interieur), `v-if="canTransferPatient"` dans la liste et `v-if="canTransfer"` (actif ou sorti, pas lecture seule) dans la modale dossier, la frise affiche `kind === 'transfer'` avec `history_line` et `history_reason`, la cloche contient `n.type === 'toxico_transfer'` dans `labelFor` ET `handleClick` ; parite FR/EN de toutes les cles du tableau ; aucune cle nouvelle absente.
- [ ] **Step 2: Run to verify failure** : `cd ah2-admin-web && node --test tests/toxicoExport.test.mjs tests/toxicoStays.test.mjs tests/toxicoTransferContract.test.mjs` -> FAIL.
- [ ] **Step 3: Implement** les points ci-dessus (fenetre sur le modele de `ToxicoDischargeModal.vue` : `FullScreenPanel`, `FormField`, `ActionBar`, `AppButton` variante propre a l'action, pas de vert partout).
- [ ] **Step 4: Run to verify pass** : `node --test tests/*.test.mjs` puis `VITE_API_URL=http://127.0.0.1:8000 npx vite build` -> PASS, build sans erreur. Verification manuelle sur l'API de demo : transfert depuis le responsable, notification chez le nouveau psychologue, ancien psychologue limite : patient disparu de ses listes et visible dans "Patients suivis auparavant" en lecture seule, entree du transfert dans l'historique.
- [ ] **Step 5: Commit** `feat(web): transfert d'un patient, historique et notification`

---

### Task 10: Guides utilisateur (texte seulement)

**Files:**
- Modify: `docs/user-guides/src/toxico-1/guide.md`, `toxico-2/guide.md`, `psychologist-1/guide.md`, `admin-1/guide.md` ; regenerer `docs/user-guides/en/*.pdf` correspondants ; mettre a jour `docs/superpowers/SUIVI-AVANCEMENT.md` (chantier termine, regles du referent et piege du cache)
- Test: `docs/user-guides/tools/check_style.py <guide_id>` (sortie 0)

**Interfaces:**
- Consumes : tous les libelles et comportements des Taches 1-9 (aucune capture nouvelle ; les figures existantes restent valables, ne pas en reprendre).

- [ ] **Step 1: Write the failing check** : ajouter dans chaque guide les passages ci-dessous AVANT de valider (le gate de style echoue tant qu'un terme interdit est present) ; pour s'assurer que les termes sont couverts, `grep -n "Transfer\|Previously followed\|own patients" docs/user-guides/src/*/guide.md` doit rendre des lignes dans les quatre guides.
  - `toxico-1` (chapitre "Evaluations") : corriger "any psychologist" -> seul le psychologue **referent** du dossier ecrit l'evaluation ; chapitre "The patient file" : le bloc "Transfers" dans l'historique (date, de, vers, qui a decide, motif).
  - `toxico-2` : nouveau chapitre "Transferring a patient to another psychologist" (bouton [[Transfer]] de la liste et du dossier, choix du psychologue, motif obligatoire, effet sur le sejour ouvert, patient sorti possible, notification du nouveau psychologue seulement, rien n'est efface) ; "Common mistakes" : motif vide, meme psychologue.
  - `psychologist-1` : seul le referent evalue (le bouton [[Evaluate]] n'apparait que sur ses patients) ; si le compte est limite : ne voit que ses patients, stats personnelles, onglet **Previously followed patients** en lecture seule (aucune evaluation, aucun export) ; notification de transfert recue ; glossaire (referent, lecture seule).
  - `admin-1` (chapitre "Staff accounts") : la case **Sees only their own toxicology patients** de la fiche d'un compte Psychologue (desactivee par defaut, effet, meme case a la creation), et le fait que l'admin peut transferer un patient.
- [ ] **Step 2: Run to verify** : `python docs/user-guides/tools/check_style.py toxico-1 toxico-2 psychologist-1 admin-1` (un guide a la fois si l'outil l'impose) : doit sortir 0 ; corriger les violations (ponctuation ASCII, pas de terme interdit).
- [ ] **Step 3: Rebuild** : `python docs/user-guides/tools/build_pdf.py <guide_id>` pour les quatre ; verifier que chaque PDF s'ouvre et que les nouveaux titres de chapitre sont presents (`--probe "Transferring a patient"`).
- [ ] **Step 4: Update SUIVI-AVANCEMENT.md** (chantier ferme, date, decisions, residuels ci-dessous).
- [ ] **Step 5: Commit** `docs: guides toxico, psychologue et admin mis a jour (vue limitee, transfert)`

---

## Decisions et ambiguites a trancher par le proprietaire (hypotheses retenues par ce plan)

1. **Readmission avec un autre psychologue** : le spec dit qu'elle "reprend le referent actuel". Le plan pre-selectionne le referent actuel dans la fenetre de readmission (Tache 8), mais `_readmit` continue d'accepter un autre choix explicite du responsable SANS ligne de transfert (reassignation non tracee). Alternative : tracer automatiquement un transfert (motif "Readmission") si le choix differe.
2. **`GET /dossiers/{id}/transfers` non cree** : l'historique des transferts est porte par le detail du dossier (`transfers`), le dossier consolide et le PDF ; un endpoint de lecture separe serait un doublon.
3. **`/patients/{id}/dossier/recent`** (dossier medical et prescriptions du patient) est ferme au psychologue limite hors perimetre (403) ; le spec ne le nomme pas.
4. **Lecture seule et exports** : un patient "suivi auparavant" n'a ni export PDF/Excel ni consentement (le spec limite les exports aux patients actuels).
5. **Liste des sortis** : la colonne "psychologue" affiche toujours le psychologue du dernier SEJOUR ; apres un transfert d'un patient sorti, seul le referent du dossier change (donc la ligne peut afficher l'ancien nom, mais le filtre de perimetre suit le referent du dossier).
6. **Drapeau perime dans le navigateur** : l'onglet "suivis auparavant" depend de `authStore.user.sees_own_toxico_only` (rafraichi par `fetchMe()` a l'ouverture de l'ecran) ; toute la securite reste cote serveur.

## Decisions prises par l assistant (a confirmer par l utilisateur a la lecture du plan)

1. Readmission avec un autre psychologue : enregistrer automatiquement un transfert (motif « Readmission ») pour ne jamais reassigner sans trace ; sans autre choix, le referent actuel est repris.
2. Pas de `GET /dossiers/{id}/transfers` separe : les transferts sont portes par le detail du dossier, le dossier consolide et le PDF.
3. `/patients/{id}/dossier/recent` : refus (403) pour un psychologue limite hors de son perimetre.
4. Patients en lecture seule (« suivis auparavant ») : ni export ni fichier de consentement.
5. La liste des patients sortis suit le referent du DOSSIER (pas le psychologue du dernier sejour) pour le filtre de perimetre.
6. Le drapeau cote navigateur ne sert qu a afficher l onglet ; l application est entierement cote serveur.
