# tests/test_nurse_shift_repo.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
import pytest
from sqlalchemy.exc import IntegrityError
from repositories.nurse_shift_repo import NurseShiftRepository
from tests.conftest import create_test_user


def test_assign_creates_shift(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin1", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse1", "nurse")
    repo = NurseShiftRepository(db_session)

    shift = repo.assign(date(2026, 10, 3), "MATIN", nurse.user_id, medecin.user_id)

    assert shift.id is not None
    assert shift.shift_type == "MATIN"
    assert shift.nurse_id == nurse.user_id
    assert shift.created_by == medecin.user_id


def test_assign_allows_multiple_nurses_same_slot(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin2", "medecin")
    nurse1 = create_test_user(db_session, "nsh_repo_nurse2a", "nurse")
    nurse2 = create_test_user(db_session, "nsh_repo_nurse2b", "nurse")
    repo = NurseShiftRepository(db_session)

    repo.assign(date(2026, 10, 4), "NUIT", nurse1.user_id, medecin.user_id)
    repo.assign(date(2026, 10, 4), "NUIT", nurse2.user_id, medecin.user_id)

    shifts = repo.list_for_range(date(2026, 10, 4), date(2026, 10, 4))
    assert len(shifts) == 2


def test_assign_refuses_exact_duplicate(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin3", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse3", "nurse")
    repo = NurseShiftRepository(db_session)
    repo.assign(date(2026, 10, 5), "APRES_MIDI", nurse.user_id, medecin.user_id)

    with pytest.raises(ValueError, match="déjà"):
        repo.assign(date(2026, 10, 5), "APRES_MIDI", nurse.user_id, medecin.user_id)


def test_assign_converts_race_integrity_error_to_value_error(db_session, monkeypatch):
    """
    Reproduit le cas de course : deux appels concurrents passent tous les
    deux la pre-verification SELECT, et le "perdant" ne decouvre le doublon
    qu'au moment du commit(), via la contrainte unique reelle
    ux_nurse_shifts_no_duplicate (IntegrityError SQLAlchemy brute).

    Une vraie course a deux connexions/threads n'est pas reproductible de
    facon fiable dans cette suite : la fixture db_session isole chaque test
    dans une SAVEPOINT sur une connexion unique (voir tests/conftest.py),
    donc une deuxieme session reelle sur une deuxieme connexion ne verrait
    ni l'utilisateur de test ni le nurse crees (jamais commit pour de vrai),
    et forcer un vrai commit concurrent polluerait durablement la base.

    A la place, ce test force le commit() a lever l'IntegrityError reelle
    que Postgres leverait dans ce scenario, pour verifier que le bloc
    try/except de assign() la convertit bien en ValueError (jamais une
    exception SQLAlchemy brute qui ne fait pas partie du contrat du repo).
    """
    medecin = create_test_user(db_session, "nsh_repo_medecin9", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse9", "nurse")
    repo = NurseShiftRepository(db_session)

    def failing_commit():
        raise IntegrityError(
            "INSERT INTO nurse_shifts (...) VALUES (...)",
            {},
            Exception(
                'duplicate key value violates unique constraint '
                '"ux_nurse_shifts_no_duplicate"'
            ),
        )

    monkeypatch.setattr(db_session, "commit", failing_commit)

    with pytest.raises(ValueError, match="déjà") as excinfo:
        repo.assign(date(2026, 10, 10), "MATIN", nurse.user_id, medecin.user_id)

    assert not isinstance(excinfo.value, IntegrityError)


def test_assign_refuses_invalid_shift_type(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin4", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse4", "nurse")
    repo = NurseShiftRepository(db_session)

    with pytest.raises(ValueError, match="invalide"):
        repo.assign(date(2026, 10, 6), "SOIREE", nurse.user_id, medecin.user_id)


def test_assign_refuses_unknown_nurse(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin5", "medecin")
    repo = NurseShiftRepository(db_session)

    with pytest.raises(ValueError, match="introuvable"):
        repo.assign(date(2026, 10, 7), "MATIN", 999999999, medecin.user_id)


def test_assign_refuses_non_nurse_user(db_session):
    """Un medecin (ou tout autre role) ne peut pas etre affecte comme
    infirmier a un creneau, meme si son user_id est valide."""
    medecin = create_test_user(db_session, "nsh_repo_medecin6", "medecin")
    other_medecin = create_test_user(db_session, "nsh_repo_medecin6b", "medecin")
    repo = NurseShiftRepository(db_session)

    with pytest.raises(ValueError, match="introuvable"):
        repo.assign(date(2026, 10, 8), "MATIN", other_medecin.user_id, medecin.user_id)


def test_remove_deletes_shift(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin7", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse7", "nurse")
    repo = NurseShiftRepository(db_session)
    shift = repo.assign(date(2026, 10, 9), "NUIT", nurse.user_id, medecin.user_id)

    repo.remove(shift.id)

    assert repo.list_for_range(date(2026, 10, 9), date(2026, 10, 9)) == []


def test_remove_refuses_unknown_id(db_session):
    repo = NurseShiftRepository(db_session)
    with pytest.raises(ValueError, match="Aucune affectation"):
        repo.remove(999999999)


def test_list_for_range_filters_by_date(db_session):
    medecin = create_test_user(db_session, "nsh_repo_medecin8", "medecin")
    nurse = create_test_user(db_session, "nsh_repo_nurse8", "nurse")
    repo = NurseShiftRepository(db_session)
    repo.assign(date(2026, 11, 1), "MATIN", nurse.user_id, medecin.user_id)
    repo.assign(date(2026, 12, 1), "MATIN", nurse.user_id, medecin.user_id)

    november_only = repo.list_for_range(date(2026, 11, 1), date(2026, 11, 30))
    assert len(november_only) == 1
    assert november_only[0].shift_date == date(2026, 11, 1)
