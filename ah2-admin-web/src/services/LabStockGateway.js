import api from '@/services/api';

// Une fonction par route du routeur /lab-stock. Les corps sont STRICTS cote serveur
// (extra=forbid) : on ne transmet que les champs du schema.
const clean = (params) => Object.fromEntries(
    Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== ''),
);

export const LabStockGateway = {
    // ---- produits ----
    async listProducts({ includeInactive } = {}) {
        const params = includeInactive ? { include_inactive: true } : {};
        return (await api.get('/lab-stock/products', { params })).data || [];
    },
    async createProduct({ name, packaging, alert_threshold, supplier }) {
        return (await api.post('/lab-stock/products', clean({ name, packaging, alert_threshold, supplier }))).data;
    },
    // PUT partiel (exclude_unset cote serveur) : packaging/supplier vides sont envoyes
    // tels quels pour pouvoir etre effaces ; seuls les champs fournis partent.
    async updateProduct(id, fields) {
        const allowed = ['name', 'packaging', 'alert_threshold', 'supplier', 'is_active'];
        const body = {};
        for (const k of allowed) if (fields && fields[k] !== undefined) body[k] = fields[k];
        return (await api.put(`/lab-stock/products/${id}`, body)).data;
    },
    async signalProduct(id, level) { return (await api.post(`/lab-stock/products/${id}/signal`, { level })).data; },

    // ---- demandes « a commander » ----
    async listRequests(status) {
        return (await api.get('/lab-stock/requests', { params: clean({ status }) })).data || [];
    },
    async markOrdered(id, expectedDate) {
        return (await api.post(`/lab-stock/requests/${id}/order`, { expected_date: expectedDate })).data;
    },
    async updateExpectedDate(id, expectedDate) {
        return (await api.put(`/lab-stock/requests/${id}/order`, { expected_date: expectedDate })).data;
    },
    async cancelRequest(id, reason) {
        return (await api.post(`/lab-stock/requests/${id}/cancel`, { reason })).data;
    },

    // ---- receptions ----
    async createReceipt(payload) { return (await api.post('/lab-stock/receipts', payload)).data; },
    async listReceipts({ supplier, from, to } = {}) {
        return (await api.get('/lab-stock/receipts', { params: clean({ supplier, from, to }) })).data || [];
    },
    async getReceipt(id) { return (await api.get(`/lab-stock/receipts/${id}`)).data; },
    async cancelReceipt(id, reason) {
        return (await api.post(`/lab-stock/receipts/${id}/cancel`, { reason })).data;
    },

    // ---- comptage / alertes / historique ----
    async submitCount(lines) {
        const body = (lines || []).map((l) => ({
            product_id: l.product_id, previous_qty: l.previous_qty, counted_qty: l.counted_qty,
        }));
        return (await api.post('/lab-stock/counts', { lines: body })).data;
    },
    async countStatus() { return (await api.get('/lab-stock/counts/status')).data; },
    async getAlerts() { return (await api.get('/lab-stock/alerts')).data; },
    async listMovements({ productId, limit } = {}) {
        return (await api.get('/lab-stock/movements', { params: clean({ product_id: productId, limit }) })).data || [];
    },

    // ---- depenses ----
    async expenses({ from, to } = {}) {
        return (await api.get('/lab-stock/expenses', { params: clean({ from, to }) })).data;
    },
    async priceHistory(productId) {
        return (await api.get(`/lab-stock/products/${productId}/price-history`)).data || [];
    },
};

// Message d'erreur serveur affichable : detail texte, liste Pydantic, objet { message }, sinon repli.
export function describeLabStockError(err, fallback) {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (detail && typeof detail === 'object' && !Array.isArray(detail) && typeof detail.message === 'string') {
        return detail.message;
    }
    if (Array.isArray(detail) && detail.length) {
        return detail.map((d) => (d.loc ? `${d.loc.slice(1).join('.')} : ` : '') + (d.msg || String(d))).join(' ; ');
    }
    return fallback;
}
