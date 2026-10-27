// Fichier: stores/toxicoStore.js

import { isLoadFailure } from '@/utils/loadFailure';
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import i18n from '../i18n.js';
import { ToxicoGateway } from '@/services/ToxicoGateway'; // Assurez-vous que le chemin est correct
import { newThisWeek } from '@/utils/toxicoUi';
import { buildDischargedQuery, clampDischargedPage, DISCHARGED_PER_PAGE } from '@/utils/toxicoDischarged';

export const useToxicoStore = defineStore('toxico', () => {
    // --- STATE ---
    const patients = ref([]);
    const totalItems = ref(0);
    const isLoading = ref(false);
    // Echec de chargement (hors ligne, serveur) : l'ecran affiche un etat d'erreur, jamais une liste vide ni des 0.
    const listLoadFailed = ref(false);
    const statsLoadFailed = ref(false);
    const psychologists = ref([]); // Liste des psys pour les selects
    
    // ✅ NOUVEL ÉTAT : Pour stocker le compte des admissions du mois venant du backend
    const monthlyAdmissionsCount = ref(0); 

    // Chiffres GLOBAUX du suivi (serveur) : independants de la page et de la recherche de la liste.
    const globalStats = ref(null);
    
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
            listLoadFailed.value = false;
            patients.value = response.data.data || [];
            totalItems.value = response.data.total || 0;
            
        } catch (error) {
            console.error("Erreur chargement patients toxico:", error);
            listLoadFailed.value = isLoadFailure(error);
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

    // 2b. Rechercher un patient existant (pour la modale d'admission toxico)
    async function searchExistingPatients(query) {
        try {
            const response = await ToxicoGateway.searchPatients(query);
            return response.data.data || [];
        } catch (e) {
            console.error("Erreur recherche patient:", e);
            return [];
        }
    }

    // 3. Admission (Création)
    async function addPatient(admissionData) {
        isLoading.value = true;
        try {
            console.log("📦 [Store] Envoi Admission JSON:", JSON.stringify(admissionData));

            const response = await ToxicoGateway.admitPatient(admissionData);
            
            // Rafraîchir la liste et les stats après succès
            await fetchToxicoPatients();
            await fetchDashboardStats(); // ✅ Mise à jour des stats après une admission
            return response?.data || {}; // { is_readmission, stay_number, ... }
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
    
    // Sejour hospitalier ouvert du patient (avertissement avant sortie toxico)
    async function fetchOpenHospitalization(dossierId) {
        return ToxicoGateway.getOpenHospitalization(dossierId);
    }

    // 5. Clôture / Sortie
    async function dischargePatient(dossierId, { reason, note, date } = {}) {
        try {
            await ToxicoGateway.dischargePatient(dossierId, { reason, note, date });
            await fetchToxicoPatients();
            await fetchDashboardStats(); // ✅ Mise à jour des stats si le décompte change
        } catch (error) {
            console.error("Erreur clôture:", error);
            throw error;
        }
    }
    
    // 5b. Transfert vers un autre psychologue referent
    async function transferDossier(dossierId, { toPsychologistId, reason } = {}) {
        try {
            await ToxicoGateway.transferDossier(dossierId, { to_psychologist_id: toPsychologistId, reason });
            await fetchToxicoPatients();
            await fetchDashboardStats();
        } catch (error) {
            console.error("Erreur transfert:", error);
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
            statsLoadFailed.value = false;
            
            if (response && response.data && response.data.currentMonthAdmissions !== undefined) {
                monthlyAdmissionsCount.value = response.data.currentMonthAdmissions ?? 0;
                globalStats.value = response.data.activeTotal !== undefined ? response.data : null;
            } else {
                console.warn("Réponse des stats inattendue ou manquante.");
                monthlyAdmissionsCount.value = 0;
            }
        } catch (error) {
            console.error("Erreur chargement stats tableau de bord:", error);
            statsLoadFailed.value = isLoadFailure(error);
            monthlyAdmissionsCount.value = 0; // Réinitialiser en cas d'échec
            throw error;
        }
    }

    // --- PATIENTS SORTIS (dossiers inactifs) ---
    const discharged = ref([]);
    const dischargedTotal = ref(0);
    const dischargedTotalPages = ref(0);
    const dischargedLoading = ref(false);
    const dischargedError = ref(null);
    const dischargedFilters = ref({ page: 1, per_page: DISCHARGED_PER_PAGE, search: '', reason: '', from: '', to: '' });
    let dischargedRequestId = 0;

    async function fetchDischarged() {
        const reqId = ++dischargedRequestId;
        dischargedLoading.value = true;
        dischargedError.value = null;
        try {
            const res = await ToxicoGateway.listDischarged(buildDischargedQuery(dischargedFilters.value));
            if (reqId !== dischargedRequestId) return;
            discharged.value = res.data?.data || [];
            dischargedTotal.value = res.data?.total || 0;
            dischargedTotalPages.value = res.data?.total_pages || 0;
            const f = dischargedFilters.value;
            const target = clampDischargedPage(f.page, dischargedTotal.value, f.per_page, discharged.value.length);
            if (target !== null && target !== f.page) {
                dischargedFilters.value = { ...f, page: target };
                return fetchDischarged();
            }
        } catch (error) {
            if (reqId !== dischargedRequestId) return;
            console.error("Erreur chargement patients sortis:", error);
            discharged.value = [];
            dischargedError.value = error;
        } finally {
            if (reqId === dischargedRequestId) dischargedLoading.value = false;
        }
    }

    function setDischargedFilters(patch) {
        dischargedFilters.value = { ...dischargedFilters.value, ...patch, page: 1 };
        return fetchDischarged();
    }

    function clearDischarged() {
        dischargedRequestId++;
        discharged.value = [];
        dischargedTotal.value = 0;
        dischargedTotalPages.value = 0;
        dischargedLoading.value = false;
        dischargedError.value = null;
    }

    function setDischargedPage(page) {
        dischargedFilters.value = { ...dischargedFilters.value, page };
        return fetchDischarged();
    }

    // --- PATIENTS SUIVIS AUPARAVANT (psychologue a vue limitee, lecture seule) ---
    const PREVIOUS_PER_PAGE = 20;
    const previous = ref([]);
    const previousTotal = ref(0);
    const previousLoading = ref(false);
    const previousError = ref(null);
    const previousPage = ref(1);
    let previousRequestId = 0;

    async function fetchPrevious() {
        const reqId = ++previousRequestId;
        previousLoading.value = true;
        previousError.value = null;
        try {
            const res = await ToxicoGateway.listPrevious({ page: previousPage.value, per_page: PREVIOUS_PER_PAGE });
            if (reqId !== previousRequestId) return;
            previous.value = res.data?.data || [];
            previousTotal.value = res.data?.total || 0;
        } catch (error) {
            if (reqId !== previousRequestId) return;
            console.error("Erreur chargement patients suivis auparavant:", error);
            previous.value = [];
            previousError.value = error;
        } finally {
            if (reqId === previousRequestId) previousLoading.value = false;
        }
    }

    function setPreviousPage(n) {
        previousPage.value = Math.max(1, Number(n) || 1);
        return fetchPrevious();
    }

    // Statistiques limitees au perimetre du psychologue (le serveur renvoie scoped: true)
    const isScoped = computed(() => globalStats.value?.scoped === true);

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
    
    // Total de la LISTE (suit la recherche) : sert a la pagination et au compteur de resultats.
    const listTotal = computed(() => totalItems.value);
    // Patients actifs, chiffre global du serveur (repli : total de la liste tant que les stats ne sont pas chargees).
    const activeTotal = computed(() => (globalStats.value ? globalStats.value.activeTotal : totalItems.value));
    const totalActive = activeTotal;
    const newThisWeekCount = computed(() => (globalStats.value ? globalStats.value.newThisWeek : newThisWeek(patients.value)));

    const statsByPhase = computed(() => {
        const counts = { 1: 0, 2: 0, 3: 0, 4: 0 };
        if (globalStats.value) {
            for (const k of Object.keys(counts)) counts[k] = Number(globalStats.value.byPhase?.[k]) || 0;
            return counts;
        }
        patients.value.forEach(p => {
            if (counts[p.currentPhase] !== undefined) counts[p.currentPhase]++;
        });
        return counts;
    });

    const statsBySubstance = computed(() => {
        const counts = {};
        if (globalStats.value) return { ...(globalStats.value.bySubstance || {}) };
        patients.value.forEach(p => {
            const sub = p.substance || 'Autre';
            counts[sub] = (counts[sub] || 0) + 1;
        });
        return counts;
    });

    const relapseRate = computed(() => {
        if (globalStats.value) return Number(globalStats.value.relapseRate) || 0;
        if (patients.value.length === 0) return 0;
        const patientsWithRelapse = patients.value.filter(p => p.relapseCount > 0).length;
        // Ce calcul n'est précis que sur la page courante, à noter.
        return Math.round((patientsWithRelapse / patients.value.length) * 100); 
    });

    const statsByPsy = computed(() => {
        const counts = {};
        if (globalStats.value) return [...(globalStats.value.byPsychologist || [])];
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
            const pName = p.patientName || i18n.global.t('toxicoScreens.unknown_patient');
            
            // A. ALERTE CRITIQUE : Si rechute détectée (> 0)
            if (p.relapseCount && p.relapseCount > 0) {
                alerts.push({
                    id: `relapse-${p.patient_id}`,
                    type: 'critical', // rouge
                    title: i18n.global.t('toxicoScreens.alert_relapse_title', { name: pName }),
                    message: i18n.global.t('toxicoScreens.alert_relapse_message', { n: p.relapseCount })
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
                        title: i18n.global.t('toxicoScreens.alert_late_title', { name: pName }),
                        message: i18n.global.t('toxicoScreens.alert_late_message', { days: diffDays })
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
        listLoadFailed,
        statsLoadFailed,
        psychologists,
        filters,
        
        // ACTIONS
        fetchDashboardStats, // Action pour les stats
        fetchToxicoPatients,
        fetchPsychologists,
        searchExistingPatients,
        addPatient,
        submitEvaluation,
        dischargePatient,
        transferDossier,
        fetchOpenHospitalization,
        getPatientDetails,
        setPage,
        setSearch,
        discharged, dischargedTotal, dischargedTotalPages, dischargedLoading, dischargedError,
        previous, previousTotal, previousLoading, previousError, previousPage, fetchPrevious, setPreviousPage, isScoped,
        dischargedFilters, fetchDischarged, setDischargedFilters, setDischargedPage, clearDischarged,
        
        // COMPUTED STATS
        totalActive, activeTotal, listTotal, newThisWeekCount, globalStats,
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