# controller/reports_controller.py
"""Rapports / controle quotidien : agregateur de lecture (cartes argent 1 a 5, croissance 12
et 13). Lecture seule : aucune ecriture, aucun commit. Les chiffres viennent des memes
requetes que les ecrans d'origine quand elles existent (CashClosureRepository.flows,
cancellations, clotures stockees) ; le reste est dans ReportRepository.

Periode : jours locaux de Douala [date_from, date_to] inclus, bornes [debut 00:00 Douala,
fin + 1 jour 00:00 Douala) converties selon la convention de chaque colonne (voir
repositories/report_repo.py). Montants : chaines Decimal a 2 decimales.
Erreurs : PermissionError -> 403 (promoteur et admin seulement), ValueError -> 422.
"""
import logging
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable, Dict, Iterable, List, Optional

from repositories.cash_closure_repo import ALL_MODES, CashClosureRepository
from sqlalchemy import func

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from repositories.report_repo import ITEM_TYPES, SORTS, DailyControlRepository, ReportRepository
from utils.business_time import BUSINESS_TZ
from utils.cash_rules import CASH, normalize_mode
from utils.report_rules import (
    MAX_PERIOD_DAYS, diff_anomalies, first_seen_map, normalize_anomaly, parse_period, per_worked_day,
    should_notify, worked_days,
)

log = logging.getLogger(__name__)

ALLOWED_ROLES = ("promoteur", "admin")
CENT = Decimal("0.01")
ZERO = Decimal("0")
GROWTH_WEEKS = 13
RECENT_CANCELLATIONS = 20
LIST_MAX = 20
Q_MAX = 100


