// Totaux d'une facture caisse (CaisseInvoiceModal.vue) - invariant serveur :
// amount = round2(brut - staff_discount_amount), avance bornee par le NET.
// Le brut est arrondi UNE fois sur la somme brute des lignes (jamais une
// somme de lignes deja arrondies), comme cote backend.
import { computeStaffDiscount } from './staffDiscount.js';

// Arrondi demi-superieur au centime, insensible au bruit binaire (meme
// technique que toCents dans staffDiscount.js).
export const round2 = (v) => {
    const x = Number(v || 0);
    const scaled = Math.abs(Number((x * 100).toPrecision(15)));
    return ((x < 0 ? -1 : 1) * Math.round(scaled)) / 100;
};

// rules === null/undefined = regles non chargees : pour un patient
// Personnel, rulesMissing bloque la validation (le serveur rejetterait
// une facture sans la remise attendue).
export function computeInvoiceTotals({ grossRaw, lines, isStaff, rules, advance }) {
    const gross = round2(grossRaw);
    const rulesMissing = Boolean(isStaff) && !Array.isArray(rules);
    const staffDiscountAmount = isStaff && !rulesMissing
        ? computeStaffDiscount(lines, true, rules).amount
        : 0;
    const net = round2(gross - staffDiscountAmount);
    const adv = Number(advance) || 0;
    const advanceOk = Number(advance) >= 0 && adv <= net;
    return { gross, staffDiscountAmount, net, advanceOk, rulesMissing };
}
