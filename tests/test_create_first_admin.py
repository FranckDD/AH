import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import text

from api_backend.backend_app.routes.auth import auth_endpoints
from models.application_role import ApplicationRole
from models.user import User, pwd_context
from scripts import create_first_admin as cfa
from tests.conftest import login

GOOD_PASSWORD = "Zx9-correct-horse-battery"


@pytest.fixture
def no_admin(db_session):
    """Aucun admin dans la transaction du test (la base de dev en a : annule au rollback)."""
    admin_id = db_session.query(ApplicationRole.role_id).filter_by(role_name="admin").scalar()
    other_id = db_session.query(ApplicationRole.role_id).filter_by(role_name="secretaire").scalar()
    db_session.execute(text("UPDATE users SET role_id = :o WHERE role_id = :a"),
                       {"o": other_id, "a": admin_id})
    db_session.flush()
    return db_session


class _KeepOpen:
    """Empeche main() de fermer la session transactionnelle de la fixture."""
    def __init__(self, session):
        self._s = session

    def __getattr__(self, name):
        return getattr(self._s, name)

    def close(self):
        pass


def test_creates_admin_with_admin_role_and_hashed_password(no_admin):
    uid = cfa.create_first_admin(no_admin, "first_admin_t6", GOOD_PASSWORD)
    user = no_admin.get(User, uid)
    assert user.username == "first_admin_t6"
    assert user.roles == ["admin"]
    assert user.is_active is True
    assert user.password_hash != GOOD_PASSWORD
    assert GOOD_PASSWORD not in user.password_hash
    assert pwd_context.verify(GOOD_PASSWORD, user.password_hash)


@pytest.mark.parametrize("pwd", ["", "short", "elevenchars", None])
def test_refuses_empty_or_short_password(no_admin, pwd):
    with pytest.raises(cfa.AdminCreationError):
        cfa.create_first_admin(no_admin, "first_admin_t6", pwd)
    assert no_admin.query(User).filter_by(username="first_admin_t6").count() == 0


def test_accepts_exactly_12_characters(no_admin):
    assert cfa.create_first_admin(no_admin, "first_admin_t6", "a" * 12) > 0


def test_refuses_second_run_when_an_admin_exists(no_admin):
    cfa.create_first_admin(no_admin, "first_admin_t6", GOOD_PASSWORD)
    with pytest.raises(cfa.AdminCreationError, match="existe deja"):
        cfa.create_first_admin(no_admin, "second_admin_t6", GOOD_PASSWORD)
    assert no_admin.query(User).filter_by(username="second_admin_t6").count() == 0


def test_password_never_in_output_or_logs(no_admin, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    env = {"AH2_ADMIN_USER": "first_admin_t6", "AH2_ADMIN_PASSWORD": GOOD_PASSWORD}
    rc = cfa.main(session_factory=lambda: _KeepOpen(no_admin), env=env)
    assert rc == 0
    # deuxieme passage (refus) et mot de passe trop court : rien non plus dans les sorties
    cfa.main(session_factory=lambda: _KeepOpen(no_admin), env=env)
    cfa.main(session_factory=lambda: _KeepOpen(no_admin),
             env={"AH2_ADMIN_USER": "x_t6", "AH2_ADMIN_PASSWORD": "tooshort"})
    out = capsys.readouterr()
    stored_hash = no_admin.query(User).filter_by(username="first_admin_t6").one().password_hash
    everything = out.out + out.err + caplog.text
    assert GOOD_PASSWORD not in everything
    assert "tooshort" not in everything
    assert stored_hash not in everything
    assert "$2b$" not in everything


def test_prompt_used_when_env_password_absent(no_admin, capsys):
    answers = iter([GOOD_PASSWORD, GOOD_PASSWORD])
    rc = cfa.main(session_factory=lambda: _KeepOpen(no_admin),
                  env={"AH2_ADMIN_USER": "first_admin_t6"},
                  getpass_fn=lambda prompt: next(answers), is_tty=lambda: True)
    assert rc == 0
    assert GOOD_PASSWORD not in capsys.readouterr().out


def test_prompt_mismatch_creates_nothing(no_admin):
    answers = iter([GOOD_PASSWORD, GOOD_PASSWORD + "x"])
    rc = cfa.main(session_factory=lambda: _KeepOpen(no_admin),
                  env={"AH2_ADMIN_USER": "first_admin_t6"},
                  getpass_fn=lambda prompt: next(answers), is_tty=lambda: True)
    assert rc == 1
    assert no_admin.query(User).filter_by(username="first_admin_t6").count() == 0


def test_created_admin_can_log_in_through_login_route(no_admin, api_client):
    cfa.create_first_admin(no_admin, "first_admin_t6", GOOD_PASSWORD)
    client = api_client(auth_endpoints)
    resp = login(client, "first_admin_t6", GOOD_PASSWORD)
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert login(client, "first_admin_t6", "not-the-password").status_code == 401


@pytest.mark.parametrize("pwd", ["            ", " " + GOOD_PASSWORD, GOOD_PASSWORD + " ", "\t" + GOOD_PASSWORD])
def test_refuses_whitespace_only_or_padded_password(no_admin, pwd):
    with pytest.raises(cfa.AdminCreationError):
        cfa.create_first_admin(no_admin, "first_admin_t6", pwd)
    assert no_admin.query(User).filter_by(username="first_admin_t6").count() == 0


def test_without_tty_reads_password_from_stdin_and_never_calls_getpass(no_admin, capsys):
    def boom(prompt):
        raise AssertionError("getpass interdit sans terminal")

    rc = cfa.main(session_factory=lambda: _KeepOpen(no_admin),
                  env={"AH2_ADMIN_USER": "first_admin_t6"},
                  getpass_fn=boom, is_tty=lambda: False,
                  stdin_readline=lambda: GOOD_PASSWORD + "\n")
    assert rc == 0
    out = capsys.readouterr()
    assert "stdin" in out.err
    assert GOOD_PASSWORD not in out.out + out.err
    assert pwd_context.verify(GOOD_PASSWORD, no_admin.query(User).filter_by(username="first_admin_t6").one().password_hash)


def test_docstring_has_no_inline_password_example():
    assert "AH2_ADMIN_PASSWORD=" not in (cfa.__doc__ or "")
