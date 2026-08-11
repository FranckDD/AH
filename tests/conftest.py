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
