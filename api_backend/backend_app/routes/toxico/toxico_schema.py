from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import date, datetime
from typing import List, Optional, Literal

# --- 1. OBJETS DE LECTURE (Ce que le Front reçoit) ---

class PsychologistSimple(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class PhaseHistoryRead(BaseModel):
    phase: int
    start_date: date
    end_date: Optional[date]
    status: str
    comments: Optional[str]
    class Config:
        from_attributes = True

class EvaluationRead(BaseModel):
    id: int
    created_at: datetime
    # On renverra le nom via une propriété ou un mapper manuel dans l'endpoint
    # car Pydantic gère mal les nested deep relations sans config spécifique
    decision: str
    observation: str
    recommendation: Optional[str]
    phase_before: int
    phase_after: int
    is_relapse: bool
    class Config:
        from_attributes = True

class ToxicoPatientListItem(BaseModel):
    """Pour le tableau de bord (Liste)"""
    patient_id: int
    dossier_id: int
    patientName: str
    code: str
    substance: str
    currentPhase: int
    relapseCount: int
    psychologist: str # Nom complet
    admissionDate: Optional[date] = None

class ToxicoDossierDetail(BaseModel):
    """Pour la modale Dossier (Détail)"""
    id: int # dossier_id
    patient_id: int
    patientName: str # Mappé manuellement dans l'endpoint
    code: str
    dob: date
    
    admission_date: date
    substance: str
    current_phase: int
    relapse_count: int
    is_active: bool
    
    guardian_name: Optional[str]
    guardian_contact: Optional[str]
    notes_admission: Optional[str]
    
    phase_history: List[PhaseHistoryRead]
    evaluations: List[EvaluationRead]
    
    # Placeholder pour le futur (si on joint les données médicales)
    medical_history: List = [] 
    prescriptions: List = []

    class Config:
        from_attributes = True

class ToxicoListResponse(BaseModel):
    data: List[ToxicoPatientListItem]
    total: int
    page: int
    per_page: int


class ToxicoLastStay(BaseModel):
    stay_number: int
    admission_date: date
    discharge_date: Optional[date] = None
    discharge_reason: Optional[str] = None
    # pas de discharge_note : texte libre clinique, reserve au detail du dossier
    discharged_by_name: Optional[str] = None
    psychologist_name: Optional[str] = None
    substance: Optional[str] = None

class ToxicoDischargedItem(BaseModel):
    dossier_id: int
    patient_id: int
    patientName: str
    code: Optional[str] = None
    stays_count: int
    last_stay: Optional[ToxicoLastStay] = None

class ToxicoDischargedListResponse(BaseModel):
    data: List[ToxicoDischargedItem]
    total: int
    page: int
    per_page: int
    total_pages: int


# --- 2. OBJETS D'ÉCRITURE (Ce que le Front envoie) ---

class ToxicoAdmissionCreate(BaseModel):
    """
    Payload complet du formulaire d'admission.
    Gère à la fois l'identité du patient et le dossier toxico.
    """
    # Données Patient
    firstName: str
    lastName: str
    dob: date
    mothersName: str
    address: Optional[str] = None
    contact: Optional[str] = None
    
    # Données Toxico
    admissionDate: date
    substance: str
    psychologist_id: int = Field(..., alias="psychologist") # Mappe 'psychologist' du front vers 'psychologist_id'
    guardianName: str
    guardianContact: str
    consentFile: Optional[str] = Field(None) # On reçoit le nom du fichier pour l'instant
    notes: Optional[str] = None

class ToxicoDischargeRequest(BaseModel):
    """Corps strict de POST /toxico/discharge/{dossier_id}."""
    model_config = ConfigDict(extra="forbid")

    reason: Literal['guerison', 'abandon', 'exclusion', 'autre']
    note: Optional[str] = Field(None, max_length=2000)
    discharge_date: Optional[date] = None  # defaut : aujourd'hui ; jamais futur (verifie par le depot)

    @model_validator(mode="after")
    def _note_required_for_autre(self):
        if self.reason == 'autre' and not (self.note or "").strip():
            raise ValueError("Une note est obligatoire pour le motif « autre ».")
        return self


class ToxicoEvaluationCreate(BaseModel):
    """Payload de la modale d'évaluation"""
    # L'ID du dossier est crucial pour le Repository
    dossier_id: int = Field(..., description="ID du dossier toxicologique concerné") 
    
    # decision: doit correspondre aux valeurs attendues par le repo (MAINTAIN|PROGRESS|REGRESS)
    decision: str = Field(..., pattern="^(MAINTAIN|PROGRESS|REGRESS)$")
    observation: str
    recommendation: Optional[str] = None
    
    # Alias pour correspondre au front qui pourrait envoyer 'targetPhase'
    target_phase: int = Field(..., ge=1, le=4, alias="targetPhase")
    
    # patientId n'est plus nécessaire dans le body si dossier_id est requis.
    
    class Config:
        populate_by_name = True
    