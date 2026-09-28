import api from '@/services/api';

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

export const ConsultationGateway = {

    async fetchConsultations(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.perPage || 20,
            search: params.search,
        };
        return api.get('/cs/', { params: cleanParams(rawQuery) });
    },

    async fetchPrayerBookTypes() {
        return api.get('/cs/prayer-book-types');
    },

    async createConsultation(data) {
        const payload = {
            patient_id: data.patientId,
            type_consultation: data.typeConsultation,
            presc_generic: data.prescGeneric || [],
            presc_med_spirituel: data.prescMedSpirituel || [],
            mp_type: data.mpType || null,
            psaume: data.psaume || null,
            notes: data.notes || null,
            fr_registered_at: data.frRegisteredAt || null,
            fr_appointment_at: data.frAppointmentAt || null,
            fr_amount_paid: data.frAmountPaid !== '' && data.frAmountPaid !== null && data.frAmountPaid !== undefined ? data.frAmountPaid : null,
            fr_observation: data.frObservation || null,
        };
        if (data.consultationDate) {
            payload.consultation_date = data.consultationDate;
        }
        return api.post('/cs/', payload);
    },

    async updateConsultation(consultationId, data) {
        const payload = {
            patient_id: data.patientId,
            type_consultation: data.typeConsultation,
            presc_generic: data.prescGeneric || [],
            presc_med_spirituel: data.prescMedSpirituel || [],
            mp_type: data.mpType || null,
            psaume: data.psaume || null,
            notes: data.notes || null,
            fr_registered_at: data.frRegisteredAt || null,
            fr_appointment_at: data.frAppointmentAt || null,
            fr_amount_paid: data.frAmountPaid !== '' && data.frAmountPaid !== null && data.frAmountPaid !== undefined ? data.frAmountPaid : null,
            fr_observation: data.frObservation || null,
        };
        if (data.consultationDate) {
            payload.consultation_date = data.consultationDate;
        }
        return api.put(`/cs/${consultationId}`, payload);
    },

    async deleteConsultation(consultationId) {
        return api.delete(`/cs/${consultationId}`);
    },
};
