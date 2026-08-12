# tests/conftest.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from datetime import date

from api_backend.backend_app.database import engine
from api_backend.backend_app.main import app
from models.user import User, pwd_context
from models.application_role import ApplicationRole
from api_backend.backend_app.rate_limit import limiter
from repositories.patient_repo import PatientRepository
from repositories.prescription_repo import PrescriptionRepository
from repositories.caisse_repo import CaisseRepository
from repositories.caisse_retrait_repo import CaisseRetraitRepository


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
    assert engine.url.database == "AH2" and engine.url.host in ("localhost", "127.0.0.1"), (
        f"Tests d'integration refuses contre {engine.url.render_as_string(hide_password=True)} "
        "- verifiez DATABASE_URL dans .env"
    )
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


@pytest.fixture
def api_client(db_session):
    """
    Fabrique un TestClient avec get_db() surcharge sur les modules
    donnes, nettoyage automatique des overrides en fin de test (plus
    besoin d'un try/finally dans chaque test).

    Usage : client = api_client(auth_endpoints)
            client = api_client(auth_endpoints, users_endpoint)
    """
    def _make(*modules):
        for module in modules:
            override_get_db(app, module, db_session)
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


def login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


def auth_headers(client, username, password):
    token = login(client, username, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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


def create_test_transaction(session, current_user, **overrides):
    """
    Cree une transaction caisse ephemere en appelant directement
    CaisseRepository.create_transaction() (ORM reel, pas de procedure
    stockee pour ce module). Contrairement a create_test_prescription,
    retourne directement l'objet Caisse complet (avec transaction_id
    reel) - le repository ne renvoie pas juste un booleen.

    item_type="Service" par defaut : ne correspond a aucun mot-cle
    special (medicament/carnet/consultation), evite toute dependance
    a de vraies donnees Pharmacy/ConsultationSpirituel.
    """
    data = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {
                "item_type": "Service",
                "item_ref_id": 1,
                "unit_price": 100.0,
                "quantity": 1,
                "line_total": 100.0,
            }
        ],
        **overrides,
    }
    repo = CaisseRepository(session)
    return repo.create_transaction(data, current_user)


def create_test_retrait(session, current_user, **overrides):
    """
    Cree un retrait de caisse ephemere en appelant directement
    CaisseRetraitRepository.create().
    """
    data = {
        "amount": 50.0,
        "justification": "Retrait de test",
        "handled_by": current_user.user_id,
        "category": None,
        "payment_method": None,
        **overrides,
    }
    repo = CaisseRetraitRepository(session)
    return repo.create(**data)
