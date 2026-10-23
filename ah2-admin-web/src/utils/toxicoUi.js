// Aides d'affichage de la toxicologie : couleur des phases (memes teintes qu'avant, via les jetons du theme)
// et calcul reel des nouveaux patients de la semaine, partage par le tableau de bord et la liste.

// Phase 1 (sevrage) rouge, 2 orange, 3 bleu, 4 vert. `bar` = remplissage plein des barres de progression ;
// la phase est toujours aussi ecrite en toutes lettres a cote.
export const PHASE_META = {
    1: { tone: 'danger', bar: 'bg-tone-danger-solid' },
    2: { tone: 'warning', bar: 'bg-tone-warning-solid' },
    3: { tone: 'info', bar: 'bg-tone-info-solid' },
    4: { tone: 'success', bar: 'bg-tone-success-solid' },
};
export const phaseMeta = (phase) => PHASE_META[phase] || { tone: 'neutral', bar: 'bg-ink-muted' };

// Part d'une phase dans les patients actifs (0 a 100).
export const percentOf = (count, total) => (!count || !total ? 0 : (count / total) * 100);

// Patients admis (ou crees) dans les 7 derniers jours, parmi la liste chargee (calcul approximatif : page courante).
export function newThisWeek(patients, now = new Date()) {
    const oneWeekAgo = new Date(now);
    oneWeekAgo.setDate(now.getDate() - 7);

    return (patients || []).filter((p) => {
        const dateSource = p.admissionDate || p.createdAt;
        if (!dateSource) return false;

        const d = new Date(typeof dateSource === 'string' ? dateSource.split('T')[0] : dateSource);
        if (isNaN(d.getTime())) return false;

        return d >= oneWeekAgo;
    }).length;
}
