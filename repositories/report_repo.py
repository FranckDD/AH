# repositories/report_repo.py
"""Rapports / controle quotidien : requetes de lecture non couvertes par les modules existants.
Lecture seule, ne commit jamais.

Conventions de colonnes (verifiees dans les modeles et ci/schema_only.sql) :
- paiement_echelonne.received_at, caisse_retrait.received_at : timestamptz -> bornes UTC aware.
- caisse.paid_at : heure locale de Douala naive (utils/business_time.py) -> bornes locales naives.
- discount_requests.decided_at : UTC naif (datetime.utcnow) -> bornes UTC naives.
- patients.created_at, medical_records.consultation_date : naifs remplis par now() /
  LOCALTIMESTAMP, donc a l'heure du fuseau de la session Postgres ; convertis en heure de
  Douala par AT TIME ZONE current_setting('TimeZone') puis AT TIME ZONE 'Africa/Douala'.
- consultation_spirituel.consultation_date : UTC naif (datetime.utcnow) -> converti en Douala.
- Ventes comptees : caisse.status = 'active' seulement.
"""
import unicodedata
from datetime import datetime
from typing import List

from sqlalchemy import bindparam, func, text

from models.stock_count import StockCountLine
from models.stock_reception import StockAdjustmentRequest

DLA = "Africa/Douala"

_RETRAITS_SQL = text("""
    SELECT r.payment_method AS mode, r.category AS category, r.amount AS amount
    FROM caisse_retrait r
    WHERE r.status = 'active' AND r.received_at >= :t0 AND r.received_at < :t1
""")

_STAFF_DISCOUNTS_SQL = text("""
    SELECT COUNT(*) AS n, COALESCE(SUM(c.staff_discount_amount), 0) AS total
    FROM caisse c
    WHERE c.status = 'active' AND c.staff_discount_amount > 0
      AND c.paid_at >= :lo AND c.paid_at < :hi
""")

_MANUAL_DISCOUNTS_SQL = text("""
    SELECT dr.id, dr.original_amount, dr.decision_percent
    FROM discount_requests dr
    JOIN caisse c ON c.transaction_id = dr.transaction_id
    WHERE dr.status = 'approved' AND dr.decision_percent > 0
      AND c.status = 'active'
      AND dr.decided_at >= :lo AND dr.decided_at < :hi
""")

# Meme filtre que CashClosureRepository._PAYMENTS_SQL (ventes pending_approval exclues) ;
# handled_by = le compte qui a recu l'argent (pose depuis current_user a chaque paiement).
_PAYMENTS_BY_USER_SQL = text(f"""
    SELECT pe.handled_by AS user_id, u.username, u.full_name,
           (pe.received_at AT TIME ZONE '{DLA}')::date AS day,
           SUM(pe.paid_amount) AS total,
           SUM(CASE WHEN c.status = 'cancelled' OR c.cancelled_at IS NOT NULL
                    THEN pe.paid_amount ELSE 0 END) AS cancelled_total
    FROM paiement_echelonne pe
    JOIN caisse c ON c.transaction_id = pe.transaction_id
    LEFT JOIN users u ON u.user_id = pe.handled_by
    WHERE pe.received_at >= :t0 AND pe.received_at < :t1
      AND c.status <> 'pending_approval'
    GROUP BY pe.handled_by, u.username, u.full_name, day
""")

_SERVER_LOCAL = "(({col} AT TIME ZONE current_setting('TimeZone')) AT TIME ZONE '" + DLA + "')"
_UTC_NAIVE = "(({col} AT TIME ZONE 'UTC') AT TIME ZONE '" + DLA + "')"


def _weekly(local_expr: str, table: str, where: str, value: str) -> text:
    return text(f"""
        SELECT date_trunc('week', {local_expr})::date AS week, {value} AS v
        FROM {table}
        WHERE {where} AND {local_expr} >= :lo AND {local_expr} < :hi
        GROUP BY week
    """)


_WEEKLY_SALES_SQL = _weekly("c.paid_at", "caisse c", "c.status = 'active'", "SUM(c.amount)")
_WEEKLY_PATIENTS_SQL = _weekly(_SERVER_LOCAL.format(col="p.created_at"), "patients p",
                               "COALESCE(p.is_deleted, false) = false", "COUNT(*)")
