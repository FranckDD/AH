from app.utils.mapping_general import normalize_data, parse_datetime, parse_decimal, get_field

def normalize_caisse_data(raw):
    """
    Normalise un objet Caisse en dict prêt pour l'API.
    Inclut tous les items liés à la transaction.
    """
    def get_items(r):
        items = getattr(r, "items", [])
        result = []
        for i in items:
            result.append({
                "item_id": get_field(i, "item_id"),
                "item_type": get_field(i, "item_type"),
                "item_ref_id": get_field(i, "item_ref_id"),
                "unit_price": parse_decimal(get_field(i, "unit_price")),
                "quantity": get_field(i, "quantity"),
                "line_total": parse_decimal(get_field(i, "line_total")),
                "note": get_field(i, "note"),
                "status": get_field(i, "status"),
            })
        return result

    return normalize_data(raw, {
        "caisse_id": lambda r: get_field(r, "transaction_id"),
        "patient_id": "patient_id",
        "patient_name": lambda r: get_field(getattr(r, "patient_by_id", None), "full_name") or get_field(r, "patient_label"),
        "amount_due": lambda r: parse_decimal(get_field(r, "amount") + get_field(r, "advance_amount")),
        "amount_paid": lambda r: parse_decimal(get_field(r, "amount")),
        "payment_date": lambda r: parse_datetime(get_field(r, "paid_at")),
        "payment_method": "payment_method",
        "status": "status",
        "items": get_items,  # Ajout de tous les items
    })
