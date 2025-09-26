# app/routes/prescriptions/mapping.py
from datetime import date, datetime
from typing import Any, Dict, Optional

def _to_dict(obj: Any) -> Dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj.copy()
    d: Dict[str, Any] = {}
    for k, v in getattr(obj, "__dict__", {}).items():
        if k.startswith("_"):
            continue
        d[k] = v
    if not d:
        # fallback: attempt attribute enumeration (safe)
        for attr in dir(obj):
            if attr.startswith("_"):
                continue
            try:
                d[attr] = getattr(obj, attr)
            except Exception:
                pass
    return d

def _normalize_date_field(val: Optional[Any]) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    # try parse string
    try:
        return datetime.fromisoformat(str(val)).date().isoformat()
    except Exception:
        return str(val)

def normalize_prescription_data(raw: Any) -> Dict:
    """
    Convertit ORM object ou dict Prescription vers dict propre pour Pydantic:
    - start_date/end_date -> ISO date strings (YYYY-MM-DD)
    - dosage/frequency/medication -> strip()
    - ensure patient_id and medication/dosage/frequency/start_date présents si fournis
    """
    data = _to_dict(raw) or {}

    # trimming strings
    for key in ("medication", "dosage", "frequency", "duration", "notes"):
        v = data.get(key)
        if v is None:
            continue
        try:
            data[key] = str(v).strip()
        except Exception:
            pass

    # normalize dates
    if "start_date" in data:
        data["start_date"] = _normalize_date_field(data.get("start_date"))
    if "end_date" in data:
        data["end_date"] = _normalize_date_field(data.get("end_date"))

    # if medical_record_id is present but falsy -> keep None
    if "medical_record_id" in data and data.get("medical_record_id") == "":
        data["medical_record_id"] = None

    return data
