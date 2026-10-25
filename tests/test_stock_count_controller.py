# tests/test_stock_count_controller.py
"""Comptage physique du stock : controleur et depot.

Les tests tournent dans la transaction de test (db_session), sauf le test de
concurrence qui utilise deux vraies sessions sur des donnees commitees, supprimees en fin de test
(triggers d'immuabilite neutralises le temps du nettoyage : session_replication_role local).
"""
import threading
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from api_backend.backend_app.database import SessionLocal
from controller.stock_count_controller import (
    StockCountConflictError, StockCountController, StockCountNotFoundError, get_stock_count_controller,
)
from models.audit import AuditUserAction
from models.notification import Notification
from models.pharmacy import Pharmacy
from models.stock_count import StockCount, StockCountLine, StockCountSettings
from models.stock_movement import StockMovement
from models.stock_reception import StockAdjustmentRequest
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from repositories.stock_count_repo import StockCountRepository
from tests.conftest import create_test_user


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _ctrl(db, user, clock=None):
    return StockCountController(StockCountRepository(db), AuditRepository(db), NotificationRepository(db),
                                user, clock=clock)


def _product(db, qty=10, name=None):
    p = Pharmacy(drug_name=name or _rand("TSC"), quantity=qty, threshold=0, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal")
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def users(db_session):
    return {k: create_test_user(db_session, _rand(f"t_sc_{k}"), role) for k, role in (
        ("ctrl", "StockController"), ("ctrl2", "StockController"), ("admin", "admin"),
        ("admin2", "admin"), ("promo", "promoteur"), ("sec", "secretaire"))}


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_keys(v)


def _no_quantity_keys(obj):
    bad = [k for k in _walk_keys(obj) if any(w in str(k).lower() for w in ("qty", "quantity", "stock",
                                                                              "difference", "gap"))]
    assert bad == [], bad


# ---------------- start ----------------
def test_start_reveals_no_quantity_and_lists_products_by_name(db_session, users):
    p1 = _product(db_session, 5, "ZZZ_TSC_" + _rand())
    p2 = _product(db_session, 7, "AAA_TSC_" + _rand())
    out = _ctrl(db_session, users["ctrl"]).start()
    _no_quantity_keys(out)
    assert out["scope"] == "tous" and out["id"] and out["started_at"]
    ids = [x["id"] for x in out["products"]]
    assert p1.medication_id in ids and p2.medication_id in ids
    assert ids.index(p2.medication_id) < ids.index(p1.medication_id)
    assert set(out["products"][0].keys()) == {"id", "name"}
    c = db_session.get(StockCount, out["id"])
    assert c.status == "en_cours" and c.started_by == users["ctrl"].user_id
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockCount", resource_id=out["id"],
                                                       action_performed="CREATE").count() == 1


def test_second_start_same_user_409_other_user_ok(db_session, users):
    _ctrl(db_session, users["ctrl"]).start()
    with pytest.raises(StockCountConflictError):
        _ctrl(db_session, users["ctrl"]).start()
    assert _ctrl(db_session, users["ctrl2"]).start()["id"]


def test_start_invalid_scope(db_session, users):
    with pytest.raises(ValueError):
        _ctrl(db_session, users["ctrl"]).start("n_importe")


@pytest.mark.parametrize("who", ["admin", "promo", "sec"])
def test_start_forbidden_roles(db_session, users, who):
    with pytest.raises(PermissionError):
        _ctrl(db_session, users[who]).start()


