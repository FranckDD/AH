# repositories/repo_factory.py
"""
Factory légère pour renvoyer les classes de repository (online vs offline).
Utilise des importations retardées (lazy import) pour éviter les dépendances circulaires
et pour ne charger que ce qui est nécessaire.
"""

from typing import Dict, Type


def get_repo_classes_for_backend(backend: str) -> Dict[str, Type]:
    """
    Retourne un dictionnaire avec les classes de repo utiles.
    Clés: "patient", "appointment", "medical_record", "prescription", "user" (optionnel).
    backend: "online" | "offline"
    """
    b = (backend or "").lower()
    if b not in ("online", "offline"):
        raise ValueError("backend must be 'online' or 'offline'")

    if b == "offline":
        # imports retardés
        from repositories.repo_offline.patient_repo_offline import PatientRepositoryOffline
        from repositories.repo_offline.appointment_repo_offline import AppointmentRepositoryOffline
        from repositories.repo_offline.medical_repo_offline import MedicalRecordRepositoryOffline
        from repositories.repo_offline.prescription_repo_offline import PrescriptionRepositoryOffline
        from repositories.repo_offline.user_repo_offline import UserRepositoryOffline

        return {
            "patient": PatientRepositoryOffline,
            "appointment": AppointmentRepositoryOffline,
            "medical_record": MedicalRecordRepositoryOffline,
            "prescription": PrescriptionRepositoryOffline,
            "user": UserRepositoryOffline,
        }

    # online
    from repositories.patient_repo import PatientRepository
    from repositories.appointment_repo import AppointmentRepository  
    from repositories.medical_repo import MedicalRecordRepository
    from repositories.prescription_repo import PrescriptionRepository
    from repositories.user_repo import UserRepository

    return {
        "patient": PatientRepository,
        "appointment": AppointmentRepository,
        "medical_record": MedicalRecordRepository,
        "prescription": PrescriptionRepository,
        "user": UserRepository,
    }