_WEEKLY_MEDICAL_SQL = _weekly(_SERVER_LOCAL.format(col="m.consultation_date"),
                              "medical_records m", "TRUE", "COUNT(*)")
_WEEKLY_SPIRITUAL_SQL = _weekly(_UTC_NAIVE.format(col="s.consultation_date"),
                                "consultation_spirituel s", "TRUE", "COUNT(*)")


class ReportRepository:
    def __init__(self, session):
        self.session = session

    def _rows(self, sql, **params) -> List:
        return list(self.session.execute(sql, params))

    def active_retraits(self, t0: datetime, t1: datetime) -> List:
        """Retraits actifs recus dans [t0, t1) (bornes aware)."""
        return self._rows(_RETRAITS_SQL, t0=t0, t1=t1)

    def staff_discounts(self, lo_local: datetime, hi_local: datetime):
        """(nombre, somme) des reductions personnel des ventes actives, paid_at local."""
        return self.session.execute(_STAFF_DISCOUNTS_SQL, {"lo": lo_local, "hi": hi_local}).one()

    def manual_discounts(self, lo_utc: datetime, hi_utc: datetime) -> List:
        """Demandes de remise approuvees (pourcentage) dont decided_at (UTC naif) est dans la
        periode, sur des ventes encore actives."""
        return self._rows(_MANUAL_DISCOUNTS_SQL, lo=lo_utc, hi=hi_utc)

    def payments_by_user_day(self, t0: datetime, t1: datetime) -> List:
        return self._rows(_PAYMENTS_BY_USER_SQL, t0=t0, t1=t1)

    def weekly_sales(self, lo_local, hi_local) -> List:
        return self._rows(_WEEKLY_SALES_SQL, lo=lo_local, hi=hi_local)

    def weekly_new_patients(self, lo_local, hi_local) -> List:
        return self._rows(_WEEKLY_PATIENTS_SQL, lo=lo_local, hi=hi_local)

    def weekly_medical_consultations(self, lo_local, hi_local) -> List:
        return self._rows(_WEEKLY_MEDICAL_SQL, lo=lo_local, hi=hi_local)

    def weekly_spiritual_consultations(self, lo_local, hi_local) -> List:
        return self._rows(_WEEKLY_SPIRITUAL_SQL, lo=lo_local, hi=hi_local)

    # ---------- tache 4 : produits, stock, tableau vendu par produit ----------
    def _int(self, sql, **params) -> int:
        return int(self.session.execute(sql, params).scalar() or 0)

    def sold_stock_qty(self, lo_local: datetime, hi_local: datetime) -> int:
        return self._int(_SOLD_STOCK_SQL, lo=lo_local, hi=hi_local)

    def received_receipts_qty(self, lo_utc: datetime, hi_utc: datetime) -> int:
        return self._int(_RECEIVED_RECEIPTS_SQL, lo=lo_utc, hi=hi_utc)

    def received_reappro_qty(self, lo_utc: datetime, hi_utc: datetime) -> int:
        return self._int(_RECEIVED_REAPPRO_SQL, lo=lo_utc, hi=hi_utc)

    def system_stock(self) -> int:
        return self._int(text("SELECT COALESCE(SUM(quantity), 0) FROM pharmacy"))

    def low_stock(self, limit: int) -> List:
        return self._rows(_LOW_STOCK_SQL, lim=limit)

    def low_stock_count(self) -> int:
        return self._int(_LOW_STOCK_COUNT_SQL)

    def pending_count_requests(self):
        """(nombre, plus ancien requested_at UTC naif) des demandes en_attente nees d'un comptage
        (stock_count_lines.adjustment_request_id)."""
        n, oldest = (self.session.query(func.count(func.distinct(StockAdjustmentRequest.id)),
                                        func.min(StockAdjustmentRequest.requested_at))
                     .join(StockCountLine,
                           StockCountLine.adjustment_request_id == StockAdjustmentRequest.id)
                     .filter(StockAdjustmentRequest.status == "en_attente")).one()
        return int(n or 0), oldest

    def sold_by_product(self, lo_local, hi_local, item_type: str, q, category, sort: str,
                        limit: int, offset: int):
        """(lignes de la page, nombre de groupes avant pagination)."""
        base = _sold_groups_sql(item_type, q is not None, category is not None)
        params = {"lo": lo_local, "hi": hi_local, "cats": list(ITEM_TYPES[item_type])}
        if q is not None:
            esc = fold_text(q).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params["pat"] = f"%{esc}%"
        if category is not None:
            params["cat"] = category
        cats = bindparam("cats", expanding=True)
        total = self._int(text(f"SELECT COUNT(*) FROM ({base}) g").bindparams(cats), **params)
        page = text(f"{base} ORDER BY {SORTS[sort]} LIMIT :lim OFFSET :off").bindparams(cats)
        return self._rows(page, lim=limit, off=offset, **params), total


