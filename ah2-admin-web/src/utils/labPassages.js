// Regroupement des examens d'un meme passage patient (batch_id) pour le laboratoire.
// Un passage = tous les examens saisis en une fois pour un patient. Un examen sans batch_id est son propre passage.

export const DONE_STATUSES = ['completed', 'validated'];
export const isDone = (status) => DONE_STATUSES.includes(status);

// Etat d'un examen : tonalite, texte (cle i18n) et icone. L'etat est toujours dit par un mot ET une icone.
export function examStatusMeta(status) {
    if (isDone(status)) {
        return { tone: 'success', labelKey: status === 'validated' ? 'lab.status.validated' : 'lab.status.completed', icon: 'check' };
    }
    if (status === 'pending') return { tone: 'warning', labelKey: 'lab.status.pending', icon: 'clock' };
    return { tone: 'info', labelKey: 'labScreens.status_in_progress', icon: 'beaker' };
}

export const passageKey = (item) => (item.batch_id ? String(item.batch_id) : `solo-${item.result_id}`);

// Progression d'un passage : examens termines sur total (affichee seulement quand il y a plus d'un examen).
export function passageProgress(exams) {
    const total = exams.length;
    const done = exams.filter((e) => isDone(e.status)).length;
    return { done, total, pct: total ? Math.round((done / total) * 100) : 0 };
}

// Paillasse : une ligne de la liste = un examen a saisir ; chaque ligne porte batch_exams (tous les examens du passage).
// Renvoie un passage par patient, dans l'ordre de la liste, avec TOUS ses examens (termines compris).
export function groupPaillasse(items) {
    const byKey = new Map();
    for (const item of items || []) {
        const key = passageKey(item);
        let passage = byKey.get(key);
        if (!passage) {
            const own = { result_id: item.result_id, examen_nom: item.examen_nom, status: item.status };
            passage = {
                key,
                batch_id: item.batch_id || null,
                code: item.code,
                patient_name: item.patient_name,
                patient_sexe: item.patient_sexe,
                patient_age: item.patient_age,
                is_external: !!item.is_external,
                exams: (item.batch_exams && item.batch_exams.length ? item.batch_exams : [own]).map((e) => ({ ...e })),
                pendingIds: [],
            };
            byKey.set(key, passage);
        }
        passage.pendingIds.push(item.result_id);
        // Securite : un examen de la liste est toujours montre, meme si batch_exams ne le contenait pas.
        if (!passage.exams.some((e) => e.result_id === item.result_id)) {
            passage.exams.push({ result_id: item.result_id, examen_nom: item.examen_nom, status: item.status });
        }
    }
    const passages = [...byKey.values()];
    for (const p of passages) {
        p.exams.sort((a, b) => a.result_id - b.result_id);
        p.progress = passageProgress(p.exams);
        p.firstPendingId = p.pendingIds[0];
    }
    return passages;
}

// Historique : une ligne = un examen ; on les regroupe par passage en gardant l'ordre de la page.
export function groupHistory(items) {
    const byKey = new Map();
    for (const item of items || []) {
        const key = passageKey(item);
        let passage = byKey.get(key);
        if (!passage) {
            passage = {
                key,
                batch_id: item.batch_id || null,
                patient_name: item.patient_name,
                patient_sexe: item.patient_sexe,
                patient_age: item.patient_age,
                is_external: !!item.is_external,
                test_date: item.test_date,
                exams: [],
            };
            byKey.set(key, passage);
        }
        passage.exams.push(item);
    }
    const passages = [...byKey.values()];
    for (const p of passages) {
        p.exams.sort((a, b) => a.result_id - b.result_id);
        p.progress = passageProgress(p.exams);
        p.abnormalCount = p.exams.reduce((n, e) => n + (Number(e.nb_anormaux) || 0), 0);
        p.status = passageStatus(p.progress);
    }
    return passages;
}

// Etat global d'un passage : tout termine, rien de termine, ou en cours (n sur total).
export function passageStatus({ done, total }) {
    if (total > 0 && done === total) return { tone: 'success', labelKey: 'lab.status.completed', params: {} };
    if (done === 0) return { tone: 'warning', labelKey: 'lab.status.pending', params: {} };
    return { tone: 'info', labelKey: 'labScreens.passage_partial', params: { done, total } };
}

// Cle du jour (AAAA-MM-JJ) d'une date ISO du serveur ; 'unknown' si la date est absente ou illisible.
export function dayKeyOf(isoDate) {
    const m = /^(\d{4}-\d{2}-\d{2})/.exec(String(isoDate || ''));
    return m ? m[1] : 'unknown';
}

// Passages d'une page regroupes par jour, dans l'ordre (le plus recent d'abord, comme le serveur).
export function groupPassagesByDay(passages) {
    const days = [];
    const index = new Map();
    for (const p of passages || []) {
        const key = dayKeyOf(p.test_date);
        if (!index.has(key)) {
            const day = { key, passages: [] };
            index.set(key, day);
            days.push(day);
        }
        index.get(key).passages.push(p);
    }
    return days;
}

// Un examen a-t-il un resultat imprimable ? (termine ou valide)
export const hasPrintable = (passage) => passage.exams.some((e) => isDone(e.status));
