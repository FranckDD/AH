// src/services/HospitalizationGateway.js
import api from '@/services/api';

export const HospitalizationGateway = {
    async admit(patientId, admissionReason) {
        return api.post('/hospitalizations/', {
            patient_id: patientId,
            admission_reason: admissionReason || null,
        });
    },

    async addStatusUpdate(hospitalizationId, statusValue, note) {
        return api.post(`/hospitalizations/${hospitalizationId}/status`, {
            status: statusValue,
            note: note || null,
        });
    },

    async discharge(hospitalizationId, dischargeDisposition, dischargeNote) {
        return api.post(`/hospitalizations/${hospitalizationId}/discharge`, {
            discharge_disposition: dischargeDisposition,
            discharge_note: dischargeNote || null,
        });
    },

    async fetchCurrent() {
        return api.get('/hospitalizations/current');
    },

    async fetchPatientHistory(patientId) {
        return api.get(`/hospitalizations/patient/${patientId}`);
    },

    async fetchKpiCount() {
        return api.get('/hospitalizations/kpi/count_current');
    },

    // responseType 'blob' : voir CaisseGateway/CaisseList.vue::downloadInvoice
    // pour le motif exact (meme decodage d'erreur cote appelant, err.response
    // .data arrive en Blob, jamais un objet JSON directement exploitable).
    async downloadDischargeLetter(hospitalizationId) {
        return api.get(`/hospitalizations/${hospitalizationId}/discharge-letter`, { responseType: 'blob' });
    },
};