# ================= tache 4 : requetes produits =================
def _fold_pairs():
    """Lettres minuscules accentuees -> lettre ASCII de base, pour translate() cote SQL ; meme
    pliage que fold_text cote Python (NFKD sans diacritiques, minuscules)."""
    src, dst = [], []
    for cp in range(0xC0, 0x250):
        ch = chr(cp)
        if ch != ch.lower():
            continue
        base = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
        if len(base) == 1 and base != ch and base.isascii():
            src.append(ch)
            dst.append(base)
    return "".join(src), "".join(dst)


_FOLD_SRC, _FOLD_DST = _fold_pairs()


def fold_text(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    for lig, rep in _LIGATURES:
        s = s.replace(lig, rep)
    return s


# Ligatures (minuscules, apres lower()) developpees avant translate(), des deux cotes.
_LIGATURES = (("œ", "oe"), ("æ", "ae"))


def _sql_fold(expr: str) -> str:
    inner = f"lower({expr})"
    for lig, rep in _LIGATURES:
        inner = f"replace({inner}, '{lig}', '{rep}')"
    return f"translate({inner}, '{_FOLD_SRC}', '{_FOLD_DST}')"


# Meme classement que utils.staff_discount.normalize_item_category (meme ordre des tests) ;
# 'medicament' et 'carnet' = utils.item_types.touches_stock.
_CATEGORY_SQL = (
    "CASE WHEN {f} LIKE '%consult%' THEN 'consultation' "
    "WHEN {f} LIKE '%medic%' THEN 'medicament' "
    "WHEN {f} LIKE '%carnet%' OR {f} LIKE '%booklet%' THEN 'carnet' "
    "WHEN {f} LIKE '%exam%' THEN 'examen' ELSE 'autre_soin' END"
).format(f=_sql_fold("ci.item_type"))

_SOLD_STOCK_SQL = text(f"""
    SELECT COALESCE(SUM(ci.quantity), 0)
    FROM caisse_item ci JOIN caisse c ON c.transaction_id = ci.transaction_id
    WHERE c.status = 'active' AND c.paid_at >= :lo AND c.paid_at < :hi
      AND ({_CATEGORY_SQL}) IN ('medicament', 'carnet')
""")

# Recu = ce que StockController.validate_receipt ajoute au stock (qty_good des receptions
# 'valide', controlled_at UTC naif) ; les lots de production passent par une reception et ne
# sont donc pas comptes a part.
_RECEIVED_RECEIPTS_SQL = text("""
    SELECT COALESCE(SUM(l.qty_good), 0)
    FROM stock_receipt_lines l JOIN stock_receipts r ON r.id = l.receipt_id
    WHERE r.status = 'valide' AND r.controlled_at >= :lo AND r.controlled_at < :hi
""")

_RECEIVED_REAPPRO_SQL = text("""
    SELECT COALESCE(SUM(a.quantity), 0) FROM stock_adjustment_requests a
    WHERE a.kind = 'reapprovisionnement' AND a.status = 'approuve'
      AND a.decided_at >= :lo AND a.decided_at < :hi
""")

# Regle du badge BAS de l'ecran Stock (StockList.vue : prod.quantity <= prod.minThreshold, avec
# minThreshold = pharmacy.threshold), qui est aussi celle de Pharmacy.update_stock_status.
_LOW_STOCK_WHERE = "quantity <= threshold"
_LOW_STOCK_SQL = text(f"""
    SELECT medication_id AS product_id, drug_name AS name, medication_type AS category,
           quantity, threshold
    FROM pharmacy WHERE {_LOW_STOCK_WHERE}
    ORDER BY drug_name, medication_id
    LIMIT :lim
""")
_LOW_STOCK_COUNT_SQL = text(f"SELECT COUNT(*) FROM pharmacy WHERE {_LOW_STOCK_WHERE}")

ITEM_TYPES = {"Medicament": ("medicament", "carnet"), "Examen": ("examen",),
              "Consultation": ("consultation",), "Service": ("autre_soin",)}
SORTS = {
    "amount_desc": "amount DESC, name ASC, gkey ASC",
    "amount_asc": "amount ASC, name ASC, gkey ASC",
    "quantity_desc": "quantity DESC, name ASC, gkey ASC",
    "quantity_asc": "quantity ASC, name ASC, gkey ASC",
    "name_asc": "name ASC, gkey ASC",
}


# Nom affiche pour une ligne dont la reference est absente ou supprimee : jamais le libelle
# generique du type de ligne.
NO_PRODUCT_LABEL = "(sans produit)"


def _ref_name(name_col: str, id_col: str) -> str:
    return (f"CASE WHEN ci.item_ref_id IS NULL THEN '{NO_PRODUCT_LABEL}' "
            f"WHEN {id_col} IS NULL THEN '(produit supprime #' || ci.item_ref_id || ')' "
            f"ELSE {name_col} END")


def _sold_groups_sql(item_type: str, with_q: bool, with_cat: bool) -> str:
    """Groupes du tableau : par produit (pharmacy) pour Medicament, par examen pour Examen, par
    libelle de type de ligne pour Consultation et Service. Ventes actives, paid_at local."""
    if item_type == "Medicament":
        sel = ("ci.item_ref_id AS gkey, p.medication_id AS product_id, "
               f"{_ref_name('p.drug_name', 'p.medication_id')} AS name, p.medication_type AS category")
        join = "LEFT JOIN pharmacy p ON p.medication_id = ci.item_ref_id"
    elif item_type == "Examen":
        sel = ("ci.item_ref_id AS gkey, e.id AS product_id, "
               f"{_ref_name('e.nom', 'e.id')} AS name, e.categorie AS category")
        join = "LEFT JOIN examens e ON e.id = ci.item_ref_id"
    else:
        sel = ("NULL::int AS gkey, NULL::int AS product_id, ci.item_type AS name, "
               "NULL::text AS category")
        join = ""
    key = "name" if item_type in ("Consultation", "Service") else "gkey"
    where = []
    if with_q:
        where.append(f"{_sql_fold('name')} LIKE :pat ESCAPE '\\'")
    if with_cat:
        where.append("category = :cat")
    return f"""
        WITH lines AS (
            SELECT {sel}, ci.quantity, ci.line_total
            FROM caisse_item ci JOIN caisse c ON c.transaction_id = ci.transaction_id {join}
            WHERE c.status = 'active' AND c.paid_at >= :lo AND c.paid_at < :hi
              AND ({_CATEGORY_SQL}) IN :cats
        ),
        groups AS (
            SELECT MIN(gkey) AS gkey, MIN(product_id) AS product_id, MIN(name) AS name,
                   MIN(category) AS category, SUM(quantity) AS quantity, SUM(line_total) AS amount
            FROM lines GROUP BY {key}
        )
        SELECT * FROM groups {('WHERE ' + ' AND '.join(where)) if where else ''}
    """


# ================= tache 5 : controle quotidien =================
# Cle du verrou consultatif du controle quotidien (differente de CASH_CLOSURE_LOCK_KEY).
DAILY_CONTROL_LOCK_KEY = 2026102505

_SETTINGS_UPSERT_SQL = text("""
    INSERT INTO report_settings (id, cancelled_sales_threshold, adjustment_pending_days,
                                 updated_by, updated_at)
    VALUES (1, :c, :d, :u, :at)
    ON CONFLICT (id) DO UPDATE SET cancelled_sales_threshold = EXCLUDED.cancelled_sales_threshold,
        adjustment_pending_days = EXCLUDED.adjustment_pending_days,
        updated_by = EXCLUDED.updated_by, updated_at = EXCLUDED.updated_at
""")


class DailyControlRepository:
    """Instantanes du controle quotidien, reglages et sources propres au controle. Ne commit
    jamais."""

    def __init__(self, session):
        self.session = session

    # --- verrou (de SESSION : le controle commite chaque jour separement) ---
    # RESERVE AU SCRIPT DU SOIR (scripts/daily_control.py, une session par execution). Un verrou
    # de session survit au commit et reste sur la connexion : expose par l'API (pool de
    # connexions partagees), il faudrait une connexion dediee, sinon il fuirait vers une autre
    # requete si la liberation echouait.
    def try_lock(self) -> bool:
        return bool(self.session.execute(text("SELECT pg_try_advisory_lock(:k)"),
                                         {"k": DAILY_CONTROL_LOCK_KEY}).scalar())

    def unlock(self) -> None:
        self.session.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": DAILY_CONTROL_LOCK_KEY})

    # --- instantanes ---
    def _q(self):
        from models.report import DailyControl
        return self.session.query(DailyControl), DailyControl

    def control_for(self, day):
        q, M = self._q()
        return q.filter(M.business_date == day).one_or_none()

    def previous_control(self, day):
        q, M = self._q()
        return q.filter(M.business_date < day).order_by(M.business_date.desc()).first()

    def pending_notifications(self) -> List:
        q, M = self._q()
        return (q.filter(M.notify_reason.isnot(None), M.notified_at.is_(None))
                .order_by(M.business_date).all())

    def latest_control(self):
        q, M = self._q()
        return q.order_by(M.business_date.desc()).first()

    def controls_upto(self, day) -> List:
        q, M = self._q()
        return q.filter(M.business_date <= day).order_by(M.business_date).all()

    def last_notice_before(self, day):
        """Dernier envoi (notification ou rappel, UTC naif) des instantanes anterieurs a day."""
        _, M = self._q()
        return (self.session.query(func.max(func.greatest(M.notified_at, M.reminder_sent_at)))
                .filter(M.business_date < day).scalar())

    # --- reglages ---
    def settings_row(self):
        from models.report import ReportSettings
        return self.session.get(ReportSettings, 1, populate_existing=True)

    def upsert_settings(self, cancelled: int, days: int, user_id, at: datetime) -> None:
        self.session.execute(_SETTINGS_UPSERT_SQL, {"c": cancelled, "d": days, "u": user_id, "at": at})
        self.session.flush()

    # --- sources ---
    def price_mismatch_sales(self, t0: datetime, t1: datetime) -> List:
        """(vente, premier instant) des audits PRICE_MISMATCH dans [t0, t1) (timestamptz)."""
        return self._rows(text("""
            SELECT resource_id AS sale_id, MIN(timestamp) AS at, COUNT(*) AS n
            FROM audit_user_actions
            WHERE action_performed = 'PRICE_MISMATCH' AND resource_id IS NOT NULL
              AND timestamp >= :t0 AND timestamp < :t1
            GROUP BY resource_id ORDER BY resource_id
        """), t0=t0, t1=t1)

    def other_outputs(self, lo_utc: datetime, hi_utc: datetime) -> List:
        """Sorties actives au motif 'autre' declarees dans [lo, hi) (UTC naif)."""
        return self._rows(text("""
            SELECT o.id, o.batch_id, b.batch_number, o.quantity, o.note, o.declared_at
            FROM fab_batch_outputs o JOIN fab_batches b ON b.id = o.batch_id
            WHERE o.reason = 'autre' AND o.status = 'active'
              AND o.declared_at >= :lo AND o.declared_at < :hi
            ORDER BY o.id
        """), lo=lo_utc, hi=hi_utc)

    def pending_adjustments_before(self, limit_utc: datetime) -> List:
        """Demandes d'ajustement en_attente demandees STRICTEMENT avant limit (UTC naif)."""
        return (self.session.query(StockAdjustmentRequest)
                .filter(StockAdjustmentRequest.status == "en_attente",
                        StockAdjustmentRequest.requested_at < limit_utc)
                .order_by(StockAdjustmentRequest.id).all())

    def _rows(self, sql, **params) -> List:
        return list(self.session.execute(sql, params))
