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
