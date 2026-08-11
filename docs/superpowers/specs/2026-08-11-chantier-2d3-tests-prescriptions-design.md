# Chantier 2d-3 — Tests d'intégration prescriptions

**Date :** 2026-08-11
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** troisième sous-chantier métier de 2d, construit sur l'infrastructure de 2d-0/2d-1/2d-2

## Contexte

2d-1 a couvert authentification et RBAC en profondeur. 2d-2 a couvert le CRUD critique du module patients. 2d-3 couvre le module prescriptions (`api_backend/backend_app/routes/prescription/prescriptions_endpoints.py`), avec un périmètre élargi par rapport aux deux précédents : CRUD + tous les endpoints secondaires (`/renewals`, `/kpi/count`, `/patient/{patient_id}`) + RBAC re-testé sur ce routeur spécifiquement (il déclare ses propres rôles autorisés, différents de `/users/`) + validations.

**Avertissement explicite, accepté par l'utilisateur** : contrairement à 2d-2 (un seul fichier en travail en cours), le module prescriptions a **cinq fichiers modifiés non commités** : `api_backend/backend_app/routes/prescription/prescriptions_endpoints.py`, `prescriptions_schemas.py`, `controller/prescription_controller.py`, `repositories/prescription_repo.py`, `models/prescription.py`. Les tests de ce chantier documentent le comportement du code **committé (`HEAD`)**, pas celui du travail en cours. Objectif assumé par l'utilisateur : dérouler tous les chantiers de tests jusqu'au bout d'abord, pour obtenir une liste complète et fiable de ce qu'il faut corriger — bugs, incohérences métier, nettoyage du dépôt — avant de commiter quoi que ce soit sur ce module. Il est donc attendu (pas anormal) que plusieurs de ces tests échouent une fois `repositories/prescription_repo.py` et les fichiers associés commités ; ce sera alors le signal qu'il faut convertir les tests concernés, comme pour B6.

## Découvertes pendant le cadrage (documentées telles quelles, pas corrigées)

### Bug 1 — suppression idempotente silencieuse (pas de 404 sur un id inexistant)

