# tests/test_fabrication_outputs.py
"""Sorties declarees d'un lot (echantillon, autre) : controleur et depot.

Les tests tournent dans la transaction de test (db_session), sauf le test de
concurrence qui utilise deux vraies sessions sur des donnees commitees, supprimees en fin de test.
"""
import threading
import time
import uuid
from datetime import date

import pytest

from api_backend.backend_app.database import SessionLocal
from controller.fabrication_controller import FabricationController
from models import AuditUserAction, FabBatch, FabBatchOutput, Pharmacy, User
from repositories.audit_repo import AuditRepository
from repositories.fabrication_repo import (
    FabricationConflictError, FabricationNotFoundError, FabricationRepository,
)
from tests.conftest import create_test_user


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _ctrl(session, user):
    return FabricationController(FabricationRepository(session), AuditRepository(session), user)


@pytest.fixture
def env(db_session):
    user = create_test_user(db_session, _rand("t_fo_pm"), "ProductionManager")
    return {"db": db_session, "user": user, "ctrl": _ctrl(db_session, user)}


def _batch(env, status="termine", qty_good=100):
    db = env["db"]
    p = Pharmacy(drug_name=_rand("prod"), quantity=0, threshold=0, medication_type="Naturel", forme="Autre")
    db.add(p)
    db.flush()
    b = FabBatch(batch_number=_rand("FO")[:30], product_id=p.medication_id, status=status,
                 production_date=date.today(), qty_good=qty_good, created_by=env["user"].user_id,
                 cancel_reason="test" if status == "annule" else None)
    db.add(b)
    db.flush()
    return b


def _audits(env, oid, action):
    return env["db"].query(AuditUserAction).filter_by(
        resource_type="FabBatchOutput", resource_id=oid, action_performed=action).all()


def test_declare_on_finished_batch_updates_derived_fields(env):
    b = _batch(env)
    out = env["ctrl"].declare_output(b.id, "echantillon", 12, None)
    assert out["reason"] == "echantillon" and out["quantity"] == 12 and out["status"] == "active"
    assert out["declared_by"] == env["user"].user_id
    d = env["ctrl"].get_batch(b.id)
    assert d["qty_outputs"] == 12
    assert d["qty_shipped"] == 88
    assert [o["id"] for o in d["outputs"]] == [out["id"]]


def test_several_outputs_accumulate_and_overflow_refused(env):
    b = _batch(env)
    env["ctrl"].declare_output(b.id, "echantillon", 30)
    env["ctrl"].declare_output(b.id, "autre", 50, "don a une association")
    d = env["ctrl"].get_batch(b.id)
    assert d["qty_outputs"] == 80 and d["qty_shipped"] == 20
    with pytest.raises(FabricationConflictError):
        env["ctrl"].declare_output(b.id, "echantillon", 21)
    env["ctrl"].declare_output(b.id, "echantillon", 20)
    assert env["ctrl"].get_batch(b.id)["qty_shipped"] == 0


def test_invalid_input_is_value_error(env):
    b = _batch(env)
    with pytest.raises(ValueError):
        env["ctrl"].declare_output(b.id, "autre", 1, "  ")
    with pytest.raises(ValueError):
        env["ctrl"].declare_output(b.id, "echantillon", 0)
    with pytest.raises(FabricationNotFoundError):
        env["ctrl"].declare_output(999999999, "echantillon", 1)


@pytest.mark.parametrize("status", ["brouillon", "en_production", "expedie", "annule"])
def test_declare_refused_outside_termine(env, status):
    b = _batch(env, status=status)
    with pytest.raises(FabricationConflictError):
        env["ctrl"].declare_output(b.id, "echantillon", 1)


def test_cancel_output_with_reason(env):
    b = _batch(env)
    o = env["ctrl"].declare_output(b.id, "echantillon", 12)
    c = env["ctrl"].cancel_output(b.id, o["id"], "  erreur de saisie ")
    assert c["status"] == "annulee" and c["cancel_reason"] == "erreur de saisie"
    assert c["cancelled_by"] == env["user"].user_id and c["cancelled_at"] is not None
    d = env["ctrl"].get_batch(b.id)
    assert d["qty_outputs"] == 0 and d["qty_shipped"] == 100
    assert [x["status"] for x in d["outputs"]] == ["annulee"]


