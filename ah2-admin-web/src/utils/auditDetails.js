// Resume court d'une ligne d'audit des actions pour la colonne Details (fonction pure, testee).
// Priorite au texte explicite (new_values.details), sinon "champ : avant -> apres" depuis old/new_values.
const HIDDEN = /password|token|secret/i;

export function auditSummary(act) {
    const nv = act?.new_values || {};
    const ov = act?.old_values || {};
    if (nv.details) return String(nv.details);
    if (act?.details) return String(act.details);
    const parts = [];
    for (const [k, v] of Object.entries(nv)) {
        if (HIDDEN.test(k) || v === null || typeof v === 'object') continue;
        parts.push(k in ov && ov[k] !== null && typeof ov[k] !== 'object' ? `${k} : ${ov[k]} -> ${v}` : `${k} : ${v}`);
    }
    return parts.join(' ; ') || '-';
}
