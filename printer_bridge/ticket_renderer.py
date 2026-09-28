# printer_bridge/ticket_renderer.py
"""Rendu ESC/POS pur du ticket de caisse - ne connait rien au reseau ni a
la config, prend n'importe quelle instance escpos.printer.* (Dummy en test,
Win32Raw/Usb en reel). Toute la logique metier (calcul du montant reduit,
recherche de la reduction approuvee) vit deja cote backend
(CaisseController.build_ticket_data) - cette fonction ne fait QUE mettre en
page ce qui lui est fourni."""

PAPER_WIDTH_CHARS = 42  # 80mm, police normale - marge de securite volontaire


def _truncate(text: str, max_len: int = PAPER_WIDTH_CHARS) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _line_item(name: str, quantity, unit_price, line_total) -> str:
    designation = _truncate(f"{quantity}x {name}", PAPER_WIDTH_CHARS - 12)
    return f"{designation}\n   P.U: {unit_price:.0f}   Total: {line_total:.0f}"


def render_ticket(printer, ticket_data: dict) -> None:
    header = ticket_data.get("header", {}) or {}

    # Fixe une page de code compatible avec les accents francais (CP1252,
    # equivalent Windows de latin-1) plutot que de laisser python-escpos
    # basculer automatiquement vers CP437 (qui produit des octets differents
    # pour les caracteres accentues). Si le profil de l'imprimante ne
    # supporte pas CP1252, on continue avec l'encodage par defaut plutot que
    # de planter le rendu.
    try:
        printer.magic.force_encoding("CP1252")
    except Exception:
        pass

    printer.set(align="center")
    ticket_logo_path = header.get("ticket_logo_path")
    if ticket_logo_path:
        try:
            printer.image(ticket_logo_path)
        except Exception:
            pass  # logo illisible/corrompu -> le ticket continue sans, jamais bloquant

    printer.set(align="center", bold=True, double_height=True)
    printer.text(f"{header.get('structure_name') or ''}\n")
    printer.set(align="center", bold=False, double_height=False)
    if header.get("address"):
        printer.text(f"{header['address']}\n")
    if header.get("phone"):
        printer.text(f"Tel: {header['phone']}\n")
    if header.get("niu") or header.get("rccm"):
        printer.text(f"NIU: {header.get('niu') or ''}  RCCM: {header.get('rccm') or ''}\n")

    printer.text("-" * PAPER_WIDTH_CHARS + "\n")
    printer.set(align="left")
    printer.text(f"Facture N: {ticket_data.get('transaction_id')}\n")
    printer.text(f"Date: {ticket_data.get('paid_at') or ''}\n")
    printer.text(f"Caissier: {ticket_data.get('user_name') or ''}\n")
    printer.text(f"Patient: {ticket_data.get('patient_name') or ''}\n")
    printer.text("-" * PAPER_WIDTH_CHARS + "\n")

    for item in ticket_data.get("items", []):
        printer.text(_line_item(
            item.get("item_name") or "Article",
            item.get("quantity"),
            float(item.get("unit_price") or 0),
            float(item.get("line_total") or 0),
        ) + "\n")

    printer.text("-" * PAPER_WIDTH_CHARS + "\n")
    printer.set(align="right")
    printer.text(f"TOTAL: {float(ticket_data.get('amount') or 0):.0f}\n")

    discount = ticket_data.get("discount")
    if discount:
        printer.set(align="left")
        printer.text(
            f"Réduction validée par {discount.get('decided_by_name') or '?'} "
            f"- {discount.get('decision_percent')}%\n"
        )
        printer.set(align="right")

    printer.text(f"Paye: {float(ticket_data.get('advance_amount') or 0):.0f}\n")
    remaining = float(ticket_data.get("remaining") or 0)
    if remaining > 0:
        printer.text(f"Reste a payer: {remaining:.0f}\n")
    printer.set(align="left")
    if ticket_data.get("payment_method"):
        printer.text(f"Mode: {ticket_data['payment_method']}\n")

    printer.text("-" * PAPER_WIDTH_CHARS + "\n")
    printer.set(align="center")
    printer.text("Merci de votre visite !\n")
    if header.get("legal_info"):
        printer.text(f"{header['legal_info']}\n")
    printer.cut()
