# Chantier 4, sous-projet 4 — Formulaires réellement utilisables hors ligne

Date : 2026-09-24 · Statut : validé en brainstorming par l'utilisateur (approche A + sections 1-2)

## Contexte et diagnostic

Test en **vraie coupure réseau** (uvicorn arrêté, pas le toggle DevTools) après la clôture du
sous-projet 3. Les sous-projets 2 (médecin/nurse) et 3 (secrétaire) avaient câblé l'écriture locale
dans les *stores*, mais pas les **dépendances des formulaires**, qui restent HTTP-only. Hors ligne,
les formulaires sont donc inutilisables même si le store sait écrire localement.

Constats vérifiés dans le code :

| Écran | Blocage hors ligne | Source |
|---|---|---|
| Consultation (medecin/nurse) | motif obligatoire, liste des motifs chargée uniquement par HTTP → liste vide | `MedicalRecordModal.vue:253`, `medicalRecordStore.fetchMotifs` |
| Consultation / prescription | recherche patient par code HTTP-only → "patient introuvable" | `composables/usePatientLookup.js:43` |
| Prescription (medecin/nurse) | modification jamais câblée hors ligne | `prescriptionStore.updatePrescription` |
| Prescription | catalogue d'examens HTTP-only | `prescriptionStore.fetchExamTypes` |
| Caisse (secrétaire) | recherche d'examen HTTP-only | `CaisseInvoiceModal.vue`, `LabGateway.getAllExams` |
| Patients (tous rôles) | création jamais câblée hors ligne, liste sans secours local | `patientStore.addPatient`, `patientStore.fetchPatients` |

## Décisions utilisateur (2026-09-24)

1. **Enchaînement complet** : un patient créé hors ligne peut recevoir immédiatement consultation et
   prescription hors ligne, avant le retour du réseau.
2. **Secrétaire : tout patient** (spirituel ou clinique) enregistrable hors ligne, comme en ligne.
3. **Doublon refusé à la sync** (`national_id` déjà existant) : signalement + **résolution
   manuelle**, jamais de rattachement automatique (risque de dossier médical attaché à la mauvaise
   personne sur une faute de frappe).
4. **Approche A** retenue pour l'enchaînement : le serveur résout le patient par son `uuid`.
5. **Quarantaine locale** retenue pour ne jamais perdre les consultations/prescriptions d'un patient
   refusé.
6. Pas de recherche de consultation spirituelle hors ligne pour la secrétaire (décision antérieure,
   inchangée).

## Hors périmètre

- Fiabilisation du garde-fou `caisse.upload_error` via la quarantaine (risque I3) : réutilisable plus
  tard, pas dans ce chantier.
