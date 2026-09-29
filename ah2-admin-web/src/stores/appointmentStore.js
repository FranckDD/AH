import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { AppointmentGateway } from '@/services/AppointmentGateway';
import { db } from '@/powersync-client/client';

// Les 3 seuls statuts reellement produits par le backend, verifie de
// facon exhaustive (grep sur toutes les affectations de status dans
// tout le code appointments) - voir registre C4. Ne pas ajouter
// "confirmed"/"accepted" ici tant que ce ticket n'est pas tranche.
export const APPOINTMENT_STATUSES = ['pending', 'cancelled', 'completed'];

export const useAppointmentStore = defineStore('appointment', () => {

    // --- ÉTAT ---
    // rawAppointments : jeu de donnees local complet tel que renvoye par
    // db.watch() (non filtre). "appointments" (expose au reste de l'appli)
    // est un computed derive de rawAppointments + filters - db.watch() ne
    // se redeclenche que sur changement en base locale (sync/ecriture),
    // jamais quand filters.value change ailleurs (ex. setFilters()) ; le
    // filtrage doit donc etre reactif independamment de la boucle de watch,
    // sinon taper dans la recherche ou changer un filtre n'a aucun effet
    // tant qu'aucune nouvelle donnee n'arrive en base locale (bug reel
    // constate pendant le test navigateur - filtres/recherche muets).
    const rawAppointments = ref([]);
    const specialties = ref([]);
    const isLoading = ref(false);

    const filters = ref({
        searchQuery: '',
        status: 'ALL', // 'ALL' | 'pending' | 'cancelled' | 'completed'
        dateMode: 'ALL', // 'ALL' | 'TODAY' | 'CUSTOM'
        customDate: '',
    });

    let watchAbortController = null;

    // --- ACTIONS ---

    // Requete reactive sur la base locale PowerSync (pas un appel REST) -
    // se met a jour automatiquement quand une synchronisation arrive ou
    // qu'une ecriture locale est faite (createAppointment/updateAppointment
    // ci-dessous), sans jamais rappeler cette fonction manuellement.
    function startWatchingAppointments() {
        if (watchAbortController) {
            watchAbortController.abort();
        }
        watchAbortController = new AbortController();

        isLoading.value = true;
        (async () => {
            try {
                for await (const result of db.watch(
                    `SELECT a.*, p.first_name, p.last_name, p.code_patient, p.contact_phone,
                            d.full_name AS doctor_full_name, d.username AS doctor_username
                     FROM appointments a
                     LEFT JOIN patients_lookup p ON p.patient_id = a.patient_id
                     LEFT JOIN doctors_lookup d ON d.user_id = a.doctor_id
                     ORDER BY a.appointment_date DESC, a.appointment_time DESC`,
                    [],
                    { signal: watchAbortController.signal }
                )) {
                    rawAppointments.value = result.rows?._array ?? [];
                    isLoading.value = false;
                }
            } catch (err) {
                if (err?.name !== 'AbortError') {
                    console.error('Erreur watch RDV PowerSync:', err);
                }
                isLoading.value = false;
            }
        })();
    }

    async function fetchSpecialties() {
        try {
            const res = await AppointmentGateway.getSpecialties();
            specialties.value = res.data || [];
        } catch (err) {
            console.error('Erreur chargement spécialités:', err);
            specialties.value = [];
        }
    }

    // Ecriture locale (pas d'appel REST direct) - PowerSync met l'INSERT
    // en file et appelle DossierConnector.uploadData() en arriere-plan,
    // en ligne comme hors ligne. crypto.randomUUID() genere le uuid client,
    // qui devient la cle primaire locale ET la colonne uuid Postgres une
    // fois synchronise (voir Contraintes globales du plan).
    async function createAppointment(data) {
        const uuid = crypto.randomUUID();
        await db.execute(
            `INSERT INTO appointments (id, patient_id, doctor_id, specialty, appointment_date, appointment_time, reason, status)
             VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')`,
            [uuid, data.patientId, data.doctorId || null, data.specialty || null, data.appointmentDate, data.appointmentTime, data.reason || '']
        );
    }

    async function updateAppointment(localId, data) {
        await db.execute(
            `UPDATE appointments
             SET patient_id = ?, doctor_id = ?, specialty = ?, appointment_date = ?, appointment_time = ?, reason = ?
             WHERE id = ?`,
            [data.patientId, data.doctorId || null, data.specialty || null, data.appointmentDate, data.appointmentTime, data.reason || '', localId]
        );
    }

    async function cancelAppointment(appointmentId) {
        await AppointmentGateway.cancelAppointment(appointmentId);
    }

    async function completeAppointment(appointmentId) {
        await AppointmentGateway.completeAppointment(appointmentId);
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters };
    }

    // Reactif a la fois aux nouvelles donnees locales (rawAppointments) et
    // aux changements de filtres (filters) - contrairement au filtrage
    // fait auparavant a l'interieur de la boucle db.watch().
    const appointments = computed(() => {
        let items = rawAppointments.value;

        if (filters.value.status !== 'ALL') {
            items = items.filter((a) => a.status === filters.value.status);
        }
        if (filters.value.dateMode === 'TODAY') {
            const today = new Date().toISOString().split('T')[0];
            items = items.filter((a) => a.appointment_date === today);
        } else if (filters.value.dateMode === 'CUSTOM' && filters.value.customDate) {
            items = items.filter((a) => a.appointment_date === filters.value.customDate);
        }
        if (filters.value.searchQuery) {
            const q = filters.value.searchQuery.toLowerCase();
            items = items.filter((a) =>
                (a.first_name || '').toLowerCase().includes(q) ||
                (a.last_name || '').toLowerCase().includes(q) ||
                (a.code_patient || '').toLowerCase().includes(q)
            );
        }

        return items;
    });

    return {
        appointments,
        // Expose en plus de "appointments" (filtre liste) - la vue
        // calendrier (AppointmentsCalendar.vue) affiche volontairement
        // TOUT le mois, independamment des filtres recherche/statut de la
        // vue liste, decision prise avec l'utilisateur (voir brainstorming
        // du 2026-09-28).
        rawAppointments,
        specialties,
        isLoading,
        filters,
        startWatchingAppointments,
        fetchSpecialties,
        createAppointment,
        updateAppointment,
        cancelAppointment,
        completeAppointment,
        setFilters,
    };
});
