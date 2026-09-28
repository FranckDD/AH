# printer_bridge/tests/test_ticket_renderer.py
import base64
import io
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PIL import Image
from escpos.printer import Dummy
from ticket_renderer import render_ticket, _load_scaled_logo, LOGO_SCALE


def _sample_ticket(**overrides):
    base = {
        "transaction_id": 42,
        "patient_name": "Jean Dupont",
        "user_name": "secretaire1",
        "paid_at": "2026-09-28T10:30:00",
        "amount": 10000.0,
        "advance_amount": 10000.0,
        "remaining": 0.0,
        "payment_method": "Espèces",
        "items": [
            {"item_name": "Consultation générale", "quantity": 1, "unit_price": 10000.0, "line_total": 10000.0},
        ],
        "discount": None,
        "header": {
            "structure_name": "Clinique AH2",
            "slogan": "Transforming lives through holistic care.",
            "address": "Douala",
            "phone": "699000000",
            "phone2": "677000000",
            "website": "ahandtohumanity-ngo.org",
            "niu": "M012345678",
            "rccm": "RC/DLA/2020/B/1234",
            "legal_info": None,
            "ticket_logo_path": None,
        },
    }
    base.update(overrides)
    return base


def test_render_ticket_includes_structure_name_and_transaction_id():
    printer = Dummy()
    render_ticket(printer, _sample_ticket())
    output = printer.output.decode("latin-1", errors="ignore")
    assert "Clinique AH2" in output
    assert "42" in output


def test_render_ticket_includes_item_line_with_quantity_and_price():
    printer = Dummy()
    render_ticket(printer, _sample_ticket())
    output = printer.output.decode("latin-1", errors="ignore")
    assert "Consultation générale" in output
    assert "10000" in output


def test_render_ticket_shows_discount_block_when_present():
    printer = Dummy()
    ticket = _sample_ticket(discount={"decision_percent": 20, "decided_by_name": "Dr Manager"})
    render_ticket(printer, ticket)
    output = printer.output.decode("latin-1", errors="ignore")
    assert "20" in output
    assert "Dr Manager" in output


def test_render_ticket_omits_discount_block_when_none():
    printer = Dummy()
    render_ticket(printer, _sample_ticket(discount=None))
    output = printer.output.decode("latin-1", errors="ignore")
    assert "Réduction" not in output


def test_render_ticket_includes_slogan_and_contacts():
    """Retour terrain 2026-09-28 : slogan, second telephone et site web
    manquaient completement du ticket alors que la config systeme les
    porte deja (models/organization_config.py)."""
    printer = Dummy()
    render_ticket(printer, _sample_ticket())
    output = printer.output.decode("latin-1", errors="ignore")
    assert "Transforming lives through holistic care." in output
    assert "699000000" in output and "677000000" in output
    assert "ahandtohumanity-ngo.org" in output


def test_load_scaled_logo_reduces_dimensions(tmp_path):
    logo_path = tmp_path / "logo.png"
    Image.new("RGB", (800, 400), color="white").save(logo_path)

    scaled = _load_scaled_logo(str(logo_path))

    assert isinstance(scaled, Image.Image)
    assert scaled.width == int(800 * LOGO_SCALE)
    assert scaled.height == int(400 * LOGO_SCALE)


def test_load_scaled_logo_falls_back_to_path_on_bad_file():
    result = _load_scaled_logo("/path/does/not/exist.png")
    assert result == "/path/does/not/exist.png"


def test_load_scaled_logo_decodes_data_uri():
    """Chemin hors ligne/local (CaisseList.vue::buildLocalTicketData) : le
    navigateur n'a jamais accès au système de fichiers serveur, il envoie le
    logo en data URI base64 (configStore.js::ticketLogoDataUri)."""
    buf = io.BytesIO()
    Image.new("RGB", (400, 200), color="black").save(buf, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    scaled = _load_scaled_logo(data_uri)

    assert isinstance(scaled, Image.Image)
    assert scaled.width == int(400 * LOGO_SCALE)
    assert scaled.height == int(200 * LOGO_SCALE)


def test_render_ticket_accepts_data_uri_logo_without_crashing():
    buf = io.BytesIO()
    Image.new("RGB", (200, 100), color="black").save(buf, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    printer = Dummy()
    ticket = _sample_ticket()
    ticket["header"]["ticket_logo_path"] = data_uri
    render_ticket(printer, ticket)  # ne doit pas lever


def test_render_ticket_truncates_long_item_name_without_crashing():
    """Review Focus : une designation trop longue pour du papier 80mm
    (~42 caracteres en police normale) ne doit jamais faire planter le
    rendu ni deborder de facon illisible."""
    printer = Dummy()
    long_name = "Consultation spécialisée en médecine interne avec suivi prolongé et bilan complet"
    render_ticket(printer, _sample_ticket(items=[
        {"item_name": long_name, "quantity": 1, "unit_price": 5000.0, "line_total": 5000.0},
    ]))
    output = printer.output.decode("latin-1", errors="ignore")
    lines = [l for l in output.split("\n") if long_name[:20] in l]
    assert len(lines) >= 1
    # aucune ligne de la sortie ne doit depasser une largeur raisonnable
    # (marge large : 48 caracteres, au-dela du 42 usuel du 80mm, pour
    # tolerer les codes ESC/POS eux-memes dans le buffer brut)
    for line in output.split("\n"):
        printable = "".join(ch for ch in line if ch.isprintable())
        assert len(printable) <= 48
