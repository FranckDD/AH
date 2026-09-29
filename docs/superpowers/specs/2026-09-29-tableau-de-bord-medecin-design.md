# Tableau de bord médecin/infirmier — vrai backend dédié — design

Date : 2026-09-29 · Statut : validé en brainstorming par l'utilisateur

## Contexte

`DoctorKpiView.vue` (chantier 3, Étape 5, livré comme MVP volontaire) fait
aujourd'hui 5 appels réseau en parallèle vers des endpoints KPI
pré-existants (`/appointments/kpi/*`, `/medical_records/kpi/*`), chacun
résolvant "mes statistiques" depuis l'utilisateur authentifié
(`_resolve_doctor`). Décision explicite de l'utilisateur à l'époque :
revenir construire un vrai tableau de bord avec un backend dédié une fois
tous les chantiers de remise à niveau terminés — c'est cette demande
qu'on traite maintenant ("suivant les normes reconnues").

Découverte du chantier d'origine (registre I1) : `GET /prescription/kpi/count`
n'acceptait pas de filtre par médecin. **Vérifié pendant ce brainstorming :
ce point a déjà été corrigé depuis** (`doctor_id` est bien accepté et
filtré, `api_backend/backend_app/routes/prescription/prescriptions_endpoints.py:302-313`,
`controller/prescription_controller.py::count_prescriptions`). Le vrai
gap restant, découvert en vérifiant l'existant avant de proposer un
design : cet endpoint n'accepte qu'un `period` fixe (`day`/`week`), pas
une plage de dates arbitraire comme les 4 autres sources KPI de ce
tableau de bord — alors que le repository sous-jacent
(`PrescriptionRepository.count_by_prescription_date_range`) supporte déjà
`start`/`end` + `doctor_id`. C'est ce gap précis qu'on ferme ici, pas le
filtre par médecin lui-même (déjà réglé).

Aucun endpoint d'agrégation/composition n'existe nulle part ailleurs dans
ce projet (vérifié) — chaque tableau de bord existant fait toujours
plusieurs appels séparés côté frontend. Ce chantier introduit ce motif
pour la première fois, à la demande explicite de l'utilisateur.

## Décisions utilisateur (2026-09-29)

1. **Un vrai backend dédié** : un seul endpoint d'agrégation côté serveur
   (motif BFF), pas une simple consolidation des appels existants.
2. **Rôles concernés** : `medecin` + `nurse`, chacun voit ses propres
   statistiques personnelles — inchangé par rapport au MVP actuel,
   cohérent avec le reste du module médical qui traite les deux rôles de
   façon symétrique.
3. **Indicateurs** : les 5 cartes/graphiques déjà existants (total RDV,
   patients distincts, dossiers médicaux, répartition RDV par statut,
   répartition consultations par motif) + un compteur de prescriptions
   personnel (corrige enfin le gap de plage de dates ci-dessus) + un
   widget hospitalisations.
4. **Sémantique du widget hospitalisations** : le chantier hospitalisations
   est conçu "équipe" (n'importe quel `medecin`/`nurse` peut admettre,
   mettre à jour ou sortir un patient — pas de "médecin assigné", soins
   holistiques). Un compteur personnel n'aurait donc pas de sens réel.
   **Choisi : total établissement** (nombre de séjours actuellement
   ouverts, tout le centre) — information d'équipe utile en un coup
   d'œil, pas une statistique personnelle. Réutilise tel quel
   `HospitalizationController.count_current()`, déjà existant, déjà
   accessible à `medecin`/`nurse`/`admin`/`promoteur` — **aucune
   modification de ce côté**.
5. **Cache** : même motif Redis déjà établi ailleurs dans le projet (TTL
   5 min, dégradation silencieuse si Redis indisponible) — mais appliqué
   au résultat composé complet en une seule clé, pas par champ individuel.
6. **Tolérance de panne** : dégradation par carte. Si une seule source
   échoue, sa carte affiche une valeur neutre (0/vide) et l'échec est
   loggé côté serveur ; les autres cartes s'affichent normalement. Jamais
   de page blanche pour un problème isolé à une seule source — même
   principe déjà appliqué au tableau de bord admin (chantier 5,
   "dashboard fault-tolerance").

## Architecture

### 1. Backend

**Nouveau module** `api_backend/backend_app/routes/doctor_dashboard/`
(schema + endpoint), sur le modèle d'organisation des modules récents
(`nurse_shifts/`, `hospitalizations/`) :

