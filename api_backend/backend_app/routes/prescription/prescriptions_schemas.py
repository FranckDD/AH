# app/routes/prescriptions/schemas.py
from typing import Optional, List, Any
from pydantic import BaseModel, Field, model_validator, field_validator
from datetime import date

class PrescriptionBase(BaseModel):
    patient_id: int = Field(..., description="Identifiant du patient")
    medical_record_id: Optional[int] = None
    
    # On laisse optionnel ici, la validation logique se fait plus bas
    medication: Optional[str] = Field(None, min_length=1)
    dosage: Optional[str] = Field(None, min_length=1)
    frequency: Optional[str] = Field(None, min_length=1)
    duration: Optional[str] = None
    
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    
    # --- Nouveaux Champs ---
    is_lab_order: bool = Field(False, description="Vrai si c'est une demande d'examen")
    
    # On accepte que ce champ soit rempli, soit par une liste, soit par la conversion de la string
    lab_exams_list: Optional[List[str]] = Field(None, description="Liste des noms d'examens")

    uuid: Optional[str] = Field(None, description="UUID client (creation hors ligne PowerSync) - si absent, Postgres en genere un")

    model_config = {"from_attributes": True}

    # --- 1. PRE-VALIDATION : Nettoyage des données entrantes (Frontend -> Backend) ---
    @model_validator(mode="before")
    @classmethod
    def pre_process_data(cls, data: Any) -> Any:
        """
        C'est ici qu'on gère la compatibilité Frontend (String) -> Backend (List).
        Si le frontend envoie 'lab_exams' (string), on le convertit en 'lab_exams_list'.
        """
        if isinstance(data, dict):
            # Cas 1 : Le frontend envoie 'lab_exams' sous forme de String (ex: "NFS, Widal")
            if "lab_exams" in data and isinstance(data["lab_exams"], str):
                raw_exams = data["lab_exams"].strip()
                if raw_exams:
                    # On split la string pour créer la liste attendue par Pydantic
                    data["lab_exams_list"] = [x.strip() for x in raw_exams.split(",") if x.strip()]
                else:
                    data["lab_exams_list"] = []
            
            # Cas 2 : Gestion des champs vides envoyés comme "" au lieu de None
            for field in ["medication", "dosage", "frequency", "notes"]:
                if field in data and data[field] == "":
                    data[field] = None
                    
        return data

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("La date de début doit être antérieure ou égale à la date de fin.")
        return self

    @model_validator(mode="after")
    def set_defaults_for_lab_orders(self):
        """
        Si c'est un examen laboratoire, on remplit les champs obligatoires de la DB
        avec des valeurs par défaut pour éviter l'erreur NOT NULL.
        """
        if self.is_lab_order:
            # On force des valeurs par défaut si elles sont vides
            if not self.medication:
                self.medication = "DEMANDE D'EXAMEN"
            if not self.dosage:
                self.dosage = "N/A"      # Pour satisfaire NOT NULL
            if not self.frequency:
                self.frequency = "N/A"   # Pour satisfaire NOT NULL
            if not self.duration:
                self.duration = "N/A"    # C'EST CELUI QUI MANQUAIT !
                
        return self    


