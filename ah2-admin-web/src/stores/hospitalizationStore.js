// src/stores/hospitalizationStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { HospitalizationGateway } from '@/services/HospitalizationGateway';

// Les 4 seules valeurs reellement acceptees par le backend (CHECK
// constraint + validation Pydantic, voir schemas.py) - ne pas en
// ajouter ici sans les ajouter aussi cote backend.
export const DISCHARGE_DISPOSITIONS = ['GUERI', 'TRANSFERE', 'SORTIE_CONTRE_AVIS_MEDICAL', 'DECES'];
export const CLINICAL_STATUSES = ['AMELIORATION', 'STABLE', 'AGGRAVATION'];

export const useHospitalizationStore = defineStore('hospitalization', () => {
    const current = ref([]);
    const patientHistory = ref([]);
    const isLoading = ref(false);
    const error = ref(null);

    async function fetchCurrent() {
        isLoading.value = true;
        error.value = null;
        try {
            const resp = await HospitalizationGateway.fetchCurrent();
            current.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement hospitalisations en cours:', err);
            error.value = "Impossible de charger la liste des patients hospitalisés.";
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchPatientHistory(patientId) {
        try {
            const resp = await HospitalizationGateway.fetchPatientHistory(patientId);
            patientHistory.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement historique hospitalisation:', err);
            patientHistory.value = [];
        }
    }

    async function admit(patientId, admissionReason) {
        await HospitalizationGateway.admit(patientId, admissionReason);
        await fetchPatientHistory(patientId);
    }

    async function addStatusUpdate(hospitalizationId, statusValue, note, patientId) {
        await HospitalizationGateway.addStatusUpdate(hospitalizationId, statusValue, note);
        if (patientId) await fetchPatientHistory(patientId);
    }

    async function discharge(hospitalizationId, dischargeDisposition, dischargeNote, patientId) {
        await HospitalizationGateway.discharge(hospitalizationId, dischargeDisposition, dischargeNote);
        if (patientId) await fetchPatientHistory(patientId);
    }

    return {
        current,
        patientHistory,
        isLoading,
        error,
        fetchCurrent,
        fetchPatientHistory,
        admit,
        addStatusUpdate,
        discharge,
    };
});