def _as_of() -> str:
    """Instant de lecture d'un etat courant : ISO UTC avec +00:00."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _state(current: bool) -> Dict[str, Any]:
    return {"current_state": True, "as_of": _as_of()} if current else {"current_state": False}
AUTO_COMMENT = "commentaire non fourni"  # meme marqueur que CashClosureController


def _m(v) -> Optional[str]:
    if v is None:
        return None
    return str(Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP))


def _local_midnight(d: date) -> datetime:
    return datetime.combine(d, time(0), tzinfo=BUSINESS_TZ)


def _naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _naive_local(d: date) -> datetime:
    return datetime.combine(d, time(0))


def _check_dates(date_from, date_to):
    for v, label in ((date_from, "Date de debut"), (date_to, "Date de fin")):
        if isinstance(v, datetime) or not isinstance(v, date):
            raise ValueError(f"{label} invalide.")
    if date_to < date_from:
        raise ValueError("La date de fin precede la date de debut.")


class ReportsController:
    def __init__(self, session, current_user,
                 clock: Optional[Callable[[], datetime]] = None):
        """current_user None = contexte systeme (script du soir) : seuls le controle quotidien
        et le rattrapage l'acceptent ; aucune ligne d'audit (user_id NOT NULL), l'instantane
        fait foi. clock : surcharge explicite (tests) ; sinon l'heure de la base."""
        self.session = session
        self.user = current_user
        self.clock = clock
        self.repo = ReportRepository(session)
        self.cash_repo = CashClosureRepository(session)
        self.dc_repo = DailyControlRepository(session)
        self._current_cache: Optional[List[Dict[str, Any]]] = None
        self._at_now: Optional[datetime] = None

    # --- outils -------------------------------------------------------------------------
    def _require(self):
        roles = getattr(self.user, "roles", None) or []
        if not any(r in ALLOWED_ROLES for r in roles):
            raise PermissionError("Rapports reserves au promoteur et a l'administrateur.")

    @staticmethod
    def _card(cid: str, period: Dict[str, str], source: str, **data) -> Dict[str, Any]:
        return dict({"id": cid, "title_key": f"reports.cards.{cid}", "period": period,
                     "source": source}, **data)

    # --- argent -------------------------------------------------------------------------
    def money(self, date_from: date, date_to: date) -> Dict[str, Any]:
        self._require()
        _check_dates(date_from, date_to)
        period = {"from": date_from.isoformat(), "to": date_to.isoformat()}
        t0 = _local_midnight(date_from)                         # aware (timestamptz)
        t1 = _local_midnight(date_to + timedelta(days=1))
        return {
            "collected": self._collected(period, t0, t1),
            "cash_gaps": self._cash_gaps(period, date_from, date_to),
            "withdrawals_and_cancellations": self._withdrawals(period, t0, t1),
            "discounts": self._discounts(period, date_from, date_to, t0, t1),
            "per_secretary": self._per_secretary(period, t0, t1),
        }

    def _collected(self, period, t0, t1):
        flows = self.cash_repo.flows(t0, t1)
        by_mode = {m: flows[m]["entries"] for m in ALL_MODES}
        return self._card("collected", period, "Cloture de caisse (entrees)",
                          total=_m(sum(by_mode.values(), ZERO)),
                          by_mode={m: _m(v) for m, v in by_mode.items()})

    def _cash_gaps(self, period, date_from, date_to):
        closures = []
        offset = 0
        while True:  # toutes les clotures de la periode, par pages
            page = self.cash_repo.list_closures(date_from=date_from, date_to=date_to,
                                                limit=500, offset=offset)
            closures += page
            if len(page) < 500:
                break
            offset += 500
        closures.sort(key=lambda c: c.period_end)
        lines = self.cash_repo.lines_for([c.id for c in closures])
        days, total_abs = [], ZERO
        for c in closures:
            ls = lines[c.id]
            for l in ls:
                if l.difference is not None:
                    total_abs += abs(Decimal(l.difference))
            days.append({
                "closure_id": c.id, "business_date": c.business_date.isoformat(),
                "kind": c.kind, "counted_cash": _m(c.counted_cash),
                "expected_cash": _m(c.expected_cash), "difference": _m(c.difference),
                "comment_missing": any((l.comment or "").strip() == AUTO_COMMENT for l in ls),
                "lines": [{"mode": l.mode_code, "expected": _m(l.expected),
                           "counted": _m(l.counted), "difference": _m(l.difference)}
                          for l in ls],
            })
        return self._card("cash_gaps", period, "Clotures de caisse", days=days,
                          total_abs_gap=_m(total_abs), scope="all_modes")

    def _withdrawals(self, period, t0, t1):
        by_mode = {m: ZERO for m in ALL_MODES}
        by_reason: Dict[str, Decimal] = {}
        count, total = 0, ZERO
        for r in self.repo.active_retraits(t0, t1):
            amount = Decimal(r.amount)
            count += 1
            total += amount
            mode = normalize_mode(r.mode) or CASH  # regle de la cloture : sans mode = especes
            by_mode[mode] = by_mode.get(mode, ZERO) + amount
            reason = (r.category or "").strip() or "non_precise"
            by_reason[reason] = by_reason.get(reason, ZERO) + amount
        sales = self.cash_repo.cancellations(t0, t1)
        recent = sorted(sales, key=lambda s: (s["cancelled_at"], s["transaction_id"]),
                        reverse=True)[:RECENT_CANCELLATIONS]
        return self._card(
            "withdrawals_and_cancellations", period, "Retraits et ventes annulees",
            withdrawals={"count": count, "total": _m(total),
                         "by_mode": {m: _m(v) for m, v in by_mode.items()},
                         "by_reason": {k: _m(v) for k, v in sorted(by_reason.items())}},
            cancelled_sales={
                "count": len(sales),
                "invoice_total": _m(sum((s["invoice_amount"] for s in sales), ZERO)),
                "amount_returned": _m(sum((s["amount"] for s in sales), ZERO)),
                "recent": [{"transaction_id": s["transaction_id"],
                            "cancelled_at": s["cancelled_at"].isoformat() if s["cancelled_at"] else None,
                            "cancelled_by": s["cancelled_by"],
                            "cancelled_by_name": s["cancelled_by_name"],
                            "justification": s["justification"],
                            "invoice_amount": _m(s["invoice_amount"]),
                            "amount": _m(s["amount"])} for s in recent],
            })

    def _discounts(self, period, date_from, date_to, t0, t1):
        n, staff_total = self.repo.staff_discounts(
            _naive_local(date_from), _naive_local(date_to + timedelta(days=1)))
        manual_total, manual_n = ZERO, 0
        for r in self.repo.manual_discounts(_naive_utc(t0), _naive_utc(t1)):
            original = Decimal(r.original_amount)
            # meme formule que DiscountRequestController.decide
            net = (original * (Decimal(100) - Decimal(r.decision_percent)) / Decimal(100)
                   ).quantize(CENT, rounding=ROUND_HALF_UP)
            manual_total += original - net
            manual_n += 1
        return self._card("discounts", period, "Demandes de remise et reductions personnel",
                          manual={"count": manual_n, "amount": _m(manual_total),
                                  "basis": "reports.basis.decision_date"},
                          staff={"count": int(n), "amount": _m(staff_total),
                                 "basis": "reports.basis.payment_date"})

    def _per_secretary(self, period, t0, t1):
        users: Dict[int, Dict[str, Any]] = {}
        for r in self.repo.payments_by_user_day(t0, t1):
            u = users.setdefault(r.user_id, {"user_id": r.user_id, "username": r.username,
                                             "full_name": r.full_name, "total": ZERO, "days": [],
                                             "cancelled": ZERO})
            u["total"] += Decimal(r.total or 0)
            u["cancelled"] += Decimal(r.cancelled_total or 0)
            u["days"].append(r.day)
        rows = []
        for u in users.values():
            days = worked_days(u["days"])
            rows.append({"user_id": u["user_id"], "username": u["username"],
                         "full_name": u["full_name"], "collected": _m(u["total"]),
                         # paiements gardes (argent recu par ce compte) dont la vente a ete
                         # annulee ensuite
                         "of_which_cancelled_later": _m(u["cancelled"]),
                         "worked_days": days,
                         "per_worked_day": _m(per_worked_day(u["total"], days))})
        rows.sort(key=lambda r: (-Decimal(r["collected"]), r["user_id"]))
        return self._card("per_secretary", period, "Paiements recus (caisse)", rows=rows)

    # --- produits et stock (cartes 6 a 8) ----------------------------------------------
    @staticmethod
    def _bounds(date_from, date_to):
        """(debut local naif, fin local naive, debut UTC naif, fin UTC naive)."""
        end = date_to + timedelta(days=1)
        return (_naive_local(date_from), _naive_local(end),
                _naive_utc(_local_midnight(date_from)), _naive_utc(_local_midnight(end)))

    def products(self, date_from: date, date_to: date) -> Dict[str, Any]:
        self._require()
        _check_dates(date_from, date_to)
        period = {"from": date_from.isoformat(), "to": date_to.isoformat()}
        lo_l, hi_l, lo_u, hi_u = self._bounds(date_from, date_to)
        receipts = self.repo.received_receipts_qty(lo_u, hi_u)
        reappro = self.repo.received_reappro_qty(lo_u, hi_u)
        return {
            "sold_vs_received": self._card(
                "sold_vs_received", period, "Caisse (ventes actives) et receptions du stock",
                sold=self.repo.sold_stock_qty(lo_l, hi_l), received=receipts + reappro,
                received_detail={"receipts": receipts, "reapprovisionnement": reappro},
                system_stock=self.repo.system_stock(),
                formula_key="reports.formula.sold_vs_received", **_state(False)),
            "stock_count": self._stock_count(period),
            "low_stock": self._low_stock(period),
        }

    def _stock_count(self, period):
        from controller.stock_count_controller import get_stock_count_controller
        st = get_stock_count_controller(self.session, self.user).status()
        rank = {"jamais_compte": 0, "en_retard": 1}
        todo = sorted((p for p in st["products"] if p["status"] in rank),
                      key=lambda p: (rank[p["status"]], -(p["days_since"] or 0),
                                     p["name"] or "", p["product_id"]))
        n, oldest = self.repo.pending_count_requests()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return self._card(
            "stock_count", period, "Comptage du stock (etat actuel)",
            interval_days=st["interval_days"], counts=st["counts"],
            products=[{k: p[k] for k in ("product_id", "name", "status", "days_since",
                                         "last_counted_at")} for p in todo[:LIST_MAX]],
            products_total=len(todo), **_state(True),
            pending_requests={"count": n,
                              "oldest_days": None if oldest is None
                              else max(0, (now - oldest).days)})

    def _low_stock(self, period):
        rows = self.repo.low_stock(LIST_MAX)
        return self._card(
            "low_stock", period, "Stock pharmacie (etat actuel)",
            # regle : quantity <= threshold (badge BAS de l'ecran Stock) ; peut differer de la
            # tuile "stock bas" de cet ecran, qui compte la colonne stockee stock_status
            rule_key="reports.rules.low_stock_quantity_lte_threshold",
            rule_text="quantity <= threshold (badge BAS de l'ecran Stock) ; peut differer de la "
                      "tuile 'stock bas' qui compte la colonne enregistree stock_status",
            **_state(True),
            total=self.repo.low_stock_count(),
            products=[{"product_id": r.product_id, "name": r.name, "category": r.category,
                       "quantity": r.quantity, "threshold": r.threshold} for r in rows])

    # --- production (cartes 9 a 11) -----------------------------------------------------
    def production(self, date_from: date, date_to: date) -> Dict[str, Any]:
        self._require()
        _check_dates(date_from, date_to)
        from controller.fabrication_controller import FabricationController
        from models.fabrication import FabBatch, FabBatchOutput
        from models.stock_reception import ProductionLot
        from repositories.audit_repo import AuditRepository
        from repositories.fabrication_repo import FabricationRepository
        period = {"from": date_from.isoformat(), "to": date_to.isoformat()}
        _, _, lo_u, hi_u = self._bounds(date_from, date_to)
        fab_repo = FabricationRepository(self.session)
        fab = FabricationController(fab_repo, AuditRepository(self.session), self.user)
        s = self.session
        anomalies = fab.list_anomalies()

        # carte 9 : etat des lots, lots trop longs (reglage stale_days de la Fabrication)
        stale = [a for a in anomalies if a["kind"] == "lot_trop_long"]
        batches = self._card(
            "batches", period, "Fabrication (etat actuel)",
            counts_by_status=fab.summary()["counts_by_status"],
            stale_days=fab.get_settings()["stale_days"], stale_total=len(stale),
            stale=[{"batch_id": a["detail"]["batch_id"], "batch_number": a["ref"],
                    "status": a["detail"]["status"], "days": a["detail"]["days"]}
                   for a in stale[:LIST_MAX]], **_state(True))

        # carte 10 : bouteilles (horodatages UTC naifs)
        produced = (s.query(func.coalesce(func.sum(FabBatch.qty_good), 0))
                    .filter(FabBatch.status.in_(("termine", "expedie")),
                            FabBatch.finished_at >= lo_u, FabBatch.finished_at < hi_u).scalar())
        outputs = {"echantillon": 0, "autre": 0}
        for reason, qty in (s.query(FabBatchOutput.reason, func.sum(FabBatchOutput.quantity))
                            .filter(FabBatchOutput.status == "active",
                                    FabBatchOutput.declared_at >= lo_u,
                                    FabBatchOutput.declared_at < hi_u)
                            .group_by(FabBatchOutput.reason)):
            outputs[reason] = int(qty or 0)
        shipped_q = (s.query(FabBatch.product_id, FabBatch.unit_cost, ProductionLot.quantity_produced)
                     .join(ProductionLot, ProductionLot.id == FabBatch.production_lot_id)
                     .filter(FabBatch.status == "expedie", FabBatch.expedited_at >= lo_u,
                             FabBatch.expedited_at < hi_u).all())
        bottles = self._card(
            "bottles", period, "Fabrication (lots termines, sorties declarees, expeditions)",
            produced=int(produced or 0), outputs=outputs,
            shipped=sum(int(q) for _, _, q in shipped_q), **_state(False))

        # carte 11 : hors tolerance (etat actuel) et cout par bouteille bonne
        oot = [a for a in anomalies if a["kind"] == "hors_tolerance"]
        costs = []
        for pid in sorted({pid for pid, _, _ in shipped_q}):
            c = fab.cost_by_product(pid)
            costs.append({"product_id": pid, "product_name": fab_repo.product_name(pid),
                          "last_unit_cost": _m(c["last_unit_cost"]),
                          "average_unit_cost": _m(c["average_unit_cost"]),
                          "batches": c["batches"]})
        unit_costs = [Decimal(u) for _, u, _ in shipped_q if u is not None]
        # meme formule que FabricationController.cost_by_product (moyenne des unit_cost figes),
        # restreinte aux lots expedies dans la periode
        period_avg = (sum(unit_costs, ZERO) / len(unit_costs)) if unit_costs else None
        loss = self._card(
            "loss_and_cost", period, "Fabrication (bilans figes et couts)",
            out_of_tolerance=dict(_state(True), total=len(oot), items=[{"batch_id": a["detail"]["batch_id"], "batch_number": a["ref"],
                               "status": a["detail"]["status"],
                               "missing_qty": a["detail"]["missing_qty"],
                               "missing_pct": _m(a["detail"]["missing_pct"]),
                               "tolerance_applied": _m(a["detail"]["tolerance_applied"])}
                              for a in oot[:LIST_MAX]]),
            # cout par bouteille bonne : cumul sur TOUS les lots expedies de chaque produit ;
            # moyenne de la periode : lots expedies dans la periode seulement
            cost_per_good_bottle=costs, cost_per_good_bottle_scope="all_time",
            period_average_unit_cost=_m(period_avg), period_average_unit_cost_scope="period",
            **_state(False))
        return {"batches": batches, "bottles": bottles, "loss_and_cost": loss}

    # --- tableau vendu par produit ------------------------------------------------------
    def sold_by_product(self, date_from: date, date_to: date, q: Optional[str] = None,
                        item_type: str = "Medicament", category: Optional[str] = None,
                        sort: str = "amount_desc", limit: int = 50,
                        offset: int = 0) -> Dict[str, Any]:
        self._require()
        _check_dates(date_from, date_to)
        if item_type not in ITEM_TYPES:
            raise ValueError("Type de ligne invalide.")
        if sort not in SORTS:
            raise ValueError("Tri invalide.")
        for v, lo, hi, label in ((limit, 1, 200, "Limite"), (offset, 0, None, "Decalage")):
            if not isinstance(v, int) or isinstance(v, bool) or v < lo or (hi is not None and v > hi):
                raise ValueError(f"{label} invalide.")
        q = (q or "").strip() or None
        if q is not None and len(q) > Q_MAX:
            raise ValueError("Recherche trop longue (100 caracteres au plus).")
        category = (category or "").strip() or None
        lo_l, hi_l, _, _ = self._bounds(date_from, date_to)
        rows, total = self.repo.sold_by_product(lo_l, hi_l, item_type, q, category, sort,
                                                limit, offset)
        return {"items": [{"product_id": r.product_id, "name": r.name, "category": r.category,
                           "quantity": int(r.quantity or 0), "amount": _m(r.amount or 0)}
                          for r in rows],
                "total": total, "limit": limit, "offset": offset,
                # montant = SUM(line_total), avant les remises de la vente (reduction personnel,
                # remise approuvee) : peut differer des chiffres encaisses des cartes argent
                "amount_basis": "reports.table.amount_before_discount",
                "note_key": "reports.table.note_differs_from_cash"}

    # --- croissance ---------------------------------------------------------------------
    @staticmethod
    def _series(rows: Iterable, mondays: List[date], money: bool,
                partial_last: bool = False) -> List[Dict[str, Any]]:
        got = {}
        for r in rows:
            wk = r.week if isinstance(r.week, date) else r.week.date()
            got[wk] = r.v
        out = []
        for m in mondays:
            v = got.get(m)
            out.append({"week_start": m.isoformat(),
                        "value": _m(v or 0) if money else int(v or 0),
                        "partial": partial_last and m == mondays[-1]})
        return out

    def growth(self, date_from: date, date_to: date) -> Dict[str, Any]:
        """13 semaines ISO (lundi) finissant a la semaine de date_to ; date_from n'est que
        rapporte dans period."""
        self._require()
        _check_dates(date_from, date_to)
        last = date_to - timedelta(days=date_to.weekday())
        first = last - timedelta(weeks=GROWTH_WEEKS - 1)
        mondays = [first + timedelta(weeks=i) for i in range(GROWTH_WEEKS)]
        prev_first = first - timedelta(weeks=GROWTH_WEEKS)
        prev_mondays = [prev_first + timedelta(weeks=i) for i in range(GROWTH_WEEKS)]
        # derniere semaine partielle si date_to n'est pas un dimanche ; la serie precedente
        # est toujours faite de semaines completes
        part = date_to.weekday() != 6
        lo, hi = _naive_local(first), _naive_local(date_to + timedelta(days=1))
        period = {"from": first.isoformat(), "to": date_to.isoformat()}
        prev_lo, prev_hi = _naive_local(prev_first), _naive_local(first)
        return {
            "new_patients": self._card(
                "new_patients", period, "Patients (date de creation)",
                series=self._series(self.repo.weekly_new_patients(lo, hi), mondays, False, part)),
            "consultations": self._card(
                "consultations", period, "Consultations medicales et spirituelles",
                medical=self._series(self.repo.weekly_medical_consultations(lo, hi), mondays, False, part),
                spiritual=self._series(self.repo.weekly_spiritual_consultations(lo, hi),
                                       mondays, False, part)),
            "sales": self._card(
                "sales", period, "Ventes actives (date de paiement)",
                series=self._series(self.repo.weekly_sales(lo, hi), mondays, True, part),
                sales_previous=self._series(self.repo.weekly_sales(prev_lo, prev_hi),
                                            prev_mondays, True),
                previous_period={"from": prev_first.isoformat(),
                                 "to": (first - timedelta(days=1)).isoformat()}),
        }

    # =====================================================================================
    # Controle quotidien (tache 5)
    # =====================================================================================
    # --- outils -------------------------------------------------------------------------
    def _require_or_system(self):
        if self.user is not None:
            self._require()

    def _require_admin(self):
        if "admin" not in (getattr(self.user, "roles", None) or []):
            raise PermissionError("Seul l'administrateur modifie les seuils du controle.")

    def _tx(self, fn):
        """Execute fn dans une transaction : commit si OK, rollback sur toute exception."""
        try:
            out = fn()
            self.session.commit()
            return out
        except Exception:
            self.session.rollback()
            raise

    def _now(self) -> datetime:
        if self.clock is None:
            return self.session.execute(text("SELECT clock_timestamp()")).scalar()
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError("L'horloge doit fournir une date avec fuseau.")
        return now

    def _aware(self, now: Optional[datetime]) -> datetime:
        if now is None:
            return self._now()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("now doit avoir un fuseau.")
        return now

    def _today(self) -> date:
        return self._now().astimezone(BUSINESS_TZ).date()

    def today(self) -> date:
        """Jour local de Douala selon l'horloge de CE controleur : l'endpoint s'en sert pour
        fixer la periode, get_control pour separer aujourd'hui des jours passes (une seule
        horloge)."""
        return self._today()

    @staticmethod
    def _check_day(day):
        if isinstance(day, datetime) or not isinstance(day, date):
            raise ValueError("Date invalide.")

    def _audit(self, resource_type, action, resource_id, old=None, new=None):
        if self.user is None:
            return  # script du soir sans utilisateur : l'instantane fait foi
        from repositories.audit_repo import AuditRepository
        AuditRepository(self.session).log_user_action(
            current_user=self.user, resource_type=resource_type, action_performed=action,
            resource_id=resource_id, old_values=old, new_values=new)

    # --- reglages -----------------------------------------------------------------------
    def _settings(self) -> Dict[str, Any]:
        row = self.dc_repo.settings_row()
        if row is None:
            return {"cancelled_sales_threshold": DEFAULT_CANCELLED_THRESHOLD,
                    "adjustment_pending_days": DEFAULT_PENDING_DAYS, "updated_at": None}
        return {"cancelled_sales_threshold": row.cancelled_sales_threshold,
                "adjustment_pending_days": row.adjustment_pending_days,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None}

    def get_settings(self) -> Dict[str, Any]:
        self._require()
        return self._settings()

    def set_settings(self, cancelled_sales_threshold, adjustment_pending_days) -> Dict[str, Any]:
        self._require_admin()
        for v, lo, hi, label in ((cancelled_sales_threshold, 1, 1000, "Seuil de ventes annulees"),
                                 (adjustment_pending_days, 1, 365, "Delai d'attente des ajustements")):
            if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
                raise ValueError(f"{label} : nombre entier entre {lo} et {hi}.")

        def run():
            old = self._settings()
            at = self._now().astimezone(timezone.utc).replace(tzinfo=None)
            self.dc_repo.upsert_settings(cancelled_sales_threshold, adjustment_pending_days,
                                         self.user.user_id, at)
            new = self._settings()
            self._audit("ReportSettings", "UPDATE", 1, old=old, new=new)
            return new
        return self._tx(run)

    # --- anomalies ----------------------------------------------------------------------
    def compute_anomalies(self, day: date) -> List[Dict[str, Any]]:
        """Anomalies normalisees du jour local de Douala `day` : sources du jour (cloture,
        annulations, prix, sorties 'autre') + etats courants (fabrication, comptage,
        ajustements en attente), recalcules a chaque appel tant qu'ils restent vrais."""
        self._require_or_system()
        self._check_day(day)
        current = self._current_cache if self._current_cache is not None \
            else self._current_anomalies()
        out, seen = [], set()
        for raw in self._day_anomalies(day) + current:
            a = normalize_anomaly(raw)
            if a["key"] in seen:
                continue
            seen.add(a["key"])
            a["detail"] = _jsonable(a["detail"] or {})
            a["link"] = raw["link"]
            out.append(a)
        return out

    def _day_anomalies(self, day: date) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        d = day.isoformat()
        t0, t1 = _local_midnight(day), _local_midnight(day + timedelta(days=1))
        _, _, lo_u, hi_u = self._bounds(day, day)
        settings = self._settings()

        # (1) caisse : clotures dont la date d'activite est `day`
        closures = self.cash_repo.list_closures(date_from=day, date_to=day, limit=500)
        lines = self.cash_repo.lines_for([c.id for c in closures])
        kinds = {c.kind for c in closures}
        if "auto" in kinds and "manual" not in kinds:
            out.append({"kind": "cloture_auto", "ref": d, "link": LINK_CASH,
                        "label": "Journée sans clôture manuelle (fermée par la clôture automatique)",
                        "detail": {"business_date": d,
                                   "closure_ids": sorted(c.id for c in closures)}})
        gaps: Dict[str, Decimal] = {}
        missing = []
        for c in sorted(closures, key=lambda c: c.period_end):
            for l in lines[c.id]:
                if l.difference is not None and Decimal(l.difference) != 0:
                    gaps[l.mode_code] = gaps.get(l.mode_code, ZERO) + Decimal(l.difference)
                if (l.comment or "").strip() == AUTO_COMMENT and c.id not in missing:
                    missing.append(c.id)
        for mode, diff in sorted(gaps.items()):
            out.append({"kind": "ecart_caisse", "ref": f"{d}:{mode}", "link": LINK_CASH,
                        "label": f"Écart de caisse ({mode}) : {_m(diff)}",
                        "detail": {"business_date": d, "mode": mode, "difference": _m(diff)}})
        if missing:
            out.append({"kind": "commentaire_manquant", "ref": d, "link": LINK_CASH,
                        "label": "Clôture avec un écart sans commentaire",
                        "detail": {"business_date": d, "closure_ids": missing}})

        # (2) ventes : annulations du jour au-dela du seuil, prix differents du catalogue
        cancelled = self.cash_repo.cancellations(t0, t1)
        threshold = settings["cancelled_sales_threshold"]
        if len(cancelled) > threshold:
            out.append({"kind": "ventes_annulees", "ref": d, "link": LINK_CASH,
                        "label": f"{len(cancelled)} ventes annulées dans la journée (seuil {threshold})",
                        "detail": {"business_date": d, "count": len(cancelled), "threshold": threshold,
                                   "transaction_ids": [s["transaction_id"] for s in cancelled]}})
        for r in self.dc_repo.price_mismatch_sales(t0, t1):
            out.append({"kind": "prix_different", "ref": r.sale_id, "link": LINK_PRICE,
                        "label": f"Prix différent du catalogue sur la vente n. {r.sale_id}",
                        "detail": {"transaction_id": r.sale_id, "at": r.at, "alerts": int(r.n)}})

        # (3) production : sorties 'autre' actives declarees ce jour
        for o in self.dc_repo.other_outputs(lo_u, hi_u):
            out.append({"kind": "sortie_autre", "ref": o.id, "link": f"{LINK_FAB}/{o.batch_id}",
                        "label": f"Sortie 'autre' de {o.quantity} bouteille(s) sur le lot {o.batch_number}",
                        "detail": {"output_id": o.id, "batch_id": o.batch_id,
                                   "batch_number": o.batch_number, "quantity": o.quantity,
                                   "note": o.note, "declared_at": o.declared_at}})
        return out

    def _current_anomalies(self) -> List[Dict[str, Any]]:
        from controller.fabrication_controller import FabricationController
        from controller.stock_count_controller import DEFAULT_INTERVAL
        from repositories.audit_repo import AuditRepository
        from repositories.fabrication_repo import FabricationRepository
        from repositories.stock_count_repo import StockCountRepository
        from utils.stock_count_rules import frequency_status

        out: List[Dict[str, Any]] = []
        now = (self._at_now or self._now()).astimezone(timezone.utc).replace(tzinfo=None)

        # (3) production : anomalies de la Fabrication (etat courant)
        fab = FabricationController(FabricationRepository(self.session),
                                    AuditRepository(self.session), self.user)
        for a in fab.list_anomalies():
            if a["kind"] == "intrant_sous_seuil":
                det = a["detail"]
                out.append({"kind": "intrant_sous_seuil", "ref": a["ref"], "link": LINK_FAB_INTRANTS,
                            "label": f"Intrant {a['ref']} sous le seuil d'alerte",
                            "detail": dict(det, intrant_name=a["ref"])})
                continue
            spec = FAB_KINDS.get(a["kind"])
            if spec is None:
                continue
            kind, label = spec
            det = a["detail"]
            out.append({"kind": kind, "ref": a["ref"], "link": f"{LINK_FAB}/{det['batch_id']}",
                        "label": label.format(n=a["ref"], days=det.get("days")),
                        "detail": dict(det, batch_number=a["ref"])})

        # (4) stock : meme regle que StockCountController.status (frequency_status)
        sc = StockCountRepository(self.session)
        st = sc.get_settings()
        interval = st.interval_days if st is not None and st.interval_days else DEFAULT_INTERVAL
        last = sc.last_counted_by_product()
        groups: Dict[str, List[str]] = {"jamais_compte": [], "en_retard": []}
        for pid, name in sc.list_products_lookup():
            status, _ = frequency_status(last.get(pid), now, interval)
            if status in groups:
                groups[status].append(name or f"#{pid}")
        # UNE cle par nature ("tous") : le nombre peut changer sans rendre le point nouveau
        for status, kind, words in (("jamais_compte", "comptage_jamais", "jamais compté(s)"),
                                    ("en_retard", "comptage_retard", "en retard de comptage")):
            names = sorted(groups[status])
            if names:
                out.append({"kind": kind, "ref": "tous", "link": LINK_COUNT,
                            "label": f"{len(names)} produit(s) {words}",
                            "detail": {"total": len(names), "products": names[:LIST_MAX],
                                       "interval_days": interval}})

        # (4) demandes d'ajustement en attente depuis STRICTEMENT plus que le reglage
        wait = self._settings()["adjustment_pending_days"]
        for r in self.dc_repo.pending_adjustments_before(now - timedelta(days=wait)):
            days = (now - r.requested_at).days
            out.append({"kind": "ajustement_en_attente", "ref": r.id, "link": LINK_ADJUST,
                        "label": f"Demande d'ajustement n. {r.id} en attente depuis {days} jours",
                        "detail": {"request_id": r.id, "product_id": r.product_id,
                                   "kind": r.kind, "quantity": r.quantity,
                                   "requested_at": r.requested_at, "days": days}})
        # (4b) ajustements de caisse (corrections de cloture) en attente depuis plus que ce meme reglage
        cutoff = now - timedelta(days=wait)
        for c in self.cash_repo.list_corrections("pending"):
            req = c.requested_at
            if req is not None and req.tzinfo is not None:
                req = req.astimezone(timezone.utc).replace(tzinfo=None)
            if req is not None and req < cutoff:
                days = (now - req).days
                out.append({"kind": "ajustement_caisse_en_attente", "ref": c.id, "link": LINK_CASH,
                            "label": f"Ajustement de caisse n. {c.id} en attente depuis {days} jours",
                            "detail": {"correction_id": c.id, "closure_id": c.closure_id, "mode": c.mode_code,
                                       "amount_delta": _m(c.amount_delta), "requested_at": c.requested_at,
                                       "days": days}})
        for a in out:  # etat courant : lu maintenant, meme pour un jour passe
            a["detail"]["current_state"] = True
        return out

    # --- instantane et notification -----------------------------------------------------
    @staticmethod
    def _keys(row) -> List[str]:
        return [a["key"] for a in (row.anomalies or [])]

    def _write_snapshot(self, day: date, now: datetime, decide: bool,
                        base_keys=None, since=None):
        """Ecrit l'instantane de `day` ET, si decide, la decision d'envoi (notify_reason et
        compteurs), dans la meme transaction. base_keys/since : reference d'un rattrapage."""
        from models.report import DailyControl
        existing = self.dc_repo.control_for(day)
        if existing is not None:
            return existing, False
        anomalies = self.compute_anomalies(day)
        prev = self.dc_repo.previous_control(day)
        d = diff_anomalies(set(self._keys(prev)) if prev is not None else set(), anomalies)
        keys = [a["key"] for a in anomalies]
        snaps = [{"business_date": s.business_date, "keys": self._keys(s)}
                 for s in self.dc_repo.controls_upto(day - timedelta(days=1))]
        fs = first_seen_map(snaps + [{"business_date": day, "keys": keys}])
        local = now.astimezone(BUSINESS_TZ)
        row = DailyControl(
            business_date=day,
            anomalies=[dict(a, first_seen=fs[a["key"]].isoformat()) for a in anomalies],
            new_count=len(d["new"]), open_count=len(anomalies),
            computed_at=now.astimezone(timezone.utc).replace(tzinfo=None),
            # honnetete de l'historique : seul un calcul fait le jour meme a 23:30 ou apres
            # est un instantane du soir ; tout autre (retard, rattrapage) est "recalcule"
            recomputed=not (local.date() == day and local.time() >= CONTROL_TIME))
        if decide:
            if base_keys is None:
                new = row.new_count
            else:
                new = len([k for k in keys if k not in base_keys])
            # Rappel : l'intervalle de 7 jours part du dernier envoi REUSSI (notified_at /
            # reminder_sent_at). Un envoi echoue le jour N ne compte pas : le jour N+1 peut
            # decider 'rappel' alors que la relance de N part dans le meme passage (accepte :
            # deux messages au plus, jamais un point perdu).
            last = self.dc_repo.last_notice_before(since or day)
            ok, reason = should_notify([None] * new, [None] * (row.open_count - new), last,
                                       now.astimezone(timezone.utc).replace(tzinfo=None))
            if ok:
                row.notify_reason = reason
                row.notify_new_count = new
                row.notify_open_count = row.open_count
        try:
            with self.session.begin_nested():
                self.session.add(row)
                self.session.flush()
        except IntegrityError:  # UNIQUE(business_date) : une autre execution a ecrit ce jour
            return self.dc_repo.control_for(day), False
        self._audit("DailyControl", "RUN", row.id,
                    new={"business_date": day.isoformat(), "new_count": row.new_count,
                         "open_count": row.open_count, "notify_reason": row.notify_reason})
        return row, True

    def _send(self, row, now: datetime) -> bool:
        """Envoie EXACTEMENT la decision stockee, dans sa propre transaction. Rien a envoyer
        (notify_reason NULL) ou deja envoye : False. Echec : rollback, reste en attente."""
        from repositories.notification_repo import NotificationRepository
        if row is None or row.notify_reason is None or row.notified_at is not None:
            return False
        try:
            payload = {"business_date": row.business_date.isoformat(),
                       "new_count": row.notify_new_count, "open_count": row.notify_open_count,
                       "reason": row.notify_reason}
            notifs = NotificationRepository(self.session)
            for uid in self.cash_repo.recipient_user_ids():
                notifs.create(uid, NOTIF_TYPE, payload)
            at = now.astimezone(timezone.utc).replace(tzinfo=None)
            row.notified_at = at
            if row.notify_reason == "rappel":
                row.reminder_sent_at = at
            self.session.flush()
            self.session.commit()
            return True
        except Exception:
            log.exception("Echec de la notification du controle du %s", row.business_date)
            self.session.rollback()
            return False

    @staticmethod
    def _result(row, created: bool, notified: bool) -> Dict[str, Any]:
        return {"day": row.business_date.isoformat(), "new": row.new_count,
                "still_open": row.open_count - row.new_count, "open": row.open_count,
                "created": created, "notified": notified,
                "reason": row.notify_reason if notified else None,
                "recomputed": bool(row.recomputed)}

    def run_daily_control(self, day: date, now: Optional[datetime] = None,
                          notify: bool = True, _base_keys=None, _since=None) -> Dict[str, Any]:
        """Calcule, compare a l'instantane precedent, ecrit l'instantane de `day` avec la
        decision d'envoi (une fois : un second appel renvoie l'existant sans notifier), puis
        envoie la decision."""
        self._require_or_system()
        self._check_day(day)
        now = self._aware(now)
        self._at_now = now  # une seule source d'heure pour les etats courants
        try:
            row, created = self._tx(lambda: self._write_snapshot(day, now, notify, _base_keys, _since))
        finally:
            self._at_now = None
        notified = self._send(row, now) if created else False
        return self._result(row, created, notified)

    def retry_notification(self, day: date) -> bool:
        """Envoie la decision stockee d'un instantane en attente (notify_reason non NULL,
        notified_at NULL). Jamais de nouvelle decision."""
        self._require_or_system()
        return self._send(self.dc_repo.control_for(day), self._now())

    def catch_up(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Relance les envois en attente, puis ecrit les jours manques du plus ancien au plus
        recent (30 jours au plus apres le dernier instantane ; sans aucun historique : hier
        seulement), aujourd'hui a partir de 23:30 Douala. Une notification au plus, portee par
        le dernier jour traite, contre l'instantane d'avant le premier jour traite.
        Verrou consultatif de session : une seconde execution simultanee renvoie []."""
        self._require_or_system()
        now = self._aware(now)
        if not self.dc_repo.try_lock():
            self.session.rollback()
            return []
        try:
            for row in self.dc_repo.pending_notifications():
                self._send(row, now)
            local = now.astimezone(BUSINESS_TZ)
            today = local.date()
            end = today if local.time() >= CONTROL_TIME else today - timedelta(days=1)
            latest = self.dc_repo.latest_control()
            if latest is None:
                start = today - timedelta(days=1)
            else:
                start = max(today - timedelta(days=MAX_CATCH_UP_DAYS),
                            latest.business_date + timedelta(days=1))
            if start > end:
                return []
            prev = self.dc_repo.previous_control(start)
            base = set(self._keys(prev)) if prev is not None else set()
            out = []
            d = start
            while d <= end:
                if d < end:
                    out.append(self.run_daily_control(d, now, notify=False))
                else:  # dernier jour : decision du lot entier
                    out.append(self.run_daily_control(d, now, True, base, start))
                d += timedelta(days=1)
            return out
        finally:
            try:
                self.dc_repo.unlock()
                self.session.commit()
            except Exception:
                self.session.rollback()
                try:
                    self.dc_repo.unlock()
                    self.session.commit()
                except Exception:
                    log.exception("Liberation du verrou du controle quotidien impossible")

    # --- lecture ------------------------------------------------------------------------
    def get_control(self, date_from: date, date_to: date) -> Dict[str, Any]:
        """Union par cle des anomalies de la periode DEJA ANALYSEE par l'appelant (l'endpoint
        la fixe avec self.today() : pas de second defaut ici, une seule horloge).
        Jour avec instantane : l'instantane ; aujourd'hui sans instantane : en direct ; jour
        passe sans instantane : en direct et signale dans `recomputed`, pour les
        MAX_LIVE_DAYS plus recents seulement ; les plus anciens ne sont pas calcules
        (requetes bornees) et sont comptes dans `uncontrolled_days` / `uncontrolled_range`.
        N'ecrit et ne notifie jamais."""
        self._require()
        _check_dates(date_from, date_to)
        if (date_to - date_from).days + 1 > MAX_PERIOD_DAYS:
            raise ValueError(f"Periode limitee a {MAX_PERIOD_DAYS} jours.")
        d_from, d_to = date_from, date_to
        today = self._today()
        stored = {s.business_date: s for s in self.dc_repo.controls_upto(d_to)}
        per_day: Dict[date, List[Dict[str, Any]]] = {}
        recomputed: List[str] = []
        live_days: List[date] = []
        days = [d_from + timedelta(days=i) for i in range((min(d_to, today) - d_from).days + 1)]
        uncovered = [d for d in days if d not in stored]
        skipped = uncovered[:-MAX_LIVE_DAYS] if len(uncovered) > MAX_LIVE_DAYS else []
        skip = set(skipped)
        try:
            for d in days:
                if d in stored:
                    per_day[d] = list(stored[d].anomalies or [])
                    if stored[d].recomputed:  # instantane tardif ou de rattrapage
                        recomputed.append(d.isoformat())
                elif d not in skip:
                    if self._current_cache is None:  # etats courants : calcules une fois
                        self._current_cache = self._current_anomalies()
                    per_day[d] = self.compute_anomalies(d)
                    live_days.append(d)
                    if d < today:
                        recomputed.append(d.isoformat())
        finally:
            self._current_cache = None
        snaps = [{"business_date": s.business_date, "keys": self._keys(s)} for s in stored.values()]
        snaps += [{"business_date": x, "keys": [a["key"] for a in per_day[x]]} for x in live_days]
        fs = first_seen_map(snaps)
        notified_on: Dict[str, date] = {}
        for s in sorted(stored.values(), key=lambda s: s.business_date):
            if s.notified_at is not None:
                for k in self._keys(s):
                    notified_on.setdefault(k, s.business_date)
        items: Dict[str, Dict[str, Any]] = {}
        for day in sorted(per_day):
            for a in per_day[day]:
                item = {k: a.get(k) for k in ("key", "kind", "ref", "label", "detail", "link")}
                item["last_seen"] = day.isoformat()
                item["current_state"] = bool((a.get("detail") or {}).get("current_state"))
                item["recomputed"] = day.isoformat() in recomputed
                items[a["key"]] = item
        out = []
        for k, item in items.items():
            item["first_seen"] = fs[k].isoformat()
            on = notified_on.get(k)
            item["already_notified_on"] = on.isoformat() if on else None
            out.append(item)
        out.sort(key=lambda i: (i["first_seen"], i["key"]))
        return {"items": out, "recomputed": recomputed,
                "uncontrolled_days": len(skipped),
                "uncontrolled_range": ({"from": skipped[0].isoformat(), "to": skipped[-1].isoformat()}
                                       if skipped else None),
                "period": {"from": d_from.isoformat(), "to": d_to.isoformat()}}


