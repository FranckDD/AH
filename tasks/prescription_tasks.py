# tasks/prescription_tasks.py
from celery_app import celery_app
import time

@celery_app.task(name="notify_new_prescription", ignore_result=True)
def task_notify_new_prescription(prescription_id: int, patient_id: int, medication: str):
    """
    Notifie la pharmacie d'une nouvelle prescription à préparer.
    """
    print(f"💊 [CELERY PRESCRIPTION] Nouvelle ordonnance #{prescription_id} pour Patient {patient_id}")
    print(f"Médicament: {medication}")
    
    # Simulation d'envoi à l'imprimante de la pharmacie ou écran de file d'attente
    time.sleep(1)
    
    return "Pharmacy Notified"