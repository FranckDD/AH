import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api'; 

export const usePatientDossierStore = defineStore('patientDossier', () => {
    
    // --- ÉTAT (STATE) ---
    const patientSummary = ref(null);
    const medicalHistory = ref([]);
    const prescriptionHistory = ref([]);
    const labHistory = ref([]);
    const spiritualHistory = ref([]);

    const isLoading = ref(false);
    const error = ref(null);

    // --- ACTIONS ---

    async function fetchDossierComplete(patientId) {
        isLoading.value = true;
        error.value = null;
        
        try {
            // 1. Charger le résumé
            const summaryRes = await api.get(`/medical_records/patient/${patientId}/dme_summary`);
            patientSummary.value = summaryRes.data;
            const flags = patientSummary.value.flags || {};

            // 2. Requêtes parallèles
            const promises = [];

            // --- Onglets Cliniques ---
            if (flags.is_clinical || flags.is_toxicology) {
                
                // 🟢 CORRECTION ICI : On utilise la route DÉDIÉE /history
                // Elle renvoie un tableau direct, sans pagination, trié par date.
                promises.push(
                    api.get(`/medical_records/patient/${patientId}/history`)
                    .then(res => {
                        medicalHistory.value = res.data || [];
                    })
                );
                
                promises.push(
                    api.get(`/prescriptions/patient/${patientId}`)
                    .then(res => prescriptionHistory.value = res.data || [])
                );
                        
                promises.push(
                    api.get(`/labo/patient/${patientId}/history`)
                    .then(res => labHistory.value = res.data || [])
                );
            }

            // --- Onglet Spirituel ---
            if (flags.is_spiritual) {
                promises.push(
                    api.get(`/cs/patient/${patientId}/history`)
                        .then(res => spiritualHistory.value = res.data || [])
                        .catch(err => {
                            console.warn("Erreur chargement spirituel:", err);
                            spiritualHistory.value = [];
                        })
                );
            }

            await Promise.all(promises);

        } catch (err) {
            console.error("Erreur chargement dossier:", err);
            error.value = "Impossible de charger le dossier complet.";
        } finally {
            isLoading.value = false;
        }
    }

    async function refreshMedicalHistory(patientId) {
        try {
            // 🟢 CORRECTION ICI AUSSI
            const res = await api.get(`/medical_records/patient/${patientId}/history`);
            medicalHistory.value = res.data || [];
            
            const sumRes = await api.get(`/medical_records/patient/${patientId}/dme_summary`);
            patientSummary.value = sumRes.data;
        } catch (err) {
            console.error("Erreur refresh medical:", err);
        }
    }

    // --- GETTERS (Inchangés) ---
    const isToxicology = computed(() => patientSummary.value?.flags?.is_toxicology || false);
    const isSpiritual = computed(() => patientSummary.value?.flags?.is_spiritual || false);
    const isClinical = computed(() => patientSummary.value?.flags?.is_clinical || false);
    const fullName = computed(() => patientSummary.value?.full_name || 'Patient Inconnu');
    const code = computed(() => patientSummary.value?.code || '-');

    const vitals = computed(() => ({
        bp: patientSummary.value?.last_bp || '-',
        weight: patientSummary.value?.last_weight ? `${patientSummary.value.last_weight} kg` : '-',
        temp: patientSummary.value?.last_temp ? `${patientSummary.value.last_temp}°C` : '-',
        lastDate: patientSummary.value?.last_consultation_date 
            ? new Date(patientSummary.value.last_consultation_date).toLocaleDateString('fr-FR') 
            : '-'
    }));

    return {
        patientSummary,
        medicalHistory,
        prescriptionHistory,
        labHistory,
        spiritualHistory,
        isLoading,
        error,
        fetchDossierComplete,
        refreshMedicalHistory,
        isToxicology,
        isSpiritual,
        isClinical,
        fullName,
        code,
        vitals
    };
});