import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { FinanceGateway } from '@/services/FinanceGateway';

export const useFinancialStore = defineStore('financial', () => {
    
    // --- ÉTAT (STATE) ---
    const transactions = ref([]); 
    const isLoading = ref(false);
    
    // Pagination (Total combiné estimé)
    const totalItems = ref(0); 
    
    // KPI (Totaux globaux calculés par le backend)
    const kpi = ref({
        income: 0,
        expense: 0
    });

    // Filtres (Liaison avec la Vue)
    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        type: 'ALL', // 'ALL', 'INCOME', 'EXPENSE'
        category: '',
        startDate: '',
        endDate: ''
    });

    // --- ACTIONS ---

    /**
     * Charge les données (Recettes + Dépenses) et met à jour les KPI
     */
    async function fetchTransactions() {
        isLoading.value = true;
        transactions.value = []; 

        try {
            const params = {
                page: filters.value.page,
                per_page: filters.value.per_page,
                searchQuery: filters.value.searchQuery,
                startDate: filters.value.startDate,
                endDate: filters.value.endDate
            };

            let incomesRaw = [];
            let expensesRaw = [];
            let countIn = 0;
            let countOut = 0;

            const promises = [];

            // 1. Appel Recettes (si filtre compatible)
            if (filters.value.type === 'ALL' || filters.value.type === 'INCOME') {
                promises.push(
                    FinanceGateway.fetchIncomes(params).then(res => {
                        incomesRaw = res.data.data || [];
                        countIn = res.data.total || 0;
                    })
                );
            }

            // 2. Appel Dépenses (si filtre compatible)
            if (filters.value.type === 'ALL' || filters.value.type === 'EXPENSE') {
                promises.push(
                    FinanceGateway.fetchExpenses(params).then(res => {
                        expensesRaw = res.data.data || []; // La nouvelle route /search renvoie {data, total}
                        countOut = res.data.total || 0;
                    })
                );
            }

            await Promise.all(promises);

            // 3. Normalisation (Unification du format pour le tableau Vue)
            
            const normalizedIncomes = incomesRaw.map(item => ({
                id: `inc-${item.transaction_id}`,
                raw_id: item.transaction_id,
                date: item.paid_at ? new Date(item.paid_at).toISOString().split('T')[0] : '', // Format YYYY-MM-DD
                description: item.note || `Recette #${item.transaction_id}`,
                category: item.transaction_type, 
                amount: parseFloat(item.amount),
                type: 'INCOME',
                status: item.status === 'active' ? 'Validé' : item.status,
                paymentMethod: item.payment_method
            }));

            const normalizedExpenses = expensesRaw.map(item => ({
                id: `exp-${item.retrait_id}`,
                raw_id: item.retrait_id,
                date: item.retrait_at ? new Date(item.retrait_at).toISOString().split('T')[0] : '',
                description: item.justification,
                category: item.category || 'Dépense', 
                amount: parseFloat(item.amount),
                type: 'EXPENSE',
                status: item.status === 'active' ? 'Validé' : item.status,
                paymentMethod: item.payment_method || 'Espèces'
            }));

            // 4. Fusion et Tri (Décroissant par date)
            let combined = [...normalizedIncomes, ...normalizedExpenses];
            combined.sort((a, b) => new Date(b.date) - new Date(a.date));

            // Filtrage Client supplémentaire pour la catégorie (si nécessaire)
            if (filters.value.category) {
                combined = combined.filter(t => t.category === filters.value.category);
            }

            transactions.value = combined;
            totalItems.value = (filters.value.type === 'ALL') ? (countIn + countOut) : (countIn || countOut);

            // 5. Mise à jour des KPI Globaux
            await updateKPIs();

        } catch (err) {
            console.error("Erreur chargement finance:", err);
        } finally {
            isLoading.value = false;
        }
    }

    /**
     * Récupère les totaux globaux (indépendamment de la page courante)
     */
    async function updateKPIs() {
        try {
            const params = { startDate: filters.value.startDate, endDate: filters.value.endDate };
            
            // On lance les requêtes de totaux en parallèle
            const [incRes, expRes] = await Promise.all([
                FinanceGateway.getIncomeTotal(params),
                FinanceGateway.getExpenseTotal(params)
            ]);
            
            // L'API renvoie directement un float (response_model=float)
            kpi.value.income = incRes.data || 0;
            kpi.value.expense = expRes.data || 0;

        } catch (e) {
            console.error("Erreur KPI:", e);
        }
    }

    // --- ACTIONS UI ---

    function setPage(page) {
        filters.value.page = page;
        fetchTransactions();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchTransactions();
    }

    async function addTransaction(data) {
        isLoading.value = true;
        try {
            if (data.type === 'INCOME') {
                await FinanceGateway.createIncome(data);
            } else {
                await FinanceGateway.createExpense(data);
            }
            // Reset page et rechargement
            filters.value.page = 1;
            await fetchTransactions(); 
        } catch (err) {
            console.error("Erreur création transaction:", err);
            // Tu peux ajouter une gestion d'erreur plus fine ici (toast/notification)
            throw err; 
        } finally {
            isLoading.value = false;
        }
    }

    // --- GETTERS ---
    
    // Ces getters sont utilisés par les cartes KPI du Dashboard
    const totalIncome = computed(() => kpi.value.income);
    const totalExpenses = computed(() => kpi.value.expense);
    const currentBalance = computed(() => kpi.value.income - kpi.value.expense);
    
    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1
    }));

    return {
        transactions,
        isLoading,
        filters,
        pagination,
        totalIncome,
        totalExpenses,
        currentBalance,
        fetchTransactions,
        addTransaction,
        setPage,
        setFilters
    };
});