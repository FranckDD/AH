# api_backend/backend_app/routes/doctor_dashboard/doctor_dashboard_endpoint.py
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .schemas import DoctorDashboardOut
from .doctors_schema import ActiveDoctorOut
from ...database import SessionLocal
from controller.doctor_dashboard_controller import DoctorDashboardController
from controller.appointment_controller import AppointmentController
from controller.medical_controller import MedicalRecordController
from controller.prescription_controller import PrescriptionController
from controller.hospitalization_controller import HospitalizationController
from repositories.user_repo import UserRepository
from api_backend.backend_app.routes.appointment.appointment_endpoints import get_appointment_controller
from api_backend.backend_app.routes.medical_records.medical_records_endpoint import get_medical_controller
from api_backend.backend_app.routes.prescription.prescriptions_endpoints import get_prescription_controller
from api_backend.backend_app.routes.hospitalizations.hospitalization_endpoint import get_hospitalization_controller
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

router = APIRouter(prefix="/doctor-dashboard", tags=["Tableau de bord medecin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_doctor_dashboard_controller(
    current_user=Depends(get_current_user),
    appointment_ctrl: AppointmentController = Depends(get_appointment_controller),
    medical_ctrl: MedicalRecordController = Depends(get_medical_controller),
    prescription_ctrl: PrescriptionController = Depends(get_prescription_controller),
    hospitalization_ctrl: HospitalizationController = Depends(get_hospitalization_controller),
) -> DoctorDashboardController:
    return DoctorDashboardController(
        appointment_ctrl=appointment_ctrl,
        medical_ctrl=medical_ctrl,
        prescription_ctrl=prescription_ctrl,
        hospitalization_ctrl=hospitalization_ctrl,
        current_user=current_user,
    )


@router.get(
    "/kpi",
    response_model=DoctorDashboardOut,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def get_kpi(
    start: date = Query(...),
    end: date = Query(...),
    ctrl: DoctorDashboardController = Depends(get_doctor_dashboard_controller),
):
    return ctrl.get_dashboard(start, end)


@router.get(
    "/doctors",
    response_model=list[ActiveDoctorOut],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def list_doctors(user_repo: UserRepository = Depends(get_user_repo)):
    return [
        ActiveDoctorOut(user_id=u.user_id, full_name=u.full_name)
        for u in user_repo.get_users_by_role_names(["medecin"])
    ]