# ---------------- submit ----------------
def test_submit_gap_creates_request_lines_audit_notifications(db_session, users):
    p_gap = _product(db_session, 10)
    p_obs = _product(db_session, 4)
    p_ok = _product(db_session, 6)
    p_absent = _product(db_session, 3)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    out = ctrl.submit(c["id"], [
        {"product_id": p_ok.medication_id, "counted_qty": 6},
        {"product_id": p_gap.medication_id, "counted_qty": 8},
        {"product_id": p_obs.medication_id, "counted_qty": 9, "observation": "  carton retrouve  "},
    ])
    assert out["status"] == "valide" and out["submitted_at"]
    by = {l["product_id"]: l for l in out["lines"]}
    assert set(by) == {p_gap.medication_id, p_obs.medication_id, p_ok.medication_id}
    g, o, k = by[p_gap.medication_id], by[p_obs.medication_id], by[p_ok.medication_id]
    assert (g["counted_qty"], g["previous_qty"], g["difference"], g["gap_kind"]) == (8, 10, -2, "moins")
    assert (o["counted_qty"], o["previous_qty"], o["difference"], o["gap_kind"]) == (9, 4, 5, "plus")
    assert (k["counted_qty"], k["previous_qty"], k["difference"], k["gap_kind"]) == (6, 6, 0, "aucun")
    assert k["adjustment_request_id"] is None and o["observation"] == "carton retrouve"
    assert g["product_name"] == p_gap.drug_name

    rg = db_session.get(StockAdjustmentRequest, g["adjustment_request_id"])
    assert (rg.kind, rg.quantity, rg.status, rg.requested_by, rg.stock_at_request) == (
        "correction", 8, "en_attente", users["ctrl"].user_id, 10)
    assert rg.reason == f"Ecart constate au comptage n. {c['id']} : systeme 10, compte 8"
    ro = db_session.get(StockAdjustmentRequest, o["adjustment_request_id"])
    assert (ro.quantity, ro.stock_at_request, ro.reason) == (9, 4, "carton retrouve")
    assert db_session.query(StockAdjustmentRequest).filter(
        StockAdjustmentRequest.product_id.in_([p_ok.medication_id, p_absent.medication_id])).count() == 0

    # stock inchange : il ne change qu'a l'approbation
    db_session.expire_all()
    assert db_session.get(Pharmacy, p_gap.medication_id).quantity == 10
    rows = db_session.query(StockCountLine).filter_by(count_id=c["id"]).all()
    assert len(rows) == 3 and p_absent.medication_id not in {r.product_id for r in rows}
    row = next(r for r in rows if r.product_id == p_gap.medication_id)
    assert (row.previous_qty, row.difference, row.adjustment_request_id) == (10, -2, rg.id)

    for adm in ("admin", "admin2"):
        notes = db_session.query(Notification).filter_by(recipient_user_id=users[adm].user_id,
                                                         type="stock_adjustment_request").all()
        payloads = sorted((n.payload for n in notes), key=lambda p: p["request_id"])
        assert payloads == sorted([
            {"request_id": rg.id, "product_name": p_gap.drug_name, "kind": "correction", "quantity": 8,
             "requested_by_name": users["ctrl"].full_name},
            {"request_id": ro.id, "product_name": p_obs.drug_name, "kind": "correction", "quantity": 9,
             "requested_by_name": users["ctrl"].full_name}], key=lambda p: p["request_id"])
    assert db_session.query(Notification).filter_by(recipient_user_id=users["ctrl"].user_id).count() == 0

    audits = db_session.query(AuditUserAction)
    assert audits.filter_by(resource_type="StockCount", resource_id=c["id"], action_performed="SUBMIT").count() == 1
    for r in (rg, ro):
        assert audits.filter_by(resource_type="StockAdjustmentRequest", resource_id=r.id,
                                action_performed="CREATE").count() == 1


def test_submit_zero_gap_no_request_no_notification(db_session, users):
    p = _product(db_session, 5)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    before = db_session.query(StockAdjustmentRequest).count()
    out = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 5}])
    assert out["lines"][0]["adjustment_request_id"] is None
    assert db_session.query(StockAdjustmentRequest).count() == before
    assert db_session.query(Notification).filter_by(recipient_user_id=users["admin"].user_id,
                                                    type="stock_adjustment_request").count() == 0


def test_previous_qty_read_under_lock_not_session_cache(db_session, users):
    p = _product(db_session, 10)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    # changement en SQL que le cache de session ignore (simule une vente faite ailleurs)
    db_session.execute(text("UPDATE pharmacy SET quantity = 7 WHERE medication_id = :i"), {"i": p.medication_id})
    assert p.quantity == 10
    out = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 7}])
    assert out["lines"][0]["previous_qty"] == 7 and out["lines"][0]["difference"] == 0


class _Clock:
    """Horloge injectable (UTC aware) que le test avance a la main."""
    def __init__(self, at):
        self.at = at

    def __call__(self):
        return self.at


T0 = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)
T0N = T0.replace(tzinfo=None)


def _move(db, p, qty, at, kind="VENTE"):
    """Mouvement de stock a l'heure `at` (UTC naif) ET stock du produit modifie en SQL."""
    db.add(StockMovement(medication_id=p.medication_id, change_qty=qty, movement_type=kind,
                         note="t", created_by="t", created_at=at))
    db.execute(text("UPDATE pharmacy SET quantity = quantity + :q WHERE medication_id = :i"),
               {"q": qty, "i": p.medication_id})
    db.flush()


def _timed(db_session, users):
    clock = _Clock(T0)
    return clock, _ctrl(db_session, users["ctrl"], clock=clock)


