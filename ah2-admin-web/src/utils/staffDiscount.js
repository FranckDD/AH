// Calcul pur de la reduction personnel - miroir STRICT de utils/staff_discount.py.
// Les deux implementations sont testees avec tests/fixtures/staff_discount_cases.json.
// Le serveur recalcule et REJETTE tout ecart: toute modification ici doit etre
// repercutee cote Python (et inversement).
//
// Arithmetique en entiers (centimes) pour eviter les erreurs flottantes;
// arrondi demi-superieur UNE seule fois sur la somme des remises.

export const CATEGORIES = ['medicament', 'examen', 'consultation', 'carnet', 'autre_soin'];

export function normalizeItemCategory(itemType) {
    const s = String(itemType ?? '')
        .normalize('NFKD')
        .replace(/[̀-ͯ]/g, '')
        .toLowerCase();
    if (s.includes('consult')) return 'consultation'; // avant "medic": "Consultation Medical"
    if (s.includes('medic')) return 'medicament';
    if (s.includes('carnet') || s.includes('booklet')) return 'carnet';
    if (s.includes('exam')) return 'examen';
    return 'autre_soin';
}

// Arrondi demi-superieur (loin de zero, comme Decimal.quantize ROUND_HALF_UP)
// de la valeur DECIMALE de v au centime, insensible au bruit binaire:
// toPrecision(15) elimine 1.005*100 = 100.49999999999999, 0.1*3, 2.675...
const toCents = (v) => {
    const x = Number(v || 0);
    const scaled = Math.abs(Number((x * 100).toPrecision(15)));
    return (x < 0 ? -1 : 1) * Math.round(scaled);
};
// rate_percent en centiemes de pourcent (supporte jusqu'a 2 decimales)
const toRate100 = (v) => Math.round(Number(v || 0) * 100);

// Division entiere arrondie demi-superieur (loin de zero, comme ROUND_HALF_UP)
function divHalfUp(num, den) {
    const sign = num < 0 ? -1 : 1;
    const a = Math.abs(num);
    return sign * Math.floor((a + den / 2) / den);
}

export function computeStaffDiscount(lines, isStaff, rules) {
    if (!isStaff || !lines || lines.length === 0) return { amount: 0, details: null };
    const active = lines.filter((l) => l.status !== 'cancelled');
    let totalCents = 0;
    const bases = {};
    for (const l of active) {
        const c = toCents(l.line_total);
        totalCents += c;
        const cat = normalizeItemCategory(l.item_type);
        bases[cat] = (bases[cat] || 0) + c;
    }

    const details = [];
    // somme brute en (centimes x centiemes de pourcent x 100) = unite 1/10000 de centime
    let rawSum = 0;
    for (const rule of rules || []) {
        if (!rule.is_active) continue;
        const minCents = toCents(rule.min_invoice_amount);
        if (totalCents < minCents) continue;
        const cat = rule.category;
        const base = bases[cat] || 0;
        if (base <= 0) continue;
        const rate100 = toRate100(rule.rate_percent);
        const raw = base * rate100; // remise = raw / 10000 centimes
        rawSum += raw;
        details.push({
            category: cat,
            rate_percent: Math.trunc(Number(rule.rate_percent || 0)),
            base: base / 100,
            discount: divHalfUp(raw, 10000) / 100, // affichage uniquement
            min_invoice_amount: minCents / 100,
        });
    }
    const amountCents = divHalfUp(rawSum, 10000);
    if (amountCents === 0) return { amount: 0, details: null };
    return { amount: amountCents / 100, details };
}
