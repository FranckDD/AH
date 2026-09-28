import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


def render_pdf_from_template(template_name: str, context: dict) -> bytes:
    """
    Rend un template Jinja2 (dossier utils/templates/) fusionne avec
    context, retourne les bytes du PDF genere par WeasyPrint. Fonction
    generique reutilisee par tous les exports PDF de ce projet (labo,
    facture caisse, export patients, export consultations) - chantier
    exports 2026-09-23, remplace l'ancienne build_medical_pdf() specifique
    au labo (conservee ci-dessous comme fine wrapper retro-compatible).
    """
    utils_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(utils_dir, 'templates')

    if not os.path.exists(template_dir):
        raise FileNotFoundError(f"Le dossier des templates est introuvable ici : {template_dir}")

    env = Environment(loader=FileSystemLoader(template_dir))

    try:
        template = env.get_template(template_name)
    except Exception:
        raise FileNotFoundError(f"Impossible de trouver '{template_name}' dans {template_dir}")

    html_content = template.render(**context)

    pdf_bytes = HTML(string=html_content, base_url=utils_dir).write_pdf()

    if not pdf_bytes:
        raise ValueError("Erreur interne : WeasyPrint n'a pas pu générer le PDF.")

    return pdf_bytes


def build_medical_pdf(print_data: dict) -> bytes:
    """
    Prend le dictionnaire complet de donnees du laboratoire, le fusionne
    avec le template labo, et retourne les bytes du PDF. Conserve tel
    quel (signature et comportement inchanges) pour ne pas toucher
    controller/lab_controller.py au-dela de la Tache 1 de ce plan.
    """
    return render_pdf_from_template('lab_result_template.html', print_data)
