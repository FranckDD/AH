"""Nom d'affichage d'un patient pour les factures / demandes de reduction."""


def resolve_patient_display_name(patient, label=None):
    """'<prenom> <nom>' du patient enregistre (parties vides ignorees) ; sinon
    le libelle libre (patient sans dossier) ; sinon None. Le patient enregistre
    l'emporte sur patient_label quand les deux existent."""
    if patient is not None:
        parts = [getattr(patient, "first_name", None), getattr(patient, "last_name", None)]
        name = " ".join(p.strip() for p in parts if p and p.strip())
        if name:
            return name
    label = (label or "").strip()
    return label or None
