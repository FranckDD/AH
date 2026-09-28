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

    async searchPatients(query) {
        if (!query || query.trim().length < 2) return { data: { data: [], total: 0 } };
        return api.get('/patients/', { params: { search: query.trim(), per_page: 8 } });
    },

    // --- ÉCRITURE ---

    async admitPatient(data) {
        const admissionDate = data.admissionDate;
        const psychologistId = data.psychologist;

        if (!admissionDate) {
            throw new Error("La date d'admission est requise.");
        }
        const psyIdNumber = Number(psychologistId);
        if (isNaN(psyIdNumber) || psyIdNumber <= 0) {
            throw new Error("L'ID du psychologue est invalide ou manquant.");
        }

        const formData = new FormData();

        if (data.patientId) {
            formData.append('patientId', data.patientId);
        } else {
            const dob = data.dob;
            if (!dob) throw new Error("La date de naissance est requise pour un nouveau patient.");
            if (new Date(dob) > new Date(admissionDate)) {
                throw new Error("La date de naissance ne peut pas être postérieure à la date d'admission.");
            }
            formData.append('firstName', data.firstName || '');
            formData.append('lastName', data.lastName || '');
            formData.append('dob', dob);
            formData.append('mothersName', data.mothersName || '');
            formData.append('address', data.address || '');
            formData.append('contact', data.contact || '');
        }

        formData.append('admissionDate', admissionDate);
        formData.append('substance', data.substance || '');
        formData.append('psychologist', psyIdNumber);
        formData.append('guardianName', data.guardianName || '');
        formData.append('guardianContact', data.guardianContact || '');
        formData.append('notes', data.notes || '');

        if (data.consentFile && data.consentFile instanceof File) {
            formData.append('consentFile', data.consentFile);
        }

        return api.post('/toxico/admission', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
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