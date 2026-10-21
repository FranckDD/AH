# tests/test_stock_write_locks.py
"""Regle R7 : caisse et pharmacie doivent relire le stock sous verrou (valeur FRAICHE).

Scenario simule sans seconde connexion : la session charge le produit (identity map
a 10), puis la ligne est modifiee derriere l'ORM par du SQL brut (= validation d'une
reception commitee ailleurs, +100). L'ecriture suivante doit partir de 110, pas de 10.
"""
from sqlalchemy import text

from models.pharmacy import Pharmacy
from repositories.caisse_repo import CaisseRepository
from repositories.pharmacy_repo import PharmacyRepository
from tests.conftest import create_test_user


def _product(db, qty=10, name="TEST_LOCK_PROD"):
    p = Pharmacy(drug_name=name, quantity=qty, threshold=5, medication_type="pharmaceutique",
                 forme="Autre", price=10, stock_status="normal")
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p


def _bump_behind_orm(db, pid, qty):
    db.execute(text("UPDATE pharmacy SET quantity = :q WHERE medication_id = :id"), {"q": qty, "id": pid})


def _stored(db, pid):
    return db.execute(text("SELECT quantity FROM pharmacy WHERE medication_id = :id"), {"id": pid}).scalar()


def _sale(repo, user, lines):
    total = sum(l["line_total"] for l in lines)
    return repo.create_transaction({"amount": total, "advance_amount": 0, "payment_method": "Especes",
                                    "transaction_type": "Vente", "patient_label": "X", "items": lines}, user)


def _line(pid, qty=1):
    return {"item_type": "médicament", "item_ref_id": pid, "unit_price": 10, "quantity": qty, "line_total": 10 * qty}


def test_sale_uses_fresh_quantity(db_session):
    user = create_test_user(db_session, "t_lock_sale", "secretaire")
    p = _product(db_session)
    assert p.quantity == 10  # identity map
    _bump_behind_orm(db_session, p.medication_id, 110)
    _sale(CaisseRepository(db_session), user, [_line(p.medication_id)])
    assert _stored(db_session, p.medication_id) == 109


def test_sale_edit_uses_fresh_quantity(db_session):
    user = create_test_user(db_session, "t_lock_edit", "secretaire")
    p = _product(db_session)
    p2 = _product(db_session, name="TEST_LOCK_PROD2")
    repo = CaisseRepository(db_session)
    tx = _sale(repo, user, [_line(p.medication_id)])  # 10 -> 9
    db_session.get(Pharmacy, p.medication_id)  # identity map tient 9
    _bump_behind_orm(db_session, p.medication_id, 109)
    # edition : restitue 1 puis revend 2 (+ une ligne d'un autre produit)
    repo.update_transaction(tx.transaction_id, {"items": [_line(p2.medication_id), _line(p.medication_id, 2)]}, user)
    assert _stored(db_session, p.medication_id) == 108
    assert _stored(db_session, p2.medication_id) == 9


def test_cancel_restock_uses_fresh_quantity(db_session):
    user = create_test_user(db_session, "t_lock_cancel", "secretaire")
    p = _product(db_session)
    repo = CaisseRepository(db_session)
    tx = _sale(repo, user, [_line(p.medication_id)])  # 10 -> 9
    db_session.get(Pharmacy, p.medication_id)
    _bump_behind_orm(db_session, p.medication_id, 109)
    repo.cancel_transaction(tx.transaction_id, user, "erreur de saisie")
    assert _stored(db_session, p.medication_id) == 110


def test_renew_uses_fresh_quantity(db_session):
    user = create_test_user(db_session, "t_lock_renew", "admin")
    p = _product(db_session)
    _bump_behind_orm(db_session, p.medication_id, 110)
    PharmacyRepository(db_session).renew_stock(p.medication_id, 5, user)
    assert _stored(db_session, p.medication_id) == 115


def test_update_quantity_uses_fresh_row(db_session):
    """update() avec 'quantity' : le mouvement doit refleter l'ecart vs la valeur FRAICHE."""
    from models.stock_movement import StockMovement
    user = create_test_user(db_session, "t_lock_upd", "admin")
    p = _product(db_session)
    _bump_behind_orm(db_session, p.medication_id, 110)
    PharmacyRepository(db_session).update(p.medication_id, {"quantity": 120}, user)
    assert _stored(db_session, p.medication_id) == 120
    mv = db_session.query(StockMovement).filter_by(medication_id=p.medication_id, movement_type="update").one()
    assert mv.change_qty == 10
