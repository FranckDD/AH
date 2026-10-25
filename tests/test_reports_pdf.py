# tests/test_reports_pdf.py
"""Rapports (tache 8) : export PDF GET /reports/export.pdf.

Texte relu avec pypdf (WeasyPrint sous-ensemble les polices : jamais de recherche dans les
octets bruts), y compris apres un aller-retour PdfReader -> PdfWriter. Un seul scenario
d'erreur par test (toute erreur du controleur annule la transaction de test).
"""
import io
import re
import unicodedata
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.reports import reports_endpoints as ep
from api_backend.backend_app.utils import reports_pdf
from models.organization_config import OrganizationConfig
from tests.cash_closure_isolation import clean_register, reset_register  # noqa: F401
from tests.conftest import create_test_user
from tests.test_report_products import _r
from tests.test_reports_endpoints import DS, Q, _seed

ROOT = Path(__file__).resolve().parents[1]
CENTRE = "Centre Rapports PDF Test"


def _norm(s: str) -> str:
    """Sans accents, espaces (fines, insecables, retours) ramenes a un espace simple."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\s   ]+", " ", s)


def _text(content: bytes) -> str:
    return _norm("\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages))


def _round_trip_text(content: bytes) -> str:
    w = PdfWriter()
    for p in PdfReader(io.BytesIO(content)).pages:
        w.add_page(p)
    buf = io.BytesIO()
    w.write(buf)
    return _text(buf.getvalue())


@pytest.fixture
def env(db_session, api_client):
    db = db_session
    users = {r: create_test_user(db, _r(f"rpdf_{r}"), r) for r in ("promoteur", "admin", "secretaire")}
    for r, u in users.items():
        u.roles = [r]
    cfg = db.query(OrganizationConfig).first()
    if cfg is None:
        cfg = OrganizationConfig(name=CENTRE)
        db.add(cfg)
    cfg.name = CENTRE
    db.flush()
    client = api_client(auth_endpoints, ep)

    def as_(role):
        if role is None:
            app.dependency_overrides.pop(auth_endpoints.get_current_user, None)
        else:
            app.dependency_overrides[auth_endpoints.get_current_user] = lambda: users[role]
        return client
    return {"db": db, "users": users, "as": as_}


# ------------------------------------------------------------------ HTTP
@pytest.mark.usefixtures("clean_register")
def test_pdf_200_content_and_round_trip(env):
    p, _ = _seed(env["db"], env["users"]["promoteur"])
    r = env["as"]("promoteur").get("/reports/export.pdf" + Q)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="rapports_{DS}_{DS}.pdf"'
    assert r.content[:4] == b"%PDF"
    txt = _text(r.content)
    assert CENTRE in txt
    assert "03/02/2021" in txt
    assert "Controle du jour" in txt
    assert "300,00" in txt                      # encaisse du jour D
    assert p.drug_name in txt                   # produit vendu
    assert "FCFA" in txt
    assert "Etat actuel au" in txt
    # piege des polices : le texte reste extractible apres reecriture par pypdf
    rt = _round_trip_text(r.content)
    assert CENTRE in rt and p.drug_name in rt and "Controle du jour" in rt


def test_pdf_admin_allowed_and_empty_period_renders(env):
    r = env["as"]("admin").get("/reports/export.pdf?date_from=2001-01-01&date_to=2001-01-01")
    assert r.status_code == 200, r.text
    txt = _text(r.content)
    # les etats courants (comptage, fabrication) restent visibles meme sur un jour ancien :
    # "Rien a signaler" est verifie par le test de rendu sans base
    assert "Controle du jour" in txt and "01/01/2001" in txt
    assert "Encaisse sur la periode" in txt and "0,00" in txt
    assert "Aucune vente sur la periode." in txt


def test_pdf_reversed_period_422_json(env):
    r = env["as"]("promoteur").get("/reports/export.pdf?date_from=2021-02-04&date_to=2021-02-03")
    assert r.status_code == 422
    assert "precede" in r.json()["detail"]


def test_pdf_too_long_period_422(env):
    r = env["as"]("promoteur").get("/reports/export.pdf?date_from=2021-01-01&date_to=2022-01-02")
    assert r.status_code == 422 and r.headers["content-type"].startswith("application/json")


def test_pdf_other_role_403(env):
    assert env["as"]("secretaire").get("/reports/export.pdf" + Q).status_code == 403


def test_pdf_unauthenticated_401(env):
    assert env["as"](None).get("/reports/export.pdf" + Q).status_code == 401


# ------------------------------------------------------------------ rendu (sans base)
HEADER = {"structure": SimpleNamespace(name=CENTRE), "logo_path": None}


def _empty_data(n_items=0, total=0):
    items = [{"product_id": i, "name": f"Produit synthetique {i:04d}", "category": "Cat",
              "quantity": 1, "amount": "1000.00"} for i in range(n_items)]
    return {"period": {"from": "2021-02-01", "to": "2021-03-02"},
            "sold": {"items": items, "total": total,
                     "amount_basis": "reports.table.amount_before_discount"}}


def test_render_truncates_at_500_rows():
    ctx = reports_pdf.build_context(HEADER, _empty_data(600, 600))
    assert len(ctx["sold_rows"]) == 500 and ctx["sold_truncated"]
    pdf = reports_pdf.render_reports_pdf(HEADER, _empty_data(600, 600))
    txt = _text(pdf)
    assert "Affichage limite aux 500 premiers produits" in txt
    assert "Produit synthetique 0499" in txt and "Produit synthetique 0500" not in txt


def test_render_not_truncated_and_empty_ok():
    ctx = reports_pdf.build_context(HEADER, _empty_data(3, 3))
    assert not ctx["sold_truncated"]
    txt = _text(reports_pdf.render_reports_pdf(HEADER, _empty_data()))
    assert "Rien a signaler" in txt and "01/02/2021" in txt and "02/03/2021" in txt


@pytest.mark.parametrize("raw,out", [
    ("0", "0,00"), ("300.00", "300,00"), ("1234567.5", "1 234 567,50"),
    ("-20.00", "-20,00"), ("-1234.005", "-1 234,01"), (None, "-"), ("999.999", "1 000,00"),
])
def test_money_format_from_strings(raw, out):
    assert reports_pdf.fmt_money(raw) == out


def test_dictionary_covers_every_controller_key():
    src = (ROOT / "controller" / "reports_controller.py").read_text(encoding="utf-8")
    keys = set(re.findall(r'"(reports\.[a-z_.]+[a-z_])"', src))
    keys |= {f"reports.cards.{m}" for m in re.findall(r'_card\(\s*"([a-z_]+)"', src)}
    assert len(keys) >= 20
    missing = sorted(k for k in keys if not reports_pdf.LABELS.get(k))
    assert not missing, missing


def test_escapes_html_in_labels():
    data = _empty_data()
    data["sold"]["items"] = [{"product_id": 1, "name": "<b>x</b> & y", "category": None,
                              "quantity": 1, "amount": "1.00"}]
    data["sold"]["total"] = 1
    txt = _text(reports_pdf.render_reports_pdf(HEADER, data))
    assert "<b>x</b> & y" in txt
