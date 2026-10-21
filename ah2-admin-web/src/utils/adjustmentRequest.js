// Validation locale d'une demande d'ajustement de stock (secretaire).
// Retourne { ok } ou { ok:false, error } ; error = suffixe de stockAdjust.err_<code>.
export const ADJUSTMENT_KINDS = ['reapprovisionnement', 'correction'];

export function validateAdjustmentRequest(req) {
    if (!ADJUSTMENT_KINDS.includes(req?.kind)) return { ok: false, error: 'kind_invalid' };
    const q = req.quantity;
    if (typeof q !== 'number' || !Number.isInteger(q) || q < 0) return { ok: false, error: 'quantity_invalid' };
    if (req.kind === 'reapprovisionnement' && q === 0) return { ok: false, error: 'quantity_positive' };
    if (!String(req.reason ?? '').trim()) return { ok: false, error: 'reason_required' };
    return { ok: true };
}
