import api from '@/services/api';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';

const cleanParams = (params) => {
    const cleaned = {};
    for (const key in params) {
        const value = params[key];
        if (value !== null && value !== undefined && value !== '') {
            cleaned[key] = value;
        }
    }
    return cleaned;
};

export const CaisseGateway = {

    // --- RECHERCHE (pour la construction d'une facture) ---

    async searchPatients(query) {
        if (!query || query.trim().length < 2) return { data: [] };
        const resp = await api.get('/patients/', { params: { search: query.trim(), per_page: 8 } });
        return resp.data;
    },

    async searchProducts(query) {
        if (!query || query.trim().length < 2) return { data: [] };
        try {
            const resp = await api.get('/pharmacy/', { params: { term: query.trim(), per_page: 8 } });
            return resp.data;
        } catch (err) {
            // Secours hors ligne (secretaire uniquement) - affichage
            // informatif du stock synchronise, jamais une
            // verification/deduction reelle (voir spec, decision
            // utilisateur 2026-09-23). Garde de role explicite : un autre
            // role (ex. admin) hors ligne doit voir l'erreur reseau
            // propagee, pas une liste vide venant de pharmacy_stock
            // (jamais synchronisee pour ces roles).
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['secretaire'])) {
                const rows = await db.getAll(
                    "SELECT * FROM pharmacy_stock WHERE drug_name LIKE ? ORDER BY drug_name LIMIT 8",
                    [`%${query.trim()}%`]
                );
                return {
                    data: rows.map((r) => ({
                        medication_id: r.server_id,
                        drug_name: r.drug_name,
                        quantity: r.quantity,
                        price: Number(r.price),
                    })),
                };
            }
            throw err;
        }
    },

    async searchConsultations(query) {
        if (!query || query.trim().length < 2) return { data: [] };
        const resp = await api.get('/cs/', { params: { search: query.trim(), per_page: 8 } });
        return resp.data;
    },

    // --- CAISSE ---

    async fetchTransactions(params) {
        const query = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            term: params.searchQuery,
            status: params.status,
            date_from: params.startDate,
            date_to: params.endDate,
        };
        return api.get('/caisse/', { params: cleanParams(query) });
    },

    async fetchKpis(params) {
        const query = {
            date_from: params.startDate,
            date_to: params.endDate,
        };
        return api.get('/caisse/dashboard/caisse/kpis', { params: cleanParams(query) });
    },

    async getTransaction(transactionId) {
        return api.get(`/caisse/${transactionId}`);
    },

    async createInvoice(payload) {
        return api.post('/caisse/', payload);
    },

    async addPayment(transactionId, data) {
        return api.post(`/caisse/${transactionId}/payment`, data);
    },

    async settleTransaction(transactionId) {
        return api.post(`/caisse/${transactionId}/settle`);
    },

    async cancelTransaction(transactionId, justification) {
        return api.post(`/caisse/${transactionId}/cancel`, { cancel_justification: justification });
    },

    downloadInvoiceUrl(transactionId) {
        return `${api.defaults.baseURL}/caisse/${transactionId}/invoice/download`;
    },

    // --- RETRAIT ---

    async fetchRetraits(params) {
        const query = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            term: params.searchQuery,
            status: params.status,
            date_from: params.startDate,
            date_to: params.endDate,
        };
        return api.get('/retrait/search', { params: cleanParams(query) });
    },

    async createRetrait(payload) {
        return api.post('/retrait/', payload);
    },

    async cancelRetrait(retraitId, justification) {
        return api.post(`/retrait/${retraitId}/cancel`, { cancel_justification: justification });
    },
};
