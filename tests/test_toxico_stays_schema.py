# tests/test_toxico_stays_schema.py
"""Schema des sejours toxico (migration 022) et remplissage de l'existant."""
from datetime import date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models.toxico import (
    DISCHARGE_REASONS, ToxicoDossier, ToxicoStay, ToxicoPhaseHistory, ToxicoEvaluation,
)
from tests.conftest import create_test_user, create_test_patient
from utils.toxico_stays_backfill import BACKFILL_STATEMENTS


@pytest.fixture
def ctx(db_session):
    user = create_test_user(db_session, "toxico_stays_schema_user", "admin")
    return db_session, user


def _patient_id(s, user):
    return create_test_patient(s, user)[0]


def _dossier(s, user, **kw):
    base = dict(patient_id=_patient_id(s, user), admission_date=date(2026, 1, 10),
                substance="Alcool", psychologist_id=user.user_id)
    base.update(kw)
    d = ToxicoDossier(**base)
    s.add(d)
    s.flush()
    return d


def _stay(d, n=1, **kw):
    base = dict(dossier_id=d.id, stay_number=n, admission_date=date(2026, 1, 10),
                substance="Alcool")
    base.update(kw)
    return ToxicoStay(**base)


def _bad(session, obj, constraint):
    with pytest.raises(IntegrityError) as exc:
        with session.begin_nested():
            session.add(obj)
            session.flush()
    assert constraint in str(exc.value), f"attendu {constraint}, obtenu: {exc.value}"


def test_constants():
    assert DISCHARGE_REASONS == ('guerison', 'abandon', 'exclusion', 'autre')


def test_valid_open_and_closed_stays(ctx):
    s, u = ctx
    d = _dossier(s, u)
    s.add(_stay(d, 1, discharge_date=date(2026, 3, 1), discharge_reason='guerison',
                discharged_by=u.user_id))
    s.flush()
    s.add(_stay(d, 2, admission_date=date(2026, 5, 1)))
    s.flush()
    s.refresh(d)
    assert [x.stay_number for x in d.stays] == [1, 2]


@pytest.mark.parametrize("reason", DISCHARGE_REASONS)
def test_each_reason_accepted(ctx, reason):
    s, u = ctx
    d = _dossier(s, u)
    s.add(_stay(d, discharge_date=date(2026, 2, 1), discharge_reason=reason))
    s.flush()


def test_unknown_reason_refused(ctx):
    s, u = ctx
    d = _dossier(s, u)
    _bad(s, _stay(d, discharge_date=date(2026, 2, 1), discharge_reason='fugue'),
         "toxico_stays_reason_check")


def test_reason_without_date_refused(ctx):
    s, u = ctx
    d = _dossier(s, u)
    _bad(s, _stay(d, discharge_reason='guerison'),
         "toxico_stays_discharge_consistency_check")


def test_date_without_reason_refused(ctx):
    s, u = ctx
    d = _dossier(s, u)
    _bad(s, _stay(d, discharge_date=date(2026, 2, 1)),
         "toxico_stays_discharge_consistency_check")


def test_stay_number_unique_per_dossier(ctx):
    s, u = ctx
    d = _dossier(s, u)
    s.add(_stay(d, 1, discharge_date=date(2026, 2, 1), discharge_reason='abandon'))
    s.flush()
    _bad(s, _stay(d, 1, discharge_date=date(2026, 3, 1), discharge_reason='abandon'),
         "uq_toxico_stays_dossier_number")


def test_stay_number_positive(ctx):
    s, u = ctx
    d = _dossier(s, u)
    _bad(s, _stay(d, 0), "toxico_stays_number_check")


def test_single_open_stay_per_dossier(ctx):
    s, u = ctx
    d = _dossier(s, u)
    s.add(_stay(d, 1))
    s.flush()
    _bad(s, _stay(d, 2), "uq_toxico_stays_one_open")


def test_two_dossiers_can_each_have_an_open_stay(ctx):
    s, u = ctx
    d1, d2 = _dossier(s, u), _dossier(s, u)
    s.add_all([_stay(d1, 1), _stay(d2, 1)])
    s.flush()


def test_delete_dossier_cascades_to_stays(ctx):
    s, u = ctx
    d = _dossier(s, u)
    s.add(_stay(d, 1))
    s.flush()
    did = d.id
    s.execute(text("DELETE FROM toxico_dossiers WHERE id = :i"), {"i": did})
    assert s.execute(text("SELECT count(*) FROM toxico_stays WHERE dossier_id = :i"),
                     {"i": did}).scalar() == 0


def test_stay_id_columns_nullable_fk(ctx):
    s, u = ctx
    d = _dossier(s, u)
    st = _stay(d, 1)
    s.add(st)
    s.flush()
    s.add(ToxicoPhaseHistory(dossier_id=d.id, phase=1, start_date=date(2026, 1, 10)))
    s.add(ToxicoPhaseHistory(dossier_id=d.id, phase=2, start_date=date(2026, 2, 10),
                             stay_id=st.id))
    s.add(ToxicoEvaluation(dossier_id=d.id, decision='MAINTAIN', observation='x',
                           phase_before=1, phase_after=1, stay_id=st.id))
    s.flush()
    with pytest.raises(IntegrityError):
        with s.begin_nested():
            s.add(ToxicoPhaseHistory(dossier_id=d.id, phase=3,
                                     start_date=date(2026, 3, 10), stay_id=999999999))
            s.flush()


