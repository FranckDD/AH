# tests/test_fabrication_domain_fixes.py
"""Defauts Fabrication releves par les guides (2026-10-26)."""
from decimal import Decimal

from models import FabIntrant, FabIntrantPurchase
from models.notification import Notification
from tests.conftest import create_test_user
from tests.test_fabrication_batches import (  # noqa: F401  (fixture env et aides partagees)
    _batch, _intrant, _purchase, _ready, _remaining, _started, env,
)

TYPE = "fab_intrant_low"


def _low_notifs(db, user, intrant_id):
    db.expire_all()
    return [n for n in db.query(Notification).filter_by(recipient_user_id=user.user_id, type=TYPE).all()
            if n.payload.get("intrant_id") == intrant_id]


def _intrant_of(env, purchase_id):
    return env["db"].get(FabIntrantPurchase, purchase_id).intrant_id


def test_franchissement_du_seuil_notifie_une_seule_fois(env):
    db = env["db"]
    admin = create_test_user(db, "t_fdf_admin", "admin")
    promo = create_test_user(db, "t_fdf_promo", "promoteur")
    b, pc, pl = _ready(env, bottles="120")
    iid = _intrant_of(env, pc)
    db.get(FabIntrant, iid).alert_threshold = Decimal("450")  # stock 500 : pas encore sous le seuil
    db.flush()
    assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 200  # 500 -> 380
    for u in (env["user"], admin, promo):
        assert len(_low_notifs(db, u, iid)) == 1, u.username
    n = _low_notifs(db, env["user"], iid)[0]
    assert n.payload["stock"] in ("380", "380.000", 380) or Decimal(str(n.payload["stock"])) == Decimal("380")
    # deuxieme lot sur le meme contenant : deja sous le seuil -> pas de nouvelle notification
    b2 = _batch(env, [{"purchase_id": pc, "quantity": "50"}])
    pl2 = _purchase(env, _intrant(env), qty="100", cost="1.00")
    assert env["c"].put(f"/fabrication/batches/{b2['id']}", json={"consumptions": [
        {"purchase_id": pc, "quantity": "50"}, {"purchase_id": pl2, "quantity": "10"}]}).status_code == 200
    assert env["c"].post(f"/fabrication/batches/{b2['id']}/start").status_code == 200
    assert len(_low_notifs(db, env["user"], iid)) == 1


def test_relever_le_seuil_au_dessus_du_stock_notifie(env):
    db = env["db"]
    admin = create_test_user(db, "t_fdf_admin2", "admin")
    iid = _intrant(env)
    _purchase(env, iid, qty="100")
    ctrl_user = env["user"]
    # le seuil est reserve a l'admin cote endpoint ; appel direct du controleur
    from controller.fabrication_controller import FabricationController
    from repositories.audit_repo import AuditRepository
    from repositories.fabrication_repo import FabricationRepository
    c = FabricationController(FabricationRepository(db), AuditRepository(db), ctrl_user)
    c.set_threshold(iid, "150")
    assert len(_low_notifs(db, admin, iid)) == 1
    c.set_threshold(iid, "200")  # deja sous le seuil : pas de repetition
    assert len(_low_notifs(db, admin, iid)) == 1


def test_annuler_un_achat_sous_le_seuil_notifie(env):
    db = env["db"]
    iid = _intrant(env)
    pid = _purchase(env, iid, qty="100")
    db.get(FabIntrant, iid).alert_threshold = Decimal("50")
    db.flush()
    assert env["c"].post(f"/fabrication/purchases/{pid}/cancel", json={"reason": "erreur"}).status_code == 200
    assert len(_low_notifs(db, env["user"], iid)) == 1


def test_achat_annule_a_un_restant_nul(env):
    iid = _intrant(env)
    pid = _purchase(env, iid, qty="100")
    assert env["c"].post(f"/fabrication/purchases/{pid}/cancel", json={"reason": "erreur"}).status_code == 200
    assert _remaining(env, pid) == 0
    rows = env["c"].get("/fabrication/purchases", params={"intrant_id": iid}).json()
    row = next(r for r in rows if r["id"] == pid)
    assert row["status"] == "annule" and Decimal(str(row["remaining_qty"])) == 0
    assert Decimal(str(row["quantity"])) == 100  # la quantite d'origine reste lisible


def test_lot_rouvert_perd_ses_resultats_et_son_drapeau_hors_tolerance(env):
    b, _, _ = _started(env)
    r = env["c"].post(f"/fabrication/batches/{b['id']}/finish",
                      json={"qty_good": 50, "qty_damaged": 3, "qty_rejected": 2, "liquid_lost": "0.500"})
    assert r.status_code == 200 and r.json()["out_of_tolerance"] is True
    r = env["c"].post(f"/fabrication/batches/{b['id']}/reopen")
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "en_production" and out["out_of_tolerance"] is False
    assert (out["qty_good"], out["qty_damaged"], out["qty_rejected"]) == (0, 0, 0)
    assert Decimal(str(out["liquid_lost"])) == 0
    assert out["found_qty"] is None and out["missing_qty"] is None and out["missing_pct"] is None
    assert out["total_cost"] is None and out["unit_cost"] is None
    assert out["expected_qty"] == 120  # l'attendu vient du contenant reserve : inchange


def test_le_controle_quotidien_inclut_les_intrants_sous_le_seuil(db_session):
    from tests.test_daily_control import _ctrl, _keys, D1, Clock, _at
    from models.fabrication import FabIntrant as FI
    i = FI(name="Intrant seuil controle", unit="u", is_container=False, alert_threshold=Decimal("5"))
    db_session.add(i)
    db_session.flush()
    admin = create_test_user(db_session, "t_fdf_ctl", "admin")
    k = _keys(_ctrl(db_session, admin, Clock(_at(D1))), D1)
    a = k["intrant_sous_seuil:Intrant seuil controle"]
    assert a["link"].startswith("/dashboard/fabrication")
