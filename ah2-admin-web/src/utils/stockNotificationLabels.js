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

// Motifs generes par le comptage physique (texte stocke en francais, jamais reecrit) : rendus dans la
// langue courante a partir du texte stocke. Un motif saisi par une personne est rendu tel quel.
const NEG_RE = /^Stock systeme negatif \(valeur lue (-?\d+)\)\. ([\s\S]*)$/;
const GAP_RE = /^Ecart constate au comptage n\. (\d+) : systeme (-?\d+), compte (-?\d+)$/;
export function adjustmentReasonText(reason, t) {
    if (typeof reason !== 'string') return reason ?? '';
    const neg = reason.match(NEG_RE);
    if (neg) return t('stockOps.reason_negative_stock', { value: neg[1], rest: adjustmentReasonText(neg[2], t) });
    const gap = reason.match(GAP_RE);
    if (gap) return t('stockOps.reason_count_gap', { id: gap[1], system: gap[2], counted: gap[3] });
    return reason;
}
