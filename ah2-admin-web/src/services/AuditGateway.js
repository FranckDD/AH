// Fichier : src/services/AuditGateway.js

import api from '@/services/api'; // Votre client axios configuré

const cleanParams = (params) => {
    // Supprime les valeurs nulles, vides ou indéfinies pour des URLs plus propres
    const cleaned = {};
    for (const key in params) {
        if (params[key] !== null && params[key] !== '' && params[key] !== undefined) {
            // Pour les dates, on s'assure qu'elles sont dans un format string ISO standard
            if (params[key] instanceof Date) {
                 cleaned[key] = params[key].toISOString().split('T')[0]; // YYYY-MM-DD
            } else {
                 cleaned[key] = params[key];
            }
        }
    }
    return cleaned;
};

export const AuditGateway = {
    
    async fetchAccessLogs(params) {
        // Mappe les clés du store Vue aux clés attendues par l'API FastAPI
        const query = {
            page: params.page,
            per_page: params.per_page,
            user_id: params.userId,
            action_type: params.actionType, // LOGIN / LOGOUT / LOGIN_FAILED
            date_from: params.dateFrom,
            date_to: params.dateTo
        };
        // L'API est `/audit/access`
        return api.get('/audit/access', { params: cleanParams(query) });
    },

    async fetchActionLogs(params) {
        const query = {
            page: params.page,
            per_page: params.per_page,
            user_id: params.userId,
            resource_type: params.resourceType, // PATIENT, PRESCRIPTION, CAISSE, etc.
            action_type: params.actionType, // CREATE, UPDATE, DELETE, DISPENSE, etc.
            date_from: params.dateFrom,
            date_to: params.dateTo
        };
        // L'API est `/audit/actions`
        return api.get('/audit/actions', { params: cleanParams(query) });
    }
};