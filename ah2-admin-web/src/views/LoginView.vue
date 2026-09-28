<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 p-4 sm:p-6 lg:p-8">
    
    <div class="w-full max-w-sm bg-white p-8 sm:p-10 rounded-2xl shadow-xl border border-gray-100 transform hover:shadow-2xl transition duration-300">
      
      <div class="text-center mb-8">
        <h1 class="text-3xl font-extrabold text-gray-900">
          Connexion <span class="text-green-600">AH2</span>
        </h1>
        <p class="mt-2 text-sm text-gray-500">Accès au tableau de bord</p>
      </div>
      
      <p v-if="error" class="text-sm text-red-700 mb-6 p-3 bg-red-100 rounded-lg border border-red-300 transition duration-300">
        <span class="font-semibold">Erreur :</span> {{ error }}
      </p>

      <form @submit.prevent="handleLogin">
        
        <div class="mb-5">
          <label for="username" class="block text-sm font-medium text-gray-700 mb-2">Identifiant</label>
          <input
            id="username"
            v-model="username"
            type="text"
            required
            placeholder="Votre nom d'utilisateur"
            class="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:ring-green-500 focus:border-green-500 transition duration-150 ease-in-out"
          />
        </div>

        <div class="mb-8">
          <label for="password" class="block text-sm font-medium text-gray-700 mb-2">Mot de passe</label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            placeholder="Mot de passe sécurisé"
            class="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:ring-green-500 focus:border-green-500 transition duration-150 ease-in-out"
          />
        </div>

        <button
          type="submit"
          :disabled="isLoading"
          class="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-md text-base font-semibold text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-70 disabled:cursor-not-allowed transition duration-150 ease-in-out"
        >
          <span v-if="!isLoading">Se connecter</span>
          <span v-else>Connexion en cours...</span>
        </button>
      </form>
      
      <div class="mt-6 text-center">
        <a href="#" @click.prevent="showForgotPasswordModal = true" class="text-sm font-medium text-gray-500 hover:text-green-600 transition duration-150">
          Mot de passe oublié ?
        </a>
      </div>
    </div>

    <!-- Simple modale d'information (pas de flux de reinitialisation -
         demande explicite de l'utilisateur, texte exact impose) -->
    <div v-if="showForgotPasswordModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="showForgotPasswordModal = false">
      <div class="w-full max-w-sm bg-white p-6 rounded-2xl shadow-xl border border-gray-100">
        <p class="text-sm text-gray-700 text-center">
          Veuillez vous rapprocher de l'administration.
        </p>
        <button
          type="button"
          @click="showForgotPasswordModal = false"
          class="mt-6 w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-white bg-green-600 hover:bg-green-700 transition duration-150"
        >
          Fermer
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const username = ref('');
const password = ref('');
const error = ref(null);
const isLoading = ref(false);
const showForgotPasswordModal = ref(false);

// 🟢 FONCTION INTELLIGENTE DE REDIRECTION
// C'est ici que tu définis la "Home Page" de chaque rôle
const getRedirectPath = (role) => {
    // Normalisation reelle (registre L4e, chantier L4b-e) - le switch
    // comparait avant la casse exacte de la BD malgre ce commentaire.
    const userRole = (role || '').toLowerCase();

    switch (userRole) {
        case 'admin':
            // L'admin va sur la vue d'ensemble globale
            return '/dashboard/overview';

        case 'promoteur':
            // Meme vue d'ensemble que l'admin (regard global sur
            // l'activite), sans les actions d'administration - route
            // MainLayout.vue gardee separement par role sur chaque item
            return '/dashboard/overview';

        case 'psychologist':
        case 'spiritualcounsellor':
            // Eux n'ont accès qu'à la partie Toxico
            return '/dashboard/toxico-dashboard';

        // ✅ NOUVEAU : Rôle LABO
        case 'laborantin':
        case 'biologiste': // Si tu as ce rôle
            // On le redirige vers SON tableau de bord spécifique
            return '/dashboard/labo/overviewlab';

        case 'toxicomanager':
        case 'assistant':
            // Le manager Toxico a aussi intérêt à voir le dashboard Toxico en premier
            return '/dashboard/toxico-dashboard';

        case 'medecin':
        case 'nurse':
            // Fenetre medicale independante (chantier 3) - jamais le dashboard toxico
            return '/medical/appointments';

        case 'secretaire':
            // Fenetre secretariat independante (chantier 3, sous-projet 2)
            return '/secretariat/';

        default:
            // Par sécurité, si le rôle est inconnu, on tente une page neutre ou on laisse le router gérer
            return '/dashboard/toxico-dashboard'; 
    }
};

const handleLogin = async () => {
  error.value = null; 
  isLoading.value = true;

  try {
    // 1. Appel API pour login
    await authStore.login(username.value, password.value);
    
    // 2. Récupération du rôle (maintenant disponible dans le store)
    const role = authStore.userRole;

    // 3. Calcul de la route de destination
    const targetRoute = getRedirectPath(role);

    //console.log(`Connexion réussie. Rôle: ${role} -> Redirection vers: ${targetRoute}`);

    // 4. Redirection ciblée
    router.push(targetRoute);

  } catch (err) {
    console.error(err);
    if (err.response && err.response.status === 401) {
      error.value = 'Identifiants ou mot de passe incorrects. Veuillez vérifier.';
    } else {
      error.value = 'Une erreur inattendue est survenue. Le serveur est peut-être inaccessible.';
    }
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
/* Tailwind gère tout */
</style>