# celery_app.py
from celery import Celery

# Configuration de Celery avec Redis comme Broker et Backend
celery_app = Celery(
    "toxico_worker",
    broker="redis://localhost:6379/0", # Adapte l'URL si besoin
    backend="redis://localhost:6379/0"
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Africa/Douala", # Ou ton fuseau horaire
    enable_utc=True,
)