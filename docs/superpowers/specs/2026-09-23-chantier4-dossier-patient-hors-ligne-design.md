# Chantier 4, sous-projet 2 — Dossier patient hors-ligne (medecin/nurse)

**Statut** : approuvé par l'utilisateur le 2026-09-23, prêt pour le plan d'implémentation.

## Contexte

Le pilote PowerSync (chantier 4, sous-projet 1 — module Rendez-vous, medecin/nurse, lecture et
écriture) est clos depuis le 2026-09-15. Toute la remise à niveau de l'application web
(chantiers 5, 6, 7, L4b-e) et la dette technique parquée (Groupes 1, 2, 3, dont les exports/
impressions) sont closes au 2026-09-23. L'utilisateur a demandé de reprendre l'extension du
hors-ligne à d'autres modules, dans cet ordre de priorité explicite : **dossier patient** (ce
document) → caisse/secrétariat → laboratoire. Chaque module fait l'objet de son propre cycle
spec → plan → implémentation, comme le pilote.

## Objectif

Permettre à `medecin`/`nurse` de consulter et d'alimenter le dossier clinique d'un patient sans
connexion réseau, avec la même garantie de reprise automatique à la reconnexion que le pilote
RDV (file CRUD locale, upload différé, aucune perte de saisie).

## Périmètre fonctionnel

- **Rôles concernés** : `medecin`, `nurse` uniquement — même périmètre que le pilote RDV,
  cohérent avec le cloisonnement clinique déjà en place (chantier périmètre médical,
  2026-09-22) : ces deux rôles ne voient jamais `dossier_toxico`/`historique_spirituel`, en
  ligne comme hors ligne.
- **Lecture hors-ligne** :
  - Liste des patients cliniques accessibles (tous les patients ayant au moins un
    `MedicalRecord`, pas seulement ceux avec un RDV programmé — décision utilisateur explicite,
    cohérent avec le filtre `is_clinical` déjà appliqué côté API REST à ces deux rôles).
  - Historique médical (`medical_records`) et prescriptions (`prescriptions`) de ces patients.
  - Résultats labo déjà `completed` (`lab_results`), même filtre que l'API REST existante
    (`LabController._est_medical_lecture_seule()`).
- **Écriture hors-ligne** :
  - Création/modification d'une consultation médicale (`medical_records`).
  - Création d'une prescription (`prescriptions`), éventuellement liée à la consultation
    créée dans le même geste hors ligne.
- **Hors périmètre** : suppression de consultation/prescription (aucun flux UI ne le permet
  actuellement, même motif que le pilote RDV qui exclut `DELETE`) ; modification d'une
  prescription existante (l'écran actuel ne le permet pas non plus en ligne).

## Architecture

Réutilisation stricte du pattern déjà validé par le pilote RDV — aucune architecture
alternative n'est nécessaire pour ce même type de besoin (auth JWT PowerSync déjà en place,
règles de sync par rôle déjà démontrées, connecteur CRUD déjà éprouvé en conditions réelles y
compris le protocole de test coupure réseau).

### Tables locales (`ah2-admin-web/src/powersync-client/AppSchema.js`)

- `patients` (nouvelle table de lecture complète — remplace l'usage de `patients_lookup` pour
  ce rôle ; `patients_lookup` reste utilisé tel quel par le pilote RDV, qui n'a besoin que du
  nom/code affiché sur un RDV, pas du dossier complet).
- `medical_records` (écriture) — colonnes miroir de `models/medical_record.py`, `id` local =
  `uuid::text`, `server_id` = `record_id` Postgres (même convention que `appointments`).
- `prescriptions` (écriture) — colonnes miroir de `models/prescription.py`, même convention
  `uuid`/`server_id`.
- `lab_results` (lecture seule) — pas de `uuid` propre en base (seul `batch_id` existe, non
  destiné à cet usage) ; sans écriture locale sur cette table, l'id PowerSync peut être
  `lab_result_id::text` directement (même motif que `patients_lookup`, qui utilise déjà
  `patient_id::text AS id` sur une clé entière, pas un uuid).

### Règles de sync (`powersync/sync-config.yaml`)

- `clinical_patients` : tous les patients avec `EXISTS (SELECT 1 FROM medical_records WHERE
  medical_records.patient_id = patients.patient_id)` — filtre par domaine, pas par médecin
  propriétaire (la politique d'accès large aux soignants, chantier 6, s'applique aussi hors
  ligne : n'importe quel medecin/nurse peut consulter n'importe quel patient clinique, protégé
  par traçabilité, pas par cloisonnement par praticien).
