from datetime import datetime, date
from app.utils.mapping_general import parse_datetime

def normalize_pharmacy_data(raw) -> dict:
    """Normalise les données de pharmacie pour la réponse API"""
    # Gestion des relations
    patient = getattr(raw, "patient", None)
    prescriber = getattr(raw, "prescriber", None)
    
    # Convertir expiry_date en date si c'est un datetime
    expiry_date_value = raw.expiry_date.date() if isinstance(raw.expiry_date, datetime) else raw.expiry_date
    current_date = date.today()
    
    return {
        "medication_id": raw.medication_id,
        "patient_id": raw.patient_id,
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else None,
        "drug_name": raw.drug_name,
        "quantity": raw.quantity,
        "threshold": raw.threshold,
        "medication_type": raw.medication_type,
        "forme": raw.forme,
        "dosage_mg": float(raw.dosage_mg) if raw.dosage_mg is not None else None,
        "expiry_date": parse_datetime(raw.expiry_date),
        "stock_status": raw.stock_status,
        "prescribed_by": raw.prescribed_by,
        "prescriber_name": f"{prescriber.first_name} {prescriber.last_name}" if prescriber else raw.name_dr,
        "created_at": parse_datetime(raw.created_at),
        "updated_at": parse_datetime(raw.updated_at),
        "expired": expiry_date_value < current_date if expiry_date_value else False,
        "critical": raw.stock_status in ('critique', 'épuisé')
    }