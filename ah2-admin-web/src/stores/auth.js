// src/stores/auth.js
import { defineStore } from 'pinia';
import api from '@/services/api';
import router from '@/router'; // 🟢 1. Importer le router pour la redirection
import { connectPowerSync, disconnectPowerSync } from '@/powersync-client/client';

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
    },

    // Comparaison de role insensible a la casse (registre L4e) - meme
    // logique que router/index.js:386-389, qui normalise deja userRole et
    // la liste autorisee avant de comparer. Les 7 endroits qui comparaient
    // authStore.userRole directement (sans normalisation) sont fragiles au
    // moindre ecart de casse en base ; ce getter est le point de verite
    // unique a utiliser desormais pour toute nouvelle garde de role.
    hasRole(state) {
        return (allowedRoles) => {
            const role = (this.userRole || '').toLowerCase();
            return (allowedRoles || []).some((r) => (r || '').toLowerCase() === role);
        };
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

        const role = this.user.application_role?.role_name;
        if (role === 'medecin' || role === 'nurse' || role === 'secretaire' || role === 'laborantin') {
          // Volontairement NON attendu. L'ouverture de la base locale OPFS +
          // le premier sync prennent parfois plusieurs secondes (verrou de
          // fichier dispute entre contextes navigateur), et tant que c'etait
          // attendu ici, la fenetre medicale ne s'ouvrait qu'apres ce delai -
          // alors que rien a l'ecran n'en depend a cet instant. La connexion
          // se poursuit en arriere-plan ; les ecrans qui lisent vraiment les
          // tables synchronisees attendent waitForInitialSync() eux-memes.
          connectPowerSync(role).catch((error) => {
            console.error('Connexion PowerSync echouee (l\'application reste utilisable) :', error);
          });
        }

        return true;

      } catch (error) {
        console.error("Erreur Login:", error);
        this.logout(); 
        throw error;
      }
    },

    async updateProfile(payload) {
      const response = await api.put('/auth/profile', payload);
      this.user = { ...this.user, ...response.data };
      localStorage.setItem('user', JSON.stringify(this.user));
      return response.data;
    },

    async fetchMe() {
      const response = await api.get('/auth/me');
      this.user = { ...this.user, ...response.data };
      localStorage.setItem('user', JSON.stringify(this.user));
      return response.data;
    },

    async changePassword(payload) {
      return api.put('/auth/password', payload);
    },

    async logout() {
      // 0. Revoquer le token cote serveur (best-effort : si l'appel echoue,
      //    on nettoie quand meme localement pour ne jamais bloquer l'utilisateur)
      try {
        await api.post('/auth/logout');
      } catch (error) {
        console.warn("Echec de la revocation serveur du token :", error);
      }

      // 0.5 Deconnecter PowerSync avant de nettoyer l'etat (best-effort,
      //     comme la revocation serveur - ne doit jamais bloquer le logout)
      try {
        await disconnectPowerSync();
      } catch (error) {
        console.warn("Echec de la deconnexion PowerSync :", error);
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