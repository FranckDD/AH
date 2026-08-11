# Chantier 2d-2 — Tests d'intégration patients

**Date :** 2026-08-11
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** deuxième sous-chantier métier de 2d, construit sur l'infrastructure de 2d-0 et 2d-1

## Contexte

2d-1 a couvert authentification et RBAC en profondeur sur une route représentative. 2d-2 couvre le CRUD critique du module patients (`api_backend/backend_app/routes/patients/patients_endpoints.py`), le plus gros routeur du projet en nombre d'endpoints (KPI, listes filtrées par service, recherche...). RBAC n'est pas re-testé ici — déjà couvert par 2d-1 — tous les tests utilisent le rôle `admin`.

## Découverte pendant le cadrage — bug de résolution de rôle dans `controller/patient_controller.py`

**Décision validée avec l'utilisateur** : documenter tel quel, corriger dans un chantier dédié ultérieur.

Sur `HEAD` (code déjà commité, pas du travail en cours), `create_patient`, `update_patient` et `delete_patient` lisent `getattr(self.user, 'role_name', '')` (lignes ~30, 79, 147) pour déterminer le rôle métier de l'appelant. Or l'objet `user` retourné par `get_current_user()` n'a jamais d'attribut `role_name` — seulement `application_role.role_name` (relation SQLAlchemy) et `roles` (liste calculée, canonique). Conséquence :

- **`create_patient`** : `user_app_role` vaut toujours `''`. L'injection automatique censée poser `is_spiritual=True` pour une secrétaire ou `is_clinical=True` pour un médecin/infirmier/assistant ne se déclenche **jamais**.
- **`update_patient`** : `if 'admin' not in user_app_role` est **toujours vrai** (`'admin' not in ''`), donc les trois drapeaux (`is_toxicology`, `is_clinical`, `is_spiritual`) sont **systématiquement réécrits avec leur ancienne valeur**, quel que soit le rôle de l'appelant — y compris un admin. Personne ne peut changer ces drapeaux via `PUT /patients/{id}` aujourd'hui.

C'est plus grave que l'item **C1** déjà au registre (« mécanisme de résolution de rôle indépendant de `get_current_user()` ») : ce n'est pas juste une source différente, c'est une branche qui ne s'exécute jamais. Les tests de ce chantier documentent ce comportement réel (pas celui qu'on souhaiterait), et l'item est ajouté au registre comme correctif prioritaire distinct de C1.

## Portée

CRUD critique uniquement :
- `POST /patients/` (création)
- `GET /patients/{id}` (lecture)
- `PUT /patients/{id}` (mise à jour)
- `DELETE /patients/{id}` (suppression logique / soft delete)
- `GET /patients/?search=...` (liste, filtrée par recherche pour ne pas dépendre du volume réel de la table — même leçon que la revue finale de 2d-1)

Hors périmètre : les endpoints KPI/rapports (`/spiritual`, `/clinical`, `/by_doctor`, `/for_day`, `/kpi/...`, etc.) — non critiques, à couvrir plus tard si besoin. RBAC n'est pas re-testé (2d-1).

## Détail de l'implémentation

### 1. Factory de patient de test (ajout à `tests/conftest.py`)

```python
from repositories.patient_repo import PatientRepository
from datetime import date


def create_test_patient(session, current_user, **overrides):
    """
    Cree un patient ephemere en appelant directement le repository
    (fonction stockee Postgres reelle create_patient()), dans la
    transaction de test (jamais de commit explicite - le repo lui-meme
    n'en fait pas, conforme au commentaire "gere par le Service appelant").
    Retourne (patient_id, code_patient).
    """
    data = {
        "first_name": "Test",
        "last_name": "Patient",
        "birth_date": date(1990, 1, 1),
        **overrides,
    }
    repo = PatientRepository(session)
    return repo.create_patient(data, current_user)
```

Réutilise le `User` créé par `create_test_user()` (2d-1) comme `current_user` — le repo lit `user_id`/`full_name` dessus via `getattr`.

### 2. Tests (`tests/test_patients.py`)

Chaque test surcharge `auth_endpoints` et `patients_endpoints` (deux `get_db()` distincts, comme pour `/users/` en 2d-1) via `api_client(auth_endpoints, patients_endpoints)`, s'authentifie via `create_test_user()` + `login()` avec le rôle `admin`.

1. `test_create_patient_success` — 201, `PatientResponse` contient les champs envoyés, `code_patient` non vide.
2. `test_create_patient_role_flag_injection_does_not_trigger` — créé en tant que `secretaire` (rôle autorisé par le routeur mais différent d'admin) sans passer `is_spiritual`, la réponse a `is_spiritual: False` — documente le bug ci-dessus tel quel.
3. `test_get_patient_success` — patient préparé via `create_test_patient`, `GET /patients/{id}` → 200, champs cohérents.
4. `test_get_patient_not_found` — id inexistant → 404.
5. `test_update_patient_success` — modifie `first_name`, `PUT /patients/{id}` → 200, la réponse reflète le changement.
6. `test_update_patient_flag_protection_prevents_any_change` — patient créé avec `is_toxicology=False`, `PUT` en tant qu'admin avec `is_toxicology=True` → la réponse a toujours `is_toxicology: False` — documente le bug ci-dessus tel quel.
7. `test_update_patient_not_found` — id inexistant → 404 "Patient introuvable" (le contrôleur lève `ValueError("Patient introuvable")`, capturé par la route et remonté tel quel — texte différent du 404 de `GET`/`DELETE`, qui vient d'un autre chemin de code).
8. `test_delete_patient_success` — `DELETE /patients/{id}` → 204, puis `GET /patients/{id}` sur le même id → 404 (soft delete confirmé côté API).
9. `test_delete_patient_not_found` — id inexistant → 404.
10. `test_list_patients_search_finds_created_patient` — patient créé avec un `last_name` unique, `GET /patients/?search=<last_name>` → le patient apparaît dans la liste.

## Vérification

- Les 10 tests neufs passent (`pytest tests/test_patients.py -v`)
- Aucune régression sur la suite existante (`pytest tests/ -v`)
- Aucune donnée résiduelle dans `AH2` après la suite

## Hors périmètre

- Les endpoints KPI/rapports/listes filtrées par service du même routeur
- Le correctif du bug `role_name` — devient un item prioritaire séparé au registre, chantier dédié ultérieur
- Toute re-vérification de `role_required()` (2d-1)
