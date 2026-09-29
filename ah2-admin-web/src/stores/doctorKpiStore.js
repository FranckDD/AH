import { defineStore } from 'pinia';
import { ref } from 'vue';
import { DoctorKpiGateway } from '@/services/DoctorKpiGateway';
import api from '@/services/api';

export const useDoctorKpiStore = defineStore('doctorKpi', () => {

    const isLoading = ref(false);
    const error = ref(null);

    const today = new Date();
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);

    const filters = ref({
        startDate: monthStart.toISOString().split('T')[0],
        endDate: today.toISOString().split('T')[0],
    });

    const stats = ref({
        totalAppointments: 0,
        distinctPatients: 0,
        countByStatus: {},
        medicalRecordsCount: 0,
        consultationDistribution: {},
        prescriptionsCount: 0,
        hospitalizationsCurrentCount: 0,
    });

    const pendingReview = ref([]);
    const claimError = ref(null);

    async function fetchPendingReview() {
        try {
            const resp = await api.get('/medical_records/pending-review');
            pendingReview.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement patients en attente:', err);
        }
    }

    async function claimRecord(recordId) {
        claimError.value = null;
        let success = true;
        try {
            await api.post(`/medical_records/${recordId}/claim`);
        } catch (err) {
            // Sur echec (ex: 409 si un autre medecin vient de le prendre en
            // charge, ou 403), on rafraichit quand meme la liste : c'est
            // l'issue la plus informative pour l'utilisateur (la ligne
            // perimee disparait si quelqu'un d'autre l'a prise).
            claimError.value = err.response?.data?.detail || 'Une erreur est survenue.';
            success = false;
        }
        await fetchPendingReview();
        return success;
    }

    async function fetchKpiData() {
        isLoading.value = true;
        error.value = null;
        try {
            const resp = await DoctorKpiGateway.fetchDashboard(filters.value.startDate, filters.value.endDate);
            const data = resp.data || {};
            stats.value.totalAppointments = data.total_appointments || 0;
            stats.value.countByStatus = data.count_by_status || {};
            stats.value.distinctPatients = data.distinct_patients || 0;
            stats.value.medicalRecordsCount = data.medical_records_count || 0;
            stats.value.consultationDistribution = data.consultation_distribution || {};
            stats.value.prescriptionsCount = data.prescriptions_count || 0;
            stats.value.hospitalizationsCurrentCount = data.hospitalizations_current_count || 0;
        } catch (err) {
            console.error('Erreur chargement tableau de bord medecin:', err);
            error.value = "Impossible de charger le tableau de bord.";
        } finally {
            isLoading.value = false;
        }
        await fetchPendingReview();
    }

    function setDates(start, end) {
        filters.value.startDate = start;
        filters.value.endDate = end;
        fetchKpiData();
    }

    return { isLoading, error, filters, stats, pendingReview, claimError, fetchKpiData, setDates, fetchPendingReview, claimRecord };
});
