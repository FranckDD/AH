# api_backend/backend_app/routes/doctor_dashboard/schemas.py
from typing import Dict
from pydantic import BaseModel


class DoctorDashboardOut(BaseModel):
    total_appointments: int
    count_by_status: Dict[str, int]
    distinct_patients: int
    medical_records_count: int
    consultation_distribution: Dict[str, int]
    prescriptions_count: int
    hospitalizations_current_count: int