def test_sale_after_counting_is_not_a_gap_and_approval_gives_shelf(db_session, users):
    # (a) stock 10, compte 8 a t1, vente de 3 a t2 > t1, validation : ecart -2, approbation -> 5
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    _move(db_session, p, -3, T0N + timedelta(minutes=2))
    clock.at = T0 + timedelta(minutes=5)
    out = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 8,
                                 "counted_at": "2030-01-01T11:01:00+01:00"}])
    l = out["lines"][0]
    assert l["counted_at"] == "2030-01-01T10:01:00+00:00"
    assert (l["movements_net"], l["stock_at_count"], l["previous_qty"], l["difference"], l["movements_during"]) == (
        -3, 10, 10, -2, 1)
    req = db_session.get(StockAdjustmentRequest, l["adjustment_request_id"])
    assert (req.quantity, req.stock_at_request) == (8, 10)
    _stock_ctrl(db_session, users["admin"]).approve_adjustment(req.id)
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 5
    row = db_session.query(StockCountLine).filter_by(count_id=c["id"]).one()
    assert (row.counted_at, row.movements_net) == (T0N + timedelta(minutes=1), -3)


def test_sale_before_counting_no_gap(db_session, users):
    # (b) vente de 3 AVANT counted_at, etagere comptee 7 : aucun ecart, aucune demande
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    _move(db_session, p, -3, T0N + timedelta(minutes=1))
    clock.at = T0 + timedelta(minutes=5)
    l = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 7,
                               "counted_at": "2030-01-01T10:02:00Z"}])["lines"][0]
    assert (l["movements_net"], l["stock_at_count"], l["difference"], l["adjustment_request_id"]) == (0, 7, 0, None)


def test_replenishment_after_counting(db_session, users):
    # (c) reception +5 apres le comptage : stock 15 a la validation, ecart calcule sur 10
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    _move(db_session, p, 5, T0N + timedelta(minutes=3), kind="reception")
    clock.at = T0 + timedelta(minutes=5)
    l = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 9,
                               "counted_at": "2030-01-01T10:01:00Z"}])["lines"][0]
    assert (l["movements_net"], l["stock_at_count"], l["difference"]) == (5, 10, -1)
    _stock_ctrl(db_session, users["admin"]).approve_adjustment(l["adjustment_request_id"])
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 14  # 9 en rayon + 5 recus


@pytest.mark.parametrize("given,expected", [
    ("2029-12-31T10:00:00Z", "2030-01-01T10:00:00+00:00"),   # avant le debut -> debut
    ("2031-01-01T10:00:00Z", "2030-01-01T10:05:00+00:00"),   # futur -> maintenant
])
def test_counted_at_clamped(db_session, users, given, expected):
    # (d)
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    clock.at = T0 + timedelta(minutes=5)
    l = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 10, "counted_at": given}])["lines"][0]
    assert l["counted_at"] == expected


def test_missing_counted_at_is_submit_time(db_session, users):
    # (e) sans heure : heure de validation, les mouvements depuis le debut ne sont pas retires
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    _move(db_session, p, -3, T0N + timedelta(minutes=2))
    clock.at = T0 + timedelta(minutes=5)
    l = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 7}])["lines"][0]
    assert l["counted_at"] == "2030-01-01T10:05:00+00:00"
    assert (l["movements_net"], l["movements_during"], l["stock_at_count"], l["difference"]) == (0, 0, 7, 0)


def test_invalid_counted_at_422(db_session, users):
    p = _product(db_session, 10)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    with pytest.raises(ValueError):
        ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 1, "counted_at": "hier"}])


def test_negative_stock_at_count_with_later_sale(db_session, users):
    # (f) stock -1 a l'heure du comptage puis vente de 2 : ligne a 0, demande garde -1, approbation -> 3 - 2
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    db_session.execute(text("UPDATE pharmacy SET quantity = -1 WHERE medication_id = :i"), {"i": p.medication_id})
    _move(db_session, p, -2, T0N + timedelta(minutes=3))
    clock.at = T0 + timedelta(minutes=5)
    l = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 3,
                               "counted_at": "2030-01-01T10:01:00Z"}])["lines"][0]
    assert (l["stock_at_count"], l["previous_qty"], l["difference"], l["movements_net"]) == (-1, 0, 3, -2)
    req = db_session.get(StockAdjustmentRequest, l["adjustment_request_id"])
    assert req.stock_at_request == -1 and req.reason.startswith("Stock systeme negatif (valeur lue -1).")


def test_blind_nothing_about_times_before_validation(db_session, users):
    # (g)
    p = _product(db_session, 10)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    for obj in (c, ctrl.get(c["id"]), ctrl.list({"mine": True}), ctrl.status()):
        keys = list(_walk_keys(obj))
        assert not any(k in ("counted_at", "movements_net", "stock_at_count", "movements_during") for k in keys)
        _no_quantity_keys(obj)
    assert p


