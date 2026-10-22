// État de connexion/synchronisation affiché dans la barre du haut (fonction pure, testée).
// Priorité : erreur > hors ligne > envoi en cours > file non vide > connecté.
export function resolveConnectionState(input) {
    const { connected, uploading, pending, hasError } = input ?? {};
    const n = Number.isFinite(pending) && pending > 0 ? Math.floor(pending) : 0;

    if (hasError) return { state: 'error', pending: n };
    if (!connected) return { state: 'offline', pending: n };
    if (uploading) return { state: 'syncing', pending: n };
    if (n > 0) return { state: 'pending', pending: n };
    return { state: 'online', pending: 0 };
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
