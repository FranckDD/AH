import axios from 'axios';
// 🟢 CORRECTION 1 : Import du fichier 'auth' (sans le 'Store' dans le nom du fichier)
import { useAuthStore } from '@/stores/auth'; 
import router from '@/router';

const API_URL = 'http://localhost:8000'; 

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});

// 1. Intercepteur de REQUÊTE
api.interceptors.request.use(config => {
    // 🟢 CORRECTION 2 : Utilisation de la clé 'token' (comme défini dans auth.js)
    // Au lieu de 'access_token' qui ne marcherait pas
    const token = localStorage.getItem('token');
    
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, error => {
    return Promise.reject(error);
});

// 2. Intercepteur de RÉPONSE (Gestion du 401)
api.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {
        const status = error.response ? error.response.status : null;

        // Si le backend renvoie 401 (Non autorisé / Token expiré)
        if (status === 401) {
            console.warn("Session expirée. Déconnexion automatique.");

            // Éviter la boucle si on est déjà sur le login
            if (router.currentRoute.value.path !== '/login') {
                
                // Instanciation du store ICI pour éviter les erreurs d'initialisation cycliques
                const authStore = useAuthStore();
                
                // Nettoyage complet via l'action du store
                authStore.logout();
            }
        }

        return Promise.reject(error);
    }
);

export default api;