def test_list_mine_filter(db_session, users):
    mine_c = _ctrl(db_session, users["ctrl"]).start()
    other = _ctrl(db_session, users["ctrl2"]).start()
    adm = _ctrl(db_session, users["admin"])
    assert {mine_c["id"], other["id"]} <= {x["id"] for x in adm.list({"limit": 200})["items"]}
    assert adm.list({"mine": True})["items"] == []
    ids = {x["id"] for x in _ctrl(db_session, users["ctrl"]).list({"mine": True})["items"]}
    assert mine_c["id"] in ids and other["id"] not in ids
    with pytest.raises(ValueError):
        adm.list({"mine": "oui"})


@pytest.mark.parametrize("counted", [5, 0])
def test_negative_system_stock_accepted_and_flagged(db_session, users, counted):
    p = _product(db_session, 10)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    db_session.execute(text("UPDATE pharmacy SET quantity = -3 WHERE medication_id = :i"), {"i": p.medication_id})
    out = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": counted}])
    l = out["lines"][0]
    assert (l["previous_qty"], l["difference"]) == (0, counted)
    req = db_session.get(StockAdjustmentRequest, l["adjustment_request_id"])
    assert (req.kind, req.quantity, req.stock_at_request) == ("correction", counted, -3)
    assert req.reason == (f"Stock systeme negatif (valeur lue -3). Ecart constate au comptage n. {c['id']} : "
                          f"systeme 0, compte {counted}")
    assert db_session.query(Notification).filter_by(recipient_user_id=users["admin"].user_id,
                                                    type="stock_adjustment_request").count() == 1


def test_negative_system_stock_prefixes_observation(db_session, users):
    p = _product(db_session, 10)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    db_session.execute(text("UPDATE pharmacy SET quantity = -3 WHERE medication_id = :i"), {"i": p.medication_id})
    out = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 2, "observation": "vu"}])
    req = db_session.get(StockAdjustmentRequest, out["lines"][0]["adjustment_request_id"])
    assert req.reason == "Stock systeme negatif (valeur lue -3). vu"


def test_second_submit_409(db_session, users):
    p = _product(db_session, 5)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 4}])
    n = db_session.query(StockAdjustmentRequest).filter_by(product_id=p.medication_id).count()
    with pytest.raises(StockCountConflictError):
        ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 3}])
    assert db_session.query(StockAdjustmentRequest).filter_by(product_id=p.medication_id).count() == n == 1


def test_submit_unknown_product_422_and_nothing_written(db_session, users):
    p = _product(db_session, 5)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    with pytest.raises(ValueError):
        ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 1},
                              {"product_id": 987654321, "counted_qty": 1}])
    db_session.expire_all()
    assert db_session.get(StockCount, c["id"]).status == "en_cours"
    assert db_session.query(StockCountLine).filter_by(count_id=c["id"]).count() == 0
    assert db_session.query(StockAdjustmentRequest).filter_by(product_id=p.medication_id).count() == 0


def test_submit_deleted_product_422(db_session, users):
    p = _product(db_session, 5)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    pid = p.medication_id
    db_session.delete(p)
    db_session.flush()
    with pytest.raises(ValueError):
        ctrl.submit(c["id"], [{"product_id": pid, "counted_qty": 1}])


def test_submit_only_by_owner_stock_controller(db_session, users):
    p = _product(db_session, 5)
    c = _ctrl(db_session, users["ctrl"]).start()
    for who in ("ctrl2", "promo", "admin"):
        with pytest.raises(PermissionError):
            _ctrl(db_session, users[who]).submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 5}])
    out = _ctrl(db_session, users["ctrl"]).submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 5}])
    assert out["status"] == "valide"


def test_submit_not_found(db_session, users):
    with pytest.raises(StockCountNotFoundError):
        _ctrl(db_session, users["ctrl"]).submit(987654321, [{"product_id": 1, "counted_qty": 1}])


# ---------------- remplacement des demandes de comptage en attente ----------------
def _count(db, user, lines):
    ctrl = _ctrl(db, user)
    c = ctrl.start()
    return ctrl.submit(c["id"], lines)