class _PrescriptionContentValidationMixin:
    """Regle de coherence metier (medicament XOR liste d'examens) - n'a de
    sens qu'a la creation/modification (PrescriptionCreate/Update), jamais
    a la lecture d'une prescription deja persistee (PrescriptionResponse).
    Extrait de l'ancien PrescriptionBase.check_content (2026-09-23) : une
    prescription plus ancienne que l'ajout de cette regle (is_lab_order
    sans lab_exams_list rempli) faisait planter GET /prescriptions/ - la
    regle se reappliquait a tort en lecture. Mixin plutot que duplication
    du corps sur Create ET Update."""

    @model_validator(mode="after")
    def check_content(self):
        # Cette regle ne s'applique que si la requete touche reellement au
        # contenu (medicament / statut labo / liste d'examens). Sur une
        # mise a jour partielle (PrescriptionUpdate) qui ne modifie que,
        # par exemple, "dosage", aucun de ces champs n'est fourni : ils
        # prennent leur valeur par defaut (None / False), qui ne reflete
        # PAS la prescription existante en base. Sans ce garde-fou, tout
        # PUT partiel omettant "medication" echouerait a tort avec
        # "medicament requis", meme quand la prescription existante en a
        # deja un. Sur une creation (PrescriptionCreate), "medication" est
        # un champ requis (voir plus bas) donc toujours present dans
        # model_fields_set - la regle continue de s'appliquer normalement.
        content_fields = {"medication", "is_lab_order", "lab_exams_list"}
        if not (self.model_fields_set & content_fields):
            return self

        # Validation : Soit des médicaments, soit des examens
        if not self.is_lab_order:
            # Si ce n'est PAS un examen, il faut un médicament
            if not self.medication:
                raise ValueError("Le nom du médicament est requis pour une prescription standard.")

        else:
            # Si C'EST un examen, il faut une liste d'examens
            # Note: lab_exams_list a été rempli par le pre_process_data ci-dessus
            if not self.lab_exams_list or len(self.lab_exams_list) == 0:
                raise ValueError("La liste des examens est requise pour une demande d'examen.")

        return self


class PrescriptionCreate(PrescriptionBase, _PrescriptionContentValidationMixin):
    # Optionnel a la creation SEULEMENT (voir MedicalRecordCreate) :
    # patient cree hors ligne connu par son uuid.
    patient_id: Optional[int] = None
    patient_uuid: Optional[str] = None
    # Correctif Critical revue finale : consultation liee creee hors ligne
    # dans le meme geste, pas encore confirmee par le serveur au moment de
    # l'envoi de la prescription - connue seulement par son uuid.
    medical_record_uuid: Optional[str] = None
    medication: Optional[str] = Field(..., min_length=1)
    dosage: Optional[str] = Field(..., min_length=1)
    frequency: Optional[str] = Field(..., min_length=1)
    # Requis (cle presente, valeur None acceptee - comble par
    # set_defaults_for_lab_orders() pour les examens) : prescriptions.duration
    # est NOT NULL en base, jamais rempli par defaut pour une prescription
    # standard (registre E6).
    duration: Optional[str] = Field(..., min_length=1)
    start_date: Optional[date] = Field(...)  # type: ignore


class PrescriptionUpdate(PrescriptionBase, _PrescriptionContentValidationMixin):
    pass


class PrescriptionResponse(PrescriptionBase):
    prescription_id: int
    prescribed_by: Optional[int] = None
    prescribed_by_name: Optional[str] = None
    patient: Optional[dict] = None
    
    # Champ calculé pour renvoyer une string simple au frontend si besoin
    # (Utile si votre frontend attend "lab_exams" en string pour l'affichage tableau)
    lab_exams: Optional[str] = None

    @field_validator("uuid", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        return str(v) if v is not None else v

    @model_validator(mode="before")
    @classmethod
    def format_output(cls, data: Any) -> Any:
        """
        Prépare les données sortantes (DB -> Frontend) pour le cas dict
        (ex. payload frontend avec "lab_exams" en string).

        Pas de branche objet ORM ici : le modele Prescription n'a pas
        d'attribut "lab_exams" (seulement "lab_exams_list", deja une
        vraie liste JSONB) - l'ancienne branche faisait
        getattr(data, "lab_exams", None), toujours None, puis
        setattr(data, "lab_exams_list", []) inconditionnellement sur
        l'instance ORM elle-meme : la vraie valeur chargee depuis la
        base etait ecrasee avant meme que Pydantic ne la lise, et
        l'instance suivie par SQLAlchemy etait marquee "dirty" (risque
        de perte de donnee reelle au prochain commit sur la meme
        session). Pydantic lit lab_exams_list nativement sur l'objet
        ORM via from_attributes=True, sans transformation necessaire.
        """
        if isinstance(data, dict):
            if "lab_exams" in data and isinstance(data["lab_exams"], str):
                data["lab_exams_list"] = [x.strip() for x in data["lab_exams"].split(",") if x.strip()]

        return data

    class Config:
        from_attributes = True


class PrescriptionListResponse(BaseModel):
    data: List[PrescriptionResponse]
    total: int
    page: int
    per_page: int

    model_config = {"from_attributes": True}
