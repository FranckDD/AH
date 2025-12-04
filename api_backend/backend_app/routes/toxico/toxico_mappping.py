# utils/toxico_mapping.py (ou dans le même dossier que 'mapping.py' si vous l'avez)

from datetime import datetime
from typing import Any, Dict

# Assurez-vous d'avoir cette fonction utilitaire disponible
def _to_dict(obj: Any) -> Dict:
    """ Convertit un ORM object ou dict en dict simple. (Implémentation vue précédemment) """
    if obj is None:
        return {}
    if isinstance(obj, dict): 
        return obj
    d = {}
    for k in getattr(obj, "__dict__", {}):
        if k.startswith("_"):
            continue
        d[k] = getattr(obj, k)
    if not d:
        for col in dir(obj):
            if col.startswith("_"):
                continue
            try:
                # Évite les erreurs sur les attributs dynamiques (relationships) si non chargés
                if col not in ['metadata', 'query', 'query_class']:
                    d[col] = getattr(obj, col)
            except Exception:
                pass
    return d

def normalize_admission_data(raw: Any) -> dict:
    """
    Normalise les données d'Admission pour la validation Pydantic.
    """
    data = _to_dict(raw) or {}
    
    # Assurer que les dates sont des objets datetime si elles existent (gestion de from_attributes)
    for key in ["admission_date", "discharge_date"]:
        v = data.get(key)
        if v is not None and not isinstance(v, datetime):
             try:
                data[key] = datetime.fromisoformat(str(v))
             except Exception:
                 pass
    
    # Assurez-vous que les IDs sont des entiers si l'ORM les retourne en string (non standard mais sûr)
    for key in ["admission_id", "patient_id", "created_by", "current_phase"]:
        v = data.get(key)
        if v is not None and not isinstance(v, int):
            try:
                data[key] = int(v)
            except Exception:
                pass
                
    return data

def normalize_evaluation_data(raw: Any) -> dict:
    """
    Normalise les données d'Évaluation Psychologique.
    """
    data = _to_dict(raw) or {}
    # Traitement des dates (eval_date) et des scores (mood_score, phase_at_time)
    for key in ["eval_date"]:
        v = data.get(key)
        if v is not None and not isinstance(v, datetime):
            try:
                data[key] = datetime.fromisoformat(str(v))
            except Exception:
                pass
    
    for key in ["mood_score", "phase_at_time"]:
        v = data.get(key)
        if v is not None and not isinstance(v, int):
            try:
                data[key] = int(v)
            except Exception:
                pass
                
    return data