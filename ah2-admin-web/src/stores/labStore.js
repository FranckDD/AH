// src/stores/labStore.js
import { defineStore } from 'pinia';
import { LabGateway } from '@/services/labGateway';

export const useLabStore = defineStore('lab', {
    state: () => ({
        // --- CONFIGURATION ---
        exams: [],                // Liste globale des examens
        currentExamParams: [],    // Liste des paramètres de l'examen en cours d'édition
        worklist: [],
        paillasseList: [],  // Technique : Dossiers en cours d'analyse

        // --- OPÉRATIONNEL ---
        searchResults: [],        // Résultats de la barre de recherche
        paginatedHistory: {
            items: [],
            total_items: 0,
            total_pages: 1,
            current_page: 1,
            limit: 20
        },
        currentResult: null,      // Le dossier complet affiché (détails + valeurs)
        patientHistory: [],       // Historique d'un patient spécifique
        batchSiblings: [],
        stats: null,              // Dashboard KPIs

        // --- UI STATE ---
        loading: false,
        error: null,
        successMessage: null
    }),

    getters: {
        getExamById: (state) => (id) => state.exams.find(e => e.id === id),
        // Compteurs utiles pour les badges de notification
        pendingWorklistCount: (state) => state.worklist.length,
        pendingPaillasseCount: (state) => state.paillasseList.length,
    },

    actions: {
        // ============================================================
        // A. CONFIGURATION (Examens & Paramètres)
        // ============================================================
        
        async fetchExams() {
            this.loading = true;
            try {
                const response = await LabGateway.getAllExams();
                this.exams = response.data;
            } catch (err) {
                this.error = "Erreur chargement examens.";
                console.error(err);
            } finally {
                this.loading = false;
            }
        },
        

        // Charge les paramètres (ex: Leucocytes) pour un examen donné
        async fetchExamParams(examId) {
            this.currentExamParams = []; 
            try {
                const response = await LabGateway.getExamParams(examId);
                this.currentExamParams = response.data;
            } catch (err) {
                console.error("Erreur chargement paramètres", err);
            }
        },

        async addParam(examId, paramData) {
            try {
                await LabGateway.addExamParam(examId, paramData);
                await this.fetchExamParams(examId); // Recharger la liste
                return true;
            } catch (err) {
                this.error = "Impossible d'ajouter le paramètre.";
                return false;
            }
        },

        async deleteParam(paramId, examId) {
            try {
                await LabGateway.deleteExamParam(paramId);
                // On retire localement pour éviter un appel réseau si on veut
                this.currentExamParams = this.currentExamParams.filter(p => p.id !== paramId);
            } catch (err) {
                this.error = "Erreur suppression paramètre.";
            }
        },

        // ============================================================
        // B. WORKFLOW LABORATOIRE (Search, Create, Fill)
        // ============================================================

        async searchPatients(query) {
            this.loading = true;
            this.searchResults = [];
            try {
                const response = await LabGateway.searchFiles(query);
                this.searchResults = response.data;
            } catch (err) {
                console.error(err);
            } finally {
                this.loading = false;
            }
        },

        async searchInternal(query) {
            // Si la recherche est vide, on vide la liste et on arrête
            if (!query || query.trim() === '') {
                this.searchResults = [];
                return;
            }

            this.loading = true;
            this.searchResults = []; // On vide avant de chercher pour éviter la confusion
            
            try {
                // Appel au Gateway sur la route /search-internal
                const response = await LabGateway.searchInternalPrescriptions(query);
                
                // Le backend renvoie déjà [{patient_id, nom, prescription_id...}, ...]
                this.searchResults = response.data;
            } catch (err) {
                console.error("Erreur recherche interne:", err);
                this.error = "Erreur lors de la recherche patient.";
            } finally {
                this.loading = false;
            }
        },

        // 🟢 NOUVELLE ACTION : Chargement de l'historique avec pagination
        async fetchPaginatedHistory(params = {}) {
            this.loading = true;
            this.error = null;
            try {
                // Par défaut, s'assurer qu'on a au moins la page 1 et une limite
                const queryParams = {
                    page: params.page || 1,
                    limit: params.limit || 20,
                    search: params.search || null,
                    status: params.status || null
                };

                const response = await LabGateway.getPaginatedHistory(queryParams);
                
                // On met à jour l'objet complet avec les données et les métadonnées de pagination
                this.paginatedHistory = response.data;
                
            } catch (err) {
                console.error("Erreur lors du chargement de l'historique paginé:", err);
                this.error = "Impossible de charger l'historique.";
            } finally {
                this.loading = false;
            }
        },

        async createExternalPatient(patientData) {
            this.loading = true;
            try {
                // Adapte 'createPatient' selon ton API réelle
                const response = await LabGateway.createPatient(patientData);
                this.successMessage = "Patient externe créé avec succès";
                return response.data; // Doit retourner l'objet patient créé
            } catch (err) {
                this.error = "Erreur lors de la création du patient";
                return null;
            } finally {
                this.loading = false;
            }
        },

        // Créer un dossier
        async createResult(payload) {
            this.loading = true;
            this.error = null;
            try {
                const response = await LabGateway.createResult(payload);
                this.successMessage = "Dossier créé avec succès.";
                return response.data; // Retourne l'objet (avec result_id) pour redirection
            } catch (err) {
                this.error = err.response?.data?.detail || "Erreur création dossier.";
                throw err;
            } finally {
                this.loading = false;
            }
        },

        // src/stores/labStore.js (extrait de l'action)

       async createBatchRequest(payload) {
            this.loading = true;
            this.error = null;
            this.successMessage = null;

            try {
                const { useAuthStore } = await import('@/stores/auth');
                const authStore = useAuthStore();

                if (authStore.hasRole(['laborantin'])) {
                    const { db } = await import('@/powersync-client/client');
                    const batchUuid = crypto.randomUUID();
                    let createdCount = 0;

                    await db.writeTransaction(async (tx) => {
                        for (const item of payload.results) {
                            const resultUuid = crypto.randomUUID();
                            await tx.execute(
                                `INSERT INTO lab_results (
                                    id, patient_id, patient_uuid, test_type, status,
                                    examen_id, prescribed_by, prescribed_by_name,
                                    origin_prescription_id, batch_uuid, external_patient_info
                                 ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)`,
                                [
                                    resultUuid, payload.patient_id || null, payload.patient_uuid || null,
                                    'Analyse Labo', item.examen_id, payload.prescribed_by_id || null,
                                    payload.prescribed_by_name || null, payload.origin_prescription_id || null,
                                    batchUuid, payload.external_patient_info ? JSON.stringify(payload.external_patient_info) : null,
                                ]
                            );
                            const params = await tx.getAll(
                                'SELECT id FROM reference_lab_params WHERE examen_id = ?',
                                [item.examen_id]
                            );
                            for (const p of params) {
                                await tx.execute(
                                    `INSERT INTO lab_result_details (id, result_uuid, parametre_id, valeur_text)
                                     VALUES (?, ?, ?, '')`,
                                    [crypto.randomUUID(), resultUuid, p.id]
                                );
                            }
                            createdCount += 1;
                        }
                    });

                    this.successMessage = `${createdCount} examen(s) enregistré(s) localement, en attente de synchronisation.`;
                    return { success: true, count: createdCount, shared_code: null, batch_id: batchUuid };
                }

                const response = await LabGateway.createBatchResults(payload);
                const data = response.data;
                const count = data.count || 0;
                const codeAffiche = data.shared_code || "EN_COURS...";
                this.successMessage = `Succès : ${count} Examens créés sous le numéro ${codeAffiche}.`;
                return data;

            } catch (err) {
                console.error("Erreur Batch Store:", err);
                if (err.response && err.response.data && err.response.data.detail) {
                    const detail = err.response.data.detail;
                    this.error = Array.isArray(detail)
                        ? "Erreur de format : " + detail[0].msg
                        : detail;
                } else {
                    this.error = "Erreur lors de l'enregistrement groupé.";
                }
                return null;
            } finally {
                this.loading = false;
            }
        },
        async downloadPDF(resultId, filename = 'resultat.pdf') {
            try {
                const response = await LabGateway.downloadResultPDF(resultId);
                
                // Création du lien invisible pour télécharger le Blob
                const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', filename);
                document.body.appendChild(link);
                link.click();
                
                link.remove();
                window.URL.revokeObjectURL(url);
                return true;
            } catch (err) {
                console.error("Erreur PDF", err);
                this.error = "Erreur lors de la génération du PDF.";
                return false;
            }
        },

        async fetchDashboardData() {
            this.loading = true;
            try {
                // On lance les deux requêtes en parallèle
                const [statsRes, worklistRes] = await Promise.all([
                    LabGateway.getStats(),
                    LabGateway.getWorklist()
                ]);
                this.stats = statsRes.data;
                this.worklist = worklistRes.data;
            } catch (err) {
                console.error("Erreur dashboard", err);
            } finally {
                this.loading = false;
            }
        },

        // Charger un dossier complet pour affichage/saisie
        async fetchResultDetail(resultId) {
            // AJOUT DE CETTE LIGNE DE SÉCURITÉ
            if (!resultId || resultId === 'undefined') {
                console.warn("Appel fetchResultDetail annulé: ID invalide");
                return null;
            }

            this.loading = true;
            this.batchSiblings = [];
            try {
                const res = await LabGateway.getResultDetail(resultId);
                this.currentResult = res.data;
                
                if (res.data.batch_id) {
                    try {
                        const batchRes = await LabGateway.getResultsByBatch(res.data.batch_id);
                        this.batchSiblings = batchRes.data;
                    } catch (e) { console.warn(e); }
                }
                return res.data;
            } catch (err) { 
                this.error = "Erreur chargement dossier"; 
                return null;
            } finally {
                this.loading = false;
            }
        },


        // Sauvegarder les valeurs saisies par le laborantin
        // payload = { values: {detailId_ou_parametreId: valeur}, completed: bool, note: string|null }
        async saveValues(resultId, payload) {
            this.loading = true;
            this.error = null;
            this.successMessage = null;
            try {
                await LabGateway.updateResultValues(resultId, payload);

                if (payload.completed) {
                    this.successMessage = "Dossier validé et clôturé !";
                    this.paillasseList = this.paillasseList.filter(item => item.result_id !== resultId);
                    this.currentResult = null;
                } else {
                    this.successMessage = "Brouillon sauvegardé.";
                    await this.fetchResultDetail(resultId);
                }

                return true;
            } catch (err) {
                this.error = "Erreur lors de la sauvegarde.";
                return false;
            } finally {
                this.loading = false;
            }
        },

        async fetchWorklist() {
            this.loading = true;
            try {
                const res = await LabGateway.getWorklist();
                this.worklist = res.data;
            } catch (err) {
                console.error("Erreur worklist", err);
            } finally {
                this.loading = false;
            }
        },

        async fetchPaillasseList() {
            this.loading = true;
            try {
                const res = await LabGateway.getPaillasseList();
                this.paillasseList = res.data;
            } catch (err) {
                console.error("Erreur paillasse list", err);
            } finally {
                this.loading = false;
            }
        },

        // ============================================================
        // C. UTILITAIRES
        // ============================================================
        
        async fetchDashboardStats(period = 'month') { // <-- Accepte la période
            try {
                const res = await LabGateway.getStats(period); // <-- Passe la période
                this.stats = res.data;
            } catch (e) { 
                console.error("Erreur chargement des stats dashboard:", e); 
            }
        },

        // Utile pour le bouton "Retour"
        clearCurrentResult() {
            this.currentResult = null;
            this.error = null;
            this.successMessage = null;
        },

        clearMessages() {
            this.error = null;
            this.successMessage = null;
        }
    }
});