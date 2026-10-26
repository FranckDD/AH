// Sejours toxico : motifs de sortie, validation et regroupement par sejour.
// Les valeurs doivent rester alignees sur ToxicoDischargeRequest (backend).

export const DISCHARGE_REASONS = ['guerison', 'abandon', 'exclusion', 'autre'];
export const NOTE_MAX_LENGTH = 2000;

export function dischargeReasonLabelKey(reason) {
    return DISCHARGE_REASONS.includes(reason) ? `toxico.stays.reason.${reason}` : 'toxico.stays.reason.unknown';
}

// Retourne une liste de cles i18n d'erreur (vide si valide). date / minDate / today : AAAA-MM-JJ locaux ;
// la date de sortie n'est ni dans le futur ni avant l'admission du sejour.
export function validateDischarge({ reason, note, date, minDate, today } = {}) {
    if (!DISCHARGE_REASONS.includes(reason)) return ['toxico.stays.errors.reason_required'];
    const trimmed = (note || '').trim();
    if (reason === 'autre' && !trimmed) return ['toxico.stays.errors.note_required'];
    if (trimmed.length > NOTE_MAX_LENGTH) return ['toxico.stays.errors.note_too_long'];
    if (date && today && date > today) return ['toxico.stays.errors.date_future'];
    if (date && minDate && date < minDate) return ['toxico.stays.errors.date_before_admission'];
    return [];
}

// Readmission : valeurs reprises du dossier existant (substance du dernier sejour, tuteur du dossier).
export function readmissionPrefill(dossier) {
    if (!dossier) return {};
    const closed = [...(dossier.stays || [])].filter((s) => !s.is_open).sort((a, b) => b.stay_number - a.stay_number)[0];
    return {
        substance: (closed && closed.substance) || dossier.substance || '',
        guardianName: dossier.guardianName || '',
        guardianContact: dossier.guardianContact || '',
    };
}

// Sortie du dernier sejour d'un dossier inactif ; null si le dossier est actif ou sans sejour clos.
export function dischargeSummary(patient) {
    if (!patient || patient.isActive !== false) return null;
    const last = [...(patient.stays || [])].filter((s) => !s.is_open && s.discharge_date)
        .sort((a, b) => b.stay_number - a.stay_number)[0];
    if (!last) return null;
    return { date: last.discharge_date, reason: last.discharge_reason || null, note: last.discharge_note || null, by: last.discharged_by_name || null };
}

// Statut d'une phase (texte enregistre en francais par le serveur) -> cle i18n ; null si inconnu.
export function phaseStatusKey(status) {
    const s = String(status || '').trim().toLowerCase();
    if (/^en cours/.test(s)) return 'toxico.stays.phase_status.in_progress';
    if (/^termin/.test(s)) return 'toxico.stays.phase_status.finished';
    if (/^interrompu/.test(s)) return 'toxico.stays.phase_status.interrupted';
    return null;
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