def test_cancel_requires_reason_and_once(env):
    b = _batch(env)
    o = env["ctrl"].declare_output(b.id, "echantillon", 12)
    for r in (None, "", "   "):
        with pytest.raises(ValueError):
            env["ctrl"].cancel_output(b.id, o["id"], r)
    env["ctrl"].cancel_output(b.id, o["id"], "erreur")
    with pytest.raises(FabricationConflictError):
        env["ctrl"].cancel_output(b.id, o["id"], "encore")


def test_cancel_wrong_batch_or_unknown_is_404(env):
    b1, b2 = _batch(env), _batch(env)
    o = env["ctrl"].declare_output(b1.id, "echantillon", 1)
    with pytest.raises(FabricationNotFoundError):
        env["ctrl"].cancel_output(b2.id, o["id"], "x")
    with pytest.raises(FabricationNotFoundError):
        env["ctrl"].cancel_output(b1.id, 999999999, "x")


def test_cancel_after_shipping_refused(env):
    b = _batch(env)
    o = env["ctrl"].declare_output(b.id, "echantillon", 3)
    b.status = "expedie"
    env["db"].flush()
    with pytest.raises(FabricationConflictError):
        env["ctrl"].cancel_output(b.id, o["id"], "trop tard")


def test_audit_create_then_cancel_with_author(env):
    b = _batch(env)
    o = env["ctrl"].declare_output(b.id, "echantillon", 4)
    env["ctrl"].cancel_output(b.id, o["id"], "erreur")
    created, cancelled = _audits(env, o["id"], "CREATE"), _audits(env, o["id"], "CANCEL")
    assert len(created) == 1 and len(cancelled) == 1
    assert created[0].user_id == env["user"].user_id
    assert cancelled[0].user_id == env["user"].user_id
    assert cancelled[0].new_values["status"] == "annulee"
    assert cancelled[0].old_values["status"] == "active"


def test_list_outputs_newest_first_and_filters(env):
    b = _batch(env)
    o1 = env["ctrl"].declare_output(b.id, "echantillon", 1)
    o2 = env["ctrl"].declare_output(b.id, "autre", 2, "note")
    rows = env["ctrl"].list_outputs()
    mine = [r for r in rows if r["batch_id"] == b.id]
    assert [r["id"] for r in mine] == [o2["id"], o1["id"]]
    assert mine[0]["batch_number"] == b.batch_number
    assert mine[0]["product_name"] is not None
    only = [r for r in env["ctrl"].list_outputs(reason="autre") if r["batch_id"] == b.id]
    assert [r["id"] for r in only] == [o2["id"]]
    today = date.today()
    assert any(r["id"] == o1["id"] for r in env["ctrl"].list_outputs(date_from=today, date_to=today))
    with pytest.raises(ValueError):
        env["ctrl"].list_outputs(reason="vol")


def test_list_batches_rows_carry_totals(env):
    b = _batch(env)
    env["ctrl"].declare_output(b.id, "echantillon", 7)
    row = next(r for r in env["ctrl"].list_batches() if r["id"] == b.id)
    assert row["qty_outputs"] == 7 and row["qty_shipped"] == 93


