<template>
  <router-view />
  <ToastContainer />
</template>

<script setup>
import { onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { connectPowerSync } from '@/powersync-client/client';
import ToastContainer from '@/components/common/ToastContainer.vue';

onMounted(() => {
  const authStore = useAuthStore();
  if (!authStore.isAuthenticated) {
    return;
  }
  const role = authStore.userRole;
  if (role === 'medecin' || role === 'nurse' || role === 'secretaire' || role === 'laborantin') {
    // Non attendu, meme raison que dans authStore.login() : le premier rendu
    // de l'application ne doit jamais dependre de l'ouverture de la base
    // locale OPFS, qui peut prendre plusieurs secondes.
    connectPowerSync(role).catch((error) => {
      console.error('Connexion PowerSync echouee (l\'application reste utilisable) :', error);
    });
  }
});
</script>

<style scoped>
/* Laissez vide ou retirez cette section si elle est vide pour ne pas interférer avec Tailwind */
</style>
