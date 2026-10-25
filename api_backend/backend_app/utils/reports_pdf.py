"""Export PDF des Rapports (tache 8) : transforme les dictionnaires du ReportsController en
contexte de gabarit (reports_export_template.html), en francais seulement.

Chaque carte devient un bloc generique {title, meta, state, kv, tables, notes} : le gabarit ne
fait que boucler, aucune logique metier. Montants : chaines Decimal formatees sans flottant
(groupes separes par une espace fine insecable, 2 decimales, virgule). Les chaines venant de la
base sont echappees dans le gabarit (|e) : render_pdf_from_template n'active pas l'autoescape.
"""
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from utils.business_time import BUSINESS_TZ

TEMPLATE = "reports_export_template.html"
MAX_ROWS = 500
THIN = " "

# Toutes les cles 'reports.*' que le controleur peut emettre (verifie par un test).
LABELS: Dict[str, str] = {
    "reports.cards.collected": "Encaissé sur la période",
    "reports.cards.cash_gaps": "Écarts de caisse",
    "reports.cards.withdrawals_and_cancellations": "Retraits et ventes annulées",
    "reports.cards.discounts": "Réductions accordées",
    "reports.cards.per_secretary": "Encaissé par secrétaire",
    "reports.cards.sold_vs_received": "Produits vendus contre reçus",
    "reports.cards.stock_count": "Comptage du stock",
    "reports.cards.low_stock": "Ruptures et seuils bas",
    "reports.cards.batches": "État des lots",
    "reports.cards.bottles": "Bouteilles produites, sorties et expédiées",
    "reports.cards.loss_and_cost": "Manque et coût de revient",
    "reports.cards.new_patients": "Nouveaux patients",
    "reports.cards.consultations": "Consultations",
    "reports.cards.sales": "Ventes sur 3 mois",
    "reports.basis.decision_date": "date de la décision",
    "reports.basis.payment_date": "date du paiement",
    "reports.formula.sold_vs_received": "Vendus = quantités des ventes actives ; reçus = réceptions "
                                        "validées plus réapprovisionnements approuvés.",
    "reports.rules.low_stock_quantity_lte_threshold": "Règle : quantité inférieure ou égale au seuil "
                                                      "(badge BAS de l'écran Stock).",
    "reports.table.amount_before_discount": "Montants des lignes avant les remises de la vente "
                                            "(réduction personnel, remise approuvée)",
    "reports.table.note_differs_from_cash": "Peut différer des chiffres encaissés du bloc Argent.",
}

MODES = {"especes": "Espèces", "orange_money": "Orange Money", "mtn_money": "MTN Mobile Money",
         "autre_mobile": "Autre mobile", "non_classe": "Non classé"}
STATUS = {"jamais_compte": "Jamais compté", "en_retard": "En retard", "a_jour": "À jour",
          "en_production": "En production", "termine": "Terminé", "expedie": "Expédié",
          "brouillon": "Brouillon", "annule": "Annulé"}
KINDS = {"auto": "automatique", "manual": "manuelle"}
BLOCKS = (("money", "Argent", ("collected", "cash_gaps", "withdrawals_and_cancellations",
                               "discounts", "per_secretary")),
          ("products", "Produits", ("sold_vs_received", "stock_count", "low_stock")),
          ("production", "Production", ("batches", "bottles", "loss_and_cost")),
          ("growth", "Croissance", ("new_patients", "consultations", "sales")))


