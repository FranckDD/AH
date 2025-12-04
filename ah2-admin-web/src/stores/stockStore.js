import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api'; // Votre client Axios configuré

export const useStockStore = defineStore('stock', () => {
    
    // --- ÉTAT (STATE) ---
    const stockData = ref({
        data: [],
        total: 0,
        page: 1,
        per_page: 10,
        total_pages: 1
    });

    // KPI Globaux (Initialisés à 0)
    const stats = ref({
        totalValue: 0,
        countPharma: 0,
        countNatural: 0,
        lowStockAlerts: 0,
        expiredCount: 0
    });

    const isLoading = ref(false);
    const error = ref(null);
    const currentFilteredValue = ref(0);

    // Filtres
    const filters = ref({
        searchQuery: '',
        categoryFilter: 'ALL', // 'ALL', 'PHARMA', 'NATUREL', 'MATERIEL', 'EXPIRED_ONLY'
        page: 1
    });

    // --- MAPPING HELPERS ---
    // Convertit le format Backend (BDD) vers le format Frontend (Vue)
    const mapProductFromApi = (p) => {
        let cat = 'AUTRE';
        
        // 1. On nettoie la valeur reçue de la BD (minuscules + sans espaces)
        const dbType = (p.medication_type || '').toLowerCase().trim();

        // 2. Vérification robuste
        if (dbType === 'pharmaceutique' || dbType === 'pharma') {
            cat = 'PHARMA';
        } 
        else if (dbType === 'naturel' || dbType === 'nature') {
            cat = 'NATUREL';
        } 
        else if (dbType === 'materiel') {
            cat = 'MATERIEL';
        }

        return {
            id: p.medication_id,
            name: p.drug_name,
            category: cat, // Maintenant ce sera 'PHARMA' correctement
            quantity: p.quantity,
            minThreshold: p.threshold,
            price: p.price,
            expiryDate: p.expiry_date ? p.expiry_date.split('T')[0] : null,
            forme: p.forme
        };
    };

    // Convertit le format Frontend vers Backend (pour Create/Update)
    const mapProductToApi = (p) => {
        let typeDb = 'Autre';
        if (p.category === 'PHARMA') typeDb = 'pharmaceutique';
        else if (p.category === 'NATUREL') typeDb = 'Naturel';
        else if (p.category === 'MATERIEL') typeDb = 'Materiel';

        return {
            drug_name: p.name,
            medication_type: typeDb,
            quantity: parseInt(p.quantity),
            threshold: parseInt(p.minThreshold),
            price: parseFloat(p.price),
            expiry_date: p.expiryDate,
            forme: p.forme || 'Autre'
        };
    };

    // --- ACTIONS ---

    // 1. Récupérer la liste paginée
    async function fetchStock() {
        isLoading.value = true;
        error.value = null;
        try {
            const params = {
                page: filters.value.page,
                per_page: stockData.value.per_page,
            };

            if (filters.value.searchQuery) {
                params.term = filters.value.searchQuery;
            }

            // Gestion des filtres spéciaux pour l'API
            if (filters.value.categoryFilter === 'EXPIRED_ONLY') {
                params.status_filter = 'EXPIRED_ONLY';
            } else if (filters.value.categoryFilter !== 'ALL') {
                params.type_filter = filters.value.categoryFilter; // L'API gère le mapping PHARMA->pharmaceutique
            }

            const response = await api.get('/pharmacy/', { params });
            
            // L'API renvoie { data: [], total: x, page: x ... }
            const result = response.data;

            stockData.value.data = result.data.map(mapProductFromApi);
            stockData.value.total = result.total;
            stockData.value.total_pages = result.total_pages;
            stockData.value.page = result.page;

            // 🟢 NOUVEAU: Mettre à jour la valeur filtrée
            currentFilteredValue.value = result.filtered_value || 0; 

            // On rafraîchit aussi les KPI globaux pour qu'ils restent à jour après une action
            fetchStats(); 

        } catch (err) {
            console.error("Erreur fetchStock:", err);
            error.value = "Impossible de charger le stock.";
        } finally {
            isLoading.value = false;
        }
    }

    // 2. Récupérer les KPI globaux (Dashboard)
    async function fetchStats() {
        try {
            const response = await api.get('/pharmacy/kpi/dashboard_stats');
            stats.value = response.data;
        } catch (err) {
            console.error("Erreur KPI:", err);
        }
    }

    // 3. Sauvegarder (Create / Update)
    async function saveProduct(product) {
        isLoading.value = true;
        try {
            const payload = mapProductToApi(product);
            
            if (product.id) {
                // Update
                await api.put(`/pharmacy/${product.id}`, payload);
            } else {
                // Create
                await api.post('/pharmacy/', payload);
            }
            await fetchStock(); // Rafraîchir la liste
        } catch (err) {
            console.error("Erreur saveProduct:", err);
            alert("Erreur lors de la sauvegarde : " + (err.response?.data?.detail || err.message));
        } finally {
            isLoading.value = false;
        }
    }

    // 4. Supprimer
    async function deleteProduct(id) {
        isLoading.value = true;
        try {
            await api.delete(`/pharmacy/${id}`);
            await fetchStock();
        } catch (err) {
            console.error("Erreur deleteProduct:", err);
            alert("Impossible de supprimer.");
        } finally {
            isLoading.value = false;
        }
    }

    

    // Gestion Pagination / Filtres
    function setPage(newPage) {
        if (newPage >= 1 && newPage <= stockData.value.total_pages) {
            filters.value.page = newPage;
            fetchStock();
        }
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchStock();
    }

    // --- GETTERS ---
    const products = computed(() => stockData.value.data);
    
    const pagination = computed(() => ({
        page: stockData.value.page,
        per_page: stockData.value.per_page,
        total: stockData.value.total,
        total_pages: stockData.value.total_pages
    }));

    return { 
        stockData, isLoading, error, products, pagination, filters, stats, currentFilteredValue,
        fetchStock, fetchStats, setPage, setFilters, saveProduct, deleteProduct
    };
});