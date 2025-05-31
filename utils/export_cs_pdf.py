# utils/exportcs_pdf.py
from fpdf import FPDF
import os

def export_cs_to_pdf(cs_list, title="Rapport Consultations Spirituelles"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    # Header
    logo = os.path.join('assets','logo_light.png')
    if os.path.exists(logo):
        pdf.image(logo, x=10, y=8, w=30)
    pdf.set_font('Arial','B',16)
    pdf.cell(0, 10, title, ln=1, align='C')
    pdf.ln(10)

    # Tableau
    cols = ["Patient","Type","Inscrit le","Rdv le","Montant","Observation"]
    widths = [40,50,30,30,30,60]
    pdf.set_font('Arial','B',12)
    for i,col in enumerate(cols):
        pdf.cell(widths[i], 8, col, border=1, align='C')
    pdf.ln()

    pdf.set_font('Arial','',10)
    for cs in cs_list:
        # Extraire les valeurs
        pat  = cs.patient.code_patient if cs.patient else ""
        typ  = cs.type_consultation or ""
        reg  = cs.fr_registered_at.strftime("%Y-%m-%d") if cs.fr_registered_at else ""
        rdv  = cs.fr_appointment_at.strftime("%Y-%m-%d") if cs.fr_appointment_at else ""
        amt  = f"{cs.fr_amount_paid:.2f}" if cs.fr_amount_paid is not None else ""
        obs  = cs.fr_observation or ""
        vals = [pat, typ, reg, rdv, amt, obs]
        for i,val in enumerate(vals):
            txt = str(val)
            # découper si trop long
            pdf.cell(widths[i], 6, txt[:int(widths[i]/2)], border=1)
        pdf.ln()

    # Sauvegarde dans ./exports
    out_dir = os.path.join('exports')
    os.makedirs(out_dir, exist_ok=True)
    filename = f"cs_{title.replace(' ','_')}.pdf"
    out = os.path.join(out_dir, filename)
    pdf.output(out)
    return out
