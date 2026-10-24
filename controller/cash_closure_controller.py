# controller/cash_closure_controller.py
"""Cloture de caisse : depart, cloture manuelle (comptage a l'aveugle), cloture automatique a
23:00 Africa/Douala, notifications promoteur + admins, audit, lecture.

Le controleur possede la transaction (commit ici, rollback sur toute exception) ; le depot ne
commit jamais. Les roles sont verifies par les endpoints (tache 5), sauf set_start (admin).
Erreurs : CashClosureNotFoundError -> 404, CashClosureConflictError -> 409,
PermissionError -> 403, ValueError -> 422.

Regles (voir le plan, "Global Constraints", et les arbitrages de la tache 4) :
- Tant que cash_closure_start n'existe pas : status() dit configured=False, submit refuse (409),
  auto_close_overdue ne fait rien.
- t0 = period_end de la derniere cloture, sinon started_at. Chaque cloture commence a la fin
  de la precedente (verifie aussi par le depot a l'insertion).
- Ouverture especes = counted_cash de la precedente, ou son expected_cash si elle etait
  automatique (opening_from_auto=True). Modes mobiles : pas d'ouverture.
- Lignes : chaque mode actif ; plus especes toujours ; plus tout mode inactif ou 'non_classe'
  qui a des mouvements dans la periode (counted NULL : non comptable par la secretaire).
- Verrou : pg_try_advisory_xact_lock pris AVANT de lire la derniere cloture et de fixer t1 ;
  une seconde cloture simultanee recoit 409. UNIQUE(period_end) reste le filet.
- anomaly = cloture auto, ou au moins un ecart non nul sur une ligne.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Optional

from models.cash_closure import CashClosure, CashClosureCorrection, CashClosureLine, PaymentMode
from sqlalchemy import text

from repositories.audit_repo import AuditRepository
from repositories.cash_closure_repo import (
    CashClosureConflictError, CashClosureNotFoundError, CashClosureRepository,
)
from repositories.notification_repo import NotificationRepository
from utils.cash_lock import lock_cash_write
from utils.cash_rules import (
    CASH, TZ, UNCLASSIFIED, closing_time_for, compute_line, overdue_days, require_comment_if_gap,
)

__all__ = ["CashClosureController", "CashClosureConflictError", "CashClosureNotFoundError",
           "get_cash_closure_controller"]

CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("999999999999.99")  # Numeric(14, 2)
MAX_COMMENT = 2000
ZERO = Decimal("0")
NOTIF_TYPE = "cash_closure"
LINE_FIELDS = ("opening", "entries", "exits", "expected", "counted", "difference", "comment")


MAX_GAP_REFUSALS = 3
AUTO_COMMENT = "commentaire non fourni"
GAP_REFUSED_ACTION = "CLOSURE_GAP_REFUSED"


class GapCommentRequired(ValueError):
    """Ecart sans commentaire (-> 422). Chaque refus est audite ; apres MAX_GAP_REFUSALS
    refus sur la meme periode (tous utilisateurs confondus), la cloture suivante est acceptee avec
    AUTO_COMMENT et marquee anomalie (comment_missing). Residuel assume : au plus 3 sondages
    d'un bit chacun (ecart nul ou non), tous audites et visibles."""

    def __init__(self, msg, period_start):
        super().__init__(msg)
        self.period_start = period_start


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _source(mode: str) -> str:
    return "physical" if mode == CASH else "operator_statement"


def _amount(v, label) -> Decimal:
    if v is None or isinstance(v, (bool, float)):
        raise ValueError(f"{label} invalide.")
    try:
        d = Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} invalide.")
    if not d.is_finite():
        raise ValueError(f"{label} invalide.")
    if d < 0:
        raise ValueError(f"{label} ne peut pas etre negatif.")
    if d > MAX_AMOUNT:
        raise ValueError(f"{label} depasse la limite autorisee.")
    if d != d.quantize(CENT):
        raise ValueError(f"{label} : precision excessive.")
    return d.quantize(CENT)


def _comment(v) -> Optional[str]:
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("Commentaire invalide.")
    v = v.strip()
    if len(v) > MAX_COMMENT:
        raise ValueError(f"Commentaire : {MAX_COMMENT} caracteres au plus.")
    return v or None


def _is_auto_comment(v) -> bool:
    return (v or "").strip() == AUTO_COMMENT


def _s(d: Optional[Decimal]) -> Optional[str]:
    return None if d is None else str(d)


