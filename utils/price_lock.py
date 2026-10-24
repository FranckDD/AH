"""Prix unitaire verrouille au catalogue pour la secretaire.

Regle (decision utilisateur 2026-10-24) :
- seuls admin et promoteur saisissent librement un prix ; tout autre role
  (en pratique la secretaire) doit facturer au prix du catalogue ;
- types a prix catalogue : Medicament/carnet (pharmacy.price), Examen
  (examens.prix), Consultation FamilyRestoration (fr_amount_paid) ;
- types libres : Service, Consultation Spiritual (pas de tarif) ;
- prix catalogue NULL ou 0 = "prix non defini" : vente refusee en ligne ;
- rejeu hors ligne (uuid client) : jamais refuse, l'ecart est trace
  (audit PRICE_MISMATCH + notification price_mismatch aux managers).
"""
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from utils.staff_discount import normalize_item_category

logger = logging.getLogger(__name__)

_CENTS = Decimal("0.01")
EXEMPT_ROLES = ("admin", "promoteur")
PRICE_UNDEFINED_MSG = "Prix non défini, contactez l'administrateur."
PRICE_MISMATCH_MSG = ("Prix unitaire différent du prix du catalogue. "
                      "Pour un autre prix, faites une demande de réduction.")
LINE_TOTAL_MSG = "Total de ligne incohérent avec le prix unitaire et la quantité."
QTY_MSG = "Quantité invalide : un nombre entier strictement positif est attendu."
PRICE_NEG_MSG = "Prix unitaire invalide : il doit être positif ou nul."
MAX_QTY = 100000
NOTIF_TYPE = "price_mismatch"
AUDIT_ACTION = "PRICE_MISMATCH"


class PriceLockError(ValueError):
    """Ecart de prix refuse en ligne (HTTP 422)."""


