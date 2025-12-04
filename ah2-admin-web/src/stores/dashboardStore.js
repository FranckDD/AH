// Fichier: src/stores/dashboardStore.js

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { FinanceGateway } from '@/services/FinanceGateway'; 
import { ToxicoGateway } from '@/services/ToxicoGateway';
import api from '@/services/api'; 

export const useDashboardStore = defineStore('dashboard', () => {
    
    const isLoading = ref(false);
    
    // Dates par défaut
    const filters = ref({
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0]
    });

    const stats = ref({
        income: 0,
        withdrawals: 0,
        debt: 0,
        activePatients: 0,
        onlineUsers: 0,
        alertsCount: 0
    });

    const recentActivities = ref([]);

    async function fetchDashboardData() {
        isLoading.value = true;
        try {
            // 🟢 1. Gestion des Dates (Heure de fin pour inclure toute la journée)
            const dateParams = {
                startDate: filters.value.startDate, 
                endDate: filters.value.endDate.includes('T') 
                    ? filters.value.endDate 
                    : filters.value.endDate + 'T23:59:59'
            };

            // 🟢 2. Paramètres pour la liste (Globales, sans filtre de date pour voir l'historique récent)
            const listParams = {
                page: 1,
                per_page: 5
            };

            // 🟢 3. Appels API
            const [
                incomeRes,
                expenseRes,
                debtRes,
                recentIncomes, 
                recentExpenses, 
                toxicoRes,
                usersRes
            ] = await Promise.all([
                // KPIs Financiers
                FinanceGateway.getIncomeTotal(dateParams),
                FinanceGateway.getExpenseTotal(dateParams),
                FinanceGateway.getDebtTotal(dateParams),
                
                // Listes pour l'activité (5 derniers de chaque)
                FinanceGateway.fetchIncomes(listParams), 
                FinanceGateway.fetchExpenses(listParams),
                
                // Autres stats
                ToxicoGateway.getDashboardStats(),
                api.get('/users/', { params: { page: 1, per_page: 1 } }) 
            ]);

            // 🟢 4. Mise à jour des Stats (KPIs)
            
            // Recettes : On prend la valeur calculée par le backend (total_payments)
            // qui somme les 'advance_amount' (ce qui est réellement payé)
            stats.value.income = Number(incomeRes.data) || 0;
            
            // Dépenses
            stats.value.withdrawals = Number(expenseRes.data) || 0;
            
            // Dettes (Reste à payer)
            stats.value.debt = Number(debtRes.data) || 0;
            
            // Toxico
            if (toxicoRes.data) {
                stats.value.activePatients = toxicoRes.data.currentMonthAdmissions || 0;
            }
            
            // Users
            if (usersRes.data) {
                stats.value.onlineUsers = usersRes.data.total || usersRes.data.count || 0;
            }

            // 🟢 5. Activités Récentes (Fusion & Correction Logique)
            
            // A. Traitement des ENTRÉES (Venant de /caisse/)
            // FORCE TYPE = INCOME (Vert)
            // MONTANT = advance_amount (Ce qui a été payé)
            const formattedIncomes = (recentIncomes.data.data || []).map(t => ({
                id: `inc-${t.transaction_id}`,
                label: t.transaction_type === 'PAYMENT' ? 'Paiement / Avance' : (t.transaction_type || 'Recette'),
                description: t.note || `Transaction #${t.transaction_id}`,
                date: t.paid_at || t.created_at,
                // CORRECTION CRITIQUE : On affiche ce qui est payé (advance_amount), pas le total dû
                amount: parseFloat(t.advance_amount || t.amount || 0), 
                total_due: parseFloat(t.amount || 0), // On garde le total pour info si besoin
                type: 'INCOME', // ✅ Toujours vert car vient de la caisse
                status: t.status === 'active' ? 'Validé' : t.status
            }));

            // B. Traitement des SORTIES (Venant de /retrait/)
            // FORCE TYPE = EXPENSE (Rouge)
            const formattedExpenses = (recentExpenses.data.data || []).map(t => ({
                id: `exp-${t.retrait_id}`,
                label: t.category || 'Dépense / Retrait',
                description: t.justification,
                date: t.retrait_at || t.created_at,
                amount: parseFloat(t.amount),
                type: 'EXPENSE', // ✅ Toujours rouge car vient des retraits
                status: 'Validé'
            }));

            // C. Fusion et Tri Décroissant (Le plus récent en haut)
            const combined = [...formattedIncomes, ...formattedExpenses].sort((a, b) => {
                return new Date(b.date) - new Date(a.date);
            });

            // D. Garder les 5 plus récents
            recentActivities.value = combined.slice(0, 5);

        } catch (error) {
            console.error("Erreur chargement Dashboard:", error);
        } finally {
            isLoading.value = false;
        }
    }

    function setDates(start, end) {
        filters.value.startDate = start;
        filters.value.endDate = end;
        fetchDashboardData();
    }

    return { isLoading, filters, stats, recentActivities, fetchDashboardData, setDates };
});