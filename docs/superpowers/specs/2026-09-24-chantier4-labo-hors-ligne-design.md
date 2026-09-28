# Chantier 4, sous-projet 5 — Labo hors ligne

Date : 2026-09-24 · Statut : validé en brainstorming par l'utilisateur

## Contexte

Quatrième extension de l'architecture offline-first PowerSync (après rendez-vous, dossier
patient medecin/nurse, caisse/secrétariat, formulaires hors ligne). Le rôle **laborantin** n'a
encore aucune synchronisation PowerSync — `connectPowerSync()` n'est gaté que pour `medecin`,
`nurse`, `secretaire` dans `auth.js`/`App.vue`.

Le module labo (`api_backend/backend_app/routes/labo/`) a trois écrans utilisés par le
laborantin au quotidien :
- **Réception** (`/labo/reception`) : enregistre un dossier (un ou plusieurs examens) pour un
  patient interne (recherché, avec pré-remplissage des examens déjà prescrits par un médecin)
  ou externe (saisi en texte libre).
- **Paillasse** (`/labo/paillasse`) : liste des dossiers `pending`/`partial`, ouvre la saisie.
- **Saisie/validation** (`/labo/validation/:id`) : entre les valeurs par paramètre, calcule
  l'interprétation (normal/anormal) par comparaison aux valeurs de référence, marque le dossier
  `completed`.

Hors périmètre : configuration des examens/paramètres (`/labo/config`, `admin`/`ToxicoManager`
uniquement), impression PDF (générée serveur), historique (lecture, déjà couvert par
`clinical_lab_results` pour medecin/nurse).

## Décisions utilisateur (2026-09-24)

1. **Réception ET saisie hors ligne**, y compris sur un dossier reçu hors ligne dans le même
   geste (enchaînement complet, même esprit que la décision structurante du sous-projet 4).
2. **Patients internes ET externes** enregistrables hors ligne à la réception.
3. **Un seul code LAB partagé** pour plusieurs examens de la même réception (comportement
   actuel en ligne) — pas un code par examen.
4. **Approche A** retenue pour l'enchaînement : le serveur résout le dossier labo par son
   `uuid`, les valeurs sont envoyées par paramètre (pas par identifiant de ligne serveur).

## Hors périmètre

