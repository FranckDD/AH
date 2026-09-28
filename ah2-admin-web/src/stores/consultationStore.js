import { defineStore } from 'pinia';
import { ref } from 'vue';
import { ConsultationGateway } from '@/services/ConsultationGateway';

export const useConsultationStore = defineStore('consultation', () => {

    const isLoading = ref(false);
    const consultations = ref([]);
    const prayerBookTypes = ref([]);
    // GET /cs/ renvoie desormais {data, total, page, per_page, total_pages}
    // (pagination toujours en memoire cote endpoint). On continue de
    // deduire "page suivante possible" du remplissage de la page recue
    // plutot que de total_pages, pour rester coherent avec l'existant.
    const hasNextPage = ref(false);

    const filters = ref({
        search: '',
    });

    const pagination = ref({
        page: 1,
        perPage: 20,
    });

    async function fetchConsultations() {
        isLoading.value = true;
        try {
            const res = await ConsultationGateway.fetchConsultations({
                page: pagination.value.page,
                perPage: pagination.value.perPage,
                search: filters.value.search,
            });
            consultations.value = res.data?.data || [];
            hasNextPage.value = consultations.value.length === pagination.value.perPage;
        } catch (error) {
            console.error('Erreur chargement consultations:', error);
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchPrayerBookTypes() {
        try {
            const res = await ConsultationGateway.fetchPrayerBookTypes();
            prayerBookTypes.value = res.data || [];
        } catch (error) {
            console.error('Erreur chargement types de livres de priere:', error);
        }
    }

    async function createConsultation(data) {
        await ConsultationGateway.createConsultation(data);
        await fetchConsultations();
    }

    async function updateConsultation(consultationId, data) {
        await ConsultationGateway.updateConsultation(consultationId, data);
        await fetchConsultations();
    }

    async function deleteConsultation(consultationId) {
        await ConsultationGateway.deleteConsultation(consultationId);
        await fetchConsultations();
    }

    function setPage(page) {
        pagination.value.page = page;
        fetchConsultations();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters };
        pagination.value.page = 1;
        fetchConsultations();
    }

    return {
        consultations, prayerBookTypes, isLoading, filters, pagination, hasNextPage,
        fetchConsultations, fetchPrayerBookTypes,
        createConsultation, updateConsultation, deleteConsultation,
        setPage, setFilters,
    };
});
