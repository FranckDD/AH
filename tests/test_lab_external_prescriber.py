# tests/test_lab_external_prescriber.py
"""Prescripteur libre du patient externe a la reception du laboratoire (patients inventes uniquement)."""
import uuid

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, LabExternalPrescriber, LabResult
from tests.conftest import create_test_user, create_test_patient, auth_headers
from utils.lab_prescriber import format_prescriber

PWD = "Correct123!"


def _exam(db):
    ex = Examen(code=f"EP-{uuid.uuid4().hex[:8]}", nom="Examen prescripteur", categorie="Bio", prix=0)
    db.add(ex)
    db.flush()
    return ex


def _lab(db, tag):
    lab = create_test_user(db, f"ep_lab_{tag}", "laborantin", password=PWD)
    lab.postgres_role = "app_laborantin"
    db.flush()
    return lab


def _client(api_client, username):
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, username, PWD)


def _external_payload(ex, title="Dr", name="Test Alpha", **extra):
    info = {"nom": "Patient Fictif", "prenom": "", "age": 30, "sexe": "M", "telephone": "",
            "prescriber_title": title, "prescriber_name": name}
    info.update(extra)
    return {"external_patient_info": info, "results": [{"examen_id": ex.id}], "batch_uuid": str(uuid.uuid4())}


def test_format_prescriber_joins_title_and_name():
    assert format_prescriber("Dr", "  Jean   Test ") == "Dr Jean Test"
    assert format_prescriber("I.D.E.", "Marie Test") == "I.D.E. Marie Test"
    assert format_prescriber("Mme", "Test") == "Mme Test"
    assert format_prescriber("Volontaire", "") == "Volontaire"
    assert format_prescriber("Volontaire", "Paul Test") == "Volontaire Paul Test"
    assert format_prescriber("Autre", "Pasteur Test") == "Pasteur Test"


def test_rejects_empty_name_and_unknown_title():
    for title, name in [("Dr", ""), ("Dr", "   "), ("Autre", ""), ("Pr", "Test"), ("", "Test"), (None, "Test"), ("dr", "Test")]:
        with pytest.raises(ValueError):
            format_prescriber(title, name)


def test_name_bounded_and_html_stripped():
    out = format_prescriber("Dr", "<script>alert(1)</script>Jean\x00\x07 Test")
    # les balises sont retirees avec leur forme, il reste le texte lisible (le contenu du script n'est pas execute
    # mais reste du texte inerte : l'echappement a l'affichage |e est la defense, voir test PDF)
    assert out == "Dr alert(1) Jean Test"
    assert "<" not in out and ">" not in out and "script" not in out and "&lt" not in out
    assert not any(ord(c) < 32 or 0x7f <= ord(c) <= 0x9f for c in out)
    # entites HTML eventuellement construites : jamais de balise reconstituee
    assert "<" not in format_prescriber("Dr", "<<b>script>x")
    assert format_prescriber("Dr", "Jean\u202eTest\u200b Alpha\ufeff") == "Dr JeanTest Alpha"
    assert format_prescriber("Dr", "Martin & Fils \"Test\"") == "Dr Martin & Fils \"Test\""
    assert out.startswith("Dr ")
    long = format_prescriber("Mme", "A" * 500)
    assert len(long) <= 100 and long == "Mme " + "A" * 80
    assert len(format_prescriber("I.D.E.", "B" * 500)) <= 100
    with pytest.raises(ValueError):
        format_prescriber("Dr", "<b></b>")


def test_external_batch_stores_prescribed_by_name(db_session, api_client):
    lab = _lab(db_session, "s1")
    ex = _exam(db_session)
    client, h = _client(api_client, lab.username)
    resp = client.post("/labo/results/batch", headers=h, json=_external_payload(ex, "Dr", "Test Alpha"))
    assert resp.status_code == 201, resp.text
    row = db_session.query(LabResult).filter(LabResult.examen_id == ex.id).order_by(LabResult.result_id.desc()).first()
    assert row.prescribed_by_name == "Dr Test Alpha"
    assert row.prescribed_by is None
    assert "prescriber_title" not in (row.external_patient_info or {})
    assert db_session.query(LabExternalPrescriber).filter_by(title="Dr", name="Test Alpha").count() == 1


def test_external_batch_rejects_invalid_prescriber(db_session, api_client):
    lab = _lab(db_session, "s2")
    ex = _exam(db_session)
    client, h = _client(api_client, lab.username)
    for title, name in [("Pr", "Test"), ("Dr", ""), (None, "Test")]:
        resp = client.post("/labo/results/batch", headers=h, json=_external_payload(ex, title, name))
        assert resp.status_code == 422, (title, name, resp.text)


