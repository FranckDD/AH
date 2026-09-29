# Calendrier de rotation des infirmiers — design

Date : 2026-09-29 · Statut : validé en brainstorming par l'utilisateur

## Contexte

Backlog issu du même échange que le suivi des hospitalisations : le centre
a besoin d'un planning de rotation pour son équipe infirmière
(matin/après-midi/nuit), et d'une manière de désigner qui, parmi les
infirmiers, a le droit de l'établir — en plus du médecin.

**Décision de conception centrale, trouvée en explorant le système de rôles
existant avant de proposer quoi que ce soit** : ce projet n'attribue
qu'**un seul rôle par utilisateur** (`users.role_id`, une seule valeur).
Créer un vrai rôle `chef_infirmier` distinct de `nurse` aurait fait perdre
à cette personne tous ses droits infirmier habituels (dossier médical,
hospitalisations, rendez-vous...) partout dans l'application, sauf à
retrouver et modifier chacun des nombreux endroits qui vérifient déjà le
rôle `nurse` — risque réel d'oubli. **Décision de l'utilisateur** : garder
`nurse` comme rôle, et ajouter un simple indicateur `is_head_nurse` sur le
compte. La personne reste infirmière avec tous ses droits habituels, et
gagne en plus le droit d'établir le planning.

## Décisions utilisateur (2026-09-29)

1. **Mécanisme de rôle** : `users.is_head_nurse` (booléen), pas un nouveau
   rôle. Coché/décoché par un admin depuis l'écran de gestion des comptes
   déjà existant (`UserManagement.vue`).
2. **Le médecin a toujours accès au planning** (création/modification),
   sans condition — en plus du chef infirmier/infirmière.
3. **Structure des créneaux** : créneaux fixes par jour — `MATIN`,
   `APRES_MIDI`, `NUIT`. Pas d'heures libres.
4. **Visibilité** : tout le monde (médecin + tous les infirmiers, chef ou
   non) voit le planning complet de l'équipe, pas seulement ses propres
   créneaux.
5. **Effectif par créneau** : plusieurs infirmiers possibles sur un même
   créneau (0, 1 ou plusieurs) — pas de limite stricte à un seul.
6. **Aucun effet sur les actions cliniques** — décision explicite,
   confirmée avec l'utilisateur : le planning est purement informatif. Un
   infirmier non planifié sur un créneau garde tous ses droits habituels
   (admission, dossier médical, etc.). Ce chantier ne touche à aucune garde
   de rôle existante ailleurs dans le projet.
7. **Pas de motif récurrent automatique** pour l'instant (« répéter cette
   semaine ») — saisie créneau par créneau, décision explicite pour rester
   simple au démarrage.

## Architecture

### 1. Modèle de données

**Colonne `users.is_head_nurse`** (Boolean, `NOT NULL DEFAULT false`) —
n'a de sens que pour un compte de rôle `nurse`, mais aucune contrainte
base ne l'impose (un admin mal configuré ne doit jamais faire planter une
requête ; la garde réelle est applicative, voir §2).

**Nouvelle table `nurse_shifts`** — une ligne par affectation :

| Colonne | Type | Notes |
|---|---|---|
| `id` | PK | |
| `shift_date` | Date, not null | |
| `shift_type` | String, not null | `MATIN` \| `APRES_MIDI` \| `NUIT` — CHECK constraint réelle |
| `nurse_id` | FK → `users`, not null | |
| `created_by` | FK → `users`, not null | qui a fait l'affectation (médecin ou chef infirmier/infirmière) |
| `created_at` | DateTime, default now | |

**Contrainte réelle en base** : index unique sur (`shift_date`,
`shift_type`, `nurse_id`) — empêche d'affecter deux fois le même infirmier
au même créneau le même jour (doublon exact), sans jamais limiter le
nombre d'infirmiers différents sur un même créneau (plusieurs lignes,
`nurse_id` différent, coexistent normalement).

### 2. Contrôle d'accès

- **Lecture** (`GET /nurse-shifts`) : `medecin` + `nurse` (tout le monde,
  chef ou non) — même garde que le reste du module clinique.
- **Écriture** (`POST`/`DELETE /nurse-shifts`) : garde de rôle routeur
  `medecin`/`nurse` (comme la lecture), **plus une vérification
  applicative** à l'intérieur du controller : autorisé si
  `role == 'medecin'` OU (`role == 'nurse'` ET `current_user.is_head_nurse
  == True`). Un infirmier sans cet indicateur reçoit un refus explicite
  (403), jamais une erreur générique.
