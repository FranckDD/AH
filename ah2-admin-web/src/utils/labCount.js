// Comptage hebdomadaire du stock labo : payload POST /lab-stock/counts et lecture des conflits.
const blank = (v) => v === undefined || v === null || String(v).trim() === '';

export const isValidCount = (v) => {
    if (blank(v)) return false;
    const n = Number(v);
    return Number.isInteger(n) && n >= 0 && n <= 1_000_000;
};

// Seuls les produits saisis partent ; previous_qty = stock charge a l'ecran (detection de conflit serveur).
export function buildCountPayload(products, entered) {
    const e = entered || {};
    return (products || [])
        .filter((p) => !blank(e[p.id]))
        .map((p) => ({ product_id: p.id, previous_qty: Number(p.quantity ?? 0), counted_qty: Number(e[p.id]) }));
}

// Accepte la reponse 200 { conflicts } ou l'erreur 409 { detail: { message, conflicts } }.
export function describeConflicts(resp) {
    const src = resp?.conflicts ?? resp?.response?.data?.detail?.conflicts ?? resp?.detail?.conflicts ?? [];
    return (Array.isArray(src) ? src : []).map((c) => ({
        product_id: c.product_id, name: c.name, expected: Number(c.expected), actual: Number(c.actual),
    }));
}
