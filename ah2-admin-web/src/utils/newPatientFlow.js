// Parcours « nouveau patient » de l'infirmière : enregistrement -> code à noter -> paramètres.
// Fonctions pures (testées dans tests/newPatientFlow.test.mjs).

const defaultSleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Interroge le serveur jusqu'à ce que le patient créé localement y soit arrivé et ait un code.
// fetchOnce() renvoie { patient_id, code_patient } ou null (pas encore là) ; une erreur est traitée
// comme « pas encore ». Renvoie null après timeoutMs ou si le signal est annulé.
export async function pollPatientCode(fetchOnce, {
    timeoutMs = 20000,
    intervalMs = 1000,
    signal,
    now = Date.now,
    sleep = defaultSleep,
} = {}) {
    const deadline = now() + timeoutMs;
    while (!signal?.aborted && now() < deadline) {
        try {
            const res = await fetchOnce();
            if (res?.code_patient) return res;
        } catch {
            // réseau coupé ou serveur occupé : on réessaie jusqu'au délai
        }
        if (signal?.aborted) break;
        await sleep(intervalMs);
    }
    return null;
}

// État affiché dans la fenêtre du code. Priorité : code reçu > hors ligne > trop long > attente.
export function codeDialogState({ code, offline, timedOut } = {}) {
    if (code) return 'ready';
    if (offline) return 'offline';
    if (timedOut) return 'late';
    return 'waiting';
}

// Seule l'infirmière suit ce parcours, et seulement pour un patient qu'elle vient de créer localement.
export function runsNewPatientFlow(role, created) {
    return (role || '').toLowerCase() === 'nurse' && !!created?.localUuid;
}

// Identité transmise au formulaire de paramètres (même forme que PatientDetailView) :
// identifiant serveur quand il est connu, sinon l'uuid local du patient en attente.
export function patientPrefillFromCreated({ localUuid, patientId, code, firstName, lastName }) {
    const known = patientId != null;
    return {
        patientId: known ? patientId : null,
        patientUuid: known ? null : localUuid,
        code: code || '',
        firstName,
        lastName,
    };
}
