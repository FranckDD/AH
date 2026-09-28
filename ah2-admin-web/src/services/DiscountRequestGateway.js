// src/services/DiscountRequestGateway.js
import api from './api';

export const DiscountRequestGateway = {
    async listManagers() {
        return api.get('/users/managers');
    },
    async create(invoiceData, requestedTo) {
        return api.post('/discount-requests', { invoice_data: invoiceData, requested_to: requestedTo });
    },
    async cancel(requestId, newRequestedTo) {
        return api.post(`/discount-requests/${requestId}/cancel`, { new_requested_to: newRequestedTo });
    },
    async getHistory(params = {}) {
        return api.get('/discount-requests/history', { params });
    },
    async getKpi(params = {}) {
        return api.get('/discount-requests/kpi', { params });
    },
};
