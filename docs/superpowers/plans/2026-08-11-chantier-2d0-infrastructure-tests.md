# Chantier 2d-0 — Infrastructure de test d'intégration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fournir une fixture pytest permettant d'écrire de vrais tests d'intégration (base de données réelle, appels HTTP réels via `TestClient`) sans jamais laisser de donnée résiduelle dans `AH2`, même quand le code testé appelle `session.commit()` en interne.

**Architecture:** `tests/conftest.py` centralise la fixture `db_session` (pattern SQLAlchemy 2.0 de transaction externe + SAVEPOINT auto-relancée) et un helper `override_get_db()` pour brancher cette session dans les dépendances FastAPI, module de routes par module de routes (14 `get_db()` distincts, pas de point d'interception unique).

**Tech Stack:** pytest, SQLAlchemy 2.0, FastAPI `TestClient`, PostgreSQL (base `AH2` locale réelle).

## Global Constraints

- Le pattern de rollback a été **vérifié empiriquement contre la base locale réelle** pendant le cadrage (script manuel, confirmé sans fuite de donnée même avec un `commit()` interne simulé) — le code de ce plan reproduit exactement ce qui a été vérifié, ne pas s'en écarter sans re-vérifier.
- Ne jamais utiliser `SessionLocal` (bindée directement à l'engine) pour les tests — toujours une `Session` bindée à la connexion transactionnelle de la fixture, sinon le rollback n'a aucune prise dessus.
- `tests/conftest.py` n'existe pas encore — fichier neuf, aucune isolation nécessaire.

---

## Task 1: Fixture `db_session` + helper `override_get_db`

**Files:**
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: fixture pytest `db_session` (type `sqlalchemy.orm.Session`), fonction `override_get_db(app, module, session)`. Consommées par toutes les tâches suivantes et par les futurs sous-chantiers 2d-1 à 2d-4.

- [ ] **Step 1: Créer `tests/conftest.py`**

```python
# tests/conftest.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from api_backend.backend_app.database import engine


@pytest.fixture
def db_session():
    """
    Session transactionnelle pour les tests d'integration.

    Pattern SQLAlchemy 2.0 "rejoindre une transaction externe" : une
    transaction est ouverte sur la connexion, une SAVEPOINT imbriquee
    est relancee automatiquement a chaque fin de transaction interne
    (y compris un session.commit() appele par le code teste). Seul le
    rollback de la transaction EXTERNE, en fin de fixture, annule tout
    - garanti meme si le code teste a fait plusieurs commit() internes.

    Verifie empiriquement contre la base AH2 locale pendant le cadrage
    de ce chantier (voir docs/superpowers/specs/2026-08-11-chantier-2d0-infrastructure-tests-design.md).
    """
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


def override_get_db(app, module, session):
    """
    Branche la session transactionnelle de test a la place du get_db()
    reel d'un module de routes donne. Chaque module de routes definit
    sa propre fonction get_db() (14 au total) - il n'existe pas de
    point d'interception unique, cet helper doit etre appele une fois
    par module dont les routes sont exercees dans un test.

    Usage : override_get_db(app, patients_endpoints, db_session)
    """
    app.dependency_overrides[module.get_db] = lambda: session
```

- [ ] **Step 2: Vérifier que le fichier s'importe sans erreur**

```bash
python -c "from tests.conftest import db_session, override_get_db; print('ok')"
```

Attendu : `ok`, pas d'exception.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: fixture db_session pour les tests d'integration (chantier 2d-0)

Pattern SQLAlchemy 2.0 de transaction externe + SAVEPOINT auto-relancee,
verifie empiriquement contre la base AH2 locale pendant le cadrage
(commit() interne simule, rollback externe confirme sans fuite de
donnee depuis une connexion separee).

override_get_db() : helper pour brancher cette session a la place
d'un get_db() de module de routes (14 distincts, ARC-05).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Méta-test — valider que le rollback fonctionne réellement

**Files:**
- Create: `tests/test_conftest_db_session.py`

**Interfaces:**
- Consumes: fixture `db_session` (Task 1)
- Produces: rien — ce test valide l'infrastructure elle-même, ne sert pas de base à d'autres tests

- [ ] **Step 1: Écrire le méta-test**

```python
# tests/test_conftest_db_session.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from api_backend.backend_app.database import engine


def test_rollback_survives_internal_commit(db_session):
    """
    Verifie que la fixture db_session annule bien TOUT, y compris les
    donnees qu'un commit() interne (comme le font plusieurs
    controleurs, ex. sync_simple_patient_creation) aurait rendu
    visibles a une autre connexion pendant le test.
    """
    # 1. Insertion + commit() interne, comme le ferait un controleur
    db_session.execute(
        text("INSERT INTO application_roles (role_name) VALUES ('TEST_ROLE_TMP_1')")
    )
    db_session.commit()

    # 2. Une deuxieme insertion apres le commit interne, pour verifier
    #    que la SAVEPOINT a bien redemarre (sinon cette ligne echouerait
    #    ou ne serait pas couverte par un rollback ulterieur)
    db_session.execute(
        text("INSERT INTO application_roles (role_name) VALUES ('TEST_ROLE_TMP_2')")
    )

    # 3. Pendant que la fixture est encore active, une connexion SEPAREE
    #    ne doit rien voir (la transaction externe n'est pas encore commitee,
    #    et ne le sera jamais - c'est tout l'interet du pattern)
    with engine.connect() as other_connection:
        visible_now = other_connection.execute(
            text("SELECT role_name FROM application_roles WHERE role_name LIKE 'TEST_ROLE_TMP%'")
        ).fetchall()
    assert visible_now == []


def test_no_residual_data_after_fixture_teardown():
    """
    Verifie qu'apres la fin d'un test utilisant db_session (celui
    ci-dessus), aucune trace ne subsiste. Depend de l'ordre d'execution
    (doit tourner apres test_rollback_survives_internal_commit) - pytest
    execute les tests d'un meme fichier dans l'ordre de definition par
    defaut, ce qui suffit ici.
    """
    with engine.connect() as verify_connection:
        residual = verify_connection.execute(
            text("SELECT role_name FROM application_roles WHERE role_name LIKE 'TEST_ROLE_TMP%'")
        ).fetchall()
    assert residual == [], f"Fuite de donnees detectee : {residual}"
```

- [ ] **Step 2: Lancer le méta-test**

```bash
pytest tests/test_conftest_db_session.py -v
```

Attendu : 2 tests `PASS`. (Il n'y a pas de phase "rouge" ici — ce test valide une infrastructure déjà vérifiée manuellement pendant le cadrage ; le faire passer du premier coup confirme que la fixture committée reproduit fidèlement ce qui a été vérifié à la main.)

- [ ] **Step 3: Si le test échoue**

Ne pas continuer vers les tâches suivantes. Un échec ici signifie que la fixture ne protège pas réellement `AH2` contre une pollution par les futurs tests métier (2d-1 à 2d-4) — s'arrêter et re-vérifier le pattern manuellement (comme pendant le cadrage) avant de retenter.

- [ ] **Step 4: Commit**

```bash
git add tests/test_conftest_db_session.py
git commit -m "test: meta-test validant le rollback de la fixture db_session (chantier 2d-0)

Verifie, via pytest cette fois (pas seulement manuellement comme
pendant le cadrage), qu'un commit() interne simule suivi d'une
insertion supplementaire est integralement annule par le rollback
externe de la fixture, sans fuite visible depuis une connexion
separee.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Test de démonstration — surcharge `get_db()` bout-en-bout via `TestClient`

**Files:**
- Create: `tests/test_conftest_override_get_db.py`

**Interfaces:**
- Consumes: fixture `db_session`, `override_get_db()` (Task 1)
- Produces: rien — sert de modèle pour 2d-1 à 2d-4

- [ ] **Step 1: Écrire le test**

```python
# tests/test_conftest_override_get_db.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app import database
from tests.conftest import override_get_db


def test_health_endpoint_uses_the_transactional_test_session(db_session):
    """
    Demontre que override_get_db() branche correctement la session de
    test dans une vraie route FastAPI appelee via TestClient. /health
    est la route la plus simple du projet (aucune auth, aucune logique
    metier) - ideale pour valider le mecanisme de surcharge isolement,
    avant de l'utiliser pour de vrais tests metier (2d-1 a 2d-4).
    """
    override_get_db(app, database, db_session)
    try:
        client = TestClient(app)
        resp = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["database"] == "connected"
```

- [ ] **Step 2: Lancer le test**

```bash
pytest tests/test_conftest_override_get_db.py -v
```

Attendu : `PASS`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_conftest_override_get_db.py
git commit -m "test: demonstration de override_get_db() bout-en-bout via TestClient (chantier 2d-0)

Valide que la substitution de get_db() fonctionne sur une vraie route
FastAPI (health_endpoint, qui reutilise directement database.get_db).
Sert de modele pour les tests metier des sous-chantiers 2d-1 a 2d-4.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Vérification finale

**Files:** aucun (vérification uniquement)

- [ ] **Step 1: Suite de tests complète**

```bash
pytest tests/ -v
```

Attendu : tous les tests passent, y compris les 4 nouveaux de ce chantier (Task 2 : 2, Task 3 : 1, plus le fichier `conftest.py` lui-même qui n'est pas un test). Les 4 échecs pré-existants et non liés restent identiques.

- [ ] **Step 2: Confirmer l'absence de donnée résiduelle sur l'ensemble de la suite**

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "SELECT count(*) FROM application_roles WHERE role_name LIKE 'TEST_ROLE_TMP%';"
```

Attendu : `0`.

- [ ] **Step 3: Mettre à jour `docs/superpowers/SUIVI-AVANCEMENT.md`**

Ajouter une ligne pour le chantier 2d-0 dans le tableau de la feuille de route, marquer comme terminé, ajouter le résumé dans la section détail.

- [ ] **Step 4: Récapitulatif**

Confirmer un par un :
- [ ] `db_session` annule bien un `commit()` interne simulé
- [ ] Aucune fuite de donnée détectable depuis une connexion séparée
- [ ] `override_get_db()` fonctionne sur une vraie route via `TestClient`
- [ ] Prêt pour 2d-1 (auth + RBAC)
