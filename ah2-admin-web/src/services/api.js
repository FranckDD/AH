import axios from 'axios';
import { useAuthStore } from '@/stores/auth'; 
import router from '@/router';

// URL de base de votre API FastAPI
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});

// 1. Intercepteur de REQUÊTE
// Ajoute le token JWT à chaque requête sortante
api.interceptors.request.use(config => {
    // Récupération du token depuis le localStorage
    const token = localStorage.getItem('token');
    
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, error => {
    return Promise.reject(error);
});

// 2. Intercepteur de RÉPONSE
// Gère globalement les erreurs, notamment l'expiration de session (401)
api.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {
        const status = error.response ? error.response.status : null;

        // Si le backend renvoie 401 (Non autorisé / Token expiré)
        if (status === 401) {
            console.warn("Session expirée ou invalide. Déconnexion automatique.");

            // Éviter la boucle de redirection si on est déjà sur la page de login
            if (router.currentRoute.value.path !== '/login') {
                
                // On importe le store ici pour éviter les dépendances circulaires au chargement
                // C'est crucial car api.js est souvent importé par les stores eux-mêmes
                const authStore = useAuthStore();
                
                // Nettoyage complet (token, user info) et redirection
                authStore.logout();
                router.push('/login');
            }
        }

        return Promise.reject(error);
    }
);

export default api;