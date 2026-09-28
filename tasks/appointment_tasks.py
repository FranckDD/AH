# tasks/appointment_tasks.py
from celery_app import celery_app
import time

@celery_app.task(name="notify_appointment_action")
def task_notify_appointment_action(appointment_id: int, action: str, patient_name: str, doctor_name: str, date_time: str):
    """
    Notifie les parties concernées d'un changement de RDV.
    action: 'created', 'cancelled', 'rescheduled'
    """
    print(f"📅 [CELERY APPT] Action '{action}' sur RDV #{appointment_id}")
    print(f"Patient: {patient_name} | Docteur: {doctor_name} | Le: {date_time}")
    
    # Simulation Envoi Email/SMS
    time.sleep(1)
    
    if action == 'created':
        print(f"📧 [CELERY APPT] Confirmation envoyée à {patient_name}")
    elif action == 'cancelled':
        print(f"🚨 [CELERY APPT] Annulation envoyée au patient et au docteur")
        
    return f"Notification {action} sent"