// Libelles des notifications de stock : retourne une cle i18n + parametres,
// jamais un chemin de cle brut en cas de valeur inconnue.
const KNOWN = {
    receipt: ['valide', 'rejete'],
    incident: ['valide', 'rejete'],
    adjustment: ['approuve', 'refuse'],
};
const ADJUSTMENT_KINDS = ['reapprovisionnement', 'correction'];

export function stockDecidedLabel(payload) {
    const p = payload || {};
    const number = p.number || '?';
    if (KNOWN[p.kind] && KNOWN[p.kind].includes(p.status)) {
        return { key: `notifications.stock_decided_${p.kind}_${p.status}`, params: { number } };
    }
    return { key: 'notifications.stock_decided_other', params: { number, status: p.status || '?' } };
}

export function adjustmentKindLabel(kind) {
    if (ADJUSTMENT_KINDS.includes(kind)) {
        return { key: `notifications.adjustment_kind_${kind}` };
    }
    return { key: null, raw: kind || '?' };
}
