# tests/test_stock_domain_fixes.py
"""Defauts du stock releves par les guides (2026-10-26) : issue des demandes d'ajustement du comptage,
liste des demandes du controleur, auteur par nom complet."""
from tests.test_stock_count_controller import _ctrl, _product, _stock_ctrl, users  # noqa: F401


def _count_with_gap(db, users, qty_sys=10, counted=8):
    p = _product(db, qty_sys)
    ctrl = _ctrl(db, users["ctrl"])
    c = ctrl.start()
    out = ctrl.submit(c["id"], [{"product_id": p.medication_id, "counted_qty": counted}])
    return p, c, out["lines"][0]


def test_detail_du_comptage_donne_l_issue_de_la_demande(db_session, users):
    p, c, line = _count_with_gap(db_session, users)
    ctrl = _ctrl(db_session, users["ctrl"])
    assert ctrl.get(c["id"])["lines"][0]["adjustment_status"] == "en_attente"
    _stock_ctrl(db_session, users["admin"]).approve_adjustment(line["adjustment_request_id"])
    assert ctrl.get(c["id"])["lines"][0]["adjustment_status"] == "approuve"


def test_detail_du_comptage_distingue_refuse_et_remplace(db_session, users):
    p, c, line = _count_with_gap(db_session, users)
    _stock_ctrl(db_session, users["admin"]).reject_adjustment(line["adjustment_request_id"], "non")
    ctrl = _ctrl(db_session, users["ctrl"])
    row = ctrl.get(c["id"])["lines"][0]
    assert row["adjustment_status"] == "refuse" and row["adjustment_decision_note"] == "non"
    # nouveau comptage du meme produit avec ecart : la demande en attente d'un comptage precedent est remplacee
    p2, c2, line2 = _count_with_gap(db_session, users)
    c3 = ctrl.start()
    ctrl.submit(c3["id"], [{"product_id": p2.medication_id, "counted_qty": 7}])
    assert ctrl.get(c2["id"])["lines"][0]["adjustment_status"] == "remplace"


def test_le_controleur_liste_ses_propres_demandes_seulement(db_session, users):
    p, c, line = _count_with_gap(db_session, users)
    mine = _ctrl(db_session, users["ctrl"]).my_requests()
    assert [r["id"] for r in mine["items"] if r["id"] == line["adjustment_request_id"]] == [line["adjustment_request_id"]]
    row = next(r for r in mine["items"] if r["id"] == line["adjustment_request_id"])
    assert row["number"] == f"AJU-{row['id']}" and row["status"] == "en_attente" and row["product_name"] == p.drug_name
    others = _ctrl(db_session, users["ctrl2"]).my_requests()
    assert all(r["id"] != line["adjustment_request_id"] for r in others["items"])


def test_mouvements_montrent_le_nom_complet_et_une_heure_utc_explicite(db_session, users):
    from datetime import datetime
    from models.stock_movement import StockMovement
    from repositories.audit_repo import AuditRepository
    from repositories.notification_repo import NotificationRepository
    from repositories.stock_repo import StockRepository
    from controller.stock_controller import StockController
    p = _product(db_session, 5)
    db_session.add(StockMovement(medication_id=p.medication_id, change_qty=3, movement_type="reception", note="x",
                                 created_by=users["ctrl"].username, created_at=datetime(2026, 10, 26, 9, 0, 0)))
    db_session.add(StockMovement(medication_id=p.medication_id, change_qty=1, movement_type="update", note="y",
                                 created_by="login_inconnu", created_at=datetime(2026, 10, 26, 8, 0, 0)))
    db_session.flush()
    ctrl = StockController(StockRepository(db_session), NotificationRepository(db_session), AuditRepository(db_session), users["admin"])
    out = ctrl.list_movements(product_id=p.medication_id)
    first, second = out["items"][0], out["items"][1]
    assert first["created_by_name"] == users["ctrl"].full_name and first["created_by"] == users["ctrl"].username
    assert second["created_by_name"] == "login_inconnu"  # repli sur l'identifiant si aucun utilisateur
    assert first["created_at"] == "2026-10-26T09:00:00Z"


def _receipt_env(db):
    from tests.test_stock_receipts import _r9_receipt, users as _u  # noqa: F401
    return _r9_receipt


def test_correction_de_ligne_refusee_donne_un_code_la_ligne_et_les_parametres(db_session):
    import pytest
    from controller.stock_controller import StockLineError
    from tests.test_stock_receipts import _r9_receipt
    from tests.conftest import create_test_user
    users = {"assistant": create_test_user(db_session, "t_sdf_assist", "Assistant"),
             "controller": create_test_user(db_session, "t_sdf_ctrl", "StockController")}
    p, r, lid, c = _r9_receipt(db_session, users, qty_good=5, qty_expected=1000)
    with pytest.raises(StockLineError) as e:
        c.update_receipt_lines(r["id"], [{"id": lid, "qty_good": 900}])
    assert e.value.code == "line_total_increase" and e.value.line_id == lid
    assert e.value.params == {"current": 5, "requested": 900}
    with pytest.raises(StockLineError) as e:
        c.update_receipt_lines(r["id"], [{"id": lid + 999999, "qty_good": 1}])
    assert e.value.code == "line_missing" and e.value.line_id == lid + 999999


def test_le_routeur_sert_le_code_en_detail_structure():
    import pytest
    from fastapi import HTTPException
    from api_backend.backend_app.routes.stock.stock_endpoints import _errors
    from controller.stock_controller import StockLineError
    with pytest.raises(HTTPException) as e:
        with _errors():
            raise StockLineError("line_total_increase", "Ligne 4 : ...", line_id=4, params={"current": 5, "requested": 9})
    assert e.value.status_code == 422
    assert e.value.detail == {"code": "line_total_increase", "line_id": 4, "params": {"current": 5, "requested": 9},
                              "message": "Ligne 4 : ..."}
