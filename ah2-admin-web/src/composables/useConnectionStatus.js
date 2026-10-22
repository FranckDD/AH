import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { db } from '@/powersync-client/client';
import { resolveConnectionState } from '@/utils/connectionStatus';

// Rafraîchissement de la file d'envoi : elle change à chaque saisie locale, sans événement de statut.
const PENDING_REFRESH_MS = 5000;

// API PowerSync utilisée (@powersync/web 2.3.1 / @powersync/common 2.2.1) :
//   db.currentStatus  -> { connected, connecting, hasSynced, dataFlowStatus: { uploading, downloading, uploadError, downloadError } }
//   db.registerListener({ statusChanged }) -> fonction de désabonnement
//   db.getUploadQueueStats() -> { count, size }
export function useConnectionStatus() {
    const input = ref({});
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

    onMounted(() => {
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
    });

    onBeforeUnmount(() => {
        alive = false;
        if (typeof dispose === 'function') dispose();
        if (timer) clearInterval(timer);
    });

    const resolved = computed(() => resolveConnectionState(input.value));
    return {
        state: computed(() => resolved.value.state),
        pending: computed(() => resolved.value.pending),
    };
}
