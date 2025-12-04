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

# --- FONCTION DE NORMALISATION AMÉLIORÉE ---
def normalize_medical_record_data(raw) -> dict:
    """
    Version Hybride : Utilise _to_dict pour la base, 
    puis ajoute les alias pour le Frontend.
    """
    # 1. On récupère la base existante (Sécurité pour les autres vues)
    data = _to_dict(raw) or {}

    # 2. Gestion des Dates (Pour que le tri fonctionne)
    cd = data.get("consultation_date") or data.get("date") or data.get("created_at")
    if cd is not None and not isinstance(cd, datetime):
        try:
            data["consultation_date"] = datetime.fromisoformat(str(cd))
        except Exception:
            data["consultation_date"] = cd
    
    # --- AJOUTS POUR LA VUE (PATCH) ---
    
    # Alias 'date' (le front utilise souvent record.date)
    data["date"] = data.get("consultation_date")

    # Motif en MAJ
    if data.get("motif_code"):
        data["motif_code"] = str(data.get("motif_code")).strip().upper()

    # Cast numérique sécurisé
    for key in ("temperature", "weight", "height"):
        v = data.get(key)
        if v is not None and not isinstance(v, (int, float)):
            try:
                data[key] = float(v)
            except:
                pass

    # GESTION CRITIQUE DU MÉDECIN (Le problème des cases vides)
    # Si created_by_name est vide, on essaie de le trouver via la relation SQLAlchemy sur 'raw'
    if not data.get("created_by_name"):
        # On tente d'accéder aux relations (qui ne sont pas dans _to_dict)
        creator = getattr(raw, "doctor", None) or getattr(raw, "user", None) or getattr(raw, "creator", None)
        if creator:
            # On construit un nom
            username = getattr(creator, "username", "")
            fname = getattr(creator, "first_name", "")
            lname = getattr(creator, "last_name", "")
            data["created_by_name"] = f"{fname} {lname}".strip() or username
        else:
            data["created_by_name"] = "Médecin" # Valeur par défaut pour l'affichage

    # Alias 'doctor_name' pour le front
    data["doctor_name"] = data["created_by_name"]

    return data
