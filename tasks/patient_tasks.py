# tasks/patient_tasks.py
from celery_app import celery_app
import time

@celery_app.task(name="notify_new_patient")
def task_notify_new_patient(patient_id: int, code: str, first_name: str, phone: str = None): # type: ignore
    """
    Envoie un message de bienvenue au patient.
    """
    print(f"👋 [CELERY PATIENT] Nouveau patient créé : {first_name} ({code})")
    
    if phone:
        # Simulation appel API SMS (Twilio, etc.)
        time.sleep(1)
        print(f"📱 [CELERY PATIENT] SMS de bienvenue envoyé au {phone}")
    else:
        print("ℹ️ [CELERY PATIENT] Pas de téléphone, notification ignorée.")
        
    return "Notification Patient OK"