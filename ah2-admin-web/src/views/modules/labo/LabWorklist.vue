<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold mb-6">📋 File d'attente Laboratoire</h1>

    <div v-if="store.loading" class="text-center py-10">Chargement...</div>

    <div v-else class="bg-white shadow rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patient</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Examens demandés</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prescripteur</th>
            <th class="px-6 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="item in store.worklist" :key="item.prescription_id">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
              {{ new Date(item.date).toLocaleDateString() }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-medium text-gray-900">{{ item.patient_name }}</div>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">
              {{ Array.isArray(item.exams_requested) ? item.exams_requested.join(', ') : item.exams_requested }}
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">{{ item.doctor }}</td>
            <td class="px-6 py-4 text-right">
              <button 
                @click="processPrescription(item)"
                class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm transition"
              >
                🧪 Traiter
              </button>
            </td>
          </tr>
          <tr v-if="store.worklist.length === 0">
            <td colspan="5" class="px-6 py-10 text-center text-gray-500">
              Aucune prescription en attente. Bonne pause café ! ☕
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useLabStore } from '@/stores/labStore';
import { useRouter } from 'vue-router';

const store = useLabStore();
const router = useRouter();

onMounted(() => {
  store.fetchWorklist();
});

const processPrescription = async (item) => {
  // Ici, on va boucler pour créer les dossiers ou ouvrir un modal de sélection.
  // Pour l'exemple simple, on crée le dossier pour le PREMIER examen de la liste (ou un flux plus complexe)
  
  // LOGIQUE SIMPLIFIÉE : On suppose que l'utilisateur choisit quel examen traiter.
  // Dans la vraie vie, tu ouvrirais peut-être un modal pour dire "Je fais l'Hémogramme maintenant".
  
  // Exemple : On redirige vers une page de création manuelle pré-remplie
  // Ou on appelle createResult directement si on sait quel examen ID correspond.
  
  alert("Fonctionnalité à connecter : Ouvrir modal choix examen pour " + item.patient_name);
};
</script>