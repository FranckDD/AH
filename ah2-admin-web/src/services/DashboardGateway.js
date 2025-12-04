import api from '@/services/api';

export const DashboardGateway = {
    /**
     * Récupère les statistiques globales (si vous avez un endpoint backend dédié /stats/global)
     * Sinon, on fera des appels individuels dans le store.
     */
    
    // --- FINANCE (Appels directs aux endpoints de KPI Finance) ---
    async getFinanceIncome(startDate, endDate) {
        const params = { date_from: startDate, date_to: endDate, status: 'active' };
        return api.get('/caisse/total', { params });
    },

    async getFinanceExpenses(startDate, endDate) {
        const params = { date_from: startDate, date_to: endDate, status: 'active' };
        return api.get('/retrait/total', { params });
    },

    async getFinanceDebt(startDate, endDate) {
        const params = { date_from: startDate, date_to: endDate };
        return api.get('/caisse/total_remaining_due', { params });
    },

    async getRecentTransactions(limit = 3) {
        // On récupère les dernières transactions (tous types confondus)
        return api.get('/caisse/', { params: { page: 1, per_page: limit } });
    },

    // --- PATIENTS / TOXICO ---
    async getActivePatientsCount() {
        // Si pas d'endpoint dédié, on peut récupérer la liste avec per_page=1 pour avoir le total
        return api.get('/toxico/patients', { params: { page: 1, per_page: 1 } });
    },

    // --- USERS ---
    async getUsersCount() {
        return api.get('/users/', { params: { page: 1, per_page: 1 } });
    }
};