def _q(v) -> Decimal:
    return Decimal(str(v)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def _parse_quantity(raw) -> int:
    """Entier > 0 ; un flottant entier (2.0) est accepte et normalise en 2.
    Chaine, booleen, fraction, <= 0 ou demesure -> PriceLockError (422)."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float, Decimal)):
        raise PriceLockError(QTY_MSG)
    try:
        d = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise PriceLockError(QTY_MSG)
    if not d.is_finite() or d != d.to_integral_value() or d <= 0 or d > MAX_QTY:
        raise PriceLockError(QTY_MSG)
    return int(d)


def validate_lines(items) -> None:
    """Pour TOUS les roles et aussi en rejeu (un client sain ne produit jamais
    ces valeurs) : quantite entiere > 0, prix >= 0, line_total == prix x qte.
    Normalise quantity en int dans la ligne. line_total absent : laisse au
    message 400 de _gross."""
    for line in items or []:
        if not isinstance(line, dict) or line.get("status") == "cancelled":
            continue
        qty = _parse_quantity(line.get("quantity"))
        line["quantity"] = qty
        raw_price = line.get("unit_price")
        if isinstance(raw_price, bool) or not isinstance(raw_price, (int, float, Decimal)):
            raise PriceLockError(PRICE_NEG_MSG)
        price = _q(raw_price)
        if price < 0:
            raise PriceLockError(PRICE_NEG_MSG)
        if line.get("line_total") is not None:
            try:
                lt = _q(line.get("line_total"))
            except (InvalidOperation, TypeError, ValueError):
                raise PriceLockError(LINE_TOTAL_MSG)
            if _q(price * qty) != lt:
                raise PriceLockError(LINE_TOTAL_MSG)


def user_role_names(user) -> set:
    names = set()
    role = getattr(user, "application_role", None)
    if role is not None and getattr(role, "role_name", None):
        names.add(str(role.role_name).lower())
    rn = getattr(user, "role_name", None)
    if isinstance(rn, str) and rn:
        names.add(rn.lower())
    roles = getattr(user, "roles", None)
    if isinstance(roles, (list, tuple, set)):
        names.update(str(r).lower() for r in roles if isinstance(r, str))
    return names


def is_price_locked_user(user) -> bool:
    """Verrou pour tout utilisateur ni admin ni promoteur."""
    return not (user_role_names(user) & set(EXEMPT_ROLES))


def catalog_price_for(session, line):
    """(soumis_au_catalogue, prix Decimal ou None). Import local des modeles
    pour ne pas alourdir l'import du module."""
    from models.pharmacy import Pharmacy
    from models.lab import Examen
    from models.consultation_spirituelle import ConsultationSpirituel

    cat = normalize_item_category(line.get("item_type"))
    ref_id = line.get("item_ref_id")
    if cat in ("medicament", "carnet"):
        obj = session.get(Pharmacy, ref_id) if ref_id else None
        if obj is None:
            raise PriceLockError(f"Produit (ID: {ref_id}) introuvable.")
        return True, obj.price
    if cat == "examen":
        obj = session.get(Examen, ref_id) if ref_id else None
        if obj is None:
            raise PriceLockError(f"Examen (ID: {ref_id}) introuvable.")
        return True, obj.prix
    if cat == "consultation":
        obj = session.get(ConsultationSpirituel, ref_id) if ref_id else None
        if obj is None or obj.type_consultation != "FamilyRestoration":
            return False, None  # Spiritual : pas de tarif
        return True, obj.fr_amount_paid
    return False, None  # Service / autre : prix libre


def check_line_prices(session, items, user, replay: bool) -> list:
    """Verifie chaque ligne active (appeler validate_lines avant : quantite,
    prix >= 0 et line_total sont deja controles). En ligne : PriceLockError au
    premier ecart. En rejeu : retourne la liste des ecarts (vente acceptee)."""
    if not is_price_locked_user(user):
        return []
    mismatches = []
    for line in items or []:
        if not isinstance(line, dict) or line.get("status") == "cancelled":
            continue
        applicable, price = catalog_price_for(session, line)
        if not applicable:
            continue
        sent = _q(line.get("unit_price"))
        catalog = _q(price) if price is not None else None
        if catalog is None or catalog == 0:
            problem = PRICE_UNDEFINED_MSG
        elif sent != catalog:
            problem = PRICE_MISMATCH_MSG
        else:
            continue
        if not replay:
            raise PriceLockError(problem)
        mismatches.append({
            "item_type": line.get("item_type"),
            "item_ref_id": line.get("item_ref_id"),
            "quantity": line.get("quantity"),
            "sent_price": float(sent),
            "catalog_price": float(catalog) if catalog is not None else None,
            "line_total": float(_q(line.get("line_total") or 0)),
            "reason": problem,
        })
    return mismatches


def record_price_mismatches(session, audit_repo, notification_repo, user, tx, mismatches) -> None:
    """1) audit PRICE_MISMATCH commite seul ; 2) notifications aux managers
    actifs (admin, promoteur) dans un second bloc : un echec de notification
    ne peut pas annuler l'audit. Ne leve jamais (la vente est deja commitee)."""
    if not mismatches:
        return
    from repositories.user_repo import UserRepository
    author = getattr(user, "full_name", None) or getattr(user, "username", None)
    tx_id = getattr(tx, "transaction_id", None)

    def _rollback():
        try:
            session.rollback()
        except Exception:
            pass

    if audit_repo is not None:
        try:
            audit_repo.log_user_action(
                current_user=user,
                resource_type="Transaction",
                action_performed=AUDIT_ACTION,
                resource_id=tx_id,
                new_values={"uuid": str(getattr(tx, "uuid", "") or ""), "lines": mismatches},
                details=f"Ecart de prix catalogue sur la vente #{tx_id} (rejeu hors ligne)",
            )
            session.commit()
        except Exception:
            logger.exception("Echec de l'audit d'ecart de prix (vente #%s)", tx_id)
            _rollback()

    if notification_repo is not None:
        try:
            first = mismatches[0]
            payload = {
                "transaction_id": tx_id,
                "item_type": first["item_type"],
                "item_ref_id": first["item_ref_id"],
                "sent_price": first["sent_price"],
                "catalog_price": first["catalog_price"],
                "author_name": author,
                "lines": mismatches,
            }
            for manager in UserRepository(session).get_users_by_role_names(list(EXEMPT_ROLES)):
                notification_repo.create(recipient_user_id=manager.user_id, type=NOTIF_TYPE,
                                         payload=payload)
            session.commit()
        except Exception:
            logger.exception("Echec des notifications d'ecart de prix (vente #%s)", tx_id)
            _rollback()
