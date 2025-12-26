import os
from fpdf import FPDF

def export_params_to_pdf(params_list, title="Rapport Paramètres de Laboratoire"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    # Header
    logo = os.path.join('assets', 'logo_light.png')
    if os.path.exists(logo):
        pdf.image(logo, x=10, y=8, w=30)
    pdf.set_font('Arial', 'B', 16)
    # Sanitize title
    sanitize = lambda s: s.encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, sanitize(title), ln=1, align='C')
    pdf.ln(10)

    # Tableau
    cols = ["ID", "Paramètre", "Unité", "Type", "Examen"]
    widths = [20, 60, 30, 30, 60]
    pdf.set_font('Arial', 'B', 12)
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 8, sanitize(col), border=1, align='C')
    pdf.ln()

    pdf.set_font('Arial', '', 10)
    for p in params_list:
        # Supporte dicts et objets
        id_val = p.get('id') if isinstance(p, dict) else getattr(p, 'id', '')
        nom = p.get('nom_parametre') if isinstance(p, dict) else getattr(p, 'nom_parametre', '')
        unite = p.get('unite') if isinstance(p, dict) else getattr(p, 'unite', '')
        type_val = p.get('type_valeur') if isinstance(p, dict) else getattr(p, 'type_valeur', '')
        examen = ''
        if isinstance(p, dict):
            examen_obj = p.get('examen')
            examen = examen_obj.get('nom') if isinstance(examen_obj, dict) else examen_obj
        else:
            examen = getattr(p.examen, 'nom', '') if getattr(p, 'examen', None) else ''

        vals = [str(id_val), nom, unite, type_val, examen]
        for i, val in enumerate(vals):
            txt = sanitize(val)
            pdf.cell(widths[i], 6, txt[:int(widths[i] / 2)], border=1)
        pdf.ln()

    # Sauvegarde dans ./exports
    out_dir = os.path.join('exports')
    os.makedirs(out_dir, exist_ok=True)
    filename = f"params_{title.replace(' ', '_')}.pdf"
    out = os.path.join(out_dir, filename)
    pdf.output(out)
    return out
