# tasks/pharmacy_tasks.py
from celery_app import celery_app
import time

@celery_app.task(name="check_low_stock_alert")
def task_check_low_stock_alert(product_id: int, product_name: str, current_qty: int, min_qty: int):
    """
    Vérifie si le stock est critique et envoie une alerte si nécessaire.
    """
    if current_qty <= min_qty:
        print(f"🚨 [CELERY PHARMA] ALERTE RUPTURE : {product_name} (Qté: {current_qty}/{min_qty})")
        
        # Simulation envoi Email au Pharmacien Chef
        time.sleep(1)
        print(f"📧 [CELERY PHARMA] Email d'alerte envoyé pour {product_name}")
        
        return f"Alert sent for {product_name}"
    
    return "Stock OK"