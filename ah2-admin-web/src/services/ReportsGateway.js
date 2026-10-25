import api from '@/services/api';

// Une fonction par route du routeur /reports (lecture promoteur et admin ; reglages : admin seul).
// dateFrom / dateTo : AAAA-MM-JJ LOCALES (construites a partir des parties locales de la date) ;
// les entiers partent en nombres JS.
const clean = (params) => Object.fromEntries(
    Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== ''),
);

export const ReportsGateway = {
    // { period, money, products, production, growth, control }
    async overview({ dateFrom, dateTo } = {}) {
        return (await api.get('/reports/overview', { params: clean({ date_from: dateFrom, date_to: dateTo }) })).data;
    },
    // { items, recomputed, period }
    async dailyControl({ dateFrom, dateTo } = {}) {
        return (await api.get('/reports/daily-control', { params: clean({ date_from: dateFrom, date_to: dateTo }) })).data;
    },
    // { items, total, limit, offset, amount_basis, note_key }
    async productsSold({ dateFrom, dateTo, q, itemType, category, sort, limit, offset } = {}) {
        return (await api.get('/reports/products-sold', {
            params: clean({
                date_from: dateFrom, date_to: dateTo, q, item_type: itemType, category, sort,
                limit: Number(limit ?? 50),
                offset: Number(offset ?? 0),
            }),
        })).data;
    },
    // PDF de la periode choisie : Blob (une erreur arrive aussi en Blob, a decoder en texte).
    async exportPdf(dateFrom, dateTo) {
        return (await api.get('/reports/export.pdf', {
            params: clean({ date_from: dateFrom, date_to: dateTo }),
            responseType: 'blob',
        })).data;
    },
    async getSettings() { return (await api.get('/reports/settings')).data; },
    async saveSettings({ cancelledSalesThreshold, adjustmentPendingDays }) {
        return (await api.put('/reports/settings', {
            cancelled_sales_threshold: Number(cancelledSalesThreshold),
            adjustment_pending_days: Number(adjustmentPendingDays),
        })).data;
    },
};