def test_internal_patient_path_unchanged(db_session, api_client):
    lab = _lab(db_session, "i1")
    pid, _ = create_test_patient(db_session, lab, first_name="Interne", last_name="Fictif")
    ex = _exam(db_session)
    client, h = _client(api_client, lab.username)
    payload = {"patient_id": pid, "prescribed_by_id": lab.user_id, "prescribed_by_name": "Dr Interne Test",
               "results": [{"examen_id": ex.id}], "batch_uuid": str(uuid.uuid4())}
    before = db_session.query(LabExternalPrescriber).count()
    resp = client.post("/labo/results/batch", headers=h, json=payload)
    assert resp.status_code == 201, resp.text
    row = db_session.query(LabResult).filter_by(patient_id=pid, examen_id=ex.id).one()
    assert row.prescribed_by_name == "Dr Interne Test" and row.prescribed_by == lab.user_id
    assert db_session.query(LabExternalPrescriber).count() == before


def test_suggestions_ordered_by_recent_use_and_deduplicated(db_session, api_client):
    lab = _lab(db_session, "g1")
    ex = _exam(db_session)
    client, h = _client(api_client, lab.username)
    for title, name in [("Dr", "Zzsug Alpha"), ("Mme", "Zzsug Beta"), ("Dr", "ZZSUG alpha")]:
        r = client.post("/labo/results/batch", headers=h, json=_external_payload(ex, title, name))
        assert r.status_code == 201, r.text
    resp = client.get("/labo/external-prescribers", headers=h, params={"q": "zzsug"})
    assert resp.status_code == 200, resp.text
    labels = [s["label"] for s in resp.json()]
    assert labels == ["Dr Zzsug Alpha", "Mme Zzsug Beta"]
    assert len(client.get("/labo/external-prescribers", headers=h).json()) <= 20
    assert client.get("/labo/external-prescribers", headers=h, params={"q": "introuvablexyz"}).json() == []


@pytest.mark.parametrize("role,expected", [("laborantin", 200), ("admin", 200), ("secretaire", 403), ("medecin", 403), ("nurse", 403)])
def test_suggestions_roles(db_session, api_client, role, expected):
    user = create_test_user(db_session, f"ep_role_{role}", role, password=PWD)
    client, h = _client(api_client, user.username)
    assert client.get("/labo/external-prescribers", headers=h).status_code == expected


def test_accented_prescriber_upsert_is_case_insensitive_and_never_fails(db_session, api_client):
    lab = _lab(db_session, "ac1")
    ex = _exam(db_session)
    client, h = _client(api_client, lab.username)
    tag = uuid.uuid4().hex[:6]
    first = client.post("/labo/results/batch", headers=h, json=_external_payload(ex, "Dr", f"\u00c9lise Zzacc{tag}"))
    assert first.status_code == 201, first.text
    row = db_session.query(LabExternalPrescriber).filter_by(title="Dr").filter(
        LabExternalPrescriber.name.ilike(f"%zzacc{tag}")).one()
    before = row.last_used_at
    again = client.post("/labo/results/batch", headers=h, json=_external_payload(ex, "Dr", f"\u00e9LISE ZZACC{tag}"))
    assert again.status_code == 201, again.text
    rows = db_session.query(LabExternalPrescriber).filter_by(title="Dr").filter(
        LabExternalPrescriber.name.ilike(f"%zzacc{tag}")).all()
    assert len(rows) == 1
    db_session.refresh(rows[0])
    assert rows[0].last_used_at > before


def test_external_batch_ignores_free_prescriber_when_validated_keys_present(db_session, api_client):
    lab = _lab(db_session, "fr1")
    ex = _exam(db_session)
    client, h = _client(api_client, lab.username)
    payload = _external_payload(ex, "Dr", "Valide Test")
    payload["prescribed_by_name"] = "Usurpateur Libre"
    payload["prescribed_by_id"] = lab.user_id
    assert client.post("/labo/results/batch", headers=h, json=payload).status_code == 201
    row = db_session.query(LabResult).filter(LabResult.examen_id == ex.id).one()
    assert row.prescribed_by_name == "Dr Valide Test" and row.prescribed_by is None


def test_pdf_templates_escape_the_prescriber(monkeypatch):
    from api_backend.backend_app.utils import pdf_generator
    from tests.test_pdf_signatures import _lab_ctx

    captured = {}

    class FakeHTML:
        def __init__(self, string=None, base_url=None):
            captured["html"] = string

        def write_pdf(self):
            return b"%PDF-fake"

    monkeypatch.setattr(pdf_generator, "HTML", FakeHTML)
    ctx = _lab_ctx()
    ctx["result_info"]["prescripteur"] = "Dr <script>alert(1)</script> & Fils"
    pdf_generator.render_pdf_from_template("lab_result_template.html", ctx)
    html = captured["html"]
    assert "<script>alert(1)</script>" not in html
    assert "Dr &lt;script&gt;alert(1)&lt;/script&gt; &amp; Fils" in html
