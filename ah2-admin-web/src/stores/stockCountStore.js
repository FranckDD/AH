import { defineStore } from 'pinia';
import { ref } from 'vue';
import { StockCountGateway } from '@/services/StockCountGateway';
import { instantISO } from '@/utils/stockCount';

// Comptage du stock de la pharmacie, A L'AVEUGLE : avant la validation, le seul etat connu d'un comptage est
// { id, started_at, scope, products: [{ id, name }] } ; le detail revele n'existe qu'apres la validation,
// dans `result` (ou dans le detail d'un comptage valide de l'historique). Les erreurs d'ecriture sont levees
// telles quelles (l'ecran lit le code et le detail).
export const HISTORY_PAGE_SIZE = 50;

export const useStockCountStore = defineStore('stockCount', () => {
    let historySeq = 0;
    const open = ref(null);
    const result = ref(null);
    const frequency = ref(null);
    const frequencyError = ref(false);
    const history = ref({ items: [], total: 0, limit: HISTORY_PAGE_SIZE, offset: 0 });
    const historyError = ref(false);
    const isLoadingHistory = ref(false);
    // Proprietaire de tout l'etat ci-dessus (user_id). Poste partage : un autre utilisateur ne voit rien du precedent.
    const owner = ref(null);

    function reset() {
        open.value = null;
        result.value = null;
        frequency.value = null;
        history.value = { items: [], total: 0, limit: HISTORY_PAGE_SIZE, offset: 0 };
        historySeq++;
        isLoadingHistory.value = false;
    }

    // A appeler au montage de l'ecran et a chaque changement d'utilisateur connecte.
    function ensureOwner(userId) {
        if (owner.value !== (userId ?? null)) {
            reset();
            owner.value = userId ?? null;
        }
    }

    // Reprise d'un comptage deja ouvert par cet utilisateur (rechargement de page, 409 au demarrage).
    // La liste des produits vient du statut de frequence (noms seulement, aucune quantite).
    async function findOpen() {
        const page = await StockCountGateway.list({ status: 'en_cours', mine: true, limit: 1 });
        const mine = (page?.items || [])[0];
        if (!mine) return null;
        const st = await StockCountGateway.getStatus();
        open.value = {
            id: mine.id, started_at: mine.started_at, scope: mine.scope,
            products: (st?.products || []).map((p) => ({ id: p.product_id, name: p.name })),
        };
        return open.value;
    }

    async function start(scope) {
        const out = await StockCountGateway.start(scope);
        result.value = null;
        open.value = {
            id: out.id, started_at: out.started_at, scope: out.scope,
            products: (out.products || []).map((p) => ({ id: p.id, name: p.name })),
        };
        return open.value;
    }

    async function submit(lines) {
        if (!open.value) throw new Error('Aucun comptage en cours.');
        result.value = await StockCountGateway.submit(open.value.id, lines, instantISO());
        open.value = null;
        loadFrequency();
        return result.value;
    }

    async function abandon() {
        if (!open.value) return null;
        const out = await StockCountGateway.abandon(open.value.id);
        open.value = null;
        return out;
    }

    // 409 a la validation ou a l'abandon : le comptage n'est plus en cours (abandonne ou valide ailleurs).
    function forgetOpen() { open.value = null; }

    function clearResult() { result.value = null; }

    async function loadFrequency() {
        frequencyError.value = false;
        try {
            frequency.value = await StockCountGateway.getStatus();
        } catch (err) {
            console.error('Erreur chargement de la frequence de comptage:', err);
            frequencyError.value = true;
        }
    }

    async function saveInterval(days) {
        const out = await StockCountGateway.setInterval(days);
        await loadFrequency();
        return out;
    }

    // filters : { dateFrom, dateTo } (dates locales AAAA-MM-JJ). Seule la derniere demande est appliquee.
    // page : 1, 2, ... (50 comptages par page)
    async function loadHistory(filters = {}, page = 1) {
        const seq = ++historySeq;
        isLoadingHistory.value = true;
        historyError.value = false;
        try {
            const out = await StockCountGateway.list({
                ...filters, status: 'valide', limit: HISTORY_PAGE_SIZE, offset: (Math.max(1, page) - 1) * HISTORY_PAGE_SIZE,
            });
            if (seq !== historySeq) return;
            history.value = {
                items: out?.items || [], total: out?.total || 0,
                limit: out?.limit || HISTORY_PAGE_SIZE, offset: out?.offset || 0,
            };
        } catch (err) {
            if (seq !== historySeq) return;
            console.error('Erreur chargement de l historique des comptages:', err);
            history.value = { items: [], total: 0, limit: HISTORY_PAGE_SIZE, offset: 0 };
            historyError.value = true;
        } finally {
            if (seq === historySeq) isLoadingHistory.value = false;
        }
    }

    const getDetail = (id) => StockCountGateway.get(id);

    return {
        open, result, frequency, frequencyError, history, historyError, isLoadingHistory,
        owner, reset, ensureOwner, findOpen, start, submit, abandon, clearResult, forgetOpen, loadFrequency, saveInterval, loadHistory, getDetail,
    };
});
