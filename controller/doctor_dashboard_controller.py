# controller/doctor_dashboard_controller.py
import os
import json
import logging
from datetime import date
from dotenv import load_dotenv
import redis

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

logger = logging.getLogger(__name__)


class DoctorDashboardController:
    """Composition pure : agrege les KPI deja exposes par les
    controllers RDV/dossiers medicaux/prescriptions/hospitalisations en
    une seule reponse, avec degradation par carte (jamais d'echec global
    pour une seule source en panne) et un cache Redis sur le resultat
    compose complet."""

    def __init__(self, appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl, current_user):
        self.appointment_ctrl = appointment_ctrl
        self.medical_ctrl = medical_ctrl
        self.prescription_ctrl = prescription_ctrl
        self.hospitalization_ctrl = hospitalization_ctrl
        self.user = current_user

    def _doctor_id(self):
        return getattr(self.user, "user_id", None)

    def _safe(self, fn, default, field_name):
        try:
            return fn()
        except Exception:
            logger.exception("Echec composition tableau de bord medecin, champ=%s", field_name)
            self._any_degraded = True
            return default

    def get_dashboard(self, start: date, end: date) -> dict:
        doctor_id = self._doctor_id()
        CACHE_KEY = f"doctor_dashboard:kpi:{doctor_id}:{start}:{end}"
        self._any_degraded = False

        try:
            cached = redis_client.get(CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        result = {
            "total_appointments": self._safe(
                lambda: self.appointment_ctrl.total_appointments(doctor_id, start, end), 0, "total_appointments"
            ),
            "count_by_status": self._safe(
                lambda: self.appointment_ctrl.count_by_status(doctor_id, start, end), {}, "count_by_status"
            ),
            "distinct_patients": self._safe(
                lambda: self.appointment_ctrl.distinct_patients_count(doctor_id, start, end), 0, "distinct_patients"
            ),
            "medical_records_count": self._safe(
                lambda: self.medical_ctrl.count_records_for_doctor(doctor_id, start, end), 0, "medical_records_count"
            ),
            "consultation_distribution": self._safe(
                lambda: self.medical_ctrl.consultation_type_distribution(doctor_id, start, end), {}, "consultation_distribution"
            ),
            "prescriptions_count": self._safe(
                lambda: self.prescription_ctrl.count_prescriptions(doctor_id=doctor_id, start=start, end=end), 0, "prescriptions_count"
            ),
            "hospitalizations_current_count": self._safe(
                lambda: self.hospitalization_ctrl.count_current(), 0, "hospitalizations_current_count"
            ),
        }

        if not self._any_degraded:
            try:
                redis_client.setex(CACHE_KEY, 300, json.dumps(result))
            except Exception:
                pass

        return result
