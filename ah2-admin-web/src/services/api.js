import axios from 'axios';
import { useAuthStore } from '@/stores/auth'; 
import router from '@/router';

// URL de base de votre API FastAPI
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Resout un chemin de fichier servi par le backend (ex. logo_url) en URL
// absolue utilisable dans un <img src>. Le backend stocke desormais un
// chemin relatif ("/static/uploads/...") pour rester valable quel que soit
// l'environnement (port local different, prod) - voir registre. Le
// startsWith('http') gere les anciennes valeurs deja absolues stockees
// avant ce correctif (redeviennent correctes au prochain upload).
export function resolveAssetUrl(path) {
    if (!path) return null;
    if (path.startsWith('http')) return path;
    return path.startsWith('/') ? `${API_URL}${path}` : `${API_URL}/${path}`;
}

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