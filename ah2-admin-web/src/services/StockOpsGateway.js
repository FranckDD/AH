import api from '@/services/api';

// Une fonction par route du routeur /stock. Les corps sont STRICTS cote serveur
// (extra=forbid) : n'envoyer que les champs du schema.
const clean = (params) => Object.fromEntries(
    Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== ''),
);

export const StockOpsGateway = {
    // ---- produits (liste deroulante) : GET /pharmacy/ pagine, toutes pages ----
    async listProducts() {
        const out = [];
        let page = 1;
        let totalPages = 1;
        do {
            const resp = await api.get('/pharmacy/', { params: { page, per_page: 200 } });
            const body = resp.data || {};
            for (const p of body.data || []) out.push({ id: p.medication_id, name: p.drug_name });
            totalPages = body.total_pages || 1;
            page += 1;
        } while (page <= totalPages && page <= 50);
        return out.sort((a, b) => String(a.name).localeCompare(String(b.name)));
    },

    // ---- liste minimale {id, name} (GET /stock/products : StockController/admin/Assistant) ----
    async listStockProducts() { return (await api.get('/stock/products')).data || []; },

    // ---- lots ----
    async createLot(payload) { return (await api.post('/stock/lots', payload)).data; },
    async listLots(status) { return (await api.get('/stock/lots', { params: clean({ status }) })).data; },
    async deliverLot(id, deliveryDate) {
        const body = deliveryDate ? { delivery_date: deliveryDate } : {};
        return (await api.post(`/stock/lots/${id}/deliver`, body)).data;
    },
    async cancelLot(id) { return (await api.post(`/stock/lots/${id}/cancel`)).data; },

    // ---- receptions ----
    async createReceipt(payload) { return (await api.post('/stock/receipts', payload)).data; },
    async listReceipts({ status, mineOnly } = {}) {
        const params = clean({ status });
        if (mineOnly) params.mine_only = true;
        return (await api.get('/stock/receipts', { params })).data;
    },
    async getReceipt(id) { return (await api.get(`/stock/receipts/${id}`)).data; },
    async updateReceiptLines(id, lines) { return (await api.put(`/stock/receipts/${id}/lines`, { lines })).data; },
    async validateReceipt(id) { return (await api.post(`/stock/receipts/${id}/validate`)).data; },
    async rejectReceipt(id, reason) { return (await api.post(`/stock/receipts/${id}/reject`, { reason })).data; },
    async cancelReceipt(id) { return (await api.post(`/stock/receipts/${id}/cancel`)).data; },

    // ---- avaries ----
    async createIncident(payload) { return (await api.post('/stock/incidents', payload)).data; },
    async listIncidents({ status, mineOnly } = {}) {
        const params = clean({ status });
        if (mineOnly) params.mine_only = true;
        return (await api.get('/stock/incidents', { params })).data;
    },
    async validateIncident(id) { return (await api.post(`/stock/incidents/${id}/validate`)).data; },
    async rejectIncident(id, reason) { return (await api.post(`/stock/incidents/${id}/reject`, { reason })).data; },
    async cancelIncident(id) { return (await api.post(`/stock/incidents/${id}/cancel`)).data; },

    // ---- demandes d'ajustement ----
    async createAdjustmentRequest(payload) { return (await api.post('/stock/adjustment-requests', payload)).data; },
    async listAdjustmentRequests({ status, mineOnly } = {}) {
        const params = clean({ status });
        if (mineOnly) params.mine_only = true;
        return (await api.get('/stock/adjustment-requests', { params })).data;
    },
    async cancelAdjustmentRequest(id) { return (await api.post(`/stock/adjustment-requests/${id}/cancel`)).data; },
    async approveAdjustmentRequest(id) { return (await api.post(`/stock/adjustment-requests/${id}/approve`)).data; },
    async rejectAdjustmentRequest(id, note) { return (await api.post(`/stock/adjustment-requests/${id}/reject`, { note })).data; },

    // ---- historique des mouvements ----
    async listMovements({ productId, movementType, dateFrom, dateTo, page, perPage } = {}) {
        const params = clean({
            product_id: productId, movement_type: movementType,
            date_from: dateFrom, date_to: dateTo, page, per_page: perPage,
        });
        return (await api.get('/stock/movements', { params })).data;
    },
};

// Message d'erreur serveur affichable : detail texte, liste Pydantic, sinon repli.
export function describeStockError(err, fallback) {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail) && detail.length) {
        return detail.map((d) => (d.loc ? `${d.loc.slice(1).join('.')} : ` : '') + (d.msg || String(d))).join(' ; ');
    }
    return fallback;
}
