import api from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import { getStaffDiscountRulesLocal } from '@/powersync-client/referenceData';

export const StaffDiscountGateway = {
    // Regles de reduction personnel. Secours hors ligne (secretaire
    // uniquement, meme garde que CaisseGateway.searchProducts) : un autre
    // role hors ligne voit l'erreur reseau, jamais une liste vide venant
    // d'une table locale jamais synchronisee pour lui.
    async list() {
        try {
            const resp = await api.get('/staff-discount-rules');
            return resp.data;
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['secretaire'])) {
                return getStaffDiscountRulesLocal();
            }
            throw err;
        }
    },

    async save(category, payload) {
        const resp = await api.put(`/staff-discount-rules/${category}`, payload);
        return resp.data;
    },

    async lookupStaff({ q, onlyStaff, limit } = {}) {
        const params = {};
        if (q) params.q = q;
        if (onlyStaff !== undefined && onlyStaff !== null) params.only_staff = onlyStaff;
        if (limit) params.limit = limit;
        const resp = await api.get('/patients/staff-lookup', { params });
        return resp.data;
    },

    async setStaff(patientId, isStaff) {
        const resp = await api.put(`/patients/${patientId}/staff`, { is_staff: isStaff });
        return resp.data;
    },
};
