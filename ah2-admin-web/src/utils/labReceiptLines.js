// Lignes de reception du stock labo : totaux affiches, validation locale (cles i18n) et
// payload POST /lab-stock/receipts. Le serveur recalcule les totaux : aucun total n'est envoye.
export const MAX_RECEIPT_LINES = 200;
const DELIVERY_TOLERANCE_DAYS = 1; // meme tolerance que le serveur (fuseaux differents)

const blank = (v) => v === undefined || v === null || String(v).trim() === '';
const toNum = (v) => (blank(v) ? NaN : Number(v));
const isInt = (v) => Number.isInteger(toNum(v));
const isPrice = (v) => {
    if (blank(v)) return false;
    const s = String(v).trim();
    return /^\d+(\.\d{1,2})?$/.test(s) && Number(s) <= 99999999.99;
};
const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

// Calcul en centimes entiers (comme le serveur : qty * prix quantifie a 0.01) : pas de derive flottante.
const priceCents = (v) => Math.round(Number(String(v).trim()) * 100);
export function lineCents(qty, unitPrice) {
    const q = toNum(qty);
    const p = toNum(unitPrice);
    if (!Number.isFinite(q) || !Number.isFinite(p)) return 0;
    return priceCents(unitPrice) * Math.trunc(q);
}
export const lineTotal = (qty, unitPrice) => lineCents(qty, unitPrice) / 100;

export function receiptTotal(lines) {
    return (lines || []).reduce((s, l) => s + lineCents(l.received_qty, l.unit_price), 0) / 100;
}

// Montant FCFA affiche avec ses decimales reelles (jusqu'a 2), sans « ,00 » superflu.
export function formatMoney(v) {
    const n = Number(v ?? 0);
    return `${(Number.isFinite(n) ? n : 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} FCFA`;
}

export function validateReceipt(form, today = new Date()) {
    const errs = new Set();
    const f = form || {};
    if (blank(f.invoice_number)) errs.add('labStock.receipt_err_invoice');
    if (blank(f.supplier)) errs.add('labStock.receipt_err_supplier');
    if (blank(f.delivery_date)) errs.add('labStock.receipt_err_date');
    else {
        const max = new Date(today.getFullYear(), today.getMonth(), today.getDate() + DELIVERY_TOLERANCE_DAYS);
        if (String(f.delivery_date) > ymd(max)) errs.add('labStock.receipt_err_date_future');
    }
    const lines = Array.isArray(f.lines) ? f.lines : [];
    if (!lines.length) errs.add('labStock.receipt_err_no_lines');
    if (lines.length > MAX_RECEIPT_LINES) errs.add('labStock.receipt_err_too_many');
    const seen = new Set();
    for (const l of lines) {
        if (seen.has(l.product_id)) errs.add('labStock.receipt_err_duplicate');
        seen.add(l.product_id);
        if (!isInt(l.received_qty) || toNum(l.received_qty) <= 0 || toNum(l.received_qty) > 1_000_000) {
            errs.add('labStock.receipt_err_qty');
        }
        if (!blank(l.ordered_qty) && (!isInt(l.ordered_qty) || toNum(l.ordered_qty) < 0 || toNum(l.ordered_qty) > 1_000_000)) {
            errs.add('labStock.receipt_err_ordered');
        }
        if (blank(l.lot_number)) errs.add('labStock.receipt_err_lot');
        if (blank(l.expiry_date)) errs.add('labStock.receipt_err_expiry');
        if (!isPrice(l.unit_price)) errs.add('labStock.receipt_err_price');
        // la case « pointee » confirme qu'on a verifie la ligne livree : obligatoire pour confirmer
        if (!l.checked) errs.add('labStock.receipt_err_unchecked');
    }
    return [...errs];
}

export function buildReceiptPayload(form) {
    return {
        invoice_number: String(form.invoice_number || '').trim(),
        supplier: String(form.supplier || '').trim(),
        delivery_date: form.delivery_date,
        lines: (form.lines || []).map((l) => ({
            product_id: l.product_id,
            ordered_qty: blank(l.ordered_qty) ? null : Number(l.ordered_qty),
            received_qty: Number(l.received_qty),
            unit_price: Number(l.unit_price),
            lot_number: String(l.lot_number || '').trim(),
            expiry_date: l.expiry_date,
        })),
    };
}
