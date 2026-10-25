# tests/test_report_products.py
"""Rapports, tache 4 : produits (cartes 6 a 8), production (9 a 11) et tableau vendu par produit.

Dates en 2031 pour ne jamais croiser les donnees reelles de la base de dev. Les cartes d'etat
(comptage, seuil, lots) portent sur toute la base : les tests y comparent avec l'ecran d'origine
ou cherchent leurs propres produits.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from controller.fabrication_controller import FabricationController
from controller.reports_controller import ReportsController
from controller.stock_count_controller import get_stock_count_controller
from models.fabrication import FabBatch, FabBatchOutput
from models.pharmacy import Pharmacy
from models.stock_count import StockCount, StockCountLine
from models.stock_reception import (
    ProductionLot, StockAdjustmentRequest, StockReceipt, StockReceiptLine,
)
from repositories.audit_repo import AuditRepository
from repositories.fabrication_repo import FabricationRepository
from tests.conftest import create_test_transaction, create_test_user

DAY = date(2031, 5, 6)
# 10:00 a Douala (UTC+1) = 09:00 UTC naif
IN_UTC = datetime(2031, 5, 6, 9, 0)
OUT_UTC = datetime(2031, 5, 8, 9, 0)
IN_LOCAL = datetime(2031, 5, 6, 10, 0)
OUT_LOCAL = datetime(2031, 5, 8, 10, 0)


def _r(p="t"):
    return f"{p}_{uuid.uuid4().hex[:8]}"


def _promo(db):
    return create_test_user(db, _r("rp_promo"), "promoteur")


def _ctrl(db, user=None):
    return ReportsController(db, user or _promo(db))


def _product(db, name=None, qty=1000, threshold=0, mtype="pharmaceutique"):
    p = Pharmacy(drug_name=name or _r("RPP"), quantity=qty, threshold=threshold,
                 medication_type=mtype, forme="Autre", price=0, stock_status="normal")
    db.add(p)
    db.flush()
    return p


def _sale(db, user, lines, paid_at=IN_LOCAL, status=None):
    items = [{"item_type": t, "item_ref_id": ref, "unit_price": amt / q, "quantity": q,
              "line_total": amt} for t, ref, q, amt in lines]
    total = sum(l[3] for l in lines)
    tx = create_test_transaction(db, user, amount=total, advance_amount=total, items=items)
    db.execute(text("UPDATE caisse SET paid_at=:p WHERE transaction_id=:t"),
               {"p": paid_at, "t": tx.transaction_id})
    if status is not None:
        db.execute(text("UPDATE caisse SET status=:s WHERE transaction_id=:t"),
                   {"s": status, "t": tx.transaction_id})
    db.flush()
    db.expire_all()
    return tx


def _receipt(db, user, product, qty, status="valide", controlled_at=IN_UTC, lot=None):
    r = StockReceipt(receipt_number=_r("REC")[:30], origin="fabrication" if lot else "fournisseur",
                     production_lot_id=lot.id if lot else None, received_date=DAY, status=status,
                     created_by=user.user_id, controlled_by=user.user_id if status != "a_controler" else None,
                     controlled_at=controlled_at if status != "a_controler" else None)
    r.lines = [StockReceiptLine(product_id=product.medication_id, qty_good=qty)]
    db.add(r)
    db.flush()
    return r


def _reappro(db, user, product, qty, status="approuve", decided_at=IN_UTC, kind="reapprovisionnement"):
    a = StockAdjustmentRequest(product_id=product.medication_id, kind=kind, quantity=qty,
                               reason="test", status=status, requested_by=user.user_id,
                               requested_at=decided_at - timedelta(hours=1),
                               decided_by=user.user_id if status != "en_attente" else None,
                               decided_at=decided_at if status != "en_attente" else None)
    db.add(a)
    db.flush()
    return a


def _batch(db, user, product, status="termine", qty_good=100, **kw):
    b = FabBatch(batch_number=_r("RB")[:30], product_id=product.medication_id, status=status,
                 production_date=DAY, qty_good=qty_good, created_by=user.user_id,
                 cancel_reason="test" if status == "annule" else None, **kw)
    db.add(b)
    db.flush()
    return b


def _fab(db, user):
    return FabricationController(FabricationRepository(db), AuditRepository(db), user)


# --- carte 6 : vendu contre recu ------------------------------------------------------------
def test_sold_vs_received_known_dataset(db_session):
    db = db_session
    u = _promo(db)
    p = _product(db)
    for q in (10, 20, 30):
        _receipt(db, u, p, q)
    _receipt(db, u, p, 500, status="rejete")
    _receipt(db, u, p, 700, status="a_controler")
    _receipt(db, u, p, 900, controlled_at=OUT_UTC)
    _reappro(db, u, p, 7)
    _reappro(db, u, p, 400, status="refuse")
    _reappro(db, u, p, 400, kind="correction")
    # lot expedie recu par une reception validee : compte une seule fois
    lot = ProductionLot(lot_number=_r("LOT")[:30], product_id=p.medication_id, quantity_produced=40,
                        production_date=DAY, status="recu", created_by=u.user_id)
    db.add(lot)
    db.flush()
    _receipt(db, u, p, 40, lot=lot)
    # ventes : active comptee ; annulee, en attente, hors periode et non stock exclues
    _sale(db, u, [("Médicament", p.medication_id, 3, 300), ("Service", 1, 9, 900)])
    _sale(db, u, [("Médicament", p.medication_id, 5, 500)], status="cancelled")
    _sale(db, u, [("Médicament", p.medication_id, 6, 600)], status="pending_approval")
    _sale(db, u, [("Médicament", p.medication_id, 8, 800)], paid_at=OUT_LOCAL)

    card = _ctrl(db, u).products(DAY, DAY)["sold_vs_received"]
    assert card["id"] == "sold_vs_received" and card["formula_key"]
    assert card["sold"] == 3
    assert card["received"] == 10 + 20 + 30 + 7 + 40
    assert card["received_detail"] == {"receipts": 100, "reapprovisionnement": 7}
    total = db.execute(text("SELECT COALESCE(SUM(quantity),0) FROM pharmacy")).scalar()
    assert card["system_stock"] == int(total)


# --- carte 7 : comptage ---------------------------------------------------------------------
def test_stock_count_card_matches_stock_count_status(db_session):
    db = db_session
    u = _promo(db)
    never = _product(db, name="000_RP_NEVER_" + _r())
    late = _product(db, name="000_RP_LATE_" + _r())
    fresh = _product(db, name="000_RP_FRESH_" + _r())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    c_old = StockCount(scope="selection", status="valide", started_by=u.user_id,
                       started_at=now - timedelta(days=400), submitted_at=now - timedelta(days=400))
    c_new = StockCount(scope="selection", status="valide", started_by=u.user_id,
                       started_at=now - timedelta(days=1), submitted_at=now - timedelta(days=1))
    db.add_all([c_old, c_new])
    db.flush()
    pending = _reappro(db, u, late, 3, status="en_attente", kind="correction",
                       decided_at=now - timedelta(days=3))
    db.add_all([StockCountLine(count_id=c_old.id, product_id=late.medication_id, counted_qty=1,
                               previous_qty=4, difference=-3, counted_at=now - timedelta(days=400),
                               adjustment_request_id=pending.id),
                StockCountLine(count_id=c_new.id, product_id=fresh.medication_id, counted_qty=1,
                               previous_qty=1, difference=0, counted_at=now - timedelta(days=1))])
    db.flush()

    card = _ctrl(db, u).products(DAY, DAY)["stock_count"]
    ref = get_stock_count_controller(db, u).status()
    assert card["counts"] == ref["counts"] and card["interval_days"] == ref["interval_days"]
    rows = {r["product_id"]: r for r in card["products"]}
    assert len(card["products"]) <= 20
    assert never.medication_id in rows and rows[never.medication_id]["status"] == "jamais_compte"
    assert late.medication_id in rows and rows[late.medication_id]["status"] == "en_retard"
    assert rows[late.medication_id]["days_since"] >= 399
    assert fresh.medication_id not in rows
    assert card["pending_requests"]["count"] >= 1
    assert card["pending_requests"]["oldest_days"] >= 3


# --- carte 8 : sous le seuil ----------------------------------------------------------------
def test_low_stock_uses_stock_list_rule(db_session):
    db = db_session
    u = _promo(db)
    at = _product(db, name="000_RP_AT_" + _r(), qty=5, threshold=5)
    under = _product(db, name="000_RP_UNDER_" + _r(), qty=2, threshold=5)
    above = _product(db, name="000_RP_ABOVE_" + _r(), qty=6, threshold=5)
    card = _ctrl(db, u).products(DAY, DAY)["low_stock"]
    # regle de l'ecran Stock (badge BAS) : quantity <= threshold
    expected = db.execute(text("SELECT COUNT(*) FROM pharmacy WHERE quantity <= threshold")).scalar()
    assert card["total"] == expected and card["rule_key"]
    ids = [r["product_id"] for r in card["products"]]
    assert len(ids) <= 20
    assert at.medication_id in ids and under.medication_id in ids
    assert above.medication_id not in ids


# --- carte 9 : lots --------------------------------------------------------------------------
def test_batches_card_matches_fabrication(db_session):
    db = db_session
    u = _promo(db)
    p = _product(db, mtype="Naturel")
    stale = _batch(db, u, p, status="en_production", qty_good=0,
                   started_at=datetime.utcnow() - timedelta(days=365))
    card = _ctrl(db, u).production(DAY, DAY)["batches"]
    fab = _fab(db, u)
    assert card["counts_by_status"] == fab.summary()["counts_by_status"]
    assert card["stale_days"] == fab.get_settings()["stale_days"]
    refs = [a["ref"] for a in fab.list_anomalies() if a["kind"] == "lot_trop_long"]
    assert [s["batch_number"] for s in card["stale"]] == refs[:20]
    assert card["stale_total"] == len(refs)
    assert stale.batch_number in refs


# --- carte 10 : bouteilles ------------------------------------------------------------------
def test_bottles_outputs_by_reason_and_shipped(db_session):
    db = db_session
    u = _promo(db)
    p = _product(db, mtype="Naturel")
    b1 = _batch(db, u, p, qty_good=100, finished_at=IN_UTC)
    _batch(db, u, p, qty_good=999, finished_at=OUT_UTC)
    _batch(db, u, p, status="annule", qty_good=555, finished_at=IN_UTC)
    for reason, q, st in (("echantillon", 4, "active"), ("echantillon", 6, "active"),
                          ("autre", 3, "active"), ("autre", 50, "annulee")):
        db.add(FabBatchOutput(batch_id=b1.id, reason=reason, quantity=q, status=st,
                              note="x" if reason == "autre" else None, declared_by=u.user_id,
                              declared_at=IN_UTC,
                              cancelled_by=u.user_id if st == "annulee" else None,
                              cancelled_at=IN_UTC if st == "annulee" else None,
                              cancel_reason="x" if st == "annulee" else None))
    lot = ProductionLot(lot_number=_r("LOT")[:30], product_id=p.medication_id, quantity_produced=77,
                        production_date=DAY, status="produit", created_by=u.user_id)
    db.add(lot)
    db.flush()
    _batch(db, u, p, status="expedie", qty_good=80, finished_at=OUT_UTC - timedelta(days=30),
           production_lot_id=lot.id, expedited_at=IN_UTC)
    db.flush()
    card = _ctrl(db, u).production(DAY, DAY)["bottles"]
    assert card["produced"] == 100
    assert card["outputs"] == {"echantillon": 10, "autre": 3}
    assert card["shipped"] == 77


# --- carte 11 : manque et cout ----------------------------------------------------------------
def test_loss_and_cost_equal_fabrication(db_session):
    db = db_session
    u = _promo(db)
    p = _product(db, mtype="Naturel")
    lot = ProductionLot(lot_number=_r("LOT")[:30], product_id=p.medication_id, quantity_produced=90,
                        production_date=DAY, status="produit", created_by=u.user_id)
    db.add(lot)
    db.flush()
    b = _batch(db, u, p, status="expedie", qty_good=90, expected_qty=100, found_qty=90,
               missing_qty=10, missing_pct=Decimal("10.00"), tolerance_applied=Decimal("2.00"),
               out_of_tolerance=True, justification="fuite", total_cost=Decimal("4500.00"),
               unit_cost=Decimal("50.00"), production_lot_id=lot.id, expedited_at=IN_UTC)
    card = _ctrl(db, u).production(DAY, DAY)["loss_and_cost"]
    fab = _fab(db, u)
    ref = [a for a in fab.list_anomalies() if a["kind"] == "hors_tolerance"]
    oot = card["out_of_tolerance"]
    assert oot["current_state"] is True and oot["as_of"].endswith("+00:00")
    assert card["current_state"] is False
    assert oot["total"] == len(ref)
    row = next(r for r in oot["items"] if r["batch_number"] == b.batch_number) \
        if len(ref) <= 20 else None
    if row is not None:
        assert row["missing_qty"] == 10 and row["missing_pct"] == "10.00"
    costs = {c["product_id"]: c for c in card["cost_per_good_bottle"]}
    want = fab.cost_by_product(p.medication_id)
    assert costs[p.medication_id]["average_unit_cost"] == str(want["average_unit_cost"])
    assert costs[p.medication_id]["last_unit_cost"] == str(want["last_unit_cost"])
    assert card["period_average_unit_cost"] == "50.00"
    assert card["cost_per_good_bottle_scope"] == "all_time"
    assert card["period_average_unit_cost_scope"] == "period"


# --- tableau vendu par produit ----------------------------------------------------------------
@pytest.fixture
def table(db_session):
    db = db_session
    u = _promo(db)
    tag = uuid.uuid4().hex[:6]
    para = _product(db, name=f"Paracetamol {tag}", mtype="pharmaceutique")
    cafe = _product(db, name=f"Café vert {tag}", mtype="Naturel")
    ibu = _product(db, name=f"Ibuprofene {tag}", mtype="pharmaceutique")
    _sale(db, u, [("Médicament", para.medication_id, 2, 200), ("Médicament", cafe.medication_id, 5, 100)])
    _sale(db, u, [("Médicament", para.medication_id, 1, 100), ("Médicament", ibu.medication_id, 1, 900)])
    _sale(db, u, [("Médicament", ibu.medication_id, 50, 5000)], status="cancelled")
    _sale(db, u, [("Examen", 1, 1, 1500), ("Consultation Medical", 1, 2, 4000)])
    return {"db": db, "u": u, "tag": tag, "para": para, "cafe": cafe, "ibu": ibu,
            "c": _ctrl(db, u)}


def test_table_partial_and_accent_insensitive_name(table):
    c = table["c"]
    r = c.sold_by_product(DAY, DAY, q="para")
    assert [i["product_id"] for i in r["items"]] == [table["para"].medication_id] and r["total"] == 1
    assert r["items"][0]["quantity"] == 3 and r["items"][0]["amount"] == "300.00"
    assert r["items"][0]["category"] == "pharmaceutique"
    r = c.sold_by_product(DAY, DAY, q="CAFE")
    assert [i["product_id"] for i in r["items"]] == [table["cafe"].medication_id]
    r = c.sold_by_product(DAY, DAY, q="café")
    assert [i["product_id"] for i in r["items"]] == [table["cafe"].medication_id]


def test_table_type_and_category_filters(table):
    c = table["c"]
    r = c.sold_by_product(DAY, DAY)
    assert r["total"] == 3   # medicaments seulement, vente annulee exclue
    ibu = next(i for i in r["items"] if i["product_id"] == table["ibu"].medication_id)
    assert ibu["quantity"] == 1 and ibu["amount"] == "900.00"
    r = c.sold_by_product(DAY, DAY, category="Naturel")
    assert [i["product_id"] for i in r["items"]] == [table["cafe"].medication_id]
    r = c.sold_by_product(DAY, DAY, item_type="Consultation")
    assert r["total"] == 1 and r["items"][0]["quantity"] == 2 and r["items"][0]["amount"] == "4000.00"
    r = c.sold_by_product(DAY, DAY, item_type="Examen")
    assert r["total"] == 1 and r["items"][0]["amount"] == "1500.00"
    assert c.sold_by_product(DAY, DAY, item_type="Service")["total"] == 0


def test_table_sorts(table):
    c = table["c"]
    para, cafe, ibu = (table[k].medication_id for k in ("para", "cafe", "ibu"))
    ids = lambda s: [i["product_id"] for i in c.sold_by_product(DAY, DAY, sort=s)["items"]]
    assert ids("amount_desc") == [ibu, para, cafe]
    assert ids("amount_asc") == [cafe, para, ibu]
    assert ids("quantity_desc") == [cafe, para, ibu]
    assert ids("quantity_asc") == [ibu, para, cafe]
    assert ids("name_asc") == [cafe, ibu, para]


def test_table_pagination_and_validation(table):
    c = table["c"]
    r = c.sold_by_product(DAY, DAY, limit=2, offset=0)
    assert len(r["items"]) == 2 and r["total"] == 3 and r["limit"] == 2 and r["offset"] == 0
    r = c.sold_by_product(DAY, DAY, limit=2, offset=2)
    assert len(r["items"]) == 1 and r["total"] == 3
    r = c.sold_by_product(DAY, DAY, limit=2, offset=10)
    assert r["items"] == [] and r["total"] == 3
    for kw in ({"sort": "bad"}, {"limit": 0}, {"limit": 201}, {"offset": -1},
               {"item_type": "Carnet"}):
        with pytest.raises(ValueError):
            c.sold_by_product(DAY, DAY, **kw)


# --- droits ------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["secretaire", "StockController", "ProductionManager"])
def test_other_roles_refused(db_session, role):
    c = _ctrl(db_session, create_test_user(db_session, _r("rp_x"), role))
    for call in (lambda: c.products(DAY, DAY), lambda: c.production(DAY, DAY),
                 lambda: c.sold_by_product(DAY, DAY)):
        with pytest.raises(PermissionError):
            call()


# --- correctifs de relecture ------------------------------------------------------------------
def test_current_state_markers(db_session):
    c = _ctrl(db_session)
    prod, fab = c.products(DAY, DAY), c.production(DAY, DAY)
    for card in (prod["stock_count"], prod["low_stock"], fab["batches"]):
        assert card["current_state"] is True
        assert card["as_of"].endswith("+00:00")
        assert datetime.fromisoformat(card["as_of"]).utcoffset() == timedelta(0)
    for card in (prod["sold_vs_received"], fab["bottles"], fab["loss_and_cost"]):
        assert card["current_state"] is False and "as_of" not in card
    assert "quantity <= threshold" in prod["low_stock"]["rule_text"]
    assert "stock_status" in prod["low_stock"]["rule_text"]


def test_table_amount_basis_and_note(table):
    r = table["c"].sold_by_product(DAY, DAY)
    assert r["amount_basis"] == "reports.table.amount_before_discount"
    assert r["note_key"]


def test_table_deleted_product_label(db_session):
    u = _promo(db_session)
    p = _product(db_session, name="Gone " + _r())
    tx = _sale(db_session, u, [("Médicament", p.medication_id, 1, 100)])
    db_session.execute(text("UPDATE caisse_item SET item_ref_id=999999901 WHERE transaction_id=:t"),
                       {"t": tx.transaction_id})
    r = _ctrl(db_session, u).sold_by_product(DAY, DAY)
    assert [i["name"] for i in r["items"]] == ["(produit supprime #999999901)"]
    assert r["items"][0]["product_id"] is None


def test_table_ligatures_literals_and_same_names(db_session):
    u = _promo(db_session)
    tag = uuid.uuid4().hex[:6]
    coeur = _product(db_session, name=f"Sœur CŒUR {tag}")
    pct = _product(db_session, name=f"Remise 50% {tag}")
    und = _product(db_session, name=f"a_b {tag}")
    bsl = _product(db_session, name=f"c\\d {tag}")
    plain = _product(db_session, name=f"axb 50x {tag}")
    twin1 = _product(db_session, name=f"Twin {tag}")
    twin2 = _product(db_session, name=f"Twin {tag}")
    _sale(db_session, u, [("Médicament", x.medication_id, 1, 10)
                          for x in (coeur, pct, und, bsl, plain, twin1, twin2)])
    c = _ctrl(db_session, u)

    def ids(q):
        return sorted(i["product_id"] for i in c.sold_by_product(DAY, DAY, q=q)["items"])
    assert ids("soeur") == [coeur.medication_id]
    assert ids("coeur") == [coeur.medication_id]
    assert ids("oe") == [coeur.medication_id]
    assert ids("%") == [pct.medication_id]
    assert ids("_") == [und.medication_id]
    assert ids("\\") == [bsl.medication_id]
    assert ids("Twin") == sorted([twin1.medication_id, twin2.medication_id])
    with pytest.raises(ValueError):
        c.sold_by_product(DAY, DAY, q="x" * 101)
    assert c.sold_by_product(DAY, DAY, q="x" * 100)["total"] == 0
