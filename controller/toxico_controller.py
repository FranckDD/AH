# Fichier: controllers/toxico_controller.py
import os
import shutil
import json
import redis
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from fastapi import UploadFile
from celery import Task # Pour le typage

# 📂 Configuration du dossier d'upload pour Toxico
UPLOAD_DIR = "static/uploads/toxico_consents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from repositories.toxico_repo import ToxicoRepository
from repositories.patient_repo import PatientRepository
from api_backend.backend_app.utils.file_storage import save_consent_file # Assurez-vous que ce chemin est correct selon votre structure

from controller.patient_controller import PatientController 
from repositories.audit_repo import AuditRepository

# Import de la tâche Celery (ajustez le chemin si nécessaire, ex: tasks.toxico_tasks)
from tasks.toxico_tasks import task_process_post_admission # type: ignore
# Typage pour l'IDE
task_process_post_admission: Task = task_process_post_admission # type: ignore

# Configuration Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class ToxicoController:
    # 🎯 Retrait de l'audit_repo de la signature du constructeur
    def __init__(
        self, 
        repo: ToxicoRepository, 
        patient_controller: PatientController, 
        current_user: Any
    ):
        self.repo = repo
        self.patient_controller = patient_controller 
        self.user = current_user
        

    # --- LECTURE (Avec Cache Redis) ---

    def get_psychologists_list(self) -> List[Dict]:
        """Récupère la liste des psy avec mise en cache Redis (1h)."""
        CACHE_KEY = "toxico:cache:psychologists_list"

        # 1. Vérification du cache (Redis indisponible = pas bloquant,
        # meme pattern defensif que patient_controller.get_global_counts -
        # sans ce garde-fou, un Redis injoignable faisait planter toute la
        # requete en 500, masque en CORS cote navigateur).
        try:
            cached_data = redis_client.get(CACHE_KEY)
            if cached_data:
                return json.loads(cached_data) # type: ignore
        except Exception: pass

        # 2. Lecture DB
        users = self.repo.get_psychologists()
        result = [{"id": u.user_id, "name": f"{u.full_name}"} for u in users]

        # 3. Mise en cache (TTL 3600s)
        try:
            redis_client.setex(CACHE_KEY, 3600, json.dumps(result))
        except Exception: pass

        return result

    def list_dossiers(self, search: str = None, phase: int = None, page: int = 1, per_page: int = 20): # type: ignore
        """
        Liste optimisée pour le tableau de bord avec pagination.
        Retourne les objets ORM et le total.
        """
        # Le Repo fait le travail lourd (JOIN, FILTRE, PAGINATION)
        return self.repo.search_dossiers(search, phase, page, per_page)

    def map_dossier_to_list_item(self, d):
        """Helper pour mapper l'objet ORM vers le format liste attendu par le Front"""
        # Mapping léger pour la liste reste dans le Controller (méthode utilitaire)
        return {
            "patient_id": d.patient_id,
            "dossier_id": d.id,
            "patientName": f"{d.patient.first_name} {d.patient.last_name}",
            "code": d.patient.code_patient,
            "substance": d.substance,
            "currentPhase": d.current_phase,
            "relapseCount": d.relapse_count,
            "psychologist": d.psychologist.full_name if d.psychologist else "Non assigné",
            # Sans cette date, le badge "+X cette semaine" et l'alerte
            # "evaluation en retard" de ToxicoList.vue ne se declenchent jamais.
            "admissionDate": d.admission_date,
        }

    def get_dossier_details(self, patient_id: int):
        """Détail complet pour la modale dossier. Retourne l'objet ORM complet."""
        # Le Repo charge toutes les relations nécessaires (Eager Loading)
        return self.repo.get_dossier_full(patient_id)

    def serialize_dossier_details(self, dossier) -> Optional[Dict[str, Any]]:
        """Serialise un ToxicoDossier ORM en dict JSON-safe. Extrait de
        l'ancien corps de GET /toxico/patients/{patient_id} (chantier 6) -
        reutilise a l'identique par cet endpoint et par le nouveau dossier
        consolide, pour ne pas dupliquer cette logique."""
        if not dossier:
            return None

        psy_name = "Non assigné"
        if dossier.psychologist:
            if hasattr(dossier.psychologist, "full_name"):
                psy_name = dossier.psychologist.full_name
            elif hasattr(dossier.psychologist, "username"):
                psy_name = dossier.psychologist.username
            else:
                psy_name = "Psychologue (Nom inconnu)"

        return {
            "dossier_id": dossier.id,
            "patient_id": dossier.patient_id,
            "code": dossier.patient.code_patient,
            "firstName": dossier.patient.first_name,
            "lastName": dossier.patient.last_name,
            "dob": dossier.patient.birth_date,
            "mothersName": getattr(dossier.patient, "mother_name", getattr(dossier.patient, "mothers_name", None)),
            "address": getattr(dossier.patient, "address", "Non renseignée"),
            "contact": getattr(dossier.patient, "contact_phone", getattr(dossier.patient, "contact", None)),
            "admissionDate": dossier.admission_date,
            "createdAt": dossier.created_at,
            "substance": dossier.substance,
            "currentPhase": dossier.current_phase,
            "relapseCount": dossier.relapse_count,
            "psychologist": psy_name,
            "guardianName": dossier.guardian_name,
            "guardianContact": dossier.guardian_contact,
            "consentFile": dossier.consent_file,
            "notes": dossier.notes_admission,
            "phaseHistory": sorted([
                {
                    "phase": h.phase,
                    "start_date": h.start_date,
                    "end_date": h.end_date,
                    "status": h.status,
                    "comments": h.comments
                } for h in dossier.phase_history
            ], key=lambda x: x['start_date'], reverse=True),
            "evaluations": [
                {
                    "id": e.id,
                    "created_at": e.created_at,
                    "decision": e.decision,
                    "observation": e.observation,
                    "recommendation": e.recommendation,
                    "phase_before": e.phase_before,
                    "phase_after": e.phase_after,
                    "is_relapse": e.is_relapse,
                    "evaluator_name": getattr(e.evaluator, "full_name", "Inconnu") if e.evaluator else "Inconnu"
                } for e in dossier.evaluations
            ]
        }

    # --- ÉCRITURE (BUSINESS LOGIC) ---

    async def admission_patient(self, data: dict, consent_file: UploadFile = None, base_url: str = ""): # type: ignore
        """ 
        Logique métier d'admission avec gestion de l'upload de fichier + Celery + Redis Invalidation.
        """
        # 1. Gestion de l'upload du fichier de consentement
        file_path_or_url = None
        
        if consent_file:
            try:
                # Génération d'un code temporaire pour le nom du fichier
                temp_code = f"{data.get('firstName', 'unk')}_{data.get('lastName', 'unk')}"
                
                # 🟢 APPEL ASYNCHRONE DE SAUVEGARDE
                file_path_or_url = await save_consent_file(consent_file, temp_code)
                
            except Exception as e:
                # Si une erreur survient, file_path_or_url reste None
                print(f"❌ Exception durant sauvegarde fichier: {e}")
        else:
            print("⚪ Aucun fichier 'consent_file' reçu.")

        # 2. Resolution du patient : rattachement a un patient existant
        # ou creation (chantier 6, registre L2 - avant ce chantier,
        # l'admission toxico creait systematiquement un nouveau patient).
        patient_id_rattachement = data.get('patient_id')
        if patient_id_rattachement:
            patient_existant = self.patient_controller.get_patient(patient_id_rattachement)
            if not patient_existant:
                raise ValueError(f"Patient {patient_id_rattachement} introuvable")
            patient_id = patient_existant['patient_id']
            patient_code = patient_existant['code_patient']
        else:
            champs_requis = ('firstName', 'lastName', 'dob', 'mothersName')
            manquants = [c for c in champs_requis if not data.get(c)]
            if manquants:
                raise ValueError(
                    f"Champs patient requis manquants pour une nouvelle admission: {', '.join(manquants)}"
                )
            try:
                patient_data_for_creation = {
                    "first_name": data['firstName'],
                    "last_name": data['lastName'],
                    "birth_date": data['dob'],
                    "mother_name": data.get('mothersName'),
                    "address": data.get('address'),
                    "contact_phone": data.get('contact'),
                    "is_toxicology": True,
                    "is_clinical": False,
                    "is_spiritual": False,
                    "gender": "M",
                    "assurance": None,
                    "residence": data.get('address'),
                    "national_id": None,
                    "father_name": None
                }
                patient_result = self.patient_controller.create_patient(patient_data_for_creation)

                if isinstance(patient_result, tuple):
                    patient_id, patient_code = patient_result
                else:
                    patient_id = patient_result
                    patient_code = "UNKNOWN" # Devrait être récupéré autrement si non retourné

            except ValueError as e:
                raise ValueError(f"Erreur lors de la création du patient: {str(e)}")

        # 3. Préparation des données Toxico
        toxico_data = {
            "admission_date": data['admissionDate'], 
            "substance": data['substance'], 
            "psychologist_id": data['psychologist_id'],
            "guardian_name": data.get('guardianName'), 
            "guardian_contact": data.get('guardianContact'),
            "notes": data.get('notes'), 
            
            # 🟢 La valeur finale qui doit aller en base
            "consent_file": file_path_or_url 
        }

        # 4. Création du dossier en base
        dossier = self.repo.create_dossier_after_patient_commit(patient_id, toxico_data)

        # 🟢 OPTIMISATIONS POST-CRÉATION (Redis + Celery)
        
        # A. Invalidation du cache Redis (le compteur a changé)
        try:
            current_month = datetime.now().strftime("%Y-%m")
            redis_client.delete(f"toxico:stats:admissions:{current_month}")
        except Exception as e:
            print(f"⚠️ Erreur Redis Invalidation: {e}")

        # B. Tâche de fond Celery (Notification, etc.)
        try:
            task_process_post_admission.delay(
                patient_code=patient_code,
                guardian_contact=data.get('guardianContact')
            )
        except Exception as e:
            print(f"⚠️ Erreur lancement Celery: {e}")

        return dossier

    def submit_evaluation(self, data: dict):
        user_id = self.user.get('user_id') if isinstance(self.user, dict) else self.user.user_id
        return self.repo.process_evaluation(dossier_id=data['dossier_id'], data=data, user_id=user_id) # type: ignore
    
    def discharge_patient(self, dossier_id: int):
        return self.repo.discharge(dossier_id)
    
    def get_current_month_admissions_count(self):
        """Calcule le nombre de dossiers créés ce mois-ci (avec Cache Redis)."""
        
        current_month = datetime.now().strftime("%Y-%m")
        CACHE_KEY = f"toxico:stats:admissions:{current_month}"

        # 1. Vérif Cache (Redis indisponible = pas bloquant, meme pattern
        # defensif que get_psychologists_list ci-dessus)
        try:
            cached_count = redis_client.get(CACHE_KEY)
            if cached_count is not None:
                return int(cached_count) # type: ignore
        except Exception: pass

        # 2. Calcul DB
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        count = self.repo.count_dossiers_created_since(start_of_month)

        # 3. Mise en cache (TTL 24h)
        try:
            redis_client.setex(CACHE_KEY, 86400, count)
        except Exception: pass

        return count