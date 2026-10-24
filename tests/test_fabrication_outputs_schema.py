# tests/test_fabrication_outputs_schema.py
"""Sorties declarees, tache 1 : table fab_batch_outputs, ses CHECK et sa cle etrangere."""
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from models import FabBatch, FabBatchOutput, Pharmacy
from tests.conftest import create_test_user


def _batch(db, user, number="FAB-OUT-0001"):
    p = Pharmacy(drug_name="t_fab_out_prod", quantity=0, threshold=0,
                 medication_type="pharmaceutique", forme="Autre")
    db.add(p)
    db.flush()
    b = FabBatch(batch_number=number, product_id=p.medication_id,
                 production_date=date.today(), created_by=user.user_id)
    db.add(b)
    db.flush()
    return b


@pytest.fixture
def ctx(db_session):
    user = create_test_user(db_session, "t_fab_out", "admin")
    return db_session, user, _batch(db_session, user)


def _refused(db, **kw):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(FabBatchOutput(**kw))
            db.flush()


def test_valid_output_and_default_status(ctx):
    db, user, batch = ctx
    out = FabBatchOutput(batch_id=batch.id, reason="echantillon", quantity=3,
                         declared_by=user.user_id)
    db.add(out)
    db.flush()
    db.refresh(out)
    assert out.status == "active"
    assert out.declared_at is not None
    assert out.note is None and out.cancelled_by is None
    other = FabBatchOutput(batch_id=batch.id, reason="autre", quantity=1, note="casse",
                           declared_by=user.user_id)
    db.add(other)
    db.flush()


@pytest.mark.parametrize("qty", [0, -1])
def test_quantity_must_be_positive(ctx, qty):
    db, user, batch = ctx
    _refused(db, batch_id=batch.id, reason="echantillon", quantity=qty, declared_by=user.user_id)


def test_unknown_reason_refused(ctx):
    db, user, batch = ctx
    _refused(db, batch_id=batch.id, reason="vol", quantity=1, declared_by=user.user_id)


@pytest.mark.parametrize("note", [None, "", "   "])
def test_autre_requires_note(ctx, note):
    db, user, batch = ctx
    _refused(db, batch_id=batch.id, reason="autre", quantity=1, note=note,
             declared_by=user.user_id)


def test_unknown_status_refused(ctx):
    db, user, batch = ctx
    _refused(db, batch_id=batch.id, reason="echantillon", quantity=1, status="supprimee",
             declared_by=user.user_id)


def test_cancelled_requires_reason_and_canceller(ctx):
    db, user, batch = ctx
    base = dict(batch_id=batch.id, reason="echantillon", quantity=1, status="annulee",
                declared_by=user.user_id)
    _refused(db, **base)
    _refused(db, cancelled_by=user.user_id, **base)
    _refused(db, cancelled_by=user.user_id, cancel_reason="   ", **base)
    _refused(db, cancel_reason="erreur de saisie", **base)
    ok = FabBatchOutput(cancelled_by=user.user_id, cancel_reason="erreur de saisie", **base)
    db.add(ok)
    db.flush()


def test_unknown_batch_refused(ctx):
    db, user, batch = ctx
    _refused(db, batch_id=batch.id + 999999, reason="echantillon", quantity=1,
             declared_by=user.user_id)
