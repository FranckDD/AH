import { defineStore } from 'pinia';
import { ref } from 'vue';
import api from '@/services/api';
import { FinanceGateway } from '@/services/FinanceGateway';
import { ConsultationGateway } from '@/services/ConsultationGateway';

export const useSecretariatHomeStore = defineStore('secretariatHome', () => {

    const isLoading = ref(false);

    const today = new Date().toISOString().split('T')[0];

    const filters = ref({
        startDate: today,
        endDate: today,
    });

    const stats = ref({
        totalPaid: 0,
        totalWithdrawn: 0,
        remainingDue: 0,
        criticalStockCount: 0,
        expiringStockCount: 0,
        consultationsCount: 0,
    });

    // Registre J2 : GET /pharmacy/alerts/critical existait deja et etait
    // deja utilise pour le COMPTEUR (criticalStockCount ci-dessus, via un
    // autre endpoint kpi/critical_stock_count) mais la liste elle-meme
    // n'etait jamais consommee cote web - la spec du sous-projet
    // secretariat prevoyait une table, jamais transcrite en tache.
    const criticalStockItems = ref([]);

    // Meme pattern que dashboardStore.js (Task 5) : distingue "0 reel" d'un
    // bloc en echec - sans ca, une carte affiche un chiffre indistinguable
    // d'un vrai zero alors que l'appel a echoue.
    const indisponibles = ref([]);

    async function fetchHomeData() {
        isLoading.value = true;
        try {
            const dateParams = {
                startDate: filters.value.startDate,
                endDate: filters.value.endDate,
            };

            const results = await Promise.allSettled([
                FinanceGateway.getIncomeTotal(dateParams),
                FinanceGateway.getExpenseTotal(dateParams),
                FinanceGateway.getDebtTotal(dateParams),
                api.get('/pharmacy/kpi/critical_stock_count'),
                api.get('/pharmacy/kpi/expiring_product_count', { params: { days: 30 } }),
                ConsultationGateway.fetchConsultations({ page: 1, perPage: 1 }),
                api.get('/pharmacy/alerts/critical'),
            ]);

            const [incomeRes, expenseRes, debtRes, criticalRes, expiringRes, consultationsRes, criticalItemsRes] = results;
            const echecs = [];

            const valeurOuEchec = (resultat, nomBloc, lecture, defaut = 0) => {
                if (resultat.status === 'fulfilled') {
                    return lecture(resultat.value);
                }
                echecs.push(nomBloc);
                return defaut;
            };

            stats.value.totalPaid = valeurOuEchec(incomeRes, 'totalPaid', (r) => Number(r.data) || 0);
            stats.value.totalWithdrawn = valeurOuEchec(expenseRes, 'totalWithdrawn', (r) => Number(r.data) || 0);
            stats.value.remainingDue = valeurOuEchec(debtRes, 'remainingDue', (r) => Number(r.data) || 0);
            stats.value.criticalStockCount = valeurOuEchec(criticalRes, 'criticalStock', (r) => r.data?.stock_alerts_count || 0);
            stats.value.expiringStockCount = valeurOuEchec(expiringRes, 'expiringStock', (r) => r.data?.expiring_alerts_count || 0);
            stats.value.consultationsCount = valeurOuEchec(consultationsRes, 'consultations', (r) => r.data?.total ?? 0);
            criticalStockItems.value = valeurOuEchec(criticalItemsRes, 'criticalStockItems', (r) => r.data || [], []);

            indisponibles.value = echecs;

            if (echecs.length > 0) {
                console.error(`Erreur chargement dashboard secretariat: ${echecs.length} appel(s) KPI en echec`, echecs);
            }
        } finally {
            isLoading.value = false;
        }
    }

    function setDates(start, end) {
        filters.value.startDate = start;
        filters.value.endDate = end;
        fetchHomeData();
    }

    return { isLoading, filters, stats, criticalStockItems, indisponibles, fetchHomeData, setDates };
});
