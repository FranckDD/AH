// Fabrication : petites fonctions d'affichage et de controle de saisie (pures, testees).

// Nature d'une quantite saisie (jusqu'a 3 decimales, virgule ou point) : 'ok', 'zero' (nombre valide mais nul)
// ou 'invalid' (vide, lettres, negatif, trop de decimales). Sert a donner le bon message d'erreur.
export function classifyQuantity(raw) {
    const s = String(raw ?? '').trim();
    if (!/^\d+([.,]\d{1,3})?$/.test(s)) return 'invalid';
    return /^0+([.,]0+)?$/.test(s) ? 'zero' : 'ok';
}

// Cout unitaire (par bouteille) avec ses deux decimales : 188,24 FCFA et non 188.
export function formatUnitCost(v) {
    const n = Number(v ?? 0);
    const text = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF', minimumFractionDigits: 2, maximumFractionDigits: 2 })
        .format(Number.isFinite(n) ? n : 0);
    return text.replace('XOF', 'FCFA').replace('XAF', 'FCFA');
}

// Libelle d'un achat dans une liste deroulante : intrant, fournisseur, reference de livraison, date, restant.
// t, qty et formatDate sont fournis par l'ecran (traduction et formats locaux).
export function purchaseOptionLabel(p, t, qty, formatDate) {
    const parts = [p.intrant_name || '-', p.supplier || '-'];
    if (p.delivery_ref) parts.push(`${t('fabrication.col_delivery_ref')} ${p.delivery_ref}`);
    parts.push(formatDate(p.purchase_date), `${t('fabrication.col_remaining')} ${qty(p.remaining_qty)}`);
    return parts.join(' | ');
}
