// Affichage des depenses du stock labo : mois continus (mois vides a 0) et largeurs de barres
// proportionnelles au mois le plus cher. Calcul en centimes entiers (pas de derive flottante).
const MIN_VISIBLE_PCT = 2;

const cents = (v) => {
    const n = Number(v);
    return Number.isFinite(n) ? Math.round(n * 100) : 0;
};

// 'YYYY-MM-DD' (ou 'YYYY-MM') -> liste des 'YYYY-MM' de from a to inclus.
export function monthRange(from, to) {
    if (!from || !to) return [];
    const [fy, fm] = String(from).split('-').map(Number);
    const [ty, tm] = String(to).split('-').map(Number);
    if (![fy, fm, ty, tm].every(Number.isFinite)) return [];
    const out = [];
    let y = fy;
    let m = fm;
    while ((y < ty || (y === ty && m <= tm)) && out.length < 240) {
        out.push(`${y}-${String(m).padStart(2, '0')}`);
        m += 1;
        if (m > 12) { m = 1; y += 1; }
    }
    return out;
}

export function buildMonthBars(byMonth, from, to) {
    const totals = new Map();
    for (const row of byMonth || []) {
        if (!row || !row.month) continue;
        totals.set(row.month, (totals.get(row.month) || 0) + cents(row.total));
    }
    const months = new Set(monthRange(from, to));
    for (const m of totals.keys()) months.add(m);
    const ordered = [...months].sort();
    const max = Math.max(0, ...ordered.map((m) => totals.get(m) || 0));
    return ordered.map((month) => {
        const c = totals.get(month) || 0;
        let pct = max > 0 ? Math.round((c / max) * 100) : 0;
        if (c > 0 && pct < MIN_VISIBLE_PCT) pct = MIN_VISIBLE_PCT;
        return { month, total: c / 100, pct, empty: c === 0 };
    });
}

export const sumAmounts = (rows) => (rows || []).reduce((s, r) => s + cents(r && r.total), 0) / 100;

// 'YYYY-MM' -> libelle court localise (ex. « janv. 2026 »).
export function monthLabel(month, locale) {
    const [y, m] = String(month).split('-').map(Number);
    if (!Number.isFinite(y) || !Number.isFinite(m)) return String(month);
    return new Date(y, m - 1, 1).toLocaleDateString(locale, { month: 'short', year: 'numeric' });
}
