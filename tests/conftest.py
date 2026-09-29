# tests/conftest.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from datetime import date, time

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


def _flush_redis_cache():
    """
    Registre M1 (docs/superpowers/SUIVI-AVANCEMENT.md) : les helpers
    create_test_prescription/create_test_transaction/create_test_retrait
    ci-dessous appellent le repository directement, jamais le controller -
    donc jamais l'invalidation de cache (redis_client.delete(...)) que le
    controller effectue normalement a la creation reelle. Un test qui lit
    un compteur/total AVANT puis APRES l'un de ces helpers retombait sur
    la valeur mise en cache par la lecture "avant", des que Redis est
    reellement joignable (ne se produisait jamais avant que Redis ne
    tourne enfin dans cette session). Best-effort : un Redis injoignable
    ne doit jamais faire echouer un test qui n'a rien a voir avec le
    cache (meme motif defensif que le reste du code applicatif, ex.
    patient_controller.get_global_counts).
    """
    try:
        from controller.patient_controller import redis_client
        redis_client.flushdb()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def flush_redis_cache_between_tests():
    """
    Meme motif que reset_rate_limiter ci-dessus : isole aussi le cache
    Redis d'un test au suivant (un test qui echoue/leve avant d'appeler
    un des helpers ci-dessus pourrait sinon laisser une valeur en cache
    lue par le test suivant).
    """
    _flush_redis_cache()
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
    _flush_redis_cache()
    return data


def create_test_appointment(session, current_user, patient_id, **overrides):
    """
    Cree un RDV ephemere en appelant directement AppointmentRepository.create()
    (ORM simple, pas de procedure stockee), dans la transaction de test.
    Meme motif que create_test_transaction : le repo fait un commit()
    interne, sans risque, la fixture db_session relance la SAVEPOINT.

    patient_id est un entier simple (create_test_patient renvoie un tuple
    (patient_id, code_patient) - deballer avant d'appeler ce helper, ex :
    patient_id, _ = create_test_patient(db_session, medecin)).
    """
    from repositories.appointment_repo import AppointmentRepository

    data = {
        "patient_id": patient_id,
        "doctor_id": getattr(current_user, "user_id", None),
        "appointment_date": date.today(),
        "appointment_time": time(9, 0),
        "reason": "Controle de routine",
        "status": "pending",
        **overrides,
    }
    repo = AppointmentRepository(session)
    return repo.create(data)


def create_test_medical_record(session, current_user, patient_id, **overrides):
    """
    Cree un dossier medical ephemere via MedicalRecordController.create_record()
    plutot que MedicalRecordRepository.create() directement : le controller
    pose created_by/created_by_name depuis current_user (comportement
    corrige le 2026-09-28, voir SUIVI-AVANCEMENT.md), reproduisant
    fidelement le chemin de creation reel de l'application.

    patient_id est un entier simple (voir create_test_appointment ci-dessus
    pour la note sur create_test_patient).

    NOTE (correction appliquee) : le brief d'origine ne fournissait que
    patient_id/motif_code/diagnosis. MedicalRecordRepository.create()
    appelle CALL public.create_medical_record(...) avec une liste fixe
    de parametres nommes (marital_status, bp, temperature, weight,
    height, medical_history, allergies, symptoms, treatment, severity,
    notes, en plus de diagnosis/motif_code) - seuls created_by/
    created_by_name/last_updated_by/last_updated_by_name/appointment_id/
    uuid ont un setdefault(None) cote repo. Sans ces cles explicitement
    presentes dans `data`, session.execute() leve
    sqlalchemy.exc.InvalidRequestError ("A value is required for bind
    parameter 'marital_status'") - verifie empiriquement en ecrivant ce
    helper. Le vrai chemin HTTP (POST /medical_records/) ne rencontre
    jamais ce probleme car MedicalRecordCreate (schemas.py) declare tous
    ces champs Optional[...] = None, donc .dict() les fournit toujours.
    """
    from controller.medical_controller import MedicalRecordController
    from repositories.medical_repo import MedicalRecordRepository

    data = {
        "patient_id": patient_id,
        "motif_code": "consultation",
        "diagnosis": "RAS",
        "marital_status": None,
        "bp": None,
        "temperature": None,
        "weight": None,
        "height": None,
        "medical_history": None,
        "allergies": None,
        "symptoms": None,
        "treatment": None,
        "severity": None,
        "notes": None,
        **overrides,
    }
    repo = MedicalRecordRepository(session)
    ctrl = MedicalRecordController(repo=repo, current_user=current_user)
    ctrl.create_record(data)


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
    result = repo.create_transaction(data, current_user)
    _flush_redis_cache()
    return result


def create_test_retrait(session, current_user, **overrides):
    """
    Cree un retrait de caisse ephemere en appelant directement
    CaisseRetraitRepository.create().
    """
    retrait_at = overrides.pop("retrait_at", None)
    data = {
        "amount": 50.0,
        "justification": "Retrait de test",
        "handled_by": current_user.user_id,
        "category": None,
        "payment_method": None,
        **overrides,
    }
    repo = CaisseRetraitRepository(session)
    retrait = repo.create(**data)
    if retrait_at is not None:
        retrait.retrait_at = retrait_at
        session.flush()
    _flush_redis_cache()
    return retrait