- Génération du code AH2 côté client : le code reste attribué par le serveur (`patient_repo.
  generate_patient_code` + suffixe d'unicité) ; hors ligne le patient affiche "code en attente".
- Modification/suppression de patient hors ligne, suppression de prescription hors ligne.
- Rendez-vous : spécialités (`/appointments/specialties`) non concernées ici.
- Rôles admin/manager/assistant/ToxicoManager : comportement HTTP inchangé.

## Architecture

Motif inchangé des sous-projets précédents : écriture **toujours locale** pour les rôles concernés
(`medecin`, `nurse`, `secretaire`), lecture HTTP d'abord avec secours local uniquement sur coupure
réelle (`!err.response`), connecteur unique `DossierConnector.js`, contrôle de rôle via
`authStore.hasRole()`.

### 1. Catalogues de référence synchronisés (lecture seule)

Deux nouveaux streams dans `powersync/sync-config.yaml`, **alias `FROM … AS …` obligatoire** (bug déjà
rencontré deux fois sur ce projet) :

- `reference_exam_catalog` : `SELECT id::text AS id, id AS server_id, code, nom, categorie,
  prix::text AS prix FROM examens AS exam_catalog`
- `reference_motifs` : `SELECT code AS id, code, label_fr, label_en FROM motif_translations AS
  motifs`

Tables locales correspondantes dans `AppSchema.js` : `exam_catalog`, `motifs`. Souscrites pour
`medecin`, `nurse`, `secretaire` dans `client.js`.

Consommateurs, avec secours local sur coupure :
- `medicalRecordStore.fetchMotifs` → `SELECT * FROM motifs`
- `prescriptionStore.fetchExamTypes` et `LabGateway.getAllExams` (utilisé par la caisse) →
  `SELECT * FROM exam_catalog`, mappé vers la forme de réponse HTTP existante (`id`, `nom`, `prix`,
  `code`, `categorie`) pour ne pas toucher aux templates.

### 2. Recherche patient et liste patients hors ligne

- `usePatientLookup.js` : sur coupure réelle, recherche par code dans la table locale
  `patients_lookup` (déjà synchronisée pour tous les rôles, contient tous les patients non
  supprimés avec leur code).
- `patientStore.fetchPatients` : secours local sur coupure = patients de `patients_lookup` + patients
  créés localement non encore synchronisés (table locale `patients`, `server_id` nul), ces derniers
  affichés avec la mention "code en attente".

### 3. Création de patient hors ligne

**Backend :**
- Migration `010_patients_uuid_unique` : index unique sur `patients.uuid` (colonne déjà présente,
  NOT NULL, défaut `gen_random_uuid()`, mais sans unicité — même situation que K1/migration 004 pour
  les rendez-vous).
- `POST /patients` accepte un `uuid` optionnel. `create_patient()` (procédure stockée) ne prend pas
  d'uuid : `patient_repo.create_patient` fait un `UPDATE patients SET uuid = :uuid WHERE patient_id =
  :new_id` juste après l'insertion, dans la même transaction.
- **Rejeu idempotent** : si `POST /patients` reçoit un `uuid` déjà présent en base (envoi précédent
  commité, réponse perdue par coupure), le backend renvoie **200 avec le patient existant**, sans
  rien créer. C'est un succès rejoué, pas un rejet : il ne doit jamais partir en quarantaine.
- **Vrai rejet** : `national_id` déjà utilisé par un *autre* patient (uuid différent) → **409** via
  `translate_integrity_error`, jamais 500 (un 500 est non fatal et bloquerait la file indéfiniment,
  leçon I2 du sous-projet 3). C'est ce 409 qui déclenche la quarantaine (section 6).

**Client :**
- `patientStore.addPatient` : pour `medecin`/`nurse`/`secretaire`, `INSERT` dans la table locale
  `patients` (id = uuid client), même payload qu'en ligne. La création est **neutre en domaine**,
  comme en ligne : le formulaire n'envoie aucun indicateur clinique/spirituel, ces indicateurs sont
  calculés côté serveur à partir des dossiers existants (chantier 6). Un patient "spirituel" est
  donc un patient créé normalement, qui recevra ensuite une consultation spirituelle ; un patient
  créé par médecin/nurse devient clinique via sa consultation. Le cloisonnement clinique n'est pas
  affecté (`clinical_patients` ne redescend que les patients ayant un dossier médical).
- La table locale `patients` gagne les colonnes du payload de création absentes aujourd'hui
  (`residence`, `national_id`, `assurance`, `father_name`, `mother_name`). "Code en attente" se
  déduit de `server_id` nul, aucune colonne supplémentaire.
- Nouveau case connecteur `patients:PUT` → appel `api.post('/patients/', {..., uuid: op.id})`
  (même appel que `patientStore.addPatient` en ligne ; il n'existe pas de gateway patient dédiée).
- Après création hors ligne, l'écran ouvre la fiche du patient créé (identifiée par son uuid local),
  depuis laquelle consultation et prescription se créent patient pré-sélectionné — pas de recherche
  par code nécessaire pour un patient sans code.

### 4. Enchaînement consultation/prescription → patient créé hors ligne (approche A)

- Tables locales `medical_records` et `prescriptions` : nouvelle colonne `patient_uuid` (texte),
  remplie quand le patient n'a pas encore de `server_id` ; `patient_id` reste utilisé sinon.
- `POST /medical_records` et `POST /prescriptions` acceptent un `patient_uuid` optionnel. Si
  `patient_id` est absent et `patient_uuid` présent, le backend résout `patient_id` via
  `patients.uuid` (index unique de la section 3). Patient introuvable → 422.
- L'ordre est garanti par la file PowerSync (strictement FIFO) : le `patients:PUT` part toujours
  avant les consultations créées ensuite.
- Le chaînage existant prescription → consultation hors ligne (sous-projet 2) reste inchangé.

### 5. Modification de prescription hors ligne

- `prescriptionStore.updatePrescription` : écriture locale (`UPDATE prescriptions … WHERE id = ?`)
  pour `medecin`/`nurse`, même motif que `medicalRecordStore.updateMedicalRecord` (déjà câblé).
- Nouveau case connecteur `prescriptions:PATCH` : relit la ligne locale complète (pas seulement
  `op.opData`, même motif que `appointments:PATCH`) et appelle la route de mise à jour avec le
  `server_id`. Modification d'une prescription pas encore synchronisée : le bouton "modifier" est
  désactivé tant que `server_id` est absent (garde "désactivé tant que non synchronisé", déjà utilisée
  pour la caisse).

### 6. Quarantaine locale des rejets (doublons)

**Problème** : la file d'envoi PowerSync est ordonnée et ne permet pas de mettre une opération de
côté. Si un patient est refusé définitivement (409 doublon `national_id`), ses consultations et
prescriptions suivantes seraient refusées à leur tour (patient introuvable) puis retirées de la file :
perte silencieuse de données médicales. Une colonne d'erreur sur une table synchronisée ne suffit pas
non plus : la ligne rejetée peut être purgée par PowerSync au checkpoint suivant (risque I3).

**Solution** : table **locale uniquement** `sync_quarantine` (`new Table({...}, { localOnly: true })`,
option supportée par `@powersync/common`, vérifiée dans `Table.d.ts`) — jamais synchronisée, jamais
purgée. Colonnes : `kind` (`patient` / `medical_record` / `prescription`), `local_id`,
`patient_uuid`, `payload` (JSON), `error`, `created_at`.

Comportement du connecteur :
- Rejet définitif d'un `patients:PUT` : copie du patient (payload complet + message d'erreur serveur)
  dans `sync_quarantine`, puis `transaction.complete()`.
- Tout `medical_records:PUT` / `prescriptions:PUT` dont le `patient_uuid` correspond à un patient en
  quarantaine : copié dans `sync_quarantine` **au lieu d'être envoyé**, puis retiré de la file. Les
  autres patients continuent de se synchroniser normalement.
- L'écriture en quarantaine est elle-même protégée par try/catch (ne doit jamais faire planter le
  connecteur), même motif que le garde-fou caisse.

Interface :
- Nouvel écran "Échecs de synchronisation" (accessible aux rôles concernés) listant la quarantaine,
  avec le motif du refus.
- Action **"Rattacher à un patient existant"** : saisie d'un code AH2 → résolution du `patient_id`
  (HTTP, donc en ligne) → réinsertion des consultations/prescriptions retenues dans les tables
  locales avec ce `patient_id` (elles repartent dans la file normalement) → suppression des entrées
  de quarantaine correspondantes.
- Badge/compteur visible dans la navigation quand la quarantaine n'est pas vide, pour que le rejet
  ne passe pas inaperçu.

## Gestion d'erreurs

- Coupure réseau pendant l'envoi : non fatal, re-tentative automatique (comportement existant).
- 409/422 sur `patients:PUT` : quarantaine (section 6).
- 422 sur `medical_records:PUT`/`prescriptions:PUT` sans patient en quarantaine : comportement
  existant (abandon journalisé) — cas anormal, non introduit par ce chantier.
- `POST /patients` rejoué avec le même `uuid` (réponse perdue) : 200 idempotent (section 3), le
  connecteur traite ça comme un succès.

## Tests

Backend (pytest) :
- Migration 010 : doublon d'uuid refusé.
- `POST /patients` avec `uuid` : persisté ; rejoué avec le même `uuid` : idempotent (pas de doublon,
  pas de 500).
- `POST /medical_records` et `POST /prescriptions` avec `patient_uuid` : résolution correcte ;
  `patient_uuid` inconnu → 422.

Frontend : build production vert à chaque tâche. Pas de tests unitaires frontend dans ce projet.

Manuel (navigateur, **vraie coupure réseau** : arrêter uvicorn, jamais le toggle DevTools) :
1. Nurse : créer un patient hors ligne → consultation (motif sélectionnable) → prescription →
   modifier une prescription existante → reconnecter → tout apparaît côté serveur, rattaché au bon
   patient, code AH2 attribué.
2. Secrétaire : créer un patient spirituel hors ligne → reconnecter → présent côté serveur.
3. Caisse : ajouter une ligne Examen hors ligne (recherche fonctionnelle) → enregistrer → sync.
4. Doublon : créer hors ligne un patient avec un `national_id` déjà en base + une consultation →
   reconnecter → patient et consultation en quarantaine, rien envoyé au mauvais patient → rattacher
   à un patient existant → la consultation part et apparaît sur le bon dossier.
5. Non-régression : admin inchangé ; RDV et caisse hors ligne toujours fonctionnels.

## Rappels de vérification pour le plan et les revues

- Tout stream : vérifier l'alias `FROM <source> AS <table_locale>` quand les noms diffèrent.
- Toute nouvelle table locale : vérifier qu'elle est bien déclarée dans l'export `AppSchema`.
- Tout nouveau rôle ou stream : vérifier `client.js` (souscription) ET le garde de
  `connectPowerSync` dans `auth.js`/`App.vue` (bug Critical du sous-projet 3).
- Tout champ lu par un template sur une ligne locale : vérifier qu'il est bien produit par le chemin
  local (famille de bugs "champ dérivé du serveur jamais peuplé localement", 3 occurrences déjà).
- Vérifier `docker ps` (les 2 conteneurs `powersync-*` stables) avant tout test manuel.
