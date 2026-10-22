// Mise en page du tableau de bord médecin / infirmière : quels blocs afficher (fonctions pures, testées).

const DOCTOR_TILES = ['totalAppointments', 'distinctPatients', 'medicalRecords', 'prescriptions', 'hospitalizations'];
// L'infirmière n'est ni médecin assigné ni prescripteur : ces cartes seraient toujours à 0 pour elle.
const NURSE_TILES = ['medicalRecords', 'hospitalizations'];

// Tout rôle autre que médecin est traité comme l'infirmière : jamais plus de droits que prévu.
export function dashboardBlocks({ role, pendingCount, error } = {}) {
    const isDoctor = (role || '').toLowerCase() === 'medecin';
    return {
        isDoctor,
        canClaim: isDoctor,
        statTiles: isDoctor ? [...DOCTOR_TILES] : [...NURSE_TILES],
        showStatusPanel: isDoctor,
        showMotifPanel: true,
        queueState: Number(pendingCount) > 0 ? 'list' : 'empty',
        showLoadError: !!error,
    };
}

const DAY_MS = 24 * 60 * 60 * 1000;

// Ancienneté d'un patient dans la file, au JOUR près : la consultation est datée du jour de saisie,
// l'heure n'est pas fiable (minuit), on ne l'affiche donc jamais.
export function waitingSince(dateString, now = new Date()) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(dateString || '');
    if (!m) return { kind: 'unknown', days: 0 };
    const then = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    if (Number.isNaN(then.getTime())) return { kind: 'unknown', days: 0 };
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const days = Math.round((today - then) / DAY_MS);
    return days <= 0 ? { kind: 'today', days: 0 } : { kind: 'days', days };
}

// Orange (attention) dès qu'un patient attend depuis la veille ou avant ; sinon neutre.
export function waitingTone(waiting) {
    return waiting?.kind === 'days' && waiting.days >= 1 ? 'warning' : 'neutral';
}
