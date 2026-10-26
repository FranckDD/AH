// État de connexion/synchronisation affiché dans la barre du haut (fonction pure, testée).
// Priorité : refus du serveur > hors ligne (ou échec réseau de l'envoi) > envoi en cours > file non vide > connecté.
// networkError : l'erreur d'envoi PowerSync vient du réseau (navigateur hors ligne, aucune réponse reçue),
// ce n'est pas un refus du serveur. PowerSync tente l'envoi même sans réseau : sans cette distinction,
// toute saisie hors ligne affichait « Erreur d'envoi » (défaut 5, 2026-10-26).
export function resolveConnectionState(input) {
    const { connected, uploading, pending, hasError, networkError } = input ?? {};
    const n = Number.isFinite(pending) && pending > 0 ? Math.floor(pending) : 0;

    if (hasError && !networkError) return { state: 'error', pending: n };
    if (!connected || (hasError && networkError)) return { state: 'offline', pending: n };
    if (uploading) return { state: 'syncing', pending: n };
    if (n > 0) return { state: 'pending', pending: n };
    return { state: 'online', pending: 0 };
}

// Échec réseau = navigateur hors ligne, ou erreur sans réponse HTTP de la classe réseau (axios ERR_NETWORK,
// délai dépassé, fetch TypeError). Une réponse 4xx/5xx reçue = refus du serveur, jamais « réseau ».
const NETWORK_CODES = new Set(['ERR_NETWORK', 'ECONNABORTED', 'ETIMEDOUT', 'ECONNREFUSED', 'ECONNRESET', 'ERR_INTERNET_DISCONNECTED']);
export function isNetworkUploadError(err, online) {
    if (!err) return false;
    if (online === false) return true;
    if (err.response) return false;
    if (err.code && NETWORK_CODES.has(err.code)) return true;
    if (err.name === 'TypeError' && /fetch|network|load failed/i.test(err.message || '')) return true;
    return /network error|failed to fetch|timeout/i.test(err.message || '');
}

const TONE_BY_STATE = {
    online: 'success',
    syncing: 'info',
    pending: 'warning',
    offline: 'warning',
    error: 'danger',
};

export function connectionTone(state) {
    return TONE_BY_STATE[state] ?? 'neutral';
}

export function connectionLabelKey(state) {
    return `medicalShell.connection.${state in TONE_BY_STATE ? state : 'offline'}`;
}

// Roles pour lesquels l'application ouvre une connexion PowerSync (App.vue et authStore.login). Pour tous les
// autres, db.currentStatus.connected reste false en permanence : le badge affichait « Hors ligne » alors que
// l'API repondait (cause racine, 2026-10-26). Garder cette liste identique a celle de connectPowerSync.
export const SYNC_ROLES = ['medecin', 'nurse', 'secretaire', 'laborantin'];
export function usesPowerSync(role) {
    return SYNC_ROLES.includes(String(role || '').toLowerCase());
}

// Entree de resolveConnectionState. Role synchronisant : etat PowerSync tel quel. Autre role : pas de file ni
// d'envoi, connecte = navigateur en ligne ET API joignable (sonde /health).
export function buildConnectionInput({ syncRole, powersync, online, apiReachable }) {
    if (syncRole) return { ...(powersync ?? {}) };
    return { connected: online !== false && !!apiReachable, uploading: false, hasError: false, networkError: false, pending: 0 };
}