def _stock_ctrl(db, user):
    from controller.stock_controller import StockController
    from repositories.stock_repo import StockRepository
    return StockController(StockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def test_recount_supersedes_pending_request_and_approval_gives_counted_stock(db_session, users):
    from controller.stock_controller import StockConflictError
    p = _product(db_session, 10)
    first = _count(db_session, users["ctrl"], [{"product_id": p.medication_id, "counted_qty": 8}])
    l1 = first["lines"][0]
    r1 = l1["adjustment_request_id"]
    assert l1["recount"] is False and l1["previous_count_id"] is None and l1["superseded_request_ids"] == []
    second = _count(db_session, users["ctrl2"], [{"product_id": p.medication_id, "counted_qty": 8}])
    l2 = second["lines"][0]
    r2 = l2["adjustment_request_id"]
    assert r2 and r2 != r1
    assert l2["superseded_request_ids"] == [r1]
    assert l2["recount"] is True and l2["previous_count_id"] == first["id"]
    db_session.expire_all()
    old = db_session.get(StockAdjustmentRequest, r1)
    assert (old.status, old.decided_by, old.decision_note) == (
        "annule", users["ctrl2"].user_id, f"remplacee par le comptage n. {second['id']}")
    assert old.decided_at is not None
    assert db_session.get(StockAdjustmentRequest, r2).status == "en_attente"
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockAdjustmentRequest", resource_id=r1,
                                                       action_performed="SUPERSEDE").count() == 1
    q = db_session.query(Notification).filter_by(recipient_user_id=users["admin"].user_id,
                                                 type="stock_adjustment_request")
    n2 = q.filter(Notification.payload["request_id"].astext == str(r2)).one()
    assert n2.payload == {"request_id": r2, "product_name": p.drug_name, "kind": "correction", "quantity": 8,
                          "requested_by_name": users["ctrl2"].full_name, "supersedes": [r1]}
    n1 = q.filter(Notification.payload["request_id"].astext == str(r1)).one()
    assert "supersedes" not in n1.payload
    adm = _stock_ctrl(db_session, users["admin"])
    with pytest.raises(StockConflictError):
        adm.approve_adjustment(r1)
    adm.approve_adjustment(r2)
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 8
    again = _ctrl(db_session, users["promo"]).get(second["id"])["lines"][0]
    assert again["superseded_request_ids"] == [r1] and again["recount"] is True


def test_recount_without_gap_cancels_pending_and_notifies(db_session, users):
    p = _product(db_session, 10)
    first = _count(db_session, users["ctrl"], [{"product_id": p.medication_id, "counted_qty": 8}])
    r1 = first["lines"][0]["adjustment_request_id"]
    second = _count(db_session, users["ctrl"], [{"product_id": p.medication_id, "counted_qty": 10}])
    l2 = second["lines"][0]
    assert l2["adjustment_request_id"] is None and l2["superseded_request_ids"] == [r1]
    db_session.expire_all()
    assert db_session.get(StockAdjustmentRequest, r1).status == "annule"
    for adm in ("admin", "admin2"):
        n = db_session.query(Notification).filter_by(recipient_user_id=users[adm].user_id,
                                                     type="stock_count_superseded").one()
        assert n.payload == {"count_id": second["id"], "product_name": p.drug_name,
                             "superseded_request_ids": [r1], "counted_by_name": users["ctrl"].full_name}


def test_other_origin_and_decided_requests_untouched(db_session, users):
    p = _product(db_session, 10)
    sec_req = _stock_ctrl(db_session, users["sec"]).create_adjustment_request(
        {"product_id": p.medication_id, "kind": "correction", "quantity": 9, "reason": "secretaire"})["id"]
    first = _count(db_session, users["ctrl"], [{"product_id": p.medication_id, "counted_qty": 8}])
    r_rej = first["lines"][0]["adjustment_request_id"]
    adm = _stock_ctrl(db_session, users["admin"])
    adm.reject_adjustment(r_rej, "non")
    second = _count(db_session, users["ctrl"], [{"product_id": p.medication_id, "counted_qty": 7}])
    r_app = second["lines"][0]["adjustment_request_id"]
    assert second["lines"][0]["superseded_request_ids"] == []
    adm.approve_adjustment(r_app)
    third = _count(db_session, users["ctrl"], [{"product_id": p.medication_id, "counted_qty": 7}])
    assert third["lines"][0]["superseded_request_ids"] == []
    db_session.expire_all()
    assert db_session.get(StockAdjustmentRequest, sec_req).status == "en_attente"
    assert db_session.get(StockAdjustmentRequest, r_rej).status == "refuse"
    assert db_session.get(StockAdjustmentRequest, r_app).status == "approuve"
    assert db_session.query(Notification).filter_by(type="stock_count_superseded",
                                                    recipient_user_id=users["admin"].user_id).count() == 0


# ---------------- abandon ----------------
def test_abandon_then_new_start_allowed(db_session, users):
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    out = ctrl.abandon(c["id"])
    assert out["status"] == "abandonne"
    assert db_session.get(StockCount, c["id"]) is not None
    with pytest.raises(StockCountConflictError):
        ctrl.abandon(c["id"])
    assert ctrl.start()["id"] != c["id"]


def test_abandon_other_counter_forbidden(db_session, users):
    c = _ctrl(db_session, users["ctrl"]).start()
    for who in ("ctrl2", "admin", "promo"):
        with pytest.raises(PermissionError):
            _ctrl(db_session, users[who]).abandon(c["id"])
    assert _ctrl(db_session, users["ctrl"]).abandon(c["id"])["status"] == "abandonne"


