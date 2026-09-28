# printer_bridge/tests/test_ticket_renderer.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from escpos.printer import Dummy
from ticket_renderer import render_ticket


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
            "address": "Douala",
            "phone": "699000000",
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
