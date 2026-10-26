"""Ordre d'affichage explicite des parametres d'un examen de labo (decision du proprietaire)."""
import uuid
from datetime import datetime

from sqlalchemy import text

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from controller.lab_controller import LabController
from models.lab import Examen, LabResult, LabResultDetail, Parametre
from repositories.lab_repo import LabRepository
from tests.conftest import create_test_user, create_test_patient, auth_headers

PWD = "Correct123!"


def _exam(db, names=("A", "B", "C")):
    ex = Examen(code=f"PO-{uuid.uuid4().hex[:8]}", nom="Ordre", categorie="Bio", prix=1000)
    db.add(ex)
    db.flush()
    ps = []
    for i, n in enumerate(names):
        p = Parametre(examen_id=ex.id, nom_parametre=n, unite="u", type_valeur="numeric",
                      input_type="numeric", ordre=i + 1)
        db.add(p)
        db.flush()
        ps.append(p)
    return ex, ps


def test_column_present_not_null_default_zero(db_session):
    row = db_session.execute(text(
        "SELECT is_nullable, column_default FROM information_schema.columns "
        "WHERE table_name='parametres' AND column_name='ordre'")).first()
    assert row is not None and row[0] == "NO" and "0" in (row[1] or "")


def test_migration_backfill_sql_keeps_id_order(db_session):
    ex, ps = _exam(db_session, ("Z", "Y", "X"))
    for p in ps:
        db_session.execute(text("UPDATE parametres SET ordre = 0 WHERE id = :i"), {"i": p.id})
    # le SQL de rattrapage de la migration 031
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions", "031_lab_param_order.py")
    spec = importlib.util.spec_from_file_location("mig031", path)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    db_session.execute(text(mig.BACKFILL_SQL))
    rows = db_session.execute(text(
        "SELECT id FROM parametres WHERE examen_id=:e ORDER BY ordre"), {"e": ex.id}).all()
    assert [r[0] for r in rows] == [p.id for p in ps]


def test_list_follows_ordre_not_id(db_session):
    ex, (a, b, c) = _exam(db_session)
    a.ordre, b.ordre, c.ordre = 3, 1, 2
    db_session.flush()
    out = LabController(repo=LabRepository(db_session)).list_parametres(ex.id)
    assert [p["nom"] for p in out] == ["B", "C", "A"]
    assert [p["ordre"] for p in out] == [1, 2, 3]


def test_new_param_gets_max_plus_one(db_session):
    ex, _ = _exam(db_session)
    ctrl = LabController(repo=LabRepository(db_session))
    out = ctrl.add_parametre(ex.id, {"nom_parametre": "D", "unite": "u", "type_valeur": "numeric"})
    assert db_session.get(Parametre, out["id"]).ordre == 4


def test_result_detail_and_print_follow_ordre(db_session):
    user = create_test_user(db_session, "po_admin", "admin", password=PWD)
    pid, _ = create_test_patient(db_session, user, first_name="Ord", gender="M")
    ex, (a, b, c) = _exam(db_session)
    a.ordre, b.ordre, c.ordre = 3, 1, 2
    r = LabResult(patient_id=pid, test_type=ex.nom, status="completed", examen_id=ex.id,
                  code_lab_patient=f"LAB-PO-{uuid.uuid4().hex[:8]}", test_date=datetime.now())
    db_session.add(r)
    db_session.flush()
    for p in (a, b, c):
        db_session.add(LabResultDetail(result_id=r.result_id, parametre_id=p.id, valeur_text="1",
                                       valeur_num=1, flagged=False, interpretation=""))
    db_session.flush()
    ctrl = LabController(repo=LabRepository(db_session))
    detail = ctrl.get_result_detail(r.result_id)
    assert [d["nom"] for d in detail["details"]] == ["B", "C", "A"]
    from controller.config_controller import ConfigController
    from repositories.config_repo import ConfigRepository
    pdata = ctrl.get_print_data(r.result_id, ConfigController(repo=ConfigRepository(db_session)))
    names = [d["parametre_nom"] for d in pdata["details"]]
    assert names == ["B", "C", "A"]


def _client(db, api_client, role="admin"):
    create_test_user(db, f"po_{role}", role, password=PWD)
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, f"po_{role}", PWD)


def test_reorder_endpoint(db_session, api_client):
    client, h = _client(db_session, api_client)
    ex, (a, b, c) = _exam(db_session)
    r = client.put(f"/labo/exams/{ex.id}/params/order", json={"ids": [c.id, a.id, b.id]}, headers=h)
    assert r.status_code == 200, r.text
    listed = client.get(f"/labo/exams/{ex.id}/params", headers=h).json()
    assert [p["nom"] for p in listed] == ["C", "A", "B"]


def test_reorder_forbidden_for_non_admin(db_session, api_client):
    client, h = _client(db_session, api_client, "laborantin")
    ex, (a, b, c) = _exam(db_session)
    assert client.put(f"/labo/exams/{ex.id}/params/order", json={"ids": [a.id, b.id, c.id]}, headers=h).status_code == 403


def test_reorder_rejects_foreign_missing_or_duplicate_ids(db_session, api_client):
    client, h = _client(db_session, api_client)
    ex, (a, b, c) = _exam(db_session)
    _, (x,) = _exam(db_session, ("X",))
    url = f"/labo/exams/{ex.id}/params/order"
    assert client.put(url, json={"ids": [a.id, b.id, x.id]}, headers=h).status_code == 422
    assert client.put(url, json={"ids": [a.id, b.id]}, headers=h).status_code == 422
    assert client.put(url, json={"ids": [a.id, a.id, b.id]}, headers=h).status_code == 422
    assert client.put(url, json={"ids": "nope"}, headers=h).status_code == 422
