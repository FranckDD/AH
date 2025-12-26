from datetime import datetime
from typing import Any, Dict

def _to_dict(obj: Any) -> Dict:
    """
    Convertit un ORM object ou dict en dict simple.
    """
    if obj is None:
        return {}
    if isinstance(obj, dict): 
        return obj
    # ORM object: prefer __dict__ but filter private attrs
    d = {}
    for k in getattr(obj, "__dict__", {}) :
        if k.startswith("_"):
            continue
        d[k] = getattr(obj, k)
    # fallback: if empty, try attribute access from SQLAlchemy result mapping
    if not d:
        for col in dir(obj):
            if col.startswith("_"):
                continue
            try:
                d[col] = getattr(obj, col)
            except Exception:
                pass
    return d

def normalize_medical_record_data(raw) -> dict:
    """
    Prend soit un ORM MedicalRecord soit un dict et renvoie un dict 'propre'
    prêt à être validé par Pydantic.
    - met motif_code en MAJ
    - convertit champs datetime en datetime
    - laisse les valeurs brutes (patient_id, notes, ...) mais tente un cast des nombres
    """
    data = _to_dict(raw) or {}
    # renommage / compatibilité si tes attributs ont des noms différents
    # normaliser consultation_date -> datetime
    cd = data.get("consultation_date") or data.get("date") or data.get("created_at")
    if cd is not None and not isinstance(cd, datetime):
        try:
            # peut être date ou string
            data["consultation_date"] = datetime.fromisoformat(str(cd))
        except Exception:
            data["consultation_date"] = cd
    # motif en uppercase si présent
    if data.get("motif_code") is not None:
        data["motif_code"] = str(data.get("motif_code")).strip().lower()
    # cast numeric-like
    for key in ("temperature", "weight", "height"):
        v = data.get(key)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            continue
        try:
            data[key] = float(v)
        except Exception:
            # la validation Pydantic renverra une erreur plus parlante
            pass

    return data
