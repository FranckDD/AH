// src/services/PrinterBridgeGateway.js
import { useConfigStore } from '@/stores/configStore';

const BRIDGE_URL = import.meta.env.VITE_PRINT_BRIDGE_URL || 'http://localhost:9123';

export const PrinterBridgeGateway = {
    /**
     * Envoie le JSON d'un ticket au service pont local pour impression.
     * Toujours best-effort du point de vue de l'appelant : cette fonction
     * leve une erreur explicite en cas d'echec (pont injoignable, jeton
     * manquant, imprimante hors ligne) - c'est a l'appelant de l'attraper
     * et de ne jamais bloquer le flux metier (creation de facture) dessus.
     */
    async printTicket(ticketData) {
        const configStore = useConfigStore();
        const token = configStore.ticketPrintToken;
        if (!token) {
            throw new Error("Jeton d'impression non configuré.");
        }
        const response = await fetch(`${BRIDGE_URL}/print`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Print-Token': token,
            },
            body: JSON.stringify(ticketData),
        });
        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            throw new Error(body.detail || `Impression échouée (${response.status})`);
        }
    },
};
