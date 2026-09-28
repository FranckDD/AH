# tasks/toxico_tasks.py
import time
from celery_app import celery_app

@celery_app.task(name="process_post_admission")
def task_process_post_admission(patient_code: str, guardian_contact: str):
    """
    Tâche exécutée en arrière-plan après une admission.
    Ne bloque pas la réponse HTTP.
    """
    print(f"⚙️ [CELERY] Début traitement post-admission pour {patient_code}")
    
    # 1. Simulation envoi SMS/Email au tuteur
    if guardian_contact:
        time.sleep(2) # Simule le temps réseau SMTP/SMS
        print(f"📧 [CELERY] Notification envoyée au tuteur ({guardian_contact})")
        
    # 2. Autres traitements lourds (ex: génération PDF, stats globales)
    time.sleep(2)
    
    print(f"✅ [CELERY] Traitement terminé pour {patient_code}")
    return "OK"