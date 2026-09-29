import api from '@/services/api';

// Un seul appel reseau desormais : le backend compose les 4 sources
// (RDV/dossiers medicaux/prescriptions/hospitalisations) en une seule
// reponse, avec degradation par carte si une source echoue cote serveur.
export const DoctorKpiGateway = {
    async fetchDashboard(start, end) {
        return api.get('/doctor-dashboard/kpi', { params: { start, end } });
    },
};
