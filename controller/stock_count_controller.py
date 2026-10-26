# controller/stock_count_controller.py
"""Comptage physique du stock de la pharmacie (a l'aveugle).

Le controleur possede la transaction (commit ici, rollback sur toute exception) ; le depot ne
commit jamais. Les roles sont verifies ici en plus des gardes des routes.
Erreurs : StockCountNotFoundError -> 404, StockCountConflictError -> 409,
PermissionError -> 403, ValueError -> 422.

Regle d'aveugle : aucune reponse avant la validation (demarrage, comptage en cours, statut de
frequence, messages d'erreur) ne contient la quantite du systeme ni un ecart.
"""
import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.exc import IntegrityError

from controller.stock_controller import _adjustment_dict
from models.stock_count import StockCount, StockCountLine
from models.stock_reception import StockAdjustmentRequest
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from repositories.stock_count_repo import StockCountRepository
from utils.business_time import BUSINESS_TZ
from utils.stock_count_rules import _whole, frequency_status, gap_kind, parse_counted_at, validate_counts

__all__ = ["StockCountController", "StockCountConflictError", "StockCountNotFoundError",
           "get_stock_count_controller"]

# Comptage reserve au StockController : l'auteur d'une demande ne peut pas l'approuver, un comptage
# d'admin serait donc inapprouvable avec un seul admin.
COUNTER_ROLES = ("StockController",)
READER_ROLES = ("StockController", "admin", "promoteur")
ALL_SEEING_ROLES = ("admin", "promoteur")
SCOPES = ("tous", "selection")
STATUSES = ("en_cours", "valide", "abandonne")
FREQUENCY_STATUSES = ("jamais_compte", "en_retard", "a_jour")
DEFAULT_INTERVAL = 30
MAX_LIMIT = 200
SKEW_CAP_S = 600   # ecart d horloge applique au plus (10 min)
SKEW_FLAG_S = 120  # ecart signale dans l audit au dela de 2 min


class StockCountConflictError(Exception):
    """Etat incompatible (comptage deja en cours, deja valide...) -> 409."""


class StockCountNotFoundError(ValueError):
    """Comptage introuvable -> 404."""


def _jsonable(d):
    return None if d is None else json.loads(json.dumps(d, default=str))


def _iso(dt: Optional[datetime]) -> Optional[str]:
    """UTC naif -> ISO avec +00:00 explicite."""
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt is not None else None


def _local_day_start_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=BUSINESS_TZ).astimezone(timezone.utc).replace(tzinfo=None)


def _date(v, label) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            pass
    raise ValueError(f"{label} invalide (format attendu AAAA-MM-JJ).")


def supersede_note(count_id: int) -> str:
    return f"remplacee par le comptage n. {count_id}"


def _utc_clock() -> datetime:
    return datetime.now(timezone.utc)


