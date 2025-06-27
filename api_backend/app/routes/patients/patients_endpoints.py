# api_backend/app/routes/patients/patients_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List

from .patients_schemas import PatientCreate, PatientUpdate, PatientResponse
from app.database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from app.routes.auth.auth_endpoints import get_current_user

router = APIRouter(prefix="/patients", tags=["Patients"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_patient_controller(current_user=Depends(get_current_user),
                           db: Session = Depends(get_db)) -> PatientController:
    auth_ctrl = AuthController(db_session=db)
    return PatientController(repo=auth_ctrl.patient_repo, current_user=current_user)

@router.get("/", response_model=List[PatientResponse])
def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    patients = patient_ctrl.list_patients(page=page, per_page=per_page, search=search)
    return patients

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    p = patient_ctrl.get_patient(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    return p

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    data: PatientCreate,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    pid, msg = patient_ctrl.create_patient(data.dict())
    patient = patient_ctrl.repo.get_by_id(pid)
    return patient

@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    data: PatientUpdate,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    patient_ctrl.update_patient(patient_id, data.dict(exclude_unset=True))
    patient = patient_ctrl.repo.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    return patient

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    success = patient_ctrl.delete_patient(patient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
