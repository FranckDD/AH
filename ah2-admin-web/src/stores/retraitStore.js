import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { CaisseGateway } from '@/services/CaisseGateway';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';

export const useRetraitStore = defineStore('retrait', () => {

    const retraits = ref([]);
    const isLoading = ref(false);
    const loadError = ref(false);
    const totalItems = ref(0);

    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        status: '',
        startDate: '',
        endDate: '',
    });

    async function fetchRetraits() {
        isLoading.value = true;
        loadError.value = false;
        try {
            const resp = await CaisseGateway.fetchRetraits(filters.value);
            const body = resp.data;
            retraits.value = body.data || [];
            totalItems.value = body.total || 0;
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['secretaire'])) {
                console.warn('Retraits hors ligne - secours sur la table locale PowerSync:', err);
                await refreshRetraitsLocal();
                loadError.value = false;
            } else {
                console.error('Erreur chargement des retraits:', err);
                retraits.value = [];
                totalItems.value = 0;
                loadError.value = true;
                throw err;
            }
        } finally {
            isLoading.value = false;
        }
    }

    // Meme motif que caisseStore.refreshTransactionsLocal (Tache 7).
    async function refreshRetraitsLocal() {
        const rows = await db.getAll('SELECT * FROM caisse_retrait ORDER BY retrait_at DESC');
        retraits.value = rows.map((r) => ({
            ...r,
            retrait_id: r.server_id,
            amount: Number(r.amount),
        }));
        totalItems.value = rows.length;
    }

    function setPage(page) {
        filters.value.page = page;
        fetchRetraits();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchRetraits();
    }

    // En ligne, un retrait en especes superieur a la caisse est refuse avant la saisie. Hors ligne ou si la
    // verification echoue, on ne bloque pas : le serveur ne refuse jamais un rejeu, l'ecart se verra a la cloture.
    async function assertWithinCash(payload) {
        if (typeof navigator !== 'undefined' && navigator.onLine === false) return;
        let over = false;
        try {
            const r = await CaisseGateway.checkRetraitCash(payload.amount, payload.payment_method);
            over = !!r?.data?.over_cash;
        } catch (_e) {
            return;
        }
        if (over) {
            const err = new Error('over cash');
            err.code = 'OVER_CASH';
            throw err;
        }
    }

    async function createRetrait(payload) {
        await assertWithinCash(payload);
        const authStore = useAuthStore();
        if (authStore.hasRole(['secretaire'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO caisse_retrait (
                    id, amount, justification, category, payment_method, retrait_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'active')`,
                [
                    uuid, String(payload.amount), payload.justification,
                    payload.category || null, payload.payment_method, new Date().toISOString(),
                ]
            );
            await refreshRetraitsLocal();
            return { retrait_id: uuid };
        }

        const resp = await CaisseGateway.createRetrait(payload);
        await fetchRetraits();
        return resp.data;
    }

    async function cancelRetrait(retraitId, justification) {
        await CaisseGateway.cancelRetrait(retraitId, justification);
        await fetchRetraits();
    }

    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1,
    }));

    return {
        retraits, isLoading, loadError, filters, pagination,
        fetchRetraits, refreshRetraitsLocal, setPage, setFilters, createRetrait, cancelRetrait,
    };
});
