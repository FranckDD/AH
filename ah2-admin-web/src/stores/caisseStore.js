import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { CaisseGateway } from '@/services/CaisseGateway';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';

export const useCaisseStore = defineStore('caisse', () => {

    const transactions = ref([]);
    const isLoading = ref(false);
    const loadError = ref(false);
    const totalItems = ref(0);

    const kpi = ref({ total_paid: 0, total_factured: 0, remaining_due: 0, recouvrement_rate: 0, total_transactions: 0 });
    const kpiError = ref(false);

    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        status: 'active',
        startDate: '',
        endDate: '',
    });

    async function fetchTransactions() {
        isLoading.value = true;
        loadError.value = false;
        try {
            const resp = await CaisseGateway.fetchTransactions(filters.value);
            const body = resp.data;
            transactions.value = body.data || [];
            totalItems.value = body.total || 0;
            await updateKpis();
        } catch (err) {
            const authStore = useAuthStore();
            // meme motif que patientDossierStore.fetchDossierComplete
            // (sous-projet 2) - !err.response signifie une vraie coupure
            // reseau, jamais une erreur applicative a masquer.
            if (!err.response && authStore.hasRole(['secretaire'])) {
                console.warn('Caisse hors ligne - secours sur la table locale PowerSync:', err);
                await refreshTransactionsLocal();
                loadError.value = false;
            } else {
                console.error('Erreur chargement des transactions caisse:', err);
                transactions.value = [];
                totalItems.value = 0;
                loadError.value = true;
                throw err;
            }
        } finally {
            isLoading.value = false;
        }
    }

    // Rafraichit transactions/totalItems depuis la table locale (pas de
    // pagination/filtre serveur) - beneficie a TOUT ecran consommant ce
    // store, pas seulement celui qui a declenche l'ecriture (meme correctif
    // qu'applique en fix round au sous-projet 2, applique ici des la
    // conception). transaction_id/amount_paid/amount_due/patient_name
    // recalcules ici pour que CaisseList.vue (Tache 9, deja lu en entier)
    // continue de fonctionner sans modification de son template au-dela de
    // ce que la Tache 9 ajoute explicitement - ce sont normalement des
    // champs calcules cote serveur (normalize_caisse_data), reproduits
    // fidelement ici a partir des memes colonnes brutes. patient_name n'a
    // pas d'equivalent local exact (le nom vient d'une jointure Patient
    // cote serveur, jamais synchronisee) - patient_label sert de repli,
    // deja un champ saisi par la secretaire pour un patient sans dossier.
    async function refreshTransactionsLocal() {
        const rows = await db.getAll('SELECT * FROM caisse ORDER BY paid_at DESC');
        transactions.value = rows.map((r) => ({
            ...r,
            transaction_id: r.server_id,
            amount: Number(r.amount),
            advance_amount: Number(r.advance_amount),
            amount_paid: Number(r.advance_amount),
            amount_due: Number(r.amount) - Number(r.advance_amount),
            patient_name: r.patient_label,
            items: r.items ? JSON.parse(r.items) : [],
        }));
        totalItems.value = rows.length;
    }

    async function updateKpis() {
        kpiError.value = false;
        try {
            const resp = await CaisseGateway.fetchKpis({
                startDate: filters.value.startDate || new Date().toISOString().slice(0, 10),
                endDate: filters.value.endDate || new Date().toISOString().slice(0, 10),
            });
            kpi.value = resp.data;
        } catch (err) {
            console.error('Erreur KPI caisse:', err);
            kpiError.value = true;
        }
    }

    function setPage(page) {
        filters.value.page = page;
        fetchTransactions();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchTransactions();
    }

    // Ecriture locale (pas d'appel REST direct) pour secretaire - en ligne
    // comme hors ligne. items serialise en JSON texte (voir AppSchema.js,
    // Tache 4). Retourne un objet minimal { transaction_id: uuid } - le
    // uuid local tient lieu d'id en attendant confirmation serveur, aucun
    // ecran de ce chantier n'enchaine dessus (contrairement au sous-projet
    // 2, ou createMedicalRecord() devait retourner un id exploitable pour
    // la prescription liee).
    async function createInvoice(payload) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['secretaire'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO caisse (
                    id, patient_id, patient_label, items, amount, advance_amount,
                    paid_at, payment_method, transaction_type, note, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')`,
                [
                    uuid, payload.patient_id || null, payload.patient_label || null,
                    JSON.stringify(payload.items || []), String(payload.amount),
                    String(payload.advance_amount || 0), new Date().toISOString(),
                    payload.payment_method, payload.transaction_type, payload.note || null,
                ]
            );
            await refreshTransactionsLocal();
            return { transaction_id: uuid };
        }

        const resp = await CaisseGateway.createInvoice(payload);
        await fetchTransactions();
        return resp.data;
    }

    // transactionId doit toujours etre un server_id reel (entier) - le
    // bouton "verser un paiement" est desactive cote UI (Tache 9) tant que
    // la transaction visee n'a pas ete synchronisee, decision utilisateur
    // 2026-09-23 (contrairement au chainage consultation->prescription du
    // sous-projet 2, jamais un uuid local ici).
    async function addPayment(transactionId, data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['secretaire'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO paiement_echelonne (
                    id, transaction_id, paid_amount, payment_date, payment_method, payment_type, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, transactionId, String(data.paid_amount), new Date().toISOString(),
                    data.payment_method, data.payment_type || 'VERSEMENT_ECHEANCE', data.note || null,
                ]
            );
            // Sans ceci, refreshTransactionsLocal() recalcule amount_paid/
            // amount_due a partir du seul caisse.advance_amount (jamais une
            // somme sur paiement_echelonne) - le solde afficherait un
            // montant perime jusqu'a synchronisation serveur (finding
            // reviewer, fix round 1).
            await db.execute(
                'UPDATE caisse SET advance_amount = advance_amount + ? WHERE server_id = ?',
                [String(data.paid_amount), transactionId]
            );
            await refreshTransactionsLocal();
            return { payment_id: uuid };
        }

        const resp = await CaisseGateway.addPayment(transactionId, data);
        await fetchTransactions();
        return resp.data;
    }

    // "Solder" = verser le solde restant du en une fois. L'endpoint dedie
    // POST /caisse/{id}/settle est documente obsolete cote backend (prefere
    // /payment) et add_installment_payment incremente advance_amount du
    // montant paye (repositories/caisse_repo.py:341) - un versement du
    // montant restant du produit donc exactement le meme effet serveur
    // qu'un solde. Reutilise addPayment() telle quelle (deja cablee en
    // ecriture locale, Tache 7) plutot que de dupliquer sa logique.
    async function settleTransaction(tx) {
        const remaining = Number(tx.amount) - Number(tx.advance_amount || 0);
        await addPayment(tx.transaction_id, {
            paid_amount: remaining,
            payment_method: tx.payment_method,
            payment_type: 'SOLDE',
        });
    }

    async function cancelTransaction(transactionId, justification) {
        await CaisseGateway.cancelTransaction(transactionId, justification);
        await fetchTransactions();
    }

    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1,
    }));

    return {
        transactions, isLoading, loadError, kpi, kpiError, filters, pagination,
        fetchTransactions, refreshTransactionsLocal, setPage, setFilters,
        createInvoice, addPayment, settleTransaction, cancelTransaction,
    };
});
