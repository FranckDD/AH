# tests/test_spiritual_notes.py
"""Notes du conseiller spirituel : regles d'acces, dates, bornes, audit, liste."""
import json
from datetime import timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.spiritual_notes import spiritual_notes_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from models.audit import AuditUserAction
from models.spiritual_note import SpiritualNote
from tests.conftest import create_test_user
from utils.business_time import business_today

PWD = "TestPass123!"
OTHER_ROLES = ("secretaire", "medecin", "nurse", "Psychologist", "ToxicoManager", "Assistant")
SECRET = "TEXTE-CONFIDENTIEL-XYZ"
BIG = 987654321


@pytest.fixture(scope="module", autouse=True)
def _memoized_password_hash():
    import tests.conftest as cf
    real = cf.pwd_context
    cache = {}

    class _Ctx:
        def hash(self, pw):
            if pw not in cache:
                cache[pw] = real.hash(pw)
            return cache[pw]

        def __getattr__(self, name):
            return getattr(real, name)

    mp = pytest.MonkeyPatch()
    mp.setattr(cf, "pwd_context", _Ctx())
    yield
    mp.undo()


@pytest.fixture
def env(db_session, api_client):
    names = {"c1": "SpiritualCounsellor", "c2": "SpiritualCounsellor", "promoteur": "promoteur", "admin": "admin"}
    for r in OTHER_ROLES:
        names[r] = r
    users = {k: create_test_user(db_session, f"t_spnote_{k.lower()}", role, password=PWD)
             for k, role in names.items()}
    for k, u in users.items():
        u.roles = [normalize_role_name(names[k])]
    client = api_client(auth_endpoints, ep)

    def as_(key):
        app.dependency_overrides[auth_endpoints.get_current_user] = lambda: users[key]
        return client

    return {"db": db_session, "users": users, "as_": as_}


def _mk(client, **kw):
    r = client.post("/spiritual-notes/", json=kw)
    assert r.status_code == 201, r.text
    return r.json()


def test_counsellor_crud_own_note(env):
    c = env["as_"]("c1")
    note = _mk(c, counsel=True, prayer=True, verse_reference="Jean 3:16", content="abc")
    assert note["can_edit"] is True and note["meeting_date"] == business_today().isoformat()
    assert note["counsel"] and note["prayer"] and not note["qa"]
    r = c.put(f"/spiritual-notes/{note['id']}", json={"qa": True, "content": "nouveau"})
    assert r.status_code == 200 and r.json()["qa"] is True and r.json()["content"] == "nouveau"
    assert r.json()["counsel"] is True
    assert c.get(f"/spiritual-notes/{note['id']}").json()["content"] == "nouveau"
    assert c.delete(f"/spiritual-notes/{note['id']}").status_code == 204
    assert c.get(f"/spiritual-notes/{note['id']}").status_code == 404


def test_other_counsellor_reads_all_but_cannot_edit_or_delete_others(env):
    note = _mk(env["as_"]("c1"), content="a moi")
    c2 = env["as_"]("c2")
    lst = c2.get("/spiritual-notes/").json()
    mine = [n for n in lst["data"] if n["id"] == note["id"]]
    assert mine and mine[0]["can_edit"] is False
    assert c2.get(f"/spiritual-notes/{note['id']}").json()["can_edit"] is False
    assert c2.put(f"/spiritual-notes/{note['id']}", json={"content": "x"}).status_code == 403
    assert c2.delete(f"/spiritual-notes/{note['id']}").status_code == 403
    assert env["db"].query(SpiritualNote).filter_by(id=note["id"]).one().content == "a moi"


def test_promoteur_and_admin_read_all_with_author_name_and_cannot_write(env):
    note = _mk(env["as_"]("c1"), content="lisible")
    for key in ("promoteur", "admin"):
        c = env["as_"](key)
        rows = [n for n in c.get("/spiritual-notes/").json()["data"] if n["id"] == note["id"]]
        assert rows and rows[0]["author_name"] == env["users"]["c1"].full_name
        assert rows[0]["can_edit"] is False
        assert c.get(f"/spiritual-notes/{note['id']}").status_code == 200
        assert c.post("/spiritual-notes/", json={}).status_code == 403
        assert c.put(f"/spiritual-notes/{note['id']}", json={"content": "x"}).status_code == 403
        assert c.delete(f"/spiritual-notes/{note['id']}").status_code == 403
    assert env["db"].query(SpiritualNote).filter_by(id=note["id"]).one().content == "lisible"


