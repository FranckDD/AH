# Chantier 7c — Flux de consultation du médecin

**Date** : 2026-09-21
**Origine** : registre `L3c` de `SUIVI-AVANCEMENT.md`, deuxième sous-projet exécuté du chantier 7 (après `7a`, terminé)
**Position** : `7c` avant `7b`, `L4b-e` et `7d` (ordre confirmé par l'utilisateur le 2026-09-21)

## Objectif

Donner au médecin (et à l'infirmier, mêmes droits backend) un chemin complet pour transformer un rendez-vous en dossier médical documenté, sans ressaisie ni détour : démarrer une consultation depuis un rendez-vous, ouvrir le dossier du patient depuis ce même rendez-vous, enregistrer la consultation, voir le rendez-vous se terminer automatiquement, et enchaîner sur une prescription si besoin.

## Pourquoi maintenant

L'audit du 2026-09-15 a constaté qu'aucun flux de consultation n'existe dans l'application web : le bouton « Nouvelle consultation » du dossier patient (`PatientDetailView.vue`) est dessiné sans gestionnaire, la liste des rendez-vous n'offre aucune action vers le patient ou vers une consultation (seulement Terminer/Annuler/Modifier le rendez-vous lui-même), et rien ne relie aujourd'hui un dossier médical au rendez-vous dont il découle. Le médecin qui reçoit un patient sur rendez-vous n'a aucun chemin dans l'application pour documenter cette consultation autrement qu'en passant par l'écran générique « Dossiers médicaux » et en resaisissant le code patient à la main.

## Périmètre

**Inclus** :
- Lien `appointment_id` (nullable) entre un dossier médical et le rendez-vous dont il découle, pour permettre le reste du flux
- Deux nouvelles actions sur chaque ligne de rendez-vous en attente : « Voir dossier » (navigation simple) et « Démarrer consultation »
- Câblage du bouton « Nouvelle consultation » du dossier patient, jusqu'ici sans gestionnaire
- Complétion automatique du rendez-vous dès que le dossier médical lié est enregistré avec succès
- Proposition explicite d'enchaîner sur une prescription après l'enregistrement d'un dossier médical, avec la prescription pré-liée au dossier qui vient d'être créé

**Exclus explicitement** :
- Le durcissement du routeur `/appointments` (aujourd'hui ouvert à n'importe quel rôle authentifié côté backend, sans `role_required`, contrairement à `/medical_records` et `/prescriptions` déjà restreints à `medecin, nurse, admin, manager`) — écart réel trouvé en creusant, mais qui relève du nettoyage `L4b-e`, planifié juste après ce sous-projet. Ce chantier ne touche à aucune garde de rôle existante.
- Le passage hors ligne de ce flux — les dossiers médicaux et les prescriptions sont explicitement exclus du pilote PowerSync du chantier 4 (seuls `appointments`, `patients_lookup`, `doctors_lookup` sont synchronisés). Toute écriture de ce chantier (création de dossier médical, complétion de rendez-vous, création de prescription) passe par le réseau, exactement comme les actions Terminer/Annuler existantes le font déjà.
- Tout export ou impression de la consultation.

## Modèle de données — une migration, nullable, non destructive

**Nouvelle colonne** : `medical_records.appointment_id` (Integer, `ForeignKey('appointments.id')`, **nullable**, aucune valeur par défaut). Nullable parce qu'une consultation reste possible sans rendez-vous d'origine (le bouton « Nouvelle consultation » du dossier patient continue de fonctionner sans lien, exactement comme aujourd'hui). Pas d'`ON DELETE CASCADE` : si un rendez-vous est un jour supprimé, le dossier médical qui en découle doit survivre (`ON DELETE SET NULL`, cohérent avec la politique de suppression déjà en place ailleurs — les patients sont en soft-delete, jamais de suppression physique réelle observée dans ce projet).

Migration Alembic à ajouter : `alembic/versions/005_medical_records_appointment_id.py`, `down_revision = '004_appointments_uuid_unique'` (tête actuelle de la chaîne, vérifiée). Écriture réelle en base : confirmation explicite de l'utilisateur requise avant application, comme pour toute migration dans ce projet.

`models/medical_record.py` gagne la colonne + une relation `appointment = relationship("Appointment")` (pas de `back_populates` requis côté `Appointment`, aucun besoin identifié de naviguer d'un rendez-vous vers son dossier autrement que par une requête filtrée — YAGNI).

## Section 1 — Pré-remplissage des modales (patient déjà connu, pas de ressaisie)

**Constat vérifié dans le code réel** : `MedicalRecordModal.vue` et `PrescriptionModal.vue` n'ont aujourd'hui qu'un seul mode de pré-remplissage — l'édition (`props.record`/`props.prescription`). Créer un nouvel enregistrement oblige toujours à ressaisir un code patient (`patientCode` + `@blur="lookupPatient"`, verrouillé en lecture seule seulement quand `isEdit`). Ce chantier ajoute un deuxième chemin de pré-remplissage, distinct de l'édition : « création pré-remplie ».

**`MedicalRecordModal.vue`** — nouvelle prop `prefilledPatient: { type: Object, default: null }` portant `{ patientId, code, firstName, lastName }` (même forme que ce que `setFromExisting()` — déjà présent dans `usePatientLookup` — consomme aujourd'hui pour le cas édition). Dans `onMounted`, si `props.prefilledPatient` est fourni (et `props.record` absent), appeler `setFromExisting(props.prefilledPatient)` exactement comme le fait déjà le bloc `if (props.record)`, et verrouiller `patientCode` en lecture seule de la même façon que pour l'édition (`:readonly="isEdit || !!props.prefilledPatient"`). Nouvelle prop `appointmentId: { type: Number, default: null }`, ajoutée telle quelle à l'objet émis par `handleSubmit`'s `emit('save', {...})` (`appointmentId: props.appointmentId`) — la modale ne fait aucun appel réseau elle-même (patron déjà en place), elle se contente de porter cette valeur jusqu'à l'appelant.

**`PrescriptionModal.vue`** — même traitement : nouvelle prop `prefilledPatient` (même forme), utilisée pour initialiser `patientCode`/`patientId`/`patientName` sans passer par la recherche manuelle. Nouvelle prop `prefilledMedicalRecordId: { type: Number, default: null }` : si fournie, `medicalRecordId.value` est initialisé à cette valeur dans `onMounted` (au lieu de rester `null`, le cas actuel pour toute création) — c'est le mécanisme qui lie la prescription enchaînée au dossier médical qui vient d'être créé.

## Section 2 — Actions sur la liste des rendez-vous

**Fichier** : `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue`. Pour chaque rendez-vous dont `status === 'pending'` (les seuls pour lesquels Terminer/Annuler s'affichent déjà aujourd'hui — même condition), deux boutons supplémentaires dans la colonne actions :
- **« Voir dossier »** : navigation directe vers `/medical/patients/{patient_id}` (le nom du patient, aujourd'hui du texte brut à la ligne 91, reste tel quel — ce nouveau bouton est une action séparée et explicite, pas une transformation du texte existant en lien, pour rester cohérent avec le patron bouton-par-action déjà en place dans cette colonne).
- **« Démarrer consultation »** : navigation vers `/medical/patients/{patient_id}?appointmentId={id}` — un paramètre de requête, pas une nouvelle route, pour ne pas dupliquer `PatientDetailView.vue` ni modifier son montage.

Aucune nouvelle garde de rôle : la route `/medical/appointments` qui héberge cet écran restreint déjà l'accès à `medecin`/`nurse` côté routeur frontend (`router/index.js`) — ces deux nouveaux boutons héritent de cette restriction sans ajout.

## Section 3 — `PatientDetailView.vue` : câblage du bouton et auto-ouverture depuis un rendez-vous

**Bouton « Nouvelle consultation » (ligne ~55, jusqu'ici sans `@click`)** : gagne `@click="openConsultationModal()"`, ouvrant `MedicalRecordModal` avec `prefilledPatient` déduit du patient déjà chargé par `patientDossierStore` (id de route, déjà connu — `dossierStore.patient` ou `dossierStore.patientSummary`, pas de nouvel appel réseau) et `appointmentId: null` (consultation spontanée, pas de rendez-vous d'origine).

**Auto-ouverture depuis un rendez-vous** : si la route est montée avec `?appointmentId=X` (venant de la Section 2), `onMounted` ouvre directement la modale avec `appointmentId: X` en plus du `prefilledPatient` habituel — le médecin voit d'abord l'en-tête du dossier (allergies, dernières constantes, historique) pendant une fraction de seconde avant que la modale s'ouvre par-dessus, exactement le même composant que le clic manuel sur « Nouvelle consultation », simplement pré-armé avec le rendez-vous d'origine.

**Après un enregistrement réussi (`@save` de `MedicalRecordModal`)** :
1. Appel à `medicalRecordStore.createMedicalRecord(data)` (le payload inclut désormais `appointment_id: data.appointmentId`, transmis jusqu'à `POST /medical_records/`) — **`createMedicalRecord` doit désormais renvoyer l'enregistrement créé** (aujourd'hui elle ignore la réponse du gateway, `MedicalRecordGateway.createMedicalRecord(data)` déjà appelée mais jamais retournée ; correction minimale : `return` la réponse).
2. `dossierStore.refreshMedicalHistory(patientId)` — action déjà existante et déjà taillée pour ce cas exact (re-fetch résumé + historique), jamais appelée jusqu'ici.
3. Si `data.appointmentId` est renseigné : `appointmentStore.completeAppointment(data.appointmentId)` (action déjà existante, déjà utilisée par le bouton Terminer de la liste des rendez-vous — même appel, juste déclenché automatiquement plutôt que par un clic).
4. Fermer `MedicalRecordModal`, puis proposition explicite (petite bannière ou `confirm()`-like, à trancher dans le plan selon le patron déjà utilisé ailleurs dans l'app pour ce genre de choix) : « Ajouter une prescription pour cette consultation ? ». Si acceptée : ouvrir `PrescriptionModal` avec `prefilledPatient` (même patient) et `prefilledMedicalRecordId` (l'id renvoyé à l'étape 1). Si refusée ou ignorée : rien de plus, le flux s'arrête proprement.

**Erreur à l'étape 1 ou 3** : si la création du dossier médical échoue, la modale reste ouverte avec le message d'erreur habituel (patron déjà en place dans `MedicalRecordsList.vue::handleSave`) — le rendez-vous n'est jamais complété sur un échec de création. Si la création réussit mais la complétion du rendez-vous échoue (panne réseau isolée, cas rare), le dossier médical reste créé (déjà en base, ne doit pas être annulé) et une bannière d'erreur signale que le rendez-vous n'a pas pu être marqué terminé automatiquement — le bouton « Terminer » existant sur la liste des rendez-vous reste disponible comme filet de secours.

## Définition du « terminé »

- Un dossier médical peut être créé avec un `appointment_id` renseigné, vérifié en base.
- Depuis la liste des rendez-vous, « Voir dossier » navigue vers le bon patient ; « Démarrer consultation » navigue vers le bon patient avec la modale de consultation déjà ouverte et pré-remplie.
- Le bouton « Nouvelle consultation » du dossier patient fonctionne (consultation spontanée, sans rendez-vous, `appointment_id` reste `NULL`).
- Un rendez-vous lié passe automatiquement à `completed` dès l'enregistrement réussi du dossier médical ; un rendez-vous non lié (consultation spontanée) n'est jamais touché.
- Après l'enregistrement, une proposition d'enchaîner sur une prescription apparaît ; accepter ouvre la prescription déjà liée au dossier médical créé (`medical_record_id` correct, vérifié en base après soumission).
- Aucune garde de rôle existante n'est modifiée ; le routeur `/appointments` reste tel quel (déjà identifié comme un écart réel, traité par `L4b-e` après ce sous-projet).
- Suite de tests existante non régressée ; nouveaux tests pour chaque point ci-dessus.
