#api_backend/app/gateway/remote_gateway.py
import requests
from typing import Optional, Dict, Any, Union
from datetime import date, datetime


class RemoteGateway:
    def __init__(self, base_url="http://127.0.0.1:8000", token=None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def set_token(self, token: str):
        """Met à jour le token JWT (après login)"""
        self.token = token

    def request(self, method: str, endpoint: str, params=None, data=None, json=None):
        """Méthode générique pour appeler l’API"""
        url = f"{self.base_url}{endpoint}"
        response = None   # <-- initialisation pour éviter l'erreur Pylance
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=self._headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            if response is not None:
                return {"error": f"HTTP {response.status_code}", "details": response.text}
            return {"error": "HTTP error", "details": "No response received"}
        except requests.exceptions.RequestException as e:
            return {"error": "Network error", "details": str(e)}

    # --------------------
    # AUTH
    # --------------------
    def login(self, username: str, password: str):
            """Connexion utilisateur via OAuth2PasswordRequestForm"""
            url = f"{self.base_url}/auth/login"
            form_data = {"username": username, "password": password}

            try:
                response = requests.post(
                    url, data=form_data,
                    headers={"Accept": "application/json"},
                    timeout=10
                )
                try:
                    res = response.json()
                except ValueError:
                    res = {"error": "Invalid response", "details": response.text}

                if isinstance(res, dict):
                    res["_status_code"] = response.status_code #type:ignore

                if response.status_code == 200 and isinstance(res, dict) and "access_token" in res:
                    self.token = res["access_token"]

                return res

            except requests.exceptions.RequestException as e:
                return {"error": "Network error", "details": str(e), "_status_code": None}


    # --------------------
    # PATIENTS
    # --------------------
    def create_patient(self, patient_data: dict):
        return self.request("POST", "/patients/", json=patient_data)

    def get_patient(self, patient_id: int):
        return self.request("GET", f"/patients/{patient_id}")

    def list_patients(self, page: int = 1, per_page: int = 20, search: Optional[str] = None):
        """Liste les patients avec pagination et recherche"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if search:
            params["search"] = search
        return self.request("GET", "/patients/", params=params)

    def update_patient(self, patient_id: int, patient_data: dict):
        return self.request("PUT", f"/patients/{patient_id}", json=patient_data)

    def delete_patient(self, patient_id: int):
        return self.request("DELETE", f"/patients/{patient_id}")
    
    def find_patient_by_code(self, code: str):
        """Recherche un patient par son code"""
        params = {"search": code}
        return self.request("GET", "/patients/", params=params)
    
    def find_patient_for_prescription(self, query: str):
        """
        Appelle l'endpoint /patients/find_presc?q=...
        """
        params = {"q": query}
        return self.request("GET", "/patients/find_presc", params=params)


    # --------------------
    # RENDEZ-VOUS (Appointments)
    # --------------------
    def create_appointment(self, appointment_data: dict):
        return self.request("POST", "/appointments/", json=appointment_data)

    def get_appointment(self, appointment_id: int):
        return self.request("GET", f"/appointments/{appointment_id}")

    def list_appointments(self, page: int = 1, per_page: int = 20, 
                         date_from: Optional[str] = None, date_to: Optional[str] = None,
                         doctor_id: Optional[int] = None, patient_id: Optional[int] = None):
        """Liste les rendez-vous avec filtres"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if doctor_id:
            params["doctor_id"] = doctor_id
        if patient_id:
            params["patient_id"] = patient_id
        return self.request("GET", "/appointments/", params=params)

    def get_upcoming_appointments(self, limit=5):
        return self.request("GET", "/appointments/upcoming", params={"limit": limit})

    def update_appointment(self, appointment_id: int, appointment_data: dict):
        return self.request("PUT", f"/appointments/{appointment_id}", json=appointment_data)

    def delete_appointment(self, appointment_id: int):
        return self.request("DELETE", f"/appointments/{appointment_id}")
    
    def find_patient_for_appointment(self, code: str):
        """
        Recherche un patient unique pour la prise de RDV (endpoint dédié).
        Renvoie un objet patient (dict) ou un dict d'erreur.
        """
        params = {"code": code}
        return self.request("GET", "/patients/find_for_appointment", params=params)


    # --------------------
    # DOSSIERS MÉDICAUX (Medical Records)
    # --------------------

    def get_medical_record(self, record_id: int):
        return self.request("GET", f"/medical_records/{record_id}")

    def list_medical_records_by_patient(self, patient_id: int):
        return self.request("GET", f"/medical_records/by_patient/{patient_id}")

    def update_medical_record(self, record_id: int, record_data: dict):
        return self.request("PUT", f"/medical_records/{record_id}", json=record_data)

    def delete_medical_record(self, record_id: int):
        return self.request("DELETE", f"/medical_records/{record_id}")
    
        # --------------------
    # DOSSIERS MÉDICAUX (Medical Records) - Méthodes manquantes
    # --------------------

    def list_medical_records(self, page: int = 1, per_page: int = 20, 
                           patient_id: Optional[int] = None,
                           date_from: Optional[str] = None, 
                           date_to: Optional[str] = None,
                           motif_code: Optional[str] = None,
                           severity: Optional[str] = None,
                           search: Optional[str] = None):
        """Liste les dossiers médicaux avec filtres"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if patient_id:
            params["patient_id"] = patient_id
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if motif_code:
            params["motif_code"] = motif_code
        if severity:
            params["severity"] = severity
        if search:
            params["search"] = search
            
        return self.request("GET", "/medical_records/", params=params)

    def list_motifs(self):
        """Liste tous les motifs disponibles"""
        return self.request("GET", "/medical_records/motifs")
    

    # --------------------
    # PRESCRIPTIONS
    # --------------------
    def create_prescription(self, prescription_data: dict):
        return self.request("POST", "/prescriptions/", json=prescription_data)

    def get_prescription(self, prescription_id: int):
        return self.request("GET", f"/prescriptions/{prescription_id}")

    def list_prescriptions_by_patient(self, patient_id: int):
        return self.request("GET", f"/prescriptions/by_patient/{patient_id}")

    def update_prescription(self, prescription_id: int, prescription_data: dict):
        return self.request("PUT", f"/prescriptions/{prescription_id}", json=prescription_data)

    def delete_prescription(self, prescription_id: int):
        return self.request("DELETE", f"/prescriptions/{prescription_id}")
    
    def list_prescriptions(self, page: int = 1, per_page: int = 20,
                           patient_id: Optional[int] = None,
                           medical_record_id: Optional[int] = None,
                           date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           search: Optional[str] = None):
        """
        Liste les prescriptions (pagination + filtres).
        Garde le même pattern que list_medical_records / list_patients.
        """
        params = {"page": page, "per_page": per_page}
        if patient_id:
            params["patient_id"] = patient_id
        if medical_record_id:
            params["medical_record_id"] = medical_record_id
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if search:
            params["search"] = search
        return self.request("GET", "/prescriptions/", params=params)

    
        # --------------------
    # DOSSIERS MÉDICAUX (Medical Records)
    # --------------------
    def create_medical_record(self, record_data: dict):
        return self.request("POST", "/medical_records/", json=record_data)


    def find_patient(self, query: str):
        """Recherche un patient par ID ou code"""
        params = {"q": query}
        return self.request("GET", "/medical_records/find_patient", params=params)

    def get_last_for_patient(self, patient_id: int):
        """Récupère le dernier dossier d'un patient"""
        return self.request("GET", f"/medical_records/last_for_patient/{patient_id}")

    def count_records_for_doctor(self, doctor_id: Optional[int] = None, 
                               start: Optional[str] = None, 
                               end: Optional[str] = None):
        """Compte les dossiers pour un médecin sur une période"""
        params = {}
        if doctor_id:
            params["doctor_id"] = doctor_id
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self.request("GET", "/medical_records/kpi/count_records", params=params)

    def consultation_type_distribution(self, doctor_id: Optional[int] = None,
                                    start: Optional[str] = None,
                                    end: Optional[str] = None):
        """Distribution des types de consultation"""
        params = {}
        if doctor_id:
            params["doctor_id"] = doctor_id
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self.request("GET", "/medical_records/kpi/consultation_distribution", params=params)

    def count_preconsultations(self, period: str = "day"):
        """Compte les préconsultations"""
        params = {"period": period}
        return self.request("GET", "/medical_records/kpi/count_preconsultations", params=params)

    def count_consultations(self, period: str = "day"):
        """Compte les consultations"""
        params = {"period": period}
        return self.request("GET", "/medical_records/kpi/count_consultations", params=params)
    

        # Ajoutez ces méthodes à votre classe RemoteGateway

    def get_distinct_patients_count(self, start, end):
        start_str = start.isoformat() if hasattr(start, 'isoformat') else str(start)
        end_str = end.isoformat() if hasattr(end, 'isoformat') else str(end)
        params = {"start_date": start_str, "end_date": end_str}
        return self.request("GET", "/appointments/kpi/distinct_patients", params=params)

    def get_total_appointments(self, start, end):
        start_str = start.isoformat() if hasattr(start, 'isoformat') else str(start)
        end_str = end.isoformat() if hasattr(end, 'isoformat') else str(end)
        params = {"start_date": start_str, "end_date": end_str}
        return self.request("GET", "/appointments/kpi/total", params=params)
    

    def get_appointments_status_count(self, start, end):
        start_str = start.isoformat() if hasattr(start, 'isoformat') else str(start)
        end_str = end.isoformat() if hasattr(end, 'isoformat') else str(end)
        params = {"start_date": start_str, "end_date": end_str}
        return self.request("GET", "/appointments/kpi/count_by_status", params=params)

    def get_registered_patients_count(self, period):
        """Compte les patients enregistrés sur une période (day, week, month)"""
        return self.request("GET", f"/stats/patients/registered/{period}")

    def get_consultations_count(self, period):
        """Compte les consultations sur une période (day, week, month)"""
        return self.request("GET", f"/stats/consultations/{period}")

    def get_prescriptions_count(self, period):
        """Compte les prescriptions sur une période (day, week, month)"""
        return self.request("GET", "/prescriptions/kpi/count", params={"period": period})

    def get_medical_records(self, page=1, per_page=10):
        """Liste les dossiers médicaux"""
        skip = (page - 1) * per_page
        return self.request("GET", "/medical_records/", params={"skip": skip, "limit": per_page})

    def get_appointments_time_series(self, start, end):
        start_str = start.isoformat() if hasattr(start, 'isoformat') else str(start)
        end_str = end.isoformat() if hasattr(end, 'isoformat') else str(end)
        params = {"start_date": start_str, "end_date": end_str}
        return self.request("GET", "/appointments/kpi/time_series", params=params)

    def get_appointments_by_day(self, date_val):
        date_str = date_val.isoformat() if hasattr(date_val, 'isoformat') else str(date_val)
        return self.request("GET", f"/appointments/by-day/{date_str}")

    def get_today_appointments(self):
        return self.request("GET", "/appointments/upcoming_today")


    def get_patients_registered_on(self, date_val):
        """Récupère les patients enregistrés à une date spécifique"""
        date_str = date_val.isoformat() if hasattr(date_val, 'isoformat') else str(date_val)
        return self.request("GET", f"/patients/registered-on/{date_str}")
    
    def get_new_patients_by_day(self, target_date: date, doctor_id: Optional[int] = None, page: int = 1, per_page: int = 200):
        dstr = target_date.isoformat() if isinstance(target_date, date) else str(target_date)
        params = {"target_date": dstr, "page": page, "per_page": per_page}
        if doctor_id:
            params["doctor_id"] = doctor_id
        return self.request("GET", "/patients/for_days", params=params)

        # --------------------
    # APPOINTMENTS - SPECIALTIES
    # --------------------
    def list_specialties(self):
        """Récupère la liste des spécialités (endpoint: GET /appointments/specialties)."""
        return self.request("GET", "/appointments/specialties")

    # --------------------
    # PATIENTS - find by code (endpoint exists /patients/find_by_code?code=..)
    # --------------------
    def find_patient_by_code(self, code: str):
        """Recherche un patient par code via endpoint dédié."""
        return self.request("GET", "/patients/find_by_code", params={"code": code})
    
    def get_registered_patients_count(self, period):
        return self.request("GET", "/patients/count_registered", params={"period": period})
    

    # --------------------
    # APPOINTMENTS - alias/update helper
    # --------------------
    def modify_appointment(self, appointment_id: int, appointment_data: dict):
        """
        Wrapper par nom “modify_appointment” -> appelle PUT /appointments/{appointment_id}
        utile pour compatibilité avec controller.modify_appointment name.
        """
        return self.request("PUT", f"/appointments/{appointment_id}", json=appointment_data)

    # NB: create_appointment, get_appointment, list_appointments, delete_appointment, etc.
    # should déjà être présents dans cette classe (vérifie).
    
        # APPOINTMENTS actions
    def accept_appointment(self, appointment_id: int):
        """POST /appointments/{id}/accept"""
        return self.request("POST", f"/appointments/{appointment_id}/accept")

    def cancel_appointment(self, appointment_id: int):
        """POST /appointments/{id}/cancel"""
        return self.request("POST", f"/appointments/{appointment_id}/cancel")

    def complete_appointment(self, appointment_id: int):
        """POST /appointments/{id}/complete"""
        return self.request("POST", f"/appointments/{appointment_id}/complete")
    
    def get_renewals_for_doctor(self, within_days=14):
        return self.request("GET", "/prescriptions/renewals", params={"within_days": within_days})
    
    def get_prescriptions_count(self, period):
    # update to call new endpoint
        return self.request("GET", "/prescriptions/kpi/count", params={"period": period})