def _legacy_rows(s, u):
    """Dossiers inseres a l'ancienne : sans sejour, sans stay_id."""
    active = _dossier(s, u, admission_date=date(2026, 1, 10), substance="Alcool")
    inactive = _dossier(s, u, admission_date=date(2025, 6, 1), substance="Cannabis",
                        is_active=False)
    s.execute(text("UPDATE toxico_dossiers SET updated_at = :t WHERE id = :i"),
              {"t": datetime(2025, 9, 15, 14, 30), "i": inactive.id})
    for d in (active, inactive):
        s.add(ToxicoPhaseHistory(dossier_id=d.id, phase=1, start_date=d.admission_date))
        s.add(ToxicoEvaluation(dossier_id=d.id, decision='MAINTAIN', observation='obs',
                               phase_before=1, phase_after=1))
    s.flush()
    return active, inactive


def _run_backfill(s):
    for stmt in BACKFILL_STATEMENTS:
        s.execute(text(stmt))


def _stays_of(s, dossier_id):
    return s.execute(text(
        "SELECT * FROM toxico_stays WHERE dossier_id = :i ORDER BY stay_number"),
        {"i": dossier_id}).mappings().all()


def _stay_ids(s, table, dossier_id):
    return s.execute(text(f"SELECT stay_id FROM {table} WHERE dossier_id = :i"),
                     {"i": dossier_id}).scalars().all()


def test_backfill_active_dossier(ctx):
    s, u = ctx
    active, _ = _legacy_rows(s, u)
    _run_backfill(s)
    rows = _stays_of(s, active.id)
    assert len(rows) == 1
    st = rows[0]
    assert st["stay_number"] == 1
    assert st["admission_date"] == date(2026, 1, 10)
    assert st["substance"] == "Alcool"
    assert st["psychologist_id"] == u.user_id
    assert st["discharge_date"] is None and st["discharge_reason"] is None
    assert st["discharge_note"] is None
    for table in ("toxico_phase_history", "toxico_evaluations"):
        assert _stay_ids(s, table, active.id) == [st["id"]]


def test_backfill_inactive_dossier(ctx):
    s, u = ctx
    _, inactive = _legacy_rows(s, u)
    _run_backfill(s)
    rows = _stays_of(s, inactive.id)
    assert len(rows) == 1
    st = rows[0]
    assert st["admission_date"] == date(2025, 6, 1)
    assert st["substance"] == "Cannabis"
    assert st["discharge_date"] == date(2025, 9, 15)
    assert st["discharge_reason"] == 'autre'
    assert st["discharge_note"] == 'Sortie antérieure au suivi des motifs'
    for table in ("toxico_phase_history", "toxico_evaluations"):
        assert _stay_ids(s, table, inactive.id) == [st["id"]]


def test_backfill_is_idempotent(ctx):
    s, u = ctx
    active, inactive = _legacy_rows(s, u)
    _run_backfill(s)
    before = s.execute(text("SELECT count(*) FROM toxico_stays")).scalar()
    first = [dict(r) for d in (active, inactive) for r in _stays_of(s, d.id)]
    _run_backfill(s)
    assert s.execute(text("SELECT count(*) FROM toxico_stays")).scalar() == before
    assert [dict(r) for d in (active, inactive) for r in _stays_of(s, d.id)] == first


def test_backfill_leaves_later_stays_alone(ctx):
    """Un sejour 2 existant et ses lignes rattachees ne sont pas touches."""
    s, u = ctx
    active, _ = _legacy_rows(s, u)
    _run_backfill(s)
    s1 = _stays_of(s, active.id)[0]
    s.execute(text("UPDATE toxico_stays SET discharge_date='2026-02-01', "
                   "discharge_reason='guerison' WHERE id = :i"), {"i": s1["id"]})
    s2 = _stay(active, 2, admission_date=date(2026, 4, 1))
    s.add(s2)
    s.flush()
    ph = ToxicoPhaseHistory(dossier_id=active.id, phase=1, start_date=date(2026, 4, 1),
                            stay_id=s2.id)
    s.add(ph)
    s.flush()
    _run_backfill(s)
    s.refresh(ph)
    assert ph.stay_id == s2.id
    assert len(_stays_of(s, active.id)) == 2


def test_discharge_before_admission_refused(ctx):
    s, u = ctx
    d = _dossier(s, u)
    _bad(s, _stay(d, discharge_date=date(2026, 1, 9), discharge_reason='abandon'),
         "toxico_stays_dates_check")


def test_backfill_discharge_never_before_admission(ctx):
    """updated_at anterieur a l'admission : la sortie est ramenee a l'admission."""
    s, u = ctx
    d = _dossier(s, u, admission_date=date(2025, 6, 1), is_active=False)
    s.execute(text("UPDATE toxico_dossiers SET updated_at = :t WHERE id = :i"),
              {"t": datetime(2025, 3, 1, 10, 0), "i": d.id})
    _run_backfill(s)
    st = _stays_of(s, d.id)[0]
    assert st["discharge_date"] == date(2025, 6, 1)
    assert st["discharge_reason"] == 'autre'