- Configuration des examens/paramètres/valeurs de référence hors ligne — lecture seule.
- Impression PDF, historique paginé, statistiques — HTTP uniquement.
- Suppression d'un dossier labo hors ligne (déjà HTTP-only en ligne, `admin` seulement).
- Rôles `admin`/`ToxicoManager` — comportement HTTP inchangé (ils utilisent aussi ces écrans,
  mais ne sont pas concernés par l'écriture locale).

## Architecture

Motif inchangé des sous-projets précédents : écriture **toujours locale** pour `laborantin`,
lecture HTTP d'abord avec secours local uniquement sur coupure réelle (`!err.response`),
connecteur unique `DossierConnector.js`, `authStore.hasRole()`.

### 1. Synchronisation pour le rôle laborantin

- **Garde `connectPowerSync`** (`auth.js`, `App.vue`) étendu à `laborantin` — tâche explicite du
  plan, leçon du sous-projet 3.
- `patients_lookup`, `doctors_lookup`, `exam_catalog` déjà synchronisés (sous-projets 1/4) —
  aucun nouveau stream, `laborantin` est simplement ajouté à leur souscription dans `client.js`
  (recherche patient interne, nom du médecin prescripteur, catalogue d'examens).
- 5 nouveaux streams, lecture seule :
  - `lab_pending_prescriptions` : prescriptions médicales actives de type examen, pas encore
    transformées en dossier labo — `FROM prescriptions AS lab_pending_prescriptions`, filtre
    `is_lab_order = true AND status = 'active'`. Alimente le pré-remplissage des examens à la
    réception d'un patient interne.
  - `lab_active_results` : dossiers `lab_results` `pending`/`partial` — la paillasse et les
    dossiers ouvrables en saisie hors ligne.
  - `lab_active_result_details` : `lab_result_details` des dossiers ci-dessus — les valeurs déjà
    saisies (saisie partielle reprise hors ligne).
  - `reference_lab_params` : `parametres` (paramètres définis pour chaque examen).
  - `reference_lab_ranges` : `reference_ranges` (valeurs de référence par âge/sexe) — affichage
    indicatif uniquement côté client, l'interprétation qui fait autorité reste calculée serveur.

### 2. Réception hors ligne (patient interne et externe)

**Backend :**
- Migration : `lab_results` gagne une colonne `uuid` (n'existe pas encore, contrairement à
  `patients`/`medical_records`/`prescriptions` — à créer avec `DEFAULT gen_random_uuid()`,
  index **unique**, une valeur par ligne) et une colonne `batch_uuid` (texte, nullable —
  identifiant de lot généré côté client, **volontairement partagé** par toutes les lignes d'une
  même réception à plusieurs examens ; index simple, non unique, pour accélérer la recherche
  "un autre item de ce lot a-t-il déjà été créé ?").
- `POST /labo/results/batch` accepte `uuid`/`batch_uuid` par item (le payload est déjà une
  liste). `create_batch_results` : pour chaque item, si `batch_uuid` correspond à un dossier
  déjà créé côté serveur (rejeu d'un item déjà envoyé, ou un autre item du même lot arrivé
  avant dans une transaction PowerSync antérieure), réutilise son `code_lab_patient` au lieu
  d'en générer un nouveau — remplace la logique actuelle "le premier de la boucle génère, les
  suivants réutilisent" (qui suppose un seul appel HTTP synchrone, invalide hors ligne où
  chaque item part dans sa propre opération CRUD).
- Chaque item accepte aussi `patient_uuid` (résolution comme pour consultation/prescription,
  réutilise `resolve_patient_id`) pour un patient interne créé hors ligne dans le même geste.
- Patient externe : `external_patient_info` (déjà un champ JSONB existant) — aucun changement
  nécessaire, transite tel quel.

**Client :**
- `labStore.createBatchRequest` : pour `laborantin`, écrit en local (une ligne par examen
  demandé, `batch_uuid` partagé, `patient_id` ou `patient_uuid` selon résolution du patient).
- Correctif au passage (bug réel repéré en lisant le code, pas introduit par ce chantier) :
  `LabReception.vue` lit `selectedPatient.value.prescription_id` mais le payload envoyé au
  backend ignore ce champ pour marquer la prescription source comme traitée — le worklist
  médecin (`get_lab_worklist`) recalcule son exclusion via `origin_prescription_id` sur
  `lab_results`, jamais réellement lié depuis la réception interne. À corriger dans ce
  chantier : propager `origin_prescription_id` dans le payload de réception interne.
- Recherche patient interne + pré-remplissage des examens prescrits : secours local sur
  `patients_lookup` (déjà synchronisé) croisé avec `lab_pending_prescriptions` (nouveau).

### 3. Paillasse et saisie hors ligne

- `labStore.fetchDashboardData`/paillasse : secours local sur la table `lab_results` filtrée
  `status IN ('pending', 'partial')`, jointe à `lab_result_details`/`parametres` pour
  reconstituer la structure attendue par `LabTechnician.vue`/`LabValidation.vue`.
- `labStore.saveValues` : pour `laborantin`, écriture locale des valeurs par
  `(result_uuid, parametre_id)` — la table locale `lab_result_details` n'a pas besoin de son
  propre identifiant serveur, une valeur est unique pour ce couple.
- `PUT /labo/results/{id}/values` gagne une variante résolue par uuid (même motif que
  `resolve_medical_record_id`) : `result_uuid` optionnel, résolu en `result_id` côté serveur.
  L'interprétation (normal/anormal/flag) reste calculée **côté serveur uniquement** à la
  synchronisation — jamais recalculée localement (évite de dupliquer la logique de
  `_interpret_single_detail`, et les valeurs de référence par âge/sexe sont déjà lues en local
  à titre indicatif uniquement, jamais faisant autorité).
- Dossier marqué `completed` hors ligne : `mark_completed` transite tel quel, le serveur
  recalcule le statut final (`completed`/`partial`) à la synchronisation, comme aujourd'hui.

### 4. Quarantaine — réutilisation du mécanisme existant

Un dossier labo refusé définitivement (examen supprimé du catalogue entre-temps, patient en
échec de synchronisation) suit le même mécanisme que le sous-projet 4 : table
`sync_quarantine` (déjà en place, `localOnly`), nouveau `kind: 'lab_result'`. Ses valeurs
saisies localement (si la saisie a eu lieu hors ligne avant l'échec de la réception, cas rare
mais possible si l'examen a été retiré du catalogue entre la réception et l'envoi) sont
retenues avec lui — même garde `isPatientQuarantined`-style, adaptée en
`isLabResultQuarantined`. Pas d'écran dédié supplémentaire : `SyncFailuresView.vue` (déjà
existant) étend son affichage aux dossiers labo en quarantaine.

