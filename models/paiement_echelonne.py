# Dans models/paiement_echelonne.py (À créer)
from sqlalchemy import Column, Integer, Numeric, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .database import Base # Assurez-vous d'importer votre Base

class PaiementEchelonne(Base):
    __tablename__ = 'paiement_echelonne'
    
    payment_id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('caisse.transaction_id'), nullable=False)
    paid_amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(DateTime, nullable=False, default=func.now())
    payment_method = Column(String(50), nullable=False)
    payment_type = Column(String(50), nullable=False) # Ex: 'AVANCE', 'SOLDE', 'VERSEMENT_ECHEANCE'
    handled_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    note = Column(Text)

    # Relation vers Caisse (utile pour le patient)
    transaction = relationship("Caisse", backref="payments")
    # Relation vers User
    handler = relationship("User", foreign_keys=[handled_by]) 

# Assurez-vous d'importer ce nouveau modèle dans votre Session et Base.