from sqlalchemy.exc import IntegrityError

from api_backend.backend_app.exceptions import translate_integrity_error


def _ie(msg):
    return IntegrityError("INSERT", {}, Exception(msg))


def test_duplicate_username_gets_a_specific_message():
    exc = translate_integrity_error(_ie('duplicate key value violates unique constraint "users_username_key"'))
    assert exc.status_code == 409 and "nom d'utilisateur" in exc.detail


def test_duplicate_email_gets_a_specific_message():
    exc = translate_integrity_error(_ie('duplicate key value violates unique constraint "users_email_key"'))
    assert exc.status_code == 409 and "e-mail" in exc.detail
