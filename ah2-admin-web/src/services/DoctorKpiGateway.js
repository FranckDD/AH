import api from '@/services/api';

// doctor_id est volontairement omis sur chaque appel : le backend le
// resout depuis l'utilisateur authentifie (AppointmentController /
// MedicalRecordController._resolve_doctor), donc ces endpoints renvoient
// toujours "mes" statistiques, jamais celles d'un autre medecin.
export const DoctorKpiGateway = {
    async fetchAppointmentsTotal(params) {
        return api.get('/appointments/kpi/total', { params });
    },

    async fetchAppointmentsByStatus(params) {
        return api.get('/appointments/kpi/count_by_status', { params });
    },

    async fetchDistinctPatients(params) {
        return api.get('/appointments/kpi/distinct_patients', { params });
    },

    // Pas de start/end ici : repositories/medical_repo.py filtre sur
    // consultation_date, qui n'est jamais reellement persistee cote
    // backend (registre H1, SUIVI-AVANCEMENT.md) - un filtre de date
    // renverrait systematiquement 0. On affiche donc un cumul global.
    async fetchMedicalRecordsCount() {
        return api.get('/medical_records/kpi/count_records');
    },

    async fetchConsultationDistribution() {
        return api.get('/medical_records/kpi/consultation_distribution');
    },
};
