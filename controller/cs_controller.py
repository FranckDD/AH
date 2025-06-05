# controllers/consultation_spirituel_controller.py
from typing import List

class ConsultationSpirituelController:
    def __init__(self, repo, patient_controller, current_user):
        self.repo = repo
        self.patient_controller = patient_controller
        self.user = current_user

    def list_consultations(self) -> List:
        return self.repo.list_all()

    def list_for_patient(self, patient_id: int) -> List:
        return self.repo.find_by_patient(patient_id)

    def create_consultation(self, data: dict):
        # Validation métier côté contrôleur
        if not data.get('patient_id'):
            raise ValueError("Le patient doit être chargé")
        if not data.get('type_consultation'):
            raise ValueError("Le type de consultation est obligatoire")
        # Autres validations selon type_consultation...
        return self.repo.create(data, self.user)

    def delete_consultation(self, cs_id: int):
        return self.repo.delete(cs_id)
    
    
    def get_consultation(self, cs_id: int):
        """
        Récupère une consultation par son identifiant.
        """
        cs = self.repo.get_by_id(cs_id)
        if not cs:
            raise ValueError(f"Aucune consultation trouvée pour l'ID {cs_id}")
        return cs
    
    def update_consultation(self, cs_id: int, data: dict):
        """
        Met à jour une consultation existante.
        """
        existing = self.repo.get_by_id(cs_id)
        if not existing:
            raise ValueError(f"Impossible de mettre à jour : la consultation {cs_id} n'existe pas.")
        return self.repo.update(cs_id, data)
    
    def get_last_for_patient(self, patient_id: int):
        return self.repo.get_last_for_patient(patient_id)
    
