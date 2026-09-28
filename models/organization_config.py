from sqlalchemy import Column, Integer, String, Text
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