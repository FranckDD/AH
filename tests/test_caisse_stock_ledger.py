# tests/test_caisse_stock_ledger.py
"""Registre de stock complet : la modification d'une vente avec lignes
ecrit un mouvement NET par produit (2026-10-24, comptage de stock).

Propriete : quantite de depart + SUM(change_qty) == quantite finale."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import func

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from api_backend.backend_app.routes.discount import discount_endpoints
from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from tests.conftest import create_test_user, auth_headers

PWD = "Correct123!"
PRICE = 250.0


@pytest.fixture
def ctx(db_session, api_client):
    create_test_user(db_session, "sl_sec", "secretaire", password=PWD)
    a = Pharmacy(drug_name="SL Produit A", quantity=50, threshold=1, medication_type="comprime", price=PRICE)
    b = Pharmacy(drug_name="SL Produit B", quantity=50, threshold=1, medication_type="comprime", price=PRICE)
    db_session.add_all([a, b])
    db_session.flush()
    client = api_client(auth_endpoints, caisse_endpoints, discount_endpoints)
    return {"client": client, "h": auth_headers(client, "sl_sec", PWD), "a": a, "b": b, "db": db_session}


def _line(ref, qty):
    return {"item_type": "Médicament", "item_ref_id": ref, "unit_price": PRICE, "quantity": qty,
            "line_total": PRICE * qty}


def _create(ctx, lines):
    total = sum(l["line_total"] for l in lines)
    r = ctx["client"].post("/caisse/", json={"payment_method": "Especes", "transaction_type": "Vente",
                                             "amount": total, "advance_amount": 0, "items": lines},
                           headers=ctx["h"])
    assert r.status_code == 201, r.text
    return r.json()["transaction_id"]


def _put(ctx, tx_id, lines):
    return ctx["client"].put(f"/caisse/{tx_id}", headers=ctx["h"],
                             json={"items": lines, "amount": sum(l["line_total"] for l in lines)})


def _qty(ctx, med):
    ctx["db"].expire_all()
    return ctx["db"].get(Pharmacy, med.medication_id).quantity


def _edit_moves(ctx, med, tx_id):
    ctx["db"].expire_all()
    return ctx["db"].query(StockMovement).filter(
        StockMovement.medication_id == med.medication_id,
        StockMovement.note == f"Modification de la vente #{tx_id}").all()


def _sum_moves(ctx, med):
    ctx["db"].expire_all()
    return int(ctx["db"].query(func.coalesce(func.sum(StockMovement.change_qty), 0))
               .filter(StockMovement.medication_id == med.medication_id).scalar())


def test_hausse_2_a_5_mouvement_moins_3(ctx):
    a = ctx["a"]
    tx = _create(ctx, [_line(a.medication_id, 2)])
    after_create = _qty(ctx, a)
    r = _put(ctx, tx, [_line(a.medication_id, 5)])
    assert r.status_code == 200, r.text
    assert _qty(ctx, a) == after_create - 3
    moves = _edit_moves(ctx, a, tx)
    assert [m.change_qty for m in moves] == [-3]
    assert moves[0].movement_type == "VENTE"
    assert moves[0].created_by == "sl_sec"


def test_baisse_5_a_2_mouvement_plus_3(ctx):
    a = ctx["a"]
    tx = _create(ctx, [_line(a.medication_id, 5)])
    after_create = _qty(ctx, a)
    r = _put(ctx, tx, [_line(a.medication_id, 2)])
    assert r.status_code == 200, r.text
    assert _qty(ctx, a) == after_create + 3
    moves = _edit_moves(ctx, a, tx)
    assert [m.change_qty for m in moves] == [3]
    assert moves[0].movement_type == "ANNULATION_VENTE"


def test_quantite_inchangee_aucun_mouvement(ctx):
    a = ctx["a"]
    tx = _create(ctx, [_line(a.medication_id, 4)])
    after_create = _qty(ctx, a)
    r = _put(ctx, tx, [_line(a.medication_id, 4)])
    assert r.status_code == 200, r.text
    assert _qty(ctx, a) == after_create
    assert _edit_moves(ctx, a, tx) == []


def test_changement_de_produit_deux_mouvements(ctx):
    a, b = ctx["a"], ctx["b"]
    tx = _create(ctx, [_line(a.medication_id, 3)])
    qa, qb = _qty(ctx, a), _qty(ctx, b)
    r = _put(ctx, tx, [_line(b.medication_id, 3)])
    assert r.status_code == 200, r.text
    assert _qty(ctx, a) == qa + 3 and _qty(ctx, b) == qb - 3
    assert [m.change_qty for m in _edit_moves(ctx, a, tx)] == [3]
    assert [m.change_qty for m in _edit_moves(ctx, b, tx)] == [-3]


def test_registre_complet_creation_modification_annulation(ctx):
    a = ctx["a"]
    start, start_sum = _qty(ctx, a), _sum_moves(ctx, a)
    tx = _create(ctx, [_line(a.medication_id, 2)])
    assert _put(ctx, tx, [_line(a.medication_id, 7)]).status_code == 200
    assert _put(ctx, tx, [_line(a.medication_id, 1)]).status_code == 200
    assert start + _sum_moves(ctx, a) - start_sum == _qty(ctx, a)
    r = ctx["client"].post(f"/caisse/{tx}/cancel", headers=ctx["h"],
                           json={"cancel_justification": "Erreur de saisie du client, test registre"})
    assert r.status_code == 200, r.text
    assert _qty(ctx, a) == start
    assert start + _sum_moves(ctx, a) - start_sum == _qty(ctx, a)


def test_stock_insuffisant_refuse_sans_ecriture(ctx):
    # En production get_db ferme la session (rien n'est commite) ; le harnais
    # partage la session sans la fermer, on simule donc la fermeture par un
    # rollback (rembobine au savepoint pose apres le commit de la creation).
    a = ctx["a"]
    start, start_sum = _qty(ctx, a), _sum_moves(ctx, a)
    tx = _create(ctx, [_line(a.medication_id, 2)])
    before_qty, before_sum = _qty(ctx, a), _sum_moves(ctx, a)
    r = _put(ctx, tx, [_line(a.medication_id, 500)])
    assert r.status_code == 400, r.text
    assert "Stock insuffisant" in r.json()["detail"]
    ctx["db"].rollback()
    assert _qty(ctx, a) == before_qty == start - 2
    assert _sum_moves(ctx, a) == before_sum == start_sum - 2
    assert _edit_moves(ctx, a, tx) == []
