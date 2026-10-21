# tests/test_stock_actor_names.py
"""Noms complets des auteurs/controleurs dans les dictionnaires du stock."""
from datetime import date

import pytest
from sqlalchemy import event

from controller.stock_controller import StockController
from models.pharmacy import Pharmacy
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from repositories.stock_repo import StockRepository
from tests.conftest import create_test_user


def _ctrl(db, user):
    return StockController(StockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _product(db, name="TEST_NAMES_PROD"):
    p = Pharmacy(drug_name=name, quantity=50, threshold=5, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal")
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def users(db_session):
    return {
        "sec": create_test_user(db_session, "t_nm_sec", "secretaire"),
        "admin": create_test_user(db_session, "t_nm_admin", "admin"),
        "ctrl": create_test_user(db_session, "t_nm_ctrl", "StockController"),
        "ctrl2": create_test_user(db_session, "t_nm_ctrl2", "StockController"),
    }


def test_lot_receipt_incident_names(db_session, users):
    p = _product(db_session)
    sec, ctrl = users["sec"], users["ctrl"]
    lot = _ctrl(db_session, sec).create_lot(
        {"product_id": p.medication_id, "quantity_produced": 10, "production_date": date.today()})
    assert lot["created_by_name"] == sec.full_name
    rec = _ctrl(db_session, sec).create_receipt({
        "origin": "fournisseur", "supplier": "X", "received_date": date.today(),
        "lines": [{"product_id": p.medication_id, "qty_good": 3}]})
    assert rec["created_by_name"] == sec.full_name and rec["controlled_by_name"] is None
    done = _ctrl(db_session, ctrl).validate_receipt(rec["id"])
    assert done["created_by_name"] == sec.full_name and done["controlled_by_name"] == ctrl.full_name
    inc = _ctrl(db_session, sec).create_incident(
        {"product_id": p.medication_id, "kind": "perdu", "quantity": 1, "reason": "casse",
         "incident_date": date.today()})
    assert inc["created_by_name"] == sec.full_name and inc["controlled_by_name"] is None
    inc = _ctrl(db_session, ctrl).validate_incident(inc["id"])
    assert inc["controlled_by_name"] == ctrl.full_name
    got = _ctrl(db_session, ctrl).get_receipt(rec["id"])
    assert got["created_by_name"] == sec.full_name and got["controlled_by_name"] == ctrl.full_name


def test_adjustment_names(db_session, users):
    p = _product(db_session)
    req = _ctrl(db_session, users["sec"]).create_adjustment_request(
        {"product_id": p.medication_id, "kind": "reapprovisionnement", "quantity": 5, "reason": "livraison"})
    assert req["requested_by_name"] == users["sec"].full_name and req["decided_by_name"] is None
    out = _ctrl(db_session, users["admin"]).approve_adjustment(req["id"])
    assert out["requested_by_name"] == users["sec"].full_name
    assert out["decided_by_name"] == users["admin"].full_name
    lst = _ctrl(db_session, users["admin"]).list_adjustment_requests()
    assert lst[0]["decided_by_name"] == users["admin"].full_name


def test_unknown_user_gives_none(db_session, users):
    repo = StockRepository(db_session)
    names = repo.user_names([users["sec"].user_id, None, 99999999])
    assert names == {users["sec"].user_id: users["sec"].full_name}
    assert repo.user_names([]) == {}
    assert repo.user_names([None]) == {}


def test_list_uses_single_names_query(db_session, users):
    p = _product(db_session)
    authors = [create_test_user(db_session, f"t_nm_a{i}", "secretaire") for i in range(5)]
    for a in authors:
        _ctrl(db_session, a).create_incident(
            {"product_id": p.medication_id, "kind": "perdu", "quantity": 1, "reason": "r",
             "incident_date": date.today()})
    stmts = []

    def spy(conn, cursor, statement, *a):
        if "full_name" in statement and "FROM users" in statement:
            stmts.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", spy)
    try:
        out = _ctrl(db_session, users["ctrl"]).list_incidents()
    finally:
        event.remove(engine, "before_cursor_execute", spy)
    mine = [i for i in out if i["created_by"] in {a.user_id for a in authors}]
    assert len(mine) == 5
    assert {i["created_by_name"] for i in mine} == {a.full_name for a in authors}
    assert len(stmts) <= 1
