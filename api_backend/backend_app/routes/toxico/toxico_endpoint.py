# Fichier: routes/toxico_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Request
from typing import List, Any, Dict, Optional
from sqlalchemy.orm import Session
from datetime import date

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

from controller.toxico_controller import ToxicoController
from repositories.toxico_repo import ToxicoRepository
from repositories.patient_repo import PatientRepository
from repositories.audit_repo import AuditRepository 
from controller.patient_controller import PatientController

from api_backend.backend_app.routes.toxico.toxico_schema import (
    PsychologistSimple,
    ToxicoListResponse,
    ToxicoAdmissionCreate,
    ToxicoEvaluationCreate
)

# 🟢 GLOBAL : On autorise le Psychologue ici.
router = APIRouter(prefix="/toxico", tags=["Toxicologie"],
                    dependencies=[Depends(role_required("ToxicoManager", "Psychologist", "SpiritualCounsellor", "Assistant", "admin"))])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_toxico_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user) 
) -> ToxicoController:
    
    toxico_repo = ToxicoRepository(session=db)
    patient_repo = PatientRepository(session=db) 
    audit_repo = AuditRepository(session=db) 
    
    patient_ctrl = PatientController(
        repo=patient_repo, 
        current_user=current_user,
        audit_repo=audit_repo 
    )

    return ToxicoController(
        repo=toxico_repo,
        patient_controller=patient_ctrl,
        current_user=current_user
    )

# --- ROUTES ---

@router.get("/psychologists", response_model=List[PsychologistSimple], 
            # 🟢 CORRECTION MAJEURE ICI : Ajout de "Psychologist" et "Assistant"
            dependencies=[Depends(role_required("ToxicoManager", "admin", "Psychologist", "SpiritualCounsellor", "Assistant"))])
def get_psychologists(
    ctrl: ToxicoController = Depends(get_toxico_controller) 
):
    return ctrl.get_psychologists_list()

@router.get("/patients", response_model=ToxicoListResponse)
def list_patients(
    search: str = Query(None),
    phase: int = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    # Cette route hérite des permissions du Router (qui incluent déjà Psychologist)
    items, total = ctrl.list_dossiers(search=search, phase=phase, page=page, per_page=per_page)
    data = [ctrl.map_dossier_to_list_item(item) for item in items]
    return {"data": data, "total": total, "page": page, "per_page": per_page}

@router.get("/patients/{patient_id}", response_model=Any)
def get_patient_detail(
    patient_id: int,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    dossier = ctrl.get_dossier_details(patient_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier Toxico introuvable")

    return ctrl.serialize_dossier_details(dossier)

@router.post("/admission", status_code=status.HTTP_201_CREATED,
             # Psychologist n'est PAS ici, c'est correct (il ne peut pas admettre)
             dependencies=[Depends(role_required("ToxicoManager", "admin", "Assistant"))])
async def admission_patient(
    request: Request,
    patientId: Optional[int] = Form(None),
    firstName: Optional[str] = Form(None),
    lastName: Optional[str] = Form(None),
    dob: Optional[date] = Form(None),
    mothersName: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    admissionDate: date = Form(...),
    substance: str = Form(...),
    psychologist: int = Form(...),
    guardianName: str = Form(...),
    guardianContact: str = Form(...),
    notes: Optional[str] = Form(None),
    consentFile: Optional[UploadFile] = File(None),
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        data = {
            "patient_id": patientId,
            "firstName": firstName, "lastName": lastName, "dob": dob, "mothersName": mothersName,
            "address": address, "contact": contact, "admissionDate": admissionDate,
            "substance": substance, "psychologist_id": psychologist,
            "guardianName": guardianName, "guardianContact": guardianContact, "notes": notes
        }
        base_url = str(request.base_url).rstrip("/")
        dossier = await ctrl.admission_patient(data=data, consent_file=consentFile, base_url=base_url) # type: ignore
        return {"message": "Admission réussie", "code_patient": dossier.patient.code_patient}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/evaluation", status_code=status.HTTP_200_OK,
             # 🟢 Psychologist est bien ici
             dependencies=[Depends(role_required("Psychologist", "SpiritualCounsellor", "admin"))])
def submit_evaluation(
    data: ToxicoEvaluationCreate,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        payload = data.model_dump()
        if not payload.get('dossier_id'):
            dossier = ctrl.get_dossier_details(payload['patientId'])
            if not dossier:
                raise ValueError("Dossier introuvable")
            payload['dossier_id'] = dossier.id

        ctrl.submit_evaluation(payload) 
        return {"message": "Évaluation enregistrée"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/discharge/{dossier_id}", status_code=status.HTTP_200_OK,
             dependencies=[Depends(role_required("ToxicoManager", "admin"))])
def discharge_patient(
    dossier_id: int,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        ctrl.discharge_patient(dossier_id)
        return {"message": "Dossier clôturé avec succès."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/stats/dashboard", response_model=Dict[str, Any], tags=["ToxicoStats"])
def get_dashboard_stats(ctrl: ToxicoController = Depends(get_toxico_controller)):
    # Hérite des permissions globales du router (donc Psychologist OK)
    admissions = ctrl.get_current_month_admissions_count()
    return {"currentMonthAdmissions": admissions}