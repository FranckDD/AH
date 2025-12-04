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
        <a href="#" class="text-sm font-medium text-gray-500 hover:text-green-600 transition duration-150">
          Mot de passe oublié ?
        </a>
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

const handleLogin = async () => {
  error.value = null; 
  isLoading.value = true;

  try {
    await authStore.login(username.value, password.value);
    
    // Redirection après succès
    router.push('/');

  } catch (err) {
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
/* Les styles spécifiques de ce composant sont gérés par Tailwind, cette section reste propre. */
</style>