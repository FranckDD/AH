import api from '@/services/api';

// Nettoie les paramètres vides avant envoi (évite un 422 sur des query
// params vides) - meme convention que AppointmentGateway.js/FinanceGateway.js.
const cleanParams = (params) => {
    const cleaned = {};
    for (const key in params) {
        const value = params[key];
        if (value !== null && value !== undefined && value !== '') {
            cleaned[key] = value;
        }
    }
    return cleaned;
};

export const PrescriptionGateway = {

    async fetchPrescriptions(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            search: params.searchQuery,
            date_from: params.dateFrom,
            date_to: params.dateTo,
        };
        return api.get('/prescriptions/', { params: cleanParams(rawQuery) });
    },

    // Catalogue reel d'examens, deja accessible a medecin/nurse (voir
    // lab_endpoints.py:62-69, "ACCES ELARGI... pour prescrire") - pas de
    // liste codee en dur cote web.
    async fetchExamTypes() {
        return api.get('/labo/exams');
    },

    async createPrescription(data) {
        const payload = {
            patient_id: data.patientId || null,
            patient_uuid: data.patientUuid || null,
            medical_record_id: data.medicalRecordId || null,
            medical_record_uuid: data.medicalRecordUuid || null,
            is_lab_order: data.isLabOrder,
            medication: data.medication || null,
            dosage: data.dosage || null,
            frequency: data.frequency || null,
            duration: data.duration || null,
            start_date: data.startDate,
            end_date: data.endDate || null,
            notes: data.notes || null,
            lab_exams_list: data.labExamsList || [],
            uuid: data.uuid || null,
        };
        return api.post('/prescriptions/', payload);
    },

    async updatePrescription(prescriptionId, data) {
        const payload = {
            patient_id: data.patientId,
            medical_record_id: data.medicalRecordId || null,
            is_lab_order: data.isLabOrder,
            medication: data.medication || null,
            dosage: data.dosage || null,
            frequency: data.frequency || null,
            duration: data.duration || null,
            start_date: data.startDate,
            end_date: data.endDate || null,
            notes: data.notes || null,
            lab_exams_list: data.labExamsList || [],
        };
        return api.put(`/prescriptions/${prescriptionId}`, payload);
    },

    async deletePrescription(prescriptionId) {
        return api.delete(`/prescriptions/${prescriptionId}`);
    },
};
