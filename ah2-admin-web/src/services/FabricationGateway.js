import api from '@/services/api';

// Une fonction par route du routeur /fabrication. Les corps sont STRICTS cote serveur
// (extra=forbid) : on ne transmet que les champs du schema. Quantites et couts partent
// tels que saisis (chaines ou nombres) : le serveur les lit en Decimal.
const clean = (params) => Object.fromEntries(
    Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== ''),
);

const pickDefined = (fields, allowed) => {
    const body = {};
    for (const k of allowed) if (fields && fields[k] !== undefined) body[k] = fields[k];
    return body;
};

export const FabricationGateway = {
    // ---- intrants ----
    async listIntrants({ includeInactive } = {}) {
        const params = includeInactive ? { include_inactive: true } : {};
        return (await api.get('/fabrication/intrants', { params })).data || [];
    },
    async createIntrant({ name, unit, is_container }) {
        return (await api.post('/fabrication/intrants', clean({ name, unit, is_container }))).data;
    },
    async updateIntrant(id, fields) {
        return (await api.put(`/fabrication/intrants/${id}`, pickDefined(fields, ['name', 'unit', 'is_container', 'is_active']))).data;
    },
    // admin seul cote serveur
    async setThreshold(id, value) {
        return (await api.put(`/fabrication/intrants/${id}/threshold`, { value })).data;
    },

    // ---- achats ----
    // dateFrom / dateTo : AAAA-MM-JJ, bornes incluses (date d'achat)
    async listPurchases({ intrantId, dateFrom, dateTo } = {}) {
        return (await api.get('/fabrication/purchases', {
            params: clean({ intrant_id: intrantId, date_from: dateFrom, date_to: dateTo }),
        })).data || [];
    },
    async createPurchase({ intrant_id, supplier, delivery_ref, purchase_date, quantity, unit_cost }) {
        return (await api.post('/fabrication/purchases', clean({
            intrant_id, supplier, delivery_ref, purchase_date, quantity, unit_cost,
        }))).data;
    },
    async updatePurchase(id, fields) {
        return (await api.put(`/fabrication/purchases/${id}`,
            pickDefined(fields, ['supplier', 'delivery_ref', 'purchase_date', 'quantity', 'unit_cost']))).data;
    },
    async cancelPurchase(id, reason) {
        return (await api.post(`/fabrication/purchases/${id}/cancel`, { reason })).data;
    },

    // ---- lots ----
    // dateFrom / dateTo : AAAA-MM-JJ, bornes incluses (date de production)
    async listBatches({ status, dateFrom, dateTo } = {}) {
        return (await api.get('/fabrication/batches', {
            params: clean({ status, date_from: dateFrom, date_to: dateTo }),
        })).data || [];
    },
    async createBatch({ product_id, production_date, producer_name }) {
        return (await api.post('/fabrication/batches', clean({ product_id, production_date, producer_name }))).data;
    },
    async getBatch(id) { return (await api.get(`/fabrication/batches/${id}`)).data; },
    // PUT partiel (exclude_unset cote serveur) ; consumptions = [{ purchase_id, quantity }]
    async updateBatch(id, fields) {
        return (await api.put(`/fabrication/batches/${id}`,
            pickDefined(fields, ['product_id', 'production_date', 'producer_name', 'consumptions']))).data;
    },
    async startBatch(id) { return (await api.post(`/fabrication/batches/${id}/start`)).data; },
    async finishBatch(id, { qty_good, qty_damaged, qty_rejected, liquid_lost }) {
        return (await api.post(`/fabrication/batches/${id}/finish`, clean({
            qty_good, qty_damaged, qty_rejected, liquid_lost,
        }))).data;
    },
    async reopenBatch(id) { return (await api.post(`/fabrication/batches/${id}/reopen`)).data; },
    async cancelBatch(id, reason) {
        return (await api.post(`/fabrication/batches/${id}/cancel`, { reason })).data;
    },
    async shipBatch(id, { delivery_date, expiry_date, justification }) {
        return (await api.post(`/fabrication/batches/${id}/ship`, clean({
            delivery_date, expiry_date, justification,
        }))).data;
    },

    // ---- sorties declarees (echantillon / autre) d'un lot termine ----
    // quantity : entier ; note exigee par le serveur quand reason = 'autre'
    async declareOutput(batchId, { reason, quantity, note }) {
        return (await api.post(`/fabrication/batches/${batchId}/outputs`, clean({ reason, quantity, note }))).data;
    },
    async cancelOutput(batchId, outputId, reason) {
        return (await api.post(`/fabrication/batches/${batchId}/outputs/${outputId}/cancel`, { reason })).data;
    },
    // dateFrom / dateTo : AAAA-MM-JJ, bornes incluses ; reason : 'echantillon' | 'autre'
    async listOutputs({ dateFrom, dateTo, reason } = {}) {
        return (await api.get('/fabrication/outputs', {
            params: clean({ date_from: dateFrom, date_to: dateTo, reason }),
        })).data || [];
    },

    // ---- produits finis (liste {id, name}, lecture) ----
    async listProducts() { return (await api.get('/fabrication/products')).data || []; },

    // ---- reglages (ecriture : admin seul) ----
    async getSettings() { return (await api.get('/fabrication/settings')).data; },
    async updateSettings({ tolerance_pct, stale_days }) {
        return (await api.put('/fabrication/settings', { tolerance_pct, stale_days })).data;
    },

    // ---- anomalies, resume, cout, tracabilite (lecture) ----
    async getAnomalies() { return (await api.get('/fabrication/anomalies')).data; },
    async getSummary() { return (await api.get('/fabrication/summary')).data; },
    async getProductCost(productId) { return (await api.get(`/fabrication/products/${productId}/cost`)).data; },
    async getTrace(productionLotId) {
        return (await api.get(`/fabrication/trace/production-lot/${productionLotId}`)).data;
    },
};

// Message d'erreur serveur affichable : detail texte, liste Pydantic, objet { message }, sinon repli.
export function describeFabricationError(err, fallback) {
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
