# tests/test_lab_stock_end_to_end.py
"""Task 8 (stock labo) : parcours complet au niveau controleur (aucune connexion HTTP).
creation (laborantin) -> signalement -> liste a commander -> commande datee -> reception
(StockController) -> demande close, stock augmente -> comptage sous le seuil -> nouvelle
demande seuil -> depenses et historique de prix coherents ; pharmacy, caisse et
stock_movements inchanges."""
from datetime import date, timedelta
from decimal import Decimal

from controller.lab_stock_controller import LabStockController
from models.caisse import Caisse
from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import LabStockRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_user

TODAY = date.today()


def _ctrl(db, user):
    return LabStockController(LabStockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _counts(db):
    return (db.query(Pharmacy).count(), db.query(Caisse).count(), db.query(StockMovement).count())


def test_full_lab_stock_scenario(db_session):
    db = db_session
    before = _counts(db)
    lab_u = create_test_user(db, "t_lse2e_lab", "laborantin")
    ctl_u = create_test_user(db, "t_lse2e_ctl", "StockController")
    promo_u = create_test_user(db, "t_lse2e_promo", "promoteur")
    lab, ctl, promo = _ctrl(db, lab_u), _ctrl(db, ctl_u), _ctrl(db, promo_u)

    # 1. creation par la laborantine
    p = lab.create_product({"name": "TEST_LSE2E_Reactif", "packaging": "Boite de 100",
                            "alert_threshold": 10, "supplier": "TEST_LSE2E_Fourn"})
    pid = p["id"]
    assert p["quantity"] == 0

    # 2. signalement -> une seule demande ouverte pour ce produit
    lab.signal(pid, "fini")
    open_reqs = [r for r in promo.list_requests("a_commander") if r["product_id"] == pid]
    assert len(open_reqs) == 1
    req_id = open_reqs[0]["id"]

    # 3. commande avec date prevue, visible pour la laborantine
    expected = TODAY + timedelta(days=5)
    promo.mark_ordered(req_id, expected.isoformat())
    seen = [r for r in lab.list_requests("commande") if r["id"] == req_id]
    assert len(seen) == 1 and seen[0]["expected_date"] == expected

    # 4. reception par le controleur : demande close, stock augmente
    rc = ctl.create_receipt({
        "invoice_number": "TEST_LSE2E_F1", "supplier": "TEST_LSE2E_Fourn",
        "delivery_date": TODAY.isoformat(),
        "lines": [{"product_id": pid, "ordered_qty": 20, "received_qty": 20, "unit_price": "1250.50",
                   "lot_number": "TEST_LOT1",
                   "expiry_date": (TODAY + timedelta(days=300)).isoformat()}],
    })
    assert Decimal(str(rc["total_amount"])) == Decimal("25010.00")
    closed = [r for r in lab.list_requests() if r["id"] == req_id][0]
    assert closed["status"] == "recu" and closed["closed_by_receipt_id"] == rc["id"]
    prod = [x for x in lab.list_products() if x["id"] == pid][0]
    assert prod["quantity"] == 20
    assert not [r for r in lab.list_requests("a_commander") if r["product_id"] == pid]

    # 5. comptage sous le seuil -> nouvelle demande seuil
    res = lab.submit_count([{"product_id": pid, "previous_qty": 20, "counted_qty": 3}])
    assert res["conflicts"] == [] and res["applied"][0]["counted_qty"] == 3
    new_reqs = [r for r in lab.list_requests("a_commander") if r["product_id"] == pid]
    assert len(new_reqs) == 1 and new_reqs[0]["origin"] == "seuil" and new_reqs[0]["id"] != req_id
    low = [x for x in lab.get_alerts()["low"] if x["product_id"] == pid]
    assert low and low[0]["request_id"] == new_reqs[0]["id"]

    # mouvements : reception +20 puis comptage -17
    mv = lab.list_movements(product_id=pid)
    assert sorted((m["movement_type"], m["change_qty"]) for m in mv) == [("comptage", -17), ("reception", 20)]

    # 6. depenses et historique de prix coherents
    exp = promo.expenses(TODAY.isoformat(), TODAY.isoformat())
    assert Decimal(str(exp["total"])) >= Decimal("25010.00")
    month = TODAY.strftime("%Y-%m")
    assert sum(Decimal(str(m["total"])) for m in exp["by_month"] if m["month"] == month) == Decimal(str(exp["total"]))
    sup = [s for s in exp["by_supplier"] if s["supplier"] == "TEST_LSE2E_Fourn"]
    assert len(sup) == 1 and Decimal(str(sup[0]["total"])) == Decimal("25010.00")
    hist = promo.price_history(pid)
    assert [(h["receipt_id"], Decimal(str(h["unit_price"])), h["received_qty"]) for h in hist] == [
        (rc["id"], Decimal("1250.50"), 20)]

    # 7. aucune ecriture hors des tables lab_stock_*
    db.flush()
    assert _counts(db) == before