# --- controle quotidien : constantes et fabrique ------------------------------------------
NOTIF_TYPE = "daily_control"
DEFAULT_CANCELLED_THRESHOLD = 3
DEFAULT_PENDING_DAYS = 3
MAX_CATCH_UP_DAYS = 30
MAX_LIVE_DAYS = 31  # jours sans instantane recalcules en direct par get_control, au plus
CONTROL_TIME = time(23, 30)
LINK_CASH = "/dashboard/cash-closures"
LINK_PRICE = "/dashboard/finance"
LINK_FAB = "/dashboard/fabrication-lots"
LINK_FAB_INTRANTS = "/dashboard/fabrication-intrants"
LINK_COUNT = "/dashboard/stock-count"
LINK_ADJUST = "/dashboard/stock-adjustment-requests"
FAB_KINDS = {
    "hors_tolerance": ("lot_hors_tolerance", "Lot {n} hors tolérance"),
    "lot_trop_long": ("lot_trop_long", "Lot {n} en cours depuis {days} jours"),
    "ecart_expedie_recu": ("ecart_expedie_recu", "Lot {n} : écart entre expédié et reçu"),
}


def _jsonable(v):
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def get_reports_controller(db, current_user, clock=None) -> ReportsController:
    """Fabrique : current_user None = contexte systeme (script du soir)."""
    return ReportsController(db, current_user, clock=clock)
