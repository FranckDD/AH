# tests/test_notifications.py (début du fichier, sera complété en Task 3)
def test_models_import_cleanly():
    from models.notification import Notification
    from models.discount_request import DiscountRequest
    assert Notification.__tablename__ == "notifications"
    assert DiscountRequest.__tablename__ == "discount_requests"


from repositories.notification_repo import NotificationRepository
from controller.notification_controller import NotificationController


from api_backend.backend_app.routes.auth import auth_endpoints
from conftest import create_test_user, auth_headers


def test_create_and_list_unread(db_session):
    repo = NotificationRepository(db_session)
    user = create_test_user(db_session, "notif_recipient1", "secretaire")
    repo.create(recipient_user_id=user.user_id, type="discount_request", payload={"amount": 5000})
    db_session.commit()
    unread = repo.list_unread(user.user_id)
    assert len(unread) == 1
    assert unread[0].type == "discount_request"


def test_mark_read_scoped_to_recipient(db_session):
    repo = NotificationRepository(db_session)
    owner = create_test_user(db_session, "notif_owner", "secretaire")
    other = create_test_user(db_session, "notif_other", "secretaire")
    notif = repo.create(recipient_user_id=owner.user_id, type="discount_request")
    db_session.commit()
    # Un autre destinataire ne peut pas la marquer lue
    result = repo.mark_read(notif.id, recipient_user_id=other.user_id)
    assert result is None
    # Le bon destinataire peut
    result = repo.mark_read(notif.id, recipient_user_id=owner.user_id)
    assert result is not None
    assert result.status == "read"


# Task 4: Endpoint integration tests
from api_backend.backend_app.routes.notifications import notification_endpoints


def test_list_notifications_endpoint_scoped_to_current_user(api_client, db_session):
    """Test GET /notifications?status=unread with current user scope"""
    # auth_endpoints doit être inclus pour que POST /auth/login (dans
    # auth_headers) voie l'utilisateur cree dans la meme transaction de
    # test - sinon le login passe par la connexion reelle SessionLocal,
    # separee de db_session, et echoue (meme lecon deja rencontree et
    # documentee au chantier labo/Task 8 de ce meme plan).
    client = api_client(auth_endpoints, notification_endpoints)

    # Create test user
    user = create_test_user(db_session, "test_secretaire", "secretaire")

    # Create a notification for this user
    repo = NotificationRepository(db_session)
    repo.create(recipient_user_id=user.user_id, type="discount_request", payload={"amount": 5000})
    db_session.commit()

    # Get auth headers for this user
    headers = auth_headers(client, "test_secretaire", "TestPass123!")

    # Call endpoint
    r = client.get("/notifications?status=unread", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 1
    assert r.json()[0]["type"] == "discount_request"


def test_mark_notification_read_endpoint(api_client, db_session):
    """Test POST /notifications/{id}/read endpoint"""
    client = api_client(auth_endpoints, notification_endpoints)

    # Create test user
    user = create_test_user(db_session, "test_secretaire_2", "secretaire")

    # Create a notification for this user
    repo = NotificationRepository(db_session)
    notif = repo.create(recipient_user_id=user.user_id, type="discount_request", payload={"amount": 5000})
    db_session.commit()

    notification_id = notif.id

    # Get auth headers for this user
    headers = auth_headers(client, "test_secretaire_2", "TestPass123!")

    # Call endpoint to mark as read
    r = client.post(f"/notifications/{notification_id}/read", headers=headers)
    assert r.status_code == 200
    assert "detail" in r.json()

    # Verify it's marked as read
    unread = repo.list_unread(user.user_id)
    assert len(unread) == 0


def test_notification_endpoint_requires_auth(api_client, db_session):
    """Test that notification endpoints require authentication"""
    client = api_client(notification_endpoints)

    # Call endpoint without auth
    r = client.get("/notifications?status=unread")
    # Pas de header Authorization du tout -> 401 (403 est reserve a un
    # jeton valide mais un role insuffisant, cf. tests/test_caisse.py
    # meme distinction deja etablie sur ce projet).
    assert r.status_code == 401
