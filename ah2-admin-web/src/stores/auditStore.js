// Fichier : src/stores/auditStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { AuditGateway } from '@/services/AuditGateway'; // 🟢 Import de la Gateway réelle

export const useAuditStore = defineStore('audit', () => {
    
    // --- STATE ---
    const accessLogs = ref([]);
    const actionLogs = ref([]);
    
    // Pagination et filtres pour les Logs d'Accès
    const accessPagination = ref({ page: 1, per_page: 20, total: 0, total_pages: 1 });
    const accessFilters = ref({
        userId: null,
        dateFrom: null,
        dateTo: null,
        actionType: null // 'LOGIN', 'LOGOUT', 'LOGIN_FAILED'
    });

    // Pagination et filtres pour les Logs d'Actions
    const actionPagination = ref({ page: 1, per_page: 20, total: 0, total_pages: 1 });
    const actionFilters = ref({
        userId: null,
        dateFrom: null,
        dateTo: null,
        resourceType: null, // 'PATIENT', 'TOXICO', etc.
        actionType: null // 'CREATE', 'UPDATE', 'DELETE', etc.
    });
    
    const isLoading = ref(false);

    // --- ACTIONS ---

    async function fetchAccessLogs() {
        isLoading.value = true;
        try {
            const params = { 
                ...accessFilters.value, 
                page: accessPagination.value.page, 
                per_page: accessPagination.value.per_page 
            };
            
            // 🟢 Appel API réel
            const res = await AuditGateway.fetchAccessLogs(params);
            
            accessLogs.value = res.data.data || [];
            accessPagination.value = {
                page: res.data.page,
                per_page: res.data.per_page,
                total: res.data.total,
                total_pages: res.data.total_pages
            };
        } catch (error) {
            console.error("Erreur chargement logs accès:", error);
            accessLogs.value = [];
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchActionLogs() {
        isLoading.value = true;
        try {
            const params = { 
                ...actionFilters.value, 
                page: actionPagination.value.page, 
                per_page: actionPagination.value.per_page 
            };
            
            // 🟢 Appel API réel
            const res = await AuditGateway.fetchActionLogs(params);
            
            actionLogs.value = res.data.data || [];
            actionPagination.value = {
                page: res.data.page,
                per_page: res.data.per_page,
                total: res.data.total,
                total_pages: res.data.total_pages
            };
        } catch (error) {
            console.error("Erreur chargement logs actions:", error);
            actionLogs.value = [];
        } finally {
            isLoading.value = false;
        }
    }

    // Méthodes pour changer la page
    function setAccessPage(page) {
        if (page > 0 && page <= accessPagination.value.total_pages) {
            accessPagination.value.page = page;
            fetchAccessLogs();
        }
    }

    function setActionPage(page) {
        if (page > 0 && page <= actionPagination.value.total_pages) {
            actionPagination.value.page = page;
            fetchActionLogs();
        }
    }
    
    // Méthodes pour changer les filtres (à utiliser dans le composant Vue)
    function setAccessFilters(newFilters) {
        accessFilters.value = { ...accessFilters.value, ...newFilters };
        accessPagination.value.page = 1; // Toujours revenir à la première page
        fetchAccessLogs();
    }
    
    function setActionFilters(newFilters) {
        actionFilters.value = { ...actionFilters.value, ...newFilters };
        actionPagination.value.page = 1; // Toujours revenir à la première page
        fetchActionLogs();
    }


    return {
        isLoading,
        accessLogs,
        actionLogs,
        accessPagination,
        actionPagination,
        accessFilters,
        actionFilters,
        fetchAccessLogs,
        fetchActionLogs,
        setAccessPage,
        setActionPage,
        setAccessFilters,
        setActionFilters
    };
});