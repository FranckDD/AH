# utils/invoice_pdf_generator.py
from fpdf import FPDF
from datetime import datetime
import os

# --- PLACEHOLDER DE RÉCUPÉRATION DES INFOS DE L'ENTREPRISE ---

def get_company_info() -> dict:
    """
    [PLACEHOLDER] Récupère les informations de l'entreprise.
    
    ATTENTION: Pour l'instant, les valeurs sont codées en dur (hard-coded).
    REMPLACEZ cette fonction par votre logique de base de données plus tard.
    """
    return {
        "name": "AH2 Santé",
        "address": "123 Rue de l'Hôpital, Ville, Pays",
        "contact": "+237 6xx xxx xxx",
        "email": "contact@ah2sante.com",
        "logo_path": os.path.join('assets','logo_light.png') 
    }

# --- CLASSE FPDF POUR LA FACTURE ---
class InvoicePDF(FPDF):
    
    def __init__(self, orientation='P', unit='mm', format='A4', company_data: dict = None):
        super().__init__(orientation, unit, format) # type: ignore
        # Stocke les données de l'entreprise (ou utilise le placeholder si non fourni)
        self.company_data = company_data if company_data is not None else get_company_info()
    
    def header(self, title="FACTURE DÉTAILLÉE"):
        
        # Récupération des données dynamiques
        info = self.company_data
        
        # --- BLOC GAUCHE : Logo et Infos Entreprise ---
        y_start = 8
        
        # 1. Logo (Positionné en x=10)
        logo = info.get("logo_path")
        logo_width = 30
        if os.path.exists(logo):
            self.image(logo, x=10, y=y_start, w=logo_width) # type: ignore
        
        # 2. Infos Entreprise 
        # Positionnement des infos à droite du logo et sous la position y initiale
        self.set_xy(10, y_start + logo_width / 2.5) 
        
        self.set_font('Arial','B', 10)
        self.cell(0, 5, info.get("name", "N/A"), ln=1, align='L')
        
        self.set_font('Arial','', 8)
        self.cell(0, 4, f"Adresse: {info.get('address', 'N/A')}", ln=1, align='L')
        self.cell(0, 4, f"Tél: {info.get('contact', 'N/A')}", ln=1, align='L')
        self.cell(0, 4, f"Email: {info.get('email', 'N/A')}", ln=1, align='L')
        
        self.ln(5) # Saut de ligne après les infos de l'entreprise

        # --- BLOC DROIT : Titre et Infos Facture ---
        # On repositionne le curseur en Y pour le titre
        self.set_y(y_start) 
        self.set_font('Arial','B', 16)
        self.cell(0, 10, title, ln=1, align='R')
        
        # Infos de date (à droite)
        self.set_font('Arial','', 10)
        self.cell(0, 5, f"Date de la facture: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1, align='R')
        
        self.ln(5)
        # Ligne de séparation
        self.set_draw_color(150, 150, 150)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        # Positionnement à 1.5 cm du bas
        self.set_y(-15)
        # Police Arial italique 8
        self.set_font('Arial','I',8)
        # Numéro de page
        self.cell(0, 10, 'Page %s/{nb}' % self.page_no(), 0, 0, 'C')

# --- FONCTIONS DE GÉNÉRATION ---
def generate_invoice_pdf(transaction_data: dict) -> bytes:
    """
    Génère le contenu binaire du PDF d'une seule facture.
    """
    
    # 1. Récupération des infos de l'entreprise
    company_info = get_company_info()
    
    # 2. Initialisation de la classe PDF avec les infos
    pdf = InvoicePDF(unit='mm', format='A4', company_data=company_info) 
    
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- DÉTAILS DE LA TRANSACTION ---
    # ... (Le reste du corps du PDF que nous avions revu) ...
    pdf.set_font('Arial','B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, f"Transaction N° {transaction_data.get('transaction_id', 'N/A')} / Statut: {transaction_data.get('status', '').upper()}", 1, 1, 'L', True)
    
    # Infos Patient & Caissier
    patient_name = transaction_data.get('patient_name') or transaction_data.get('patient_label', 'Inconnu')
    caissier_name = transaction_data.get('user_name') or transaction_data.get('created_by_name', 'N/A')
    
    pdf.set_font('Arial','', 10)
    pdf.cell(0, 6, f"Patient: {patient_name}", 0, 1, 'L')
    pdf.cell(0, 6, f"Enregistré par: {caissier_name}", 0, 1, 'L')
    pdf.ln(5)
    
    # --- TABLEAU DES ARTICLES ---
    pdf.set_font('Arial','B', 10)
    cols = ["Description (Type)", "Référence", "Qté", "P. Unit. (CFA)", "Total (CFA)"]
    widths = [70, 40, 20, 40, 30] 
    
    # En-tête
    pdf.set_fill_color(200, 220, 255)
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 7, col, 1, 0, 'C', True)
    pdf.ln()

    # Corps du tableau
    pdf.set_font('Arial','', 9)
    total_amount_calculated = 0.0 # Utilisation d'une variable locale
    items = transaction_data.get('items', [])
    for item in items:
        # Données de la ligne
        i_desc = f"{item.get('item_type', 'Service')} - {item.get('item_name', 'Détail')}"
        i_ref = str(item.get('item_ref_id', ''))
        i_qty = str(item.get('quantity', 1))
        # S'assurer que les montants sont bien des floats
        try:
            i_pu = float(item.get('unit_price', 0))
            i_tot = float(item.get('line_total', 0))
        except (TypeError, ValueError):
            i_pu = 0.0
            i_tot = 0.0
            
        total_amount_calculated += i_tot

        # Affichage (alignement)
        pdf.cell(widths[0], 6, i_desc, 1, 0, 'L')
        pdf.cell(widths[1], 6, i_ref, 1, 0, 'C')
        pdf.cell(widths[2], 6, i_qty, 1, 0, 'C')
        pdf.cell(widths[3], 6, f"{i_pu:,.2f}", 1, 0, 'R')
        pdf.cell(widths[4], 6, f"{i_tot:,.2f}", 1, 1, 'R') # ln=1 pour passer à la ligne suivante

    # --- RÉSUMÉ DES PAIEMENTS ---
    pdf.ln(5)
    pdf.set_font('Arial','B', 10)
    
    # Utilisation du montant du dictionnaire pour le résumé (pour respecter les paiements)
    amount = float(transaction_data.get('amount', 0)) 
    advance = float(transaction_data.get('advance_amount', 0))
    remaining = amount - advance
    
    # Total Global
    pdf.cell(sum(widths) - 50, 7, "TOTAL FACTURE :", 0, 0, 'R')
    pdf.set_font('Arial','B', 11)
    pdf.cell(50, 7, f"{amount:,.2f} CFA", 1, 1, 'R')
    
    # Montant Payé (Avance)
    pdf.set_font('Arial','', 10)
    pdf.cell(sum(widths) - 50, 7, "Montant Payé (Avance) :", 0, 0, 'R')
    pdf.cell(50, 7, f"{advance:,.2f} CFA", 1, 1, 'R')

    # Reste à payer
    if remaining > 0:
        pdf.set_font('Arial','B', 11)
        pdf.set_text_color(255, 0, 0) # Rouge
        pdf.cell(sum(widths) - 50, 7, "RESTE À PAYER :", 0, 0, 'R')
        pdf.cell(50, 7, f"{remaining:,.2f} CFA", 1, 1, 'R')
        pdf.set_text_color(0, 0, 0) # Noir
        
    # Fin de la génération, retourne les bytes
    # FIX FINAL: Assurer le retour en 'bytes' (pas 'bytearray')
    return bytes(pdf.output(dest='S')) 

def export_invoice_to_pdf_bytes(transaction_data: dict) -> bytes:
    """ Fonction publique à appeler """
    return generate_invoice_pdf(transaction_data)