# Fichier: controllers/toxico_controller.py
import os
import shutil
# 📂 Configuration du dossier d'upload pour Toxico
UPLOAD_DIR = "static/uploads/toxico_consents"
os.makedirs(UPLOAD_DIR, exist_ok=True)
from fastapi import UploadFile
from datetime import datetime, date
from typing import List, Dict, Any,Optional
from repositories.toxico_repo import ToxicoRepository
from repositories.patient_repo import PatientRepository
from api_backend.backend_app.utils.file_storage import save_consent_file


from controller.patient_controller import PatientController 
from repositories.audit_repo import AuditRepository


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
        

    # --- LECTURE ---

    def get_psychologists_list(self) -> List[Dict]:
        users = self.repo.get_psychologists()
        # Le mapping simple pour la liste déroulante reste ici (logique de sélection)
        return [{"id": u.user_id, "name": f"{u.full_name}"} for u in users]

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
            "psychologist": d.psychologist.full_name if d.psychologist else "Non assigné"
        }

    def get_dossier_details(self, patient_id: int):
        """Détail complet pour la modale dossier. Retourne l'objet ORM complet."""
        # Le Repo charge toutes les relations nécessaires (Eager Loading)
        return self.repo.get_dossier_full(patient_id)

    # --- ÉCRITURE (BUSINESS LOGIC) ---

    async def admission_patient(self, data: dict, consent_file: UploadFile = None, base_url: str = ""): # type: ignore
        """ 
        Logique métier d'admission avec gestion de l'upload de fichier.
        """
        #print("⚡ [CONTROLLER] Début admission_patient")
        
        # 1. Gestion de l'upload du fichier de consentement
        file_path_or_url = None # ⬅️ Initialisation
        
        if consent_file:
            #print(f"📂 [CONTROLLER] Fichier détecté: {consent_file.filename}")
            try:
                # Génération d'un code temporaire pour le nom du fichier
                temp_code = f"{data.get('firstName', 'unk')}_{data.get('lastName', 'unk')}"
                
                # 🟢 APPEL ASYNCHRONE DE SAUVEGARDE
                file_path_or_url = await save_consent_file(consent_file, temp_code)
                
                # 🟢 DEBUG A : La valeur est-elle bien retournée par la fonction de sauvegarde ?
                #print(f"DEBUG A: Valeur retournée par SAVE : {file_path_or_url}")
                
            except Exception as e:
                # Si une erreur survient, file_path_or_url reste None
                print(f"❌  Exception durant sauvegarde fichier: {e}")
                
        else:
            print("⚪  Aucun fichier 'consent_file' reçu.")

        # 2. Création du Patient via PatientController
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
            patient_id, patient_code = self.patient_controller.create_patient(patient_data_for_creation)
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

        # 🟢 DEBUG B : La valeur envoyée au Repo est-elle correcte ?
        #print(f"DEBUG B: Valeur FINALE envoyée au Repo : {toxico_data.get('consent_file')}")


        # 4. Création du dossier en base
        return self.repo.create_dossier_after_patient_commit(patient_id, toxico_data)

    def submit_evaluation(self, data: dict):
        user_id = self.user.get('user_id') if isinstance(self.user, dict) else self.user.user_id
        return self.repo.process_evaluation(dossier_id=data['dossier_id'], data=data, user_id=user_id) # type: ignore
    
    def discharge_patient(self, dossier_id: int):
        return self.repo.discharge(dossier_id)
    
    def get_current_month_admissions_count(self):
        """Calcule le nombre de dossiers créés ce mois-ci."""
        
        # 1. Déterminer les bornes du mois courant
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        # 2. Utiliser la fonction de comptage du repository (DB)
        # Note : On compte sur le champ  'created_at' selon la logique
        count = self.repo.count_dossiers_created_since(start_of_month)
        
        return count