- `GET /doctor-dashboard/kpi?start=YYYY-MM-DD&end=YYYY-MM-DD` — accessible
  à `medecin`+`nurse` (garde de rôle route-level, jamais router-level —
  piège déjà documenté sur ce projet, chantier hospitalisations).
  `start`/`end` optionnels ; comportement par défaut à définir dans le
  plan (probablement mois courant, cohérent avec le store actuel).

**Réponse** (forme exacte à fixer dans le plan, un champ par carte) :
- `total_appointments` (int)
- `count_by_status` (dict statut→compte)
- `distinct_patients` (int)
- `medical_records_count` (int)
- `consultation_distribution` (dict motif→compte)
- `prescriptions_count` (int)
- `hospitalizations_current_count` (int, total établissement)

**Nouveau `controller/doctor_dashboard_controller.py`** — composition
pure, ne réimplémente aucune logique métier :
- Résout `doctor_id` depuis l'utilisateur authentifié (même motif
  `_resolve_doctor` que les 3 autres contrôleurs déjà utilisés).
- Compose, chacun dans son propre `try/except` qui logue
  (`logger.exception`) et retombe sur une valeur neutre en cas
  d'échec :
  - `AppointmentController.total_appointments/count_by_status/distinct_patients_count`
  - `MedicalRecordController.count_records_for_doctor/consultation_type_distribution`
  - `PrescriptionController.count_prescriptions` (étendu, voir ci-dessous)
  - `HospitalizationController.count_current()` (inchangé)
- Le résultat composé complet est mis en cache Redis
  (`doctor_dashboard:kpi:{doctor_id}:{start}:{end}`, TTL 300s,
  `try/except` autour de `get`/`setex`, même motif que
  `PrescriptionController.count_prescriptions`).

**Extension minimale de `PrescriptionController.count_prescriptions`** :
accepte des `start`/`end` optionnels en plus de `period`. Si fournis,
utilise `PrescriptionRepository.count_by_prescription_date_range(start,
end, doctor_id=d)` (déjà existant, déjà filtrable par médecin) au lieu de
la logique `period` day/week actuelle. Si absents, comportement
inchangé (y compris l'appel existant sans `doctor_id` depuis le desktop,
`remote_gateway.py`, qui doit continuer à renvoyer le total
établissement).

**Aucun nouveau repository** — chaque méthode composée existe déjà et
accepte déjà les paramètres nécessaires.

### 2. Frontend

- `DoctorKpiGateway.js` : un seul appel,
  `fetchDashboard(start, end) → GET /doctor-dashboard/kpi`.
- `doctorKpiStore.js` : un seul `fetchKpiData()`, plus `error` (motif
  déjà standard dans les stores récents de ce projet, ex.
  `nurseShiftStore.js`) pour distinguer "vide car en chargement" de "vide
  car en échec".
- `DoctorKpiView.vue` : garde les 3 cartes + 2 graphiques existants, ajoute
  2 cartes (`StatCard.vue`, déjà existant, aucun nouveau composant) :
  "Prescriptions (période)" et "Séjours en cours (établissement)".
  Nouvelles clés i18n `doctorKpi.prescriptions_total`,
  `doctorKpi.hospitalizations_current` (FR+EN).
- Accès inchangé : route `/medical/doctors`, rôles `medecin`+`nurse`.

## Hors périmètre de ce chantier

- Pas de refonte visuelle des cartes/graphiques.
- Pas de nouveau widget au-delà des 2 ajoutés (prescriptions,
  hospitalisations) — pas de série temporelle, pas d'export PDF pour ce
  tableau de bord.
- Le KPI "patients hospitalisés" du tableau de bord **admin** (item
  séparé du backlog, `project_roadmap_post_notifications`) n'est pas
  traité ici.

## Tests

Backend : suite pytest, vrais appels HTTP (`TestClient`, base réelle),
motif déjà établi (`nurse_shifts`/`hospitalizations`) :
- Réponse complète pour un médecin avec des données réelles dans les 4
  domaines.
- Dégradation par carte : simuler l'échec d'une seule source → la
  réponse reste 200, les autres champs corrects, le champ en échec à sa
  valeur neutre.
- `doctor_id` résolu depuis l'utilisateur authentifié uniquement.
- Plage de dates arbitraire appliquée à chaque source, y compris
  prescriptions (le gap corrigé).
- `nurse` reçoit ses propres statistiques personnelles.
- Cache : un deuxième appel identique ne refait pas les requêtes
  sous-jacentes.
- `secretaire`/autres rôles reçoivent 403.
- Non-régression : l'appel desktop existant à `/prescription/kpi/count`
  sans `doctor_id` continue de renvoyer le total établissement.

Frontend : build de production (convention constante de ce projet, aucun
test automatisé de composant Vue).
