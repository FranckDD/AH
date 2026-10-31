from sqlalchemy import Column, Integer, String, Text, text
from .database import Base

class OrganizationConfig(Base):
    __tablename__ = "organization_config"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identité
    name = Column(String, nullable=False, default="AH2 CLINIC")
    slogan = Column(String, nullable=True)
    logo_url = Column(String, nullable=True) # Chemin relatif ou URL complète
    ticket_logo_url = Column(String, nullable=True)  # Logo monochrome dedie au ticket thermique, distinct du logo couleur
    ticket_print_token = Column(String, nullable=True)  # Jeton partage requis par le service pont local (jamais expose via GET /config/structure)

    # Coordonnées
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    po_box = Column(String, nullable=True) # Boite Postale
    phone = Column(String, nullable=True)
    phone2 = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # Infos Légales
    niu = Column(String, nullable=True)  # Numéro Identifiant Unique
    rccm = Column(String, nullable=True) # Registre Commerce
    legal_info = Column(Text, nullable=True) # Texte libre supplémentaire pour pied de page

    # Fiches de resultats (migration 041) : numero d'agrement imprime dans l'en-tete, texte du pied de
    # page (plusieurs lignes), libelle de signature par defaut (si l'examen n'en a pas).
    agrement_number = Column(String(200), nullable=True)
    footer_text = Column(Text, nullable=True)
    signature_label_default = Column(String(120), nullable=True)
    # Migration 046 : centered_results (defaut) ou left_laboratory (titre et bloc patient des fiches du laboratoire)
    lab_sheet_title_variant = Column(String(20), nullable=False, default="centered_results", server_default=text("'centered_results'"))

    # Taille des etiquettes de produits (mm), reglee par l'admin.
    label_width_mm = Column(Integer, nullable=False, default=50, server_default=text("50"))
    label_height_mm = Column(Integer, nullable=False, default=30, server_default=text("30"))