@pytest.mark.parametrize("role", OTHER_ROLES)
def test_other_roles_get_403_on_every_route(env, role):
    note = _mk(env["as_"]("c1"), content="prive")
    c = env["as_"](role)
    nid = note["id"]
    assert c.get("/spiritual-notes/").status_code == 403
    assert c.get(f"/spiritual-notes/{nid}").status_code == 403
    assert c.post("/spiritual-notes/", json={}).status_code == 403
    assert c.put(f"/spiritual-notes/{nid}", json={}).status_code == 403
    assert c.delete(f"/spiritual-notes/{nid}").status_code == 403
    assert c.get(f"/spiritual-notes/{BIG}").status_code == 403


def test_meeting_date_rules(env):
    c = env["as_"]("c1")
    today = business_today()
    assert _mk(c)["meeting_date"] == today.isoformat()
    assert _mk(c, meeting_date=(today - timedelta(days=365)).isoformat())["meeting_date"] == \
        (today - timedelta(days=365)).isoformat()
    r = c.post("/spiritual-notes/", json={"meeting_date": (today - timedelta(days=366)).isoformat()})
    assert r.status_code == 422 and "365" in r.json()["detail"]
    r = c.post("/spiritual-notes/", json={"meeting_date": (today + timedelta(days=1)).isoformat()})
    assert r.status_code == 422 and "futur" in r.json()["detail"]
    for bad in ("31/12/2025", "pas-une-date", "", None, 20260101, "2026-13-40"):
        r = c.post("/spiritual-notes/", json={"meeting_date": bad})
        assert r.status_code == 422, (bad, r.status_code)
        assert str(r.json()["detail"]).isascii()
    note = _mk(c)
    r = c.put(f"/spiritual-notes/{note['id']}", json={"meeting_date": (today + timedelta(days=1)).isoformat()})
    assert r.status_code == 422
    r = c.put(f"/spiritual-notes/{note['id']}", json={"meeting_date": (today - timedelta(days=366)).isoformat()})
    assert r.status_code == 422
    assert c.get(f"/spiritual-notes/{note['id']}").json()["meeting_date"] == today.isoformat()


def test_old_note_stays_editable_but_date_change_obeys_limits(env):
    c = env["as_"]("c1")
    today = business_today()
    old = today - timedelta(days=400)
    n = SpiritualNote(author_id=env["users"]["c1"].user_id, meeting_date=old, content="ancienne")
    env["db"].add(n)
    env["db"].flush()
    url = f"/spiritual-notes/{n.id}"
    r = c.put(url, json={"content": "omise"})
    assert r.status_code == 200 and r.json()["meeting_date"] == old.isoformat()
    r = c.put(url, json={"meeting_date": old.isoformat(), "content": "inchangee"})
    assert r.status_code == 200 and r.json()["content"] == "inchangee"
    r = c.put(url, json={"meeting_date": (today - timedelta(days=500)).isoformat()})
    assert r.status_code == 422 and "365" in r.json()["detail"]
    r = c.put(url, json={"meeting_date": (today + timedelta(days=1)).isoformat()})
    assert r.status_code == 422
    r = c.put(url, json={"meeting_date": (today - timedelta(days=5)).isoformat()})
    assert r.status_code == 200


def test_empty_note_allowed_with_date_only(env):
    c = env["as_"]("c1")
    d = (business_today() - timedelta(days=2)).isoformat()
    n = _mk(c, meeting_date=d)
    assert n["meeting_date"] == d and n["content"] is None and n["verse_reference"] is None
    for f in ("counsel", "prayer", "verse_read", "discussion", "text_given", "qa", "no_one_spoke"):
        assert n[f] is False
    n2 = _mk(c, no_one_spoke=True)
    assert n2["no_one_spoke"] is True


