import { defineStore } from 'pinia';
import { ref } from 'vue';
import { ReportsGateway } from '@/services/ReportsGateway';
import { PAGE_SIZE } from '@/utils/reports';

// Page Rapports (lecture). Chaque type de requete a son compteur : une reponse arrivee apres une requete plus
// recente (periode changee vite, filtre tape) est ignoree. L'etat appartient a un utilisateur (poste partage).
export const useReportsStore = defineStore('reports', () => {
    let overviewSeq = 0;
    let tableSeq = 0;
    let settingsSeq = 0;
    const owner = ref(null);

    const overview = ref(null);
    const overviewLoading = ref(false);
    const overviewError = ref('');

    const table = ref({ items: [], total: 0, limit: PAGE_SIZE, offset: 0, amount_basis: '', note_key: '' });
    const tableLoading = ref(false);
    const tableError = ref('');

    const settings = ref(null);
    const settingsError = ref('');

    function reset() {
        overviewSeq++; tableSeq++; settingsSeq++;
        overview.value = null; overviewLoading.value = false; overviewError.value = '';
        table.value = { items: [], total: 0, limit: PAGE_SIZE, offset: 0, amount_basis: '', note_key: '' };
        tableLoading.value = false; tableError.value = '';
        settings.value = null; settingsError.value = '';
    }

    function ensureOwner(userId) {
        if (owner.value !== (userId ?? null)) {
            reset();
            owner.value = userId ?? null;
        }
    }

    async function loadOverview(period) {
        const seq = ++overviewSeq;
        overviewLoading.value = true;
        overviewError.value = '';
        try {
            const data = await ReportsGateway.overview({ dateFrom: period.from, dateTo: period.to });
            if (seq !== overviewSeq) return;
            overview.value = data;
        } catch (e) {
            if (seq !== overviewSeq) return;
            overview.value = null;
            overviewError.value = e?.response?.data?.detail && typeof e.response.data.detail === 'string'
                ? e.response.data.detail : 'error';
        } finally {
            if (seq === overviewSeq) overviewLoading.value = false;
        }
    }

    async function loadTable(period, { q, itemType, category, sort, offset }) {
        const seq = ++tableSeq;
        tableLoading.value = true;
        tableError.value = '';
        try {
            const data = await ReportsGateway.productsSold({
                dateFrom: period.from, dateTo: period.to, q, itemType, category, sort, limit: PAGE_SIZE, offset,
            });
            if (seq !== tableSeq) return;
            table.value = data;
        } catch (e) {
            if (seq !== tableSeq) return;
            table.value = { items: [], total: 0, limit: PAGE_SIZE, offset: 0, amount_basis: '', note_key: '' };
            tableError.value = typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : 'error';
        } finally {
            if (seq === tableSeq) tableLoading.value = false;
        }
    }

    async function loadSettings() {
        const seq = ++settingsSeq;
        settingsError.value = '';
        try {
            const data = await ReportsGateway.getSettings();
            if (seq !== settingsSeq) return;
            settings.value = data;
        } catch (e) {
            if (seq !== settingsSeq) return;
            settingsError.value = typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : 'error';
        }
    }

    // Erreur levee telle quelle : l'ecran affiche le message du serveur.
    async function saveSettings(values) {
        const out = await ReportsGateway.saveSettings(values);
        settingsSeq++;
        settings.value = out;
        return out;
    }

    return {
        owner, overview, overviewLoading, overviewError, table, tableLoading, tableError, settings, settingsError,
        ensureOwner, reset, loadOverview, loadTable, loadSettings, saveSettings,
    };
});
