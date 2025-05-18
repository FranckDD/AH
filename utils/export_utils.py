from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def export_medical_records_to_excel(records: list[dict], file_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Dossiers Médicaux"

    headers = [
        "ID", "Date consultation", "Patient", "Motif", "Gravité",
        "Tension", "Température", "Poids", "Taille", "Diagnostic", "Traitement"
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for rec in records:
        ws.append([
            rec.get("record_id"),
            rec.get("consultation_date").strftime("%Y-%m-%d %H:%M"),
            rec.get("patient_name", ""),
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
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    title = Paragraph("Liste des dossiers médicaux", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    headers = [
        "ID", "Date", "Patient", "Motif", "Gravité", 
        "Tension", "Temp", "Poids", "Taille", "Diagnostic", "Traitement"
    ]
    data = [headers]

    for rec in records:
        data.append([
            rec.get("record_id"),
            rec.get("consultation_date").strftime("%Y-%m-%d"),
            rec.get("patient_name", ""),
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
        ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.25, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)
