from models.retrait import CaisseRetrait


def normalize_retrait_data(retrait: CaisseRetrait) -> dict:
    """
    Normalise Retrait pour API.
    Transforme l'objet SQLAlchemy en dictionnaire sécurisé.
    """
    
    # Récupération intelligente du nom de l'utilisateur (si la relation 'user' est chargée)
    user_name = "Inconnu"
    if hasattr(retrait, "user") and retrait.user:
        # Si relation SQLAlchemy active
        user_name = getattr(retrait.user, "username", str(retrait.handled_by))
    elif hasattr(retrait, "created_by_name"):
        # Si propriété hybride définie dans le modèle
        user_name = retrait.created_by_name
    else:
        # Fallback sur l'ID
        user_name = str(retrait.handled_by)

    return {
        "retrait_id": retrait.retrait_id,
        "amount": float(retrait.amount),
        "justification": retrait.justification,
        "status": retrait.status,
        
        # Date principale (nom réel en DB)
        "retrait_at": retrait.retrait_at.isoformat() if retrait.retrait_at else None,
        
        # --- CORRECTION DU BUG ---
        # On mappe 'created_at' (attendu par le frontend) sur 'retrait_at' (existant en DB)
        "created_at": retrait.retrait_at.isoformat() if retrait.retrait_at else None,
        
        # Champs d'annulation
        "cancelled_at": retrait.cancelled_at.isoformat() if retrait.cancelled_at else None,
        "cancel_justification": retrait.cancel_justification,
        
        # Infos utilisateur
        "handled_by": retrait.handled_by,
        "cancelled_by": retrait.cancelled_by,
        "created_by_name": user_name, # <--- Ajout utile pour l'affichage direct
        
        # 🟢 NOUVEAUX CHAMPS pour l'intégration VueJS
        # On les mappe directement de l'objet SQLAlchemy (qui doit maintenant avoir ces attributs)
        # On fournit une valeur par défaut au cas où ils sont NULL (anciens enregistrements)
        "category": getattr(retrait, "category", None) or "Dépense",
        "payment_method": getattr(retrait, "payment_method", None) or "Espèces"
    }