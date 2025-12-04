# export_utils.py
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime, date


def _to_datetime_like(value):
    """Retourne un objet datetime/date ou None. Essaie de parser si value est une str."""
    if value is None:
        return None
    if isinstance(value, datetime) or isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        try:
            return datetime.fromisoformat(s)
        except Exception:
            pass
    return None


def format_datetime_for_display(value, fmt="%Y-%m-%d %H:%M"):
    """Retourne une chaîne formatée sûre pour l'affichage/export."""
    dt = _to_datetime_like(value)
    if dt is None:
        return ""
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.strftime(fmt.split()[0])
    return dt.strftime(fmt)


def export_medical_records_to_excel(records: list[dict], file_path: str):
    """
    Export Excel comprenant : ID, Date consultation, Patient, Code Patient, Motif, Gravité,
    Tension, Température, Poids, Taille, Diagnostic, Traitement
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Dossiers Médicaux"

    headers = [
        "ID", "Date consultation", "Patient", "Code Patient", "Motif", "Gravité",
        "Tension", "Température", "Poids", "Taille", "Diagnostic", "Traitement"
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for rec in records:
        ws.append([
            rec.get("record_id", ""),
            format_datetime_for_display(rec.get("consultation_date"), fmt="%Y-%m-%d %H:%M"),
            rec.get("patient_name", ""),
            rec.get("patient_code", ""),
            rec.get("motif_code", ""),
            rec.get("severity", ""),
            rec.get("bp", ""),
            rec.get("temperature", ""),
            rec.get("weight", ""),
            rec.get("height", ""),
            rec.get("diagnosis", ""),
            rec.get("treatment", "")
        ])

    wb.save(file_path)


def export_medical_records_to_pdf(records: list[dict], file_path: str):
    """
    Export PDF avec les mêmes colonnes que l'Excel.
    Le layout utilise orientation paysage pour plus de place.
    """
    # Utiliser landscape pour mieux afficher beaucoup de colonnes
    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()

    title = Paragraph("Liste des dossiers médicaux", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    headers = [
        "ID", "Date", "Patient", "Code Patient", "Motif", "Gravité",
        "Tension", "Temp", "Poids", "Taille", "Diagnostic", "Traitement"
    ]
    data = [headers]

    for rec in records:
        data.append([
            rec.get("record_id", ""),
            format_datetime_for_display(rec.get("consultation_date"), fmt="%Y-%m-%d"),
            rec.get("patient_name", ""),
            rec.get("patient_code", ""),
            rec.get("motif_code", ""),
            rec.get("severity", ""),
            rec.get("bp", ""),
            rec.get("temperature", ""),
            rec.get("weight", ""),
            rec.get("height", ""),
            rec.get("diagnosis", ""),
            rec.get("treatment", "")
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2e86c1")),  # header background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)