- `clinical_medical_records` / `clinical_prescriptions` : même filtre par domaine (jointure sur
  un patient clinique), pas de filtre par `created_by`/`prescribed_by` — cohérent avec la
  politique d'accès large déjà appliquée côté REST à ces deux rôles.
- `clinical_lab_results` : reprend le filtre déjà en place côté API REST pour medecin/nurse
  (`status = 'completed'` uniquement).
- **Aucune de ces règles ne doit jamais inclure** de colonne provenant de `toxico_dossiers` ou
  `consultation_spirituelle` — la garantie de cloisonnement doit être posée au niveau des
  règles de sync elles-mêmes, pas seulement côté client, sinon des données interdites
  transiteraient et resteraient stockées dans le SQLite local du navigateur même si l'UI ne les
  affiche jamais.
- Toutes en `auto_subscribe: false`, souscription pilotée par le rôle courant côté client
  (même mécanisme que `my_appointments` vs `all_appointments`).

### Connecteur (`ah2-admin-web/src/powersync-client/`)

Un seul connecteur pour l'ensemble du dossier (décision utilisateur explicite) plutôt qu'un
connecteur par table — une consultation et sa prescription sont souvent saisies dans le même
geste hors ligne, une seule file CRUD à vider est plus simple à raisonner. Renommage de
`AppointmentConnector.js` en `DossierConnector.js`, qui prend en charge RDV (déjà existant,
inchangé) + `medical_records` + `prescriptions`. Même structure `switch (op.op)` que
l'existant :
- `PUT` sur `medical_records` → `POST /medical_records/` avec `uuid: op.id`.
- `PUT` sur `prescriptions` → `POST /prescriptions/` avec `uuid: op.id`, `medical_record_id`
  résolu depuis la ligne locale si liée à une consultation créée dans la même session hors
  ligne (nécessite d'attendre que la consultation ait un `server_id` avant d'uploader la
  prescription liée — PowerSync ordonne déjà les opérations dans l'ordre de création locale,
  donc la consultation est uploadée avant sa prescription si créées dans cet ordre ; si le
  `server_id` de la consultation liée est encore absent au moment de l'upload de la
  prescription, appliquer le même garde-fou que le `PATCH` du pilote RDV : abandonner cette
  opération pour cet upload, elle sera reprise automatiquement au prochain cycle).
- `PATCH` sur `medical_records` → `PUT /medical_records/{record_id}`, même relecture de la
  ligne locale complète que le pilote (évite qu'un champ non modifié localement soit envoyé à
  `null`).
- `DELETE` → log défensif uniquement, hors périmètre (même motif que le pilote).
- Mêmes codes d'erreur fatals (400/404/409/422 abandonnés de la file) vs transitoires (réseau,
  la transaction n'est pas complétée, PowerSync retente).

## Tests

Reprise du protocole de test navigateur réel déjà utilisé pour le pilote (aucun outil de
navigateur disponible dans l'environnement agentique — diagnostics et validation via code/logs/
DB réels à partir de captures fournies par l'utilisateur) : coupure réseau → consultation d'un
dossier déjà synchronisé → création d'une consultation + prescription hors ligne → reconnexion
→ vérification que les deux lignes apparaissent bien côté serveur avec le bon `server_id`,
répété sur 2 navigateurs/rôles (medecin et nurse) comme le pilote. Vérification explicite que
`dossier_toxico`/`historique_spirituel` n'apparaissent jamais dans la base SQLite locale
(inspection directe du fichier local, pas seulement de l'UI) pour un patient qui a ces deux
domaines par ailleurs.

## Risques / points de vigilance déjà identifiés

- Redémarrage du service PowerSync obligatoire après toute modification de
  `sync-config.yaml` (déjà noté dans le fichier existant, à répéter dans le plan).
- Le filtre par domaine (`EXISTS ... medical_records`) doit être vérifié comme performant à
  l'échelle réelle de la table `patients` avant de le considérer acquis — à valider pendant
  l'implémentation, pas supposé.
- Le lien `medical_record_id` sur une prescription créée hors ligne dans la foulée d'une
  consultation elle-même créée hors ligne est le point le plus délicat de ce sous-projet (aucun
  équivalent dans le pilote RDV, qui n'a pas de dépendance inter-tables à l'écriture) — mérite
  une attention particulière à la revue de tâche correspondante du plan.
