# tasks/caisse_retrait_tasks.py

from celery_app import celery_app
import time

@celery_app.task(name="notify_manager_on_withdrawal")
def task_notify_manager_on_withdrawal(retrait_id: int, amount: float, justification: str, user_id: int, manager_email: str = "manager@ah2.com"):
    """
    Tâche asynchrone pour notifier un responsable après un retrait de caisse.
    Ceci est essentiel pour l'audit et la sécurité.
    """
    print(f"🚨 [CELERY RETRAIT] Notification de retrait (ID: {retrait_id}) démarrée.")
    print(f"Montant: {amount} XAF retiré par l'utilisateur ID {user_id}")
    print(f"Justification: {justification}")
    
    # --- LOGIQUE MÉTIER DE LA TÂCHE ASYNCHRONE ---
    
    # 1. Simuler l'envoi d'un email au manager pour validation
    time.sleep(2) 
    print(f"📧 [CELERY RETRAIT] Email de notification envoyé à {manager_email}")
    
    # 2. Vous pourriez ici aussi générer un rapport PDF d'audit ou un log externe.
    
    return "Notification Manager OK"