# tests/test_stock_item_types.py
"""Une seule regle 'cette ligne touche au stock' pour vente / modification / annulation."""
import pytest
from sqlalchemy import text

from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from repositories.caisse_repo import CaisseRepository
from tests.conftest import create_test_user
from utils.item_types import touches_stock


@pytest.mark.parametrize("label", [
    "Vente Médicament", "Médicament", "Sale Medication", "medication",
    "Vente Carnet", "Carnet", "booklet"])
def test_touches_stock_true(label):
    assert touches_stock(label) is True


@pytest.mark.parametrize("label", [
    "Examens", "Examen", "Consultation Spirituel", "Consultation Médical",
    "Désintox", "Service", None, ""])
def test_touches_stock_false(label):
    assert touches_stock(label) is False


def _product(db, qty=20, name="TEST_ITEMTYPE_PROD"):
    p = Pharmacy(drug_name=name, quantity=qty, threshold=1, medication_type="pharmaceutique",
                 forme="Autre", price=10, stock_status="normal")
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p


def _stored(db, pid):
    return db.execute(text("SELECT quantity FROM pharmacy WHERE medication_id = :id"), {"id": pid}).scalar()


def _line(label, pid, qty):
    return {"item_type": label, "item_ref_id": pid, "unit_price": 10, "quantity": qty, "line_total": 10 * qty}


def _sale(repo, user, lines):
    total = sum(l["line_total"] for l in lines)
    return repo.create_transaction({"amount": total, "advance_amount": 0, "payment_method": "Especes",
                                    "transaction_type": "Vente", "patient_label": "X", "items": lines}, user)


@pytest.mark.parametrize("label", ["Vente Médicament", "Sale Medication", "Vente Carnet"])
def test_sale_edit_cancel_touch_stock(db_session, label):
    user = create_test_user(db_session, "t_itype_" + label[:4].lower().strip(), "secretaire")
    p = _product(db_session)
    repo = CaisseRepository(db_session)
    tx = _sale(repo, user, [_line(label, p.medication_id, 2)])
    assert _stored(db_session, p.medication_id) == 18          # creation
    repo.update_transaction(tx.transaction_id, {"items": [_line(label, p.medication_id, 5)]}, user)
    assert _stored(db_session, p.medication_id) == 15          # ecart de 3
    repo.cancel_transaction(tx.transaction_id, user, "test")
    assert _stored(db_session, p.medication_id) == 20          # tout remis
    mv = db_session.query(StockMovement).filter_by(
        medication_id=p.medication_id, movement_type="ANNULATION_VENTE").one()
    assert mv.change_qty == 5


def test_examen_never_touches_stock(db_session):
    # Une ligne stock sur p2 accompagne l'Examen (p) : annuler une facture sans
    # AUCUNE ligne stock echoue deja en base (trigger fn_caisse_protect_cancelled,
    # bug preexistant hors perimetre, signale dans le rapport).
    user = create_test_user(db_session, "t_itype_exam", "secretaire")
    p = _product(db_session)
    p2 = _product(db_session, name="TEST_ITEMTYPE_PROD2")
    repo = CaisseRepository(db_session)
    tx = _sale(repo, user, [_line("Examen", p.medication_id, 2), _line("Vente Médicament", p2.medication_id, 1)])
    assert _stored(db_session, p.medication_id) == 20
    assert _stored(db_session, p2.medication_id) == 19
    repo.update_transaction(tx.transaction_id, {"items": [_line("Examen", p.medication_id, 5),
                                                        _line("Vente Médicament", p2.medication_id, 1)]}, user)
    assert _stored(db_session, p.medication_id) == 20
    assert _stored(db_session, p2.medication_id) == 19
    repo.cancel_transaction(tx.transaction_id, user, "test")
    assert _stored(db_session, p.medication_id) == 20
    assert _stored(db_session, p2.medication_id) == 20
    assert db_session.query(StockMovement).filter_by(
        medication_id=p.medication_id, movement_type="ANNULATION_VENTE").count() == 0
