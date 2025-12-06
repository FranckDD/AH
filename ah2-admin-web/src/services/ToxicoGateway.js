import api from '@/services/api';


export const ToxicoGateway = {
    // --- LECTURE ---
    
    async getPsychologists() {
        //console.log("[GATEWAY] getPsychologists appelé");
        return api.get('/toxico/psychologists');
    },

    // 👇 NOUVELLE MÉTHODE POUR LES STATS DU BACKEND 👇
    async getDashboardStats() {
        //console.log("[GATEWAY] getDashboardStats appelé");
        // Appel GET sur le nouvel endpoint FastAPI: /toxico/stats/dashboard
        return api.get('/toxico/stats/dashboard'); 
    },

    async listPatients(params) {
        //console.log("[GATEWAY] listPatients appelé avec params:", params);
        const query = {};
        for (const key in params) {
            if (params[key] !== null && params[key] !== '' && params[key] !== undefined) {
                query[key] = params[key];
            }
        }
       // console.log("[GATEWAY] Query final:", query);
        return api.get('/toxico/patients', { params: query });
    },

    async getPatientDetails(patientId) {
       // console.log("[GATEWAY] getPatientDetails appelé pour patientId:", patientId);
        return api.get(`/toxico/patients/${patientId}`);
    },

    // --- ÉCRITURE ---

    async admitPatient(data) {
        // ---------------------------------------------------------
        // 1. EXTRACTION ET VALIDATION (D'ABORD !)
        // ---------------------------------------------------------
        // Il faut sortir les variables AVANT de les utiliser dans les 'if'
        const dob = data.dob;
        const admissionDate = data.admissionDate;
        const psychologistId = data.psychologist;

        // Validation des dates
        if (!dob || !admissionDate) {
            throw new Error("Les dates de naissance et d'admission sont requises.");
        }

        // Validation logique des dates
        if (new Date(dob) > new Date(admissionDate)) {
            throw new Error("La date de naissance ne peut pas être postérieure à la date d'admission.");
        }
        
        // Validation de l'ID psy
        const psyIdNumber = Number(psychologistId);
        if (isNaN(psyIdNumber) || psyIdNumber <= 0) {
            throw new Error("L'ID du psychologue est invalide ou manquant.");
        }

        // ---------------------------------------------------------
        // 2. CONSTRUCTION DU FORMDATA
        // ---------------------------------------------------------
        const formData = new FormData();

        // Ajout des champs texte
        formData.append('firstName', data.firstName || '');
        formData.append('lastName', data.lastName || '');
        formData.append('dob', dob);
        formData.append('mothersName', data.mothersName || '');
        formData.append('address', data.address || '');
        formData.append('contact', data.contact || '');
        formData.append('admissionDate', admissionDate);
        formData.append('substance', data.substance || '');
        formData.append('psychologist', psyIdNumber); // On envoie l'ID validé
        formData.append('guardianName', data.guardianName || '');
        formData.append('guardianContact', data.guardianContact || '');
        formData.append('notes', data.notes || '');

        // 3. Ajout du FICHIER (si présent)
        if (data.consentFile && data.consentFile instanceof File) {
            formData.append('consentFile', data.consentFile);
        }

        // ---------------------------------------------------------
        // 3. ENVOI (La correction spécifique)
        // ---------------------------------------------------------
        // On surcharge le header JUSTE pour cette requête.
        // Cela garantit qu'Axios n'utilise pas 'application/json' défini dans api.js
        return api.post('/toxico/admission', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
    },

    async submitEvaluation(data) {
        //console.log("[GATEWAY] submitEvaluation appelé avec données:", data);
        
        // 🟢 Normalisation et validation
        const payload = {
            dossier_id: Number(data.dossier_id || data.dossierId || 0),
            decision: String(data.decision || '').toUpperCase(),
            observation: String(data.observation || '').trim(),
            recommendation: data.recommendation ? String(data.recommendation).trim() : null,
            targetPhase: Number(data.targetPhase || data.target_phase || 0)
        };
        
        // Validation
        if (payload.dossier_id <= 0) {
            throw new Error("dossier_id invalide");
        }
        
        if (!['MAINTAIN', 'PROGRESS', 'REGRESS'].includes(payload.decision)) {
            throw new Error(`Decision invalide: ${payload.decision}. Doit être MAINTAIN, PROGRESS ou REGRESS`);
        }
        
        if (!payload.observation || payload.observation.length < 50) {
            throw new Error("Observation requise (min 50 caractères)");
        }
        
        if (payload.targetPhase < 1 || payload.targetPhase > 4) {
            throw new Error(`targetPhase invalide: ${payload.targetPhase}. Doit être entre 1 et 4`);
        }
        
       // console.log("[GATEWAY] Payload évaluation normalisé:", payload);
       /* console.log("[GATEWAY] Types:", {
            dossier_id: typeof payload.dossier_id,
            decision: typeof payload.decision,
            targetPhase: typeof payload.targetPhase
        });*/
        
        return api.post('/toxico/evaluation', payload);
    },

    async dischargePatient(dossierId) {
        //console.log("[GATEWAY] dischargePatient appelé pour dossierId:", dossierId);
        return api.post(`/toxico/discharge/${dossierId}`);
    }

    
};