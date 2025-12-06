from sqlalchemy.orm import Session
from models.organization_config import OrganizationConfig

class ConfigRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_config(self) -> OrganizationConfig:
        """
        Récupère la configuration unique. 
        Si elle n'existe pas, on en crée une par défaut en mémoire (sans commit immédiat) 
        ou on retourne None selon la logique voulue.
        Ici, on retourne la première ligne trouvée.
        """
        return self.session.query(OrganizationConfig).first()

    def save_config(self, data: dict) -> OrganizationConfig:
        """
        Met à jour la configuration existante ou la crée.
        """
        config = self.get_config()

        if not config:
            # Création si n'existe pas
            config = OrganizationConfig(**data)
            self.session.add(config)
        else:
            # Mise à jour des champs
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        self.session.commit()
        self.session.refresh(config)
        return config