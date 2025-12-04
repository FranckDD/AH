import api from '@/services/api';

// 🟢 Fonction utilitaire pour nettoyer les paramètres vides
// Transforme { date_from: "" } en {} pour éviter l'erreur 422
const cleanParams = (params) => {
    const cleaned = {};
    for (const key in params) {
        const value = params[key];
        // On garde la valeur seulement si elle n'est pas vide/null/undefined
        if (value !== null && value !== undefined && value !== '') {
            cleaned[key] = value;
        }
    }
    return cleaned;
};

export const FinanceGateway = {
    
    // --- RECETTES (Caisse) ---
    
    async fetchIncomes(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.per_page || 50,
            term: params.searchQuery, 
            date_from: params.startDate,
            date_to: params.endDate
            // status: 'active' // Optionnel selon ton backend
        };

        // 🟢 Nettoyage avant envoi
        const query = cleanParams(rawQuery);
        
        return api.get('/caisse/', { params: query });
    },

    async createIncome(data) {
        const payload = {
            amount: data.amount,
            payment_method: data.paymentMethod,
            transaction_type: data.category || 'AUTRE', 
            note: data.description, 
            paid_at: data.date, 
            patient_id: null, 
            advance_amount: data.amount, 
            items: [] 
        };
        return api.post('/caisse/', payload);
    },

    async getIncomeTotal(params) {
        const query = { 
            date_from: params.startDate, 
            date_to: params.endDate
            // On ne filtre pas par status pour avoir tout l'argent entré, comme la secrétaire
        };
        return api.get('/caisse/total_payments', { params: cleanParams(query) });
    },

    // --- DÉPENSES (Retraits) ---

    async fetchExpenses(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.per_page || 50,
            date_from: params.startDate,
            date_to: params.endDate,
            term: params.searchQuery, 
            status: 'active'
        };

        // 🟢 Nettoyage avant envoi
        const query = cleanParams(rawQuery);

        return api.get('/retrait/search', { params: query });
    },

    async createExpense(data) {
        const payload = {
            amount: data.amount,
            justification: data.description, 
            category: data.category,
            payment_method: data.paymentMethod,
            // Si le backend supporte une date forcée, on l'ajoute ici
            // retrait_at: data.date 
        };
        return api.post('/retrait/', payload);
    },

    async getExpenseTotal(params) {
        const rawQuery = {
            date_from: params.startDate,
            date_to: params.endDate,
            status: 'active'
        };
        return api.get('/retrait/total', { params: cleanParams(rawQuery) });
    },
    async getDebtTotal(params) {
        const query = {
            date_from: params.startDate,
            date_to: params.endDate
        };
        return api.get('/caisse/total_remaining_due', { params: cleanParams(query) });
    },
    async getDashboardCaisseKpis(params) {
        const query = { 
            date_from: params.startDate, 
            date_to: params.endDate
        };
        return api.get('/caisse/dashboard/caisse/kpis', { params: cleanParams(query) });
    },

    

    /**
     * Récupère les activités récentes (Mixte ou Caisse).
     * On utilise l'endpoint de recherche existant mais limité à X éléments.
     */
    async getRecentTransactions(limit = 3) {
        const query = {
            page: 1,
            per_page: limit
            // On ne filtre pas par date ici pour toujours voir les dernières actions saisies
        };
        return api.get('/caisse/', { params: query });
    },
    

};