# ---------------- concurrence reelle (deux sessions) ----------------
def test_concurrent_declarations_only_one_succeeds():
    """A et B declarent chacune plus de la moitie du reste ; B attend le verrou du lot puis echoue."""
    s0 = SessionLocal()
    sa = None
    ids = {}
    try:
        user = s0.query(User).filter(User.is_active.is_(True)).order_by(User.user_id).first()
        assert user is not None
        prod = Pharmacy(drug_name=_rand("prod"), quantity=0, threshold=0,
                        medication_type="Naturel", forme="Autre")
        s0.add(prod)
        s0.flush()
        b = FabBatch(batch_number=_rand("FC")[:30], product_id=prod.medication_id, status="termine",
                     production_date=date.today(), qty_good=100, created_by=user.user_id)
        s0.add(b)
        s0.commit()
        ids = {"prod": prod.medication_id, "b": b.id}

        sa = SessionLocal()
        ctrl_a = _ctrl(sa, sa.get(User, user.user_id))
        ctrl_a._tx = lambda fn: fn()  # garde la transaction de A ouverte (verrou tenu)
        out_a = ctrl_a.declare_output(ids["b"], "echantillon", 60)

        result = {}

        def run_b():
            sb = SessionLocal()
            try:
                try:
                    result["out"] = _ctrl(sb, sb.get(User, user.user_id)).declare_output(
                        ids["b"], "echantillon", 60)
                except Exception as e:  # noqa: BLE001
                    result["err"] = e
            finally:
                sb.close()

        t = threading.Thread(target=run_b)
        t.start()
        time.sleep(1.0)
        blocked = t.is_alive()
        sa.commit()
        t.join(timeout=15)
        assert blocked, ("B doit attendre le verrou du lot", result)
        assert not t.is_alive()
        assert "out" not in result, result
        assert isinstance(result["err"], FabricationConflictError), result

        s0.expire_all()
        rows = s0.query(FabBatchOutput).filter(FabBatchOutput.batch_id == ids["b"]).all()
        assert [(r.id, r.quantity) for r in rows] == [(out_a["id"], 60)]
    finally:
        if sa is not None:
            sa.rollback()
            sa.close()
        s0.rollback()
        if ids:
            oids = [o for (o,) in s0.query(FabBatchOutput.id).filter(FabBatchOutput.batch_id == ids["b"])]
            if oids:
                s0.query(AuditUserAction).filter(AuditUserAction.resource_type == "FabBatchOutput",
                                                 AuditUserAction.resource_id.in_(oids)).delete(
                    synchronize_session=False)
            s0.query(FabBatchOutput).filter(FabBatchOutput.batch_id == ids["b"]).delete()
            s0.query(FabBatch).filter(FabBatch.id == ids["b"]).delete()
            s0.query(Pharmacy).filter(Pharmacy.medication_id == ids["prod"]).delete()
            s0.commit()
        s0.close()


# ---- revue finale : annulation d'un lot avec sorties, filtre de dates en heure locale ----
def test_cancel_batch_refused_with_active_output(env):
    b = _batch(env)
    env["ctrl"].declare_output(b.id, "echantillon", 5, None)
    with pytest.raises(FabricationConflictError, match="Annulez d'abord les sorties declarees"):
        env["ctrl"].cancel_batch(b.id, "erreur de lot")


def test_cancel_batch_accepted_after_cancelling_output(env):
    b = _batch(env)
    o = env["ctrl"].declare_output(b.id, "echantillon", 5, None)
    env["ctrl"].cancel_output(b.id, o["id"], "erreur")
    assert env["ctrl"].cancel_batch(b.id, "erreur de lot")["status"] == "annule"


def test_cancel_batch_accepted_with_only_cancelled_outputs(env):
    b = _batch(env)
    for _ in range(2):
        o = env["ctrl"].declare_output(b.id, "autre", 1, "n")
        env["ctrl"].cancel_output(b.id, o["id"], "erreur")
    assert env["ctrl"].cancel_batch(b.id, "x")["status"] == "annule"


def test_list_outputs_date_filter_uses_douala_local_day(env):
    from datetime import datetime
    b = _batch(env)
    o = env["ctrl"].declare_output(b.id, "echantillon", 3, None)
    row = env["db"].get(FabBatchOutput, o["id"])
    row.declared_at = datetime(2026, 3, 9, 23, 30)  # UTC = 2026-03-10 00:30 a Douala
    env["db"].flush()
    local_day = date(2026, 3, 10)
    ids = {r["id"] for r in env["ctrl"].list_outputs(date_from=local_day, date_to=local_day)}
    assert o["id"] in ids
    prev = date(2026, 3, 9)
    assert o["id"] not in {r["id"] for r in env["ctrl"].list_outputs(date_from=prev, date_to=prev)}
