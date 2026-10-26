import { defineStore } from 'pinia';
import { ref } from 'vue';
import { NurseShiftGateway } from '@/services/NurseShiftGateway';

// Les 3 seuls creneaux reellement acceptes par le backend (CHECK
// constraint + validation Pydantic, voir schemas.py) - ne pas en ajouter
// ici sans les ajouter aussi cote backend.
export const SHIFT_TYPES = ['MATIN', 'APRES_MIDI', 'NUIT'];

export const useNurseShiftStore = defineStore('nurseShift', () => {
    const shifts = ref([]);
    const activeNurses = ref([]);
    const isLoading = ref(false);
    const error = ref(null);
    // true = echec reseau (aucune reponse du serveur), distinct d'une erreur applicative.
    const offline = ref(false);

    async function fetchShifts(start, end) {
        isLoading.value = true;
        error.value = null;
        offline.value = false;
        try {
            const resp = await NurseShiftGateway.fetchShifts(start, end);
            shifts.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement planning infirmiers:', err);
            // Ne jamais laisser croire que personne n'est assigne : l'ecran montre un etat inconnu.
            shifts.value = [];
            offline.value = !err.response;
            error.value = "Impossible de charger le planning.";
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchActiveNurses() {
        try {
            const resp = await NurseShiftGateway.fetchActiveNurses();
            activeNurses.value = resp.data || [];
        } catch (err) {
            console.error('Erreur chargement liste infirmiers:', err);
            activeNurses.value = [];
        }
    }

    async function createShift(shiftDate, shiftType, nurseId, start, end) {
        await NurseShiftGateway.createShift(shiftDate, shiftType, nurseId);
        await fetchShifts(start, end);
    }

    async function deleteShift(shiftId, start, end) {
        await NurseShiftGateway.deleteShift(shiftId);
        await fetchShifts(start, end);
    }

    return {
        shifts,
        activeNurses,
        isLoading,
        error,
        offline,
        fetchShifts,
        fetchActiveNurses,
        createShift,
        deleteShift,
    };
});