_UNSET = object()
MAX_LABEL = 80
CORRECTION_STATUSES = ("pending", "approved", "rejected")


def _instant(v) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Date de derniere cloture invalide.")
    else:
        raise ValueError("Date de derniere cloture invalide.")
    if dt.tzinfo is None:
        raise ValueError("La date de derniere cloture doit avoir un fuseau.")
    return dt


def _delta(v) -> Decimal:
    """Montant de correction : signe, non nul, 2 decimales au plus."""
    if v is None or isinstance(v, (bool, float)):
        raise ValueError("Montant de correction invalide.")
    try:
        d = Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        raise ValueError("Montant de correction invalide.")
    if not d.is_finite() or d == 0:
        raise ValueError("Le montant de correction doit etre non nul.")
    if abs(d) > MAX_AMOUNT:
        raise ValueError("Montant de correction : depasse la limite autorisee.")
    if d != d.quantize(CENT):
        raise ValueError("Montant de correction : precision excessive.")
    return d.quantize(CENT)


def _label(v) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError("Libelle obligatoire.")
    v = v.strip()
    if len(v) > MAX_LABEL:
        raise ValueError(f"Libelle : {MAX_LABEL} caracteres au plus.")
    return v


def _sort_order(v) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not -10000 <= v <= 10000:
        raise ValueError("Ordre d'affichage invalide.")
    return v


def _mode_out(m: PaymentMode) -> Dict[str, Any]:
    return {"code": m.code, "label": m.label, "is_active": m.is_active, "sort_order": m.sort_order}


def _corr_out(c: CashClosureCorrection) -> Dict[str, Any]:
    return {"id": c.id, "closure_id": c.closure_id, "mode_code": c.mode_code,
            "amount_delta": c.amount_delta, "reason": c.reason, "status": c.status,
            "requested_by": c.requested_by, "requested_at": c.requested_at,
            "decided_by": c.decided_by, "decided_at": c.decided_at}