`repositories/prescription_repo.py::delete()` (HEAD) exécute un `DELETE FROM public.prescriptions WHERE prescription_id = :id` brut et retourne **toujours `True`**, sans vérifier `rowcount`. Le modèle `Prescription` n'a pas de colonne `is_deleted`/`status` de suppression logique (contrairement à `Patient`) — c'est une suppression physique. Conséquence : `DELETE /prescriptions/{id}` sur un id **inexistant** renvoie **204** au lieu du 404 attendu (`prescription_ctrl.delete_prescription()` retourne toujours une valeur truthy, donc le `if not ok: raise 404` de l'endpoint ne se déclenche jamais). À la différence de `delete_patient` (2d-2), il n'y a ici ni bug SQL préexistant ni garde-fou : le comportement silencieux est celui du code actuel, pas un accident d'implémentation.

### Bug 2 — message d'erreur en anglais sur `PUT` (incohérence de langue)

`repositories/prescription_repo.py::update()` lève `ValueError(f"Prescription with ID {prescription_id} not found")` (ligne 97) quand l'id n'existe pas ; l'endpoint le remonte tel quel en 404. Tout le reste de l'API répond en français (`"Patient introuvable"`, `"Prescription non trouvée"` sur `GET`/`DELETE`). Incohérence de langue à documenter, pas à corriger ici.

### Bug 3 — le contrôle métier `start_date > end_date` de l'endpoint `POST` est probablement mort code

`prescriptions_schemas.py::PrescriptionBase` porte un `@model_validator(mode="after")` qui lève `ValueError` si `start_date > end_date`. Pydantic convertit toute `ValueError` levée dans un `model_validator` en erreur de validation — FastAPI répond alors **422** au moment du parsing du corps de la requête, **avant** que la fonction de la route ne s'exécute. Or `create_prescription` (l'endpoint) contient *aussi* un contrôle explicite équivalent qui répond **400** (`prescriptions_endpoints.py`, juste après `payload = data.model_dump()`). Comme le modèle Pydantic est validé en premier par FastAPI, ce contrôle explicite est vraisemblablement **inatteignable** : la requête est déjà rejetée en 422 avant d'arriver à cette ligne. Aucun contrôle équivalent n'existe sur `PUT` (l'endpoint `update_prescription` ne fait pas ce `if` explicite), mais le même `model_validator` s'applique puisque `PrescriptionUpdate` hérite de `PrescriptionBase` — donc `PUT` avec des dates invalides devrait aussi renvoyer 422.

**Ceci n'est pas confirmé par lecture de code seule** — le plan demande à l'implémenteur de vérifier empiriquement (exécuter le test contre l'API réelle) plutôt que de supposer, et d'écrire l'assertion sur le code de statut réellement observé (422 très probable, mais le test doit constater, pas deviner).

### Point d'incertitude — comportement sur `patient_id` inexistant à la création

`create()`/`update()` appellent des procédures stockées PostgreSQL (`CALL public.create_prescription(...)`, `CALL public.update_prescription(...)`) dont le corps n'est tracé nulle part (ni Alembic, ni dump du dépôt — item de registre `D2`, déjà connu depuis 2d-2). Le comportement exact sur un `patient_id` qui n'existe pas (contrainte de clé étrangère) est donc inconnu à la lecture du code : `IntegrityError` → 409, autre exception → 500, ou autre chose. **Hors périmètre** de ce chantier : ne pas écrire de test qui suppose un comportement non vérifiable sans exécution réelle contre la procédure ; si le temps le permet pendant l'implémentation, le constater et le documenter au registre plutôt que de deviner, mais ce n'est pas un item obligatoire du plan.

## Portée

Tout le routeur `/prescriptions` :
- `POST /prescriptions/` (création)
- `GET /prescriptions/{id}` (lecture)
- `GET /prescriptions/` (liste, avec filtres `patient_id`, `search`, `date_from`/`date_to`)
- `PUT /prescriptions/{id}` (mise à jour)
- `DELETE /prescriptions/{id}` (suppression physique)
- `GET /prescriptions/renewals` (renouvellements à venir pour le médecin courant)
- `GET /prescriptions/kpi/count` (compteur KPI, `period=day|week`)
- `GET /prescriptions/patient/{patient_id}` (historique patient, avec filtre `status` optionnel)

RBAC re-testé sur ce routeur (contrairement à 2d-2) car il déclare sa propre liste de rôles autorisés au niveau du routeur : `role_required("medecin", "nurse", "admin", "manager")` — différente de celle de `/users/` testée en 2d-1. `secretaire` n'y figure pas.

## Détail de l'implémentation

### 1. Factory de prescription de test (ajout à `tests/conftest.py`)

```python
from repositories.prescription_repo import PrescriptionRepository
from datetime import date


def create_test_prescription(session, patient_id, current_user, **overrides):
    """
    Cree une prescription ephemere en appelant directement le repository
    (procedure stockee Postgres reelle create_prescription()), dans la
    transaction de test. Retourne le dict des donnees envoyees (le repo
    ne retourne que True - il faut relire via list_prescriptions/get
    pour obtenir l'id reel si necessaire).
    """
    data = {
        "patient_id": patient_id,
        "medical_record_id": None,
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": date.today(),
        "end_date": None,
        "notes": None,
        "prescribed_by": getattr(current_user, "user_id", None),
        "prescribed_by_name": getattr(current_user, "username", None),
        **overrides,
    }
    repo = PrescriptionRepository(session)
    repo.create(data)
    return data
```

Nécessite un patient existant (`create_test_patient`, 2d-2) — `patient_id` est une FK obligatoire. Comme `create()` ne retourne que `True` (procédure stockée), les tests qui ont besoin de l'id réel doivent le retrouver via `GET /prescriptions/?patient_id=...` après création.

### 2. Tests (`tests/test_prescriptions.py`)

Chaque test s'authentifie via `create_test_user()` + `login()`, et surcharge `auth_endpoints` et `prescriptions_endpoints` via `api_client(auth_endpoints, prescriptions_endpoints)`. Les tests qui ont besoin d'un patient existant utilisent `api_client(auth_endpoints, prescriptions_endpoints, patients_endpoints)` + `create_test_patient`.

**Création**
1. `test_create_prescription_success` — rôle `medecin`, 201, `PrescriptionResponse` reflète les champs envoyés.
2. `test_create_prescription_missing_required_field_returns_422` — `medication` omis → 422 (validation Pydantic standard).
3. `test_create_prescription_invalid_dates_status_code` — `start_date > end_date` → constate le code réel renvoyé (422 attendu d'après Bug 3, à confirmer par exécution, pas par supposition) et documente en commentaire pourquoi (le contrôle 400 de l'endpoint est mort code).
4. `test_create_prescription_forbidden_for_secretaire` — 403 `"Accès refusé : rôle utilisateur insuffisant"` (même message qu'en 2d-1).
5. `test_create_prescription_unauthenticated_returns_401` — pas de header `Authorization` → 401.
6. `test_create_prescription_allowed_for_nurse` — rôle `nurse` → 201 (confirme que le routeur autorise bien ce rôle, pas seulement `medecin`/`admin`).
7. `test_create_prescription_allowed_for_manager` — rôle `manager` → 201 (idem).

**Lecture**
8. `test_get_prescription_success` — prescription préparée via `create_test_prescription`, retrouvée par `GET /prescriptions/?patient_id=...` pour obtenir son id, puis `GET /prescriptions/{id}` → 200.
9. `test_get_prescription_not_found` — id inexistant → 404 `"Prescription non trouvée"`.
10. `test_list_prescriptions_filters_by_patient_id` — deux patients, une prescription chacun, `GET /prescriptions/?patient_id=X` ne renvoie que celle de X.
11. `test_list_prescriptions_filters_by_date_range` — prescription avec `start_date` connue, `date_from`/`date_to` encadrant strictement cette date → apparaît ; encadrement qui l'exclut → n'apparaît pas.
12. `test_list_prescriptions_search` — recherche par nom de médicament ou code patient (vérifier le comportement réel de `list_paginated_with_relations` sur le paramètre `search` pendant l'implémentation, documenter si le filtre ne matche pas ce qui est attendu).

**Mise à jour**
13. `test_update_prescription_success` — modifie `dosage`, `PUT /prescriptions/{id}` → 200, la réponse reflète le changement.
14. `test_update_prescription_not_found` — id inexistant → 404, message **en anglais** `"Prescription with ID {id} not found"` (Bug 2, documenté tel quel).
15. `test_update_prescription_invalid_dates_status_code` — même logique que le test 3 mais sur `PUT` (Bug 3).

**Suppression**
16. `test_delete_prescription_success` — `DELETE /prescriptions/{id}` → 204, puis `GET /prescriptions/{id}` sur le même id → 404 (suppression physique confirmée, pas seulement logique).
17. `test_delete_prescription_nonexistent_returns_204_not_404` — id inexistant → **204** (pas 404), documente le Bug 1 tel quel avec un commentaire explicite renvoyant à `repositories/prescription_repo.py::delete()`.

**Renouvellements**
18. `test_renewals_returns_prescription_within_window` — prescription créée avec `prescribed_by=current_user.user_id` et `end_date` dans les 14 prochains jours, `GET /prescriptions/renewals` (rôle `medecin`) → la prescription créée apparaît dans la liste.
19. `test_renewals_excludes_prescription_outside_window` — même setup mais `end_date` à 30 jours → n'apparaît pas avec `within_days=14` par défaut.

**KPI**
20. `test_kpi_count_day_includes_todays_prescription` — prescription créée avec `start_date=aujourd'hui`, `GET /prescriptions/kpi/count?period=day` → le compteur inclut au moins cette prescription (comparer avant/après plutôt qu'une valeur absolue, pour ne pas dépendre du volume réel de la table).
21. `test_kpi_count_week` — `period=week` → réponse 200, structure `{"count": int}`.

**Historique patient**
22. `test_patient_prescription_history_returns_created_prescription` — `GET /prescriptions/patient/{patient_id}` → contient la prescription créée pour ce patient.
23. `test_patient_prescription_history_filters_by_status` — filtre `status=active` (valeur par défaut du modèle) → prescription incluse ; `status=completed` → exclue.

**RBAC transversal**
24. `test_prescriptions_list_forbidden_for_secretaire` — `GET /prescriptions/` en tant que `secretaire` → 403 (confirme que `role_required` s'applique à tout le routeur, pas seulement `POST /`).
25. `test_prescriptions_list_unauthenticated_returns_401` — idem sans authentification.

## Vérification

- Les ~25 tests neufs passent contre `HEAD` (`pytest tests/test_prescriptions.py -v`)
- Aucune régression sur la suite existante (`pytest tests/ -v`) — les échecs déjà connus (`test_patient_repo.py`, `test_prescription_repo.py`, le test B6 patients) restent attribués au travail en cours de l'utilisateur, pas à ce chantier
- Aucune donnée résiduelle dans `AH2` après la suite
- Mise à jour de `docs/superpowers/SUIVI-AVANCEMENT.md` : nouvelle catégorie de registre pour les Bugs 1/2/3 découverts ici

## Hors périmètre

- Comportement sur `patient_id` inexistant à la création (point d'incertitude ci-dessus — non garanti sans exécution empirique)
- Correctif de `repositories/prescription_repo.py` et fichiers associés — bloqué par le travail en cours de l'utilisateur (comme B1-B6)
- `medical_record_id` — pas de tests dédiés au lien avec les dossiers médicaux (module hors périmètre de ce chantier)
- Toute re-vérification de l'infrastructure d'authentification elle-même (2d-1)
