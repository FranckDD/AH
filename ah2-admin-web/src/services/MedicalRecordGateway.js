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

export const MedicalRecordGateway = {

    async fetchMedicalRecords(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            search: params.searchQuery,
            motif_code: params.motifCode,
            severity: params.severity,
            // Contrairement au module Prescription, repositories/medical_repo.py
            // (lignes 38-58) supporte des bornes de date independantes
            // (elif date_from / elif date_to) - pas besoin d'exiger les deux.
            // cleanParams() ci-dessous retire automatiquement celle(s) qui
            // sont vides.
            date_from: params.dateFrom,
            date_to: params.dateTo,
        };

        return api.get('/medical_records/', { params: cleanParams(rawQuery) });
    },

    async fetchMotifs() {
        return api.get('/medical_records/motifs');
    },

    async createMedicalRecord(data) {
        const payload = {
            patient_id: data.patientId || null,
            patient_uuid: data.patientUuid || null,
            consultation_date: data.consultationDate,
            motif_code: data.motifCode,
            appointment_id: data.appointmentId || null,
            marital_status: data.maritalStatus || null,
            severity: data.severity || null,
            bp: data.bp || null,
            temperature: data.temperature,
            weight: data.weight,
            height: data.height,
            medical_history: data.medicalHistory || null,
            allergies: data.allergies || null,
            symptoms: data.symptoms || null,
            diagnosis: data.diagnosis || null,
            treatment: data.treatment || null,
            notes: data.notes || null,
            needs_doctor_review: !!data.needsDoctorReview,
            assigned_doctor_id: data.assignedDoctorId || null,
            uuid: data.uuid || null,
        };
        return api.post('/medical_records/', payload);
    },

    async updateMedicalRecord(recordId, data) {
        const payload = {
            patient_id: data.patientId,
            consultation_date: data.consultationDate,
            motif_code: data.motifCode,
            marital_status: data.maritalStatus || null,
            severity: data.severity || null,
            bp: data.bp || null,
            temperature: data.temperature,
            weight: data.weight,
            height: data.height,
            medical_history: data.medicalHistory || null,
            allergies: data.allergies || null,
            symptoms: data.symptoms || null,
            diagnosis: data.diagnosis || null,
            treatment: data.treatment || null,
            notes: data.notes || null,
        };
        return api.put(`/medical_records/${recordId}`, payload);
    },

    async deleteMedicalRecord(recordId) {
        return api.delete(`/medical_records/${recordId}`);
    },
};
