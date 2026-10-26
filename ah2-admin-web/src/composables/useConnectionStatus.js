import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { db } from '@/powersync-client/client';
import { resolveConnectionState, isNetworkUploadError, usesPowerSync, buildConnectionInput } from '@/utils/connectionStatus';
import { useAuthStore } from '@/stores/auth';
import { API_URL } from '@/services/api';

// Rafraîchissement de la file d'envoi : elle change à chaque saisie locale, sans événement de statut.
const PENDING_REFRESH_MS = 5000;
// Roles sans PowerSync : sonde de joignabilite de l'API.
const HEALTH_REFRESH_MS = 15000;
const HEALTH_TIMEOUT_MS = 5000;

// API PowerSync utilisée (@powersync/web 2.3.1 / @powersync/common 2.2.1) :
//   db.currentStatus  -> { connected, connecting, hasSynced, dataFlowStatus: { uploading, downloading, uploadError, downloadError } }
//   db.registerListener({ statusChanged }) -> fonction de désabonnement
//   db.getUploadQueueStats() -> { count, size }
export function useConnectionStatus() {
    const input = ref({});
    const syncRole = usesPowerSync(useAuthStore().userRole);
    const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine !== false);
    const apiReachable = ref(true);
    let healthTimer = null;
    let dispose = null;
    let timer = null;
    let alive = true;

    function readStatus() {
        try {
            const s = db?.currentStatus;
            const flow = s?.dataFlowStatus ?? {};
            input.value = {
                ...input.value,
                connected: !!s?.connected,
                connecting: !!s?.connecting,
                uploading: !!flow.uploading,
                // Seule une erreur d'envoi est une vraie erreur ; une erreur de téléchargement hors réseau = hors ligne.
                hasError: !!flow.uploadError,
                // Un échec réseau de l'envoi = hors ligne, pas « Erreur d'envoi ».
                networkError: isNetworkUploadError(flow.uploadError, typeof navigator !== 'undefined' ? navigator.onLine : undefined),
            };
        } catch {
            input.value = { ...input.value, connected: false, uploading: false, hasError: false };
        }
    }

    async function readPending() {
        try {
            const stats = await db.getUploadQueueStats();
            if (alive) input.value = { ...input.value, pending: stats?.count ?? 0 };
        } catch {
            // base indisponible : on garde la dernière valeur connue
        }
    }

    async function probeApi() {
        online.value = typeof navigator === 'undefined' ? true : navigator.onLine !== false;
        if (!online.value) { apiReachable.value = false; return; }
        const ctrl = new AbortController();
        const to = setTimeout(() => ctrl.abort(), HEALTH_TIMEOUT_MS);
        try {
            await fetch(`${API_URL}/health`, { signal: ctrl.signal, cache: 'no-store' });
            // Toute reponse HTTP prouve que l'API repond ; seul un echec reseau/delai = injoignable.
            if (alive) apiReachable.value = true;
        } catch {
            if (alive) apiReachable.value = false;
        } finally {
            clearTimeout(to);
        }
    }

    onMounted(() => {
        if (!syncRole) {
            probeApi();
            healthTimer = setInterval(probeApi, HEALTH_REFRESH_MS);
            window.addEventListener('online', probeApi);
            window.addEventListener('offline', probeApi);
            return;
        }
        readStatus();
        readPending();
        try {
            dispose = db.registerListener({
                statusChanged: () => {
                    readStatus();
                    readPending();
                },
            });
        } catch {
            dispose = null;
        }
        timer = setInterval(readPending, PENDING_REFRESH_MS);
        // navigator.onLine change sans événement PowerSync : relire l'état.
        window.addEventListener('online', readStatus);
        window.addEventListener('offline', readStatus);
    });

    onBeforeUnmount(() => {
        alive = false;
        if (typeof dispose === 'function') dispose();
        if (timer) clearInterval(timer);
        if (healthTimer) clearInterval(healthTimer);
        window.removeEventListener('online', probeApi);
        window.removeEventListener('offline', probeApi);
        window.removeEventListener('online', readStatus);
        window.removeEventListener('offline', readStatus);
    });

    const resolved = computed(() => resolveConnectionState(
        buildConnectionInput({ syncRole, powersync: input.value, online: online.value, apiReachable: apiReachable.value })
    ));
    return {
        state: computed(() => resolved.value.state),
        pending: computed(() => resolved.value.pending),
    };
}
