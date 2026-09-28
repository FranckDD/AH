<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100">
    <div class="text-center p-8 bg-white shadow-xl rounded-2xl border border-gray-200 max-w-lg">
      
      <div class="mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-red-100 mb-6">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>

      <h1 class="text-6xl font-black text-gray-900 tracking-tighter">403</h1>
      <p class="text-2xl font-bold text-gray-800 mt-2">Accès Interdit</p>
      
      <p class="text-gray-500 mt-4 mb-8 leading-relaxed">
        Désolé, votre rôle actuel (<strong>{{ userRoleDisplay }}</strong>) ne vous permet pas d'accéder à cette ressource.
      </p>

      <div class="flex justify-center space-x-4">
        <button 
          @click="goSafeHome" 
          class="px-6 py-3 bg-green-600 text-white font-semibold rounded-xl hover:bg-green-700 transition shadow-lg shadow-green-200 transform hover:-translate-y-1"
        >
          Aller à mon Tableau de bord
        </button>
      </div>
      
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

// Affichage propre du rôle pour l'info utilisateur
const userRoleDisplay = computed(() => authStore.userRole || 'Utilisateur');

// Fonction de redirection intelligente (Logique Glostone)
const goSafeHome = () => {
  const role = authStore.userRole;

  // On réutilise la logique qu'on a définie pour le Login
  if (role === 'admin') {
    router.push('/dashboard/overview');
  } else if (['Psychologist', 'SpiritualCounsellor', 'ToxicoManager', 'Assistant'].includes(role)) {
    router.push('/dashboard/toxico-dashboard');
  } else {
    // Par défaut, ou si le rôle est inconnu, on renvoie au login
    router.push('/login');
  }
};
</script>