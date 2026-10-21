// Validation d'une ligne de bon de reception.
// Retourne { ok, error } ; error est un code (suffixe de la cle i18n stockOps.line_error_<code>).
export const QTY_FIELDS = ['qty_good', 'qty_damaged', 'qty_lost', 'qty_defective'];

const isQty = (v) => typeof v === 'number' && Number.isInteger(v) && v >= 0;

export function lineTotal(line) {
    return QTY_FIELDS.reduce((s, f) => s + (isQty(line?.[f]) ? line[f] : 0), 0);
}

export function validateReceiptLine(line) {
    for (const f of QTY_FIELDS) {
        if (!isQty(line?.[f])) return { ok: false, error: 'invalid_qty' };
    }
    const sum = lineTotal(line);
    if (sum <= 0) return { ok: false, error: 'sum_zero' };
    const exp = line.qty_expected;
    if (typeof exp === 'number' && Number.isFinite(exp) && sum > exp) {
        return { ok: false, error: 'sum_exceeds' };
    }
    return { ok: true };
}

// Ligne prerenseignee depuis un lot fabrique livre.
export function prefillFromLot(lot) {
    return {
        product_id: lot.product_id,
        product_name: lot.product_name,
        qty_expected: lot.quantity_produced,
        qty_good: 0,
        qty_damaged: 0,
        qty_lost: 0,
        qty_defective: 0,
        lot_number: lot.lot_number || '',
        expiry_date: lot.expiry_date || null,
    };
}
