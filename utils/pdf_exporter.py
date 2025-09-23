# utils/pdf_exporter.py
from typing import List, Dict, Any, Optional, Callable
from reportlab.lib.pagesizes import A4, landscape as rl_landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm
import json
import os

DEFAULT_PER_PAGE = 100  # limite côté client (évite 422 si serveur restreint)


def _ensure_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item
    try:
        # prenez les attributs publics utiles
        return {k: getattr(item, k) for k in dir(item) if not k.startswith("_") and not callable(getattr(item, k))}
    except Exception:
        return {"value": str(item)}


def _format_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return str(v)


def dicts_to_pdf(
    path: str,
    rows: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    column_labels: Optional[Dict[str, str]] = None,
    title: Optional[str] = "Export",
    page_size=A4,
    force_landscape: Optional[bool] = None,
    margin_mm: int = 12,
    font_size: int = 9,
    title_font_size: int = 14,
    logo_path: Optional[str] = None,
    admin_header: Optional[Dict[str, str]] = None
) -> None:
    """
    Écrit `rows` (liste de dicts) dans un PDF multi-page.
    - retire patient_id par défaut
    - ajoute automatiquement father_name/mother_name si présentes
    - bascule en paysage si force_landscape=True ou si beaucoup de colonnes
    - header: logo + admin_header (dict de champs affichés à droite)
    """
    try:
        # décider orientation
        # inférer colonnes si non fournies
        if columns is None:
            keys = []
            for r in rows:
                d = r if isinstance(r, dict) else _ensure_dict(r)
                for k in d.keys():
                    if k not in keys:
                        keys.append(k)
            # enlever colonne id technique si présente
            for id_key in ("patient_id", "id"):
                if id_key in keys:
                    keys.remove(id_key)
            # forcer présence parents si trouvés
            for p in ("father_name", "mother_name"):
                if any((isinstance(r, dict) and p in r) or (not isinstance(r, dict) and hasattr(r, p)) for r in rows):
                    if p not in keys:
                        if "last_name" in keys:
                            idx = keys.index("last_name") + 1
                            keys.insert(idx, p)
                        else:
                            keys.append(p)
            columns = keys

        # header labels
        if column_labels is None:
            column_labels = {}
        header = [column_labels.get(c, c.replace("_", " ").title()) for c in columns]

        # Décider paysage si forcé ou trop de colonnes
        col_count = max(1, len(columns))
        if force_landscape is None:
            landscape = col_count > 6  # heuristique: >6 colonnes -> paysage
        else:
            landscape = bool(force_landscape)

        pagesize = rl_landscape(page_size) if landscape else page_size

        # construire data pour le tableau (header + rows)
        data = [header]
        for r in rows:
            d = r if isinstance(r, dict) else _ensure_dict(r)
            row = []
            for c in columns:
                val = d.get(c) if isinstance(d, dict) else getattr(d, c, None)
                row.append(_format_cell(val))
            data.append(row)

        # doc setup
        margin = margin_mm * mm
        doc = SimpleDocTemplate(path, pagesize=pagesize, leftMargin=margin, rightMargin=margin,
                                topMargin=margin + 20 * mm, bottomMargin=margin + 10 * mm)

        width, height = pagesize
        usable_width = width - 2 * margin

        # calcule largeurs colonnes
        avg_chars = [max(len(str(h)), 8) for h in header]
        sample_n = min(30, len(data))
        for i in range(col_count):
            maxc = avg_chars[i]
            for r in data[1: sample_n]:
                try:
                    maxc = max(maxc, len(str(r[i])))
                except Exception:
                    pass
            avg_chars[i] = maxc

        total_chars = sum(avg_chars) or col_count
        col_widths = [max(30, int(usable_width * (c / total_chars))) for c in avg_chars]
        s = sum(col_widths)
        if s > 0:
            col_widths = [w * usable_width / s for w in col_widths]

        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        normal.fontSize = font_size
        title_style = ParagraphStyle("title", parent=styles["Heading1"], alignment=1, fontSize=title_font_size)

        flowables = []
        if title:
            flowables.append(Paragraph(title, title_style))
            flowables.append(Spacer(1, 6))

        table = Table(data, colWidths=col_widths, repeatRows=1)
        tbl_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4f81bd")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
        ])
        table.setStyle(tbl_style)
        flowables.append(table)

        # header & footer drawing
        def _header_footer(canvas, doc_):
            canvas.saveState()
            w, h = doc_.pagesize
            # logo (gauche)
            if logo_path and os.path.exists(logo_path):
                try:
                    logo_w = 35 * mm
                    logo_h = 18 * mm
                    canvas.drawImage(logo_path, margin, h - margin - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True)
                except Exception:
                    pass
            # titre centré en haut
            if title:
                canvas.setFont("Helvetica-Bold", max(10, title_font_size))
                canvas.drawCentredString(w / 2.0, h - margin + 4 * mm, title)
            # admin infos (droite)
            if admin_header and isinstance(admin_header, dict):
                canvas.setFont("Helvetica", 8)
                x = w - margin
                y = h - margin + 3 * mm
                for key, val in admin_header.items():
                    try:
                        canvas.drawRightString(x, y, str(val))
                        y -= 9
                    except Exception:
                        pass
            # footer: numéro de page
            canvas.setFont("Helvetica", 8)
            page_no = f"Page {doc_.page}"
            canvas.drawRightString(w - margin, margin / 2.0, page_no)
            canvas.restoreState()

        doc.build(flowables, onFirstPage=_header_footer, onLaterPages=_header_footer)

    except ModuleNotFoundError:
        raise RuntimeError("reportlab requis: pip install reportlab")
    except Exception:
        raise


