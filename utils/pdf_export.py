# utils/pdf_export.py
from fpdf import FPDF
import os

def export_patients_to_pdf(patients, title="Rapport Patients"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    # En-tête officiel
    logo = os.path.join('assets','logo_light.png')
    pdf.image(logo, x=10, y=8, w=30)
    pdf.set_font('Arial','B',16)
    pdf.cell(0, 10, title, ln=1, align='C')
    pdf.ln(10)
    # Tableau
    pdf.set_font('Arial','B',12)
    cols = ["ID","Code","Nom","Prénom","Naissance","Téléphone"]
    widths = [20,40,40,40,30,40]
    for i,col in enumerate(cols):
        pdf.cell(widths[i], 8, col, border=1, align='C')
    pdf.ln()
    pdf.set_font('Arial','',10)
    for p in patients:
        vals = [
            str(p.patient_id), p.code_patient, p.last_name, p.first_name,
            p.birth_date.strftime("%Y-%m-%d"), p.contact_phone or ""
        ]
        for i,val in enumerate(vals):
            pdf.cell(widths[i],6, val, border=1)
        pdf.ln()
    # Sauvegarde
    out = os.path.join('exports', f"patients_{title.replace(' ','_')}.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pdf.output(out)
    return out
