// src/services/labGateway.js
import api from './api';
import { useAuthStore } from '@/stores/auth';
import { getExamCatalogLocal } from '@/powersync-client/referenceData';

export const LabGateway = {

    // ============================================================
    // 1. CONFIGURATION (Examens)
    // ============================================================

    async getAllExams() {
        try {
            return await api.get('/labo/exams');
        } catch (err) {
            // Secours hors ligne (caisse : facturation d'un examen). Garde de
            // role explicite : le labo/admin hors ligne voit l'erreur reseau,
            // jamais un catalogue local qui n'est pas synchronise pour eux.
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['secretaire', 'medecin', 'nurse', 'laborantin'])) {
                return { data: await getExamCatalogLocal() };
            }
            throw err;
        }
    },

    async createExam(examData) {
        return api.post('/labo/exams', examData);
    },

    async updateExam(id, examData) {
        return api.put(`/labo/exams/${id}`, examData);
    },

    async deleteExam(id) {
        return api.delete(`/labo/exams/${id}`);
    },

    // --- SOUS-RESSOURCES : PARAMÈTRES (Leucocytes, etc.) ---
    
    async getExamParams(examId) {
        return api.get(`/labo/exams/${examId}/params`);
    },

    async addExamParam(examId, paramData) {
        // paramData = { nom_parametre: "...", unite: "...", type_resultat: "numeric" }
        return api.post(`/labo/exams/${examId}/params`, paramData);
    },

    async deleteExamParam(paramId) {
        return api.delete(`/labo/params/${paramId}`);
    },

    // ============================================================
    // 2. GESTION DES DOSSIERS (Workflow Laborantin)
    // ============================================================

    /**
     * Recherche chirurgicale : Patients + Prescriptions Actives
     * Point d'entrée pour la barre de recherche du laborantin.
     */

    searchInternalPrescriptions: async (query) => {
        try {
            return await api.get('/labo/search-internal', {
                params: { q: query }
            });
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['laborantin'])) {
                const { db } = await import('@/powersync-client/client');
                const q = `%${query}%`;
                const rows = await db.getAll(
                    `SELECT p.patient_id AS patient_id, p.first_name || ' ' || p.last_name AS nom,
                            p.code_patient AS patient_code, lp.prescribed_by_name,
                            lp.lab_exams_list, lp.server_id AS prescription_id
                     FROM patients_lookup p
                     LEFT JOIN lab_pending_prescriptions lp ON lp.patient_id = p.patient_id
                     WHERE p.first_name LIKE ? OR p.last_name LIKE ? OR p.code_patient LIKE ?
                     LIMIT 20`,
                    [q, q, q]
                );
                return { data: rows.map((r) => ({
                    id: r.patient_id,
                    nom: r.nom,
                    patient_code: r.patient_code,
                    prescribed_by_name: r.prescribed_by_name || null,
                    exams_prescribed: r.lab_exams_list ? JSON.parse(r.lab_exams_list) : [],
                    prescription_id: r.prescription_id || null,
                })) };
            }
            throw err;
        }
    },

    // 🔍 Recherche globale (Code, Nom patient)
    async searchFiles(query) {
        return api.get('/labo/search', { params: { q: query } });
    },

    createPatient(payload) {
        // Endpoint pour créer un patient (externe)
        return api.post('/patients', payload);
    },

    // 📝 Création d'un dossier (vide ou pré-rempli)
    async createResult(payload) {
        return api.post('/labo/results', payload);
    },

    // 🚀 Création par lot (Batch)
    async createBatchResults(payload) {
        return api.post('/labo/results/batch', payload);
    },

    // 🔗 Récupérer les frères et sœurs d'un lot
    async getResultsByBatch(batchId) {
        return api.get(`/labo/batch/${batchId}`);
    },
    // --------------------------

    // 👁️ Visualiser le détail d'un dossier (Feuille de paillasse)
    async getResultDetail(resultId) {
        try {
            return await api.get(`/labo/results/${resultId}`);
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['laborantin'])) {
                const { db } = await import('@/powersync-client/client');
                const result = await db.get(
                    `SELECT lr.id AS result_id, lr.code_lab_patient AS code, lr.status, lr.note,
                            lr.patient_id, lr.examen_id, lr.external_patient_info,
                            COALESCE(p.first_name || ' ' || p.last_name, json_extract(lr.external_patient_info, '$.nom')) AS patient_nom,
                            ec.nom AS examen_nom
                     FROM lab_results lr
                     LEFT JOIN patients_lookup p ON p.patient_id = lr.patient_id
                     LEFT JOIN exam_catalog ec ON ec.server_id = lr.examen_id
                     WHERE lr.id = ?`,
                    [resultId]
                );
                // Deux sortes de lignes locales pour un meme dossier (voir
                // AppSchema.js sur lab_result_details) :
                //  - creee hors ligne : seul result_uuid est renseigne, pas de
                //    vrai detail_id serveur -> detail_id synthetise NEGATIF
                //    (-parametre_id). Un serial Postgres est toujours positif :
                //    aucune collision possible avec un vrai detail_id ou
                //    parametre_id, cote client comme cote serveur
                //    (save_results_values traite une cle negative comme
                //    "-parametre_id", sans ambiguite).
                //  - telechargee (stream lab_active_result_details, dossier deja
                //    passe par au moins un cycle de synchro, y compris un
                //    dossier cree hors ligne puis synchronise) : seul result_id
                //    est renseigne, et la PK locale d.id EST le vrai detail_id
                //    serveur (detail_id::text AS id) -> reutilise tel quel.
                // Sans la seconde branche du OR, un dossier deja synchronise
                // rouvert hors ligne n'affichait aucun parametre.
                const rawDetails = await db.getAll(
                    `SELECT CASE WHEN d.result_id IS NOT NULL THEN CAST(d.id AS INTEGER)
                                 ELSE -d.parametre_id END AS detail_id,
                            d.parametre_id AS parametre_id,
                            rp.nom_parametre AS nom, rp.unite, rp.input_type, rp.options_list AS options,
                            d.valeur_text AS valeur
                     FROM lab_result_details d
                     JOIN reference_lab_params rp ON rp.server_id = d.parametre_id
                     WHERE d.result_uuid = ?
                        OR d.result_id = (SELECT server_id FROM lab_results WHERE id = ?)`,
                    [resultId, resultId]
                );
                // Garde-fou : si les deux sortes de lignes coexistaient un
                // instant pour un meme parametre (fenetre de reconciliation
                // PowerSync), on garde la ligne locale (detail_id negatif),
                // porteuse de la saisie hors ligne la plus recente.
                const byParam = new Map();
                for (const d of rawDetails) {
                    const prev = byParam.get(d.parametre_id);
                    if (!prev || (d.detail_id < 0 && prev.detail_id >= 0)) {
                        byParam.set(d.parametre_id, d);
                    }
                }
                const details = [...byParam.values()];

                const paramIds = details.map((d) => d.parametre_id);
                let rangesByParam = {};
                if (paramIds.length) {
                    const placeholders = paramIds.map(() => '?').join(',');
                    const rangeRows = await db.getAll(
                        `SELECT parametre_id, sexe, valeur_min AS min, valeur_max AS max
                         FROM reference_lab_ranges
                         WHERE parametre_id IN (${placeholders})`,
                        paramIds
                    );
                    rangesByParam = rangeRows.reduce((acc, r) => {
                        (acc[r.parametre_id] ||= []).push({ sexe: r.sexe, min: r.min, max: r.max });
                        return acc;
                    }, {});
                }

                return {
                    data: {
                        result_id: resultId,
                        id: resultId,
                        code: result?.code ?? null,
                        status: result?.status ?? null,
                        note: result?.note ?? null,
                        // Best-effort seulement : pas d'acces local a l'age/sexe pour
                        // un patient interne (patients_lookup n'a pas ces colonnes).
                        patient_info: { nom: result?.patient_nom || '', sexe: '-', age: '-' },
                        examen_nom: result?.examen_nom || '',
                        details: details.map((d) => ({
                            detail_id: d.detail_id,
                            parametre_id: d.parametre_id,
                            nom: d.nom,
                            unite: d.unite,
                            input_type: d.input_type,
                            options: d.options,
                            valeur: d.valeur,
                            // L'interpretation fait toujours autorite cote serveur,
                            // jamais dupliquee/calculee ici.
                            interpretation: null,
                            is_abnormal: false,
                            ranges: rangesByParam[d.parametre_id] || [],
                        })),
                    },
                };
            }
            throw err;
        }
    },

    // 🧪 Saisir/Sauvegarder les valeurs
    async updateResultValues(resultId, payload) {
        // Le payload est déjà parfaitement formaté par le composant Vue
        try {
            return await api.put(`/labo/results/${resultId}/values`, payload);
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['laborantin'])) {
                const { db } = await import('@/powersync-client/client');
                await db.writeTransaction(async (tx) => {
                    // resultId peut etre soit la PK locale (uuid, dossier ouvert
                    // hors ligne), soit le result_id entier reel du serveur
                    // (dossier ouvert en ligne puis reseau coupe avant Valider/
                    // Sauvegarder - LabTechnician.vue recoit alors l'entier de
                    // get_result_detail). WHERE id = ? sur lab_results ne matche
                    // jamais un entier (id local est toujours un uuid), d'ou la
                    // resolution explicite ci-dessous avant toute ecriture sur
                    // lab_results/lab_result_details (branche result_id entier).
                    const localRow = await tx.getOptional(
                        'SELECT id FROM lab_results WHERE id = ? OR server_id = ?',
                        [resultId, resultId]
                    );
                    const localResultId = localRow?.id || resultId;
                    // payload.values est toujours { [detailId]: { valeur, flag, interpretation } }
                    // (LabTechnician.vue::submit()), detailId venant de
                    // getResultDetail ci-dessus - deux espaces d'identifiants :
                    //  - negatif : ligne creee hors ligne, detailId = -parametre_id,
                    //    resolue par (result_uuid, parametre_id) ;
                    //  - positif ou nul : ligne telechargee, detailId = vrai
                    //    detail_id serveur = PK locale de la ligne, mise a jour
                    //    directe.
                    // flag/interpretation ne sont jamais persistes cote client
                    // (calcules serveur uniquement).
                    for (const [detailId, data] of Object.entries(payload.values || {})) {
                        const numericId = Number(detailId);
                        const valeur = data?.valeur;
                        if (numericId >= 0) {
                            const downloaded = await tx.getOptional(
                                'SELECT id FROM lab_result_details WHERE id = ?',
                                [String(numericId)]
                            );
                            if (downloaded) {
                                await tx.execute(
                                    'UPDATE lab_result_details SET valeur_text = ? WHERE id = ?',
                                    [String(valeur ?? ''), downloaded.id]
                                );
                            } else {
                                console.warn(`Detail labo ${detailId} introuvable localement, valeur ignoree.`);
                            }
                            continue;
                        }
                        const parametreId = -numericId;
                        const existing = await tx.getOptional(
                            'SELECT id FROM lab_result_details WHERE result_uuid = ? AND parametre_id = ?',
                            [resultId, parametreId]
                        );
                        if (existing) {
                            await tx.execute(
                                'UPDATE lab_result_details SET valeur_text = ? WHERE id = ?',
                                [String(valeur ?? ''), existing.id]
                            );
                        } else {
                            await tx.execute(
                                `INSERT INTO lab_result_details (id, result_uuid, parametre_id, valeur_text)
                                 VALUES (?, ?, ?, ?)`,
                                [crypto.randomUUID(), resultId, parametreId, String(valeur ?? '')]
                            );
                        }
                    }
                    if (payload.completed) {
                        // Sentinelle LOCALE uniquement : '_local_completing' ne
                        // vient jamais du serveur (qui n'envoie que pending/
                        // partial/completed). Elle seule signale au connecteur
                        // (DossierConnector.js, lab_results:PATCH) un "Valider &
                        // Cloturer" hors ligne - 'partial' ne le pouvait pas,
                        // c'est aussi le statut serveur legitime d'un dossier
                        // deja partiellement saisi, qu'un simple brouillon
                        // aurait alors finalise a tort. Le statut final reste
                        // calcule cote serveur a la synchronisation. Exclu de la
                        // paillasse locale (filtre status IN pending/partial).
                        await tx.execute("UPDATE lab_results SET status = '_local_completing' WHERE id = ?", [localResultId]);
                    }
                    if (payload.note !== undefined && payload.note !== null) {
                        await tx.execute('UPDATE lab_results SET note = ? WHERE id = ?', [payload.note, localResultId]);
                    }
                });
                return { data: { success: true } };
            }
            throw err;
        }
    },

    // 🗑️ Supprimer un dossier
    async deleteResult(resultId) {
        return api.delete(`/labo/results/${resultId}`);
    },

    // 🖨️ Télécharger le PDF
    async downloadResultPDF(resultId) {
        return api.get(`/labo/results/${resultId}/pdf`, {
            responseType: 'blob' // CRUCIAL : Indique qu'on reçoit un fichier binaire
        });
    },

    // Ajoutez ceci dans la section "GESTION DES DOSSIERS"
    async getWorklist() {
        return api.get('/labo/worklist');
    },

    async getPaillasseList() {
        try {
            return await api.get('/labo/paillasse');
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['laborantin'])) {
                const { db } = await import('@/powersync-client/client');
                // Champs alignes sur le contrat reel lu par LabTechnician.vue
                // (list template), pas sur LabValidation.vue qui est orphelin.
                // patients_lookup n'a ni sexe ni date de naissance -> '-' pour un
                // patient interne ; pour un patient externe on lit le json
                // external_patient_info sauvegarde a la creation du dossier.
                const rows = await db.getAll(
                    `SELECT lr.id AS result_id,
                            COALESCE(p.first_name || ' ' || p.last_name, json_extract(lr.external_patient_info, '$.nom')) AS patient_name,
                            ec.nom AS examen_nom,
                            CASE WHEN lr.patient_id IS NULL
                                 THEN COALESCE(json_extract(lr.external_patient_info, '$.sexe'), '-')
                                 ELSE '-' END AS patient_sexe,
                            CASE WHEN lr.patient_id IS NULL
                                 THEN COALESCE(json_extract(lr.external_patient_info, '$.age'), '-')
                                 ELSE '-' END AS patient_age,
                            CASE WHEN lr.patient_id IS NULL THEN 1 ELSE 0 END AS is_external
                     FROM lab_results lr
                     LEFT JOIN patients_lookup p ON p.patient_id = lr.patient_id
                     LEFT JOIN exam_catalog ec ON ec.server_id = lr.examen_id
                     WHERE lr.status IN ('pending', 'partial')
                       AND NOT EXISTS (
                         SELECT 1 FROM sync_quarantine sq
                         WHERE sq.kind IN ('lab_result', 'lab_result_detail') AND sq.local_id = lr.id
                       )
                     ORDER BY lr.test_date DESC`
                );
                return { data: rows };
            }
            throw err;
        }
    },

    // ============================================================
    // 3. STATS & HISTORIQUE
    // ============================================================

    async getPaginatedHistory(params) {
        // params attend un objet du type { page: 1, limit: 20, search: "nom", status: "completed" }
        return api.get('/labo/history/paginated', { params });
    },

    async getPatientHistory(patientId) {
        return api.get(`/labo/patient/${patientId}/history`);
    },

    async getStats(period = 'month') {
        // Envoie ?period=month (ou day, ou year) dans l'URL
        return api.get('/labo/stats', { params: { period } });
    }
};