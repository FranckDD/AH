// src/stores/auth.js
import { defineStore } from 'pinia';
import api from '@/services/api';
import router from '@/router'; // 🟢 1. Importer le router pour la redirection

export const useAuthStore = defineStore('auth', {
  state: () => ({
    // 🟢 2. On s'assure d'utiliser la même clé partout (ici 'token')
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user')) || null, 
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    
    userRole: (state) => {
        if (state.user && state.user.application_role && state.user.application_role.role_name) {
            return state.user.application_role.role_name;
        }
        return state.user?.role?.role_name || state.user?.role || 'Guest';
    },

    isAdmin: (state) => {
        // Accès au getter via 'this'
        const role = state.user?.application_role?.role_name || 'Guest'; 
        return role === 'admin';
    },
    
    isToxicoTeam: (state) => {
        const role = state.user?.application_role?.role_name || 'Guest';
        return ['admin', 'ToxicoManager', 'Psychologist', 'Assistant'].includes(role);
    }
  },

  actions: {
    async login(username, password) {
      try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await api.post('/auth/login', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });

        this.token = response.data.access_token;

        // 🟢 Stockage avec la clé 'token' (Doit être identique dans api.js)
        localStorage.setItem('token', this.token);

        const meResponse = await api.get('/auth/me', {
            headers: { Authorization: `Bearer ${this.token}` }
        });

        this.user = meResponse.data; 
        
        console.log("Utilisateur stocké :", this.user);
        console.log("Rôle détecté :", this.user.application_role?.role_name);

        localStorage.setItem('user', JSON.stringify(this.user));

        return true; 

      } catch (error) {
        console.error("Erreur Login:", error);
        this.logout(); 
        throw error;
      }
    },

    async logout() {
      // 0. Revoquer le token cote serveur (best-effort : si l'appel echoue,
      //    on nettoie quand meme localement pour ne jamais bloquer l'utilisateur)
      try {
        await api.post('/auth/logout');
      } catch (error) {
        console.warn("Echec de la revocation serveur du token :", error);
      }

      // 1. Nettoyer l'état Pinia
      this.token = null;
      this.user = null;

      // 2. Nettoyer le LocalStorage
      localStorage.removeItem('token');
      localStorage.removeItem('user');

      // 3. 🟢 Redirection forcée via le router Vue
      router.push('/login');
    }
  }
});