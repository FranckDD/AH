import { defineStore } from 'pinia';
import { ref } from 'vue';
import { CashClosureGateway } from '@/services/CashClosureGateway';

// Cloture de caisse de la secretaire : EN LIGNE SEULEMENT, aucune ecriture PowerSync.
// Avant la validation, le seul etat connu est le statut (sans aucun total) ; le detail revele (attendu,
// ecarts) n'existe qu'apres une validation reussie, dans `result`.
export const useCashClosureStore = defineStore('cashClosure', () => {
    const status = ref(null);
    const result = ref(null);
    const isLoading = ref(false);
    const isSubmitting = ref(false);
    const loadError = ref(false);

    // Ouverture de l'ecran : rattrapage des clotures automatiques en retard, puis statut.
    async function load() {
        isLoading.value = true;
        loadError.value = false;
        result.value = null;
        try {
            try {
                await CashClosureGateway.catchup();
            } catch (err) {
                // le rattrapage est refait par le serveur a la validation ; le statut reste lisible
                console.warn('Rattrapage des clotures automatiques impossible:', err);
            }
            status.value = await CashClosureGateway.getStatus();
        } catch (err) {
            console.error('Erreur chargement du statut de cloture:', err);
            status.value = null;
            loadError.value = true;
        } finally {
            isLoading.value = false;
        }
    }

    // Leve l'erreur axios telle quelle : l'ecran lit le code (409, 422) et le detail.
    // 409 (autre cloture validee entre-temps, caisse non initialisee, retard) : le statut est recharge.
    async function submit(counts) {
        isSubmitting.value = true;
        try {
            result.value = await CashClosureGateway.submit(counts, status.value?.last_closed_at ?? null);
            return result.value;
        } catch (err) {
            // un resultat deja revele (double envoi) n'est jamais efface : on informe seulement
            if (err?.response?.status === 409 && !result.value) await load();
            throw err;
        } finally {
            isSubmitting.value = false;
        }
    }

    function reset() {
        result.value = null;
    }

    // Regularisation de la cloture qui vient d'etre revelee. Leve l'erreur axios telle quelle (422, 404).
    const isRequestingCorrection = ref(false);
    async function requestCorrection({ modeCode, amountDelta, reason }) {
        if (!result.value?.id) throw new Error('Aucune cloture revelee.');
        isRequestingCorrection.value = true;
        try {
            return await CashClosureGateway.requestCorrection(result.value.id, { modeCode, amountDelta, reason });
        } finally {
            isRequestingCorrection.value = false;
        }
    }

    return {
        status, result, isLoading, isSubmitting, loadError, load, submit, reset,
        isRequestingCorrection, requestCorrection,
    };
});

// Revue des clotures (promoteur / admin) : lecture des clotures validees, decision des corrections,
// et pour l'admin seulement la liste des modes et l'initialisation. Les erreurs d'ecriture sont levees
// telles quelles (l'ecran lit le code et le detail).
export const useCashClosureReviewStore = defineStore('cashClosureReview', () => {
    const closures = ref([]);
    const corrections = ref([]);
    const modes = ref([]);
    const status = ref(null);
    const selected = ref(null);
    const isLoading = ref(false);
    const loadError = ref(false);
    const correctionsError = ref(false);
    const busy = ref(false);

    // filters : { dateFrom, dateTo, kind } (dates locales AAAA-MM-JJ)
    // Compteur de requetes : seule la reponse de la DERNIERE demande est appliquee (filtres changes vite).
    let loadSeq = 0;
    async function load(filters = {}) {
        const seq = ++loadSeq;
        isLoading.value = true;
        loadError.value = false;
        try {
            const rows = await CashClosureGateway.list({ ...filters, limit: 500 });
            if (seq !== loadSeq) return;
            closures.value = rows;
            if (selected.value) selected.value = closures.value.find((c) => c.id === selected.value.id) || null;
        } catch (err) {
            if (seq !== loadSeq) return;
            console.error('Erreur chargement des clotures:', err);
            closures.value = [];
            loadError.value = true;
        } finally {
            if (seq === loadSeq) isLoading.value = false;
        }
    }

    async function loadCorrections() {
        correctionsError.value = false;
        try {
            corrections.value = await CashClosureGateway.listCorrections('pending');
        } catch (err) {
            console.error('Erreur chargement des corrections:', err);
            corrections.value = [];
            correctionsError.value = true;
        }
    }

    async function loadModes() {
        modes.value = [...await CashClosureGateway.listModes()]
            .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    }

    async function loadStatus() {
        status.value = await CashClosureGateway.getStatus();
    }

    function select(closure) {
        selected.value = closure;
    }

    async function run(fn) {
        busy.value = true;
        try {
            return await fn();
        } finally {
            busy.value = false;
        }
    }

    const decide = (id, approve) => run(async () => {
        const out = await CashClosureGateway.decideCorrection(id, approve);
        await loadCorrections();
        return out;
    });

    const updateMode = (code, data) => run(async () => {
        const out = await CashClosureGateway.updateMode(code, data);
        await loadModes();
        return out;
    });

    const start = (openingCash) => run(async () => {
        const out = await CashClosureGateway.start(openingCash);
        await loadStatus();
        return out;
    });

    return {
        closures, corrections, modes, status, selected, isLoading, loadError, correctionsError, busy,
        load, loadCorrections, loadModes, loadStatus, select, decide, updateMode, start,
    };
});
