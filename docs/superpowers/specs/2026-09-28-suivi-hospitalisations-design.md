# Suivi des hospitalisations — design

Date : 2026-09-28 · Statut : validé en brainstorming par l'utilisateur

## Contexte

Item du backlog post-notifications (voir mémoire `project_roadmap_post_notifications`
côté agent, et `SUIVI-AVANCEMENT.md`) : aujourd'hui, rien dans le projet ne
permet de savoir si un patient est actuellement hospitalisé. Une note de
brainstorming récupérée évoquait « amélioration/rechute/remise en
forme/transfert » comme les seuls états — en creusant avec l'utilisateur, ces
quatre termes mélangeaient en réalité deux notions différentes qu'un vrai
système hospitalier sépare toujours : une **décision administrative**
(admis/sorti) et une **évolution clinique** pendant le séjour
(amélioration/aggravation). Ce chantier suit donc le modèle ADT
(Admission-Discharge-Transfer) standard des systèmes d'information
hospitaliers plutôt que les quatre termes bruts de la note initiale.

Le module toxico (`ToxicoDossier`/`ToxicoPhaseHistory`) a déjà son propre
système de phases avec historique — ce chantier est **volontairement
indépendant**, pour les patients cliniques généraux (médecin/infirmier), pas
un remplacement ni une fusion avec le système toxico.

## Décisions utilisateur (2026-09-28)

1. **Périmètre** : patients cliniques généraux, module médecin/infirmier
   (`/medical/...`) uniquement. Pas les patients toxico.
2. **Cycle de vie** : Admission → (évolution clinique libre, va-et-vient
   possible) → Sortie. Un séjour a un début et une fin explicites.
3. **Sortie suit les conventions hospitalières standard** (demande
   explicite de l'utilisateur de suivre les normes du métier plutôt que les
   termes de la note initiale) : quatre types de sortie (« disposition de
   sortie ») — guéri, transféré, sorti contre avis médical, décès.
   L'amélioration/aggravation ne sont **pas** des types de sortie, ce sont
   des évolutions cliniques pendant le séjour.
4. **Rôles** : médecin et infirmier, sans distinction, peuvent admettre,
   mettre à jour l'état clinique, et prononcer la sortie — cohérent avec le
   périmètre clinique déjà en place (chantier médecin/nurse périmètre,
   2026-09-22).
5. **Écran dédié** : en plus d'une carte dans le dossier patient, un écran
   liste de tous les patients actuellement hospitalisés.

## Architecture

### 1. Modèle de données

**Nouvelle table `hospitalizations`** — un séjour :

| Colonne | Type | Notes |
|---|---|---|
| `id` | PK | |
| `patient_id` | FK → `patients` | pas unique : plusieurs séjours possibles dans le temps |
| `admitted_at` | DateTime, not null | |
| `admitted_by` | FK → `users`, not null | |
| `admission_reason` | Text, nullable | |
| `discharged_at` | DateTime, nullable | **NULL = toujours hospitalisé** — seule source de vérité pour "actuellement hospitalisé", jamais un champ de statut séparé qui pourrait diverger |
| `discharge_disposition` | String, nullable | rempli seulement à la sortie : `GUERI` \| `TRANSFERE` \| `SORTIE_CONTRE_AVIS_MEDICAL` \| `DECES` |
| `discharge_note` | Text, nullable | |
| `discharged_by` | FK → `users`, nullable | |
| `created_at` / `updated_at` | DateTime | |

**Contrainte réelle en base** (pas juste une garde d'interface, pour ne
jamais permettre une incohérence qui casserait le KPI/la liste) : index
unique partiel sur `patient_id` où `discharged_at IS NULL` — un patient ne
peut pas avoir deux séjours ouverts simultanément.

**Nouvelle table `hospitalization_status_updates`** — l'évolution clinique
pendant le séjour :

| Colonne | Type | Notes |
|---|---|---|
| `id` | PK | |
| `hospitalization_id` | FK → `hospitalizations`, not null | |
| `status` | String, not null | `AMELIORATION` \| `STABLE` \| `AGGRAVATION` |
| `note` | Text, nullable | |
| `created_by` | FK → `users`, not null | |
| `created_at` | DateTime, default now | |

Pas de règle de « transitions autorisées » entre ces trois valeurs — un vrai
suivi médical n'empêche jamais de noter une aggravation après une
amélioration. La seule règle est : on ne peut ajouter une entrée que sur un
séjour encore ouvert (`discharged_at IS NULL`).

### 2. Backend

Nouveau routeur `api_backend/backend_app/routes/hospitalizations/`, sur le
modèle de `medical_records_endpoint.py`. Réservé à `medecin`/`nurse` au
niveau du routeur (`Depends(role_required("medecin", "nurse"))`), à
l'exception explicite de l'endpoint KPI (voir plus bas).

- `POST /hospitalizations/` — admettre. Body : `patient_id`,
  `admission_reason`. Refuse (409, message explicite) si le patient a déjà
  un séjour ouvert.
- `POST /hospitalizations/{id}/status` — ajouter une évolution clinique.
  Body : `status`, `note`. Refuse (400) si le séjour est déjà clos.
