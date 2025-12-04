import api from '@/services/api';


export const ToxicoGateway = {
    // --- LECTURE ---
    
    async getPsychologists() {
        //console.log("[GATEWAY] getPsychologists appelé");
        return api.get('/toxico/psychologists');
    },

    // 👇 NOUVELLE MÉTHODE POUR LES STATS DU BACKEND 👇
    async getDashboardStats() {
        console.log("[GATEWAY] getDashboardStats appelé");
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
        //console.log("[GATEWAY] admitPatient appelé avec données:", data);
        
        // 🟢 Normalisation et validation
        const payload = {
            firstName: String(data.firstName || '').trim(),
            lastName: String(data.lastName || '').trim(),
            dob: String(data.dob || ''), // Doit être YYYY-MM-DD
            mothersName: String(data.mothersName || '').trim(),
            address: String(data.address || '').trim(),
            contact: String(data.contact || '').trim(),
            admissionDate: String(data.admissionDate || ''), // Doit être YYYY-MM-DD
            substance: String(data.substance || '').trim(),
            psychologist: Number(data.psychologist), // ⚠️ Convertir en nombre
            guardianName: String(data.guardianName || '').trim(),
            guardianContact: String(data.guardianContact || '').trim(),
            consentFile: String(data.consentFile || '').trim(),
            notes: String(data.notes || '').trim()
        };
        
        // Validation supplémentaire
        if (!payload.dob || !payload.admissionDate) {
            throw new Error("Les dates sont requises");
        }
        
        if (isNaN(payload.psychologist) || payload.psychologist <= 0) {
            throw new Error("Psychologist ID invalide");
        }
        
       // console.log("[GATEWAY] Payload normalisé:", payload);
        /*console.log("[GATEWAY] Types:", {
            psychologist: typeof payload.psychologist,
            dob: typeof payload.dob,
            admissionDate: typeof payload.admissionDate
        });*/
        
        return api.post('/toxico/admission', payload);
    },

    async submitEvaluation(data) {
        console.log("[GATEWAY] submitEvaluation appelé avec données:", data);
        
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
        
        if (!payload.observation || payload.observation.length < 5) {
            throw new Error("Observation requise (min 5 caractères)");
        }
        
        if (payload.targetPhase < 1 || payload.targetPhase > 4) {
            throw new Error(`targetPhase invalide: ${payload.targetPhase}. Doit être entre 1 et 4`);
        }
        
        console.log("[GATEWAY] Payload évaluation normalisé:", payload);
        console.log("[GATEWAY] Types:", {
            dossier_id: typeof payload.dossier_id,
            decision: typeof payload.decision,
            targetPhase: typeof payload.targetPhase
        });
        
        return api.post('/toxico/evaluation', payload);
    },

    async dischargePatient(dossierId) {
        //console.log("[GATEWAY] dischargePatient appelé pour dossierId:", dossierId);
        return api.post(`/toxico/discharge/${dossierId}`);
    }

    
};