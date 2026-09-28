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

    // Correction 2026-09-28 : consultation_date EST bien persistee a la
    // creation (LOCALTIMESTAMP cote procedure stockee - seule une
    // modification ulterieure est un no-op, registre H1 dans
    // SUIVI-AVANCEMENT.md, sans rapport avec ce filtre), donc un filtre de
    // periode fonctionne. Le vrai bug qui faisait renvoyer 0 dans tous les
    // cas etait ailleurs : created_by n'etait jamais renseigne du tout a la
    // creation (voir controller/medical_controller.py::create_record) -
    // corrige separement le meme jour.
    async fetchMedicalRecordsCount(params) {
        return api.get('/medical_records/kpi/count_records', { params });
    },

    async fetchConsultationDistribution(params) {
        return api.get('/medical_records/kpi/consultation_distribution', { params });
    },
};
