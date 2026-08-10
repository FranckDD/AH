<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100">
    <div class="text-center">
      <h1 class="text-6xl font-bold text-red-600">403</h1>
      <p class="text-2xl font-semibold text-gray-800 mt-4">Accès Interdit</p>
      <p class="text-gray-600 mt-2">Vous n'avez pas les droits nécessaires pour accéder à cette page.</p>
      <button 
        @click="$router.go(-1)" 
        class="mt-6 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
      >
        Retour
      </button>
    </div>
  </div>
</template>