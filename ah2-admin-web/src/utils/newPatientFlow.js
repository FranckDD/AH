import { describeServerError } from './serverError.js';

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

// État affiché dans la fenêtre du code. Priorité : code reçu > refusé par le serveur > hors ligne > trop long > attente.
// Un patient refusé (doublon de numéro d'identité...) n'aura jamais de code : on le dit au lieu d'attendre.
export function codeDialogState({ code, offline, timedOut, rejected } = {}) {
    if (code) return 'ready';
    if (rejected) return 'rejected';
    if (offline) return 'offline';
    if (timedOut) return 'late';
    return 'waiting';
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

// Le code d'un patient tout juste cree localement s'affiche pour l'infirmiere ET pour la secretaire
// (les deux creent sans connaitre le code, genere par le serveur a l'envoi).
export function showsCodeDialog(role, created) {
    const r = (role || '').toLowerCase();
    return (r === 'nurse' || r === 'secretaire') && !!created?.localUuid;
}

// Apres le code, seule l'infirmiere enchaine sur le formulaire de parametres : c'est une action medicale,
// la secretaire n'y a pas droit.
export function goesToVitalsAfterCode(role) {
    return (role || '').toLowerCase() === 'nurse';
}

// La liste est un instantane : les patients « en attente » (crees localement, pas encore confirmes) y sont
// ajoutes au chargement. Quand leur nombre baisse, le serveur les a confirmes : il faut recharger la liste,
// sinon ils disparaissent sans que leur version confirmee (avec son code) n'apparaisse.
export function shouldRefreshAfterSync(previousPending, currentPending) {
    if (!Number.isFinite(previousPending) || !Number.isFinite(currentPending)) return false;
    return currentPending < previousPending;
}

// Motif d'un refus conserve en quarantaine : le texte du serveur tel quel, ou, pour une erreur de validation
// (liste JSON), les champs refuses. Chaine vide si rien n'est connu.
export function quarantineReason(errorText) {
    if (!errorText) return '';
    const text = String(errorText);
    if (text.startsWith('[')) {
        try {
            const detail = JSON.parse(text);
            return describeServerError({ response: { data: { detail } } }, text);
        } catch {
            return text;
        }
    }
    return text;
}
