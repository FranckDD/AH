// Sejours toxico : motifs de sortie, validation et regroupement par sejour.
// Les valeurs doivent rester alignees sur ToxicoDischargeRequest (backend).

export const DISCHARGE_REASONS = ['guerison', 'abandon', 'exclusion', 'autre'];
export const NOTE_MAX_LENGTH = 2000;

export function dischargeReasonLabelKey(reason) {
    return DISCHARGE_REASONS.includes(reason) ? `toxico.stays.reason.${reason}` : 'toxico.stays.reason.unknown';
}

// Retourne une liste de cles i18n d'erreur (vide si valide).
export function validateDischarge({ reason, note } = {}) {
    if (!DISCHARGE_REASONS.includes(reason)) return ['toxico.stays.errors.reason_required'];
    const trimmed = (note || '').trim();
    if (reason === 'autre' && !trimmed) return ['toxico.stays.errors.note_required'];
    if (trimmed.length > NOTE_MAX_LENGTH) return ['toxico.stays.errors.note_too_long'];
    return [];
}

// Regroupe evaluations/phases par sejour, sejours par ordre chronologique
// (stay_number croissant). Elements sans sejour -> groupe "ancien" en dernier.
export function groupByStay(items, stays) {
    const ordered = [...(stays || [])].sort((a, b) => a.stay_number - b.stay_number);
    const groups = ordered.map((stay) => ({ stay, legacy: false, items: [] }));
    const byNumber = new Map(groups.map((g) => [g.stay.stay_number, g]));
    const legacy = { stay: null, legacy: true, items: [] };
    for (const item of items || []) {
        const g = item?.stay_number != null ? byNumber.get(item.stay_number) : null;
        (g || legacy).items.push(item);
    }
    if (legacy.items.length) groups.push(legacy);
    return groups;
}

// Message lisible depuis une erreur axios (detail texte ou liste pydantic).
export function apiErrorMessage(error, fallback) {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail) && detail.length) {
        return detail.map((d) => String(d?.msg || '').replace(/^Value error,\s*/, '')).filter(Boolean).join(' ') || fallback;
    }
    return fallback;
}

// Tri du plus recent au plus ancien sur item.date (ISO). Stable pour les egalites.
export function sortNewestFirst(items) {
    return [...(items || [])].sort((a, b) => String(b?.date || '').localeCompare(String(a?.date || '')));
}

// Badge vert des phases terminees (statut texte du backend, ex. "Terminé").
export function isFinishedStatus(status) {
    return typeof status === 'string' && /termin/i.test(status);
}