def test_text_and_verse_length_bounds(env):
    c = env["as_"]("c1")
    assert _mk(c, content="x" * 5000, verse_reference="v" * 120)
    assert c.post("/spiritual-notes/", json={"content": "x" * 5001}).status_code == 422
    assert c.post("/spiritual-notes/", json={"verse_reference": "v" * 121}).status_code == 422
    note = _mk(c)
    assert c.put(f"/spiritual-notes/{note['id']}", json={"content": "x" * 5001}).status_code == 422
    assert c.put(f"/spiritual-notes/{note['id']}", json={"verse_reference": "v" * 121}).status_code == 422


def test_delete_is_hard_and_audit_has_no_text(env):
    c = env["as_"]("c1")
    d = (business_today() - timedelta(days=3)).isoformat()
    note = _mk(c, meeting_date=d, content=SECRET, verse_reference="Psaume 23")
    assert c.delete(f"/spiritual-notes/{note['id']}").status_code == 204
    assert env["db"].query(SpiritualNote).filter_by(id=note["id"]).count() == 0
    rows = env["db"].query(AuditUserAction).filter_by(resource_type="SpiritualNote", resource_id=note["id"]).all()
    assert {r.action_performed for r in rows} >= {"CREATE", "DELETE"}
    dele = [r for r in rows if r.action_performed == "DELETE"][0]
    assert dele.old_values["note_id"] == note["id"]
    assert dele.old_values["meeting_date"] == d
    assert dele.old_values["author_id"] == env["users"]["c1"].user_id
    for r in rows:
        blob = json.dumps([r.old_values, r.new_values], default=str)
        assert SECRET not in blob and "Psaume" not in blob


def test_list_order_pagination_and_stable_tie_break(env):
    c = env["as_"]("c1")
    db = env["db"]
    today = business_today()
    old = (today - timedelta(days=10)).isoformat()
    a = _mk(c, meeting_date=old)
    b = _mk(c, meeting_date=old)
    d = _mk(c, meeting_date=today.isoformat())
    # force un created_at identique : le tri doit retomber sur id DESC
    db.query(SpiritualNote).filter(SpiritualNote.id.in_([a["id"], b["id"]])).update(
        {SpiritualNote.created_at: db.query(SpiritualNote).get(a["id"]).created_at}, synchronize_session=False)
    db.flush()
    mine = {a["id"], b["id"], d["id"]}
    body = c.get("/spiritual-notes/", params={"per_page": 100}).json()
    ids = [n["id"] for n in body["data"] if n["id"] in mine]
    assert ids == [d["id"], b["id"], a["id"]]
    assert body["total_pages"] == (body["total"] + 99) // 100 and body["page"] == 1
    p1 = c.get("/spiritual-notes/", params={"page": 1, "per_page": 1}).json()
    p2 = c.get("/spiritual-notes/", params={"page": 2, "per_page": 1}).json()
    assert len(p1["data"]) == 1 and len(p2["data"]) == 1 and p1["data"][0]["id"] != p2["data"][0]["id"]
    assert p1["total"] == body["total"] and p1["per_page"] == 1 and p1["total_pages"] == body["total"]
    empty = c.get("/spiritual-notes/", params={"page": body["total"] + 5, "per_page": 1}).json()
    assert empty["data"] == [] and empty["total"] == body["total"]
    for bad in ({"per_page": 0}, {"per_page": 101}, {"page": 0}):
        assert c.get("/spiritual-notes/", params=bad).status_code == 422


def test_deleting_counsellor_with_notes_gives_clear_409(env, api_client):
    from api_backend.backend_app.routes.admin import users_endpoint
    _mk(env["as_"]("c1"), content="a garder")
    client = api_client(auth_endpoints, ep, users_endpoint)
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: env["users"]["admin"]
    uid = env["users"]["c1"].user_id
    r = client.delete(f"/users/{uid}")
    assert r.status_code == 409 and "notes spirituelles" in r.json()["detail"]
    assert env["db"].query(SpiritualNote).filter_by(author_id=uid).count() == 1
