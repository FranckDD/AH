# controller/discount_request_controller.py
import os
import redis
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from dotenv import load_dotenv
from controller.caisse_controller import check_invoice_amounts, validate_staff_discount, invalidate_caisse_kpi_cache
from repositories.discount_request_repo import DiscountRequestRepository
from repositories.caisse_repo import CaisseRepository
from repositories.notification_repo import NotificationRepository
from models.discount_request import DiscountRequest
from models.user import User
from utils.patient_display import resolve_patient_display_name
from utils.payment_mode_guard import resolve_payment_mode
from utils.price_lock import check_line_prices, validate_lines
from models.application_role import ApplicationRole

# Les seuls pourcentages proposes par l'UI (DiscountDecisionModal) - toute
# autre valeur (150 -> montant negatif, -10 -> montant majore) est refusee.
ALLOWED_DECISION_PERCENTS = (10, 20, 50, 100)
_CENTS = Decimal("0.01")
MANAGER_ROLE_NAMES = ["admin", "promoteur"]

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Compteur dedie aux mots de passe INCORRECTS uniquement (pas au decorateur
# slowapi de la route, qui compte toute requete y compris les decisions
# reussies - residu documente au chantier notifications : throttlait un
# manager occupe qui approuve plusieurs demandes de suite). Le vrai
# garde-fou anti-bruteforce ne doit reagir qu'aux echecs.
FAILED_PASSWORD_LIMIT = 5
FAILED_PASSWORD_WINDOW_SECONDS = 60


class DiscountRequestController:
    def __init__(self, repo: DiscountRequestRepository, caisse_repo: CaisseRepository,
                 notification_repo: NotificationRepository, current_user, audit_repo=None):
        self.repo = repo
        self.caisse_repo = caisse_repo
        self.notification_repo = notification_repo
        self.audit_repo = audit_repo
        self.user = current_user

    def _validate_recipient(self, requested_to) -> None:
        """Le destinataire doit etre un utilisateur actif admin/promoteur
        (meme filtre que GET /users/managers). Appele AVANT toute creation
        d'etat : sinon une facture pourrait rester verrouillee en
        pending_approval (stock deja deduit) sans demande exploitable."""
        recipient = (
            self.repo.session.query(User)
            .join(ApplicationRole)
            .filter(
                User.user_id == requested_to,
                User.is_active == True,  # noqa: E712
                ApplicationRole.role_name.in_(MANAGER_ROLE_NAMES),
            )
            .first()
        )
        if not recipient:
            raise ValueError("Le destinataire choisi n'est pas un manager actif valide.")

    def create_request(self, invoice_data: Dict[str, Any], requested_to: int) -> DiscountRequest:
        """Cree la facture (status='pending_approval' des la creation,
        decision utilisateur n2) ET la demande dans le meme geste."""
        required_keys = ["payment_method", "transaction_type", "amount", "items", "advance_amount"]
        for key in required_keys:
            if key not in invoice_data:
                raise ValueError(f"Champ manquant : {key}")
        self._validate_recipient(requested_to)
        # Rien ne doit etre encaisse tant que la decision n'est pas prise :
        # une avance pourrait depasser le montant finalement approuve.
        if invoice_data.get("advance_amount", 0):
            raise ValueError("Aucune avance ne peut être encaissée sur une facture en attente de validation d'une réduction.")
        if not invoice_data["items"] and invoice_data.get("advance_amount", 0) == 0:
            raise ValueError("La transaction doit contenir au moins une ligne ou indiquer une avance.")
        # Prix verrouille au catalogue, meme regle que la facturation directe.
        # Chemin en ligne uniquement (appel reseau direct) : un uuid client
        # n'en fait PAS un rejeu, tout ecart est refuse (422).
        validate_lines(invoice_data["items"])
        check_line_prices(self.repo.session, invoice_data["items"], self.user, replay=False)
        # Meme invariant et memes arrondis que la facturation directe.
        staff_sent, amount = check_invoice_amounts(invoice_data)
        staff_sent, staff_details = validate_staff_discount(self.repo.session, invoice_data, staff_sent)
        invoice_data = {**invoice_data, "amount": amount, "staff_discount_amount": staff_sent,
                        "staff_discount_details": staff_details,
                        "payment_method": resolve_payment_mode(
                            self.repo.session, invoice_data["payment_method"], required=False,
                            replay=bool(invoice_data.get("uuid")))}

        tx = self.caisse_repo.create_transaction(invoice_data, self.user, initial_status="pending_approval")

        # Base de la remise manuelle = BRUT (net du + reduction personnel eventuelle).
        req = self.repo.create(
            transaction_id=tx.transaction_id,
            requested_by=self.user.user_id,
            requested_to=requested_to,
            original_amount=amount + staff_sent,
        )

        self.notification_repo.create(
            recipient_user_id=requested_to,
            type="discount_request",
            payload={
                "discount_request_id": req.id,
                "transaction_id": tx.transaction_id,
                "patient_label": resolve_patient_display_name(tx.patient_by_id, tx.patient_label),
                "amount": float(req.original_amount),
                "requested_by_name": getattr(self.user, "full_name", self.user.username),
            },
        )
        self.repo.session.commit()
        # Facture creee/modifiee : les tuiles KPI caisse doivent se recalculer (defaut 6b).
        invalidate_caisse_kpi_cache()
        return req

    def _patient_label_for(self, transaction_id: int):
        tx = self.caisse_repo.get_by_id(transaction_id)
        return resolve_patient_display_name(tx.patient_by_id, tx.patient_label) if tx else None

    def cancel_and_reassign(self, request_id: int, new_requested_to: int) -> DiscountRequest:
        old_req = self.repo.get_by_id(request_id)
        if not old_req:
            raise ValueError("Demande introuvable.")
        if old_req.requested_by != self.user.user_id:
            raise PermissionError("Seul l'auteur de la demande peut l'annuler.")
        if old_req.status != "pending":
            raise ValueError("Cette demande n'est plus en attente.")
        self._validate_recipient(new_requested_to)

        self.repo.cancel(old_req)

        new_req = self.repo.create(
            transaction_id=old_req.transaction_id,
            requested_by=self.user.user_id,
            requested_to=new_requested_to,
            original_amount=old_req.original_amount,
        )
        self.notification_repo.create(
            recipient_user_id=new_requested_to,
            type="discount_request",
            payload={
                "discount_request_id": new_req.id,
                "transaction_id": new_req.transaction_id,
                "patient_label": self._patient_label_for(new_req.transaction_id),
                "amount": float(new_req.original_amount),
                "requested_by_name": getattr(self.user, "full_name", self.user.username),
            },
        )
        self.repo.session.commit()
        return new_req

    def decide_request(self, request_id: int, password: str, refuse: bool,
                        decision_percent: int = None, decision_echelonne_deadline=None) -> DiscountRequest:
        """Decision du manager (approbation/refus) sur une demande de remise,
        gardee par une reconfirmation du mot de passe (anti-fraude - le
        processus papier remplace etait activement falsifie). Utilise
        User.check_password() directement (models/user.py:60-61), jamais
        AuthController.authenticate() qui ecrirait un faux LOGIN_SUCCESS
        dans l'audit a chaque decision."""
        fail_key = f"discount_decide_fail:{self.user.user_id}"
        try:
            fail_count = int(redis_client.get(fail_key) or 0)
        except Exception:
            fail_count = 0  # Redis indisponible : on degrade en ne bloquant jamais une vraie decision.
        if fail_count >= FAILED_PASSWORD_LIMIT:
            raise PermissionError("Trop de tentatives avec un mot de passe incorrect. Réessayez dans une minute.")

        if not self.user.check_password(password):
            try:
                redis_client.incr(fail_key)
                redis_client.expire(fail_key, FAILED_PASSWORD_WINDOW_SECONDS)
            except Exception:
                pass
            raise PermissionError("Mot de passe incorrect.")

        try:
            redis_client.delete(fail_key)
        except Exception:
            pass

        req = self.repo.get_by_id(request_id)
        if not req:
            raise ValueError("Demande introuvable.")
        if req.requested_to != self.user.user_id:
            raise PermissionError("Cette demande ne vous est pas adressée.")
        if req.status != "pending":
            raise ValueError("Cette demande n'est plus en attente.")
        if refuse and (decision_percent or decision_echelonne_deadline):
            raise ValueError("Un refus ne peut pas être accompagné d'un pourcentage ou d'une échéance.")
        if not refuse:
            if decision_percent is not None and decision_percent not in ALLOWED_DECISION_PERCENTS:
                raise ValueError("decision_percent doit être 10, 20, 50 ou 100.")
            if not decision_percent and not decision_echelonne_deadline:
                raise ValueError("Une décision d'approbation doit accorder un pourcentage et/ou une échéance.")

        self.repo.decide(req, self.user.user_id, refuse, decision_percent, decision_echelonne_deadline)

        tx = self.caisse_repo.get_by_id(req.transaction_id)
        replaced_staff = Decimal("0")
        if not refuse and decision_percent:
            # La remise manuelle remplace la reduction personnel : base = brut
            # (original_amount), jamais le net deja reduit.
            replaced_staff = Decimal(str(tx.staff_discount_amount or 0))
            tx.amount = (Decimal(str(req.original_amount)) * (Decimal(100) - Decimal(decision_percent)) / Decimal(100)
                         ).quantize(_CENTS, rounding=ROUND_HALF_UP)
            if replaced_staff > 0:
                tx.staff_discount_details = {
                    "replaced_by_discount_request": req.id,
                    "previous": tx.staff_discount_details,
                }
                tx.staff_discount_amount = 0
        tx.status = "active"

        if self.audit_repo:
            audit_values = {
                "transaction_id": req.transaction_id,
                "decision_percent": decision_percent,
                "decision_echelonne_deadline": str(decision_echelonne_deadline) if decision_echelonne_deadline else None,
                "original_amount": float(req.original_amount),
                "final_amount": float(tx.amount),
            }
            if replaced_staff > 0:
                audit_values["replaced_staff_discount_amount"] = float(replaced_staff)
            self.audit_repo.log_user_action(
                current_user=self.user,
                resource_type="DiscountRequest",
                action_performed="REFUSE" if refuse else "APPROVE",
                resource_id=req.id,
                new_values=audit_values,
            )

        self.notification_repo.create(
            recipient_user_id=req.requested_by,
            type="discount_decided",
            payload={
                "discount_request_id": req.id,
                "transaction_id": req.transaction_id,
                "status": req.status,
                "decision_percent": decision_percent,
                "decision_echelonne_deadline": str(decision_echelonne_deadline) if decision_echelonne_deadline else None,
            },
        )
        self.repo.session.commit()
        # Facture creee/modifiee : les tuiles KPI caisse doivent se recalculer (defaut 6b).
        invalidate_caisse_kpi_cache()
        return req