class CashClosureController:
    def __init__(self, repo: CashClosureRepository, audit_repo: AuditRepository,
                 notification_repo: NotificationRepository, current_user,
                 clock: Optional[Callable[[], datetime]] = None):
        if repo is None or audit_repo is None or notification_repo is None:
            raise TypeError("CashClosureController exige repo, audit_repo et notification_repo.")
        self.repo = repo
        self.audit_repo = audit_repo
        self.notification_repo = notification_repo
        self.user = current_user
        self.session = repo.session
        # clock : surcharge EXPLICITE (tests). Sans elle, l'heure vient de la base
        # (clock_timestamp()), la meme horloge que les ecrivains d'argent (utils/cash_lock.py) :
        # une horloge applicative en avance ne peut pas placer t1 au-dessus d'un received_at futur.
        self.clock = clock

    # --- outils -------------------------------------------------------------------------
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

    def _lock(self):
        if not self.repo.try_lock():
            raise CashClosureConflictError("Une cloture de caisse est deja en cours. Reessayez.")

    def _audit(self, resource_type, action, resource_id, new):
        if self.user is None:
            return  # rattrapage sans utilisateur (script) : la cloture elle-meme fait foi
        self.audit_repo.log_user_action(current_user=self.user, resource_type=resource_type,
                                        action_performed=action, resource_id=resource_id,
                                        new_values=new)

    def _chain_point(self, start):
        """(t0, derniere cloture) : fin de la derniere cloture, sinon debut du suivi."""
        last = self.repo.last_closure()
        return (last.period_end if last is not None else start.started_at), last

    @staticmethod
    def _due_days(last, t0: datetime, now: datetime) -> list:
        """Jours a cloturer automatiquement. Un jour qui a deja une cloture MANUELLE (la
        derniere, de meme date locale Douala) est cloture : pas de cloture auto residuelle ;
        les flux suivants tombent dans la periode suivante. Seul point d'usage de overdue_days."""
        days = overdue_days(t0, now)
        if last is not None and last.kind == "manual":
            manual_day = last.period_end.astimezone(TZ).date()
            days = [d for d in days if d != manual_day]
        return days

    @staticmethod
    def _opening(start, last) -> tuple:
        if last is None:
            return Decimal(start.opening_cash), False
        if last.counted_cash is None:  # cloture automatique : rien n'a ete compte
            return Decimal(last.expected_cash), True
        return Decimal(last.counted_cash), False

    def _detail(self, c: CashClosure, lines: List[CashClosureLine],
                applied: Optional[List[CashClosureCorrection]] = None) -> Dict[str, Any]:
        if applied is None:  # lecture : recalcule depuis decided_at dans [period_start, period_end)
            applied = self.repo.approved_corrections(c.period_start, c.period_end)
        return {
            # ventes annulees dans [period_start, period_end) : auteur, montant rendu, motif, vente
            "cancellations": [{"transaction_id": x["transaction_id"],
                               "cancelled_at": x["cancelled_at"],
                               "cancelled_by": x["cancelled_by"],
                               "cancelled_by_name": x["cancelled_by_name"],
                               "justification": x["justification"],
                               "invoice_amount": x["invoice_amount"], "amount": x["amount"],
                               "by_mode": dict(x["by_mode"])}
                              for x in self.repo.cancellations(c.period_start, c.period_end)],
            # regularisations comprises dans entries/exits de cette cloture
            "corrections_applied": [{"id": x.id, "closure_id": x.closure_id,
                                     "mode": x.mode_code, "amount_delta": x.amount_delta,
                                     "reason": x.reason, "decided_by": x.decided_by,
                                     "decided_at": x.decided_at} for x in applied],
            "id": c.id, "period_start": c.period_start, "period_end": c.period_end,
            "business_date": c.business_date, "kind": c.kind, "closed_by": c.closed_by,
            "closed_at": c.closed_at, "opening_cash": c.opening_cash,
            "expected_cash": c.expected_cash, "counted_cash": c.counted_cash,
            "difference": c.difference, "opening_from_auto": c.opening_from_auto,
            "comment": c.comment, "unsynced_ignored": c.unsynced_ignored,
            # vrai si la secretaire n'a pas fourni de commentaire apres les refus (AUTO_COMMENT)
            "comment_missing": any(_is_auto_comment(l.comment) for l in lines),
            "lines": [dict({"mode": l.mode_code, "source": l.source,
                            "comment_missing": _is_auto_comment(l.comment)},
                           **{f: getattr(l, f) for f in LINE_FIELDS}) for l in lines],
        }

    # --- calcul et ecriture d'une cloture ------------------------------------------------
    def _build(self, start, last, t0, t1, kind, counted: Dict[str, Dict[str, Any]],
               active_codes: List[str]):
        flows = self.repo.flows(t0, t1)
        # Regularisations approuvees pendant la periode : compensees ICI (entree si positive,
        # sortie si negative), au mode de la correction. La cloture d'origine ne bouge jamais ;
        # expected = opening + entries - exits reste la seule formule.
        applied = self.repo.approved_corrections(t0, t1)
        for corr in applied:
            f = flows.setdefault(corr.mode_code, {"entries": ZERO, "exits": ZERO})
            delta = Decimal(corr.amount_delta)
            if delta > 0:
                f["entries"] = f["entries"] + delta
            else:
                f["exits"] = f["exits"] - delta
        opening, from_auto = self._opening(start, last)
        codes = list(active_codes)
        if CASH not in codes:
            codes.insert(0, CASH)
        extras = sorted(m for m, f in flows.items()
                        if m not in codes and m != UNCLASSIFIED and (f["entries"] or f["exits"]))
        codes += extras
        unc = flows.get(UNCLASSIFIED)
        if unc and (unc["entries"] or unc["exits"]):
            codes.append(UNCLASSIFIED)

        rows = []
        for mode in codes:
            f = flows.get(mode, {"entries": ZERO, "exits": ZERO})
            entry = counted.get(mode) if kind == "manual" else None
            cnt = entry["counted"] if entry else None
            calc = compute_line(mode, opening, f["entries"], f["exits"], cnt)
            rows.append({"mode": mode, "source": _source(mode),
                         "opening": opening if mode == CASH else ZERO,
                         "entries": f["entries"], "exits": f["exits"],
                         "expected": calc["expected"], "counted": cnt,
                         "difference": calc["difference"],
                         "comment": entry["comment"] if entry else None})
        comment_missing = False
        gaps = [r for r in rows if r["difference"] not in (None, ZERO)
                and not (r["comment"] or "").strip()]
        if gaps:
            if self.repo.count_gap_refusals(_iso_utc(t0)) < MAX_GAP_REFUSALS:
                # le message nomme le premier mode, jamais un montant
                raise GapCommentRequired(
                    f"Commentaire obligatoire pour l'ecart du mode {gaps[0]['mode']}",
                    period_start=_iso_utc(t0))
            for r in gaps:  # sondage plafonne : on accepte, sans commentaire, en anomalie
                r["comment"] = AUTO_COMMENT
            comment_missing = True
        require_comment_if_gap(rows)

        cash = next(r for r in rows if r["mode"] == CASH)
        closure = CashClosure(
            period_start=t0, period_end=t1,
            # manuel : date locale de now ; auto : t1 = 23:00 local du jour concerne
            business_date=t1.astimezone(TZ).date(),
            kind=kind, closed_by=(self.user.user_id if kind == "manual" else None),
            # CHECK opening_cash >= 0 : un attendu negatif reporte d'une cloture auto est garde
            # tel quel sur la ligne especes, la colonne de synthese est bornee a 0.
            opening_cash=max(opening, ZERO), expected_cash=cash["expected"],
            counted_cash=cash["counted"], difference=cash["difference"],
            opening_from_auto=from_auto,
        )
        lines = [CashClosureLine(mode_code=r["mode"], source=r["source"], opening=r["opening"],
                                 entries=r["entries"], exits=r["exits"], expected=r["expected"],
                                 counted=r["counted"], difference=r["difference"],
                                 comment=r["comment"]) for r in rows]
        self.repo.insert_closure(closure, lines)
        extra = set(extras) | {UNCLASSIFIED}  # argent d'origine inconnue ou de mode inactif
        anomaly = (kind == "auto"
                   or any(r["difference"] not in (None, ZERO) for r in rows)
                   or any(r["mode"] in extra and (r["entries"] or r["exits"]) for r in rows))
        payload = {"closure_id": closure.id, "business_date": closure.business_date.isoformat(),
                   "expected_cash": _s(closure.expected_cash),
                   "counted_cash": _s(closure.counted_cash),
                   "difference": _s(closure.difference), "auto": kind == "auto",
                   "anomaly": anomaly or comment_missing}
        if comment_missing:
            payload["comment_missing"] = True
        for uid in self.repo.recipient_user_ids():
            self.notification_repo.create(uid, NOTIF_TYPE, payload)
        self._audit("CashClosure", "CLOSE_MANUAL" if kind == "manual" else "CLOSE_AUTO",
                    closure.id, dict(payload, period_start=t0.isoformat(),
                                     period_end=t1.isoformat()))
        return self._detail(closure, lines, applied)

    def _validate_counts(self, counts, active_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        if not isinstance(counts, list):
            raise ValueError("Comptage invalide.")
        out: Dict[str, Dict[str, Any]] = {}
        for item in counts:
            if not isinstance(item, dict) or not isinstance(item.get("mode"), str):
                raise ValueError("Comptage invalide.")
            mode = item["mode"]
            if mode not in active_codes:
                raise ValueError(f"Mode de paiement inconnu ou inactif : {mode}")
            if mode in out:
                raise ValueError(f"Mode de paiement en double : {mode}")
            comment = _comment(item.get("comment"))
            if comment is not None and comment.lower() == AUTO_COMMENT:
                # texte reserve au remplissage automatique (marqueur comment_missing)
                raise ValueError("Ce commentaire est reserve : decrivez l'ecart avec vos mots.")
            out[mode] = {"counted": _amount(item.get("counted"), f"Montant compte ({mode})"),
                         "comment": comment}
        missing = [m for m in active_codes if m not in out]
        if missing:
            raise ValueError("Comptage manquant pour : " + ", ".join(missing))
        return out

    # --- cas d'usage ----------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        """Etat sans aucun total (comptage a l'aveugle)."""
        start = self.repo.start_row()
        modes = [{"code": m.code, "label": m.label, "source": _source(m.code)}
                 for m in self.repo.active_modes()]
        if start is None:
            return {"configured": False, "last_closed_at": None, "overdue_days": [],
                    "modes": modes}
        last = self.repo.last_closure()
        t0 = last.period_end if last is not None else start.started_at
        return {"configured": True,
                "last_closed_at": last.period_end if last is not None else None,
                "overdue_days": self._due_days(last, t0, self._now()), "modes": modes}

    def set_start(self, opening_cash, started_at: Optional[datetime] = None) -> Dict[str, Any]:
        if "admin" not in (getattr(self.user, "roles", None) or []):
            raise PermissionError("Seul l'administrateur initialise la caisse.")

        def run():
            self._lock()
            if self.repo.start_row() is not None:
                raise CashClosureConflictError("La caisse est deja initialisee.")
            opening = _amount(opening_cash, "Solde d'ouverture")
            at = started_at or self._now()
            if at.tzinfo is None:
                raise ValueError("La date de debut doit avoir un fuseau.")
            row = self.repo.insert_start(at, opening, self.user.user_id)
            out = {"started_at": row.started_at, "opening_cash": row.opening_cash,
                   "set_by": row.set_by}
            self._audit("CashClosureStart", "CREATE", 1,
                        {"started_at": at.isoformat(), "opening_cash": str(opening)})
            return out
        return self._tx(run)

    def submit(self, counts, last_closed_at: Any = _UNSET) -> Dict[str, Any]:
        """last_closed_at (garde double onglet) : la valeur de status()["last_closed_at"] vue
        par l'ecran (ISO avec fuseau, datetime avec fuseau, ou None). Si elle differe de la
        fin de la derniere cloture (comparee en instants) : 409. Omis (appels internes et
        tests de la tache 4) : pas de controle."""
        seen = _UNSET if last_closed_at is _UNSET else _instant(last_closed_at)

        def run():
            self._lock()
            start = self.repo.start_row()
            if start is None:
                raise CashClosureConflictError("Caisse non initialisee.")
            if seen is not _UNSET:
                last = self.repo.last_closure()
                current = last.period_end if last is not None else None
                if (current is None) != (seen is None) or (current is not None and current != seen):
                    raise CashClosureConflictError(
                        "Une autre cloture a ete validee entre-temps. Rechargez l'ecran.")
            active = [m.code for m in self.repo.active_modes()]
            counted = self._validate_counts(counts, active)
            t0, last = self._chain_point(start)
            t1 = self._now()
            if self._due_days(last, t0, t1):
                raise CashClosureConflictError(
                    "Des clotures automatiques sont en retard : elles doivent etre faites d'abord.")
            if t1 <= t0:
                raise CashClosureConflictError("Cette periode vient deja d'etre cloturee.")
            return self._build(start, last, t0, t1, "manual", counted, active)
        try:
            return self._tx(run)
        except GapCommentRequired as e:
            # La transaction du refus est annulee : le refus est journalise dans sa propre
            # transaction, pour qu'il survive et compte dans le plafond de sondage.
            self._tx(lambda: self._audit("CashClosure", GAP_REFUSED_ACTION, None,
                                         {"period_start": e.period_start}))
            raise

    def auto_close_overdue(self, now: datetime) -> List[Dict[str, Any]]:
        """Ferme chaque jour manque a son 23:00, du plus ancien au plus recent. Idempotente."""
        if now.tzinfo is None:
            raise ValueError("now doit avoir un fuseau.")

        def run():
            if not self.repo.try_lock():
                return []  # une autre transaction cloture deja ; elle fera le rattrapage
            start = self.repo.start_row()
            if start is None:
                return []
            active = [m.code for m in self.repo.active_modes()]
            out = []
            t0, last = self._chain_point(start)
            for day in self._due_days(last, t0, now):
                t1 = closing_time_for(day)
                out.append(self._build(start, last, t0, t1, "auto", {}, active))
                t0, last = self._chain_point(start)
            return out
        return self._tx(run)

    def catch_up(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Rattrapage public (route /catchup, script CLI) : auto_close_overdue a l'horloge."""
        return self.auto_close_overdue(now if now is not None else self._now())

    # --- modes de paiement (ecriture : admin ; jamais de suppression, codes stables) ------
    def _require_admin(self, msg: str):
        if "admin" not in (getattr(self.user, "roles", None) or []):
            raise PermissionError(msg)

    def list_modes(self) -> List[Dict[str, Any]]:
        return [_mode_out(m) for m in self.repo.list_modes()]

    # Pas de create_mode : la liste officielle des codes est fixe (regle 6).

    def update_mode(self, code: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_admin("Seul l'administrateur gere les modes de paiement.")
        data = dict(data or {})
        unknown = set(data) - {"label", "is_active", "sort_order"}
        if unknown:
            raise ValueError("Champs non modifiables : " + ", ".join(sorted(unknown)))
        changes: Dict[str, Any] = {}
        if "label" in data:
            changes["label"] = _label(data["label"])
        if "sort_order" in data:
            changes["sort_order"] = _sort_order(data["sort_order"])
        if "is_active" in data:
            if not isinstance(data["is_active"], bool):
                raise ValueError("Etat actif invalide.")
            changes["is_active"] = data["is_active"]

        def run():
            m = self.repo.get_mode(code)
            if m is None:
                raise CashClosureNotFoundError("Mode de paiement introuvable.")
            if code == CASH and changes.get("is_active") is False:
                raise ValueError("Les especes ne peuvent pas etre desactivees.")
            before = _mode_out(m)
            for k, v in changes.items():
                setattr(m, k, v)
            self.session.flush()
            out = _mode_out(m)
            self._audit("PaymentMode", "UPDATE", None, {"code": code, "before": before, "after": out})
            return out
        return self._tx(run)

    # --- corrections (la cloture n'est jamais modifiee) -----------------------------------
    def request_correction(self, closure_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(data or {})
        mode = data.get("mode_code")
        if not isinstance(mode, str) or not mode:
            raise ValueError("Mode de paiement obligatoire.")
        amount = _delta(data.get("amount_delta"))
        reason = _comment(data.get("reason"))
        if not reason:
            raise ValueError("Le motif de la correction est obligatoire.")
        if self.user is None:
            raise PermissionError("Utilisateur requis.")

        def run():
            c = self.repo.get(closure_id)
            if c is None:
                raise CashClosureNotFoundError("Cloture introuvable.")
            if mode not in {l.mode_code for l in self.repo.lines_for([c.id])[c.id]}:
                raise ValueError(f"Ce mode ne figure pas dans la cloture : {mode}")
            corr = self.repo.add_correction(CashClosureCorrection(
                closure_id=c.id, mode_code=mode, amount_delta=amount, reason=reason,
                status="pending", requested_by=self.user.user_id))
            out = _corr_out(corr)
            self._audit("CashClosureCorrection", "REQUEST", corr.id,
                        {"closure_id": c.id, "mode_code": mode, "amount_delta": str(amount),
                         "reason": reason})
            return out
        return self._tx(run)

    def list_corrections(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        status = (filters or {}).get("status")
        if status is not None and status not in CORRECTION_STATUSES:
            raise ValueError("Statut de correction invalide.")
        return [_corr_out(c) for c in self.repo.list_corrections(status)]

    def decide_correction(self, correction_id: int, approve) -> Dict[str, Any]:
        if not isinstance(approve, bool):
            raise ValueError("Decision invalide.")
        if self.user is None:
            raise PermissionError("Utilisateur requis.")

        def run():
            # verrou PARTAGE des ecrivains d'argent : une cloture en cours (verrou exclusif) est
            # attendue, et decided_at est pris APRES, donc >= le t1 de cette cloture.
            locked_at = lock_cash_write(self.session)
            corr = self.repo.get_correction(correction_id, for_update=True)
            if corr is None:
                raise CashClosureNotFoundError("Correction introuvable.")
            if corr.status != "pending":
                raise CashClosureConflictError("Cette correction a deja ete traitee.")
            corr.status = "approved" if approve else "rejected"
            corr.decided_by = self.user.user_id
            corr.decided_at = self._now() if self.clock is not None else locked_at
            self.session.flush()
            out = _corr_out(corr)
            self._audit("CashClosureCorrection", "APPROVE" if approve else "REJECT", corr.id,
                        {"closure_id": corr.closure_id, "status": corr.status})
            return out
        return self._tx(run)

    def get(self, closure_id: int) -> Dict[str, Any]:
        c = self.repo.get(closure_id)
        if c is None:
            raise CashClosureNotFoundError("Cloture introuvable.")
        return self._detail(c, self.repo.lines_for([c.id])[c.id])

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        f = dict(filters or {})
        date_from, date_to, kind = f.get("date_from"), f.get("date_to"), f.get("kind")
        for v, label in ((date_from, "date_from"), (date_to, "date_to")):
            if v is not None and not isinstance(v, date):
                raise ValueError(f"{label} invalide.")
        if date_from and date_to and date_from > date_to:
            raise ValueError("La date de debut doit preceder la date de fin.")
        if kind is not None and kind not in ("manual", "auto"):
            raise ValueError("Type de cloture invalide.")
        limit = int(f.get("limit") or 50)
        offset = int(f.get("offset") or 0)
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError("Pagination invalide.")
        rows = self.repo.list_closures(date_from=date_from, date_to=date_to, kind=kind,
                                       limit=limit, offset=offset)
        lines = self.repo.lines_for([c.id for c in rows])
        return [self._detail(c, lines[c.id]) for c in rows]


def get_cash_closure_controller(db, current_user, clock=None) -> CashClosureController:
    """Fabrique : les TROIS depots sont reellement injectes (notifications comprises).
    Le routeur (tache 5) l'appelle avec sa session et l'utilisateur courant ; clock None =
    horloge reelle (les tests l'injectent)."""
    return CashClosureController(CashClosureRepository(db), AuditRepository(db),
                                 NotificationRepository(db), current_user, clock=clock)