def fetch_all_and_export_pdf(
    controller: Any,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    fetch_fn: str = "list_patients",
    per_page: int = DEFAULT_PER_PAGE,
    columns: Optional[List[str]] = None,
    column_labels: Optional[Dict[str, str]] = None,
    title: Optional[str] = "Export Patients",
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
    logo_path: Optional[str] = None,
    admin_header: Optional[Dict[str, str]] = None,
    force_landscape: Optional[bool] = None
) -> int:
    """
    Page à travers controller.<fetch_fn> et exporte tous les résultats en PDF.
    Retourne le nombre de lignes exportées.
    """
    if params is None:
        params = {}
    try:
        per_page = int(per_page)
    except Exception:
        per_page = DEFAULT_PER_PAGE
    per_page = min(per_page, DEFAULT_PER_PAGE)

    results: List[Dict[str, Any]] = []
    page = 1
    total_estimate = None

    fetch = getattr(controller, fetch_fn, None)
    if not callable(fetch):
        raise AttributeError(f"Controller has no method '{fetch_fn}'")

    while True:
        call_kwargs = dict(params, page=page, per_page=per_page)
        raw = fetch(**call_kwargs)
        if isinstance(raw, dict) and "data" in raw:
            items = raw.get("data") or []
            total_estimate = raw.get("total")
        elif isinstance(raw, list):
            items = raw
            if page == 1:
                total_estimate = len(items)
        else:
            items = []

        for it in items:
            if not isinstance(it, dict):
                try:
                    it = _ensure_dict(it)
                except Exception:
                    it = {"_raw": str(it)}
            results.append(it)

        if progress_callback:
            progress_callback(len(results), total_estimate)

        # stop conditions
        if isinstance(total_estimate, int):
            if len(results) >= int(total_estimate):
                break
        if not items or len(items) < per_page:
            break
        page += 1

    # infer default columns if not provided, ensure father/mother present, and remove id keys
    if columns is None:
        cols = []
        for r in results:
            for k in r.keys():
                if k not in cols:
                    cols.append(k)
        for id_key in ("patient_id", "id"):
            if id_key in cols:
                cols.remove(id_key)
        for p in ("father_name", "mother_name"):
            if any(p in r for r in results) and p not in cols:
                cols.append(p)
        columns = cols

    # automatic landscape decision if many columns
    if force_landscape is None:
        force_landscape = len(columns) > 6

    dicts_to_pdf(path, results, columns=columns, column_labels=column_labels, title=title,
                 page_size=A4, force_landscape=force_landscape, logo_path=logo_path,
                 admin_header=admin_header)
    return len(results)
