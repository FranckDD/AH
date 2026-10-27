# tests/test_toxico_transfer_schema.py
"""Schema des transferts de psychologue et drapeau 'psychologue limite'."""
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from models.toxico import ToxicoDossier, ToxicoPsychologistTransfer
from tests.conftest import create_test_user, create_test_patient


def _setup(db_session, tag):
    sec = create_test_user(db_session, f"sec_{tag}", "secretaire")
    p1 = create_test_user(db_session, f"psy1_{tag}", "Psychologist")
    p2 = create_test_user(db_session, f"psy2_{tag}", "Psychologist")
    patient_id, _ = create_test_patient(db_session, sec)
    dossier = ToxicoDossier(patient_id=patient_id, admission_date=date(2026, 1, 10),
                            substance="Alcool", psychologist_id=p1.user_id)
    db_session.add(dossier)
    db_session.flush()
    return dossier, p1, p2, sec


def _transfer(dossier, frm, to, by, reason="Changement de suivi"):
    return ToxicoPsychologistTransfer(
        dossier_id=dossier.id,
        from_psychologist_id=frm.user_id if frm else None,
        to_psychologist_id=to.user_id if to else None,
        decided_by=by.user_id, decided_at=datetime(2026, 10, 27, 10, 0), reason=reason)


def test_transfer_row_can_be_inserted(db_session):
    dossier, p1, p2, sec = _setup(db_session, "ins")
    db_session.add(_transfer(dossier, p1, p2, sec))
    db_session.flush()
    db_session.refresh(dossier)
    assert len(dossier.transfers) == 1
    assert dossier.transfers[0].to_psychologist.user_id == p2.user_id


def test_blank_reason_is_refused(db_session):
    dossier, p1, p2, sec = _setup(db_session, "blank")
    db_session.add(_transfer(dossier, p1, p2, sec, reason="   "))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_from_equal_to_is_refused(db_session):
    dossier, p1, p2, sec = _setup(db_session, "same")
    db_session.add(_transfer(dossier, p1, p1, sec))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_to_psychologist_is_required(db_session):
    dossier, p1, p2, sec = _setup(db_session, "noto")
    db_session.add(_transfer(dossier, p1, None, sec))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_new_user_defaults_to_not_limited(db_session):
    u = create_test_user(db_session, "limited_default", "Psychologist")
    db_session.refresh(u)
    assert u.sees_own_toxico_only is False


def test_schema_only_sql_mirrors_migration():
    sql = (Path(__file__).resolve().parent.parent / "ci" / "schema_only.sql").read_text(encoding="utf-8")
    assert "toxico_psychologist_transfers" in sql
    assert "sees_own_toxico_only" in sql