## Gestion d'erreurs

- Coupure réseau pendant l'envoi : non fatal, retry automatique (comportement existant).
- Rejeu d'un item déjà accepté (même `uuid`) : idempotent, renvoie le dossier existant sans
  dupliquer (même motif que `POST /patients/`).
- Examen supprimé du catalogue entre la réception hors ligne et l'envoi (`examen_id`
  introuvable) : 422 → quarantaine du dossier (jamais un 500, jamais une perte silencieuse).
- Patient interne en quarantaine (créé hors ligne, refusé) : le dossier labo qui le référence
  rejoint la quarantaine au lieu d'être envoyé — même motif que consultation/prescription.

## Tests

Backend (pytest) :
- Migration : colonnes `uuid`/`batch_uuid` ajoutées avec index unique, aucun doublon existant.
- `POST /labo/results/batch` avec `uuid`/`batch_uuid` : code LAB partagé correctement entre 2
  items du même lot envoyés dans 2 appels HTTP séparés (simule 2 opérations CRUD distinctes).
- Rejeu d'un item avec le même `uuid` : idempotent.
- `PUT /labo/results/{id}/values` avec `result_uuid` : résolution correcte ; uuid inconnu → 422.
- `origin_prescription_id` propagé depuis une réception interne liée à une prescription.

Frontend : build production vert à chaque tâche.

Manuel (navigateur, **vraie coupure réseau**, jamais DevTools) :
1. Laborantin : réception hors ligne d'un patient interne avec 2 examens prescrits par un
   médecin → saisie des valeurs hors ligne → reconnexion → vérifier un seul code LAB côté
   serveur pour les 2 examens, et que la prescription source apparaît traitée côté médecin.
2. Réception d'un patient externe hors ligne → reconnexion → dossier présent, code attribué.
3. Examen supprimé du catalogue pendant la coupure → reconnexion → dossier en quarantaine,
   visible dans "Échecs de synchronisation", jamais perdu silencieusement.
4. Non-régression : `admin`/`ToxicoManager` sur les mêmes écrans, comportement HTTP inchangé ;
   les 4 sous-projets précédents (RDV, dossier patient, caisse, formulaires) toujours
   fonctionnels.

## Rappels de vérification pour le plan et les revues

- Alias `FROM <source> AS <table_locale>` obligatoire partout où les noms diffèrent.
- Garde `connectPowerSync` (`auth.js`/`App.vue`) : tâche EXPLICITE, pas supposée acquise.
- Identifiant de révision Alembic ≤ 32 caractères (piège déjà rencontré).
- Toute référence à une entité créée dans le même lot hors ligne (patient, prescription,
  dossier labo) doit être résolue par uuid côté serveur dès la conception — jamais un
  `server_id` local gardé en attente d'un re-téléchargement (bug Critical déjà corrigé deux
  fois : sous-projet 4, patient et consultation).
- Vérifier `docker ps` (conteneurs `powersync-*` stables) avant tout test manuel.