# ---------------- get / list ----------------
def test_get_reveals_only_after_validation(db_session, users):
    p = _product(db_session, 5)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    before = ctrl.get(c["id"])
    _no_quantity_keys(before)
    assert before["status"] == "en_cours" and before["lines"] is None
    ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 2}])
    after = ctrl.get(c["id"])
    assert after["lines"][0]["difference"] == -3 and after["lines"][0]["previous_qty"] == 5
    assert after["lines"][0]["gap_kind"] == "moins"
    assert _ctrl(db_session, users["promo"]).get(c["id"])["lines"][0]["difference"] == -3


def test_counter_cannot_read_other_count(db_session, users):
    c = _ctrl(db_session, users["ctrl"]).start()
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["ctrl2"]).get(c["id"])
    assert _ctrl(db_session, users["admin"]).get(c["id"])["id"] == c["id"]
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["sec"]).get(c["id"])
    with pytest.raises(StockCountNotFoundError):
        _ctrl(db_session, users["admin"]).get(987654321)


def test_list_scoping_filters_and_bounds(db_session, users):
    p = _product(db_session, 5)
    a = _ctrl(db_session, users["ctrl"])
    c1 = a.start()
    a.submit(c1["id"], [{"product_id": p.medication_id, "counted_qty": 5}])
    c2 = a.start()
    o = _ctrl(db_session, users["ctrl2"]).start()

    mine = {x["id"] for x in a.list({})["items"]}
    assert {c1["id"], c2["id"]} <= mine and o["id"] not in mine
    every = {x["id"] for x in _ctrl(db_session, users["promo"]).list({"limit": 200})["items"]}
    assert {c1["id"], c2["id"], o["id"]} <= every
    valides = a.list({"status": "valide"})["items"]
    assert [x["id"] for x in valides if x["id"] in (c1["id"], c2["id"])] == [c1["id"]]
    en_cours = next(x for x in a.list({})["items"] if x["id"] == c2["id"])
    _no_quantity_keys(en_cours)
    today = date.today()
    assert c1["id"] in {x["id"] for x in a.list({"date_from": today - timedelta(days=1),
                                                    "date_to": today + timedelta(days=1)})["items"]}
    assert a.list({"date_from": (today + timedelta(days=5)).isoformat()})["items"] == []
    for bad in ({"limit": 0}, {"limit": 201}, {"offset": -1}, {"status": "x"},
                {"date_from": "2026-13-01"}, {"date_from": today, "date_to": today - timedelta(days=1)}):
        with pytest.raises(ValueError):
            a.list(bad)
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["sec"]).list({})


# ---------------- status ----------------
def test_status_three_states_no_quantity(db_session, users):
    fixed = datetime(2030, 1, 31, 12, 0, tzinfo=timezone.utc)
    clock = lambda: fixed  # noqa: E731
    p_new = _product(db_session, 5)
    p_old = _product(db_session, 5)
    p_recent = _product(db_session, 5)
    # la ligne de reglage existe (sinon le test verifierait le repli a 30, pas le reglage)
    db_session.execute(text("INSERT INTO stock_count_settings (id, interval_days) VALUES (1, 30) "
                            "ON CONFLICT (id) DO UPDATE SET interval_days = 30"))
    for prod, when in ((p_old, datetime(2029, 12, 31, 11, 0)), (p_recent, datetime(2030, 1, 1, 12, 0))):
        sc = StockCount(status="en_cours", started_by=users["ctrl"].user_id, started_at=when, scope="tous")
        db_session.add(sc)
        db_session.flush()
        db_session.add(StockCountLine(count_id=sc.id, product_id=prod.medication_id, counted_qty=5,
                                      previous_qty=5, difference=0, movements_during=0, counted_at=when))
        db_session.flush()
        sc.status = "valide"
        sc.submitted_at = when
        db_session.flush()
    out = _ctrl(db_session, users["promo"], clock=clock).status()
    _no_quantity_keys(out)
    assert out["interval_days"] == 30
    by = {x["product_id"]: x for x in out["products"]}
    assert (by[p_new.medication_id]["status"], by[p_new.medication_id]["days_since"]) == ("jamais_compte", None)
    assert (by[p_old.medication_id]["status"], by[p_old.medication_id]["days_since"]) == ("en_retard", 31)
    assert (by[p_recent.medication_id]["status"], by[p_recent.medication_id]["days_since"]) == ("a_jour", 30)
    assert by[p_recent.medication_id]["last_counted_at"].startswith("2030-01-01T12:00:00")
    assert by[p_new.medication_id]["name"] == p_new.drug_name
    counts = out["counts"]
    assert counts["jamais_compte"] >= 1 and counts["en_retard"] >= 1 and counts["a_jour"] >= 1
    assert sum(counts.values()) == len(out["products"])


