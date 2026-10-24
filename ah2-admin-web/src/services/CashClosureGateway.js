import api from '@/services/api';

// Une fonction par route du routeur /cash-closure. Corps STRICTS cote serveur (extra=forbid) : on ne transmet
// que les champs du schema. Les montants partent et reviennent en chaines (Decimal cote serveur).
const clean = (params) => Object.fromEntries(
    Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== ''),
);

export const CashClosureGateway = {
    // { configured, last_closed_at, overdue_days, modes: [{ code, label, source }] } : aucun total (a l'aveugle)
    async getStatus() { return (await api.get('/cash-closure/status')).data; },
    // ferme les jours manques a leur 23 h ; renvoie la liste des clotures automatiques creees
    async catchup() { return (await api.post('/cash-closure/catchup')).data || []; },
    // counts = [{ mode, counted: '1500', comment? }] ; lastClosedAt = status.last_closed_at (garde double onglet)
    async submit(counts, lastClosedAt) {
        return (await api.post('/cash-closure', { counts, last_closed_at: lastClosedAt })).data;
    },
    // dateFrom / dateTo : AAAA-MM-JJ ; kind : manual | auto
    async list({ dateFrom, dateTo, kind, limit, offset } = {}) {
        return (await api.get('/cash-closure', {
            params: clean({ date_from: dateFrom, date_to: dateTo, kind, limit, offset }),
        })).data || [];
    },
    async get(id) { return (await api.get(`/cash-closure/${id}`)).data; },
    // secretaire : demande de regularisation d'une cloture validee (approuvee ensuite par promoteur/admin).
    // amountDelta : chaine decimale signee non nulle ; reason : motif non vide.
    async requestCorrection(closureId, { modeCode, amountDelta, reason }) {
        return (await api.post(`/cash-closure/${closureId}/corrections`, {
            mode_code: modeCode, amount_delta: amountDelta, reason,
        })).data;
    },
};

// ---------- revue promoteur / admin (tache 10) ----------
Object.assign(CashClosureGateway, {
    // admin, une seule fois : fond de caisse de depart (chaine decimale), immuable ensuite
    async start(openingCash) {
        return (await api.post('/cash-closure/start', { opening_cash: openingCash })).data;
    },
    // status : pending | approved | rejected (vide = toutes)
    async listCorrections(status) {
        return (await api.get('/cash-closure/corrections', { params: clean({ status }) })).data || [];
    },
    async decideCorrection(id, approve) {
        return (await api.post(`/cash-closure/corrections/${id}/decide`, { approve: !!approve })).data;
    },
    // [{ code, label, is_active, sort_order }], actifs et inactifs
    async listModes() { return (await api.get('/payment-modes')).data || []; },
    // admin : { label?, is_active?, sort_order? } ; aucune creation ni suppression de mode
    async updateMode(code, data) {
        return (await api.put(`/payment-modes/${encodeURIComponent(code)}`, data)).data;
    },
});
