# Notes du conseiller spirituel - Plan d'implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner au conseiller spirituel un ecran simple de notes de rencontres (liste commune, sans lien avec un patient), lisible en lecture seule par le promoteur et l'admin.

**Architecture:** Une nouvelle table `spiritual_notes` et un routeur `/spiritual-notes` (repo, controleur, endpoints) sur le modele des autres modules ; un ecran web unique (liste + formulaire) dont les boutons d'ecriture dependent du role ; aucune table existante modifiee, pas de PowerSync.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Vue 3, vue-i18n.

**Spec:** `docs/superpowers/specs/2026-10-28-notes-conseiller-spirituel-design.md` (approuvee 2026-10-28).

## Global Constraints

- Roles serveur : ecriture (creer, modifier, supprimer) `SpiritualCounsellor` seulement et **sur ses propres notes** ; lecture `SpiritualCounsellor` (toutes les notes du role), `promoteur`, `admin` (toutes, avec le nom de l'auteur). Tout autre role : 403.
- Date de rencontre : defaut aujourd'hui Douala (`utils/business_time.business_today()`), jamais dans le futur, au plus 365 jours dans le passe.
- Contenu : cases booleennes (conseil, priere, verset lu, discussion, texte remis, questions et reponses), reference du verset (texte court, facultatif), mention « n'a pas voulu parler » (booleen), texte libre (facultatif) ; une note peut etre vide sauf la date.
- Suppression definitive par l'auteur seulement ; audit (`AuditRepository.log_user_action`) avec identifiant, date et auteur de la note, **jamais son texte**.
- Aucun journal des lectures, aucun rappel, aucun compteur, aucun indicateur « sans note », aucun export, rien dans les statistiques ni les exports existants.
- Liste triee par date de rencontre decroissante puis creation decroissante, paginee cote serveur (page, per_page, `total`, `total_pages` comme les autres listes), sans filtre ni recherche.
- Migration Alembic : id `035_spiritual_notes` (<= 32 caracteres), `down_revision = '034_product_photo_label_size'`, appliquee a la base de developpement, miroir dans `ci/schema_only.sql` ; verifier les contraintes avant de decrire un champ comme libre.
- UI : jetons seulement, textes >= 13 px, cibles >= 44 px, FR/EN a cles identiques, ponctuation ASCII (ni tiret long, ni fleche, ni points de suspension en un caractere, ni point median), dates jj/mm/aaaa, `authStore.hasRole()`. Ecriture en ligne uniquement (message clair si le reseau manque ; le brouillon reste dans la fenetre).
- Ne pas toucher aux consultations spirituelles facturees, au carnet de la caisse, aux ecrans de toxicologie ni aux droits de lecture actuels du conseiller.

## Review Focus

- Un conseiller ne peut pas modifier ni supprimer la note d'un autre conseiller (403 identique que la note existe ou non est inutile ici : 403/404 au choix mais jamais de succes) ; promoteur et admin ne peuvent jamais ecrire, meme avec une requete directe.
- Date dans le futur, a plus de 365 jours, absente ou mal formee : refus clair ; un champ libre tres long ou une reference de verset trop longue sont refuses ou bornes.
- Une suppression ne laisse le texte de la note ni dans l'audit ni dans les journaux.
- Un role non autorise (secretaire, medecin, psychologue, responsable de toxicologie, assistant) ne voit ni l'entree de menu ni les donnees (liste, detail).
- Pagination : page vide, `per_page` hors bornes, tri stable quand deux notes ont la meme date.

---

### Task 1: Table, routeur et regles d'acces (serveur)

**Files:**
- Create: `alembic/versions/035_spiritual_notes.py`, `models/spiritual_note.py`, `repositories/spiritual_note_repo.py`, `controller/spiritual_note_controller.py`, `api_backend/backend_app/routes/spiritual_notes/__init__.py`, `.../spiritual_notes_endpoints.py`, `.../spiritual_notes_schemas.py`
- Modify: `api_backend/backend_app/main.py` (inclusion du routeur, comme `lab_stock_endpoints`), `ci/schema_only.sql`
- Test: `tests/test_spiritual_notes.py`

**Interfaces:**
- Produces: table `spiritual_notes` (id, `author_id` FK `users.user_id`, `meeting_date` date, six booleens, `verse_reference` varchar(120) null, `no_one_spoke` boolean, `content` text null, `created_at`, `updated_at`) ; `GET /spiritual-notes/?page&per_page` -> `{ data: [Note + author_name + can_edit], total, page, per_page, total_pages }` ; `POST /spiritual-notes/` ; `PUT /spiritual-notes/{id}` ; `DELETE /spiritual-notes/{id}` (204) ; `GET /spiritual-notes/{id}`.
- Consumes: `role_required`, `get_current_user`, `AuditRepository.log_user_action`, `business_today`.

- [ ] **Step 1: Tests (echouent d'abord)** dans `tests/test_spiritual_notes.py` : `test_counsellor_crud_own_note`, `test_other_counsellor_reads_all_but_cannot_edit_or_delete_others`, `test_promoteur_and_admin_read_all_with_author_name_and_cannot_write`, `test_other_roles_get_403_on_every_route` (secretaire, medecin, nurse, Psychologist, ToxicoManager, Assistant), `test_meeting_date_rules` (defaut aujourd'hui, futur refuse, 366 jours refuse, 365 accepte, mal forme refuse), `test_empty_note_allowed_with_date_only`, `test_text_and_verse_length_bounds`, `test_delete_is_hard_and_audit_has_no_text`, `test_list_order_pagination_and_stable_tie_break`.
- [ ] **Step 2: Migration 035** et modele ; l'appliquer a la base de developpement (`alembic upgrade head`, verifier la table) ; miroir dans `ci/schema_only.sql`.
- [ ] **Step 3: Implementer** repo, controleur (regles d'auteur, bornes de date, audit sans texte) et endpoints avec gardes de role ; inclure le routeur dans `main.py`.
- [ ] **Step 4: Lancer** `pytest tests/test_spiritual_notes.py` (un seul pytest a la fois, `REDIS_URL=redis://localhost:6379/0`) : tout passe. Ajouter les routes aux tests de roles existants s'il en existe une table.
- [ ] **Step 5: Commit** (le controleur seul decide des commits).

### Task 2: Ecran web, menu et route

**Files:**
- Create: `ah2-admin-web/src/services/SpiritualNoteGateway.js`, `ah2-admin-web/src/utils/spiritualNote.js`, `ah2-admin-web/src/views/modules/spiritual/SpiritualNotes.vue`, `ah2-admin-web/src/components/spiritual/SpiritualNoteForm.vue`
- Modify: `ah2-admin-web/src/router/index.js`, `ah2-admin-web/src/components/layout/MainLayout.vue` (entree « Notes spirituelles » pour `SpiritualCounsellor`, `promoteur`, `admin`), `ah2-admin-web/src/i18n.js`, `ah2-admin-web/src/views/errors/Forbidden.vue` seulement si l'accueil du role l'exige
- Test: `ah2-admin-web/tests/spiritualNote.test.mjs`, `ah2-admin-web/tests/spiritualNotesContract.test.mjs`

**Interfaces:**
- Produces: `validateNote(form, todayIso) -> { ok: boolean, errors: Record<string,string> }` (pure : date requise, pas dans le futur, pas plus de 365 jours dans le passe ; verset <= 120 ; texte <= 5000) ; `emptyNote(todayIso)` ; `SpiritualNoteGateway.list({page, perPage})`, `create`, `update`, `remove` ; ecran liste (la plus recente en premier, derniere note mise en avant, pagination) + formulaire (cases, verset, « n'a pas voulu parler », texte libre) ; boutons d'ecriture visibles seulement pour `SpiritualCounsellor`, et modifier/supprimer seulement sur ses propres notes (`can_edit`).
- Consumes: Task 1 (endpoints).

- [ ] **Step 1: Tests purs** `spiritualNote.test.mjs` : date du jour acceptee, demain refuse, 365 jours acceptes, 366 refuse, date absente refusee, verset de 121 caracteres refuse, note vide avec date acceptee, `emptyNote` met la date du jour.
- [ ] **Step 2: Test de contrat** `spiritualNotesContract.test.mjs` (style des autres `*Contract.test.mjs`) : l'entree de menu et la route n'existent que pour les trois roles, les boutons d'ecriture sont conditionnes au role et a `can_edit`, aucune cle i18n manquante FR/EN, aucun caractere interdit.
- [ ] **Step 3: Implementer** l'ecran, la passerelle (erreurs serveur traduites par le mecanisme existant), le menu et la route ; message clair si le reseau manque, le brouillon reste ouvert.
- [ ] **Step 4: Lancer** `cd ah2-admin-web && node --test tests/spiritualNote.test.mjs tests/spiritualNotesContract.test.mjs tests/i18nMessagesCompile.test.mjs tests/sidebarMenu.test.mjs`, puis tout `node --test tests/*.test.mjs`, puis le build (`VITE_API_URL=http://127.0.0.1:8000 NODE_OPTIONS=--max-old-space-size=2048 npx vite build`).

### Task 3: Verification navigateur, guides, suivi

**Files:**
- Modify: `docs/user-guides/src/spiritual-1/guide.md` (refait : notes), guides du promoteur et de l'admin concernes (lecture seule), `docs/superpowers/SUIVI-AVANCEMENT.md`, `docs/superpowers/DEFAUTS-RELEVES-PAR-LES-GUIDES.md` si utile

- [ ] **Step 1: Navigateur reel** (demo API :8000, build :4173) : conseiller cree, modifie, supprime une note ; deuxieme conseiller (a creer pour le test puis supprimer) la lit sans pouvoir la modifier ; promoteur et admin la lisent sans bouton d'ecriture ; secretaire n'a ni menu ni acces direct a la route ; date future refusee ; hors ligne : message clair.
- [ ] **Step 2: Guides** : refaire `spiritual-1` (texte et figures), ajouter une courte section de lecture seule pour promoteur et admin, verifier le style (`check_style.py`), ne regenerer que les PDF touches.
- [ ] **Step 3: Suites completes** : backend complet (un seul pytest) et tests node ; seuls les 6 echecs connus (donnees de demonstration) sont acceptes.
- [ ] **Step 4: Suivi** mis a jour, revue finale de la branche (modele le plus capable), attendre la demande de commit.
