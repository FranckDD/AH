import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { PrescriptionGateway } from '@/services/PrescriptionGateway';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';
import { getExamCatalogLocal } from '@/powersync-client/referenceData';

export const usePrescriptionStore = defineStore('prescription', () => {

    // --- ÉTAT ---
    const prescriptions = ref([]);
    const examTypes = ref([]);
    const isLoading = ref(false);
    const totalItems = ref(0);

    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        dateFrom: '',
        dateTo: '',
    });

    // --- ACTIONS ---

    async function fetchPrescriptions() {
        isLoading.value = true;
        try {
            const params = {
                page: filters.value.page,
                per_page: filters.value.per_page,
                searchQuery: filters.value.searchQuery,
            };

            // Le backend n'applique le filtre de date que si les DEUX bornes
            // sont presentes (repository: "if date_from and date_to") - un
            // filtre a une seule borne serait silencieusement ignore cote
            // serveur sans le rendre visible a l'utilisateur ; on ne
            // l'envoie donc que quand les deux sont renseignees.
            if (filters.value.dateFrom && filters.value.dateTo) {
                params.dateFrom = filters.value.dateFrom;
                params.dateTo = filters.value.dateTo;
            }

            const res = await PrescriptionGateway.fetchPrescriptions(params);
            prescriptions.value = res.data.data || [];
            totalItems.value = res.data.total || 0;
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Prescriptions hors ligne - secours sur la table locale PowerSync:', err);
                await refreshPrescriptionsLocal();
            } else {
                console.error('Erreur chargement prescriptions:', err);
                prescriptions.value = [];
            }
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchExamTypes() {
        try {
            const res = await PrescriptionGateway.fetchExamTypes();
            examTypes.value = res.data || [];
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Catalogue examens hors ligne - secours sur la table locale PowerSync:', err);
                examTypes.value = await getExamCatalogLocal();
                return;
            }
            console.error('Erreur chargement types examens:', err);
            examTypes.value = [];
        }
    }

    // Meme motif que medicalRecordStore.refreshMedicalRecordsLocal - registre
    // Important I1, revue finale 2026-09-23.
    // Forme identique a la reponse HTTP (registre Important I1 + famille de
    // bugs "champ derive du serveur jamais peuple localement") : les ecrans
    // lisent prescription_id, patient.*, lab_exams_list (tableau).
    function parseList(raw) {
        if (!raw) return [];
        try {
            const v = JSON.parse(raw);
            return Array.isArray(v) ? v : [];
        } catch {
            return [];
        }
    }

    function mapLocalPrescription(r) {
        return {
            ...r,
            prescription_id: r.server_id,
            local_id: r.id,
            is_lab_order: !!r.is_lab_order,
            lab_exams_list: parseList(r.lab_exams_list),
            patient: {
                patient_id: r.patient_id,
                code_patient: r.p_code,
                first_name: r.p_first_name,
                last_name: r.p_last_name,
            },
        };
    }

    async function refreshPrescriptionsLocal() {
        const rows = await db.getAll(
            `SELECT pr.*,
                    COALESCE(pl.code_patient, lp.code_patient) AS p_code,
                    COALESCE(pl.first_name, lp.first_name) AS p_first_name,
                    COALESCE(pl.last_name, lp.last_name) AS p_last_name
             FROM prescriptions pr
             LEFT JOIN patients_lookup pl ON pl.patient_id = pr.patient_id
             LEFT JOIN patients lp ON lp.id = pr.patient_uuid
             ORDER BY pr.start_date DESC`
        );
        prescriptions.value = rows.map(mapLocalPrescription);
        totalItems.value = rows.length;
    }

    // Ecriture locale pour medecin/nurse, meme motif que
    // medicalRecordStore.createMedicalRecord (Tache 2). data.medicalRecordId
    // peut etre l'id local (uuid) d'une consultation creee dans le meme
    // geste hors ligne - stocke tel quel dans la colonne medical_record_id
    // (declaree column.integer mais SQLite est faiblement type, accepte le
    // texte sans erreur - deja le comportement anticipe par
    // DossierConnector.js, qui resout le vrai server_id au moment de
    // l'upload). lab_exams_list serialise en JSON texte, aucune colonne
    // array/JSON native cote PowerSync.
    async function createPrescription(data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['medecin', 'nurse'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO prescriptions (
                    id, patient_id, patient_uuid, medical_record_id, medication, dosage, frequency,
                    duration, start_date, end_date, notes, is_lab_order, lab_exams_list
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId || null, data.patientUuid || null, data.medicalRecordId || null, data.medication || null,
                    data.dosage || null, data.frequency || null, data.duration || null,
                    data.startDate || null, data.endDate || null, data.notes || null,
                    data.isLabOrder ? 1 : 0, JSON.stringify(data.labExamsList || []),
                ]
            );
            await refreshPrescriptionsLocal();
            return;
        }

        await PrescriptionGateway.createPrescription(data);
        filters.value.page = 1;
        await fetchPrescriptions();
    }

    // Ecriture locale pour medecin/nurse (connecteur : prescriptions:PATCH).
    // prescriptionId = server_id (bouton "modifier" desactive tant qu'une
    // prescription n'est pas synchronisee). Existence verifiee AVANT
    // l'UPDATE : rowsAffected n'est pas fiable pour un UPDATE PowerSync, et
    // une modification sur une ligne absente localement serait perdue sans
    // bruit.
    async function updatePrescription(prescriptionId, data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['medecin', 'nurse'])) {
            const existing = await db.getOptional(
                'SELECT id FROM prescriptions WHERE id = ? OR server_id = ?',
                [String(prescriptionId), prescriptionId]
            );
            if (!existing) {
                throw new Error('Prescription introuvable localement - modification impossible hors ligne.');
            }
            await db.execute(
                `UPDATE prescriptions SET
                    medication = ?, dosage = ?, frequency = ?, duration = ?, start_date = ?,
                    end_date = ?, notes = ?, is_lab_order = ?, lab_exams_list = ?
                 WHERE id = ?`,
                [
                    data.medication || null, data.dosage || null, data.frequency || null,
                    data.duration || null, data.startDate || null, data.endDate || null,
                    data.notes || null, data.isLabOrder ? 1 : 0,
                    JSON.stringify(data.labExamsList || []), existing.id,
                ]
            );
            await refreshPrescriptionsLocal();
            return;
        }

        await PrescriptionGateway.updatePrescription(prescriptionId, data);
        await fetchPrescriptions();
    }

    async function deletePrescription(prescriptionId) {
        await PrescriptionGateway.deletePrescription(prescriptionId);
        await fetchPrescriptions();
    }

    function setPage(page) {
        filters.value.page = page;
        fetchPrescriptions();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchPrescriptions();
    }

    // --- GETTERS ---
    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1,
    }));

    return {
        prescriptions,
        examTypes,
        isLoading,
        filters,
        pagination,
        fetchPrescriptions,
        fetchExamTypes,
        refreshPrescriptionsLocal,
        createPrescription,
        updatePrescription,
        deletePrescription,
        setPage,
        setFilters,
    };
});
