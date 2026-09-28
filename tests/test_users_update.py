import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from tests.conftest import create_test_user, auth_headers

TEST_PASSWORD = "Correct123!"


def test_update_user_duplicate_email_returns_409_not_500(db_session, api_client):
    """Registre L3f (chantier 7d) : UserController.update_user attrapait
    IntegrityError dans son 'except SQLAlchemyError' generique (IntegrityError
    est une sous-classe de SQLAlchemyError), le convertissant en RuntimeError
    avant meme de sortir du controller - le bloc 'except IntegrityError' de
    cet endpoint n'a donc jamais pu s'executer. Un email deja pris par un
    autre compte renvoyait un 500 generique au lieu d'un 409 propre."""
    admin = create_test_user(db_session, "l7d_admin_dupemail", "admin", password=TEST_PASSWORD)
    admin.email = "deja.pris@example.com"
    db_session.flush()
    target = create_test_user(db_session, "l7d_target_dupemail", "secretaire", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "l7d_admin_dupemail", TEST_PASSWORD)

    resp = client.put(f"/users/{target.user_id}", json={"email": "deja.pris@example.com"}, headers=headers)

    assert resp.status_code == 409
