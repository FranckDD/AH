# tests/test_invoice_pdf_staff_discount.py
"""Task 11 - facture PDF : ligne de reduction personnel."""
import io
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from jinja2 import Environment, FileSystemLoader

import repositories.caisse_repo as caisse_repo_module
from models.caisse import Caisse
from models.caisse_item import CaisseItem
from repositories.caisse_repo import CaisseRepository
from tests.conftest import create_test_user, create_test_patient

TEMPLATE_DIR = os.path.join(
    os.path.dirname(__file__), '..', 'api_backend', 'backend_app', 'utils', 'templates'
)


def _make_tx(db, staff_discount=0, details=None, net=5500.0):
    user = create_test_user(db, "pdf_sd_user", "secretaire", password="Correct123!")
    pid, _ = create_test_patient(db, user)
    gross = net + staff_discount
    tx = Caisse(
        patient_id=pid, handled_by=user.user_id, amount=net, advance_amount=0, created_by_name="pdf_sd_user",
        status="active", payment_method="Especes", transaction_type="Vente",
        staff_discount_amount=staff_discount, staff_discount_details=details,
    )
    db.add(tx)
    db.flush()
    db.add(CaisseItem(
        transaction_id=tx.transaction_id, item_type="Examens", item_ref_id=1,
        quantity=1, unit_price=gross, line_total=gross, note="Bilan",
    ))
    db.flush()
    return tx


def _capture_context(db, tx, monkeypatch):
    captured = {}

    def fake_render(template_name, context):
        captured["template"] = template_name
        captured["context"] = context
        return b"%PDF-fake"

    monkeypatch.setattr(caisse_repo_module, "render_pdf_from_template", fake_render)
    CaisseRepository(db).generate_invoice_pdf_content(tx.transaction_id)
    return captured


def _render_html(context):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    return env.get_template("invoice_template.html").render(**context)


def test_staff_invoice_context_and_html(db_session, monkeypatch):
    tx = _make_tx(db_session, staff_discount=1500.0, net=5500.0,
                  details=[{"category": "medicament", "rate_percent": 50}])
    cap = _capture_context(db_session, tx, monkeypatch)
    t = cap["context"]["transaction"]
    assert t["amount"] == 5500.0
    assert t["staff_discount_amount"] == 1500.0
    assert t["gross_amount"] == 7000.0
    html = _render_html(cap["context"])
    assert "Prix normal" in html
    assert "7000.00 CFA" in html
    assert "Réduction personnel" in html
    assert "1500.00 CFA" in html
    # TOTAL FACTURE = net
    idx = html.index("TOTAL FACTURE")
    assert "5500.00 CFA" in html[idx:idx + 200]


def test_no_discount_adds_nothing(db_session, monkeypatch):
    tx = _make_tx(db_session, staff_discount=0, net=5500.0)
    cap = _capture_context(db_session, tx, monkeypatch)
    html = _render_html(cap["context"])
    assert "Prix normal" not in html
    assert "Réduction personnel" not in html
    assert "TOTAL FACTURE" in html


def test_replaced_by_manual_discount_shows_no_staff_line(db_session, monkeypatch):
    tx = _make_tx(db_session, staff_discount=0, net=4000.0,
                  details={"replaced_by_discount_request": 12})
    cap = _capture_context(db_session, tx, monkeypatch)
    html = _render_html(cap["context"])
    assert "Prix normal" not in html
    assert "Réduction personnel" not in html


def test_real_pdf_contains_staff_lines(db_session):
    pypdf = pytest.importorskip("pypdf")
    tx = _make_tx(db_session, staff_discount=1500.0, net=5500.0,
                  details=[{"category": "medicament", "rate_percent": 50}])
    pdf_bytes = CaisseRepository(db_session).generate_invoice_pdf_content(tx.transaction_id)
    assert pdf_bytes[:4] == b"%PDF"
    text = "".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf_bytes)).pages)
    assert "Prix normal" in text
    assert "7000.00" in text
    assert "Réduction personnel" in text
    assert "1500.00" in text
    assert "5500.00" in text
