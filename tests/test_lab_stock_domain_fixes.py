# tests/test_lab_stock_domain_fixes.py
"""Defauts du stock labo releves par les guides (2026-10-26)."""
from datetime import timedelta

from models.lab_stock import LabStockMovement, LabStockRequest
from tests.test_lab_stock_counts_alerts import (  # noqa: F401  (fixture env et aides partagees)
    TODAY, _count, _ctrl, _open_req, _receive, env,
)


def test_comptage_a_valeur_inchangee_ne_cree_pas_de_mouvement_nul(env):
    db, a, b = env["db"], env["a"], env["b"]
    _receive(env, a["id"], 10, TODAY + timedelta(days=300), "TEST_LSDF_F1")
    r = _count(env, [{"product_id": a["id"], "previous_qty": 10, "counted_qty": 10},
                     {"product_id": b["id"], "previous_qty": 0, "counted_qty": 0}])
    assert r.status_code == 200, r.text
    out = r.json()
    assert len(out["applied"]) == 2  # le comptage est bien enregistre pour les deux produits
    assert db.query(LabStockMovement).filter_by(ref_type="count", ref_id=out["count_id"]).count() == 0


def test_produit_cree_a_zero_sous_son_seuil_a_une_demande_seuil(env):
    db = env["db"]
    # env["a"] : seuil 5, stock 0 -> demande ouverte des la creation ; env["b"] : seuil 0 -> aucune
    req = _open_req(db, env["a"]["id"])
    assert req is not None and req.origin == "seuil"
    assert _open_req(db, env["b"]["id"]) is None


def test_lot_proche_de_peremption_cree_une_demande_peremption(env):
    db, a = env["db"], env["a"]
    _receive(env, a["id"], 50, TODAY + timedelta(days=10), "TEST_LSDF_F2")
    # la reception ferme la demande seuil ; le stock (50) est au-dessus du seuil (5)
    assert _open_req(db, a["id"]) is None
    alerts = _ctrl(db, env["u"]["lab"]).get_alerts(TODAY)
    assert any(e["product_id"] == a["id"] for e in alerts["expiring"])
    req = _open_req(db, a["id"])
    assert req is not None and req.origin == "peremption" and req.status == "a_commander"
    # une seconde lecture ne duplique rien
    _ctrl(db, env["u"]["lab"]).get_alerts(TODAY)
    assert db.query(LabStockRequest).filter_by(product_id=a["id"], origin="peremption").count() == 1


def test_alerte_de_peremption_donne_la_quantite_recue_et_le_stock_du_produit(env):
    db, a = env["db"], env["a"]
    _receive(env, a["id"], 50, TODAY + timedelta(days=10), "TEST_LSDF_F3")
    alerts = _ctrl(db, env["u"]["lab"]).get_alerts(TODAY)
    e = next(x for x in alerts["expiring"] if x["product_id"] == a["id"])
    assert e["received_qty"] == 50 and e["product_quantity"] == 50
