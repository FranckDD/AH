// Passerelle du catalogue du laboratoire (routes /labo/catalogue/*). En ligne seulement : aucune lecture ni
// ecriture locale, aucun secours hors ligne (une modification du catalogue doit etre tracee et immediate).
// Aucune charge utile de cette passerelle ne porte de prix (le serveur le refuse en 422).
import api from './api';

const BASE = '/labo/catalogue';

export const LabCatalogueGateway = {
    // Examens avec parametres et plages ; inactifs inclus pour l'ecran de gestion.
    async listExams(includeInactive = true) {
        const res = await api.get(`${BASE}/exams`, { params: { include_inactive: includeInactive } });
        return res.data;
    },

    // --- examens
    createExam(payload) { return api.post(`${BASE}/exams`, payload); },
    updateExam(id, payload) { return api.put(`${BASE}/exams/${id}`, payload); },
    deleteExam(id) { return api.delete(`${BASE}/exams/${id}`); },
    orderExams(ids) { return api.put(`${BASE}/exams/order`, { ids }); },
    moveExam(id, position) { return api.put(`${BASE}/exams/${id}/order`, { position }); },

    // --- parametres
    createParam(payload) { return api.post(`${BASE}/parameters`, payload); },
    updateParam(id, payload) { return api.put(`${BASE}/parameters/${id}`, payload); },
    deleteParam(id) { return api.delete(`${BASE}/parameters/${id}`); },
    moveParam(id, position) { return api.put(`${BASE}/parameters/${id}/order`, { position }); },
    orderParams(examId, ids) { return api.put(`${BASE}/exams/${examId}/parameters/order`, { ids }); },

    // --- plages
    createRange(payload) { return api.post(`${BASE}/ranges`, payload); },
    updateRange(id, payload) { return api.put(`${BASE}/ranges/${id}`, payload); },
    deleteRange(id) { return api.delete(`${BASE}/ranges/${id}`); },
};
