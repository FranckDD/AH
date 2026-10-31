# Laboratoire : fiches fideles, catalogue modifiable, age precis, grossesse, prescripteur externe - Plan d'implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que le laboratoire imprime des fiches de resultats fideles a ses propres modeles, modifie lui-meme son catalogue, conserve l'age exact et la grossesse (suivi exige par l'Etat) et saisisse le prescripteur d'un patient externe.

**Architecture:** On etend les tables `examens`, `parametres`, `reference_ranges`, `lab_results`, `lab_result_details`, `patients` (ajouts seulement, migrations 036 et suivantes). Un module `utils/lab_age.py` calcule et formate l'age ; `utils/lab_reference.py` choisit la plage ; un gabarit WeasyPrint par famille de mise en page lit une copie figee du resultat validee a la validation ; l'ecran de gestion du catalogue (`LabConfig.vue` existant) devient editable par l'admin et la cheffe du laboratoire (drapeau `is_head_lab`, modele `is_head_nurse`).

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, WeasyPrint, Vue 3, vue-i18n, PowerSync.

**Spec:** `docs/superpowers/specs/2026-10-31-laboratoire-fiches-catalogue-age-grossesse-design.md` (approuvee 2026-10-31, avec la section « Reponses aux questions de la relecture »). Analyse des fiches (non versionnee, sans donnees patient reelles) : `.superpowers/sdd/2026-10-28-chantier8-deploiement/lab-templates-analysis.md`.

## Global Constraints

