// src/stores/patientStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api'; 

export const usePatientStore = defineStore('patient', () => {
    
    // --- STATE ---
    
    // Données de la liste (Change selon l'onglet)
    const patientData = ref({
        data: [],
        total: 0,
        page: 1,
        per_page: 10,
        total_pages: 1
    });
    
    // 🟢 NOUVEAU : Compteurs globaux (Restent fixes peu importe l'onglet)
    const globalCounts = ref({
        total_all: 0,
        total_clinical: 0,
        total_toxicology: 0,
        total_spiritual: 0
    });
    
    const isLoading = ref(false);
    const error = ref(null);

    // Filtres
    const filters = ref({
        search: '',
        type: 'ALL', 
        page: 1
    });

    // --- ACTIONS ---

    // 1. Récupérer les patients (Liste paginée)
    async function fetchPatients() {
        isLoading.value = true;
        error.value = null;

        try {
            const params = {
                page: filters.value.page,
                per_page: patientData.value.per_page,
            };
            
            if (filters.value.search) {
                params.search = filters.value.search;
            }

            // Sélection dynamique de l'endpoint
            let endpoint = '/patients/'; 
            if (filters.value.type === 'CLINIQUE') endpoint = '/patients/clinical';
            else if (filters.value.type === 'TOXICO') endpoint = '/patients/toxicology';
            else if (filters.value.type === 'SPIRITUEL') endpoint = '/patients/spiritual/list'; 

            const response = await api.get(endpoint, { params });
            const resData = response.data;

            // Gestion réponse (structure paginée vs liste brute)
            const rawList = Array.isArray(resData) ? resData : (resData.data || []);

            // Mapping
            const mappedList = rawList.map(p => {
                let displayType = 'AUTRE';
                if (p.is_clinical) displayType = 'CLINIQUE';
                else if (p.is_toxicology) displayType = 'TOXICO';
                else if (p.is_spiritual) displayType = 'SPIRITUEL';

                return {
                    id: p.id || p.patient_id,
                    code: p.code_patient,
                    firstName: p.first_name,
                    lastName: p.last_name,
                    admissionDate: p.birth_date,
                    phone: p.contact_phone,
                    type: displayType, 
                    flags: {
                        is_clinical: p.is_clinical,
                        is_toxicology: p.is_toxicology,
                        is_spiritual: p.is_spiritual
                    }
                };
            });

            patientData.value.data = mappedList;

            if (!Array.isArray(resData) && resData.total !== undefined) {
                patientData.value.page = resData.page;
                patientData.value.per_page = resData.per_page;
                patientData.value.total = resData.total;
                patientData.value.total_pages = resData.total_pages;
            } else {
                patientData.value.total = rawList.length;
                patientData.value.total_pages = 1; 
            }

        } catch (err) {
            console.error("Erreur fetchPatients:", err);
            error.value = "Erreur de connexion au serveur.";
            patientData.value.data = [];
            patientData.value.total = 0;
        } finally {
            isLoading.value = false;
        }
    }

    // 🟢 2. NOUVELLE ACTION : Récupérer les compteurs globaux
    async function fetchCounts() {
        try {
            // Appelle le nouvel endpoint backend
            const response = await api.get('/patients/counts/global');
            globalCounts.value = response.data;
        } catch (err) {
            console.error("Erreur chargement des compteurs:", err);
            // On ne bloque pas l'UI, on laisse les compteurs à 0 ou valeurs précédentes
        }
    }

    function setPage(newPage) {
        filters.value.page = newPage;
        fetchPatients();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchPatients();
    }

    async function addPatient(patientData) {
        isLoading.value = true;
        try {
            const payload = {
                first_name: patientData.firstName,
                last_name: patientData.lastName,
                birth_date: patientData.birth_date || "2000-01-01",
                // ... mapping ...
            };
            
            await api.post('/patients/', payload);
            
            // 🟢 Rafraîchir la liste ET les compteurs après un ajout
            await Promise.all([
                fetchPatients(),
                fetchCounts()
            ]);
        } catch (err) {
            console.error("Erreur addPatient:", err);
            alert("Erreur lors de la création: " + (err.response?.data?.detail || err.message));
        } finally {
            isLoading.value = false;
        }
    }

    async function deletePatient(id) {
        try {
            await api.delete(`/patients/${id}`);
            
            // Optimiste : on retire de la liste locale
            patientData.value.data = patientData.value.data.filter(p => p.id !== id);
            
            // 🟢 Rafraîchir les compteurs réels
            fetchCounts();
            // Optionnel : re-fetchPatients() si on veut être sûr de la pagination
        } catch (err) {
            console.error("Erreur deletePatient:", err);
            alert("Impossible de supprimer : " + (err.response?.data?.detail || err.message));
        }
    }

    // --- GETTERS ---
    const patients = computed(() => patientData.value.data);
    
    const pagination = computed(() => ({
        page: patientData.value.page,
        per_page: patientData.value.per_page,
        total: patientData.value.total,
        total_pages: patientData.value.total_pages,
        hasNext: patientData.value.page < patientData.value.total_pages
    }));

    // 🟢 GETTER MIS À JOUR : Utilise maintenant les vrais compteurs DB
    const counts = computed(() => {
        return {
            ALL: globalCounts.value.total_all, 
            CLINIQUE: globalCounts.value.total_clinical,
            TOXICO: globalCounts.value.total_toxicology,
            SPIRITUEL: globalCounts.value.total_spiritual,
        };
    });

    return { 
        patients, isLoading, error, pagination, filters, 
        counts, globalCounts, // 👈 Exporté pour l'UI
        fetchPatients, fetchCounts, addPatient, deletePatient, setPage, setFilters 
    };
});