- **`GET /nurse-shifts/nurses`** (liste des infirmiers actifs, pour remplir
  le sélecteur d'affectation) : même garde que la lecture — réutilise
  `UserRepository.get_users_by_role_names(["nurse"])`, déjà existant (utilisé
  aussi par la diffusion des alertes d'aggravation, chantier hospitalisations).

### 3. Backend

Nouveau module `api_backend/backend_app/routes/nurse_shifts/`, sur le
modèle exact du module `hospitalizations` (modèle → repository →
controller → routeur) :

- `POST /nurse-shifts` — body : `shift_date`, `shift_type`, `nurse_id`.
  Refuse (422) si `shift_type` hors des 3 valeurs, (404) si `nurse_id` ne
  correspond à aucun utilisateur actif de rôle `nurse`, (409) si
  l'affectation existe déjà (doublon exact), (403) si l'appelant n'a pas le
  droit d'écrire (voir §2).
- `DELETE /nurse-shifts/{id}` — retire une affectation. (404) si
  inexistante, (403) si pas le droit.
- `GET /nurse-shifts?start=YYYY-MM-DD&end=YYYY-MM-DD` — toutes les
  affectations de la période, avec nom de l'infirmier et de qui a créé
  l'affectation (même motif de résolution de noms que le chantier
  hospitalisations — ne jamais renvoyer un `user_id` brut sans nom
  résolu).
- `GET /nurse-shifts/nurses` — `{user_id, full_name, is_head_nurse}` pour
  chaque infirmier actif.

**Extension de la gestion des comptes** (`UserUpdate`/`UserCreate`
schemas, `UserController.update_user()`'s whitelist déjà présente) :
ajout de `is_head_nurse: Optional[bool]` — même motif que les champs déjà
whitelistés (`is_active`, `role_id`, etc.).

### 4. Frontend

**`UserModal.vue`** : case à cocher « Chef infirmier/infirmière »,
visible uniquement quand le rôle sélectionné dans le formulaire est
`nurse` (masquée et réinitialisée à `false` sinon, pour ne jamais
soumettre `is_head_nurse: true` sur un compte non-infirmier).

**Écran calendrier** `/medical/nurse-shifts` (`ROLES.MEDECIN`,
`ROLES.NURSE`, ajouté au menu `MedicalLayout.vue`) : grille mensuelle,
même construction que `AppointmentsCalendar.vue` (chantier calendrier RDV,
2026-09-28 — `dayjs`, semaines lundi-first, navigation mois
précédent/suivant). Chaque jour affiche ses 3 créneaux, chacun listant les
infirmiers assignés (ou vide). Clic sur un jour → panneau latéral avec le
détail des 3 créneaux :
- Médecin ou chef infirmier/infirmière : boutons "Ajouter"/"Retirer" une
  affectation par créneau (sélecteur parmi les infirmiers actifs).
- Infirmier sans cet indicateur : même panneau, lecture seule (pas de
  bouton — le frontend cache l'action, le backend la refuse de toute
  façon si elle était appelée directement).

`nurseShiftStore.js` (nouveau), `NurseShiftGateway.js` (nouveau) — appels
REST classiques, pas de PowerSync/hors-ligne pour ce chantier (même
décision que le chantier hospitalisations, pour la même raison : un acte
de planification n'a pas besoin d'un pilote hors-ligne dédié).

## Hors périmètre de ce chantier (déjà tranché avec l'utilisateur)

- **Aucun effet sur les actions cliniques** — pas de restriction "seul un
  infirmier planifié peut agir" nulle part (décision utilisateur, §item 6).
- **Pas de motif récurrent** ("répéter cette semaine/ce mois") — saisie
  manuelle créneau par créneau uniquement pour ce chantier.
- **Pas d'échange de créneau entre infirmiers** (demande de swap,
  validation) — pourrait être une extension future, pas demandée ici.
- **Mode hors ligne** — voir §4.

## Tests

Backend : suite pytest, vrais appels HTTP, sur le modèle des tests
hospitalisations (`api_client`, `auth_headers`, `create_test_user`) :
- Création d'une affectation réussie, refus si `shift_type` invalide
  (422), refus si `nurse_id` ne correspond pas à un infirmier actif (404),
  refus si doublon exact (409).
- Un médecin peut créer/supprimer une affectation.
- Un infirmier avec `is_head_nurse=True` peut créer/supprimer une
  affectation.
- Un infirmier avec `is_head_nurse=False` (ou absent) reçoit un refus
  explicite (403) sur la création/suppression.
- `GET /nurse-shifts` accessible en lecture à tout médecin/infirmier,
  renvoie plusieurs infirmiers sur un même créneau/jour correctement.
- `GET /nurse-shifts/nurses` ne renvoie que des infirmiers actifs.
- Mise à jour de `is_head_nurse` via `PUT /users/{id}` (garde admin déjà
  existante, aucune régression sur les autres champs déjà whitelistés).

Frontend : build de production (convention constante de ce projet, aucun
test automatisé de composant Vue).