- Les documents `docs/laboratory/` contiennent de vrais noms de patients : jamais commites, jamais recopies dans le depot, les tests ou les gabarits ; les exemples de tests utilisent des patients inventes.
- En-tete et pied de page des fiches : dynamiques, produits par `get_pdf_header_context` / `_pdf_header.html` (meme source que les autres PDF) ; ajouter a `organization_config` les champs manquants (numero d'agrement, texte du pied de page, libelle de signature par defaut) avec migration et ecran de configuration.
- Fiche : une page par examen, Lettre US 21,59 x 27,94 cm portrait, polices Liberation (Times, Arial, Courier equivalents) ; Conclusion et NB = deux champs libres du laborantin, jamais de phrase automatique ; signature sans nom a droite, libelle de l'examen.
- Age en jours exacts (naissance -> date de reference = date d'enregistrement a la reception, ou date de prelevement si saisie) ; affichage exact sous un an : 5 jours -> « 5 jours », 17 jours -> « 2 semaines 3 jours », 3 mois 15 jours -> « 3 mois 2 semaines », 12 a 59 mois (mois complets, plancher : 716 j -> 1 an 11 mois, 1825 j -> 4 ans 11 mois) -> « 1 an 6 mois », des 5 ans -> « N ans ».
- Plages : migration `age_min_days = age_min*365`, `age_max_days = (age_max+1)*365-1` ; bornes inclusives ; bornes absentes = ouvertes ; pediatriques standard en lignes : nouveau-ne 0 a 28 jours, enfant 29 jours a moins de 5 ans ; selection : sexe (M, F, X), age en jours, SA ; plusieurs candidates -> plus de criteres renseignes, puis intervalle d'age le plus etroit, puis plus petit id.
- Grossesse : `pregnancy_status` (enceinte / non_enceinte / inconnu, defaut inconnu), `expected_delivery_date`, `pregnancy_program_number` sur `patients` ; SA (`gestational_age_weeks`, 0 a 45) sur `lab_results` ; memes champs dans `external_patient_info` pour l'externe. **La secretaire ne voit ni ne saisit ces champs** : les reponses de toutes les routes qu'elle appelle n'en contiennent aucun, test par role cote serveur. Ecriture : medecin, infirmier, laboratoire, admin ; lecture : ces roles + promoteur (rapport).
- Numero de dossier : format `NNN/NN du JJ/MM/AAAA` ; attribue par le serveur sous verrou a l'enregistrement a la reception ; premier nombre = compteur annuel qui avance au premier dossier de chaque nouvelle journee d'activite, remis a zero le 1er janvier ; second = rang du patient dans la journee, partage par ses examens du jour ; unicite (annee, compteur, rang) ; reference temporaire hors ligne, numero officiel au premier envoi, fiche imprimable seulement apres ; numero d'ordre interne unique (annee + compteur) conserve.
- Prescripteur libre : uniquement pour le patient externe a la reception du laboratoire ; titre dans {Dr, I.D.E., Fr, Br, M., Mme, Volontaire, Autre} + nom libre -> `lab_results.prescribed_by_name` (100 caracteres) sous la forme `<titre> <nom>` ; suggestions depuis `lab_external_prescribers` ; le champ et la liste des medecins internes ne changent pas.
- Catalogue : ecriture reservee a admin et laborantin avec `is_head_lab` ; les prix restent au catalogue des prix (admin) ; modification en ligne seulement ; historique dans le journal d'audit (avant/apres) ; un resultat valide garde une copie figee (libelle, unite, norme imprimee, ordre, famille, titre, methode, section, signature) ; reimpression = copie figee ; un resultat sans copie figee utilise l'ancien PDF (code conserve).
- Familles de mise en page (liste fermee) : tableau, trois colonnes, lignes libelle-valeur, compte rendu narratif, formulaire en cases ; defaut pour un nouvel examen : lignes libelle-valeur.
- Donnees de depart : completer le catalogue des examens manquants, aligner noms, unites (mg/dl pour les variantes), ordre ; serologies qualitatives en positif/negatif avec titre quand la fiche en imprime un ; valeurs normales des fiches (min-max standards pour les serologies) ; le fichier d'export du catalogue de production est regenere ; `scripts/import_reference_data.py` doit charger les nouvelles colonnes, mettre les prix a 0 ; les plages validees par la cheffe du laboratoire (PDF `docs/documentation-validation/`) completent apres signature.
- UI : jetons seulement, textes >= 13 px (14 px au laboratoire), cibles >= 44 px, FR/EN a cles identiques, ponctuation ASCII (ni tiret long, ni fleche, ni points de suspension en un caractere, ni point median), dates jj/mm/aaaa, `authStore.hasRole()`.
- PowerSync : toute colonne qui traverse un formulaire hors ligne passe par les quatre couches (AppSchema.js, ecriture locale, DossierConnector PUT et PATCH, passerelle) ; ne jamais faire confiance a `op.opData` sur PATCH (relire la ligne locale complete).
- Migrations Alembic a la suite de `035_spiritual_notes` (ids <= 32 caracteres), ajout seulement, miroir dans `ci/schema_only.sql`, appliquees a la base de developpement ; verifier les contraintes CHECK avant de decrire un champ comme libre.
- Heure : `utils/business_time.py` (Africa/Douala) partout.
- Les guides utilisateur sont mis a jour a la fin (laboratoire, reception, admin) ; le chantier 8 (deploiement) reste en pause et reprend apres.

## Review Focus

- Une secretaire (et tout role non autorise) n'obtient jamais `pregnancy_*` ni `gestational_age_weeks`, y compris via liste de patients, dossier, caisse, recherche, export, resultat de laboratoire et PowerSync (regles de synchronisation) ; test par role et par route (tache B2).
- Age aux bornes : 0 jour, 6, 7, 13, 14 jours, 27, 28, 29, 30, 31 jours, 12 mois, fin de mois, annee bissextile, naissance le 29 fevrier, date de naissance dans le futur, age inconnu ; jamais « 0 ans » pour un nourrisson (tache B1).
- Deux plages qui se chevauchent, plage avec seulement une borne, plage SA seule contre plage age seule : resultat deterministe (tache B3).
- Un resultat valide est reimprime identique apres renommage d'un parametre, changement d'unite, de norme ou d'ordre dans le catalogue (tache C3, D3).
- Deux receptions simultanees ou hors ligne n'obtiennent jamais le meme numero de dossier ; le rang ne se reutilise pas ; le 1er janvier remet le compteur a zero ; un jour sans enregistrement ne fait pas avancer le compteur (tache A2).
- Un laborantin sans `is_head_lab`, une secretaire, un medecin ne peuvent pas modifier le catalogue (403 sur chaque route d'ecriture) ; un changement de prix est refuse a la cheffe du laboratoire (tache C2).
- Un nom de prescripteur externe tres long, vide, avec caracteres speciaux ou balises HTML est borne ou refuse et ne casse pas le PDF (tache A1, D2).

---

## Sous-projet A : prescripteur externe et numero de dossier

### Task A1: Prescripteur libre du patient externe

**Files:**
- Create: `alembic/versions/036_lab_external_prescribers.py`, `models/lab.py` (ajout du modele `LabExternalPrescriber`), `tests/test_lab_external_prescriber.py`, `ah2-admin-web/tests/labExternalPrescriber.test.mjs`
- Modify: `repositories/lab_repo.py`, `controller/lab_controller.py`, `api_backend/backend_app/routes/labo/lab_endpoints.py`, `labo_schemas.py`, `ah2-admin-web/src/views/modules/labo/LabReception.vue`, `ah2-admin-web/src/i18n.js`, `ci/schema_only.sql`

**Interfaces:**
- Produces: `format_prescriber(title: str, name: str) -> str` (dans `utils/lab_prescriber.py`, titres autorises {Dr, I.D.E., Fr, Br, M., Mme, Volontaire, Autre}, nom nettoye et borne a 80 caracteres, rejette vide) ; `GET /lab/external-prescribers?q=` (suggestions, 20 max, roles laboratoire) ; `LabExternalPrescriber(title, name, last_used_at)`.

- [ ] **Step 1: Tests** : `test_format_prescriber_joins_title_and_name`, `test_rejects_empty_name_and_unknown_title`, `test_name_bounded_and_html_stripped`, `test_internal_patient_path_unchanged` (la reception d'un patient interne n'accepte et n'ecrit rien de nouveau), `test_external_batch_stores_prescribed_by_name`, `test_suggestions_ordered_by_recent_use_and_deduplicated`, `test_suggestions_roles` ; web : le champ n'apparait que pour un patient externe, titre obligatoire, memoire des noms.
- [ ] **Step 2: Migration 036**, modele, depot, controleur, route, miroir `ci/schema_only.sql`.
- [ ] **Step 3: UI** dans `LabReception.vue` : pour un patient externe, titre (liste) + nom libre avec suggestions ; patient interne : aucun changement. Verifier la saisie hors ligne (ecriture locale existante de la reception) : si le champ passe par un formulaire hors ligne, les quatre couches.
- [ ] **Step 4: Tests serveur et web, build.** **Step 5: Commit** (le controleur decide).

### Task A2: Numero de dossier `NNN/NN du JJ/MM/AAAA`

**Files:**
- Create: `alembic/versions/037_lab_dossier_numbers.py`, `utils/lab_dossier.py`, `tests/test_lab_dossier_number.py`
- Modify: `models/lab.py`, `repositories/lab_repo.py`, `controller/lab_controller.py`, `ci/schema_only.sql`, `ah2-admin-web/src/views/modules/labo/LabReception.vue` (affichage), `powersync/sync-config.yaml` si la reception hors ligne lit ces champs

**Interfaces:**
- Produces: colonnes sur `lab_results` : `dossier_year` (int), `dossier_counter` (int), `dossier_rank` (int), nulles tant que non attribuees ; table `lab_dossier_days(year, day date, counter)` unique (year, day) ; `assign_dossier(session, patient_key, day: date) -> DossierNumber(year, counter, rank)` sous verrou consultatif PostgreSQL ; `format_dossier(number, day) -> str` (`"289/02 du 08/10/2026"`, compteur sur 3 chiffres, rang sur 2) ; unicite (dossier_year, dossier_counter, dossier_rank, patient_key) ; `patient_key` = `patient_id` ou une cle stable de l'externe (nom normalise + age + sexe + telephone) pour partager le rang entre les examens d'un meme patient le meme jour.

- [ ] **Step 1: Tests** : `test_first_dossier_of_day_advances_counter`, `test_same_patient_same_day_shares_rank_and_counter`, `test_second_patient_gets_next_rank`, `test_no_registration_day_does_not_advance_counter`, `test_new_year_resets_counter_to_001`, `test_concurrent_assignments_never_collide` (threads), `test_format_dossier_padding`, `test_offline_provisional_reference_replaced_by_official_number_on_sync`, `test_unassigned_result_cannot_be_printed`.
- [ ] **Step 2: Migration, modele, `assign_dossier` (verrou `pg_advisory_xact_lock`), integration a l'enregistrement du passage et a la synchronisation.**
- [ ] **Step 3: Affichage** du numero a la reception et dans la liste ; reference temporaire visible hors ligne. **Step 4: Tests, commit.**

---

## Sous-projet B : age precis et grossesse

### Task B1: Calcul et formatage de l'age

**Files:**
- Create: `utils/lab_age.py`, `tests/test_lab_age.py`

**Interfaces:**
- Produces: `age_in_days(birth: date, ref: date) -> int` (leve `ValueError` si naissance posterieure) ; `format_age(days: int) -> str` selon la regle des contraintes ; `age_from_external(value: int, unit: str) -> int` (unites `jours`, `semaines`, `mois`, `ans` -> jours, mois = 30,4375 jours arrondi, ans = 365,25) ; `parse_external_age(info: dict) -> int | None` (lit `age_days` sinon l'ancien `age` en annees).

- [ ] **Step 1: Tests** de toutes les bornes du Review Focus (liste exacte d'assertions : 0 -> « 0 jour », 1 -> « 1 jour », 6 -> « 6 jours », 7 -> « 1 semaine », 13 -> « 1 semaine 6 jours », 14 -> « 2 semaines », 17 -> « 2 semaines 3 jours », 27/28/29/30/31 jours, 45 jours, 100 jours, 365 jours -> « 1 an », 540 -> « 1 an 6 mois », 1825 -> « 4 ans 11 mois », 1826 -> « 5 ans », naissance 29 fevrier, bissextile) ; les libelles exacts viennent de la fiche (singulier/pluriel, casse) et sont figes dans les tests.
- [ ] **Step 2: Implementer.** **Step 3: Tests, commit.**

### Task B2: Statut de grossesse du patient (serveur) et visibilite

**Files:**
- Create: `alembic/versions/038_pregnancy_fields.py`, `utils/pregnancy_visibility.py`, `tests/test_pregnancy_fields.py`
- Modify: `models/patient.py`, patients schemas/mapping/endpoints (lecture et ecriture), `models/lab.py` (`gestational_age_weeks`), `api_backend/backend_app/routes/patients/*`, caisse/patient listes qui renvoient des patients, export patient, `powersync/sync-config.yaml`, `ci/schema_only.sql`

**Interfaces:**
- Produces: colonnes `patients.pregnancy_status` (CHECK in enceinte, non_enceinte, inconnu ; defaut inconnu), `patients.expected_delivery_date` (date, nulle), `patients.pregnancy_program_number` (varchar(50), nul) ; `lab_results.gestational_age_weeks` (CHECK 0 a 45) ; `can_see_pregnancy(user) -> bool` (medecin, infirmier, laborantin, admin, promoteur ; PAS secretaire ni les autres) ; `strip_pregnancy_fields(payload: dict, user) -> dict` appliquee a toutes les sorties de patient ; ecriture refusee (403) aux roles non ecrivains.

- [ ] **Step 1: Tests par role et par route** (matrice : secretaire, laborantin, medecin, nurse, admin, promoteur, assistant, toxico, psychologue, stock, production, conseiller spirituel) : lecture patient par id, liste, recherche, dossier consolide, caisse (patient joint), export, resultat de laboratoire ; ecriture ; aucune cle `pregnancy_*` ni `expected_delivery_date` ni `gestational_age_weeks` dans les reponses d'un role non autorise ; PowerSync : la regle de synchronisation du secretariat n'inclut pas ces colonnes.
- [ ] **Step 2: Migration, modele, filtres de sortie centralises, regles de synchronisation.**
- [ ] **Step 3: Tests, commit.**

### Task B3: Plages de reference : jours, SA, selection deterministe

**Files:**
- Create: `alembic/versions/039_reference_ranges_days_ga.py`, `tests/test_lab_reference_selection.py`
- Modify: `utils/lab_reference.py`, `repositories/lab_repo.py` (`_patient_bio`, filtre ligne ~593), `models/lab.py`, `ci/schema_only.sql`

**Interfaces:**
- Produces: colonnes `reference_ranges.age_min_days`, `age_max_days` (nulles = ouvertes), `ga_min_weeks`, `ga_max_weeks` (nulles) ; migration de donnees des plages existantes (`age_min*365`, `(age_max+1)*365-1`) ; ajout des lignes pediatriques standard ; `select_range(ranges, sex: str, age_days: int | None, ga_weeks: int | None) -> Range | None` deterministe selon les contraintes.

- [ ] **Step 1: Tests** : migration des anciennes bornes, nouveau-ne a 28 jours / enfant a 29 jours, chevauchement, borne unique, SA seule, age inconnu, sexe X, ties par id, ancien comportement (annees) conserve pour les plages non migrees.
- [ ] **Step 2: Migration et selection ; remplacer le calcul en annees entieres par `lab_age`.** **Step 3: Tests, commit.**

### Task B4: Saisie age et grossesse (ecrans) et rapport de subvention

**Files:**
- Create: `api_backend/backend_app/routes/labo/pregnancy_report_endpoints.py`, `ah2-admin-web/src/views/modules/labo/PregnancyReport.vue`, `tests/test_pregnancy_report.py`, `ah2-admin-web/tests/labAgePregnancy.test.mjs`
- Modify: `LabReception.vue` (age avec unite ou date de naissance, SA, statut pour l'externe), fiche patient web (bloc grossesse masque a la secretaire par `hasRole`), `PatientDetailView.vue`, router et menu (rapport : promoteur et admin), `i18n.js`, passerelles, quatre couches PowerSync pour `gestational_age_weeks` et l'age externe

**Interfaces:**
- Produces: `GET /lab/reports/pregnancy?from&to` (roles promoteur, admin) -> lignes (numero de dossier patient, nom, numero de suivi, SA, examens valides, date de validation) + export PDF ; la SA est proposee a partir de la DPA et de la date de reference quand la DPA est connue.

- [ ] **Step 1: Tests** (serveur : filtres de dates par validation, inclusion des externes, roles ; web : champs masques a la secretaire, age en unites, SA bornee). **Step 2: Implementer.** **Step 3: Verification navigateur reelle** (age « 2 semaines 3 jours » sur la fiche et la reception, secretaire sans champ de grossesse, rapport). **Step 4: Commit.**

---

## Sous-projet C : catalogue modifiable par le laboratoire

### Task C1: Modele du catalogue etendu et donnees de depart

**Files:**
- Create: `alembic/versions/040_lab_catalogue_extended.py`, `scripts/seed_lab_catalogue.py`, `docs/laboratory-templates.md` (liste des familles et des examens, SANS donnees patient), `tests/test_lab_catalogue_seed.py`
- Modify: `models/lab.py`, `models/organization_config.py` (numero d'agrement, texte du pied de page, libelle de signature par defaut), `ci/schema_only.sql`, `scripts/export_reference_data.py` / `import_reference_data.py`, `powersync/sync-config.yaml` (nouvelles colonnes du catalogue)

**Interfaces:**
- Produces: `examens` : `section` (texte), `method` (texte nul), `layout_family` (CHECK in table, three_columns, label_value, narrative, boxed ; defaut label_value), `signature_label` (texte nul), `print_title` (texte nul), `sort_order` ; `parametres` : `print_label`, `result_kind` (CHECK in numeric, text, choice, pos_neg), `choices` (jsonb nul) en conservant `type_valeur`/`input_type` existants ; seed idempotent des examens des fiches (liste dans `docs/laboratory-templates.md`).

- [ ] **Step 1: Tests** : seed idempotent, aucun examen existant detruit, tous les examens des fiches presents avec famille, ordre des parametres egal a celui des fiches (liste de controle), serologies qualitatives en pos_neg, unites en mg/dl pour les variantes, import de production inclut les nouvelles colonnes et met les prix a 0.
- [ ] **Step 2: Migration et modeles ; seed a partir de l'analyse (le sous-agent lit `lab-templates-analysis.md` et `docs/laboratory/` en lecture seule pour les libelles, jamais pour copier des patients).**
- [ ] **Step 3: Regenerer l'export de reference ; tests ; commit.**

### Task C2: Droit d'ecriture : cheffe du laboratoire et routes d'edition

**Files:**
- Create: `alembic/versions/041_user_is_head_lab.py`, `tests/test_lab_catalogue_write.py`
- Modify: `models/user.py` (`is_head_lab`), `users_schemas.py` / `users_endpoint.py` (creation et modification, 4 endroits comme `is_head_nurse`), `UserModal.vue` et `userStore.js`, `auth.js` (forme de l'utilisateur), `lab_endpoints.py` (routes d'ecriture du catalogue), `lab_controller.py`

**Interfaces:**
- Produces: `users.is_head_lab` (booleen, defaut faux) ; `can_edit_lab_catalogue(user) -> bool` (admin, ou role laborantin avec `is_head_lab`) ; routes `POST/PUT/DELETE /lab/catalogue/exams`, `/lab/catalogue/parameters`, `/lab/catalogue/ranges` (garde `can_edit_lab_catalogue`, jamais le prix) ; reordonnancement `PUT /lab/catalogue/exams/{id}/order` ; audit avant/apres ; suppression d'un examen ou parametre deja utilise par un resultat refusee (409) : desactivation a la place.

- [ ] **Step 1: Tests** : matrice de roles sur chaque route d'ecriture (laborantin simple, medecin, secretaire, stock... : 403), prix intouchable pour la cheffe, audit ecrit sans donnees sensibles, suppression d'un element utilise refusee, le drapeau ne s'attribue que par l'admin et que sur un laborantin, creation d'utilisateur ne perd pas le drapeau (leçon du chantier rotation infirmiers : POST et PUT et liste et authStore).
- [ ] **Step 2: Implementer.** **Step 3: Tests, commit.**

### Task C3: Copie figee a la validation

**Files:**
- Create: `alembic/versions/042_lab_result_snapshot.py`, `tests/test_lab_result_snapshot.py`
- Modify: `models/lab.py` (`lab_results.print_snapshot` jsonb nul), `repositories/lab_repo.py` / `lab_controller.py` (validation), `ci/schema_only.sql`

**Interfaces:**
- Produces: `build_print_snapshot(result, exam, params, ranges, patient_bio) -> dict` (famille, titre, section, methode, signature, age affiche, SA, et par parametre : libelle, unite, norme imprimee, ordre, valeur) ecrit par le serveur a la validation, immuable ; un resultat sans copie reste imprime par l'ancien PDF.

- [ ] **Step 1: Tests** : copie creee a la validation, jamais modifiee ensuite ; renommer un parametre, changer unite, norme, ordre apres validation ne change pas la copie ; amendement d'un resultat valide (flux existant `lab_result_amendments`) cree une nouvelle copie tracee ; resultat sans copie -> ancien chemin.
- [ ] **Step 2: Implementer.** **Step 3: Tests, commit.**

### Task C4: Ecran de gestion du catalogue

**Files:**
- Create: `ah2-admin-web/src/services/LabCatalogueGateway.js`, `ah2-admin-web/src/components/labo/CatalogueExamForm.vue`, `CatalogueParamTable.vue`, `CatalogueRangeEditor.vue`, `ah2-admin-web/tests/labCatalogue.test.mjs`, `ah2-admin-web/tests/labCatalogueContract.test.mjs`
- Modify: `ah2-admin-web/src/views/modules/labo/LabConfig.vue`, `router/index.js`, menu, `i18n.js`

**Interfaces:**
- Consumes: routes de C2. Produces: liste des examens par section ; edition de l'examen (nom imprime, section, methode, famille, signature, ordre), des parametres (libelle, unite, type, choix, ordre par glisser ou fleches), des plages (sexe, age avec unite, SA, min, max ou texte) ; lecture seule pour les laborantins sans le drapeau ; prix visible mais non modifiable ici ; en ligne seulement (message clair sinon, brouillon conserve) ; confirmation avant suppression ; avertissement « les resultats deja valides gardent leurs anciennes normes ».

- [ ] **Step 1: Tests** (validation pure des plages : min <= max, pas de chevauchement exact, age avec unite ; contrat : controles reserves a `can_edit`, i18n FR/EN, ASCII). **Step 2: Implementer.** **Step 3: Verification navigateur reelle** (cheffe edite une unite, un laborantin simple ne peut pas, un resultat valide garde l'ancienne norme a la reimpression). **Step 4: Commit.**

---

## Sous-projet D : PDF de resultats fidele par examen

### Task D1: Cadre commun et polices

**Files:**
- Create: `api_backend/backend_app/utils/templates/lab_sheet_base.html`, `lab_sheet.css`, `tests/test_lab_sheet_frame.py`
- Modify: `deploy/Dockerfile.api` (`fonts-liberation`), `api_backend/backend_app/utils/pdf_header.py` / `_pdf_header.html` seulement si un champ de configuration manque

**Interfaces:**
- Produces: gabarit de base Lettre US : en-tete et pied dynamiques (`get_pdf_header_context`), ligne « Yaounde, le <date en lettres> » (date de validation), titre, bloc patient (`format_dossier`, nom, age formate, sexe, grossesse et SA seulement si renseignees, « Examen demande par »), zone de corps (bloc `body`), Conclusion et NB (deux champs libres), signature a droite avec le libelle de l'examen.

- [ ] **Step 1: Tests** (PDF genere : une page Lettre US ; en-tete issu de la configuration modifiee ; polices Liberation embarquees ; champs vides = pas de ligne vide ; HTML du prescripteur et du nom echappe ; contournement connu de la sous-selection de polices : lire le texte via pypdf comme les autres tests de PDF). **Step 2: Implementer.** **Step 3: Tests, commit.**

### Task D2: Quatre gabarits de famille + formulaire en cases

**Files:**
- Create: `lab_sheet_table.html`, `lab_sheet_three_columns.html`, `lab_sheet_label_value.html`, `lab_sheet_narrative.html`, `lab_sheet_boxed.html`, `tests/test_lab_sheet_families.py`

**Interfaces:**
- Consumes: la copie figee de C3 et le cadre de D1. Produces: un gabarit par famille ; pour chaque famille, rendu fidele des libelles, de l'ordre, des unites et des normes de la copie ; texte long et caracteres speciaux sans debordement ; une fiche tient sur une page.

- [ ] **Step 1: Tests** (un resultat type par famille avec les libelles et l'ordre de la fiche correspondante : hemogramme avec blocs NUMERATION GLOBULAIRE et FORMULE SANGUINE, biochimie, ASLO, typhoide, KOAP, ECBU, Chlamydiae ; assertions sur l'ordre et les libelles lus dans le PDF par pypdf ; une seule page ; norme H/F imprimee comme la fiche). **Step 2: Implementer a partir de `docs/laboratory-templates.md` (sans donnees patient).** **Step 3: Rendre en PNG et comparer visuellement avec la page correspondante du PDF du laboratoire (lecture seule, hors depot) ; ajuster.** **Step 4: Tests, commit.**

### Task D3: Branchement : impression, reimpression, un PDF multi-pages

**Files:**
- Modify: `api_backend/backend_app/utils/pdf_generator.py`, `routes/labo/lab_endpoints.py`, `controller/lab_controller.py`, `LabHistory.vue`, `MedicalLabResults.vue` (boutons d'impression), `tests/test_lab_pdf_routes.py`

**Interfaces:**
- Produces: `GET /lab/results/{id}/pdf` et la route par passage : un resultat valide avec copie figee -> gabarit de sa famille ; sans copie -> ancien PDF ; passage a plusieurs examens -> un PDF, une page par examen ; fiche non imprimable tant que le numero de dossier n'est pas attribue (message clair) ; droits de lecture inchanges (roles actuels) ; la secretaire n'obtient pas la grossesse dans le PDF si elle y a acces.

- [ ] **Step 1: Tests** (famille correcte, ancien chemin conserve, multi-pages, reimpression identique apres changement du catalogue, role non autorise 403, numero absent bloque). **Step 2: Implementer.** **Step 3: Tests, commit.**

### Task D4: Verification complete et guides

**Files:**
- Modify: `docs/user-guides/src/*` (laboratoire, reception, admin, promoteur), `docs/superpowers/SUIVI-AVANCEMENT.md`, memoire du projet

- [ ] **Step 1: Navigateur reel** de bout en bout : reception d'un patient externe avec prescripteur libre, age de 2 semaines, patiente enceinte avec SA, saisie et validation, PDF fidele, reimpression, edition du catalogue par la cheffe, secretaire sans grossesse, rapport de subvention, hors ligne puis synchronisation (numero attribue).
- [ ] **Step 2: Suites completes** (backend, web, build) : seuls les echecs connus de donnees de demonstration sont acceptes.
- [ ] **Step 3: Guides** (anglais, outillage existant) et PDF des guides touches ; suivi mis a jour ; revue finale de la branche par le modele le plus capable ; commits par theme apres accord.
