<template>
  <div class="space-y-6 animate-fade-in-up">
    
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-xl font-bold text-gray-800">Catalogue des Examens</h2>
        <p class="text-sm text-gray-500">Liste de référence des analyses.</p>
      </div>
      
      <button 
        v-if="isAdmin"
        @click="openModal()"
        class="px-4 py-2 bg-indigo-600 text-white rounded-xl shadow hover:bg-indigo-700 transition flex items-center gap-2"
      >
        <PlusIcon class="w-5 h-5" /> Nouvel Examen
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-sm text-left">
        <thead class="bg-gray-50 text-gray-500 uppercase font-bold text-xs">
          <tr>
            <th class="px-6 py-4">Code</th>
            <th class="px-6 py-4">Nom de l'examen</th>
            <th class="px-6 py-4">Catégorie</th>
            <th v-if="isAdmin" class="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="exam in labStore.exams" :key="exam.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 font-mono text-gray-600 font-medium">{{ exam.code }}</td>
            <td class="px-6 py-4 font-medium text-gray-900">{{ exam.nom }}</td>
            <td class="px-6 py-4">
               <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                 {{ exam.categorie }}
               </span>
            </td>
            
            <td v-if="isAdmin" class="px-6 py-4 text-right">
              <button @click="labStore.deleteExam(exam.id)" class="text-gray-400 hover:text-red-600">
                <TrashIcon class="w-5 h-5"/>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useLabStore } from '@/stores/labStore';
import { useAuthStore } from '@/stores/auth';
import { PlusIcon, TrashIcon } from '@heroicons/vue/24/outline';

const labStore = useLabStore();
const authStore = useAuthStore();

// Vérification du rôle pour l'affichage conditionnel
const isAdmin = computed(() => {
    return authStore.hasRole(['admin', 'manager']);
});

onMounted(() => {
    labStore.fetchExams();
});

// ... reste du script (openModal, saveExam) inchangé
</script>