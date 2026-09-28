# Chantier 4, sous-projet 2 (suite) — Câblage UI du dossier patient sur PowerSync

**Statut** : approuvé par l'utilisateur le 2026-09-23, prêt pour le plan d'implémentation.

## Contexte

Les 6 tâches du sous-projet "dossier patient hors-ligne" (backend `uuid`, règles de sync
PowerSync, schéma client, `DossierConnector.js`) sont terminées et validées — voir
`docs/superpowers/specs/2026-09-23-chantier4-dossier-patient-hors-ligne-design.md`. En
vérifiant un test navigateur réel de l'utilisateur, il s'avère qu'**aucun écran ne consomme
réellement cette infrastructure** : `PatientDetailView.vue` charge toujours le dossier via
`patientDossierStore.fetchDossierComplete()` (HTTP, `GET /patients/{id}/dossier`), et
`medicalRecordStore.js`/`prescriptionStore.js` créent toujours via
`MedicalRecordGateway`/`PrescriptionGateway` (HTTP direct, jamais `db.execute()` local). Le
connecteur et les 4 streams `clinical_*` existent mais ne sont alimentés par rien côté écran.
Ce document couvre le câblage manquant, uniquement pour `medecin`/`nurse` (périmètre déjà
confirmé) — les autres rôles gardent leur chemin HTTP actuel, strictement inchangé.

## Écriture (création/modification consultation, création prescription)

Pour `medecin`/`nurse` : `medicalRecordStore.createMedicalRecord()`/`updateMedicalRecord()` et
`prescriptionStore.createPrescription()` écrivent désormais via `db.execute()` sur les tables
locales `medical_records`/`prescriptions` — en ligne comme hors ligne, PowerSync gère la
synchronisation en arrière-plan (`DossierConnector.js`, déjà validé), exactement le pattern déjà
en place pour `appointmentStore.createAppointment()`. Les autres rôles gardent l'appel direct
`MedicalRecordGateway`/`PrescriptionGateway` existant, inchangé.

`createMedicalRecord()` génère `crypto.randomUUID()` comme id local et **renvoie
`{ record_id: uuid }`** (le uuid local tenant lieu d'id, en attendant confirmation serveur) —
préserve la signature attendue par `PatientDetailView.vue:234` (`record.record_id`, utilisé pour
proposer une prescription juste après la consultation créée). Si l'utilisateur enchaîne
immédiatement sur une prescription liée à cette consultation, `prescriptions.medical_record_id`
reçoit ce même uuid local (texte) le temps que `DossierConnector.js` résolve le vrai
`server_id` — logique déjà présente et déjà validée dans le connecteur (résolution
`SELECT server_id FROM medical_records WHERE id = ?`, abandon-pour-ce-cycle si absent).

Plus d'appel `fetchMedicalRecords()`/`fetchPrescriptions()` après une écriture locale (ces
fonctions restent utilisées ailleurs pour les vues de LISTE globales, hors périmètre de ce
document, non touchées) — l'écran dossier patient doit refléter l'écriture immédiatement via une
requête locale ponctuelle (`db.getAll(...)`, pas un `db.watch()` continu : ce document garde
volontairement une réactivité minimale, une lecture immédiatement après l'écriture locale suffit
puisque SQLite rend la ligne interrogeable dès le `db.execute()` résolu), jamais via un refetch
réseau qui échouerait hors ligne ou lirait une valeur pas encore uploadée (course).

## Lecture (affichage du dossier)

`patientDossierStore.fetchDossierComplete(patientId)` : pour `medecin`/`nurse` uniquement, tente
d'abord l'appel HTTP existant (`GET /patients/{id}/dossier`) comme aujourd'hui. **Seulement en
cas d'échec réseau** (pas une erreur 4xx/5xx applicative — distinguer via l'absence de réponse
HTTP, ex. `err.response` absent sur une erreur axios) elle retombe sur une lecture directe des
tables locales `patients`/`medical_records`/`prescriptions`/`lab_results` (déjà synchronisées si
une connexion a eu lieu au moins une fois) :
- `patientSummary` : reconstruit depuis la ligne locale `patients` (identité, `flags` calculés
  depuis `is_clinical`/`is_toxicology`/`is_spiritual`) — **`last_bp`/`last_weight`/`last_temp`/
  `last_diagnosis`/`last_consultation_date` restent `null`** en secours hors ligne (décision
  utilisateur explicite : pas de recalcul du résumé clinique côté client, pour ne pas dupliquer
  la logique serveur et risquer une divergence).
- `medicalHistory`/`prescriptionHistory`/`labHistory` : lecture directe des lignes locales
  filtrées par `patient_id`, triées par date décroissante (même ordre que le backend).
- `toxicoDossier`/`spiritualHistory`/`toxicoRestreint`/`spirituelRestreint` : toujours vides/
  restreints en secours hors ligne pour `medecin`/`nurse` — cohérent avec le cloisonnement déjà
  en place (ces domaines ne transitent par aucun stream `clinical_*`, il n'y a physiquement rien
  à lire localement).
- `error.value` : un message distinct ("Mode hors ligne — dernières données synchronisées",
  pas une erreur) plutôt que le message d'erreur HTTP existant, pour ne pas donner l'impression
  d'un échec au soignant qui consulte volontairement hors connexion.

Pour les rôles autres que `medecin`/`nurse`, `fetchDossierComplete()` garde son comportement
HTTP actuel strictement inchangé, y compris son message d'erreur en cas d'échec réseau.

## Tests

Pas de suite automatisée pour ces flux (frontend Vue sans framework de test en place dans ce
projet, comme pour les 6 tâches précédentes de ce sous-projet) — vérification par build
production (`npx vite build --mode production`) et, comme pour le pilote RDV et les 6 tâches
précédentes, un protocole de test navigateur réel à la charge de l'utilisateur (coupure réseau
réelle, pas seulement le toggle DevTools, pour écarter toute ambiguïté sur ce qui a réellement
été testé — leçon du chantier medical_perimetre/N2 ci-dessus).

## Risques déjà identifiés

- `medical_record_id` en texte (uuid local) temporairement stocké dans une colonne PowerSync
  déclarée `column.integer` (SQLite est faiblement typé, accepte cette valeur sans erreur, mais
  ce n'est pas un typage propre) — accepté, cohérent avec la conception déjà validée du
  connecteur, à surveiller si PowerSync durcit un jour ce comportement.
- Distinguer une erreur réseau réelle d'une erreur applicative (404 patient inexistant, 403
  périmètre médical) est nécessaire pour ne pas basculer à tort en mode dégradé sur une vraie
  erreur métier — implémenté via l'absence de `err.response` (axios ne peuple ce champ que
  lorsqu'une réponse HTTP a réellement été reçue).
