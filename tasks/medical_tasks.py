# tasks/medical_tasks.py
from celery_app import celery_app
import time

@celery_app.task(name="process_medical_record_creation")
def task_process_medical_record_creation(record_id: int, patient_id: int, doctor_id: int):
    """
    Tâche exécutée après la création d'un dossier médical.
    Peut servir à :
    - Envoyer un résumé au patient par email.
    - Générer un PDF d'ordonnance ou de compte-rendu.
    - Mettre à jour des statistiques complexes.
    """
    print(f"🩺 [CELERY MEDICAL] Traitement du dossier #{record_id} (Patient {patient_id})")
    
    # 1. Simulation génération PDF ou analyse IA
    time.sleep(1)
    
    # 2. Simulation Notification au médecin référent ou patient
    print(f"📧 [CELERY MEDICAL] Notification envoyée pour le suivi du patient {patient_id}.")
    
    return "Medical Record Processed"