# tests/test_lab_catalogue_old_routes.py
"""Tache C4 : les anciennes routes d'ecriture du catalogue (/labo/exams, /labo/params, /labo/ranges) appliquent
la meme garde que /labo/catalogue/* : admin ou laborantin avec is_head_lab. Le prix reste a l'admin sur toute route.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.routes.labo import lab_catalogue_endpoints as cat
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, Parametre, ReferenceRange
from tests.conftest import auth_headers, create_test_user

PWD = "Correct123!"


@pytest.fixture
def ctx(db_session, api_client):
    client = api_client(auth_endpoints, users_endpoint, cat, lab_endpoints)
    users = {}

    def make(role, head=False):
        name = f"c4_{role}_{'head' if head else 'std'}"
        if name not in users:
            u = create_test_user(db_session, name, role, password=PWD)
            u.is_head_lab = head
            db_session.flush()
            users[name] = auth_headers(client, name, PWD)
        return users[name]

    class C:
        pass

    c = C()
    c.client, c.session, c.make = client, db_session, make
    c.admin = lambda: make("admin")
    c.head = lambda: make("laborantin", head=True)
    c.std = lambda: make("laborantin")
    exam = Examen(code="C4OLD", nom="Examen C4", categorie="Bio", prix=1000)
    db_session.add(exam)
    db_session.flush()
    param = Parametre(examen_id=exam.id, nom_parametre="P C4", unite="g/l", type_valeur="numeric", input_type="numeric")
    db_session.add(param)
    db_session.flush()
    rng = ReferenceRange(parametre_id=param.id, sexe="M", age_min=None, age_max=None, valeur_min=1, valeur_max=2)
    db_session.add(rng)
    db_session.flush()
    c.exam, c.param, c.range = exam, param, rng
    return c


def _calls(c):
    """(libelle, appel(headers) -> reponse) pour chaque ancienne route d'ecriture accessible aux laborantins."""
    cl = c.client
    return [
        ("POST exams", lambda h: cl.post("/labo/exams", json={"code": "C4NEW", "nom": "N", "categorie": "B", "prix": 0}, headers=h)),
        ("PUT exams", lambda h: cl.put(f"/labo/exams/{c.exam.id}", json={"nom": "Renomme"}, headers=h)),
        ("POST params", lambda h: cl.post(f"/labo/exams/{c.exam.id}/params", json={"nom_parametre": "Neuf", "unite": "u"}, headers=h)),
        ("PUT params", lambda h: cl.put(f"/labo/params/{c.param.id}", json={"unite": "mg/l"}, headers=h)),
        ("POST ranges", lambda h: cl.post(f"/labo/params/{c.param.id}/ranges", json={"sexe": "F", "valeur_min": 1, "valeur_max": 3}, headers=h)),
        ("DELETE ranges", lambda h: cl.delete(f"/labo/ranges/{c.range.id}", headers=h)),
    ]


def test_laborantin_sans_drapeau_refuse_sur_chaque_route(ctx):
    for label, call in _calls(ctx):
        r = call(ctx.std())
        assert r.status_code == 403, (label, r.status_code, r.text)
    # rien n'a ete modifie
    ctx.session.expire_all()
    assert ctx.session.get(Examen, ctx.exam.id).nom == "Examen C4"
    assert ctx.session.get(Parametre, ctx.param.id).unite == "g/l"
    assert ctx.session.get(ReferenceRange, ctx.range.id) is not None


@pytest.mark.parametrize("role", ["medecin", "nurse", "secretaire", "ToxicoManager", "StockController"])
def test_autres_roles_toujours_refuses(ctx, role):
    h = ctx.make(role)
    for label, call in _calls(ctx):
        assert call(h).status_code in (401, 403), (role, label)


def test_cheffe_du_laboratoire_modifie_examen_parametre_plage(ctx):
    h = ctx.head()
    r = ctx.client.put(f"/labo/exams/{ctx.exam.id}", json={"nom": "Renomme par la cheffe"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["nom"] == "Renomme par la cheffe"
    r = ctx.client.put(f"/labo/params/{ctx.param.id}", json={"unite": "mg/l"}, headers=h)
    assert r.status_code == 200, r.text
    r = ctx.client.post(f"/labo/exams/{ctx.exam.id}/params", json={"nom_parametre": "Neuf", "unite": "u"}, headers=h)
    assert r.status_code == 201, r.text
    r = ctx.client.post(f"/labo/params/{ctx.param.id}/ranges", json={"sexe": "F", "valeur_min": 1, "valeur_max": 3}, headers=h)
    assert r.status_code == 201, r.text
    r = ctx.client.delete(f"/labo/ranges/{ctx.range.id}", headers=h)
    assert r.status_code == 204, r.text


def test_admin_modifie_et_fixe_le_prix(ctx):
    h = ctx.admin()
    r = ctx.client.put(f"/labo/exams/{ctx.exam.id}", json={"prix": 2500}, headers=h)
    assert r.status_code == 200, r.text
    ctx.session.expire_all()
    assert float(ctx.session.get(Examen, ctx.exam.id).prix) == 2500.0
    r = ctx.client.post("/labo/exams", json={"code": "C4ADM", "nom": "Par admin", "categorie": "B", "prix": 300}, headers=h)
    assert r.status_code == 201, r.text
    r = ctx.client.put(f"/labo/params/{ctx.param.id}", json={"unite": "mmol/l"}, headers=h)
    assert r.status_code == 200, r.text


def test_prix_jamais_modifiable_par_la_cheffe_sur_aucune_route(ctx):
    h = ctx.head()
    r = ctx.client.put(f"/labo/exams/{ctx.exam.id}", json={"nom": "X", "prix": 9999}, headers=h)
    assert r.status_code == 403, r.text
    r = ctx.client.post("/labo/exams", json={"code": "C4HEAD", "nom": "N", "categorie": "B", "prix": 10}, headers=h)
    assert r.status_code == 403, r.text
    ctx.session.expire_all()
    ex = ctx.session.get(Examen, ctx.exam.id)
    assert float(ex.prix) == 1000.0 and ex.nom == "Examen C4"
    assert ctx.session.query(Examen).filter_by(code="C4HEAD").count() == 0
    # route du catalogue : le prix est refuse en 422
    r = ctx.client.put(f"/labo/catalogue/exams/{ctx.exam.id}", json={"prix": 5}, headers=h)
    assert r.status_code == 422
    r = ctx.client.post("/labo/catalogue/exams", json={"code": "C4HEAD2", "nom": "N", "categorie": "B", "price": 5}, headers=h)
    assert r.status_code == 422


def test_cheffe_peut_changer_le_nom_sans_toucher_au_prix(ctx):
    # prix absent du corps : accepte ; le prix reste inchange
    r = ctx.client.put(f"/labo/exams/{ctx.exam.id}", json={"nom": "Sans prix", "categorie": "Autre"}, headers=ctx.head())
    assert r.status_code == 200, r.text
    ctx.session.expire_all()
    assert float(ctx.session.get(Examen, ctx.exam.id).prix) == 1000.0
