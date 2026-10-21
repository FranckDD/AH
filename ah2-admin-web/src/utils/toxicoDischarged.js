// Vue "Patients sortis" (toxico) : construction des parametres de
// GET /toxico/dossiers/discharged et petites aides pures.
import { DISCHARGE_REASONS } from './toxicoStays.js';

export const DISCHARGED_PER_PAGE = 20;

export function buildDischargedQuery({ page, per_page, search, reason, from, to } = {}) {
    const p = Number.isInteger(page) && page >= 1 ? page : 1;
    const n = Number.isInteger(per_page) ? Math.min(Math.max(per_page, 1), 100) : DISCHARGED_PER_PAGE;
    const q = { page: p, per_page: n };
    const s = (search || '').trim();
    if (s) q.search = s;
    if (DISCHARGE_REASONS.includes(reason)) q.reason = reason;
    if (from) q.discharged_from = from;
    if (to) q.discharged_to = to;
    return q;
}

// Page a recharger quand la page courante est vide alors que des lignes
// existent (ex. apres une readmission sur la derniere page) ; sinon null.
export function clampDischargedPage(page, total, perPage, rowsOnPage) {
    if (!(total > 0) || !(perPage > 0)) return null;
    const last = Math.max(1, Math.ceil(total / perPage));
    if (page > last || (rowsOnPage === 0 && page > 1)) return Math.min(Math.max(page - 1, 1), last);
    return null;
}

// Cle i18n d'erreur si la periode est inversee (dates ISO YYYY-MM-DD), sinon null.
export function dischargedDateRangeError(from, to) {
    return from && to && from > to ? 'toxico.discharged.errors.date_range' : null;
}

// Ligne de la liste -> forme attendue par ToxicoAdmissionModal (preselectedPatient).
// Nom affichable a partir des parties non vides (pas de double espace).
export function displayName(...parts) {
    return parts.map((p) => String(p ?? '').trim()).filter(Boolean).join(' ');
}

export function toPreselectedPatient(row) {
    if (!row?.patient_id) return null;
    return { patient_id: row.patient_id, first_name: row.patientName || '', last_name: '', code_patient: row.code || '' };
}
