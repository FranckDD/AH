import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { MedicalRecordGateway } from '@/services/MedicalRecordGateway';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';

export const useMedicalRecordStore = defineStore('medicalRecord', () => {

    // --- ÉTAT ---
    const records = ref([]);
    const motifs = ref([]);
    const isLoading = ref(false);
    const totalItems = ref(0);

    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        dateFrom: '',
        dateTo: '',
        motifCode: '',
        severity: '',
    });

    // --- ACTIONS ---

    async function fetchMedicalRecords() {
        isLoading.value = true;
        try {
            const params = {
                page: filters.value.page,
                per_page: filters.value.per_page,
                searchQuery: filters.value.searchQuery,
                motifCode: filters.value.motifCode,
                severity: filters.value.severity,
                dateFrom: filters.value.dateFrom,
                dateTo: filters.value.dateTo,
            };

            const res = await MedicalRecordGateway.fetchMedicalRecords(params);
            records.value = res.data.data || [];
            totalItems.value = res.data.total || 0;
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Consultations hors ligne - secours sur la table locale PowerSync:', err);
                await refreshMedicalRecordsLocal();
            } else {
                console.error('Erreur chargement dossiers medicaux:', err);
                records.value = [];
            }
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchMotifs() {
        try {
            const res = await MedicalRecordGateway.fetchMotifs();
            motifs.value = res.data || [];
        } catch (err) {
            // Le motif est obligatoire pour enregistrer une consultation
            // (MedicalRecordModal) : sans ce secours, toute consultation hors
            // ligne etait impossible (liste vide).
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Motifs hors ligne - secours sur la table locale PowerSync:', err);
                motifs.value = await db.getAll('SELECT code, label_fr FROM motifs ORDER BY label_fr');
                return;
            }
            console.error('Erreur chargement motifs:', err);
            motifs.value = [];
        }
    }

    // Rafraichit records/totalItems depuis la table locale (pas de
    // pagination/filtre serveur - approximation raisonnable, le jeu de
    // donnees local est celui deja synchronise pour ce role, jamais
    // volumineux). Utilise apres une ecriture locale (createMedicalRecord/
    // updateMedicalRecord ci-dessous) pour que TOUT ecran consommant ce
    // store (MedicalRecordsList.vue, pas seulement PatientDetailView.vue)
    // voie la mise a jour - registre Important I1, revue finale 2026-09-23.
    function mapLocalMedicalRecord(r) {
        return {
            ...r,
            record_id: r.server_id,
            local_id: r.id,
            patient: {
                patient_id: r.patient_id,
                code_patient: r.p_code,
                first_name: r.p_first_name,
                last_name: r.p_last_name,
            },
        };
    }

    async function refreshMedicalRecordsLocal() {
        const rows = await db.getAll(
            `SELECT mr.*,
                    COALESCE(pl.code_patient, lp.code_patient) AS p_code,
                    COALESCE(pl.first_name, lp.first_name) AS p_first_name,
                    COALESCE(pl.last_name, lp.last_name) AS p_last_name
             FROM medical_records mr
             LEFT JOIN patients_lookup pl ON pl.patient_id = mr.patient_id
             LEFT JOIN patients lp ON lp.id = mr.patient_uuid
             ORDER BY mr.consultation_date DESC`
        );
        records.value = rows.map(mapLocalMedicalRecord);
        totalItems.value = rows.length;
    }

    // Ecriture locale (pas d'appel REST direct) pour medecin/nurse - en
    // ligne comme hors ligne, PowerSync met l'INSERT en file et appelle
    // DossierConnector.uploadData() en arriere-plan (voir plan precedent,
    // Tache 6). crypto.randomUUID() genere le uuid client, qui devient la
    // cle primaire locale ET la colonne uuid Postgres une fois synchronise.
    // { record_id: uuid } prend la place du vrai record_id (pas encore
    // confirme par le serveur) - contrat deja attendu par
    // PatientDetailView.vue pour proposer une prescription liee juste
    // apres cette consultation.
    async function createMedicalRecord(data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['medecin', 'nurse'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO medical_records (
                    id, patient_id, patient_uuid, consultation_date, motif_code, appointment_id,
                    marital_status, severity, bp, temperature, weight, height,
                    medical_history, allergies, symptoms, diagnosis, treatment, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId || null, data.patientUuid || null, data.consultationDate || null, data.motifCode, data.appointmentId || null,
                    data.maritalStatus || null, data.severity || null, data.bp || null,
                    data.temperature ?? null, data.weight ?? null, data.height ?? null,
                    data.medicalHistory || null, data.allergies || null, data.symptoms || null,
                    data.diagnosis || null, data.treatment || null, data.notes || null,
                ]
            );
            await refreshMedicalRecordsLocal();
            return { record_id: uuid };
        }

        const res = await MedicalRecordGateway.createMedicalRecord(data);
        filters.value.page = 1;
        await fetchMedicalRecords();
        return res.data;
    }

    // recordId peut etre soit l'id local (uuid, consultation creee/editee
    // hors ligne dans cette meme session), soit le vrai server_id entier
    // (consultation deja synchronisee, ouverte depuis une liste chargee en
    // HTTP) - WHERE id = ? OR server_id = ? couvre les deux cas. String()
    // sur le premier binding : comparer un entier a la colonne "id" (TEXT)
    // ne doit jamais matcher par coincidence de type.
    async function updateMedicalRecord(recordId, data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['medecin', 'nurse'])) {
            const existing = await db.getOptional(
                'SELECT id FROM medical_records WHERE id = ? OR server_id = ?',
                [String(recordId), recordId]
            );
            if (!existing) {
                throw new Error('Consultation introuvable localement - modification impossible hors ligne.');
            }
            await db.execute(
                `UPDATE medical_records SET
                    patient_id = ?, consultation_date = ?, motif_code = ?, marital_status = ?,
                    severity = ?, bp = ?, temperature = ?, weight = ?, height = ?,
                    medical_history = ?, allergies = ?, symptoms = ?, diagnosis = ?,
                    treatment = ?, notes = ?
                 WHERE id = ? OR server_id = ?`,
                [
                    data.patientId, data.consultationDate || null, data.motifCode, data.maritalStatus || null,
                    data.severity || null, data.bp || null, data.temperature ?? null, data.weight ?? null,
                    data.height ?? null, data.medicalHistory || null, data.allergies || null,
                    data.symptoms || null, data.diagnosis || null, data.treatment || null, data.notes || null,
                    String(recordId), recordId,
                ]
            );
            await refreshMedicalRecordsLocal();
            return;
        }

        await MedicalRecordGateway.updateMedicalRecord(recordId, data);
        await fetchMedicalRecords();
    }

    async function deleteMedicalRecord(recordId) {
        await MedicalRecordGateway.deleteMedicalRecord(recordId);
        await fetchMedicalRecords();
    }

    function setPage(page) {
        filters.value.page = page;
        fetchMedicalRecords();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchMedicalRecords();
    }

    // --- GETTERS ---
    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1,
    }));

    return {
        records,
        motifs,
        isLoading,
        filters,
        pagination,
        fetchMedicalRecords,
        fetchMotifs,
        refreshMedicalRecordsLocal,
        createMedicalRecord,
        updateMedicalRecord,
        deleteMedicalRecord,
        setPage,
        setFilters,
    };
});
