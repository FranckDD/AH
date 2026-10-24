# utils/payment_mode_guard.py
"""Mode de paiement a l'ecriture (vente, paiement echelonne, retrait).

Une valeur ancienne ou libre ('Mobile Money', 'Virement', 'Cash'...) est
normalisee vers un code officiel (ou 'non_classe'), jamais rejetee : la file
hors ligne ne doit pas se bloquer. Seul un mode officiel desactive par l'admin
est refuse pour une NOUVELLE ecriture ; les anciens paiements restent lisibles.
"""
from typing import Optional

from models.cash_closure import PaymentMode
from utils.cash_rules import UNCLASSIFIED, normalize_mode


class PaymentModeError(ValueError):
    """Mode absent (retrait) ou desactive : les endpoints repondent 422."""


def resolve_payment_mode(session, raw: Optional[str], *, required: bool, replay: bool = False) -> str:
    """Code a stocker. required=True (retrait) : vide -> PaymentModeError ;
    required=False (vente, versement) : vide -> 'non_classe'.

    replay=True : operation rejouee depuis la file hors ligne (le client envoie
    son uuid). L'argent a reellement bouge : elle n'est jamais refusee pour une
    question de mode (vide -> 'non_classe', mode desactive -> garde tel quel)."""
    s = raw.strip() if isinstance(raw, str) else ""
    if not s:
        if required and not replay:
            raise PaymentModeError("Le mode de paiement est obligatoire.")
        return UNCLASSIFIED
    # Un code deja present dans la table payment_modes (liste fixe) est garde tel quel.
    row = session.get(PaymentMode, s)
    code = s if row is not None else normalize_mode(s)
    if code != UNCLASSIFIED and not replay:
        if row is None:
            row = session.get(PaymentMode, code)
        if row is not None and not row.is_active:
            raise PaymentModeError(f"Le mode de paiement '{row.label}' est désactivé.")
    return code
