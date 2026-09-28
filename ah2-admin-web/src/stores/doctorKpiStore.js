import { defineStore } from 'pinia';
import { ref } from 'vue';
import { DoctorKpiGateway } from '@/services/DoctorKpiGateway';

export const useDoctorKpiStore = defineStore('doctorKpi', () => {

    const isLoading = ref(false);

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
    });

    async function fetchKpiData() {
        isLoading.value = true;
        try {
            const dateParams = {
                start: filters.value.startDate,
                end: filters.value.endDate,
            };

            const [totalRes, statusRes, patientsRes, recordsRes, distribRes] = await Promise.all([
                DoctorKpiGateway.fetchAppointmentsTotal(dateParams),
                DoctorKpiGateway.fetchAppointmentsByStatus(dateParams),
                DoctorKpiGateway.fetchDistinctPatients(dateParams),
                DoctorKpiGateway.fetchMedicalRecordsCount(),
                DoctorKpiGateway.fetchConsultationDistribution(),
            ]);

            stats.value.totalAppointments = totalRes.data?.total || 0;
            stats.value.countByStatus = statusRes.data || {};
            stats.value.distinctPatients = patientsRes.data?.distinct_patients || 0;
            stats.value.medicalRecordsCount = recordsRes.data?.count || 0;
            stats.value.consultationDistribution = distribRes.data || {};
        } catch (error) {
            console.error('Erreur chargement KPI medecin:', error);
        } finally {
            isLoading.value = false;
        }
    }

    function setDates(start, end) {
        filters.value.startDate = start;
        filters.value.endDate = end;
        fetchKpiData();
    }

    return { isLoading, filters, stats, fetchKpiData, setDates };
});
