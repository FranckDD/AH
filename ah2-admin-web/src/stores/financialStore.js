import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { FinanceGateway } from '@/services/FinanceGateway';

export const useFinancialStore = defineStore('financial', () => {
    
    // --- ÉTAT (STATE) ---
    const transactions = ref([]); 
    const isLoading = ref(false);
    
    // Pagination (Total combiné estimé)
    const totalItems = ref(0);
    // Distingue "0 resultat reel" d'un echec de chargement : sans ca, l'entete
    // affiche "0 transactions trouvees" que ce soit vide ou en panne, ce qui
    // viole la contrainte globale du chantier (un chiffre indisponible ne
    // s'affiche jamais comme 0).
    const loadError = ref(false);
    // Meme raisonnement que loadError, mais dedie aux totaux KPI (income/expense) :
    // updateKPIs() est appele independamment de fetchTransactions() et peut echouer
    // seul (ex: la liste charge mais /caisse/total timeout). Sans ce flag, les cartes
    // KPI retombent silencieusement sur leur derniere valeur (0 au premier chargement).
    const kpiError = ref(false);

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
     * Charge le journal financier unifie (Recettes + Dépenses) depuis le
     * backend et met à jour les KPI. Tri, filtrage et pagination sont
     * désormais entièrement côté serveur (voir GET /finance/mouvements) :
     * ne plus rien trier ni filtrer ici, c'est précisément ce qui faussait
     * l'ordre d'une page à l'autre et vidait la dernière page.
     */
    async function fetchTransactions() {
        isLoading.value = true;
        loadError.value = false;
        transactions.value = [];

        try {
            const reponse = await FinanceGateway.fetchMouvements({
                page: filters.value.page,
                per_page: filters.value.per_page,
                date_from: filters.value.startDate,
                date_to: filters.value.endDate,
                search: filters.value.searchQuery,
                category: filters.value.category || undefined,
                sens: filters.value.type === 'ALL' ? undefined : filters.value.type,
                // Restaure le filtrage de l'ancien code (fetchIncomes/fetchExpenses
                // forcaient deja status:'active') : sans ce filtre, les mouvements
                // annules/rembourses (caisse.status permet active/cancelled/refunded)
                // reapparaissent dans le journal alors que les totaux KPI
                // (getIncomeTotal/getExpenseTotal, toujours filtres 'active')
                // les excluent deja - la liste et les totaux se contrediraient.
                status: 'active',
            });

            const corps = reponse.data;

            transactions.value = (corps.data || []).map((m) => ({
                id: `${m.sens === 'INCOME' ? 'inc' : 'exp'}-${m.id}`,
                date: m.date ? String(m.date).split('T')[0] : '',
                description: m.description,
                category: m.category || (m.sens === 'INCOME' ? 'Recette' : 'Dépense'),
                amount: Number(m.amount) || 0,
                type: m.sens,
                status: m.status === 'active' ? 'Validé' : m.status,
                paymentMethod: m.payment_method || 'Espèces',
            }));

            totalItems.value = corps.total || 0;

            await updateKPIs();
        } catch (error) {
            console.error('Erreur chargement des mouvements financiers:', error);
            transactions.value = [];
            totalItems.value = 0;
            loadError.value = true;
            throw error;
        } finally {
            isLoading.value = false;
        }
    }

    /**
     * Récupère les totaux (recettes/dépenses) filtrés exactement comme la
     * liste (fetchTransactions) : mêmes date_from/date_to/search/category/
     * sens/status, via le flux unifié (GET /finance/totaux). Avant, les
     * cartes KPI appelaient getIncomeTotal/getExpenseTotal qui n'acceptaient
     * que date_from/date_to/status - filtrer la liste par catégorie ou
     * recherche laissait les totaux KPI inchangés, en désaccord avec la
     * liste affichée juste en dessous.
     */
    async function updateKPIs() {
        kpiError.value = false;
        try {
            const reponse = await FinanceGateway.fetchTotaux({
                date_from: filters.value.startDate,
                date_to: filters.value.endDate,
                search: filters.value.searchQuery,
                category: filters.value.category || undefined,
                sens: filters.value.type === 'ALL' ? undefined : filters.value.type,
                status: 'active',
            });
            kpi.value.income = reponse.data.income || 0;
            kpi.value.expense = reponse.data.expense || 0;
        } catch (e) {
            console.error("Erreur KPI:", e);
            kpiError.value = true;
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
        loadError,
        kpiError,
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