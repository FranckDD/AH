# utils/exportcs_pdf.py
from fpdf import FPDF
import os

# Ajout d'une classe personnalisée pour gérer le MultiCell correctement dans une ligne
class PDF(FPDF):
    def chapter_body(self, cs_list, widths):
        self.set_font('Arial','',10)
        
        # Dimensions de la ligne normale (hors observation)
        cell_height = 6 
        
        for cs in cs_list:
            # Récupération et formatage des données
            # J'ai ajouté le nom complet du patient si possible (Patient Name)
            patient_info = cs.patient.full_name if cs.patient and hasattr(cs.patient, 'full_name') else (cs.patient.code_patient if cs.patient else "")
            
            vals = [
                patient_info,
                cs.type_consultation or "",
                cs.fr_registered_at.strftime("%Y-%m-%d") if cs.fr_registered_at else "N/A",
                cs.fr_appointment_at.strftime("%Y-%m-%d") if cs.fr_appointment_at else "N/A",
                f"{cs.fr_amount_paid:,.2f}" if cs.fr_amount_paid is not None else "0.00",
                cs.fr_observation or "" # Observation (géré avec multi_cell)
            ]
            
            # Calculer la hauteur maximale nécessaire pour cette ligne (principalement due à l'observation)
            obs_text = vals[-1]
            obs_width = widths[-1]
            
            # Estimer la hauteur du MultiCell (approximation)
            self.set_xy(self.get_x() + sum(widths[:-1]), self.get_y())
            required_height = self.multi_cell(obs_width, cell_height, obs_text, border=0, align='L', dry_run=True)
            
            # Hauteur finale de la ligne (au moins cell_height)
            line_height = max(cell_height, required_height)

            # Enregistrer la position Y de départ
            start_y = self.get_y()
            start_x = self.get_x()
            
            # Afficher les 5 premières cellules (cell)
            for i in range(len(vals) - 1):
                x = start_x + sum(widths[:i])
                y = start_y
                self.set_xy(x, y)
                
                # Dessiner le rectangle de la cellule complète (pour le bord)
                self.rect(x, y, widths[i], line_height)
                
                # Afficher le texte (centré verticalement dans la mesure du possible, 
                # en utilisant 'cell' qui tronque si trop long)
                # Utilisation de 'self.cell' pour un contenu court
                self.cell(widths[i], line_height, str(vals[i]), 0, 0, 'C') 

            # Afficher la dernière cellule (Observation - multi_cell)
            self.set_xy(start_x + sum(widths[:-1]), start_y)
            self.multi_cell(obs_width, cell_height, obs_text, border=1, align='L')
            
            # Se repositionner pour la prochaine ligne (le multi_cell a fait un saut de ligne)

def export_cs_to_pdf(cs_list, title="Rapport Consultations Spirituelles"):
    # Utiliser la classe PDF personnalisée
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Header
    logo = os.path.join('assets','logo_light.png')
    if os.path.exists(logo):
        pdf.image(logo, x=10, y=8, w=30)
    pdf.set_font('Arial','B',16)
    pdf.cell(0, 10, title, ln=1, align='C')
    pdf.ln(10)

    # Tableau - En-tête
    cols = ["Patient","Type","Inscrit le","Rdv le","Montant","Observation"]
    widths = [40, 40, 30, 30, 30, 70] # Augmenté Observation à 70 pour plus d'espace
    pdf.set_font('Arial','B',12)
    pdf.set_fill_color(200, 220, 255) # Couleur de fond pour l'en-tête
    for i,col in enumerate(cols):
        pdf.cell(widths[i], 8, col, border=1, align='C', fill=True)
    pdf.ln()

    # Corps du tableau (utilise la nouvelle méthode du corps)
    pdf.chapter_body(cs_list, widths)

    # Sauvegarde dans ./exports
    out_dir = os.path.join('exports')
    os.makedirs(out_dir, exist_ok=True)
    filename = f"cs_{title.replace(' ','_')}.pdf"
    out = os.path.join(out_dir, filename)
    pdf.output(out)
    return out