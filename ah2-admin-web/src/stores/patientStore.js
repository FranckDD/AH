// src/stores/patientStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';

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

    const LOCAL_ROLES = ['medecin', 'nurse', 'secretaire'];

    function mapPendingPatient(p) {
        return {
            id: p.id,
            code: 'Code en attente',
            firstName: p.first_name,
            lastName: p.last_name,
            admissionDate: p.birth_date,
            phone: p.contact_phone,
            type: 'AUTRE',
            pending: true,
            flags: { is_clinical: false, is_toxicology: false, is_spiritual: false },
        };
    }

    // Patients crees localement, pas encore confirmes par le serveur
    // (server_id nul) - affiches en tete de liste, en ligne comme hors
    // ligne, sinon un patient tout juste cree n'apparait nulle part tant
    // que l'envoi n'est pas termine.
    async function pendingLocalPatients() {
        const authStore = useAuthStore();
        if (!authStore.hasRole(LOCAL_ROLES)) return [];
        const rows = await db.getAll(
            'SELECT * FROM patients WHERE server_id IS NULL ORDER BY last_name'
        );
        return rows.map(mapPendingPatient);
    }

    // Secours hors ligne : patients_lookup (memes patients que GET /patients/
    // en ligne pour ces roles), filtre de recherche applique localement. Le
    // filtre par onglet (CLINIQUE/TOXICO/SPIRITUEL) n'est pas applicable :
    // patients_lookup ne porte pas les indicateurs de domaine.
    async function localPatientList() {
        const search = (filters.value.search || '').trim();
        const like = `%${search}%`;
        const rows = search
            ? await db.getAll(
                `SELECT * FROM patients_lookup
                 WHERE code_patient LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                 ORDER BY last_name LIMIT 200`,
                [like, like, like]
            )
            : await db.getAll('SELECT * FROM patients_lookup ORDER BY last_name LIMIT 200');
        return rows.map((p) => ({
            id: p.patient_id,
            code: p.code_patient,
            firstName: p.first_name,
            lastName: p.last_name,
            admissionDate: null,
            phone: p.contact_phone,
            type: 'AUTRE',
            flags: { is_clinical: false, is_toxicology: false, is_spiritual: false },
        }));
    }

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

            patientData.value.data = [...(await pendingLocalPatients()), ...mappedList];

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
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(LOCAL_ROLES)) {
                console.warn('Patients hors ligne - secours sur les tables locales PowerSync:', err);
                const list = [...(await pendingLocalPatients()), ...(await localPatientList())];
                patientData.value.data = list;
                patientData.value.total = list.length;
                patientData.value.total_pages = 1;
            } else {
                console.error("Erreur fetchPatients:", err);
                error.value = "Erreur de connexion au serveur.";
                patientData.value.data = [];
                patientData.value.total = 0;
            }
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

    async function addPatient(formData) {
        isLoading.value = true;
        try {
            const payload = {
                first_name: formData.firstName,
                last_name: formData.lastName,
                birth_date: formData.birthDate,
                gender: formData.gender || null,
                national_id: formData.nationalId || null,
                contact_phone: formData.contactPhone,
                assurance: formData.assurance,
                residence: formData.residence,
                father_name: formData.fatherName,
                mother_name: formData.motherName,
            };

            // Ecriture locale pour medecin/nurse/secretaire, en ligne comme
            // hors ligne (connecteur : patients:PUT). Creation neutre en
            // domaine, comme en ligne : les indicateurs clinique/spirituel
            // sont calcules cote serveur a partir des dossiers (chantier 6).
            const authStore = useAuthStore();
            if (authStore.hasRole(LOCAL_ROLES)) {
                const uuid = crypto.randomUUID();
                await db.execute(
                    `INSERT INTO patients (
                        id, first_name, last_name, birth_date, gender, national_id,
                        contact_phone, assurance, residence, father_name, mother_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                    [
                        uuid, payload.first_name, payload.last_name, payload.birth_date,
                        payload.gender || null, payload.national_id || null,
                        payload.contact_phone || null, payload.assurance || null,
                        payload.residence || null, payload.father_name || null,
                        payload.mother_name || null,
                    ]
                );
                await fetchPatients();
                return { localUuid: uuid };
            }

            await api.post('/patients/', payload);

            // Rafraîchir la liste ET les compteurs après un ajout
            await Promise.all([
                fetchPatients(),
                fetchCounts()
            ]);
        } catch (err) {
            console.error("Erreur addPatient:", err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    async function updatePatient(patientId, formData) {
        isLoading.value = true;
        try {
            const payload = {
                first_name: formData.firstName,
                last_name: formData.lastName,
                birth_date: formData.birthDate,
                gender: formData.gender || null,
                national_id: formData.nationalId || null,
                contact_phone: formData.contactPhone,
                assurance: formData.assurance,
                residence: formData.residence,
                father_name: formData.fatherName,
                mother_name: formData.motherName,
            };

            await api.put(`/patients/${patientId}`, payload);

            await Promise.all([
                fetchPatients(),
                fetchCounts()
            ]);
        } catch (err) {
            console.error("Erreur updatePatient:", err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    async function getPatientById(id) {
        const response = await api.get(`/patients/${id}`);
        return response.data;
    }

    async function deletePatient(id) {
        try {
            await api.delete(`/patients/${id}`);

            // Optimiste : on retire de la liste locale
            patientData.value.data = patientData.value.data.filter(p => p.id !== id);

            // Rafraîchir les compteurs réels
            fetchCounts();
        } catch (err) {
            console.error("Erreur deletePatient:", err);
            throw err;
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
        counts, globalCounts,
        fetchPatients, fetchCounts, addPatient, updatePatient, deletePatient, getPatientById, setPage, setFilters
    };
});