# Triage infirmière → médecin + assignation RDV — design

Date : 2026-09-29 · Statut : validé en brainstorming par l'utilisateur

## Contexte

Signalé juste après la livraison du tableau de bord médecin/infirmier : une
consultation enregistrée par une infirmière, et un RDV enregistré par une
infirmière, n'apparaissaient sur le dashboard d'aucun médecin. **Vérifié
avant toute proposition, ce n'est pas un bug du chantier précédent** :

- `MedicalRecordController.create_record()` pose `created_by` =
  l'utilisateur qui enregistre la consultation
  (`controller/medical_controller.py:137-139`). Le dashboard filtre
  `WHERE created_by = doctor_id` — un dossier créé par une infirmière
  n'apparaît donc jamais sur le dashboard d'un médecin, quel que soit le
  médecin qui a réellement vu le patient.
- `AppointmentController.book_appointment()` (`controller/appointment_controller.py:147-150`) :
  si `doctor_id` n'est pas fourni explicitement, il prend automatiquement
  l'ID de qui crée le RDV. `AppointmentModal.vue` n'a **aucun** sélecteur
  de médecin — un RDV créé par une infirmière est donc silencieusement
  attribué à elle-même.

Ces deux comportements sont cohérents avec ce qui a été construit
(statistiques personnelles "mon activité"), mais ne représentent pas la
réalité métier du centre : une infirmière voit souvent le patient en
premier (triage) avant de le diriger vers un médecin, et peut enregistrer
un RDV pour le compte d'un médecin absent au moment de la prise de RDV.

**Décision utilisateur, importante pour le design** : le centre a
aujourd'hui un seul médecin, mais le système doit anticiper plusieurs
médecins à l'avenir — le mécanisme d'assignation ne doit pas supposer un
seul médecin.

## Décisions utilisateur (2026-09-29)

1. **Assignation avec file d'attente partagée pour les dossiers médicaux**
   (Approche A retenue) : l'infirmière choisit un médecin précis, ou
   laisse "non assigné" — auquel cas le dossier est visible dans une file
   partagée par tous les médecins, jusqu'à ce que l'un d'eux le prenne en
   charge.
2. **Signal explicite, pas une déduction implicite** : une infirmière ne
   transmet un dossier au médecin que si elle coche explicitement "à
   transmettre au médecin" — un dossier "consultation" créé par une
   infirmière n'a pas forcément besoin d'un médecin.
3. **RDV : assignation correcte, pas de file partagée** (pour l'instant).
   Un vrai sélecteur de médecin sur le formulaire RDV suffit ; pas de
   vue "RDV non assignés" partagée à ce stade.
4. **"Prendre en charge" = marquer traité, pas créer une consultation
   liée.** Le médecin clique "Prendre en charge" depuis la file
   d'attente, ce qui retire l'entrée de la file ; il crée ensuite sa
   propre consultation séparément, comme il le fait déjà aujourd'hui
   depuis le dossier patient.
5. **Notification à l'assignation, dossier médical uniquement.** Quand un
   dossier est créé avec `needs_doctor_review=true` ET un médecin précis
   assigné (pas la file partagée, où on ne sait pas encore à qui
   notifier), le médecin assigné reçoit une notification. Pas de
   notification pour l'assignation de RDV (visible à l'avance sur le
   calendrier du médecin, moins urgent qu'un patient physiquement en
   attente).

## Architecture

### 1. Modèle de données

**4 nouveaux champs sur `medical_records`** :

| Colonne | Type | Notes |
|---|---|---|
| `needs_doctor_review` | Boolean, `NOT NULL DEFAULT false` | Coché explicitement par qui crée le dossier — jamais déduit du motif. |
| `assigned_doctor_id` | FK → `users`, nullable | Médecin précis choisi, ou `NULL` = file d'attente partagée. N'a de sens que si `needs_doctor_review=true`. |
| `reviewed_by` | FK → `users`, nullable | Qui a cliqué "Prendre en charge". |
| `reviewed_at` | DateTime, nullable | Quand. Tant que vide, le dossier reste dans la file. |

**`appointments.doctor_id` devient nullable** (migration, colonne
actuellement `NOT NULL`) — `NULL` = non assigné. Pas de nouvelle table,
pas de nouvelle file d'attente pour les RDV (décision §3).

### 2. Contrôle d'accès

- Création/lecture des dossiers médicaux : inchangé (`medecin`+`nurse`,
  déjà en place).
- `POST /medical_records/{id}/claim` (nouveau) : réservé au rôle
  `medecin` uniquement — "prendre en charge" est une action médecin,
  contrairement au reste du module qui est `medecin`+`nurse`.
- `GET /doctor-dashboard/pending-review` (nouveau) : même garde que le
  reste du module `doctor_dashboard` (`medecin`+`nurse` en lecture,
  cohérent avec le reste du tableau de bord).

