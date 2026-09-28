# api_backend/backend_app/celery_app.py

from celery import Celery
import os
from dotenv import load_dotenv # ⬅️ AJOUT DE L'IMPORT

# 🟢 Charger les variables d'environnement du fichier .env
load_dotenv()

# URL de connexion Redis (Docker ou local)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "toxico_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Africa/Douala", # Adapte selon ton fuseau
    enable_utc=True,
    # Permet de trouver les tâches automatiquement si elles sont dans un module 'tasks'
    include=[
        "tasks.toxico_tasks",
        "tasks.finance_tasks",
        "tasks.caisse_retrait_tasks",
        "tasks.patient_tasks",
        "tasks.medical_tasks",
        "tasks.pharmacy_tasks",
        "tasks.prescription_tasks",
        "tasks.appointment_tasks" 
    ] 
)