def test_status_falls_back_to_30_when_settings_row_missing(db_session, users):
    db_session.execute(text("DELETE FROM stock_count_settings"))
    ctrl = _ctrl(db_session, users["admin"])
    assert ctrl.status()["interval_days"] == 30
    assert ctrl.get_settings()["interval_days"] == 30
    assert ctrl.set_interval(12)["interval_days"] == 12
    db_session.expire_all()
    row = db_session.get(StockCountSettings, 1)
    assert row.interval_days == 12 and row.updated_by == users["admin"].user_id and row.updated_at


# ---------------- settings ----------------
def test_set_interval_admin_only_bounds_and_audit(db_session, users):
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["ctrl"]).set_interval(10)
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["promo"]).set_interval(10)
    adm = _ctrl(db_session, users["admin"])
    for bad in (0, 366, -1, True, 2.5, "10", None):
        with pytest.raises(ValueError):
            adm.set_interval(bad)
    assert adm.set_interval(365)["interval_days"] == 365
    assert adm.set_interval(1)["interval_days"] == 1
    assert _ctrl(db_session, users["promo"]).get_settings()["interval_days"] == 1
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockCountSettings",
                                                       action_performed="UPDATE").count() >= 2
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["sec"]).get_settings()


# ---------------- fabrique ----------------
def test_factory_wires_notifications_and_audit(db_session, users):
    p = _product(db_session, 5)
    ctrl = get_stock_count_controller(db_session, users["ctrl"])
    assert ctrl.notification_repo is not None and ctrl.audit_repo is not None
    c = ctrl.start()
    out = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 1}])
    rid = out["lines"][0]["adjustment_request_id"]
    assert db_session.query(Notification).filter_by(recipient_user_id=users["admin"].user_id,
                                                    type="stock_adjustment_request").count() == 1
    assert db_session.query(Notification).filter_by(type="stock_adjustment_request").filter(
        Notification.payload["request_id"].astext == str(rid)).count() >= 2


# ---------------- concurrence (vraies connexions, donnees commitees) ----------------
def _cleanup(user_id, product_id):
    s = SessionLocal()
    try:
        s.execute(text("SET LOCAL session_replication_role = replica"))
        s.execute(text("DELETE FROM stock_count_lines WHERE count_id IN "
                       "(SELECT id FROM stock_counts WHERE started_by = :u)"), {"u": user_id})
        s.execute(text("DELETE FROM stock_counts WHERE started_by = :u"), {"u": user_id})
        s.execute(text("DELETE FROM notifications WHERE type = 'stock_adjustment_request' AND "
                       "payload->>'request_id' IN (SELECT id::text FROM stock_adjustment_requests "
                       "WHERE requested_by = :u)"), {"u": user_id})
        s.execute(text("DELETE FROM stock_adjustment_requests WHERE requested_by = :u"), {"u": user_id})
        s.execute(text("DELETE FROM audit_user_actions WHERE user_id = :u"), {"u": user_id})
        if product_id:
            s.execute(text("DELETE FROM stock_movement WHERE medication_id = :p"), {"p": product_id})
            s.execute(text("DELETE FROM pharmacy WHERE medication_id = :p"), {"p": product_id})
        s.execute(text("DELETE FROM users WHERE user_id = :u"), {"u": user_id})
        s.commit()
    finally:
        s.close()


def _is_superuser() -> bool:
    s = SessionLocal()
    try:
        return s.execute(text("select current_setting('is_superuser')")).scalar() == "on"
    finally:
        s.close()


def test_concurrent_double_submit_one_wins():
    # Donnees commitees : le nettoyage doit contourner les triggers d'immuabilite
    # (comptages valides/abandonnes et lignes indelebiles) via session_replication_role,
    # ce qui exige un super-utilisateur PostgreSQL. Sinon le test est saute (rien a nettoyer).
    if not _is_superuser():
        pytest.skip("necessite un super-utilisateur PostgreSQL pour nettoyer les comptages commites")
    setup = SessionLocal()
    user_id = product_id = None
    try:
        user = create_test_user(setup, _rand("t_sc_conc"), "StockController")
        p = _product(setup, 10)
        setup.commit()
        user_id, product_id = user.user_id, p.medication_id
        cid = _ctrl(setup, user).start()["id"]
        setup.close()

        results, barrier = [], threading.Barrier(2)

        def run():
            s = SessionLocal()
            try:
                u = s.get(type(user), user_id)
                barrier.wait()
                _ctrl(s, u).submit(cid, [{"product_id": product_id, "counted_qty": 7}])
                results.append("ok")
            except StockCountConflictError:
                results.append("409")
            except Exception as e:  # pragma: no cover
                results.append(repr(e))
            finally:
                s.close()

        ts = [threading.Thread(target=run) for _ in range(2)]
        [t.start() for t in ts]
        [t.join(60) for t in ts]
        assert sorted(results) == ["409", "ok"], results
        chk = SessionLocal()
        try:
            assert chk.query(StockAdjustmentRequest).filter_by(product_id=product_id).count() == 1
            assert chk.query(StockCountLine).filter_by(count_id=cid).count() == 1
        finally:
            chk.close()
    finally:
        try:
            setup.close()
        except Exception:
            pass
        if user_id:
            _cleanup(user_id, product_id)


