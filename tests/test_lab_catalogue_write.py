# tests/test_lab_catalogue_write.py
"""Chantier laboratoire (fiches, catalogue, age, grossesse), tache C2 : droit d'edition du catalogue.

Couvre : users.is_head_lab (admin seul, laborantin seul, POST / PUT / liste / auth/me : les trois
bogues historiques de is_head_nurse), can_edit_lab_catalogue, matrice de roles sur chaque route
d'ecriture, prix intouchable, audit avant/apres, suppression d'un element utilise (409),
desactivation, validations, reordonnancement, is_active honore a la creation d'un resultat.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.routes.labo import lab_catalogue_endpoints as cat
from api_backend.backend_app.routes.labo import lab_endpoints
from models.audit import AuditUserAction
from models.lab import Examen, LabResult, LabResultDetail, Parametre, ReferenceRange
from tests.conftest import auth_headers, create_test_user
from utils.lab_catalogue_access import can_edit_lab_catalogue

PWD = "Correct123!"
B = "/labo/catalogue"


# ------------------------------------------------------------------ helpers
@pytest.fixture
def ctx(db_session, api_client):
    client = api_client(auth_endpoints, users_endpoint, cat, lab_endpoints)
    users = {}

    def make(role, name=None, head=False):
        name = name or f"c2_{role}_{'head' if head else 'std'}"
        if name not in users:
            u = create_test_user(db_session, name, role, password=PWD)
            u.is_head_lab = head
            db_session.flush()
            users[name] = (u, auth_headers(client, name, PWD))
        return users[name]

    class C:
        pass

    c = C()
    c.client, c.make, c.session = client, make, db_session
    c.admin = lambda: make("admin")[1]
    c.head = lambda: make("laborantin", head=True)[1]
    return c


def _exam(c, headers=None, code="C2_X1", **over):
    body = {"code": code, "nom": "Examen C2", "categorie": "Biochimie", "layout_family": "table"}
    body.update(over)
    return c.client.post(f"{B}/exams", json=body, headers=headers or c.head())


def _param(c, exam_id, **over):
    body = {"examen_id": exam_id, "nom_parametre": "Param C2", "unite": "g/l", "result_kind": "numeric"}
    body.update(over)
    return c.client.post(f"{B}/parameters", json=body, headers=c.head())


def _range(c, param_id, **over):
    body = {"parametre_id": param_id, "sexe": "M", "age_min_days": 0, "age_max_days": 100,
            "valeur_min": 1, "valeur_max": 2}
    body.update(over)
    return c.client.post(f"{B}/ranges", json=body, headers=c.head())


def _used_result(c, exam_id, param_id):
    r = LabResult(test_type="C2", examen_id=exam_id, code_lab_patient=f"C2-{exam_id}-{param_id}")
    c.session.add(r)
    c.session.flush()
    c.session.add(LabResultDetail(result_id=r.result_id, parametre_id=param_id, valeur_text="1"))
    c.session.flush()
    return r


# ------------------------------------------------------- can_edit_lab_catalogue
class _U:
    def __init__(self, roles, head=False):
        self.roles, self.is_head_lab = roles, head


def test_can_edit_lab_catalogue_matrix():
    assert can_edit_lab_catalogue(_U(["admin"]))
    assert can_edit_lab_catalogue(_U(["laborantin"], True))
    assert not can_edit_lab_catalogue(_U(["laborantin"], False))
    assert not can_edit_lab_catalogue(_U(["nurse"], True))  # drapeau sans role laborantin : sans effet
    assert not can_edit_lab_catalogue(_U(["promoteur"], True))
    assert not can_edit_lab_catalogue(None)


# --------------------------------------------------------------- role matrix
WRITES = [
    ("post", "/exams", {"code": "C2_RM", "nom": "n", "categorie": "c"}),
    ("put", "/exams/1", {"nom": "n"}),
    ("put", "/exams/1/order", {"position": 1}),
    ("put", "/exams/order", {"ids": [1]}),
    ("put", "/exams/1/parameters/order", {"ids": [1]}),
    ("delete", "/exams/1", None),
    ("post", "/parameters", {"examen_id": 1, "nom_parametre": "p"}),
    ("put", "/parameters/1", {"nom_parametre": "p"}),
    ("put", "/parameters/1/order", {"position": 1}),
    ("delete", "/parameters/1", None),
    ("post", "/ranges", {"parametre_id": 1, "sexe": "M", "valeur_min": 1, "valeur_max": 2}),
    ("put", "/ranges/1", {"sexe": "M", "valeur_min": 1, "valeur_max": 2}),
    ("delete", "/ranges/1", None),
]


@pytest.mark.parametrize("role", ["laborantin", "medecin", "secretaire", "nurse", "StockController", "promoteur", "ProductionManager"])
@pytest.mark.parametrize("method,path,body", WRITES)
def test_write_routes_refuse_everyone_but_admin_and_head_of_lab(ctx, role, method, path, body):
    headers = ctx.make(role)[1]  # laborantin sans le drapeau
    kwargs = {"json": body} if body is not None else {}
    resp = getattr(ctx.client, method)(B + path, headers=headers, **kwargs)
    assert resp.status_code == 403, (role, method, path, resp.text)


def test_head_of_lab_and_admin_can_write(ctx):
    assert _exam(ctx, ctx.head(), code="C2_OK1").status_code == 201
    assert _exam(ctx, ctx.admin(), code="C2_OK2").status_code == 201


def test_reads_roles(ctx):
    for role, expected in (("laborantin", 200), ("admin", 200), ("promoteur", 200), ("medecin", 403), ("secretaire", 403), ("nurse", 403)):
        assert ctx.client.get(f"{B}/exams", headers=ctx.make(role)[1]).status_code == expected, role


# ---------------------------------------------------------------- price
def test_price_cannot_be_sent_by_head_of_lab_or_admin(ctx):
    for headers in (ctx.head(), ctx.admin()):
        r = _exam(ctx, headers, code="C2_PRIX", prix=500)
        assert r.status_code == 422
        assert "prix" in r.text.lower()
    ex = _exam(ctx, code="C2_PRIX2").json()
    assert ex["prix"] == 0
    r = ctx.client.put(f"{B}/exams/{ex['id']}", json={"prix": 900}, headers=ctx.head())
    assert r.status_code == 422
    assert float(ctx.session.get(Examen, ex["id"]).prix) == 0


def test_update_keeps_existing_price(ctx):
    ex = _exam(ctx, code="C2_KEEP").json()
    ctx.session.get(Examen, ex["id"]).prix = 1234
    ctx.session.flush()
    assert ctx.client.put(f"{B}/exams/{ex['id']}", json={"nom": "Autre nom"}, headers=ctx.head()).status_code == 200
    assert float(ctx.session.get(Examen, ex["id"]).prix) == 1234
    listed = [e for e in ctx.client.get(f"{B}/exams", headers=ctx.head()).json() if e["id"] == ex["id"]][0]
    assert listed["prix"] == 1234


# ---------------------------------------------------------------- exams CRUD
def test_exam_create_update_and_validation(ctx):
    r = _exam(ctx, code="c2_lower", section="BIOCHIMIE", method="Colorimetrie", signature_label="Dr X", sort_order=3)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"] == "C2_LOWER" and body["layout_family"] == "table" and body["is_active"] is True
    assert body["section"] == "BIOCHIMIE" and body["sort_order"] == 3 and body["parameters"] == []
    assert _exam(ctx, code="C2_LOWER").status_code == 409  # code deja pris (insensible a la casse)
    assert _exam(ctx, code="C2_FAM", layout_family="grid").status_code == 422
    assert _exam(ctx, code="C2 SPACE").status_code == 422
    assert _exam(ctx, code="C2_NONAME", nom="  ").status_code == 422
    u = ctx.client.put(f"{B}/exams/{body['id']}", json={"nom": "Renomme", "layout_family": "boxed", "is_active": False}, headers=ctx.head())
    assert u.status_code == 200 and u.json()["nom"] == "Renomme" and u.json()["layout_family"] == "boxed" and u.json()["is_active"] is False
    assert ctx.client.put(f"{B}/exams/{body['id']}", json={"layout_family": "x"}, headers=ctx.head()).status_code == 422
    assert ctx.client.put(f"{B}/exams/{body['id']}", json={"code": "OTHER"}, headers=ctx.head()).status_code == 422  # code immuable
    assert ctx.client.put(f"{B}/exams/99999999", json={"nom": "x"}, headers=ctx.head()).status_code == 404


def test_list_hides_inactive_unless_asked(ctx):
    ex = _exam(ctx, code="C2_INACT").json()
    p = _param(ctx, ex["id"]).json()
    q = _param(ctx, ex["id"], nom_parametre="Autre").json()
    ctx.client.put(f"{B}/parameters/{q['id']}", json={"is_active": False}, headers=ctx.head())
    ctx.client.put(f"{B}/exams/{ex['id']}", json={"is_active": False}, headers=ctx.head())
    ids = lambda r: {e["id"] for e in r.json()}
    assert ex["id"] not in ids(ctx.client.get(f"{B}/exams", headers=ctx.head()))
    full = ctx.client.get(f"{B}/exams?include_inactive=true", headers=ctx.head()).json()
    mine = [e for e in full if e["id"] == ex["id"]][0]
    assert {x["id"] for x in mine["parameters"]} == {p["id"], q["id"]}
    ctx.client.put(f"{B}/exams/{ex['id']}", json={"is_active": True}, headers=ctx.head())
    shown = [e for e in ctx.client.get(f"{B}/exams", headers=ctx.head()).json() if e["id"] == ex["id"]][0]
    assert [x["id"] for x in shown["parameters"]] == [p["id"]]  # parametre inactif masque


# ------------------------------------------------------------- parameters
def test_parameter_kinds_derive_legacy_columns(ctx):
    ex = _exam(ctx, code="C2_KIND").json()
    choice = _param(ctx, ex["id"], nom_parametre="Aspect", result_kind="choice", choices=["Clair", "Trouble"])
    assert choice.status_code == 201, choice.text
    row = ctx.session.get(Parametre, choice.json()["id"])
    assert (row.type_valeur, row.input_type, row.options_list, row.choices) == ("text", "select", "Clair,Trouble", ["Clair", "Trouble"])
    pn = _param(ctx, ex["id"], nom_parametre="HIV", result_kind="pos_neg").json()
    assert ctx.session.get(Parametre, pn["id"]).options_list == "Positif,Negatif"
    num = _param(ctx, ex["id"], nom_parametre="Glycemie").json()
    row = ctx.session.get(Parametre, num["id"])
    assert (row.type_valeur, row.input_type, row.options_list) == ("numeric", "numeric", None)
    assert [p["ordre"] for p in ctx.client.get(f"{B}/exams", headers=ctx.head()).json()[0]["parameters"]] is not None
    assert _param(ctx, ex["id"], result_kind="choice").status_code == 422  # choix obligatoires
    assert _param(ctx, ex["id"], result_kind="choice", choices=["A,B"]).status_code == 422
    assert _param(ctx, ex["id"], result_kind="weird").status_code == 422
    assert _param(ctx, 99999999).status_code == 404


def test_parameter_update_and_kind_frozen_when_used(ctx):
    ex = _exam(ctx, code="C2_UPK").json()
    p = _param(ctx, ex["id"]).json()
    r = ctx.client.put(f"{B}/parameters/{p['id']}", json={"nom_parametre": "Nouveau", "unite": "mg/dl", "print_label": "Imprime"}, headers=ctx.head())
    assert r.status_code == 200 and r.json()["nom_parametre"] == "Nouveau" and r.json()["print_label"] == "Imprime"
    r = ctx.client.put(f"{B}/parameters/{p['id']}", json={"result_kind": "choice", "choices": ["a", "b"]}, headers=ctx.head())
    assert r.status_code == 200 and r.json()["choices"] == ["a", "b"]
    _used_result(ctx, ex["id"], p["id"])
    r = ctx.client.put(f"{B}/parameters/{p['id']}", json={"result_kind": "numeric"}, headers=ctx.head())
    assert r.status_code == 409
    assert ctx.client.put(f"{B}/parameters/{p['id']}", json={"choices": ["a", "c"]}, headers=ctx.head()).status_code == 200


# ------------------------------------------------------------------ ranges
def test_range_validation_and_columns(ctx):
    ex = _exam(ctx, code="C2_RNG").json()
    p = _param(ctx, ex["id"]).json()
    ok = _range(ctx, p["id"])
    assert ok.status_code == 201, ok.text
    row = ctx.session.get(ReferenceRange, ok.json()["id"])
    assert (row.age_min_days, row.age_max_days, row.age_min, row.age_max) == (0, 100, None, None)
    assert _range(ctx, p["id"]).status_code == 409  # doublon exact
    assert _range(ctx, p["id"], valeur_max=3).status_code == 201  # meme bornes d'age, autre valeur : pas un doublon
    assert _range(ctx, p["id"], valeur_min=5, valeur_max=1).status_code == 422
    assert _range(ctx, p["id"], sexe="Z").status_code == 422
    assert _range(ctx, p["id"], age_min_days=50, age_max_days=10).status_code == 422
    assert _range(ctx, p["id"], ga_min_weeks=30, ga_max_weeks=20).status_code == 422
    assert _range(ctx, p["id"], ga_min_weeks=0, ga_max_weeks=46).status_code == 422
    assert _range(ctx, p["id"], age_min_days=-1).status_code == 422
    open_ended = _range(ctx, p["id"], sexe="F", age_min_days=None, age_max_days=None, ga_min_weeks=4, ga_max_weeks=12)
    assert open_ended.status_code == 201 and open_ended.json()["ga_max_weeks"] == 12
    assert _range(ctx, 99999999).status_code == 404
    up = ctx.client.put(f"{B}/ranges/{ok.json()['id']}", json={"sexe": "X", "age_min_days": 0, "age_max_days": 200, "valeur_min": 1, "valeur_max": 4}, headers=ctx.head())
    assert up.status_code == 200 and up.json()["sexe"] == "X" and up.json()["age_max_days"] == 200
    dup = ctx.client.put(f"{B}/ranges/{ok.json()['id']}", json={"sexe": "F", "ga_min_weeks": 4, "ga_max_weeks": 12, "valeur_min": 1, "valeur_max": 2}, headers=ctx.head())
    assert dup.status_code == 409  # devient identique a la plage F / SA 4-12 deja creee
    assert ctx.client.delete(f"{B}/ranges/{ok.json()['id']}", headers=ctx.head()).status_code == 204
    assert ctx.client.delete(f"{B}/ranges/{ok.json()['id']}", headers=ctx.head()).status_code == 404
    listed = [e for e in ctx.client.get(f"{B}/exams", headers=ctx.head()).json() if e["id"] == ex["id"]][0]
    assert all("valeur_min" in r and "age_min_days" in r and "ga_min_weeks" in r for r in listed["parameters"][0]["ranges"])


# ----------------------------------------------------------- delete / use
def test_delete_unused_exam_removes_parameters_and_ranges(ctx):
    ex = _exam(ctx, code="C2_DEL").json()
    p = _param(ctx, ex["id"]).json()
    _range(ctx, p["id"])
    assert ctx.client.delete(f"{B}/exams/{ex['id']}", headers=ctx.head()).status_code == 204
    assert ctx.session.get(Examen, ex["id"]) is None
    assert ctx.session.query(Parametre).filter(Parametre.examen_id == ex["id"]).count() == 0


def test_delete_used_exam_or_parameter_is_refused_with_deactivation_hint(ctx):
    ex = _exam(ctx, code="C2_USED").json()
    p = _param(ctx, ex["id"]).json()
    spare = _param(ctx, ex["id"], nom_parametre="Libre").json()
    _used_result(ctx, ex["id"], p["id"])
    r = ctx.client.delete(f"{B}/exams/{ex['id']}", headers=ctx.head())
    assert r.status_code == 409 and r.json()["detail"]["code"] == "in_use" and "is_active=false" in r.json()["detail"]["message"]
    r = ctx.client.delete(f"{B}/parameters/{p['id']}", headers=ctx.head())
    assert r.status_code == 409 and "is_active=false" in r.json()["detail"]["message"]
    assert ctx.client.delete(f"{B}/parameters/{spare['id']}", headers=ctx.head()).status_code == 204
    # la desactivation reste permise et ne touche pas les resultats existants
    assert ctx.client.put(f"{B}/exams/{ex['id']}", json={"is_active": False}, headers=ctx.head()).status_code == 200
    assert ctx.client.put(f"{B}/parameters/{p['id']}", json={"is_active": False}, headers=ctx.head()).status_code == 200
    assert ctx.session.query(LabResultDetail).filter(LabResultDetail.parametre_id == p["id"]).count() == 1
    flags = [e for e in ctx.client.get(f"{B}/exams?include_inactive=true", headers=ctx.head()).json() if e["id"] == ex["id"]][0]
    assert flags["in_use"] is True and flags["parameters"][0]["in_use"] is True


# ----------------------------------------------------------------- order
def test_reorder_exams_and_parameters_persist(ctx):
    a, b, c3 = (_exam(ctx, code=f"C2_O{i}", sort_order=0).json() for i in range(3))
    r = ctx.client.put(f"{B}/exams/order", json={"ids": [c3["id"], a["id"], b["id"]]}, headers=ctx.head())
    assert r.status_code == 200
    order = [e["id"] for e in ctx.client.get(f"{B}/exams", headers=ctx.head()).json() if e["id"] in {a["id"], b["id"], c3["id"]}]
    assert order == [c3["id"], a["id"], b["id"]]
    m = ctx.client.put(f"{B}/exams/{b['id']}/order", json={"position": 1}, headers=ctx.head())
    assert m.status_code == 200 and m.json()["sort_order"] == 1
    order = [e["id"] for e in ctx.client.get(f"{B}/exams", headers=ctx.head()).json() if e["id"] in {a["id"], b["id"], c3["id"]}]
    assert order[0] == b["id"]
    assert ctx.client.put(f"{B}/exams/order", json={"ids": [a["id"], a["id"]]}, headers=ctx.head()).status_code == 422
    assert ctx.client.put(f"{B}/exams/order", json={"ids": [99999999]}, headers=ctx.head()).status_code == 422
    assert ctx.client.put(f"{B}/exams/{b['id']}/order", json={"position": 0}, headers=ctx.head()).status_code == 422

    p1, p2, p3 = (_param(ctx, a["id"], nom_parametre=f"P{i}").json() for i in range(3))
    assert ctx.client.put(f"{B}/parameters/{p3['id']}/order", json={"position": 1}, headers=ctx.head()).status_code == 200
    got = [p["id"] for p in [e for e in ctx.client.get(f"{B}/exams", headers=ctx.head()).json() if e["id"] == a["id"]][0]["parameters"]]
    assert got == [p3["id"], p1["id"], p2["id"]]
    ok = ctx.client.put(f"{B}/exams/{a['id']}/parameters/order", json={"ids": [p2["id"], p3["id"], p1["id"]]}, headers=ctx.head())
    assert ok.status_code == 200 and [p["id"] for p in ok.json()] == [p2["id"], p3["id"], p1["id"]]
    assert ctx.client.put(f"{B}/exams/{a['id']}/parameters/order", json={"ids": [p1["id"]]}, headers=ctx.head()).status_code == 422


# ------------------------------------------------------------------ audit
def test_every_write_is_audited_without_sensitive_data(ctx):
    head_user = ctx.make("laborantin", head=True)[0]
    ex = _exam(ctx, code="C2_AUD").json()
    ctx.client.put(f"{B}/exams/{ex['id']}", json={"nom": "Apres"}, headers=ctx.head())
    p = _param(ctx, ex["id"]).json()
    ctx.client.put(f"{B}/parameters/{p['id']}", json={"unite": "mg"}, headers=ctx.head())
    rg = _range(ctx, p["id"]).json()
    ctx.client.delete(f"{B}/ranges/{rg['id']}", headers=ctx.head())
    ctx.client.delete(f"{B}/parameters/{p['id']}", headers=ctx.head())
    ctx.client.delete(f"{B}/exams/{ex['id']}", headers=ctx.head())
    rows = ctx.session.query(AuditUserAction).filter(
        AuditUserAction.user_id == head_user.user_id, AuditUserAction.resource_type.in_(["LabExam", "LabParameter", "LabRange"])).all()
    seen = {(r.resource_type, r.action_performed) for r in rows}
    assert seen == {("LabExam", "CREATE"), ("LabExam", "UPDATE"), ("LabExam", "DELETE"),
                    ("LabParameter", "CREATE"), ("LabParameter", "UPDATE"), ("LabParameter", "DELETE"),
                    ("LabRange", "CREATE"), ("LabRange", "DELETE")}
    upd = [r for r in rows if r.resource_type == "LabExam" and r.action_performed == "UPDATE"][0]
    assert upd.old_values == {"nom": "Examen C2"} and upd.new_values["nom"] == "Apres"
    assert upd.resource_id == ex["id"]
    blob = " ".join(str(r.old_values) + str(r.new_values) for r in rows).lower()
    for forbidden in ("patient", "password", "prix"):
        assert forbidden not in blob


# --------------------------------------------- is_active honore a la creation
def test_inactive_exam_and_parameter_not_offered_for_new_results(ctx):
    from repositories.lab_repo import LabRepository
    ex = _exam(ctx, code="C2_NEWRES").json()
    keep = _param(ctx, ex["id"], nom_parametre="Garde").json()
    off = _param(ctx, ex["id"], nom_parametre="Coupe").json()
    ctx.client.put(f"{B}/parameters/{off['id']}", json={"is_active": False}, headers=ctx.head())
    repo = LabRepository(ctx.session)
    assert ex["id"] in {e.id for e in repo.list_all_examens()}
    result = repo.create_lab_result({"test_type": "C2", "examen_id": ex["id"], "status": "pending"})
    got = {d.parametre_id for d in ctx.session.query(LabResultDetail).filter(LabResultDetail.result_id == result.result_id)}
    assert got == {keep["id"]}
    ctx.client.put(f"{B}/exams/{ex['id']}", json={"is_active": False}, headers=ctx.head())
    assert ex["id"] not in {e.id for e in repo.list_all_examens()}
    legacy = ctx.client.get("/labo/exams", headers=ctx.admin()).json()
    assert ex["id"] not in {e["id"] for e in legacy}


# ------------------------------------------------- is_head_lab : le drapeau
def _new_user(ctx, headers, name, role_id, **extra):
    return ctx.client.post("/users/", headers=headers, json={"username": name, "password": "NewPass123!", "full_name": "Test " + name, "role_id": role_id, **extra})


def _role_id(ctx, name):
    from models.application_role import ApplicationRole
    return ctx.session.query(ApplicationRole).filter_by(role_name=name).one().role_id


def test_post_user_keeps_head_lab_flag_and_it_shows_in_get_list_and_auth_me(ctx):
    admin = ctx.admin()
    r = _new_user(ctx, admin, "c2_new_head", _role_id(ctx, "laborantin"), is_head_lab=True)
    assert r.status_code == 201, r.text
    assert r.json()["is_head_lab"] is True  # bogue historique 1 : le POST perdait le drapeau
    uid = r.json()["user_id"]
    assert ctx.client.get(f"/users/{uid}", headers=admin).json()["is_head_lab"] is True
    listed = ctx.client.get("/users/?per_page=500&search=c2_new_head", headers=admin).json()["data"]
    assert [u["is_head_lab"] for u in listed if u["user_id"] == uid] == [True]  # bogue 2 : forme de la liste
    token_headers = auth_headers(ctx.client, "c2_new_head", "NewPass123!")
    me = ctx.client.get("/auth/me", headers=token_headers).json()
    assert me["is_head_lab"] is True and me["application_role"]["role_name"] == "laborantin"  # bogue 3 : forme de authStore.user
    # et la nouvelle cheffe peut vraiment ecrire
    assert ctx.client.post(f"{B}/exams", headers=token_headers, json={"code": "C2_NEWHEAD", "nom": "n", "categorie": "c"}).status_code == 201
    # un utilisateur sans drapeau l'expose a faux
    plain = ctx.make("laborantin")[1]
    assert ctx.client.get("/auth/me", headers=plain).json()["is_head_lab"] is False


def test_put_user_sets_and_clears_head_lab(ctx):
    admin = ctx.admin()
    u = ctx.make("laborantin", "c2_target_lab")[0]
    r = ctx.client.put(f"/users/{u.user_id}", headers=admin, json={"is_head_lab": True, "is_active": True})
    assert r.status_code == 200 and r.json()["is_head_lab"] is True and r.json()["is_active"] is True
    r = ctx.client.put(f"/users/{u.user_id}", headers=admin, json={"full_name": "Autre"})
    assert r.json()["is_head_lab"] is True  # un PUT sans le champ ne l'efface pas
    r = ctx.client.put(f"/users/{u.user_id}", headers=admin, json={"is_head_lab": False})
    assert r.json()["is_head_lab"] is False
    audited = ctx.session.query(AuditUserAction).filter(AuditUserAction.resource_type == "User", AuditUserAction.resource_id == u.user_id).all()
    assert any("is_head_lab" in (a.new_values or {}) for a in audited)


def test_head_lab_only_on_lab_technician(ctx):
    admin = ctx.admin()
    nurse = ctx.make("nurse", "c2_nurse_flag")[0]
    r = ctx.client.put(f"/users/{nurse.user_id}", headers=admin, json={"is_head_lab": True})
    assert r.status_code == 422
    assert _new_user(ctx, admin, "c2_sec_flag", _role_id(ctx, "secretaire"), is_head_lab=True).status_code == 422
    # on passe une cheffe a un autre role : le drapeau tombe
    head = ctx.make("laborantin", "c2_demoted", head=True)[0]
    r = ctx.client.put(f"/users/{head.user_id}", headers=admin, json={"role_id": _role_id(ctx, "nurse")})
    assert r.status_code == 200 and r.json()["is_head_lab"] is False
    # changer le role ET poser le drapeau en meme temps
    other = ctx.make("nurse", "c2_promoted")[0]
    r = ctx.client.put(f"/users/{other.user_id}", headers=admin, json={"role_id": _role_id(ctx, "laborantin"), "is_head_lab": True})
    assert r.status_code == 200 and r.json()["is_head_lab"] is True


def test_head_lab_cannot_be_set_by_non_admin(ctx):
    # la cheffe ne peut pas se promouvoir elle-meme ni en designer une autre (routes /users: admin / manager)
    head_headers = ctx.head()
    target = ctx.make("laborantin", "c2_wannabe")[0]
    assert ctx.client.put(f"/users/{target.user_id}", headers=head_headers, json={"is_head_lab": True}).status_code == 403
    assert ctx.client.post("/users/", headers=head_headers, json={"username": "x", "password": "p", "full_name": "x"}).status_code == 403
    promoteur = ctx.make("promoteur")[1]
    assert ctx.client.put(f"/users/{target.user_id}", headers=promoteur, json={"is_head_lab": True}).status_code == 403
    assert ctx.session.get(type(target), target.user_id).is_head_lab is False


# ------------------------------------------------ C5 : textes imprimes, sous-titres, notes fixes
NOTE = {"position": "after_body", "text": "Zones therapeutiques :", "style": "bold"}


def test_exam_fixed_notes_roundtrip_order_and_clear(ctx):
    notes = [NOTE, {"position": "before_body", "text": "<b>Avant</b> & < 5", "style": "italic"},
             {"position": "after_conclusion", "text": "Fin", "style": "normal"}]
    ex = _exam(ctx, code="C5_N1", fixed_notes=notes)
    assert ex.status_code == 201 and ex.json()["fixed_notes"] == notes          # ordre garde, HTML non interprete
    eid = ex.json()["id"]
    assert ctx.session.get(Examen, eid).fixed_notes == notes
    listed = [e for e in ctx.client.get(f"{B}/exams", headers=ctx.head()).json() if e["id"] == eid][0]
    assert listed["fixed_notes"] == notes
    # un PUT sans le champ ne touche pas aux notes ; une liste vide ou null les efface (NULL en base)
    assert ctx.client.put(f"{B}/exams/{eid}", json={"nom": "Autre"}, headers=ctx.head()).json()["fixed_notes"] == notes
    swapped = [notes[2], notes[0]]
    assert ctx.client.put(f"{B}/exams/{eid}", json={"fixed_notes": swapped}, headers=ctx.head()).json()["fixed_notes"] == swapped
    assert ctx.client.put(f"{B}/exams/{eid}", json={"fixed_notes": []}, headers=ctx.head()).json()["fixed_notes"] == []
    ctx.session.expire_all()
    assert ctx.session.get(Examen, eid).fixed_notes is None
    assert ctx.client.put(f"{B}/exams/{eid}", json={"fixed_notes": [NOTE]}, headers=ctx.admin()).status_code == 200
    assert ctx.client.put(f"{B}/exams/{eid}", json={"fixed_notes": None}, headers=ctx.admin()).json()["fixed_notes"] == []


def test_exam_fixed_notes_validation(ctx):
    eid = _exam(ctx, code="C5_N2").json()["id"]

    def put(notes):
        return ctx.client.put(f"{B}/exams/{eid}", json={"fixed_notes": notes}, headers=ctx.head()).status_code

    assert put([NOTE] * 12) == 200
    assert put([NOTE] * 13) == 422                                              # 12 au plus
    assert put([{**NOTE, "text": "x" * 1000}]) == 200
    assert put([{**NOTE, "text": "x" * 1001}]) == 422
    assert put([{**NOTE, "text": "   "}]) == 422
    assert put([{**NOTE, "position": "milieu"}]) == 422
    assert put([{**NOTE, "style": "souligne"}]) == 422
    assert put([{**NOTE, "text": "a\x00b"}]) == 422                             # caractere de controle
    assert put([{**NOTE, "extra": 1}]) == 422
    assert put([{"position": "after_body", "text": "ok"}]) == 200               # style par defaut : normal
    assert put(["texte"]) == 422
    assert ctx.client.put(f"{B}/exams/{eid}", json={"fixed_notes": [NOTE]}, headers=ctx.make("laborantin")[1]).status_code == 403


def test_parameter_group_norm_text_and_range_display_text(ctx):
    eid = _exam(ctx, code="C5_N3").json()["id"]
    p = _param(ctx, eid, group_label="  NUMERATION GLOBULAIRE ", norm_text="H: 4,0 - 5,5   F: 4,0 - 5,0")
    assert p.status_code == 201
    pj = p.json()
    assert pj["group_label"] == "NUMERATION GLOBULAIRE" and pj["norm_text"] == "H: 4,0 - 5,5   F: 4,0 - 5,0"
    r = _range(ctx, pj["id"], display_text="4,0 - 5,5")
    assert r.status_code == 201 and r.json()["display_text"] == "4,0 - 5,5"
    rid = r.json()["id"]
    # PUT parametre : champs absents inchanges, vide -> NULL
    up = ctx.client.put(f"{B}/parameters/{pj['id']}", json={"unite": "mg"}, headers=ctx.head()).json()
    assert up["group_label"] == "NUMERATION GLOBULAIRE" and up["norm_text"]
    up = ctx.client.put(f"{B}/parameters/{pj['id']}", json={"group_label": "", "norm_text": None}, headers=ctx.head()).json()
    assert up["group_label"] is None and up["norm_text"] is None
    # PUT plage : remplacement complet
    full = {"sexe": "M", "age_min_days": 0, "age_max_days": 100, "valeur_min": 1, "valeur_max": 2}
    got = ctx.client.put(f"{B}/ranges/{rid}", json={**full, "display_text": "1,0 - 2,0"}, headers=ctx.head()).json()
    assert got["display_text"] == "1,0 - 2,0"
    assert ctx.client.put(f"{B}/ranges/{rid}", json=full, headers=ctx.head()).json()["display_text"] is None
    listed = [e for e in ctx.client.get(f"{B}/exams", headers=ctx.head()).json() if e["id"] == eid][0]
    assert "group_label" in listed["parameters"][0] and "display_text" in listed["parameters"][0]["ranges"][0]


def test_printed_text_length_limits(ctx):
    eid = _exam(ctx, code="C5_N4").json()["id"]
    assert _param(ctx, eid, nom_parametre="G80", group_label="g" * 80, norm_text="n" * 200).status_code == 201
    assert _param(ctx, eid, nom_parametre="G81", group_label="g" * 81).status_code == 422
    assert _param(ctx, eid, nom_parametre="N201", norm_text="n" * 201).status_code == 422
    assert _param(ctx, eid, nom_parametre="NUL", norm_text="a\x00").status_code == 422
    pid = _param(ctx, eid, nom_parametre="P").json()["id"]
    assert ctx.client.put(f"{B}/parameters/{pid}", json={"group_label": "g" * 81}, headers=ctx.head()).status_code == 422
    assert ctx.client.put(f"{B}/parameters/{pid}", json={"norm_text": "n" * 201}, headers=ctx.head()).status_code == 422
    assert _range(ctx, pid, display_text="d" * 60).status_code == 201
    assert _range(ctx, pid, valeur_min=5, valeur_max=6, display_text="d" * 61).status_code == 422
    assert _range(ctx, pid, valeur_min=7, valeur_max=8, display_text="a\x01").status_code == 422


def test_printed_text_changes_are_audited_before_and_after(ctx):
    head_user = ctx.make("laborantin", head=True)[0]
    ex = _exam(ctx, code="C5_AUD", fixed_notes=[NOTE]).json()
    ctx.client.put(f"{B}/exams/{ex['id']}", json={"fixed_notes": [{**NOTE, "text": "Apres"}]}, headers=ctx.head())
    p = _param(ctx, ex["id"], norm_text="avant").json()
    ctx.client.put(f"{B}/parameters/{p['id']}", json={"norm_text": "apres", "group_label": "SOUS-TITRE"}, headers=ctx.head())
    rg = _range(ctx, p["id"], display_text="1,0 - 2,0").json()
    ctx.client.put(f"{B}/ranges/{rg['id']}", json={"sexe": "M", "age_min_days": 0, "age_max_days": 100,
                                                    "valeur_min": 1, "valeur_max": 2, "display_text": "1 - 2"}, headers=ctx.head())
    rows = ctx.session.query(AuditUserAction).filter(
        AuditUserAction.user_id == head_user.user_id,
        AuditUserAction.resource_type.in_(["LabExam", "LabParameter", "LabRange"])).all()
    exam_upd = [r for r in rows if r.resource_type == "LabExam" and r.action_performed == "UPDATE"][0]
    assert exam_upd.old_values == {"fixed_notes": [NOTE]}
    assert exam_upd.new_values["fixed_notes"] == [{**NOTE, "text": "Apres"}]
    par_upd = [r for r in rows if r.resource_type == "LabParameter" and r.action_performed == "UPDATE"][0]
    assert par_upd.old_values == {"group_label": None, "norm_text": "avant"}
    assert (par_upd.new_values["group_label"], par_upd.new_values["norm_text"]) == ("SOUS-TITRE", "apres")
    rng_upd = [r for r in rows if r.resource_type == "LabRange" and r.action_performed == "UPDATE"][0]
    assert rng_upd.old_values == {"display_text": "1,0 - 2,0"} and rng_upd.new_values["display_text"] == "1 - 2"
