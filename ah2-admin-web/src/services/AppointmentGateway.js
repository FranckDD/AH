import api from '@/services/api';

// Nettoie les paramètres vides avant envoi (évite un 422 sur des query
// params vides) - meme convention que FinanceGateway.js.
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

export const AppointmentGateway = {

    async fetchAppointments(params) {
        const rawQuery = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            search: params.searchQuery,
            date_from: params.dateFrom,
            date_to: params.dateTo,
        };
        return api.get('/appointments/', { params: cleanParams(rawQuery) });
    },

    async getSpecialties() {
        return api.get('/appointments/specialties');
    },

    async createAppointment(data) {
        const payload = {
            patient_id: data.patientId,
            specialty: data.specialty || null,
            appointment_date: data.appointmentDate,
            appointment_time: data.appointmentTime,
            reason: data.reason || '',
            uuid: data.uuid || null,
        };
        return api.post('/appointments/', payload);
    },

    async updateAppointment(appointmentId, data) {
        const payload = {
            patient_id: data.patientId,
            specialty: data.specialty || null,
            appointment_date: data.appointmentDate,
            appointment_time: data.appointmentTime,
            reason: data.reason || '',
        };
        return api.put(`/appointments/${appointmentId}`, payload);
    },

    // Pas de cancel_status côté client : le backend fixe status="cancelled"
    // lui-même (endpoint dédié), rien à lui passer.
    async cancelAppointment(appointmentId) {
        return api.post(`/appointments/${appointmentId}/cancel`);
    },

    async completeAppointment(appointmentId) {
        return api.post(`/appointments/${appointmentId}/complete`);
    },

    // Volontairement PAS de acceptAppointment() ici : voir registre C4
    // (docs/superpowers/SUIVI-AVANCEMENT.md) - /accept n'a aucune
    // semantique reelle sur ce backend aujourd'hui (ecrit "pending",
    // deja la valeur par defaut - et regresserait un RDV completed/
    // cancelled vers pending si on l'appelait dessus). A ajouter ici
    // seulement si/quand ce ticket est tranche par le metier.
};
