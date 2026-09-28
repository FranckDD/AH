<template>
  <div class="p-6 max-w-5xl mx-auto">
    
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-center gap-4">
        <button 
          @click="goBack"
          class="p-2 rounded-full hover:bg-gray-100 text-gray-500 transition"
          title="Retour à la liste"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </button>
        <div>
          <h1 class="text-2xl font-bold text-gray-800">Saisie des résultats</h1>
          <p class="text-sm text-gray-500">Validez les paramètres biologiques pour ce dossier.</p>
        </div>
      </div>

      <div class="flex gap-3" v-if="currentResult">
        <button 
          v-if="currentResult.is_completed"
          @click="handlePrint"
          class="flex items-center gap-2 px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition shadow"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          Réimprimer PDF
        </button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>

    <div v-else-if="error" class="bg-red-50 border-l-4 border-red-500 p-4 mb-6 rounded shadow-sm">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-red-700">{{ error }}</p>
        </div>
      </div>
    </div>

    <div v-else-if="currentResult" class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <div class="lg:col-span-1">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 sticky top-6">
          <div class="flex items-center gap-4 mb-4 border-b pb-4">
            <div class="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-xl">
              {{ getInitials(currentResult.patient_info?.nom_complet) }}
            </div>
            <div>
              <h2 class="text-lg font-bold text-gray-800">{{ currentResult.patient_info?.nom_complet }}</h2>
              <span class="px-2 py-0.5 rounded text-xs font-semibold"
                :class="currentResult.is_completed ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'">
                {{ currentResult.is_completed ? 'Clôturé' : 'En cours' }}
              </span>
            </div>
          </div>

          <div class="space-y-3 text-sm text-gray-600">
            <div class="flex justify-between">
              <span>Code Dossier:</span>
              <span class="font-mono font-medium text-gray-900">{{ currentResult.code }}</span>
            </div>
            <div class="flex justify-between">
              <span>Âge / Sexe:</span>
              <span class="font-medium text-gray-900">
                {{ currentResult.patient_info?.age }} ans / {{ currentResult.patient_info?.sexe }}
              </span>
            </div>
            <div class="flex justify-between">
              <span>Prescripteur:</span>
              <span class="font-medium text-gray-900">{{ currentResult.prescripteur || 'N/A' }}</span>
            </div>
            <div class="flex justify-between">
              <span>Date:</span>
              <span class="font-medium text-gray-900">{{ formatDate(currentResult.created_at) }}</span>
            </div>
          </div>
          
          <div v-if="successMessage" class="mt-6 p-3 bg-green-50 text-green-700 text-sm rounded border border-green-200 animate-fade-in">
            {{ successMessage }}
          </div>
        </div>
      </div>

      <div class="lg:col-span-2 space-y-6">
        
        <div v-for="exam in currentResult.exams" :key="exam.exam_id" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div class="bg-gray-50 px-6 py-3 border-b border-gray-200 flex justify-between items-center">
            <h3 class="font-bold text-gray-700 uppercase tracking-wide text-sm">{{ exam.exam_name }}</h3>
          </div>

          <div class="p-6">
            <table class="w-full text-sm text-left">
              <thead class="text-xs text-gray-500 uppercase bg-gray-50">
                <tr>
                  <th class="px-4 py-2 w-1/3">Paramètre</th>
                  <th class="px-4 py-2 w-1/3">Valeur</th>
                  <th class="px-4 py-2">Unité & Ref</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="detail in exam.details" :key="detail.id" class="hover:bg-gray-50">
                  <td class="px-4 py-3 font-medium text-gray-700">
                    {{ detail.param_name }}
                  </td>
                  <td class="px-4 py-3">
                    <input 
                      type="text" 
                      v-model="formValues[detail.id]"
                      :disabled="currentResult.is_completed"
                      placeholder="Résultat..."
                      class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm disabled:bg-gray-100 disabled:text-gray-500"
                    />
                  </td>
                  <td class="px-4 py-3 text-gray-500">
                    <span class="font-medium text-gray-700">{{ detail.unit }}</span>
                    <span v-if="detail.ref_min || detail.ref_max" class="text-xs text-gray-400 block">
                      [{{ detail.ref_min }} - {{ detail.ref_max }}]
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="!currentResult.is_completed" class="bg-white p-6 rounded-xl shadow-lg border border-gray-200 sticky bottom-6 flex justify-between items-center z-10">
          <span class="text-sm text-gray-500 italic">
            * Vérifiez les valeurs avant de valider.
          </span>
          <div class="flex gap-4">
            <button 
              @click="handleSave(false)" 
              :disabled="isSaving"
              class="px-5 py-2.5 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50 transition focus:ring-2 focus:ring-offset-2 focus:ring-gray-200 disabled:opacity-50"
            >
              {{ isSaving ? 'Sauvegarde...' : 'Sauvegarder brouillon' }}
            </button>
            
            <button 
              @click="handleSave(true)"
              :disabled="isSaving"
              class="px-5 py-2.5 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 transition shadow-md hover:shadow-lg focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 flex items-center gap-2"
            >
              <svg v-if="!isSaving" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Valider & Clôturer
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useLabStore } from '@/stores/labStore';
import { storeToRefs } from 'pinia';

// --- SETUP ---
const route = useRoute();
const router = useRouter();
const store = useLabStore();

// Utilisation de storeToRefs pour la réactivité propre des états du store
const { currentResult, loading, error, successMessage } = storeToRefs(store);

// --- STATE LOCAL ---
const formValues = ref({}); // Stocke les ID -> Valeurs
const isSaving = ref(false);

// --- LIFECYCLE ---
onMounted(async () => {
  const resultId = route.params.id;
  store.clearMessages(); // Reset messages précédents
  
  // 1. Charger le dossier complet
  const data = await store.fetchResultDetail(resultId);
  
  // 2. Initialiser le formulaire avec les valeurs existantes (si mode brouillon)
  if (data && data.exams) {
    data.exams.forEach(exam => {
      if (exam.details) {
        exam.details.forEach(detail => {
          // On pré-remplit le formulaire avec la valeur existante ou vide
          formValues.value[detail.id] = detail.value !== null ? detail.value : '';
        });
      }
    });
  }
});

// --- ACTIONS ---

// Sauvegarde (Brouillon ou Validation Finale)
const handleSave = async (markCompleted) => {
  if (markCompleted && !confirm("Attention : Cette action est irréversible. Voulez-vous valider et clôturer ce dossier ?")) {
    return;
  }

  isSaving.value = true;
  try {
    const success = await store.saveValues(route.params.id, {
      values: formValues.value,
      completed: markCompleted,
      note: null,
    });

    if (success) {
      if (markCompleted) {
        const wantPrint = confirm("Dossier validé ! Voulez-vous imprimer le PDF maintenant ?");
        if (wantPrint) {
          await handlePrint();
        }
        router.push({ name: 'LabTechnician' });
      }
    }
  } catch (e) {
    console.error(e);
  } finally {
    isSaving.value = false;
  }
};

// Impression PDF
const handlePrint = async () => {
  const success = await store.downloadPDF(route.params.id, `Resultat_${currentResult.value.code}.pdf`);
  if (!success) {
    alert("Erreur lors du téléchargement du PDF.");
  }
};

const goBack = () => {
  store.clearCurrentResult(); // Nettoyer le store pour éviter les flashs au prochain chargement
  router.push({ name: 'LabTechnician' });
};

// --- UTILS ---
const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
};

const getInitials = (name) => {
  if (!name) return '?';
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
};
</script>

<style scoped>
/* Petite animation pour le message de succès */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}
</style>