# --- formats ----------------------------------------------------------------------------
def fmt_money(v: Any) -> str:
    """'1234567.5' -> '1 234 567,50' (espaces fines) ; None -> '-'. Jamais de float."""
    if v is None or v == "":
        return "-"
    try:
        d = Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return str(v)
    s = f"{d:f}"
    sign = "-" if s.startswith("-") else ""
    whole, frac = s.lstrip("-").split(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    out = THIN.join(groups) + "," + frac
    return "-" + out if sign and Decimal(d) != 0 else out


def fmt_int(v: Any) -> str:
    if v is None:
        return "-"
    s = str(int(v))
    sign = "-" if s.startswith("-") else ""
    s = s.lstrip("-")
    groups = []
    while len(s) > 3:
        groups.insert(0, s[-3:])
        s = s[:-3]
    groups.insert(0, s)
    return sign + THIN.join(groups)


def fmt_date(v: Any) -> str:
    """Date locale AAAA-MM-JJ -> JJ/MM/AAAA, sans conversion de fuseau."""
    if not v:
        return "-"
    if isinstance(v, (date, datetime)):
        return v.strftime("%d/%m/%Y")
    s = str(v)[:10]
    try:
        return date.fromisoformat(s).strftime("%d/%m/%Y")
    except ValueError:
        return str(v)


def fmt_instant(v: Any) -> str:
    """Instant ISO (UTC ou avec decalage) -> 'JJ/MM/AAAA HH:MM' heure de Douala."""
    if not v:
        return "-"
    try:
        dt = v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
    except ValueError:
        return str(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BUSINESS_TZ).strftime("%d/%m/%Y %H:%M")


def label(key: Optional[str]) -> str:
    return LABELS.get(key or "", key or "")


def _mode(m):
    return MODES.get(m, m or "-")


def _status(s):
    return STATUS.get(s, (s or "-").replace("_", " "))


def _period_text(p: Optional[Dict[str, str]]) -> str:
    if not p:
        return "-"
    if p.get("from") == p.get("to"):
        return f"le {fmt_date(p.get('from'))}"
    return f"du {fmt_date(p.get('from'))} au {fmt_date(p.get('to'))}"


def _table(caption, headers, rows, numeric=(), empty="Aucune ligne."):
    return {"caption": caption, "headers": headers, "rows": rows, "numeric": set(numeric),
            "empty": empty}


# --- cartes -----------------------------------------------------------------------------
def _card_money(cid, c):
    kv, tables, notes = [], [], []
    if cid == "collected":
        kv.append(("Total encaissé", fmt_money(c.get("total"))))
        tables.append(_table("Par mode de paiement", ["Mode", "Montant"],
                             [[_mode(m), fmt_money(v)] for m, v in (c.get("by_mode") or {}).items()],
                             numeric=(1,)))
        notes.append("Compte les entrées des clôtures de caisse, y compris les paiements de ventes "
                     "annulées ensuite et les retraits rendus.")
    elif cid == "cash_gaps":
        kv.append(("Total des écarts (valeur absolue, tous modes)", fmt_money(c.get("total_abs_gap"))))
        tables.append(_table("Clôtures de la période",
                             ["Date", "Clôture", "Espèces comptées", "Espèces attendues", "Écart",
                              "Commentaire"],
                             [[fmt_date(d.get("business_date")), KINDS.get(d.get("kind"), d.get("kind")),
                               fmt_money(d.get("counted_cash")), fmt_money(d.get("expected_cash")),
                               fmt_money(d.get("difference")),
                               "manquant" if d.get("comment_missing") else "-"]
                              for d in c.get("days") or []],
                             numeric=(2, 3, 4), empty="Aucune clôture sur la période."))
    elif cid == "withdrawals_and_cancellations":
        w = c.get("withdrawals") or {}
        s = c.get("cancelled_sales") or {}
        kv += [("Retraits (nombre)", fmt_int(w.get("count"))),
               ("Retraits (montant)", fmt_money(w.get("total"))),
               ("Ventes annulées (nombre)", fmt_int(s.get("count"))),
               ("Montant des factures annulées", fmt_money(s.get("invoice_total"))),
               ("Montant rendu", fmt_money(s.get("amount_returned")))]
        tables.append(_table("Retraits par mode", ["Mode", "Montant"],
                             [[_mode(m), fmt_money(v)] for m, v in (w.get("by_mode") or {}).items()],
                             numeric=(1,)))
        reasons = [["Motif non précisé" if k == "non_precise" else k, fmt_money(v)]
                   for k, v in (w.get("by_reason") or {}).items()]
        tables.append(_table("Retraits par motif", ["Motif", "Montant"], reasons, numeric=(1,),
                             empty="Aucun retrait."))
        tables.append(_table("Dernières ventes annulées", ["Vente", "Annulée le", "Par",
                                                           "Facture", "Rendu", "Justification"],
                             [[f"n. {x.get('transaction_id')}", fmt_instant(x.get("cancelled_at")),
                               x.get("cancelled_by_name") or "-", fmt_money(x.get("invoice_amount")),
                               fmt_money(x.get("amount")), x.get("justification") or "-"]
                              for x in s.get("recent") or []],
                             numeric=(3, 4), empty="Aucune vente annulée."))
    elif cid == "discounts":
        m = c.get("manual") or {}
        st = c.get("staff") or {}
        kv += [("Remises manuelles approuvées", f"{fmt_int(m.get('count'))} pour {fmt_money(m.get('amount'))}"),
               ("Compté selon", label(m.get("basis"))),
               ("Réductions du personnel", f"{fmt_int(st.get('count'))} pour {fmt_money(st.get('amount'))}"),
               ("Compté selon", label(st.get("basis")))]
    elif cid == "per_secretary":
        tables.append(_table("Paiements reçus par compte",
                             ["Compte", "Encaissé", "Dont annulé ensuite", "Jours travaillés",
                              "Par jour travaillé"],
                             [[r.get("full_name") or r.get("username") or f"#{r.get('user_id')}",
                               fmt_money(r.get("collected")), fmt_money(r.get("of_which_cancelled_later")),
                               fmt_int(r.get("worked_days")), fmt_money(r.get("per_worked_day"))]
                              for r in c.get("rows") or []],
                             numeric=(1, 2, 3, 4), empty="Aucun paiement sur la période."))
    return kv, tables, notes


def _card_products(cid, c):
    kv, tables, notes = [], [], []
    if cid == "sold_vs_received":
        det = c.get("received_detail") or {}
        kv += [("Vendus", fmt_int(c.get("sold"))), ("Reçus", fmt_int(c.get("received"))),
               ("Dont réceptions", fmt_int(det.get("receipts"))),
               ("Dont réapprovisionnements", fmt_int(det.get("reapprovisionnement"))),
               ("Stock du système (état actuel)", fmt_int(c.get("system_stock")))]
        notes.append(label(c.get("formula_key")))
    elif cid == "stock_count":
        pr = c.get("pending_requests") or {}
        kv.append(("Fréquence", f"un comptage tous les {fmt_int(c.get('interval_days'))} jour(s)"))
        for k, v in (c.get("counts") or {}).items():
            kv.append((_status(k), fmt_int(v)))
        oldest = pr.get("oldest_days")
        kv.append(("Demandes d'ajustement en attente",
                   fmt_int(pr.get("count")) + ("" if oldest is None else f" (la plus ancienne depuis {oldest} jour(s))")))
        tables.append(_table(f"Produits à compter ({fmt_int(c.get('products_total'))} au total)",
                             ["Produit", "État", "Jours depuis le dernier comptage"],
                             [[p.get("name") or f"#{p.get('product_id')}", _status(p.get("status")),
                               "-" if p.get("days_since") is None else fmt_int(p.get("days_since"))]
                              for p in c.get("products") or []],
                             numeric=(2,), empty="Aucun produit en retard."))
    elif cid == "low_stock":
        kv.append(("Produits sous le seuil", fmt_int(c.get("total"))))
        tables.append(_table("Produits", ["Produit", "Catégorie", "Quantité", "Seuil"],
                             [[p.get("name") or "-", p.get("category") or "-",
                               fmt_int(p.get("quantity")), fmt_int(p.get("threshold"))]
                              for p in c.get("products") or []],
                             numeric=(2, 3), empty="Aucun produit sous le seuil."))
        notes.append(label(c.get("rule_key")))
    return kv, tables, notes


def _card_production(cid, c):
    kv, tables, notes = [], [], []
    if cid == "batches":
        for k, v in (c.get("counts_by_status") or {}).items():
            kv.append((f"Lots {_status(k).lower()}", fmt_int(v)))
        kv.append((f"Lots trop longs (plus de {c.get('stale_days')} jours)", fmt_int(c.get("stale_total"))))
        tables.append(_table("Lots trop longs", ["Lot", "État", "Jours"],
                             [[x.get("batch_number") or "-", _status(x.get("status")), fmt_int(x.get("days"))]
                              for x in c.get("stale") or []],
                             numeric=(2,), empty="Aucun lot trop long."))
    elif cid == "bottles":
        o = c.get("outputs") or {}
        kv += [("Bouteilles bonnes produites", fmt_int(c.get("produced"))),
               ("Sorties échantillon", fmt_int(o.get("echantillon"))),
               ("Sorties autre", fmt_int(o.get("autre"))),
               ("Expédiées", fmt_int(c.get("shipped")))]
    elif cid == "loss_and_cost":
        oot = c.get("out_of_tolerance") or {}
        kv.append(("Coût moyen par bouteille bonne (lots expédiés sur la période)",
                   fmt_money(c.get("period_average_unit_cost"))))
        kv.append(("Lots hors tolérance", fmt_int(oot.get("total"))))
        cap = "Lots hors tolérance"
        if oot.get("current_state"):
            cap += f" (état actuel au {fmt_instant(oot.get('as_of'))})"
        tables.append(_table(cap, ["Lot", "État", "Manquant", "Manquant (%)", "Tolérance (%)"],
                             [[x.get("batch_number") or "-", _status(x.get("status")),
                               fmt_int(x.get("missing_qty")), fmt_money(x.get("missing_pct")),
                               fmt_money(x.get("tolerance_applied"))] for x in oot.get("items") or []],
                             numeric=(2, 3, 4), empty="Aucun lot hors tolérance."))
        tables.append(_table("Coût par bouteille bonne", ["Produit", "Dernier", "Moyen", "Lots"],
                             [[x.get("product_name") or f"#{x.get('product_id')}",
                               fmt_money(x.get("last_unit_cost")), fmt_money(x.get("average_unit_cost")),
                               fmt_int(x.get("batches"))] for x in c.get("cost_per_good_bottle") or []],
                             numeric=(1, 2, 3), empty="Aucun lot expédié sur la période."))
    return kv, tables, notes


def _week_rows(series_by_col, money_cols=()):
    """series_by_col : liste de séries de même longueur -> lignes [semaine, v1, v2...]."""
    rows = []
    first = series_by_col[0] if series_by_col else []
    for i, pt in enumerate(first):
        week = fmt_date(pt.get("week_start")) + (" (en cours)" if pt.get("partial") else "")
        row = [week]
        for j, s in enumerate(series_by_col):
            v = s[i].get("value") if i < len(s) else None
            row.append(fmt_money(v) if j in money_cols else fmt_int(v))
        rows.append(row)
    return rows


def _card_growth(cid, c):
    kv, tables, notes = [], [], []
    if cid == "new_patients":
        tables.append(_table("Par semaine", ["Semaine du", "Nouveaux patients"],
                             _week_rows([c.get("series") or []]), numeric=(1,)))
    elif cid == "consultations":
        tables.append(_table("Par semaine", ["Semaine du", "Médicales", "Spirituelles"],
                             _week_rows([c.get("medical") or [], c.get("spiritual") or []]),
                             numeric=(1, 2)))
    elif cid == "sales":
        tables.append(_table("Par semaine (FCFA)", ["Semaine du", "Ventes"],
                             _week_rows([c.get("series") or []], money_cols=(0,)), numeric=(1,)))
        prev = c.get("previous_period")
        tables.append(_table(f"Période précédente ({_period_text(prev)})", ["Semaine du", "Ventes"],
                             _week_rows([c.get("sales_previous") or []], money_cols=(0,)), numeric=(1,)))
    return kv, tables, notes


BUILDERS = {"money": _card_money, "products": _card_products, "production": _card_production,
            "growth": _card_growth}


def _card(section, cid, c):
    kv, tables, notes = BUILDERS[section](cid, c)
    state = f"État actuel au {fmt_instant(c.get('as_of'))}" if c.get("current_state") else None
    return {"title": label(c.get("title_key") or f"reports.cards.{cid}"),
            "period": "état actuel, pas la période choisie" if c.get("current_state")
            else _period_text(c.get("period")),
            "source": c.get("source") or "-", "state": state,
            "kv": kv, "tables": tables, "notes": [n for n in notes if n]}


def _control(control):
    items = []
    for i in (control or {}).get("items") or []:
        flags = []
        if i.get("current_state"):
            flags.append("état actuel")
        if i.get("recomputed"):
            flags.append("recalculé")
        if i.get("already_notified_on"):
            flags.append(f"déjà signalé le {fmt_date(i['already_notified_on'])}")
        items.append({"label": i.get("label") or i.get("kind") or "-",
                      "first_seen": fmt_date(i.get("first_seen")),
                      "flags": ", ".join(flags) or "-"})
    rec = (control or {}).get("recomputed") or []
    return items, (f"{len(rec)} jour(s) sans enregistrement du soir ont été recalculés." if rec else None)


def build_context(header_ctx: Dict[str, Any], data: Dict[str, Any],
                  now: Optional[datetime] = None) -> Dict[str, Any]:
    """data : {period, money, products, production, growth, control, sold} (sections absentes
    tolerees). sold : {items, total, amount_basis}."""
    now = now or datetime.now(timezone.utc)
    blocks = []
    for section, title, ids in BLOCKS:
        cards = [_card(section, cid, (data.get(section) or {})[cid])
                 for cid in ids if (data.get(section) or {}).get(cid)]
        if cards:
            blocks.append({"title": title, "cards": cards})
    control_items, control_note = _control(data.get("control"))
    sold = data.get("sold") or {}
    items = list(sold.get("items") or [])
    total = int(sold.get("total") or len(items))
    rows = [[x.get("name") or f"#{x.get('product_id')}", x.get("category") or "-",
             fmt_int(x.get("quantity")), fmt_money(x.get("amount"))] for x in items[:MAX_ROWS]]
    return {**header_ctx,
            "period_text": _period_text(data.get("period")),
            "generated_at": fmt_instant(now),
            "control_items": control_items, "control_note": control_note,
            "blocks": blocks, "sold_rows": rows,
            "sold_truncated": total > MAX_ROWS or len(items) > MAX_ROWS,
            "sold_total": fmt_int(total), "max_rows": MAX_ROWS,
            "amount_basis": label(sold.get("amount_basis") or "reports.table.amount_before_discount"),
            "amount_note": label("reports.table.note_differs_from_cash")}


def render_reports_pdf(header_ctx: Dict[str, Any], data: Dict[str, Any],
                       now: Optional[datetime] = None) -> bytes:
    return render_pdf_from_template(TEMPLATE, build_context(header_ctx, data, now))