class StockCountController:
    def __init__(self, repo: StockCountRepository, audit_repo: AuditRepository,
                 notification_repo: NotificationRepository, current_user,
                 clock: Optional[Callable[[], datetime]] = None):
        if repo is None or audit_repo is None or notification_repo is None:
            raise TypeError("StockCountController exige repo, audit_repo et notification_repo.")
        self.repo = repo
        self.audit_repo = audit_repo
        self.notification_repo = notification_repo
        self.user = current_user
        self.session = repo.session
        self._clock = clock or _utc_clock

    # ---------------- helpers ----------------
    def _now(self) -> datetime:
        """Maintenant en UTC naif (format des colonnes)."""
        return self._clock().astimezone(timezone.utc).replace(tzinfo=None)

    def _tx(self, fn):
        try:
            out = fn()
            self.session.commit()
            return out
        except Exception:
            self.session.rollback()
            raise

    def _audit(self, resource_type, action, resource_id, old=None, new=None):
        self.audit_repo.log_user_action(current_user=self.user, resource_type=resource_type,
                                        action_performed=action, resource_id=resource_id,
                                        old_values=_jsonable(old), new_values=_jsonable(new))

    def _role(self) -> Optional[str]:
        role = getattr(self.user, "application_role", None)
        return role.role_name if role else None

    def _require(self, roles, message):
        if self._role() not in roles:
            raise PermissionError(message)

    def _require_counter(self):
        self._require(COUNTER_ROLES, "Seul un controleur de stock peut compter le stock.")

    def _require_reader(self):
        self._require(READER_ROLES, "Acces au comptage du stock refuse.")

    def _sees_all(self) -> bool:
        return self._role() in ALL_SEEING_ROLES

    def _require_owner(self, c: StockCount):
        if c.started_by != self.user.user_id:
            raise PermissionError("Seul l'auteur du comptage peut agir sur ce comptage.")

    def _interval(self) -> int:
        s = self.repo.get_settings()
        return s.interval_days if s is not None and s.interval_days else DEFAULT_INTERVAL

    def _header(self, c: StockCount, names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
        names = names if names is not None else self.repo.user_names([c.started_by])
        return {"id": c.id, "status": c.status, "scope": c.scope, "started_by": c.started_by,
                "started_by_name": names.get(c.started_by), "started_at": _iso(c.started_at),
                "submitted_at": _iso(c.submitted_at)}

    def _stock_at_count(self, l: StockCountLine) -> int:
        """Stock systeme a l'heure du comptage : previous_qty le borne a 0, la valeur reelle (negative
        possible) reste dans la demande (stock_at_request) quand il y en a une."""
        if l.adjustment_request_id is not None:
            req = self.session.get(StockAdjustmentRequest, l.adjustment_request_id)
            if req is not None and req.stock_at_request is not None:
                return req.stock_at_request
        return l.previous_qty

    def _request_outcome(self, l: StockCountLine):
        """(statut, note) de la demande d'ajustement d'une ligne ; 'remplace' = annulee par un comptage plus recent."""
        if l.adjustment_request_id is None:
            return None, None
        req = self.session.get(StockAdjustmentRequest, l.adjustment_request_id)
        if req is None:
            return None, None
        if req.status == "annule" and (req.decision_note or "").startswith("remplacee par le comptage"):
            return "remplace", req.decision_note
        return req.status, req.decision_note

    def my_requests(self, limit: int = 100) -> Dict[str, Any]:
        """Demandes d'ajustement saisies par l'utilisateur (le controleur voit les siennes ; admin/promoteur toutes)."""
        self._require_reader()
        q = self.session.query(StockAdjustmentRequest)
        if not self._sees_all():
            q = q.filter(StockAdjustmentRequest.requested_by == self.user.user_id)
        rows = q.order_by(StockAdjustmentRequest.id.desc()).limit(limit).all()
        items = []
        for r in rows:
            status = "remplace" if (r.status == "annule" and (r.decision_note or "").startswith("remplacee par le comptage")) else r.status
            items.append({"id": r.id, "number": f"AJU-{r.id}", "product_id": r.product_id,
                          "product_name": r.product.drug_name if r.product else None, "status": status,
                          "requested_at": _iso(r.requested_at), "decided_at": _iso(r.decided_at),
                          "decision_note": r.decision_note})
        return {"items": items}

    def _detail(self, c: StockCount) -> Dict[str, Any]:
        out = self._header(c)
        if c.status != "valide":
            out["lines"] = None  # rien n'est revele avant la validation
            return out
        rows = self.repo.lines_with_names(c.id)
        pids = [l.product_id for l, _ in rows]
        before = c.submitted_at
        prev = (self.repo.previous_counts(pids, c.id, before, before - timedelta(days=self._interval()))
                if before is not None else {})
        superseded = self.repo.superseded_by_count(c.id, supersede_note(c.id))
        out["lines"] = [{
            "product_id": l.product_id, "product_name": name, "counted_qty": l.counted_qty,
            "previous_qty": l.previous_qty, "difference": l.difference, "gap_kind": gap_kind(l.difference),
            "movements_during": l.movements_during, "observation": l.observation,
            "counted_at": _iso(l.counted_at), "movements_net": l.movements_net,
            "stock_at_count": self._stock_at_count(l),
            "adjustment_request_id": l.adjustment_request_id,
            "adjustment_status": self._request_outcome(l)[0],
            "adjustment_decision_note": self._request_outcome(l)[1],
            "recount": l.product_id in prev, "previous_count_id": prev.get(l.product_id),
            "superseded_request_ids": superseded.get(l.product_id, []),
        } for l, name in rows]
        return out

    # ---------------- comptage ----------------
    def start(self, scope: str = "tous") -> Dict[str, Any]:
        self._require_counter()
        if scope not in SCOPES:
            raise ValueError("Perimetre de comptage invalide (tous ou selection).")

        def work():
            if self.repo.has_open_count(self.user.user_id):
                raise StockCountConflictError("Vous avez deja un comptage en cours.")
            try:
                c = self.repo.add(StockCount(status="en_cours", started_by=self.user.user_id,
                                             started_at=self._now(), scope=scope))
            except IntegrityError:
                # index unique partiel : un comptage concurrent du meme utilisateur a gagne
                raise StockCountConflictError("Vous avez deja un comptage en cours.")
            header = self._header(c)
            self._audit("StockCount", "CREATE", c.id, new=header)
            products = [{"id": pid, "name": name} for pid, name in self.repo.list_products_lookup()]
            return {"id": c.id, "started_at": header["started_at"], "scope": c.scope, "products": products}
        return self._tx(work)

    def submit(self, count_id: int, lines: List[Dict[str, Any]], client_now: Optional[str] = None) -> Dict[str, Any]:
        """client_now : heure du navigateur a l'envoi (ISO) ; absente = aucun decalage d'horloge."""
        self._require_counter()
        try:
            client_dt = parse_counted_at(client_now)
        except ValueError:
            raise ValueError("Heure du poste (client_now) invalide.")

        def work():
            c = self.repo.get_count(count_id, lock=True)
            if c is None:
                raise StockCountNotFoundError("Comptage introuvable.")
            self._require_owner(c)
            if c.status != "en_cours":
                raise StockCountConflictError(f"Ce comptage n'est plus en cours (statut : {c.status}).")
            clean = validate_counts(lines, self.repo.product_ids())
            now = self._now()
            # ecart d'horloge navigateur -> serveur (borne a +/- 10 min) applique a chaque counted_at :
            # un navigateur en retard ferait passer une vente faite avant le comptage pour posterieure
            raw_skew_s = int(round((now - client_dt).total_seconds())) if client_dt is not None else 0
            skew_s = max(-SKEW_CAP_S, min(SKEW_CAP_S, raw_skew_s))
            skew = timedelta(seconds=skew_s)
            adjusted: Dict[int, bool] = {}
            # demandes de comptages anterieurs encore en attente : verrouillees AVANT les produits
            # (meme ordre que approve_adjustment : demande puis produit), remplacees plus bas
            pending: Dict[int, List[StockAdjustmentRequest]] = {}
            for r in self.repo.lock_pending_count_requests([l["product_id"] for l in clean], c.id):
                if r.status == "en_attente":
                    pending.setdefault(r.product_id, []).append(r)
            computed = []
            # verrous produits en ordre croissant : pas d'interblocage entre validations concurrentes
            for line in sorted(clean, key=lambda x: x["product_id"]):
                prod = self.repo.lock_product(line["product_id"])  # FOR UPDATE + populate_existing
                if prod is None:
                    raise ValueError(f"Produit introuvable : {line['product_id']}.")
                # heure de comptage de la ligne : decalee de l'ecart d'horloge du navigateur, puis bornee a
                # [debut du comptage, maintenant] ; absente = maintenant (non marquee comme ajustee)
                given = line["counted_at"]
                counted_at = min(max(given + skew if given is not None else now, c.started_at), now)
                adjusted[line["product_id"]] = given is not None and counted_at != given
                stock_now = prod.quantity or 0
                # mouvements (ventes, receptions...) faits APRES que l'etagere a ete comptee : retires du
                # stock actuel pour retrouver ce que le systeme disait au moment du comptage
                moves, net = self.repo.movements_after(prod.medication_id, counted_at)
                real = stock_now - net  # stock systeme a l'heure du comptage (peut etre negatif)
                # stock systeme negatif : la ligne garde max(reel, 0) (CHECK previous_qty >= 0),
                # la demande garde la valeur reelle (stock_at_request sans CHECK)
                previous = max(real, 0)
                computed.append((line, prod, real, previous, line["counted_qty"] - previous, moves,
                                 counted_at, net))

            payloads = []
            superseded_notes = []
            note = supersede_note(c.id)
            for line, prod, real, previous, diff, moves, counted_at, net in computed:
                req_id = None
                superseded_ids = []
                for old_req in pending.get(prod.medication_id, []):
                    old_vals = {"status": old_req.status, "decided_by": old_req.decided_by,
                                "decided_at": old_req.decided_at, "decision_note": old_req.decision_note}
                    old_req.status = "annule"
                    old_req.decided_by = self.user.user_id
                    old_req.decided_at = now
                    old_req.decision_note = note
                    self.session.flush()
                    self._audit("StockAdjustmentRequest", "SUPERSEDE", old_req.id, old=old_vals,
                                new={"status": "annule", "decided_by": self.user.user_id, "decided_at": now,
                                     "decision_note": note, "superseded_by_count_id": c.id})
                    superseded_ids.append(old_req.id)
                # compare au stock REEL a l'heure du comptage (un stock negatif compte 0 cree quand meme la
                # correction). L'approbation applique (compte - stock_at_request) au stock ACTUEL :
                # resultat = compte + mouvements faits apres le comptage = quantite reelle en rayon.
                if line["counted_qty"] != real:
                    reason = line["observation"] or (
                        f"Ecart constate au comptage n. {c.id} : systeme {previous}, compte {line['counted_qty']}")
                    if real < 0:
                        reason = f"Stock systeme negatif (valeur lue {real}). {reason}"
                    req = self.repo.add(StockAdjustmentRequest(
                        product_id=prod.medication_id, kind="correction", quantity=line["counted_qty"],
                        reason=reason, status="en_attente", requested_by=self.user.user_id,
                        stock_at_request=real))
                    req_id = req.id
                    self._audit("StockAdjustmentRequest", "CREATE", req.id,
                                new=_adjustment_dict(req, self.repo.user_names([req.requested_by])))
                    payload = {"request_id": req.id, "product_name": prod.drug_name, "kind": "correction",
                               "quantity": line["counted_qty"], "requested_by_name": self.user.full_name}
                    if superseded_ids:
                        payload["supersedes"] = superseded_ids
                    payloads.append(payload)
                elif superseded_ids:
                    superseded_notes.append({"count_id": c.id, "product_name": prod.drug_name,
                                             "superseded_request_ids": superseded_ids,
                                             "counted_by_name": self.user.full_name})
                self.session.add(StockCountLine(
                    count_id=c.id, product_id=prod.medication_id, counted_qty=line["counted_qty"],
                    previous_qty=previous, difference=diff, observation=line["observation"],
                    movements_during=moves, adjustment_request_id=req_id,
                    counted_at=counted_at, movements_net=net))
            self.session.flush()
            c.status = "valide"
            c.submitted_at = now
            self.session.flush()
            out = self._detail(c)
            self._audit("StockCount", "SUBMIT", c.id, old={"status": "en_cours"},
                        new={"status": "valide", "submitted_at": out["submitted_at"],
                             "clock_skew_seconds": skew_s, "clock_skew_flag": abs(raw_skew_s) > SKEW_FLAG_S,
                             "clock_skew_capped": abs(raw_skew_s) > SKEW_CAP_S,
                             "lines": [
                            {**{k: l[k] for k in ("product_id", "counted_qty", "previous_qty", "difference",
                                                  "movements_during", "adjustment_request_id", "counted_at",
                                                  "movements_net", "stock_at_count")},
                             "counted_at_adjusted": adjusted.get(l["product_id"], False)}
                            for l in out["lines"]]})
            for uid in self.repo.admin_user_ids():
                for p in payloads:
                    self.notification_repo.create(uid, "stock_adjustment_request", p)
                for p in superseded_notes:
                    self.notification_repo.create(uid, "stock_count_superseded", p)
            return out
        return self._tx(work)

    def abandon(self, count_id: int) -> Dict[str, Any]:
        self._require_counter()

        def work():
            c = self.repo.get_count(count_id, lock=True)
            if c is None:
                raise StockCountNotFoundError("Comptage introuvable.")
            self._require_owner(c)
            if c.status != "en_cours":
                raise StockCountConflictError(f"Ce comptage n'est plus en cours (statut : {c.status}).")
            c.status = "abandonne"
            self.session.flush()
            self._audit("StockCount", "ABANDON", c.id, old={"status": "en_cours"}, new={"status": "abandonne"})
            return self._header(c)
        return self._tx(work)

    # ---------------- lecture ----------------
    def get(self, count_id: int) -> Dict[str, Any]:
        self._require_reader()
        c = self.repo.get_count(count_id)
        if c is None:
            raise StockCountNotFoundError("Comptage introuvable.")
        if not self._sees_all() and c.started_by != self.user.user_id:
            raise PermissionError("Vous ne pouvez consulter que vos propres comptages.")
        return self._detail(c)

    def list(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._require_reader()
        f = filters or {}
        status = f.get("status") or None
        if status is not None and status not in STATUSES:
            raise ValueError("Statut de comptage invalide.")
        limit = _whole(f.get("limit", 50) if f.get("limit") is not None else 50, "limit")
        offset = _whole(f.get("offset", 0) if f.get("offset") is not None else 0, "offset")
        if not 1 <= limit <= MAX_LIMIT or offset < 0:
            raise ValueError(f"Pagination invalide (1 <= limit <= {MAX_LIMIT}, offset >= 0).")
        d_from = _date(f.get("date_from"), "date_from")
        d_to = _date(f.get("date_to"), "date_to")
        if d_from and d_to and d_from > d_to:
            raise ValueError("date_from doit preceder date_to.")
        mine = f.get("mine")
        if mine is not None and not isinstance(mine, bool):
            raise ValueError("Filtre mine invalide.")
        rows, total = self.repo.list_counts(
            self.user.user_id if (mine or not self._sees_all()) else None, status,
            _local_day_start_utc(d_from) if d_from else None,
            _local_day_start_utc(d_to + timedelta(days=1)) if d_to else None, limit, offset)
        names = self.repo.user_names(c.started_by for c in rows)
        summaries = self.repo.line_summaries([c.id for c in rows if c.status == "valide"])
        items = []
        for c in rows:
            item = self._header(c, names)
            if c.status == "valide":  # resume des ecarts seulement apres validation
                item["lines_count"], item["gaps_count"] = summaries.get(c.id, (0, 0))
            items.append(item)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def status(self) -> Dict[str, Any]:
        self._require_reader()
        interval = self._interval()
        now = self._now()
        last = self.repo.last_counted_by_product()
        counts = {k: 0 for k in FREQUENCY_STATUSES}
        products = []
        for pid, name in self.repo.list_products_lookup():
            st, days = frequency_status(last.get(pid), now, interval)
            counts[st] += 1
            products.append({"product_id": pid, "name": name, "last_counted_at": _iso(last.get(pid)),
                             "days_since": days, "status": st})
        return {"interval_days": interval, "counts": counts, "products": products}

    # ---------------- reglage ----------------
    def get_settings(self) -> Dict[str, Any]:
        self._require_reader()
        s = self.repo.get_settings()
        if s is None:
            return {"interval_days": DEFAULT_INTERVAL, "updated_by": None, "updated_at": None}
        return {"interval_days": s.interval_days, "updated_by": s.updated_by, "updated_at": _iso(s.updated_at)}

    def set_interval(self, days) -> Dict[str, Any]:
        self._require(("admin",), "Seul un administrateur peut modifier la frequence de comptage.")
        days = _whole(days, "La frequence")
        if not 1 <= days <= 365:
            raise ValueError("La frequence doit etre comprise entre 1 et 365 jours.")

        def work():
            old = self.get_settings()
            self.repo.upsert_interval(days, self.user.user_id, self._now())
            new = self.get_settings()
            self._audit("StockCountSettings", "UPDATE", 1, old=old, new=new)
            return new
        return self._tx(work)


def get_stock_count_controller(db, current_user, clock=None) -> StockCountController:
    """Fabrique : les TROIS depots sont reellement injectes (notifications comprises)."""
    return StockCountController(StockCountRepository(db), AuditRepository(db), NotificationRepository(db),
                                current_user, clock=clock)
