# tests/conftest.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from api_backend.backend_app.database import engine
from models.user import User, pwd_context
from models.application_role import ApplicationRole
from api_backend.backend_app.rate_limit import limiter


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


def create_test_user(session, username, role_name, password="TestPass123!", is_active=True):
    """
    Cree un utilisateur ephemere dans la transaction de test (flush, jamais
    commit) rattache a un role deja seede en base (ex: 'admin', 'secretaire').
    Reutilisable par les sous-chantiers 2d-2 a 2d-4.
    """
    role = session.query(ApplicationRole).filter_by(role_name=role_name).one()
    user = User(
        username=username,
        password_hash=pwd_context.hash(password),
        full_name=f"Test {username}",
        role_id=role.role_id,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Evite que les tests successifs de /auth/login ne se bloquent entre eux :
    TestClient envoie toutes ses requetes avec la meme adresse cliente
    ('testclient'), slowapi la traiterait sinon comme un seul appelant
    cumulant les appels de tous les tests (limite : 5/minute, SEC-05).
    """
    limiter.reset()
    yield
