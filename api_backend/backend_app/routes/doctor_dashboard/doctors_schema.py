# api_backend/backend_app/routes/doctor_dashboard/doctors_schema.py
from pydantic import BaseModel


class ActiveDoctorOut(BaseModel):
    user_id: int
    full_name: str
