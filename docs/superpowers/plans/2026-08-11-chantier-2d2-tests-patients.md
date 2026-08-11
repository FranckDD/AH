# Chantier 2d-2 — Tests d'intégration patients — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Couvrir par des tests d'intégration réels le CRUD critique du module patients (`POST`/`GET`/`PUT`/`DELETE`/liste sur `/patients/`), en s'appuyant sur l'infrastructure `db_session`/`api_client`/`create_test_user`/`login` livrée par 2d-0 et 2d-1, et documenter (sans le corriger) un bug de résolution de rôle déjà présent sur `HEAD`.

**Architecture:** Une factory `create_test_patient()` ajoutée à `tests/conftest.py` (appelle directement `PatientRepository.create_patient()`, la vraie fonction stockée Postgres, pour préparer l'état des tests GET/PUT/DELETE/liste). Un seul fichier de tests, `tests/test_patients.py`, 10 tests.

**Tech Stack:** pytest, SQLAlchemy 2.0, FastAPI `TestClient`, PostgreSQL (base `AH2` locale réelle, fonctions/procédures stockées `create_patient`/`update_patient`/`delete_patient`).

## Global Constraints

- RBAC n'est pas re-testé (déjà couvert par 2d-1) — tous les tests utilisent le rôle `admin`, sauf le test qui documente explicitement le bug d'injection de drapeau (rôle `secretaire`, nécessaire pour observer le bug).
- `create_test_patient()` n'appelle jamais `session.commit()` — cohérent avec `PatientRepository.create_patient()` lui-même, qui ne commit pas (commenté "géré par le Service appelant").
- Chaque test qui exerce une route `/patients/*` surcharge **deux** `get_db()` : celui d'`auth_endpoints` (pour `role_required()` → `get_current_user()`) et celui de `patients_endpoints` (pour `get_patient_controller()`), via `api_client(auth_endpoints, patients_endpoints)`.
- Le test de liste utilise `search=` pour ne jamais dépendre du volume réel de la table `patients` (même leçon que la revue finale de 2d-1).
- Les deux tests de documentation de bug (`test_create_patient_role_flag_injection_does_not_trigger`, `test_update_patient_flag_protection_prevents_any_change`) doivent volontairement exercer le chemin où la règle métier attendue *devrait* changer une valeur, pour que le test échoue si le bug venait à être corrigé sans mise à jour du test — pas une simple vérification qu'une valeur par défaut reste inchangée.

---

## Task 1: Factory `create_test_patient` (ajout à `tests/conftest.py`)

**Files:**
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: `PatientRepository` (`repositories/patient_repo.py`, déjà existant, inchangé)
- Produces: `create_test_patient(session, current_user, **overrides) -> tuple[int, str]` (patient_id, code_patient)

- [ ] **Step 1: Ajouter les imports nécessaires en tête de `tests/conftest.py`**

Après les imports existants, ajouter :

```python
from datetime import date
from repositories.patient_repo import PatientRepository
```

- [ ] **Step 2: Ajouter `create_test_patient()` à la fin de `tests/conftest.py`**

```python
def create_test_patient(session, current_user, **overrides):
    """
    Cree un patient ephemere en appelant directement le repository
    (fonction stockee Postgres reelle create_patient()), dans la
    transaction de test. Le repo ne commit jamais lui-meme (voir son
    propre commentaire) - rien a annuler explicitement ici, le rollback
    de db_session suffit en fin de test.

    Reutilise le User cree par create_test_user() comme current_user
    (le repo lit user_id/full_name dessus via getattr).

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

- [ ] **Step 3: Vérifier que le fichier s'importe sans erreur**

```bash
python -c "from tests.conftest import create_test_patient; print('ok')"
```

Attendu : `ok`, pas d'exception.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: factory create_test_patient (chantier 2d-2)

Appelle directement PatientRepository.create_patient() (fonction
stockee Postgres reelle) pour preparer l'etat des tests GET/PUT/DELETE/
liste sans repasser par HTTP a chaque fois. Reutilise le User cree par
create_test_user() (chantier 2d-1) comme current_user.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Tests de création (`tests/test_patients.py`, partie 1)

**Files:**
- Create: `tests/test_patients.py`

**Interfaces:**
- Consumes: `db_session`, `api_client`, `create_test_user`, `login`, `create_test_patient` (tous déjà disponibles dans `tests/conftest.py` après Task 1)
- Produces: rien — fichier de test, complété par les tâches suivantes

- [ ] **Step 1: Écrire les 2 tests de création**

```python
# tests/test_patients.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import create_test_user, create_test_patient, login


def _auth_headers(client, username, password):
    token = login(client, username, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_patient_success(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_create", "admin", password="Correct123!")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_create", "Correct123!")

    payload = {
        "first_name": "Jean",
        "last_name": "Dupont",
        "birth_date": "1985-03-12",
    }
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["first_name"] == "Jean"
    assert body["last_name"] == "Dupont"
    assert body["birth_date"] == "1985-03-12"
    assert body["code_patient"]


def test_create_patient_role_flag_injection_does_not_trigger(db_session, api_client):
    """
    Documente un bug present sur HEAD (controller/patient_controller.py) :
    getattr(self.user, 'role_name', '') est toujours vide (cet attribut
    n'existe pas sur User), donc l'injection automatique de is_spiritual=True
    pour une secretaire ne se declenche jamais. On force explicitement
    is_spiritual=False dans la requete pour que ce test echoue si le bug
    est corrige sans que ce test soit mis a jour (voir SUIVI-AVANCEMENT.md,
    registre B6).
    """
    create_test_user(db_session, "test_patients_secretaire_create", "secretaire", password="Correct123!")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_secretaire_create", "Correct123!")

    payload = {
        "first_name": "Marie",
        "last_name": "Curie",
        "birth_date": "1990-06-01",
        "is_spiritual": False,
    }
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["is_spiritual"] is False
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_patients.py -v
```

Attendu : 2 `PASS`.

- [ ] **Step 3: Si un test échoue avec une erreur liée à la fonction stockée `create_patient` introuvable**

Vérifier que la fonction stockée existe bien dans la base `AH2` locale :

```bash
python -c "
from api_backend.backend_app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    r = conn.execute(text(\"SELECT proname FROM pg_proc WHERE proname = 'create_patient'\")).fetchall()
    print(r)
"
```

Attendu : au moins une ligne. Si vide, la base locale n'a pas cette fonction stockée — signaler l'anomalie à l'utilisateur plutôt que de contourner (ne pas réécrire `create_patient` pour utiliser l'ORM directement, ce serait un changement d'architecture hors périmètre de ce chantier).

- [ ] **Step 4: Commit**

```bash
git add tests/test_patients.py
git commit -m "test: creation de patients (chantier 2d-2)

Succes (201, champs corrects) et documentation du bug d'injection de
drapeau par role (getattr(self.user, 'role_name', '') toujours vide
sur HEAD - voir SUIVI-AVANCEMENT.md registre B6).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Tests de lecture (`tests/test_patients.py`, partie 2)

**Files:**
- Modify: `tests/test_patients.py`

**Interfaces:**
- Consumes: fixtures/helpers de Task 1-2, plus `_auth_headers` (définie en Task 2, réutilisée ici)
- Produces: rien

- [ ] **Step 1: Ajouter les 2 tests de lecture à la fin de `tests/test_patients.py`**

```python
def test_get_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_get", "admin", password="Correct123!")
    patient_id, code = create_test_patient(db_session, user, last_name="Lecture")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_get", "Correct123!")

    resp = client.get(f"/patients/{patient_id}", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_id"] == patient_id
    assert body["code_patient"] == code
    assert body["last_name"] == "Lecture"


def test_get_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_get404", "admin", password="Correct123!")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_get404", "Correct123!")

    resp = client.get("/patients/999999999", headers=headers)

    assert resp.status_code == 404
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_patients.py -v
```

Attendu : 4 `PASS` (2 de Task 2 + 2 nouveaux).

- [ ] **Step 3: Commit**

```bash
git add tests/test_patients.py
git commit -m "test: lecture de patients (chantier 2d-2)

GET /patients/{id} : succes et 404. Utilise create_test_patient()
(Task 1) pour preparer l'etat.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Tests de mise à jour (`tests/test_patients.py`, partie 3)

**Files:**
- Modify: `tests/test_patients.py`

**Interfaces:**
- Consumes: fixtures/helpers de Task 1-3
- Produces: rien

- [ ] **Step 1: Ajouter les 3 tests de mise à jour à la fin de `tests/test_patients.py`**

```python
def test_update_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_update", "admin", password="Correct123!")
    patient_id, _ = create_test_patient(db_session, user, first_name="Avant")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_update", "Correct123!")

    resp = client.put(f"/patients/{patient_id}", json={"first_name": "Apres"}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Apres"


def test_update_patient_flag_protection_prevents_any_change(db_session, api_client):
    """
    Documente un bug present sur HEAD : la condition
    "if 'admin' not in user_app_role" est toujours vraie (user_app_role
    vaut toujours '', voir Task 2), donc is_toxicology est systematiquement
    reecrit avec son ancienne valeur pour TOUT appelant, y compris un
    admin. Personne ne peut changer ce drapeau via PUT aujourd'hui (voir
    SUIVI-AVANCEMENT.md registre B6).
    """
    user = create_test_user(db_session, "test_patients_admin_flagprotect", "admin", password="Correct123!")
    patient_id, _ = create_test_patient(db_session, user, is_toxicology=False)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_flagprotect", "Correct123!")

    resp = client.put(f"/patients/{patient_id}", json={"is_toxicology": True}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["is_toxicology"] is False


def test_update_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_update404", "admin", password="Correct123!")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_update404", "Correct123!")

    resp = client.put("/patients/999999999", json={"first_name": "X"}, headers=headers)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Patient introuvable"
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_patients.py -v
```

Attendu : 7 `PASS` (4 de Task 2-3 + 3 nouveaux).

- [ ] **Step 3: Commit**

```bash
git add tests/test_patients.py
git commit -m "test: mise a jour de patients (chantier 2d-2)

Succes, 404, et documentation du bug de protection des drapeaux
(is_toxicology systematiquement reecrit avec son ancienne valeur pour
tout appelant - voir SUIVI-AVANCEMENT.md registre B6).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Tests de suppression et de liste (`tests/test_patients.py`, partie 4)

**Files:**
- Modify: `tests/test_patients.py`

**Interfaces:**
- Consumes: fixtures/helpers de Task 1-4
- Produces: rien — fichier de test terminal

- [ ] **Step 1: Ajouter les 3 derniers tests à la fin de `tests/test_patients.py`**

```python
def test_delete_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_delete", "admin", password="Correct123!")
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_delete", "Correct123!")

    delete_resp = client.delete(f"/patients/{patient_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/patients/{patient_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_delete404", "admin", password="Correct123!")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_delete404", "Correct123!")

    resp = client.delete("/patients/999999999", headers=headers)

    assert resp.status_code == 404


def test_list_patients_search_finds_created_patient(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_list", "admin", password="Correct123!")
    patient_id, _ = create_test_patient(db_session, user, last_name="Zzuniquesearchname")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_list", "Correct123!")

    resp = client.get("/patients/?search=Zzuniquesearchname", headers=headers)

    assert resp.status_code == 200
    ids = [p["patient_id"] for p in resp.json()]
    assert patient_id in ids
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_patients.py -v
```

Attendu : 10 `PASS`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_patients.py
git commit -m "test: suppression et liste de patients (chantier 2d-2)

DELETE (succes -> soft delete confirme via GET 404, et 404 sur id
inexistant) et GET liste filtree par search (jamais de dependance au
volume reel de la table, meme lecon que la revue finale de 2d-1).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Vérification finale

**Files:** aucun (vérification uniquement)

- [ ] **Step 1: Suite de tests complète**

```bash
pytest tests/ -v
```

Attendu : tous les tests passent, y compris les 10 nouveaux de ce chantier. Les échecs pré-existants et non liés (`test_patient_repo.py`, éventuellement `test_prescription_repo.py` selon l'état du travail en cours de l'utilisateur au moment du run) restent identiques à avant ce chantier.

- [ ] **Step 2: Confirmer l'absence de donnée résiduelle**

```bash
python -c "
from api_backend.backend_app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    users = conn.execute(text(\"SELECT username FROM users WHERE username LIKE 'test_%'\")).fetchall()
    patients = conn.execute(text(\"SELECT code_patient FROM patients WHERE last_name IN ('Dupont','Curie','Lecture','Avant','Apres','Zzuniquesearchname') OR first_name = 'Test'\")).fetchall()
    print('users:', users)
    print('patients:', patients)
"
```

Attendu : `users: []` et `patients: []`.

- [ ] **Step 3: Mettre à jour `docs/superpowers/SUIVI-AVANCEMENT.md`**

Marquer 2d-2 comme terminé dans le tableau de la feuille de route (commits de Task 1 à 5), ajouter un résumé dans la section détail (10 tests, factory `create_test_patient`, confirmation du bug B6 par des tests qui échoueraient si le bug était corrigé sans mise à jour du test).

- [ ] **Step 4: Commit de la mise à jour du suivi**

```bash
git add docs/superpowers/SUIVI-AVANCEMENT.md
git commit -m "docs: cloture du chantier 2d-2 dans le suivi d'avancement

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git push origin AH2_V3-1
```

- [ ] **Step 5: Récapitulatif**

Confirmer un par un :
- [ ] Création : succès + injection de drapeau par rôle documentée comme inopérante
- [ ] Lecture : succès + 404
- [ ] Mise à jour : succès + 404 + protection de drapeau documentée comme bloquant tout changement
- [ ] Suppression : succès (soft delete confirmé) + 404
- [ ] Liste : recherche retrouve le patient créé, sans dépendre du volume réel de la table
- [ ] Aucune donnée résiduelle dans `AH2`
- [ ] Prêt pour 2d-3 (tests prescriptions)
