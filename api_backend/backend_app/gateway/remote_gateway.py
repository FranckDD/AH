#api_backend/app/gateway/remote_gateway.py
import os
import requests
from typing import Optional, Dict, Any, Union, List
from datetime import date, datetime
from functools import lru_cache
from api_backend.backend_app.config import AH2_API_BASE


class RemoteGateway:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or AH2_API_BASE).rstrip("/")
        if not self.base_url:
            raise RuntimeError("AH2_API_BASE non défini. Vérifiez .env dans le bundle EXE.")
        self.token = token

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def set_token(self, token: str):
        """Met à jour le token JWT (après login)"""
        self.token = token

    def is_online(self):
        """Vérifie si l'API est accessible."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False    

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
    
    def list_clinical_patients(self, page: int = 1, per_page: int = 20, search: Optional[str] = None):
        """Liste les patients Cliniques avec pagination et recherche"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if search:
            params["search"] = search
            
        # 🟢 Utilise l'endpoint /patients/clinical
        return self.request("GET", "/patients/clinical", params=params)

    def list_toxicology_patients(self, page: int = 1, per_page: int = 20, search: Optional[str] = None):
        """Liste les patients Toxicologie avec pagination et recherche"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if search:
            params["search"] = search
            
        # 🟢 Utilise l'endpoint /patients/toxicology
        return self.request("GET", "/patients/toxicology", params=params)

    def lists_spiritual_patients(self, page: int = 1, per_page: int = 20, search: Optional[str] = None):
        """Liste les patients Spirituels avec pagination et recherche"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if search:
            params["search"] = search
            
        # 🟢 Utilise l'endpoint /patients/spiritual/list
        return self.request("GET", "/patients/spiritual/list", params=params)

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
    

    # =========================================================================
    # --------------------
    # TOXICOLOGIE (TOXICO)
    # --------------------
    # =========================================================================

    def get_toxico_psychologists(self):
        """Récupère la liste des psychologues/gestionnaires Toxico pour les listes déroulantes."""
        return self.request("GET", "/toxico/psychologists")

    def list_toxico_dossiers(
        self, 
        page: int = 1, 
        per_page: int = 20, 
        search: Optional[str] = None, 
        phase: Optional[int] = None
    ) -> Dict[str, Any]:
        """Liste les dossiers Toxico actifs avec filtres et pagination."""
        params: Dict[str, Union[int, str]] = {
            "page": page,
            "per_page": per_page
        }
        if search:
            params["search"] = search
        if phase is not None:
            params["phase"] = phase
            
        return self.request("GET", "/toxico/patients", params=params)

    def get_toxico_dossier_details(self, patient_id: int) -> Dict[str, Any]:
        """Récupère tous les détails (historique, évaluations) d'un dossier Toxico."""
        return self.request("GET", f"/toxico/patients/{patient_id}")
    
    def get_toxico_patient_details(self, patient_id: int) -> Dict[str, Any]:
        """
        Récupère les détails complets d'un patient toxico.
        Inclut : informations patient, historique des phases, évaluations.
        """
        return self.request("GET", f"/toxico/patients/{patient_id}")
        
    def admit_toxico_patient(self, admission_data: dict) -> Dict[str, Any]:
        """
        Admet un patient dans le programme Toxico.
        Gère l'envoi en multipart/form-data pour supporter l'upload de fichier.
        """
        # 1. On fait une copie pour ne pas modifier le dictionnaire original
        form_data = admission_data.copy()
        
        # 2. On prépare le dictionnaire de fichiers
        files = None
        
        # On vérifie si la clé 'consentFile' existe et contient quelque chose
        if "consentFile" in form_data and form_data["consentFile"]:
            files = {"consentFile": form_data.pop("consentFile")}
        
        return self.request(
            "POST", 
            "/toxico/admission", 
            data=form_data,  # ⚠️ REMPLACE 'json=admission_data'
            files=files
        )

    def submit_toxico_evaluation(self, evaluation_data: dict) -> Dict[str, Any]:
        """Enregistre une nouvelle évaluation psychologique et met à jour la phase."""
        return self.request("POST", "/toxico/evaluation", json=evaluation_data)

    def discharge_toxico_patient(self, dossier_id: int) -> Dict[str, Any]:
        """Clôture le dossier et sort le patient du programme (discharge)."""
        return self.request("POST", f"/toxico/discharge/{dossier_id}")
    
    def get_dashboard_toxico_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques clés du tableau de bord Toxico 
        (ex: Admissions du mois, etc.)
        Endpoint: GET /toxico/stats/dashboard
        """
        # Utilisation de la méthode générique pour un GET sur le nouvel endpoint
        return self.request("GET", "/toxico/stats/dashboard")
    
    # --------------------
    # CONFIGURATION DE LA STRUCTURE (NOUVEAU)
    # --------------------

    def get_structure_info(self) -> Dict[str, Any]:
        """Récupère les informations de configuration de la structure."""
        return self.request("GET", "/config/structure")

    def update_structure_info(self, data: Dict[str, Any], logo_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Met à jour les informations de la structure, incluant potentiellement l'upload d'un logo.

        Args:
            data (Dict): Dictionnaire des champs textuels (name, slogan, address, etc.).
            logo_file_path (Optional[str]): Chemin local vers le fichier logo à uploader.
        """
        endpoint = "/config/structure"
        
        files = None
        if logo_file_path and os.path.exists(logo_file_path):
            # Préparation du fichier pour l'upload multipart
            # Clé 'logo' correspond au paramètre `logo: Optional[UploadFile] = File(None)` dans le router FastAPI
            files = {'logo': (os.path.basename(logo_file_path), open(logo_file_path, 'rb'), 'image/*')}
        
        # Les données textuelles sont envoyées comme `data` (form fields)
        response = self.request(
            method="POST", 
            endpoint=endpoint, 
            data=data, 
            files=files
        )
        
        # Fermeture du fichier après l'envoi
        if files:
            files['logo'][1].close()
        
        return response



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
    
    def get_patient_dme_summary(self, patient_id: int):
        """
        Récupère le résumé vital (Flash) pour l'en-tête du dossier patient.
        Endpoint: GET /medical_records/patient/{id}/dme_summary
        """
        return self.request("GET", f"/medical_records/patient/{patient_id}/dme_summary")
    
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
    

    def get_patient_prescriptions_history(self, patient_id: int, status: Optional[str] = None):
        """
        Récupère l'historique complet des prescriptions d'un patient.
        Endpoint: GET /prescriptions/patient/{id}
        """
        params = {}
        if status:
            params["status"] = status
        return self.request("GET", f"/prescriptions/patient/{patient_id}", params=params)

    
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
    
        # --------------------
    # USERS / ADMIN
    # --------------------
    def list_users(self, page: int = 1, per_page: int = 50, search: Optional[str] = None):
        params = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search
        return self.request("GET", "/users", params=params)

    def search_users(self, q: str):
        # Endpoint dédié /users/search?q=...
        params = {"q": q}  # si ton endpoint attend 'q' ou 'q' en query param
        # d'après ton router: /users/search?q=... -> Query param name 'q'
        return self.request("GET", "/users/search", params=params)

    def get_user(self, user_id: int):
        return self.request("GET", f"/users/{user_id}")

    def create_user(self, data: dict):
        return self.request("POST", "/users", json=data)

    def update_user(self, user_id: int, data: dict):
        return self.request("PUT", f"/users/{user_id}", json=data)

    def delete_user(self, user_id: int):
        return self.request("DELETE", f"/users/{user_id}")

    def _unwrap_list_response(self, res):
            # res may be list[str] or {"roles": [...]} or {"specialties":[...]}
            if isinstance(res, dict):
                # try common keys
                for k in ("roles", "specialties", "data", "items", "results"):
                    if k in res and isinstance(res[k], list):
                        return res[k]
                # If not found, try to guess first list value
                for v in res.values():
                    if isinstance(v, list):
                        return v
                return []
            if isinstance(res, list):
                return res
            # fallback
            return []

    def list_roles(self):
        res = self.request("GET", "/users/roles")
        return self._unwrap_list_response(res)

    def list_speciality(self):
        res = self.request("GET", "/users/specialties")
        return self._unwrap_list_response(res)
    

    # --------------------
    # CAISSE RETRAITS
    # --------------------
    def list_retraits(self, status: Optional[str] = None, date_from: Optional[Union[datetime, str]] = None, 
                     date_to: Optional[Union[datetime, str]] = None, page: int = 1, per_page: int = 50):
        """
        Liste les retraits avec filtres (status, date_from, date_to) et pagination.
        Endpoint: GET /retrait/
        """
        params = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        if date_from:
            params["date_from"] = date_from.isoformat() if isinstance(date_from, datetime) else str(date_from)
        if date_to:
            params["date_to"] = date_to.isoformat() if isinstance(date_to, datetime) else str(date_to)
        return self.request("GET", "/retrait/", params=params)

    def get_retrait(self, retrait_id: int):
        """
        Récupère un retrait par ID.
        Endpoint: GET /retrait/{retrait_id}
        """
        return self.request("GET", f"/retrait/{retrait_id}")

    def create_retrait(self, amount: float, justification: str):
        """
        Crée un nouveau retrait.
        Endpoint: POST /retrait/
        """
        data = {"amount": amount, "justification": justification}
        return self.request("POST", "/retrait/", json=data)

    def cancel_retrait(self, retrait_id: int, cancel_justification: str):
        """
        Annule un retrait existant.
        Endpoint: POST /retrait/{retrait_id}/cancel
        """
        data = {"cancel_justification": cancel_justification}
        return self.request("POST", f"/retrait/{retrait_id}/cancel", json=data)
    
    # Dans remote_gateway.py

    def get_total_retraits(self, status: str = None, date_from=None, date_to=None):
        """
        Calcule le total des retraits via l'API.
        Endpoint supposé: GET /retrait/total
        """
        params = {}
        if status:
            params["status"] = status
        
        if date_from:
            d_str = date_from.isoformat() if hasattr(date_from, 'isoformat') else str(date_from)
            # Force le début de journée si l'heure est absente
            if "T" not in d_str and len(d_str) <= 10:
                d_str += "T00:00:00"
            params["date_from"] = d_str

        if date_to:
            d_str = date_to.isoformat() if hasattr(date_to, 'isoformat') else str(date_to)
            # 🟢 CORRECTION CRITIQUE : Force la FIN de journée (23:59:59)
            if "T" not in d_str and len(d_str) <= 10:
                d_str += "T23:59:59"
            params["date_to"] = d_str
            
        return self.request("GET", "/retrait/total", params=params)
    
    # Dans remote_gateway.py

    def effectuer_retrait(self, amount: float, justification: str):
        """
        Crée un nouveau retrait.
        Endpoint: POST /retrait/
        """
        data = {
            "amount": amount, 
            "justification": justification
        }
        # Note: L'endpoint backend attend 'amount' et 'justification'
        return self.request("POST", "/retrait/", json=data)
    
    # --------------------
    # CAISSE TRANSACTIONS
    # --------------------

    def list_transactions(self, page: int = 1, per_page: int = 50, 
                          term: str = None, payment_method: str = None,
                          date_from: Union[date, str] = None, date_to: Union[date, str] = None):
        params = {
            "page": page,
            "per_page": per_page
        }
        if term: params["term"] = term
        if payment_method: params["payment_method"] = payment_method
        if date_from: params["date_from"] = str(date_from)
        if date_to: params["date_to"] = str(date_to)
        
        # L'API retourne maintenant { "data": [...], "meta": {...} }
        return self.request("GET", "/caisse/", params=params)

    def get_transaction(self, transaction_id: int):
        """
        Récupère une transaction spécifique par son ID.
        Endpoint: GET /caisse/{transaction_id}
        """
        return self.request("GET", f"/caisse/{transaction_id}")

    def list_transactions_by_patient(self, patient_id: int):
        """
        Récupère toutes les transactions d'un patient spécifique.
        Endpoint: GET /caisse/patient/{patient_id}
        """
        return self.request("GET", f"/caisse/patient/{patient_id}")

    def get_daily_total(self, for_date: Union[date, str]):
        """
        Récupère le total encaissé pour une date spécifique.
        Endpoint: GET /caisse/daily_total
        """
        date_str = for_date.isoformat() if isinstance(for_date, date) else str(for_date)
        params = {"for_date": date_str}
        return self.request("GET", "/caisse/daily_total", params=params)

    def get_total_transactions(self, status: str = None, date_from: Optional[Union[datetime, str]] = None, 
                               date_to: Optional[Union[datetime, str]] = None):
        """
        Calcule la somme des montants sur une période donnée via l'API.
        Endpoint: GET /caisse/total
        """
        params = {}
        # --- AJOUT ---
        if status:
            params["status"] = status
        if date_from:
            params["date_from"] = date_from.isoformat() if isinstance(date_from, datetime) else str(date_from)
        if date_to:
            params["date_to"] = date_to.isoformat() if isinstance(date_to, datetime) else str(date_to)
            
        return self.request("GET", "/caisse/total", params=params)

    def create_transaction(self, transaction_data: dict):
        """
        Crée une nouvelle transaction.
        Endpoint: POST /caisse/
        Payload attendu (transaction_data) :
          - payment_method (str)
          - transaction_type (str)
          - amount (float)
          - items (list[dict])
          - advance_amount (float)
          - patient_id, patient_label, note, etc.
        """
        # Assure-toi que les dates dans transaction_data sont sérialisées si nécessaire
        return self.request("POST", "/caisse/", json=transaction_data)

    def update_transaction(self, transaction_id: int, update_data: dict):
        """
        Met à jour une transaction existante.
        Endpoint: PUT /caisse/{transaction_id}
        """
        return self.request("PUT", f"/caisse/{transaction_id}", json=update_data)

    def cancel_transaction(self, transaction_id: int):
        """
        Annule une transaction (remet le stock, change le statut).
        Endpoint: POST /caisse/{transaction_id}/cancel
        Note: Cet endpoint ne prend pas de body json dans ton code actuel, juste l'ID dans l'URL.
        """
        return self.request("POST", f"/caisse/{transaction_id}/cancel")

    def delete_transaction(self, transaction_id: int):
        """
        Supprime définitivement une transaction (admin).
        Endpoint: DELETE /caisse/{transaction_id}
        """
        return self.request("DELETE", f"/caisse/{transaction_id}")
    
    def search_transactions(self, **kwargs):
        """
        Recherche les transactions dans l'API en utilisant les filtres (kwargs).
        kwargs inclut page, page_size, start_date, end_date, etc.
        Route Backend : GET /caisse/
        """
        # Utilise la méthode request du gateway pour faire un appel GET
        # kwargs sera automatiquement converti en paramètres de requête (ex: ?page=1&page_size=20)
        return self.request("GET", "/caisse/", params=kwargs)
    
    # --- NOUVELLE MÉTHODE POUR LE PAIEMENT ÉCHELONNÉ ---
    def add_installment_payment(self, transaction_id: int, payment_data: dict):
        """
        Ajoute un versement à une transaction pour solder la balance.
        Endpoint: POST /caisse/{transaction_id}/payment
        Payload attendu (payment_data) :
          - paid_amount (float)
          - payment_method (str)
          - note (str, optional)
        """
        return self.request("POST", f"/caisse/{transaction_id}/payment", json=payment_data)
    
    def settle_transaction(self, transaction_id: int):
        """
        Solde le reste à payer d'une transaction.
        Endpoint: POST /caisse/{transaction_id}/settle
        """
        return self.request("POST", f"/caisse/{transaction_id}/settle")
    
    def download_invoice_pdf(self, transaction_id: int):
        """
        Télécharge le fichier PDF de la facture en faisant un appel brut.
        """
        url = f"{self.base_url}/caisse/{transaction_id}/invoice/download"
        headers = self._headers() # Récupère les headers (token d'auth, etc.)
        
        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # Retourne le contenu binaire brut
                return response.content 
            else:
                # Gestion des erreurs HTTP
                response.raise_for_status() 
        except requests.exceptions.RequestException as e:
            #logger.error(f"Erreur de téléchargement du PDF: {e}")
            raise Exception(f"Erreur réseau/API lors du téléchargement: {e}")
        
        return None # En cas d'échec non géré
    
    # --------------------
    # CONSULTATIONS SPIRITUELLES
    # --------------------
    def list_consultations(self, page=None, per_page=None, search=None):
        params = {}
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page
        if search:
            params["search"] = search
        return self.request("GET", "/cs", params=params)

    def list_consultations_for_patient(self, patient_id: int):
        """
        Liste les consultations spirituelles pour un patient donné.
        Endpoint: GET /cs/patient/{patient_id}
        """
        return self.request("GET", f"/cs/patient/{patient_id}")
    
    def list_spiritual_patients(self):
        return self.request("GET", "/patients/spiritual")

    def get_last_consultation_for_patient(self, patient_id: int):
        """
        Récupère la dernière consultation spirituelle pour un patient.
        Endpoint: GET /cs/last/{patient_id}
        """
        return self.request("GET", f"/cs/last/{patient_id}")

    def get_consultation(self, cs_id: int):
        """
        Récupère une consultation spirituelle par ID.
        Endpoint: GET /cs/{cs_id}
        """
        return self.request("GET", f"/cs/{cs_id}")

    def create_consultation(self, consultation_data: dict):
        """
        Crée une nouvelle consultation spirituelle.
        Endpoint: POST /cs/
        """
        return self.request("POST", "/cs/", json=consultation_data)

    def update_consultation(self, cs_id: int, consultation_data: dict):
        """
        Met à jour une consultation spirituelle existante.
        Endpoint: PUT /cs/{cs_id}
        """
        return self.request("PUT", f"/cs/{cs_id}", json=consultation_data)

    def delete_consultation(self, cs_id: int):
        """
        Supprime une consultation spirituelle.
        Endpoint: DELETE /cs/{cs_id}
        """
        return self.request("DELETE", f"/cs/{cs_id}")

    def get_prayer_book_types(self):
        """Récupère la liste des types de Prayer Book depuis l'API"""
        return self.request("GET", "/cs/prayer-book-types")
    
    # --------------------
    # SPIRITUEL
    # --------------------
    
    
    def get_patient_spiritual_history(self, patient_id: int):
        """
        Appelle l'endpoint Backend pour l'historique spirituel.
        Route: GET /cs/patient/{id}/history
        """
        return self.request("GET", f"/cs/patient/{patient_id}/history")
    

    # --------------------
    # PHARMACY
    # --------------------
    def list_products(self, page: int = 1, per_page: int = 20, term: str = None, type_filter: str = None, status_filter: str = None):
        params = {
            "page": page,
            "per_page": per_page
        }
        if term:
            params["term"] = term
        if type_filter and type_filter != "Tous":
            params["type_filter"] = type_filter
        if status_filter and status_filter != "Tous":
            params["status_filter"] = status_filter
        return self.request("GET", "/pharmacy/", params=params)

    def get_product(self, medication_id: int):
        """Récupère un produit par ID."""
        return self.request("GET", f"/pharmacy/{medication_id}")

    def create_product(self, product_data: dict):
        """Crée un nouveau produit."""
        return self.request("POST", "/pharmacy/", json=product_data)

    def update_product(self, medication_id: int, product_data: dict):
        """Met à jour un produit existant."""
        return self.request("PUT", f"/pharmacy/{medication_id}", json=product_data)

    def delete_product(self, medication_id: int):
        """Supprime un produit."""
        return self.request("DELETE", f"/pharmacy/{medication_id}")

    def renew_stock(self, medication_id: int, added_quantity: int):
        """Réapprovisionne le stock d’un produit."""
        params = {"added_quantity": added_quantity}
        return self.request("POST", f"/pharmacy/{medication_id}/renew", params=params)

    def list_critical_products(self):
        """Liste les produits critiques ou épuisés."""
        return self.request("GET", "/pharmacy/alerts/critical")

    def list_expiring_products(self, days: int = 30):
        """Liste les produits proches de l’expiration."""
        params = {"days": days}
        return self.request("GET", "/pharmacy/alerts/expiring", params=params)
    
    def get_critical_stock_kpi(self) -> Dict:
        """
        Appelle l'endpoint Backend pour obtenir le nombre d'articles en stock critique.
        Endpoint: GET /pharmacy/kpi/critical_stock_count
        Retourne : {"stock_alerts_count": int}
        """
        return self.request("GET", "/pharmacy/kpi/critical_stock_count")
    
    def get_expiring_product_kpi(self, days: int = 30) -> Dict:
        """
        Appelle l'endpoint Backend pour obtenir le nombre de produits expirant bientôt.
        Endpoint: GET /pharmacy/kpi/expiring_product_count?days={days}
        Retourne : {"expiring_alerts_count": int}
        """
        params = {"days": days}
        return self.request("GET", "/pharmacy/kpi/expiring_product_count", params=params)

    # NOUVELLE MÉTHODE KPI 3
    def get_total_stock_value_kpi(self) -> Dict:
        """
        Appelle l'endpoint Backend pour obtenir la valeur monétaire totale du stock.
        Endpoint: GET /pharmacy/kpi/total_stock_value
        Retourne : {"total_stock_value": float}
        """
        return self.request("GET", "/pharmacy/kpi/total_stock_value")
    

    # --------------------
    # DASHBOARD / KPIs
    # --------------------
    
    def get_caisse_financial_kpis(self, date_from, date_to) -> Dict:
        """
        Appelle l'endpoint Backend pour récupérer les KPIs financiers de la caisse.
        Endpoint: GET /dashboard/caisse/kpis
        """
        # Gestion date début
        d_from_str = date_from.isoformat() if hasattr(date_from, 'isoformat') else str(date_from)
        if "T" not in d_from_str and len(d_from_str) <= 10:
             d_from_str += "T00:00:00"

        # Gestion date fin
        d_to_str = date_to.isoformat() if hasattr(date_to, 'isoformat') else str(date_to)
        
        # 🟢 CORRECTION CRITIQUE : Ajout de l'heure de fin pour inclure aujourd'hui
        if "T" not in d_to_str and len(d_to_str) <= 10:
             d_to_str += "T23:59:59"

        params = {
            "date_from": d_from_str,
            "date_to": d_to_str
        }
        return self.request("GET", "/dashboard/caisse/kpis", params=params)

    def get_caisse_unpaid_action_list(self, date_from: date, date_to: date) -> List[Dict]:
        """
        Appelle l'endpoint Backend pour récupérer la liste d'action des transactions impayées.
        Endpoint: GET /dashboard/caisse/unpaid
        """
        # Assurer que les dates sont au format 'YYYY-MM-DD' (ISO standard)
        params = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        }
        return self.request("GET", "/dashboard/caisse/unpaid", params=params)
    
    def get_caisse_payment_distribution(self, date_from: date, date_to: date) -> Dict[str, Any]:
        """
        Récupère la répartition de l'encaissement par mode de paiement.
        Endpoint: GET /caisse/dashboard/caisse/payment_distribution
        """
        params = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        }
        return self.request("GET", "/caisse/dashboard/caisse/payment_distribution", params=params)
    
    def get_total_payments(self, status: str = None, date_from: Optional[Union[datetime, str]] = None, 
                           date_to: Optional[Union[datetime, str]] = None):
        """
        Calcule la somme des ENCAISSEMENTS RÉELS (advance_amount) via l'API.
        Endpoint: GET /caisse/total_payments
        """
        params = {}
        if status:
            params["status"] = status
        if date_from:
            params["date_from"] = date_from.isoformat() if hasattr(date_from, 'isoformat') else str(date_from)
        if date_to:
            params["date_to"] = date_to.isoformat() if hasattr(date_to, 'isoformat') else str(date_to)
            
        return self.request("GET", "/caisse/total_payments", params=params)
    
    def get_total_remaining_due(self, status: str = None, date_from: Optional[Union[datetime, str]] = None, 
                                date_to: Optional[Union[datetime, str]] = None):
        """
        Calcule la somme totale des montants restant dûs via l'API.
        Endpoint: GET /caisse/total_remaining_due
        """
        params = {}
        if status:
            params["status"] = status
        if date_from:
            params["date_from"] = date_from.isoformat() if hasattr(date_from, 'isoformat') else str(date_from)
        if date_to:
            params["date_to"] = date_to.isoformat() if hasattr(date_to, 'isoformat') else str(date_to)
            
        return self.request("GET", "/caisse/total_remaining_due", params=params)
    
    def get_critical_stock_count_kpi(self):
        """KPI : Nombre de produits en rupture ou stock critique."""
        # Assurez-vous que l'endpoint existe côté backend (ex: /pharmacy/kpi/critical_count)
        return self.request("GET", "/pharmacy/kpi/critical_count")

    def get_expiring_product_count_kpi(self, days: int = 30):
        """KPI : Nombre de produits périmés ou bientôt périmés."""
        params = {"days": days}
        return self.request("GET", "/pharmacy/kpi/expiring_count", params=params)

    def list_critical_or_empty(self):
        """Liste des produits en alerte pour le tableau."""
        return self.request("GET", "/pharmacy/critical_list")
    
    def get_spiritual_new_patients_kpi(self, period: str = "week") -> Dict:
        """
        Appelle l'endpoint Backend pour obtenir le nombre de nouveaux patients Spirituels.
        Endpoint: GET /patient/kpi/spiritual/new_patients_count?period={period}
        Retourne : {"new_patients_count": int}
        """
        params = {"period": period}
        return self.request("GET", "/patient/kpi/spiritual/new_patients_count", params=params)
    
    # --------------------
    # PHARMACY - KPIs DASHBOARD
    # --------------------

    def get_dashboard_critical_stock_kpi(self):
        """
        KPI DASHBOARD : Nombre de produits en rupture ou stock critique.
        (Appel la route qui renvoie le COUNT, non la liste.)
        Endpoint: GET /pharmacy/kpi/critical_stock_count
        """
        return self.request("GET", "/pharmacy/kpi/critical_stock_count")

    def get_dashboard_expiring_stock_kpi(self, days: int = 30):
        """
        KPI DASHBOARD : Nombre de produits périmés ou bientôt périmés (dans {days} jours).
        Endpoint: GET /pharmacy/kpi/expiring_product_count
        """
        params = {"days": days}
        return self.request("GET", "/pharmacy/kpi/expiring_product_count", params=params)

    def list_dashboard_critical_products(self):
        """
        Liste détaillée des produits en alerte, spécifiquement pour le tableau du Dashboard.
        Utilise l'endpoint générique /pharmacy/ avec le filtre 'critical=True'.
        """
        # Limité à 5 résultats pour l'affichage dans le petit tableau
        return self.request("GET", "/pharmacy/", params={"critical": True, "per_page": 5})

    def get_dashboard_total_stock_value_kpi(self) -> Dict:
        """
        KPI DASHBOARD : Valeur monétaire totale du stock disponible.
        Endpoint: GET /pharmacy/kpi/total_stock_value
        """
        return self.request("GET", "/pharmacy/kpi/total_stock_value")
    
    # 🟢 NOUVELLES MÉTHODES KPI (DASHBOARD)

    def get_pharmaceutique_count_kpi(self) -> Dict:
        """
        Récupère le nombre de produits 'pharmaceutique'.
        Endpoint: /pharmacy/kpi/pharmaceutique_count
        """
        return self.request("GET", "/pharmacy/kpi/pharmaceutique_count")

    def get_naturel_count_kpi(self) -> Dict:
        """
        Récupère le nombre de produits 'Naturel'.
        Endpoint: /pharmacy/kpi/naturel_count
        """
        return self.request("GET", "/pharmacy/kpi/naturel_count")

    def get_stock_dashboard_stats(self) -> Dict:
        """
        Récupère TOUTES les statistiques du tableau de bord en un seul appel.
        Endpoint: /pharmacy/kpi/dashboard_stats
        Retourne : {
            "totalValue": float,
            "countPharma": int,
            "countNatural": int,
            "lowStockAlerts": int,
            "expiredCount": int
        }
        """
        return self.request("GET", "/pharmacy/kpi/dashboard_stats")

    # NOUVELLE MÉTHODE KPI 2 : Statut Actif/Inactif Spirituel
    def get_spiritual_status_distribution_kpi(self) -> Dict:
        """
        Appelle l'endpoint Backend pour obtenir la distribution Actif/Inactif des patients Spirituels.
        Endpoint: GET /patient/kpi/spiritual/status_distribution
        Retourne : {"active_patients_count": int, "inactive_patients_count": int, "total_patients_count": int}
        """
        return self.request("GET", "/patient/kpi/spiritual/status_distribution")

    # NOUVELLE MÉTHODE KPI 3 : Répartition Assurance Spirituelle
    def get_spiritual_assurance_distribution_kpi(self) -> Dict:
        """
        Appelle l'endpoint Backend pour obtenir la répartition Assurance des patients Spirituels.
        Endpoint: GET /patient/kpi/spiritual/assurance_distribution
        Retourne : {"assurance_distribution": Dict[str, int]}
        """
        return self.request("GET", "/patient/kpi/spiritual/assurance_distribution")
    

    # --------------------
    # Laboratoire 🟢 AJOUTS CRUD EXAMEN
    # --------------------
    def list_examens(self):
        """
        Récupère la liste complète des examens depuis l'API.
        Route Backend: GET /labo/
        """
        return self.request("GET", "/labo/")
    
    def create_examen(self, data: Dict[str, Any]):
        """
        Crée un nouvel examen.
        Route Backend: POST /labo/exams
        """
        return self.request("POST", "/labo/exams", json=data)

    def update_examen(self, examen_id: int, data: Dict[str, Any]):
        """
        Met à jour un examen existant.
        Route Backend: PUT /labo/exams/{examen_id}
        """
        return self.request("PUT", f"/labo/exams/{examen_id}", json=data)

    def delete_examen(self, examen_id: int):
        """
        Supprime un examen.
        Route Backend: DELETE /labo/exams/{examen_id}
        """
        # Le backend renvoie 204 No Content, donc on gère le statut plutôt que le JSON.
        response = self.request("DELETE", f"/labo/exams/{examen_id}")
        if isinstance(response, dict) and "_status_code" in response:
             return response["_status_code"] == 200
        # Si la requête réussit sans corps, requests.request peut ne pas retourner de JSON.
        # Nous modifions request pour capturer le statut HTTP si l'appel réussit mais ne renvoie pas de JSON.
        # Pour une méthode DELETE qui renvoie 204, on suppose que le succès est 204.
        return response

    
    def get_patient_lab_history(self, patient_id: int):
        """
        Récupère l'historique des résultats labo pour un patient.
        Endpoint: GET /labo/patient/{id}/history
        """
        return self.request("GET", f"/labo/patient/{patient_id}/history")
    

    #-----------
    # Log Actions
    #------------
    def get_total_retraits(self, status: str = None, date_from=None, date_to=None):
        """
        Calcule le total des retraits via l'API, en assurant une plage de temps complète.
        """
        params = {}
        if status:
            params["status"] = status
        
        if date_from:
            d_str = date_from.isoformat() if hasattr(date_from, 'isoformat') else str(date_from)
            # Force le début de journée si l'heure est absente
            if "T" not in d_str and len(d_str) <= 10:
                d_str += "T00:00:00"
            params["date_from"] = d_str

        if date_to:
            d_str = date_to.isoformat() if hasattr(date_to, 'isoformat') else str(date_to)
            # Correction: Force la FIN de journée (23:59:59)
            if "T" not in d_str and len(d_str) <= 10:
                d_str += "T23:59:59"
            params["date_to"] = d_str
            
        return self.request("GET", "/retrait/total", params=params)

    def get_caisse_financial_kpis(self, date_from: date, date_to: date) -> Dict:
        """
        Appelle l'endpoint Backend pour récupérer les KPIs financiers de la caisse.
        """
        # Assurer que les dates incluent la fin de journée
        d_from_str = date_from.isoformat() if hasattr(date_from, 'isoformat') else str(date_from)
        if "T" not in d_from_str and len(d_from_str) <= 10:
             d_from_str += "T00:00:00"

        d_to_str = date_to.isoformat() if hasattr(date_to, 'isoformat') else str(date_to)
        if "T" not in d_to_str and len(d_to_str) <= 10:
             d_to_str += "T23:59:59"

        params = {
            "date_from": d_from_str,
            "date_to": d_to_str
        }
        return self.request("GET", "/dashboard/caisse/kpis", params=params)
        
        
    # --- 2. FONCTIONS D'AUDIT (NOUVELLES) ---
    
    def list_access_logs(self, page: int = 1, per_page: int = 20, user_id: Optional[int] = None, 
                         date_from: Optional[date] = None, date_to: Optional[date] = None, 
                         action_type: Optional[str] = None) -> Dict:
        """
        Récupère les logs d'accès (Login/Logout) paginés.
        Endpoint: GET /audit/access
        """
        params = {
            "page": page,
            "per_page": per_page,
            "user_id": user_id,
            "action_type": action_type
        }
        # Convertir les dates si elles existent
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
            
        # Nettoyage des paramètres None avant envoi (important pour les requêtes GET)
        cleaned_params = {k: v for k, v in params.items() if v is not None}
        
        return self.request("GET", "/audit/access", params=cleaned_params)

    def list_action_logs(self, page: int = 1, per_page: int = 20, user_id: Optional[int] = None, 
                         date_from: Optional[date] = None, date_to: Optional[date] = None, 
                         resource_type: Optional[str] = None) -> Dict:
        """
        Récupère les logs d'actions métier (CRUD) paginés.
        Endpoint: GET /audit/actions
        """
        params = {
            "page": page,
            "per_page": per_page,
            "user_id": user_id,
            "resource_type": resource_type
        }
        # Convertir les dates si elles existent
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
            
        # Nettoyage des paramètres None
        cleaned_params = {k: v for k, v in params.items() if v is not None}
        
        return self.request("GET", "/audit/actions", params=cleaned_params)
