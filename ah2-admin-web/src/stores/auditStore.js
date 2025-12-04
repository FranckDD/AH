// src/stores/auditStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';

// MOCK : audit_access (Connexions - Inchangé)
const mockAccessLogs = [
    { access_id: 105, username: 'ToxicoManager', action_type: 'LOGIN', timestamp: '2023-11-26 14:00:00', ip_address: '10.0.0.5', details: 'Connexion réussie' },
    { access_id: 104, username: 'Admin', action_type: 'LOGOUT', timestamp: '2023-11-26 12:00:00', ip_address: '192.168.1.10', details: 'Déconnexion manuelle' },
    { access_id: 103, username: 'Mme. Nurse', action_type: 'LOGIN_FAILED', timestamp: '2023-11-26 08:20:00', ip_address: '192.168.1.15', details: 'Mot de passe incorrect' },
];

// 🟢 MOCK : audit_user_actions (Reflétant tes contrôleurs)
// Les types de ressources correspondent à tes modules backend
const mockActionLogs = [
    // Toxico
    { action_id: 601, username: 'Dr. Nkono', resource_type: 'TOXICO', action_performed: 'EVALUATION', timestamp: '2023-11-26 15:30:00', details: 'Ajout évaluation phase 2 (Marie Curie)' },
    // Pharma / Stock
    { action_id: 602, username: 'Pharmacien', resource_type: 'PHARMACY', action_performed: 'DISPENSE', timestamp: '2023-11-26 14:10:00', details: 'Sortie stock: Doliprane x2 boites' },
    // Caisse
    { action_id: 603, username: 'Caissier', resource_type: 'CAISSE', action_performed: 'PAYMENT', timestamp: '2023-11-26 11:45:00', details: 'Encaissement facture #FAC-2023-889' },
    // Médical
    { action_id: 604, username: 'Dr. House', resource_type: 'MEDICAL_RECORD', action_performed: 'CREATE', timestamp: '2023-11-26 09:15:00', details: 'Création dossier médical initial' },
    // Labo
    { action_id: 605, username: 'Laborantin', resource_type: 'LAB', action_performed: 'VALIDATE', timestamp: '2023-11-26 10:20:00', details: 'Validation résultats NFS' },
    // Spirituel
    { action_id: 606, username: 'Père Jean', resource_type: 'SPIRITUEL', action_performed: 'NOTE', timestamp: '2023-11-26 16:00:00', details: 'Ajout note consultation spirituelle' },
    // Admin
    { action_id: 607, username: 'Admin', resource_type: 'USER', action_performed: 'UPDATE', timestamp: '2023-11-26 08:05:00', details: 'Changement rôle utilisateur ID 45' },
];

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const useAuditStore = defineStore('audit', () => {
    const accessLogs = ref([]);
    const actionLogs = ref([]);
    const isLoading = ref(false);

    async function fetchAccessLogs() {
        isLoading.value = true;
        await delay(500);
        accessLogs.value = [...mockAccessLogs];
        isLoading.value = false;
    }

    async function fetchActionLogs() {
        isLoading.value = true;
        await delay(500);
        actionLogs.value = [...mockActionLogs];
        isLoading.value = false;
    }

    return { 
        accessLogs, 
        actionLogs, 
        isLoading, 
        fetchAccessLogs, 
        fetchActionLogs 
    };
});