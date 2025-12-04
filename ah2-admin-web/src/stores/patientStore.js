// src/stores/patientStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api'; // 👈 Utilise notre client Axios

export const usePatientStore = defineStore('patient', () => {
    
    // État
    const patientData = ref({
        data: [],
        total: 0,
        page: 1,
        per_page: 10,
        total_pages: 1
    });
    
    const isLoading = ref(false);
    const error = ref(null);

    // Filtres
    const filters = ref({
        search: '',
        type: 'ALL', // 'ALL', 'CLINIQUE', 'TOXICO', 'SPIRITUEL'
        page: 1
    });

    // --- ACTIONS ---

    async function fetchPatients() {
        isLoading.value = true;
        error.value = null;

        try {
            // 1. Préparation des paramètres pour FastAPI
            const params = {
                page: filters.value.page,
                per_page: patientData.value.per_page,
            };
            if (filters.value.search) {
                params.search = filters.value.search;
            }

            // 2. 🟢 APPEL API RÉEL
            const response = await api.get('/patients/', { params });
            
            // FastAPI renvoie une liste directe [{}, {}]
            const rawList = response.data; 

            // 3. MAPPING : Conversion des données Backend -> Frontend
            const mappedList = rawList.map(p => {
                // Déterminer le "Type" principal pour l'affichage du badge
                let displayType = 'AUTRE';
                if (p.is_clinical) displayType = 'CLINIQUE';
                else if (p.is_toxicology) displayType = 'TOXICO';
                else if (p.is_spiritual) displayType = 'SPIRITUEL';

                return {
                    id: p.patient_id,
                    code: p.code_patient,
                    firstName: p.first_name,
                    lastName: p.last_name,
                    admissionDate: p.birth_date, // Ou created_at si disponible dans votre réponse API
                    phone: p.contact_phone,
                    type: displayType, 
                    status: 'Actif', // Le backend n'a pas encore de colonne status "hospitalisé/etc", on met par défaut
                    // On garde les drapeaux bruts si besoin
                    flags: {
                        is_clinical: p.is_clinical,
                        is_toxicology: p.is_toxicology,
                        is_spiritual: p.is_spiritual
                    }
                };
            });

            // 4. FILTRAGE CLIENT (TEMPORAIRE)
            // L'Admin reçoit TOUT du backend. Pour que les onglets fonctionnent visuellement,
            // on filtre la liste reçue.
            // (Note: Pour une optimisation parfaite, le backend devrait accepter un paramètre `?service_type=...`)
            let finalData = mappedList;
            if (filters.value.type !== 'ALL') {
                finalData = mappedList.filter(p => p.type === filters.value.type);
            }

            // Mise à jour du state
            patientData.value.data = finalData;
            patientData.value.page = filters.value.page;
            
            // Estimation de la pagination (car le backend ne renvoie pas encore le total)
            // Si on a reçu autant d'éléments que per_page, on suppose qu'il y en a d'autres
            patientData.value.total = rawList.length >= patientData.value.per_page 
                ? (filters.value.page * patientData.value.per_page) + 1 
                : rawList.length;
            
            // Calcul simple des pages
            patientData.value.total_pages = rawList.length >= patientData.value.per_page 
                ? filters.value.page + 1 
                : filters.value.page;

        } catch (err) {
            console.error("Erreur fetchPatients:", err);
            error.value = "Erreur de connexion au serveur.";
            patientData.value.data = [];
        } finally {
            isLoading.value = false;
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

    // Ajout via API
    async function addPatient(patientData) {
        isLoading.value = true;
        try {
            // Mapping Frontend -> Backend Payload
            const payload = {
                first_name: patientData.firstName,
                last_name: patientData.lastName,
                birth_date: patientData.birth_date || "2000-01-01", // Valeur par défaut si manquant
                // ... autres champs requis par votre schéma PatientCreate
                // La gestion des drapeaux est faite par l'API selon le rôle, mais on peut les passer si l'UI le permet
            };
            
            await api.post('/patients/', payload);
            await fetchPatients(); // Rafraîchir la liste
        } catch (err) {
            console.error("Erreur addPatient:", err);
            alert("Erreur lors de la création: " + (err.response?.data?.detail || err.message));
        } finally {
            isLoading.value = false;
        }
    }

    // Suppression via API
    async function deletePatient(id) {
        try {
            await api.delete(`/patients/${id}`);
            // Rafraîchissement optimiste ou re-fetch
            patientData.value.data = patientData.value.data.filter(p => p.id !== id);
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
        // Bouton "Suivant" actif si on n'est pas à la fin
        hasNext: patientData.value.data.length > 0 && patientData.value.total > (filters.value.page * patientData.value.per_page) 
    }));

    // Compteurs (Mockés pour l'instant ou calculés sur la page courante)
    const counts = computed(() => {
        // Idéalement, il faut un endpoint API /patients/kpi/counts
        // Ici on compte juste ce qu'on voit sur la page courante
        const d = patientData.value.data;
        return {
            ALL: d.length, 
            CLINIQUE: d.filter(p => p.type === 'CLINIQUE').length,
            TOXICO: d.filter(p => p.type === 'TOXICO').length,
            SPIRITUEL: d.filter(p => p.type === 'SPIRITUEL').length,
        };
    });

    return { 
        patients, isLoading, error, pagination, filters, counts,
        fetchPatients, addPatient, deletePatient, setPage, setFilters 
    };
});