# tasks/finance_tasks.py
from celery_app import celery_app
import time

@celery_app.task(name="process_payment_notification")
def task_process_payment_notification(transaction_id: int, action: str, amount_paid: float = 0.0):
    print(f"💰 [CELERY] Traitement paiement ID: {transaction_id}, Action: {action}")
    # Simuler envoi de reçu
    time.sleep(1)
    print("📧 [CELERY] Reçu envoyé.")
    return "OK"