- `POST /hospitalizations/{id}/discharge` — sortie. Body :
  `discharge_disposition` (obligatoire, une des 4 valeurs), `discharge_note`.
  Refuse (400) si le séjour est déjà clos, (422) si `discharge_disposition`
  manque ou n'est pas une valeur valide.
- `GET /hospitalizations/current` — liste des séjours ouverts (écran liste),
  avec nom patient, date d'admission, dernière évolution clinique connue,
  qui a admis.
- `GET /hospitalizations/patient/{patient_id}` — historique complet d'un
  patient (séjour ouvert le cas échéant + séjours passés), pour la carte
  dossier.
- `GET /hospitalizations/kpi/count_current` — nombre de séjours ouverts,
  pour le KPI admin. Exception au niveau routeur : accessible aussi à
  `admin`/`promoteur` (appelé depuis `DashboardOverview.vue`), même motif
  que les autres endpoints `kpi/*` déjà exposés plus largement que le reste
  de leur module.

Chaque admission/sortie s'écrit dans `audit_user_actions` (même motif que
`MedicalRecordController.create_record`) : `resource_type="Hospitalization"`,
`action_performed` = `ADMIT` / `DISCHARGE`.

Controller `HospitalizationController` + repository
`HospitalizationRepository`, sur le modèle de
`MedicalRecordController`/`MedicalRecordRepository`.

### 3. Frontend

**Carte "Hospitalisation" dans le dossier patient**
(`PatientDetailView.vue`, visible médecin/infirmier) — même esprit que la
carte "Phases" côté toxico :
- Patient non hospitalisé → bouton "Admettre" (ouvre un petit formulaire :
  motif).
- Patient hospitalisé → état actuel (dernière évolution clinique ou "aucune
  mise à jour" si aucune depuis l'admission), historique complet, boutons
  "Mettre à jour l'état" et "Sortir" (formulaire de sortie : disposition +
  note, disposition obligatoire).

**Écran liste** `/medical/hospitalizations` (`ROLES.MEDECIN`,
`ROLES.NURSE`, ajouté au menu `MedicalLayout.vue`) : une ligne par patient
actuellement hospitalisé (nom, date d'admission, nombre de jours depuis,
dernière évolution clinique, qui a admis). Clic sur une ligne → dossier
patient. Actions rapides directement depuis la liste (mettre à jour l'état,
sortir), même motif que le panneau latéral du calendrier RDV
(2026-09-28) — pas de navigation obligatoire pour un geste courant.

`hospitalizationStore.js` (nouveau), `HospitalizationGateway.js` (nouveau) —
appels REST classiques, pas de PowerSync/hors-ligne pour ce chantier (les
autres écrans médecin/infirmier — RDV, dossier médical — sont déjà
hors-ligne via PowerSync, mais l'admission/sortie d'un patient est un acte
suffisamment rare et engageant pour ne pas justifier l'effort d'un nouveau
pilote hors-ligne ici ; à reconsidérer si le besoin réel se manifeste une
fois en usage).

## Hors périmètre de ce chantier (déjà tranché avec l'utilisateur)

- **KPI "patients hospitalisés" (admin dashboard)** : `count_current`
  ci-dessus est fait pour l'alimenter directement, mais le branchement
  réel sur `DashboardOverview.vue` (nouvelle carte ou remplacement de la
  carte "Admissions Toxico (Mois)" mal étiquetée précédemment) est un petit
  ajout séparé, après ce chantier.
- **KPI "patients actifs" réel** (admin) : dépend en partie de ce chantier
  pour la notion d'hospitalisé, mais la définition complète d'un "patient
  actif" clinique reste à concevoir séparément.
- **Règle "consultation secrétaire visible côté médecin"** (vrai tableau
  de bord médecin, `DoctorKpiView.vue`) : chantier séparé, sans lien direct.
- **Transferts internes entre services/lits** : ce centre n'a pas de
  modèle de lits/services dans le projet aujourd'hui ; "transféré" est
  uniquement une disposition de sortie (le patient quitte cet
  établissement), pas un mouvement interne.
- **Mode hors ligne** (voir ci-dessus).

## Tests

Backend : suite pytest, vrais appels HTTP (`api_client`, `auth_headers`,
convention établie sur tout le projet), sur le modèle de
`tests/test_medical_records_uuid.py` :
- Admission réussie, refus si séjour déjà ouvert (409).
- Ajout d'une évolution clinique, refus si séjour clos (400).
- Sortie réussie avec chaque disposition valide, refus sans disposition
  (422), refus si séjour déjà clos (400).
- `GET /hospitalizations/current` ne renvoie que les séjours ouverts.
- `GET /hospitalizations/kpi/count_current` accessible à admin/promoteur
  en plus de médecin/nurse.
- Entrée d'audit écrite à l'admission et à la sortie.
- Garde RBAC : secrétaire/admin (hors KPI)/autres rôles refusés sur les
  endpoints d'écriture.

Frontend : build de production (ce projet n'a pas de tests automatisés de
composants Vue, convention constante).
