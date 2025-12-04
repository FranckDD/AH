// Fichier: stores/toxicoStore.js

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { ToxicoGateway } from '@/services/ToxicoGateway'; // Assurez-vous que le chemin est correct

export const useToxicoStore = defineStore('toxico', () => {
    // --- STATE ---
    const patients = ref([]);
    const totalItems = ref(0);
    const isLoading = ref(false);
    const psychologists = ref([]); // Liste des psys pour les selects
    
    // ✅ NOUVEL ÉTAT : Pour stocker le compte des admissions du mois venant du backend
    const monthlyAdmissionsCount = ref(0); 
    
    // Pagination et Filtres actuels
    const filters = ref({
        page: 1,
        per_page: 20,
        search: '',
        phase: null
    });

    // --- ACTIONS ---

    // 1. Charger la liste principale
    async function fetchToxicoPatients() {
        isLoading.value = true;
        try {
            const params = {
                page: filters.value.page,
                per_page: filters.value.per_page,
                search: filters.value.search,
                phase: filters.value.phase
            };
            
            const response = await ToxicoGateway.listPatients(params);
            
            // Le backend renvoie { data: [...], total: ... }
            patients.value = response.data.data || [];
            totalItems.value = response.data.total || 0;
            
        } catch (error) {
            console.error("Erreur chargement patients toxico:", error);
        } finally {
            isLoading.value = false;
        }
    }

    // 2. Charger les psychologues (pour la modale d'admission)
    async function fetchPsychologists() {
        if (psychologists.value.length > 0) return; // Cache simple
        try {
            const response = await ToxicoGateway.getPsychologists();
            psychologists.value = response.data;
        } catch (error) {
            console.error("Erreur chargement psychologues:", error);
        }
    }

    // 3. Admission (Création)
    async function addPatient(admissionData) {
        isLoading.value = true;
        try {
            console.log("📦 [Store] Envoi Admission JSON:", JSON.stringify(admissionData));

            await ToxicoGateway.admitPatient(admissionData);
            
            // Rafraîchir la liste et les stats après succès
            await fetchToxicoPatients();
            await fetchDashboardStats(); // ✅ Mise à jour des stats après une admission
            return true; // Succès
        } catch (error) {
            if (error.response) {
                console.error("❌ Erreur API Admission:", error.response.status, error.response.data);
            } else {
                console.error("❌ Erreur Réseau/Client:", error);
            }
            throw error; 
        } finally {
            isLoading.value = false;
        }
    }

    // 4. Évaluation
    async function submitEvaluation(evalData) {
        isLoading.value = true;
        try {
            await ToxicoGateway.submitEvaluation(evalData);
            
            // Rafraîchir la liste pour voir les changements de phase/rechutes
            await fetchToxicoPatients(); 
            return true;
        } catch (error) {
            console.error("Erreur évaluation:", error);
            throw error;
        } finally {
            isLoading.value = false;
        }
    }
    
    // 5. Clôture / Sortie
    async function dischargePatient(dossierId) {
        try {
            await ToxicoGateway.dischargePatient(dossierId);
            await fetchToxicoPatients();
            await fetchDashboardStats(); // ✅ Mise à jour des stats si le décompte change
        } catch (error) {
            console.error("Erreur clôture:", error);
            throw error;
        }
    }
    
    // 6. Récupérer les détails d'un patient spécifique (pour la modale Dossier)
    async function getPatientDetails(patientId) {
        isLoading.value = true;
        try {
            const response = await ToxicoGateway.getPatientDetails(patientId);
            return response.data;
        } catch (error) {
            console.error("Erreur détails patient:", error);
            throw error;
        } finally {
            isLoading.value = false;
        }
    }

    // 7. Charger les statistiques du tableau de bord (Endpoint dédié)
    async function fetchDashboardStats() {
        try {
            const response = await ToxicoGateway.getDashboardStats(); 
            
            if (response && response.data && response.data.currentMonthAdmissions !== undefined) {
                monthlyAdmissionsCount.value = response.data.currentMonthAdmissions;
            } else {
                console.warn("Réponse des stats inattendue ou manquante.");
                monthlyAdmissionsCount.value = 0;
            }
        } catch (error) {
            console.error("Erreur chargement stats tableau de bord:", error);
            monthlyAdmissionsCount.value = 0; // Réinitialiser en cas d'échec
            throw error;
        }
    }

    // --- ACTIONS UI (Pagination) ---
    function setPage(page) {
        filters.value.page = page;
        fetchToxicoPatients();
    }
    
    function setSearch(query) {
        filters.value.search = query;
        filters.value.page = 1; // Reset page on search
        fetchToxicoPatients();
    }

    // --- COMPUTED STATS ---
    
    const totalActive = computed(() => totalItems.value); // Le vrai total venant du backend

    const statsByPhase = computed(() => {
        const counts = { 1: 0, 2: 0, 3: 0, 4: 0 };
        patients.value.forEach(p => {
            if (counts[p.currentPhase] !== undefined) counts[p.currentPhase]++;
        });
        return counts;
    });

    const statsBySubstance = computed(() => {
        const counts = {};
        patients.value.forEach(p => {
            const sub = p.substance || 'Autre';
            counts[sub] = (counts[sub] || 0) + 1;
        });
        return counts;
    });

    const relapseRate = computed(() => {
        if (patients.value.length === 0) return 0;
        const patientsWithRelapse = patients.value.filter(p => p.relapseCount > 0).length;
        // Ce calcul n'est précis que sur la page courante, à noter.
        return Math.round((patientsWithRelapse / patients.value.length) * 100); 
    });

    const statsByPsy = computed(() => {
        const counts = {};
        patients.value.forEach(p => {
            const psy = p.psychologist || 'Non assigné';
            counts[psy] = (counts[psy] || 0) + 1;
        });
        return Object.entries(counts).map(([name, count]) => ({ name, count }));
    });

    // 1. Admissions du mois courant
    // ✅ Utilise la valeur exacte du backend pour une fiabilité maximale.
    const currentMonthAdmissions = computed(() => monthlyAdmissionsCount.value);

    // 2. Générateur d'Alertes (Critiques + Retards)
    const generatedAlerts = computed(() => {
        const alerts = [];
        const now = new Date();

        patients.value.forEach(p => {
            const pName = p.patientName || 'Patient Inconnu';
            
            // A. ALERTE CRITIQUE : Si rechute détectée (> 0)
            if (p.relapseCount && p.relapseCount > 0) {
                alerts.push({
                    id: `relapse-${p.patient_id}`,
                    type: 'critical', // rouge
                    title: `Rechute critique - ${pName}`,
                    message: `Le patient a ${p.relapseCount} incident(s) signalé(s).`
                });
            }

            // B. ALERTE RETARD : Vérification des durées de phase
            // Logique exemple : Phase 1 ne doit pas dépasser 15 jours
            if (p.admissionDate && p.currentPhase === 1) {
                const admission = new Date(p.admissionDate);
                const diffTime = Math.abs(now - admission);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 

                if (diffDays > 15) {
                    alerts.push({
                        id: `delay-${p.patient_id}`,
                        type: 'warning', // jaune
                        title: `Évaluation en retard - ${pName}`,
                        message: `En Phase 1 depuis ${diffDays} jours (Max standard: 15j).`
                    });
                }
            }
        });

        // On retourne les 5 plus importantes (Critiques d'abord)
        return alerts.sort((a, b) => (a.type === 'critical' ? -1 : 1)).slice(0, 5);
    });


    return { 
        // STATES
        patients, 
        isLoading, 
        psychologists,
        filters,
        
        // ACTIONS
        fetchDashboardStats, // Action pour les stats
        fetchToxicoPatients, 
        fetchPsychologists,
        addPatient,
        submitEvaluation,
        dischargePatient,
        getPatientDetails,
        setPage,
        setSearch,
        
        // COMPUTED STATS
        totalActive,
        statsByPhase,
        statsBySubstance,
        relapseRate,
        statsByPsy,
        currentMonthAdmissions, // Statistique fiable du mois courant (vient de monthlyAdmissionsCount)
        generatedAlerts,
        
        // Exposer la valeur brute (Optionnel)
        monthlyAdmissionsCount,
    };
});