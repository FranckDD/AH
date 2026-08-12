# Chantier 2d-3 — Tests d'intégration prescriptions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Couvrir par des tests d'intégration réels tout le routeur `/prescriptions` (CRUD + `/renewals` + `/kpi/count` + `/patient/{id}`) et son propre RBAC (`medecin`, `nurse`, `admin`, `manager`), en s'appuyant sur l'infrastructure `db_session`/`api_client`/`create_test_user`/`create_test_patient`/`login` livrée par 2d-0/2d-1/2d-2, et documenter (sans les corriger) plusieurs défauts réels découverts sur `HEAD` pendant le cadrage de ce plan — vérifiés par exécution réelle contre un worktree jetable basé sur `HEAD` (jamais contre le répertoire de travail principal, contaminé par cinq fichiers du module en travail non commité).

**Architecture:** Une factory `create_test_prescription()` ajoutée à `tests/conftest.py` (appelle directement `PrescriptionRepository.create()`, la vraie procédure stockée Postgres, pour préparer l'état des tests GET/PUT/DELETE/renewals/KPI/historique). Un seul fichier de tests, `tests/test_prescriptions.py`, 25 tests.

**Tech Stack:** pytest, SQLAlchemy 2.0, FastAPI `TestClient`, PostgreSQL (base `AH2` locale réelle, procédures stockées `create_prescription`/`update_prescription`).

## Corrections empiriques par rapport à la spec (`2026-08-11-chantier-2d3-tests-prescriptions-design.md`)

La spec formulait trois hypothèses ("Bug 1/2/3") en partie confirmées, en partie infirmées par l'exécution réelle contre un worktree jetable basé sur `HEAD` (créé, sondé, puis supprimé pendant le cadrage de ce plan — jamais contre le répertoire de travail principal). Ce qui suit remplace la spec sur ces points précis :

- **Bug 1 (suppression idempotente, 204 au lieu de 404) : confirmé tel quel.** `DELETE /prescriptions/999999999` → 204.
- **Bug 2 de la spec (message anglais sur `PUT` 404) : infirmé.** `PrescriptionUpdate` impose `patient_id` comme champ requis (hérité de `PrescriptionBase`), donc le payload HTTP contient toujours `patient_id` — la branche `if 'patient_id' not in data` de `repositories/prescription_repo.py::update()` qui lèverait le `ValueError` anglais ne se déclenche **jamais** via l'API. En réalité, la procédure stockée `public.update_prescription` fait elle-même sa vérification d'existence et lève une exception PL/pgSQL **française** (`"Aucune prescription avec l'ID {id} n'existe."`) ; côté Python cette exception remonte comme `SQLAlchemyError` générique (pas `ValueError`), et l'endpoint répond **500** `"Erreur serveur lors de la mise à jour de la prescription"` — pas 404 du tout.
- **Bug 3 de la spec (contrôle 400 mort code, 422 réel) : confirmé dans son mécanisme, mais le résultat réel est plus grave qu'un simple 422.** `main.py::validation_exception_handler` (le gestionnaire global des erreurs 422) sérialise `exc.errors()` tel quel dans un `JSONResponse` (`json.dumps` standard, pas `jsonable_encoder`). Quand une erreur de validation vient d'un `model_validator` qui lève `ValueError` (le cas de `PrescriptionBase.check_dates`), Pydantic inclut l'exception **elle-même** (pas sa représentation texte) dans `error["ctx"]["error"]`, ce qui n'est pas sérialisable en JSON → **`TypeError` non intercepté**, propagé brut au client. Ce n'est donc ni un 400 ni un 422 propre : c'est un plantage. **Ce défaut n'est pas spécifique au module prescriptions** — il touche potentiellement toute route de l'API dont un schéma Pydantic utilise `raise ValueError(...)` dans un validateur. Sa gravité justifie un registre séparé et prioritaire (voir Task 8).

**Découverte supplémentaire, hors spec initiale — mise à jour partielle destructive (nouveau, plus grave que le Bug 2 initialement documenté).** `public.update_prescription` fait une réécriture complète et inconditionnelle de toutes les colonnes (`SET medication = p_medication, dosage = p_dosage, ...`), sans `COALESCE` avec les valeurs existantes. Comme `PrescriptionUpdate` a tous ses champs optionnels sauf `patient_id`, un `PUT` qui n'envoie que certains champs (ex. `{"patient_id": X, "dosage": "750mg"}`) envoie `None` pour tous les champs omis — et comme `medication`/`frequency`/`duration`/`start_date` sont `NOT NULL` en base, la procédure échoue avec `NotNullViolation`, remontée comme `IntegrityError` → **409 `"Conflit en base de données"`**. Un `PUT` qui omettrait seulement des colonnes nullable (`notes`, `end_date`, `medical_record_id`) ne planterait pas mais **effacerait silencieusement ces valeurs** — un comportement destructif qui ne casse rien visiblement. `PUT /prescriptions/{id}` n'est donc utilisable en pratique qu'avec un payload complet, jamais partiel — contrairement à ce qu'un client REST attendrait normalement d'un verbe `PUT`/`PATCH`-like.

**Découverte supplémentaire, remontée par l'implémenteur de Task 2 (pas par le cadrage initial de ce plan), vérifiée indépendamment avant correction du plan — le pire défaut trouvé sur ce module.** `POST /prescriptions/` ne renvoie **jamais** la prescription créée, même en cas de succès complet. `repo.create()` renvoie le booléen `True` ; en Python, `bool` est une sous-classe d'`int`, donc `isinstance(True, int)` vaut `True` — la branche `if isinstance(created, int):` (`prescriptions_endpoints.py:183`) intercepte systématiquement avant la branche `elif created is True or created is None:` (ligne 191) qui avait pourtant été écrite spécifiquement pour ce cas. Le code exécute donc `get_prescription(True)` → `session.get(Prescription, True)`, qui échoue contre PostgreSQL (`operator does not exist: integer = boolean`, confirmé par exécution directe). L'exception est avalée silencieusement, et l'endpoint retourne systématiquement son repli générique : 201 avec `{"detail": "Prescription créée (lecture non disponible)"}` — jamais le corps `PrescriptionResponse` pourtant déclaré par `response_model=PrescriptionResponse` (le repli utilise `JSONResponse` directement, qui contourne la validation de `response_model`). Un vrai client (le frontend Vue) ne reçoit donc jamais la prescription qu'il vient de créer. Les tests 1 et 6 de Task 2 (`test_create_prescription_success`, `test_create_prescription_allowed_for_nurse`) ont été corrigés en conséquence.

## Global Constraints

- RBAC re-testé sur ce routeur (contrairement à 2d-2) : `role_required("medecin", "nurse", "admin", "manager")`, différent de `/users/`. `secretaire` en est exclu.
- **Aucun rôle `manager` n'est seedé dans `application_roles`** (confirmé par requête directe : `admin`, `Assistant`, `laborantin`, `medecin`, `nurse`, `Psychologist`, `secretaire`, `SpiritualCounsellor`, `ToxicoManager` — 9 lignes, pas de `manager`). `api_backend/backend_app/security/role_map.py` documente `MANAGER` comme "réservé sans ligne en base (rôle en développement)". `create_test_user(session, ..., "manager", ...)` lèverait `NoResultFound`. La couverture RBAC positive de ce chantier se limite donc à `medecin` et `nurse` (les deux rôles réellement seedés parmi les quatre autorisés) — noté au registre, pas un test à écrire.
- Chaque test qui exerce une route `/prescriptions/*` surcharge **deux** `get_db()` via `api_client(auth_endpoints, prescriptions_endpoints)`. Les tests qui ont besoin d'un patient existant utilisent en plus `create_test_patient` (appel direct au repository, pas de `patients_endpoints` à surcharger puisqu'aucune requête HTTP n'est faite vers `/patients/`).
- Formes de réponse confirmées par exécution réelle :
  - `GET /prescriptions/` → `{"data": [...], "total": N, "page": N, "per_page": N}`
  - `GET /prescriptions/renewals` → **liste JSON nue** (pas de clé `data`)
  - `GET /prescriptions/patient/{id}` → **liste JSON nue** (pas de clé `data`)
  - `GET /prescriptions/kpi/count` → `{"count": N}`
- `search=` fait un `ilike '%valeur%'` sur `medication`/`code_patient`/`first_name`/`last_name` — **des données réelles préexistantes matchent des noms de médicaments courants** (confirmé : chercher `"Paracetamol"` renvoie aussi une ligne réelle `"paracetamol"` en base). Toujours utiliser une valeur de recherche hautement improbable (ex. `"Zzuniquemedicationsearch2d3"`) pour ne jamais dépendre du contenu réel de la table.
- `date_from`/`date_to` ne filtrent que si les **deux** sont fournis ensemble (`repositories/prescription_repo.py::list_paginated_with_relations` : `if date_from and date_to:`).
- **`PUT /prescriptions/{id}` doit toujours recevoir tous les champs de `PrescriptionBase`** (`patient_id`, `medication`, `dosage`, `frequency`, `duration`, `start_date`, `end_date`, `notes`) — jamais un payload partiel — sauf dans le test qui documente explicitement le bug de réécriture destructive (Task 4).
- Toute requête qui déclenche le `model_validator` de dates avec une erreur (`start_date > end_date`) fait planter `main.py::validation_exception_handler` avec un `TypeError` non intercepté, propagé jusqu'à l'appelant. `TestClient` (option par défaut `raise_server_exceptions=True`) relaie cette exception à l'appelant — les tests concernés utilisent `with pytest.raises(TypeError, match="not JSON serializable"):`.
- Comme 2d-2 : `create_test_prescription()` appelle `PrescriptionRepository.create()`, qui **fait un `session.commit()` interne** (contrairement à `PatientRepository.create_patient()`) — sans risque, la fixture `db_session` restaure la SAVEPOINT automatiquement après chaque transaction interne (voir son docstring).

---

## Task 1: Factory `create_test_prescription` (ajout à `tests/conftest.py`)

**Files:**
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: `PrescriptionRepository` (`repositories/prescription_repo.py`, déjà existant, inchangé), `create_test_patient` (2d-2, déjà dans `conftest.py`)
- Produces: `create_test_prescription(session, patient_id, current_user, **overrides) -> dict` (les données envoyées à la procédure stockée — pas d'id, `create()` ne retourne que `True`)

- [ ] **Step 1: Ajouter l'import nécessaire en tête de `tests/conftest.py`**

Après les imports existants (`from repositories.patient_repo import PatientRepository`), ajouter :

```python
from repositories.prescription_repo import PrescriptionRepository
```

- [ ] **Step 2: Ajouter `create_test_prescription()` à la fin de `tests/conftest.py`**

```python
def create_test_prescription(session, patient_id, current_user, **overrides):
    """
    Cree une prescription ephemere en appelant directement le repository
    (procedure stockee Postgres reelle create_prescription()), dans la
    transaction de test. Contrairement a create_test_patient(), le repo
    fait un session.commit() interne (voir son propre code) - sans
    risque, la fixture db_session relance la SAVEPOINT automatiquement.

    Necessite un patient existant (create_test_patient, chantier 2d-2) -
    patient_id est une cle etrangere obligatoire.

    Retourne le dict des donnees envoyees (create() ne renvoie que True -
    pour obtenir l'id reel, retrouver la prescription via
    GET /prescriptions/?patient_id=... apres coup).
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

- [ ] **Step 3: Vérifier que le fichier s'importe sans erreur**

```bash
python -c "from tests.conftest import create_test_prescription; print('ok')"
```

Attendu : `ok`, pas d'exception.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: factory create_test_prescription (chantier 2d-3)

Appelle directement PrescriptionRepository.create() (procedure stockee
Postgres reelle) pour preparer l'etat des tests GET/PUT/DELETE/renewals/
KPI/historique sans repasser par HTTP a chaque fois. Necessite un
patient existant (create_test_patient, chantier 2d-2).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Tests de création (`tests/test_prescriptions.py`, partie 1)

**Files:**
- Create: `tests/test_prescriptions.py`

**Interfaces:**
- Consumes: `db_session`, `api_client`, `create_test_user`, `create_test_patient`, `login`, `auth_headers` (tous déjà dans `tests/conftest.py`)
- Produces: rien — fichier de test, complété par les tâches suivantes

- [ ] **Step 1: Écrire les 6 tests de création**

```python
# tests/test_prescriptions.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.prescription import prescriptions_endpoints
from tests.conftest import create_test_user, create_test_patient, create_test_prescription, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_create_prescription_success(db_session, api_client):
    """
    Documente un bug reel sur HEAD, plus grave que prevu par la spec
    (SUIVI-AVANCEMENT.md registre E5) : prescriptions_endpoints.py::
    create_prescription() ne renvoie JAMAIS la prescription creee, meme
    en cas de succes complet. repo.create() renvoie le booleen True ;
    en Python, bool est une sous-classe de int, donc
    `isinstance(True, int)` vaut True (ligne 183) - la branche
    `elif created is True or created is None:` (ligne 191), ecrite pour
    gerer exactement ce cas, n'est JAMAIS atteinte : elle est
    court-circuitee par la branche int au-dessus. Le code prend donc le
    chemin `prescription_ctrl.get_prescription(True)` ->
    `repo.get(True)` -> `session.get(Prescription, True)`, qui plante
    contre PostgreSQL (`operator does not exist: integer = boolean` -
    confirme par execution directe pendant le cadrage de ce plan). Cette
    exception est avalee silencieusement (`except Exception: obj = None`),
    et l'endpoint retourne son repli generique : 201 avec
    {"detail": "Prescription creee (lecture non disponible)"} - jamais
    le corps PrescriptionResponse pourtant declare par
    response_model=PrescriptionResponse sur la route (le repli utilise
    JSONResponse directement, qui contourne la validation de response_model).
    Un vrai client (le frontend Vue) ne recoit donc jamais la prescription
    qu'il vient de creer.
    """
    user = create_test_user(db_session, "test_presc_medecin_create", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_create", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "medication": "Amoxicilline",
        "dosage": "500mg",
        "frequency": "2x/jour",
        "duration": "7 jours",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 201
    assert resp.json() == {"detail": "Prescription créée (lecture non disponible)"}


def test_create_prescription_missing_required_field_returns_422(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_422", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_422", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "dosage": "500mg",
        "frequency": "2x/jour",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 422


def test_create_prescription_invalid_dates_crashes_validation_handler(db_session, api_client):
    """
    Documente un bug transversal, pas specifique aux prescriptions (voir
    SUIVI-AVANCEMENT.md registre E1) : main.py::validation_exception_handler
    serialise exc.errors() tel quel en JSON (json.dumps standard, pas
    jsonable_encoder). Quand l'erreur vient d'un model_validator qui leve
    ValueError (PrescriptionBase.check_dates ici), Pydantic inclut
    l'exception ELLE-MEME (pas son texte) dans error['ctx']['error'] - non
    serialisable -> TypeError non intercepte, au lieu d'un 422 propre.
    Constate par execution reelle contre un worktree jetable base sur HEAD
    pendant le cadrage de ce plan (jamais contre le repertoire de travail
    principal, contamine par le travail en cours sur ce module).
    """
    user = create_test_user(db_session, "test_presc_medecin_dates", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_dates", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "medication": "Amoxicilline",
        "dosage": "500mg",
        "frequency": "2x/jour",
        "start_date": "2026-08-20",
        "end_date": "2026-08-10",
    }
    with pytest.raises(TypeError, match="not JSON serializable"):
        client.post("/prescriptions/", json=payload, headers=headers)


def test_create_prescription_forbidden_for_secretaire(db_session, api_client):
    user = create_test_user(db_session, "test_presc_secretaire", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_secretaire", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "medication": "Amoxicilline",
        "dosage": "500mg",
        "frequency": "2x/jour",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_create_prescription_unauthenticated_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, prescriptions_endpoints)

    payload = {
        "patient_id": 1,
        "medication": "Amoxicilline",
        "dosage": "500mg",
        "frequency": "2x/jour",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload)

    assert resp.status_code == 401


def test_create_prescription_allowed_for_nurse(db_session, api_client):
    """
    Confirme que le role nurse est bien autorise (pas de 403) - le corps
    de reponse n'est pas verifie ici pour le contenu de la prescription,
    voir test_create_prescription_success pour le bug du corps de reponse
    (registre E5, valable pour tout role autorise, pas specifique a
    nurse).

    "duration" est obligatoire dans ce payload malgre son statut Optional
    dans le schema Pydantic PrescriptionCreate : la colonne DB
    prescriptions.duration est NOT NULL, et rien ne comble cet ecart
    cote schema (registre E6 - omettre "duration" fait echouer TOUTE
    creation avec 409, quel que soit le role, decouvert empiriquement
    par l'implementeur de Task 2 puis verifie independamment).
    """
    user = create_test_user(db_session, "test_presc_nurse_create", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_nurse_create", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "medication": "Ibuprofene",
        "dosage": "200mg",
        "frequency": "1x/jour",
        "duration": "3 jours",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 201
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_prescriptions.py -v
```

Attendu : 6 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_prescriptions.py
git commit -m "test: creation de prescriptions (chantier 2d-3)

6 tests sur POST /prescriptions/ : succes, 422 (champ requis manquant),
plantage du gestionnaire de validation global sur dates invalides
(registre E1, transversal - pas specifique aux prescriptions), 403
secretaire, 401 non-authentifie, 201 pour le role nurse.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Tests de lecture (`tests/test_prescriptions.py`, partie 2)

**Files:**
- Modify: `tests/test_prescriptions.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 5 tests de lecture à la fin de `tests/test_prescriptions.py`**

```python
def test_get_prescription_success(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_get", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user, medication="Doliprane")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_get", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    resp = client.get(f"/prescriptions/{prescription_id}", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["prescription_id"] == prescription_id
    assert body["medication"] == "Doliprane"


def test_get_prescription_not_found(db_session, api_client):
    create_test_user(db_session, "test_presc_medecin_get404", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_get404", TEST_PASSWORD)

    resp = client.get("/prescriptions/999999999", headers=headers)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Prescription non trouvée"


def test_list_prescriptions_filters_by_patient_id(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_listpid", "medecin", password=TEST_PASSWORD)
    patient_a, _ = create_test_patient(db_session, user, last_name="PatientA2d3")
    patient_b, _ = create_test_patient(db_session, user, last_name="PatientB2d3")
    create_test_prescription(db_session, patient_a, user, medication="MedicamentA2d3")
    create_test_prescription(db_session, patient_b, user, medication="MedicamentB2d3")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_listpid", TEST_PASSWORD)

    resp = client.get(f"/prescriptions/?patient_id={patient_a}", headers=headers)

    assert resp.status_code == 200
    items = resp.json()["data"]
    assert all(p["patient_id"] == patient_a for p in items)
    assert any(p["medication"] == "MedicamentA2d3" for p in items)


def test_list_prescriptions_filters_by_date_range(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_presc_medecin_listdate", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        medication="MedicamentDateRange2d3",
        start_date=date_cls(2030, 1, 15),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_listdate", TEST_PASSWORD)

    resp = client.get("/prescriptions/?date_from=2030-01-01&date_to=2030-01-31", headers=headers)
    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()["data"]]
    assert "MedicamentDateRange2d3" in medications

    resp_excl = client.get("/prescriptions/?date_from=2030-02-01&date_to=2030-02-28", headers=headers)
    assert resp_excl.status_code == 200
    medications_excl = [p["medication"] for p in resp_excl.json()["data"]]
    assert "MedicamentDateRange2d3" not in medications_excl


def test_list_prescriptions_search_finds_by_medication(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_search", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user, medication="Zzuniquemedicationsearch2d3")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_search", TEST_PASSWORD)

    resp = client.get("/prescriptions/?search=Zzuniquemedicationsearch2d3", headers=headers)

    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()["data"]]
    assert "Zzuniquemedicationsearch2d3" in medications
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_prescriptions.py -v
```

Attendu : 11 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_prescriptions.py
git commit -m "test: lecture et liste de prescriptions (chantier 2d-3)

5 tests : GET par id (succes + 404), liste filtree par patient_id, par
plage de dates (date_from/date_to), par recherche sur le medicament
(valeur hautement unique - une recherche sur 'Paracetamol' matche des
donnees reelles preexistantes, constate empiriquement).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Tests de mise à jour (`tests/test_prescriptions.py`, partie 3)

**Files:**
- Modify: `tests/test_prescriptions.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-3
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 4 tests de mise à jour à la fin de `tests/test_prescriptions.py`**

```python
def test_update_prescription_success(db_session, api_client):
    """
    Le payload doit contenir TOUS les champs de PrescriptionBase : la
    procedure stockee public.update_prescription fait une reecriture
    complete et inconditionnelle de toutes les colonnes (pas de
    COALESCE avec les valeurs existantes) - voir
    test_update_prescription_partial_payload_returns_409 ci-dessous et
    SUIVI-AVANCEMENT.md registre E4.
    """
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_presc_medecin_update", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        medication="Doliprane", dosage="500mg",
        start_date=date_cls.today(), end_date=date_cls.today() + timedelta(days=5),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_update", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    full_payload = {
        "patient_id": patient_id,
        "medication": "Doliprane",
        "dosage": "1000mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": str(date_cls.today()),
        "end_date": str(date_cls.today() + timedelta(days=5)),
        "notes": None,
    }
    resp = client.put(f"/prescriptions/{prescription_id}", json=full_payload, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["dosage"] == "1000mg"


def test_update_prescription_partial_payload_returns_409(db_session, api_client):
    """
    Documente un bug reel sur HEAD (constate par execution reelle,
    SUIVI-AVANCEMENT.md registre E4) : public.update_prescription
    reecrit TOUTES les colonnes inconditionnellement, y compris celles
    omises du payload (mises a NULL). Comme medication/frequency/
    duration/start_date sont NOT NULL en base, un PUT partiel (ici :
    seulement patient_id + dosage) declenche une violation de contrainte
    -> IntegrityError -> 409. PUT /prescriptions/{id} n'est donc
    utilisable en pratique qu'avec un payload complet (voir le test
    precedent), jamais partiel comme un client REST l'attendrait
    normalement d'un verbe PUT.
    """
    user = create_test_user(db_session, "test_presc_medecin_updatepartial", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_updatepartial", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    resp = client.put(
        f"/prescriptions/{prescription_id}",
        json={"patient_id": patient_id, "dosage": "750mg"},
        headers=headers,
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Conflit en base de données"


def test_update_prescription_not_found_returns_500(db_session, api_client):
    """
    Documente un bug reel sur HEAD (constate par execution reelle,
    SUIVI-AVANCEMENT.md registre E3 - corrige l'hypothese initiale de
    la spec, qui supposait un message anglais 404) : la procedure
    stockee public.update_prescription fait elle-meme sa verification
    d'existence et leve une exception PL/pgSQL francaise
    ("Aucune prescription avec l'ID {id} n'existe."). Cote Python, cette
    exception remonte comme SQLAlchemyError generique (pas ValueError -
    la branche qui le leverait dans repositories/prescription_repo.py::
    update() ne se declenche jamais via l'API, patient_id etant toujours
    present dans le payload). L'endpoint capture SQLAlchemyError et
    repond 500, pas 404.
    """
    user = create_test_user(db_session, "test_presc_medecin_update404", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_update404", TEST_PASSWORD)

    resp = client.put("/prescriptions/999999999", json={"patient_id": patient_id}, headers=headers)

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Erreur serveur lors de la mise à jour de la prescription"


def test_update_prescription_invalid_dates_crashes_validation_handler(db_session, api_client):
    """
    Meme mecanisme que test_create_prescription_invalid_dates_crashes_
    validation_handler (Task 2) : PrescriptionUpdate herite du meme
    model_validator que PrescriptionCreate sur PrescriptionBase, et
    passe par le meme gestionnaire d'erreurs global. Confirme par
    execution reelle sur PUT specifiquement (pas seulement deduit par
    analogie) pendant le cadrage de ce plan.
    """
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_presc_medecin_updatedates", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        start_date=date_cls.today(), end_date=date_cls.today() + timedelta(days=5),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_updatedates", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    full_payload = {
        "patient_id": patient_id,
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": "2026-08-20",
        "end_date": "2026-08-10",
        "notes": None,
    }
    with pytest.raises(TypeError, match="not JSON serializable"):
        client.put(f"/prescriptions/{prescription_id}", json=full_payload, headers=headers)
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_prescriptions.py -v
```

Attendu : 15 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_prescriptions.py
git commit -m "test: mise a jour de prescriptions (chantier 2d-3)

4 tests sur PUT /prescriptions/{id}. Deux corrigent des hypotheses
fausses de la spec initiale, verifiees par execution reelle contre un
worktree jetable base sur HEAD : le 404 attendu sur id inexistant est
en realite un 500 (la procedure stockee leve sa propre exception
francaise, remontee comme SQLAlchemyError generique) ; et une
decouverte non prevue par la spec - la procedure stockee fait une
reecriture complete inconditionnelle de toutes les colonnes, donc un
PUT partiel efface silencieusement les colonnes omises et plante avec
409 si l'une d'elles est NOT NULL (registre E3/E4).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Tests de suppression (`tests/test_prescriptions.py`, partie 4)

**Files:**
- Modify: `tests/test_prescriptions.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-4
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 2 tests de suppression à la fin de `tests/test_prescriptions.py`**

```python
def test_delete_prescription_success(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_delete", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_delete", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    delete_resp = client.delete(f"/prescriptions/{prescription_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/prescriptions/{prescription_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_prescription_nonexistent_returns_204_not_404(db_session, api_client):
    """
    Documente un bug reel sur HEAD (SUIVI-AVANCEMENT.md registre E2) :
    repositories/prescription_repo.py::delete() execute un DELETE FROM
    brut sans verifier le rowcount, et retourne toujours True. Le
    modele Prescription n'a pas de suppression logique (contrairement a
    Patient) - c'est une suppression physique, mais sans garde-fou :
    supprimer un id inexistant renvoie 204 au lieu du 404 attendu.
    """
    create_test_user(db_session, "test_presc_medecin_delete404", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_delete404", TEST_PASSWORD)

    resp = client.delete("/prescriptions/999999999", headers=headers)

    assert resp.status_code == 204
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_prescriptions.py -v
```

Attendu : 17 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_prescriptions.py
git commit -m "test: suppression de prescriptions (chantier 2d-3)

2 tests sur DELETE /prescriptions/{id} : succes (suppression physique
confirmee via GET 404 apres coup) + documentation du bug de suppression
idempotente silencieuse (204 au lieu de 404 sur un id inexistant,
registre E2).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Tests renewals + KPI (`tests/test_prescriptions.py`, partie 5)

**Files:**
- Modify: `tests/test_prescriptions.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-5
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 4 tests renewals/KPI à la fin de `tests/test_prescriptions.py`**

```python
def test_renewals_returns_prescription_within_window(db_session, api_client):
    """
    GET /prescriptions/renewals renvoie une LISTE JSON NUE (pas de cle
    "data") - confirme par execution reelle, different du format de
    GET /prescriptions/ (liste paginee avec data/total/page/per_page).
    """
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_presc_medecin_renewals", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        medication="MedicamentRenewal2d3",
        end_date=date_cls.today() + timedelta(days=5),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_renewals", TEST_PASSWORD)

    resp = client.get("/prescriptions/renewals", headers=headers)

    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()]
    assert "MedicamentRenewal2d3" in medications


def test_renewals_excludes_prescription_outside_window(db_session, api_client):
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_presc_medecin_renewalsout", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        medication="MedicamentRenewalOut2d3",
        end_date=date_cls.today() + timedelta(days=30),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_renewalsout", TEST_PASSWORD)

    resp = client.get("/prescriptions/renewals?within_days=14", headers=headers)

    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()]
    assert "MedicamentRenewalOut2d3" not in medications


def test_kpi_count_day_includes_todays_prescription(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_presc_medecin_kpiday", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_kpiday", TEST_PASSWORD)

    before = client.get("/prescriptions/kpi/count?period=day", headers=headers).json()["count"]
    create_test_prescription(db_session, patient_id, user, start_date=date_cls.today())
    after = client.get("/prescriptions/kpi/count?period=day", headers=headers).json()["count"]

    assert after == before + 1


def test_kpi_count_week(db_session, api_client):
    create_test_user(db_session, "test_presc_medecin_kpiweek", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_kpiweek", TEST_PASSWORD)

    resp = client.get("/prescriptions/kpi/count?period=week", headers=headers)

    assert resp.status_code == 200
    assert isinstance(resp.json()["count"], int)
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_prescriptions.py -v
```

Attendu : 21 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_prescriptions.py
git commit -m "test: renouvellements et KPI de prescriptions (chantier 2d-3)

4 tests : GET /prescriptions/renewals (dans la fenetre / hors fenetre
within_days, format liste nue confirme par execution reelle) et
GET /prescriptions/kpi/count (day via comparaison avant/apres pour ne
pas dependre du volume reel de la table, week via verification de
structure).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Tests historique patient (`tests/test_prescriptions.py`, partie 6)

**Files:**
- Modify: `tests/test_prescriptions.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-6
- Produces: rien — complété par la tâche suivante

- [ ] **Step 1: Ajouter les 2 tests d'historique patient à la fin de `tests/test_prescriptions.py`**

```python
def test_patient_prescription_history_returns_created_prescription(db_session, api_client):
    """
    GET /prescriptions/patient/{id} renvoie aussi une LISTE JSON NUE,
    comme /renewals - confirme par execution reelle.
    """
    user = create_test_user(db_session, "test_presc_medecin_history", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user, medication="MedicamentHistory2d3")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_history", TEST_PASSWORD)

    resp = client.get(f"/prescriptions/patient/{patient_id}", headers=headers)

    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()]
    assert "MedicamentHistory2d3" in medications


def test_patient_prescription_history_filters_by_status(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_historystatus", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user, medication="MedicamentActive2d3")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_historystatus", TEST_PASSWORD)

    resp_active = client.get(f"/prescriptions/patient/{patient_id}?status=active", headers=headers)
    assert resp_active.status_code == 200
    assert any(p["medication"] == "MedicamentActive2d3" for p in resp_active.json())

    resp_completed = client.get(f"/prescriptions/patient/{patient_id}?status=completed", headers=headers)
    assert resp_completed.status_code == 200
    assert not any(p["medication"] == "MedicamentActive2d3" for p in resp_completed.json())
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_prescriptions.py -v
```

Attendu : 23 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_prescriptions.py
git commit -m "test: historique des prescriptions par patient (chantier 2d-3)

2 tests sur GET /prescriptions/patient/{id} : la prescription creee
apparait dans l'historique, et le filtre status=active/completed
distingue correctement (status='active' est la valeur par defaut du
modele Prescription).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: RBAC transversal, vérification finale, registre

**Files:**
- Modify: `tests/test_prescriptions.py`
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-7
- Produces: rien — dernière tâche du chantier

- [ ] **Step 1: Ajouter les 2 tests RBAC transversaux à la fin de `tests/test_prescriptions.py`**

```python
def test_prescriptions_list_forbidden_for_secretaire(db_session, api_client):
    """
    Confirme que role_required s'applique a tout le routeur (declare au
    niveau du router, pas seulement sur POST /) - deja verifie sur
    POST / (Task 2), verifie ici sur GET / pour eliminer tout doute.
    """
    create_test_user(db_session, "test_presc_secretaire_list", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_secretaire_list", TEST_PASSWORD)

    resp = client.get("/prescriptions/", headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_prescriptions_list_unauthenticated_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, prescriptions_endpoints)

    resp = client.get("/prescriptions/")

    assert resp.status_code == 401
```

- [ ] **Step 2: Suite de tests complète**

```bash
pytest tests/test_prescriptions.py -v
```

Attendu : 25 tests, tous PASS.

```bash
pytest tests/ -v
```

Attendu : aucune régression sur les tests déjà verts avant ce chantier. Les échecs déjà connus et attribués au travail en cours de l'utilisateur restent inchangés : `test_patient_repo.py` (2 tests, source déjà commitée mais tests obsolètes), `test_prescription_repo.py` (2 tests, `repositories/prescription_repo.py` en pleine réécriture non commitée — **ce chantier n'y touche pas**, il ajoute un fichier séparé `test_prescriptions.py`), et `test_patients.py::test_update_patient_flag_protection_prevents_any_change` (le bug `B6` déjà corrigé dans le `controller/patient_controller.py` non commité de l'utilisateur).

- [ ] **Step 3: Confirmer l'absence de donnée résiduelle**

```bash
psql -U postgres -h localhost -d AH2 -c "SELECT COUNT(*) FROM prescriptions WHERE medication LIKE '%2d3%' OR medication IN ('Amoxicilline','Ibuprofene','Doliprane');"
```

Attendu : `0` — tous les tests s'exécutent dans la transaction annulée de `db_session`, rien n'est jamais réellement committé de façon persistante dans la base partagée.

- [ ] **Step 4: Mettre à jour `docs/superpowers/SUIVI-AVANCEMENT.md`**

Ajouter la section de détail suivante pour le chantier 2d-3 dans "Détail des chantiers terminés", juste après la section "### Chantier 2d-2 — Tests d'intégration patients" existante :

```markdown
### Chantier 2d-3 — Tests d'intégration prescriptions
Spec : `2026-08-11-chantier-2d3-tests-prescriptions-design.md` · Plan : `2026-08-11-chantier-2d3-tests-prescriptions.md`
Troisième sous-chantier métier, construit sur 2d-0/2d-1/2d-2. Exécuté via subagent-driven-development, worktree isolé (`.claude/worktrees/chantier-2d3-tests-prescriptions`). 25 tests neufs dans `tests/test_prescriptions.py`, tout le routeur `/prescriptions` : CRUD, `/renewals`, `/kpi/count`, `/patient/{id}`, RBAC propre à ce routeur (`medecin`, `nurse`, `admin`, `manager` — différent de `/users/`) :
- Création : succès (documente le bug `E5`, le corps de réponse réel est le repli générique) + 422 (champ requis manquant) + plantage `TypeError` du gestionnaire de validation global sur dates invalides (`E1`, transversal) + 403 secrétaire + 401 non-authentifié + 201 pour le rôle `nurse`.
- Lecture : succès + 404 + liste filtrée par `patient_id`/plage de dates/recherche (valeur hautement unique pour éviter toute collision avec des données réelles préexistantes).
- Mise à jour : succès avec payload complet + 409 sur payload partiel (`E4`, réécriture destructive de la procédure stockée) + 500 sur id inexistant (`E3`, corrige une hypothèse initiale erronée de la spec) + même plantage `TypeError` que la création.
- Suppression : suppression physique confirmée via `GET` 404 après coup + documentation du bug `E2` (204 au lieu de 404 sur un id inexistant).
- Renouvellements et KPI : fenêtre `within_days` (dans/hors fenêtre) et compteurs jour/semaine (comparaison avant/après pour ne pas dépendre du volume réel de la table).
- Historique patient : prescription créée retrouvée + filtre par `status`.
- RBAC transversal : confirme que `role_required` s'applique à tout le routeur, pas seulement à `POST /`.

**Périmètre élargi par rapport à 2d-1/2d-2** (demandé explicitement par l'utilisateur, malgré cinq fichiers du module en travail non commité) : couverture complète du routeur plutôt que le seul CRUD critique, RBAC re-testé (routeur avec ses propres rôles autorisés), et un cadrage du plan appuyé sur exécution réelle contre un worktree jetable basé sur `HEAD` (créé et supprimé pendant le cadrage) plutôt que sur la seule lecture de code — ce qui a permis d'infirmer deux hypothèses de la spec initiale et de découvrir deux bugs supplémentaires (`E5`, `E6`) non anticipés, remontés par les implémenteurs de Task 2 puis vérifiés indépendamment avant correction du plan.

**Nouvelle catégorie de registre E** (6 items, détaillée ci-dessous) : contrairement à la catégorie B, ces défauts sont dans du code déjà committé (`main.py`, procédures stockées, schémas Pydantic) et ne dépendent d'aucun fichier en travail en cours côté utilisateur — corrigeables dès qu'un chantier dédié leur est consacré. `E1` et `E5` sont les plus prioritaires : `E1` est transversal (touche potentiellement toute route utilisant un validateur Pydantic qui lève `ValueError`), et `E5` signifie que la route de création la plus utilisée du module ne renvoie jamais son contrat documenté à un vrai client.
```

Puis, une nouvelle catégorie de registre **E** après la catégorie D existante :

```markdown
### E — Découvertes du chantier 2d-3 (prescriptions), non bloquées par le travail en cours

Contrairement aux catégories B, ces défauts sont dans du code purement
committé (`main.py`, procédures stockées) et ne dépendent d'aucun fichier
en travail en cours côté utilisateur — ils peuvent être corrigés dès
qu'un chantier dédié leur est consacré.

| # | Découverte | Fichier | Gravité |
|---|---|---|---|
| E1 | `main.py::validation_exception_handler` sérialise `exc.errors()` tel quel en JSON (`json.dumps` standard). Quand une erreur de validation vient d'un `model_validator` qui lève `ValueError` (ex. `PrescriptionBase.check_dates`), Pydantic inclut l'exception elle-même dans `error["ctx"]["error"]` — non sérialisable → `TypeError` non intercepté, propagé brut au client au lieu d'un 422 propre. **Transversal : touche potentiellement toute route dont un schéma Pydantic utilise `raise ValueError(...)` dans un validateur**, pas seulement les prescriptions. | `api_backend/backend_app/main.py` | Élevée — un client réel reçoit une erreur 500 non structurée là où un 422 propre est attendu |
| E2 | `repositories/prescription_repo.py::delete()` exécute un `DELETE FROM` brut sans vérifier le rowcount, retourne toujours `True`. Pas de suppression logique sur `Prescription` (à la différence de `Patient`) — suppression physique sans garde-fou : `DELETE /prescriptions/{id}` sur un id inexistant renvoie 204 au lieu de 404. | `repositories/prescription_repo.py` | Faible — comportement silencieux, pas de perte de données |
| E3 | `PUT /prescriptions/{id}` sur un id inexistant renvoie 500 (`"Erreur serveur lors de la mise à jour de la prescription"`), pas 404 : la procédure stockée `public.update_prescription` lève sa propre exception PL/pgSQL sur un id absent, remontée comme `SQLAlchemyError` générique. | `repositories/prescription_repo.py`, procédure stockée `public.update_prescription` (non tracée — item `D2`) | Moyenne |
| E4 | `public.update_prescription` réécrit toutes les colonnes inconditionnellement (pas de `COALESCE`). Un `PUT` avec un payload partiel remet à `NULL` les champs omis — plante en 409 si un champ `NOT NULL` est omis, sinon efface silencieusement les champs nullable (`notes`, `end_date`, `medical_record_id`). `PUT` n'est utilisable qu'avec un payload complet, jamais partiel. | procédure stockée `public.update_prescription` (non tracée — item `D2`) | Élevée — perte de données silencieuse possible sur les champs nullable |
| E5 | `POST /prescriptions/` ne renvoie **jamais** la prescription créée, même en cas de succès complet. `repo.create()` renvoie `True` ; comme `bool` est une sous-classe d'`int` en Python, `isinstance(True, int)` vaut `True` — la branche `if isinstance(created, int):` intercepte systématiquement avant la branche `elif created is True or created is None:` écrite pour ce cas précis. Le code tente alors `get_prescription(True)`, qui plante contre PostgreSQL (`operator does not exist: integer = boolean`), silencieusement avalé, et retombe sur le repli générique `{"detail": "Prescription créée (lecture non disponible)"}` — jamais le corps `PrescriptionResponse` déclaré par la route. Un vrai client (le frontend Vue) ne reçoit donc jamais la prescription qu'il vient de créer. | `api_backend/backend_app/routes/prescription/prescriptions_endpoints.py:183-207` | **La plus élevée du registre E** — la route de création la plus utilisée de ce module ne remplit jamais son contrat documenté |
| E6 | La colonne `prescriptions.duration` est `NOT NULL` en base (`models/prescription.py`), mais `PrescriptionBase.duration` est `Optional[str] = None` côté Pydantic et `PrescriptionCreate` ne le rend pas requis (contrairement à `medication`/`dosage`/`frequency`/`start_date`, explicitement surchargés en requis). Toute création qui omet `duration` échoue en 409 `IntegrityError`, quel que soit le rôle — découvert par l'implémenteur de Task 2 sur un payload de test, vérifié indépendamment (`nullable=False` confirmé sur le modèle). | `api_backend/backend_app/routes/prescription/prescriptions_schemas.py:12`, `models/prescription.py:16` | Moyenne — écart schéma/base cohérent avec E4 (mêmes colonnes `NOT NULL` que la procédure de mise à jour) |

**Note (pas un bug, une limite de couverture)** : aucun rôle `manager` n'est seedé dans `application_roles` (`api_backend/backend_app/security/role_map.py` le documente comme "réservé, en développement"). La couverture RBAC positive de ce chantier se limite à `medecin`/`nurse` parmi les 4 rôles autorisés par le routeur.
```

- [ ] **Step 5: Commit de la mise à jour du suivi**

```bash
git add tests/test_prescriptions.py docs/superpowers/SUIVI-AVANCEMENT.md
git commit -m "docs: cloture du chantier 2d-3 dans le suivi d'avancement

25 tests sur tout le routeur /prescriptions (CRUD + renewals + KPI +
historique patient + RBAC propre a ce routeur). Nouvelle categorie de
registre E (6 items) - contrairement a B, ces defauts sont dans du code
deja committe (main.py, procedures stockees, schemas Pydantic), pas
bloques par le travail en cours de l'utilisateur : E1 (plantage
transversal du gestionnaire de validation sur tout model_validator qui
leve ValueError, pas specifique aux prescriptions), E2 (suppression
idempotente silencieuse), E3 (500 au lieu de 404 sur update d'un id
inexistant), E4 (mise a jour partielle destructive - la procedure
stockee reecrit toutes les colonnes sans COALESCE), E5 (POST ne renvoie
jamais la prescription creee - bool/int aliasing en Python fait
court-circuiter la branche prevue pour ce cas, le plus grave item du
registre E), E6 (colonne duration NOT NULL en base mais Optional cote
Pydantic - toute creation omettant ce champ echoue en 409).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Récapitulatif**

Chantier 2d-3 terminé : 25 tests neufs (`tests/test_prescriptions.py`), aucune régression, 6 nouveaux items de registre (E1-E6) dont deux (E1 transversal, E5 le plus grave du registre) prioritaires pour un futur chantier de correctifs. Prêt pour `superpowers:finishing-a-development-branch`.