# ---------------- ecart d'horloge du navigateur (client_now) ----------------
def _iso_z(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _submit_audit(db, cid):
    return db.query(AuditUserAction).filter_by(resource_type="StockCount", resource_id=cid,
                                               action_performed="SUBMIT").one().new_values


def _skew_case(db_session, users, client_offset_s, send_client_now=True):
    """Debut T0 ; vente de 3 a T0+8 min ; vrai moment du comptage M = T0+10 min ; validation a T0+15 min.
    Le navigateur a `client_offset_s` secondes d'avance (negatif = retard) sur le serveur."""
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    _move(db_session, p, -3, T0N + timedelta(minutes=8))
    clock.at = T0 + timedelta(minutes=15)
    true_moment = T0 + timedelta(minutes=10)
    off = timedelta(seconds=client_offset_s)
    body_now = _iso_z(clock.at + off) if send_client_now else None
    out = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 7,
                                 "counted_at": _iso_z(true_moment + off)}], client_now=body_now)
    return c, out["lines"][0]


@pytest.mark.parametrize("offset", [-300, 300])
def test_browser_clock_skew_corrected(db_session, users, offset):
    c, l = _skew_case(db_session, users, offset)
    assert l["counted_at"] == "2030-01-01T10:10:00+00:00"
    assert (l["movements_net"], l["stock_at_count"], l["difference"], l["adjustment_request_id"]) == (0, 7, 0, None)
    a = _submit_audit(db_session, c["id"])
    assert a["clock_skew_seconds"] == -offset and a["clock_skew_flag"] is True and a["clock_skew_capped"] is False
    assert a["lines"][0]["counted_at_adjusted"] is True


def test_browser_behind_without_client_now_documents_old_bug(db_session, users):
    # sans client_now : la vente faite AVANT le vrai comptage passe pour posterieure -> faux ecart
    c, l = _skew_case(db_session, users, -300, send_client_now=False)
    assert l["counted_at"] == "2030-01-01T10:05:00+00:00"
    assert (l["movements_net"], l["stock_at_count"], l["difference"]) == (-3, 10, -3)
    a = _submit_audit(db_session, c["id"])
    assert a["clock_skew_seconds"] == 0 and a["clock_skew_flag"] is False
    assert a["lines"][0]["counted_at_adjusted"] is False


def test_skew_beyond_ten_minutes_capped(db_session, users):
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    clock.at = T0 + timedelta(minutes=60)
    off = timedelta(seconds=-1200)  # navigateur 20 min en retard
    l = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 10,
                               "counted_at": _iso_z(T0 + timedelta(minutes=40) + off)}],
                    client_now=_iso_z(clock.at + off))["lines"][0]
    assert l["counted_at"] == "2030-01-01T10:30:00+00:00"  # 10:20 + 600 s seulement
    a = _submit_audit(db_session, c["id"])
    assert (a["clock_skew_seconds"], a["clock_skew_flag"], a["clock_skew_capped"]) == (600, True, True)


def test_small_skew_not_flagged_and_unadjusted_line(db_session, users):
    p = _product(db_session, 10)
    clock, ctrl = _timed(db_session, users)
    c = ctrl.start()
    clock.at = T0 + timedelta(minutes=15)
    ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 10,
                           "counted_at": "2030-01-01T10:10:00Z"}], client_now="2030-01-01T10:15:00Z")
    a = _submit_audit(db_session, c["id"])
    assert (a["clock_skew_seconds"], a["clock_skew_flag"]) == (0, False)
    assert a["lines"][0]["counted_at_adjusted"] is False


@pytest.mark.parametrize("bad", ["hier", "2030-13-01T00:00:00Z", 5])
def test_invalid_client_now_422(db_session, users, bad):
    p = _product(db_session, 10)
    ctrl = _ctrl(db_session, users["ctrl"])
    c = ctrl.start()
    with pytest.raises(ValueError):
        ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": 1}], client_now=bad)
    db_session.expire_all()
    assert db_session.get(StockCount, c["id"]).status == "en_cours"