### 3. Backend

**`MedicalRecordRepository`** (nouvelles méthodes) :
- `list_pending_for_doctor(doctor_id, limit=20)` — `WHERE
  needs_doctor_review=true AND reviewed_at IS NULL AND
  (assigned_doctor_id=doctor_id OR assigned_doctor_id IS NULL)`, triée du
  plus ancien au plus récent (FIFO).
- `claim(record_id, doctor_id)` — pose `assigned_doctor_id` s'il était
  vide (le médecin "prend" l'entrée de la file partagée), `reviewed_by`,
  `reviewed_at`. Lève une erreur explicite si le dossier n'existe pas ou
  est déjà pris en charge (évite qu'un second médecin "prenne" un dossier
  déjà traité par un collègue — condition de course réelle avec plusieurs
  médecins, scénario que ce chantier doit justement anticiper).

**`MedicalRecordController.create_record()`** — accepte `needs_doctor_review`
et `assigned_doctor_id` en plus des champs déjà gérés. Si
`needs_doctor_review=true` ET `assigned_doctor_id` est un médecin précis
(pas `NULL`), envoie une notification via `NotificationRepository.create(
recipient_user_id=assigned_doctor_id, type="patient_pending_review",
payload={...})` — même motif exact que l'alerte d'aggravation du
chantier hospitalisations (`_notify_team_of_aggravation`), jamais
bloquant (`try/except`, la création du dossier ne doit jamais échouer à
cause d'un problème de notification).

**Nouveau `POST /medical_records/{id}/claim`** — appelle
`MedicalRecordController.claim_review(record_id)`, garde `medecin`
uniquement, mappe une erreur "déjà pris en charge" vers 409.

**Nouveau `GET /doctor-dashboard/pending-review`** — liste (pas un
chiffre agrégé comme le `GET /kpi` déjà existant) : nom patient, motif,
date de création, qui a créé, assigné ou file partagée. Module séparé du
`GET /kpi` existant.

**`AppointmentCreate`/`AppointmentUpdate`** — `doctor_id` devient
optionnel dans le schéma (déjà optionnel niveau modèle après la
migration).

### 4. Frontend

**`AppointmentModal.vue`** — nouveau sélecteur de médecin (réutilise
`UserRepository.get_users_by_role_names(["medecin"])`, déjà utilisé pour
le planning infirmiers), avec une option "Non assigné".

**Formulaire de création de dossier médical** — nouvelle case "À
transmettre au médecin" (visible pour le rôle `nurse`, probablement aussi
pour `medecin` par cohérence même si rarement utilisé) ; si cochée, un
sélecteur de médecin apparaît avec une option "File d'attente (tout
médecin)".

**`DoctorKpiView.vue`** — nouvelle section "Patients en attente" sous les
cartes KPI existantes (liste, pas une carte chiffrée — motif différent de
`StatCard.vue`). Chaque ligne : nom patient (lien vers son dossier
consolidé déjà existant, chantier 6), motif, qui a créé, bouton "Prendre
en charge".

**`NotificationBell.vue`** — nouveau cas `patient_pending_review` dans
`labelFor()`/`handleClick()`, même motif exact que
`hospitalization_aggravation` (libellé + navigation vers le dossier
patient au clic).

## Hors périmètre de ce chantier

- Pas de file d'attente partagée pour les RDV non assignés (décision
  §3).
- Pas de création de consultation liée automatique au clic "Prendre en
  charge" (décision §4).
- Pas de notification pour l'assignation de RDV (décision §5).
- Pas de mode hors ligne pour la file d'attente ni pour l'assignation de
  RDV.

## Tests

Backend : suite pytest, vrais appels HTTP (`TestClient`), motif déjà
établi (`nurse_shifts`/`hospitalizations`/`doctor_dashboard`) :
- Un dossier créé avec `needs_doctor_review=true` et un médecin précis
  apparaît dans `list_pending_for_doctor` de ce médecin, jamais d'un
  autre.
- Un dossier avec `assigned_doctor_id=NULL` apparaît dans la file de
  **tous** les médecins.
- Un dossier sans `needs_doctor_review` n'apparaît dans la file d'aucun
  médecin.
- `claim()` retire le dossier de la file de tout le monde après coup, y
  compris de la file partagée.
- `claim()` sur un dossier déjà pris en charge par quelqu'un d'autre
  renvoie 409 (protection contre la course à plusieurs médecins).
- La notification part uniquement quand un médecin précis est assigné,
  jamais pour la file partagée.
- `nurse` ne peut pas appeler `claim()` (403).
- RDV : `doctor_id` optionnel accepté, RDV assigné apparaît sur le
  dashboard du bon médecin, RDV non assigné n'apparaît sur le dashboard
  d'aucun médecin (comportement neutre, pas d'erreur).

Frontend : build de production (convention constante de ce projet, aucun
test automatisé de composant Vue).
