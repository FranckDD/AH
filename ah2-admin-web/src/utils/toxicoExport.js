// Exports PDF toxico (liste des patients sortis + dossier) : aides pures.
import { buildDischargedQuery } from './toxicoDischarged.js';

// Miroir exact des gardes backend (role_required) - codes exacts pour authStore.hasRole.
export const TOXICO_LIST_EXPORT_ROLES = ['ToxicoManager', 'Psychologist', 'SpiritualCounsellor', 'Assistant', 'admin'];
// Evaluations = donnees sensibles : ni Assistant ni accompagnateur spirituel.
export const TOXICO_DOSSIER_EXPORT_ROLES = ['Psychologist', 'ToxicoManager', 'admin'];

export const DISCHARGED_EXPORT_FILENAME = 'toxico_patients_sortis.pdf';

// Memes filtres que la liste affichee, sans pagination (l'export prend tout).
export function buildDischargedExportQuery(filters = {}) {
    const { page, per_page, ...rest } = buildDischargedQuery(filters); // eslint-disable-line no-unused-vars
    return rest;
}

// Recherche a exporter : une saisie encore en attente (debounce) prime sur
// la valeur deja appliquee, pour que le PDF corresponde a ce qui est tape.
export function resolveExportSearch(pending, applied) {
    return pending !== null && pending !== undefined ? pending : (applied ?? '');
}

export function dossierExportFilename(patientId) {
    return `dossier_toxico_${patientId}.pdf`;
}

export function exportErrorKey(error) {
    const status = error?.response?.status;
    if (status === 401 || status === 403) return 'toxico.export.errors.forbidden';
    if (status === 404) return 'toxico.export.errors.not_found';
    if (status === 422) return 'toxico.export.errors.invalid';
    return 'toxico.export.errors.generic';
}

// Declenche le telechargement navigateur d'un blob PDF.
export function downloadPdfBlob(data, filename) {
    const blob = new Blob([data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    // Firefox/Safari : le lien doit etre dans le DOM, et l'URL revoquee apres coup.
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}
