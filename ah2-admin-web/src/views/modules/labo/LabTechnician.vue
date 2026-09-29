<template>
  <div class="flex h-[calc(100vh-120px)] gap-6 max-w-7xl mx-auto pb-4">
    
    <div class="w-1/3 flex flex-col bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="p-4 border-b bg-gray-50 flex justify-between items-center">
        <div>
           <h2 class="font-bold text-gray-700 flex items-center gap-2">
             <span class="bg-indigo-100 text-indigo-600 p-1 rounded-sm">🧪</span>
             Paillasse Technique
           </h2>
           <p class="text-xs text-gray-500 mt-1">
             {{ labStore.paillasseList.length }} dossier(s) en analyse
           </p>
        </div>
        <button @click="refreshList" class="text-indigo-600 hover:bg-indigo-100 p-2 rounded-full transition">
          <ArrowPathIcon class="w-5 h-5" :class="{'animate-spin': labStore.loading}"/>
        </button>
      </div>
      
      <div class="flex-1 overflow-y-auto p-2 space-y-2">
        <div v-if="labStore.paillasseList.length === 0 && !labStore.loading" class="text-center text-gray-400 mt-10 text-sm italic flex flex-col items-center">
          <BeakerIcon class="w-10 h-10 mb-2 opacity-20"/>
          Aucun résultat à saisir.
        </div>
        
        <div 
          v-for="item in labStore.paillasseList" 
          :key="item.result_id"
          @click="openDossier(item.result_id)"
          :class="activeId === item.result_id ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500' : 'hover:bg-gray-50 border-transparent'"
          class="p-3 border-l-4 rounded-sm bg-white shadow-xs cursor-pointer transition-all relative group"
        >
          <div class="font-bold text-gray-800 truncate pr-6">
            {{ item.patient_name }}
          </div>
          
          <div class="flex justify-between items-center mt-2">
            <span class="text-xs font-bold bg-blue-100 text-blue-700 px-2 py-1 rounded-sm border border-blue-200 truncate max-w-[150px]">
              {{ item.examen_nom || 'Examen' }}
            </span>
            <span class="text-xs text-gray-500 font-mono">
                {{ item.patient_sexe }} | {{ item.patient_age }} ans
            </span>
          </div>

          <div v-if="item.is_external" class="absolute top-2 right-2">
            <span class="inline-flex items-center px-1.5 py-0.5 rounded-sm text-[10px] font-medium bg-orange-100 text-orange-800 border border-orange-200">
              EXT
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="w-2/3 flex flex-col bg-white rounded-2xl shadow-sm border border-gray-200 relative overflow-hidden">
      
      <div v-if="!activeDossier" class="flex-1 flex flex-col items-center justify-center text-gray-300">
        <div class="bg-gray-50 p-6 rounded-full mb-4">
            <BeakerIcon class="w-16 h-16 text-gray-300"/>
        </div>
        <p class="font-medium text-gray-400">Sélectionnez un dossier à gauche.</p>
      </div>

      <div v-else class="flex flex-col h-full animate-fade-in">
        
        <div class="px-6 py-4 border-b bg-indigo-600 text-white flex justify-between items-center shadow-md z-10">
          <div>
            <h1 class="text-xl font-bold flex items-center gap-2">
              {{ activeDossier.examen_nom }}
              <span class="text-xs bg-indigo-500/50 px-2 py-0.5 rounded-sm text-white border border-indigo-400 font-mono">
                #{{ activeDossier.code }}
              </span>
            </h1>
            <div class="flex items-center gap-2 text-sm opacity-90 mt-1">
               <UserIcon class="w-4 h-4"/> 
               <span class="font-medium">{{ activeDossier.patient_info?.nom }}</span>
            </div>
          </div>
          <div class="text-right">
              <div class="text-xs opacity-80 leading-tight font-mono bg-indigo-700 px-3 py-1.5 rounded-lg mb-1 inline-block">
                 {{ activeDossier.patient_info?.sexe }} | {{ activeDossier.patient_info?.age }} ans
              </div>
          </div>
        </div>

        <div v-if="labStore.batchSiblings.length > 1" class="bg-gray-100 px-4 pt-2 border-b flex gap-2 overflow-x-auto">
            <button 
                v-for="sibling in labStore.batchSiblings" 
                :key="sibling.result_id"
                @click="openDossier(sibling.result_id)"
                :class="sibling.result_id === activeDossier.result_id ? 'bg-white text-indigo-700 border-t-2 border-indigo-600 font-bold' : 'bg-gray-200 text-gray-500 hover:bg-gray-300'"
                class="px-4 py-2 rounded-t-lg text-xs transition-colors whitespace-nowrap"
            >
                {{ sibling.exam_name }} 
                <span v-if="sibling.status === 'completed'" class="text-green-500 ml-1">✓</span>
            </button>
        </div>

        <div class="p-4 border-b bg-white flex justify-between items-center shadow-xs z-10 relative">
            <button 
              @click="submit(false)" 
              :disabled="labStore.loading"
              class="text-gray-500 font-bold text-sm hover:text-indigo-600 transition flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-indigo-50"
            >
              <span>Sauvegarder Brouillon</span>
            </button>

            <div class="flex gap-3">
                <button 
                  @click="submit(true, false)" 
                  :disabled="labStore.loading || !activeDossier.details.length || isFormEmpty"
                  class="bg-white border border-gray-300 text-gray-700 px-4 py-2.5 rounded-xl font-bold text-sm hover:bg-gray-50 shadow-xs transition transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-100"
                >
                  Valider & Clôturer
                </button>

                <button 
                  @click="submit(true, true)" 
                  :disabled="labStore.loading || !activeDossier.details.length || isFormEmpty"
                  class="bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-indigo-700 shadow-lg shadow-indigo-200 flex items-center gap-2 transition transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
                >
                  <span v-if="!labStore.loading">VALIDER & IMPRIMER</span>
                  <ArrowPathIcon v-else class="w-5 h-5 animate-spin"/>
                  <PrinterIcon v-if="!labStore.loading" class="w-5 h-5"/>
                </button>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto p-6 bg-gray-50 pb-12">
          
          <div class="bg-white rounded-xl shadow-xs border border-gray-200 overflow-hidden">
            <table class="w-full">
              <thead class="bg-gray-50">
                <tr class="text-left text-xs font-bold text-gray-500 uppercase tracking-wider border-b border-gray-200">
                  <th class="py-3 pl-6">Paramètre</th>
                  <th class="py-3 w-48">Valeur</th>
                  <th class="py-3 w-24 text-center">Unité</th>
                  <th class="py-3 w-32 text-right pr-6">Référence</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                
                <template v-for="detail in activeDossier.details" :key="detail.detail_id">
                  
                  <tr class="group hover:bg-indigo-50/30 transition-colors">
                    <td class="py-3 pl-6 font-medium text-gray-700">
                      {{ detail.nom }}
                    </td>
                    
                    <td class="py-3">
                      <div class="relative">
                          <input 
                              v-if="detail.input_type === 'numeric'"
                              v-model.number="formValues[detail.detail_id]" 
                              type="number" 
                              step="any"
                              @wheel="$event.target.blur()"
                              class="w-full border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-bold text-gray-900 shadow-xs transition-all text-center py-2"
                              placeholder="-"
                          />
                          <input 
                              v-else
                              v-model="formValues[detail.detail_id]" 
                              type="text"
                              class="w-full border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 shadow-xs transition-all py-2"
                              placeholder="Résultat..."
                          />
                      </div>
                    </td>

                    <td class="py-3 text-center">
                      <span class="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-sm">
                          {{ detail.unite }}
                      </span>
                    </td>
                    
                    <td class="py-3 text-right pr-6">
                      <div class="text-xs text-gray-500 font-mono">
                        {{ getRangeForPatient(detail.ranges, activeDossier.patient_info?.sexe) }}
                      </div>
                    </td>
                  </tr>

                  <tr v-if="hasValue(formValues[detail.detail_id])" class="bg-indigo-50/20 border-t-0">
                    <td colspan="4" class="py-2 pl-6 pr-6 pb-3">
                      <div class="flex items-center gap-3 pl-4 border-l-2 border-indigo-200 ml-2">
                        
                        <div class="w-36 shrink-0">
                          <select 
                            v-model="formFlags[detail.detail_id]"
                            class="w-full text-xs border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 shadow-xs py-1.5 text-gray-700 bg-white"
                          >
                            <option value="">-- Flag --</option>
                            <option value="H">🔺 Haut (H)</option>
                            <option value="L">🔻 Bas (L)</option>
                            <option value="N">✅ Normal (N)</option>
                            <option value="A">⚠️ Anormal (A)</option>
                          </select>
                        </div>

                        <div class="flex-1 relative">
                          <input 
                            v-model="formInterpretations[detail.detail_id]"
                            type="text"
                            class="w-full text-xs border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 shadow-xs py-1.5 px-3 bg-white"
                            placeholder="Interprétation ou remarque spécifique à ce paramètre..."
                          />
                        </div>
                      </div>
                    </td>
                  </tr>

                </template>
                <tr v-if="!activeDossier.details || activeDossier.details.length === 0">
                  <td colspan="4" class="py-8 text-center text-orange-500">
                     ⚠️ Aucun paramètre configuré.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="activeDossier.details && activeDossier.details.length > 0" class="mt-6 bg-white rounded-xl shadow-xs border border-gray-200 overflow-hidden">
            <div class="bg-gray-50 px-6 py-3 border-b border-gray-200">
              <h3 class="text-sm font-bold text-gray-700 tracking-wider">
                Conclusion Globale de l'Examen
              </h3>
            </div>
            <div class="p-4">
              <textarea 
                v-model="formGlobalNote"
                rows="3"
                class="w-full border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700 shadow-xs transition-all p-3 text-sm"
                placeholder="Saisissez ici la conclusion ou les notes générales qui apparaîtront au bas du compte-rendu..."
              ></textarea>
            </div>
          </div>

          <div class="h-8"></div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useLabStore } from '@/stores/labStore';
import dayjs from 'dayjs';
import { 
  ArrowPathIcon, BeakerIcon, UserIcon, PrinterIcon 
} from '@heroicons/vue/24/outline';

const labStore = useLabStore();
const activeId = ref(null);

// Nouveaux états réactifs pour la structure séparée
const formValues = ref({}); 
const formFlags = ref({});
const formInterpretations = ref({});
const formGlobalNote = ref('');

// Récupère le dossier complet depuis le store
const activeDossier = computed(() => labStore.currentResult);

// Vérifie si aucune valeur n'a été saisie dans le formulaire principal
const isFormEmpty = computed(() => {
  if (Object.keys(formValues.value).length === 0) return true;
  return !Object.values(formValues.value).some(val => val !== '' && val !== null && val !== undefined);
});

// Helper pour afficher la sous-ligne
const hasValue = (val) => {
  return val !== '' && val !== null && val !== undefined;
};

onMounted(() => {
  refreshList();
});

const refreshList = () => {
  labStore.fetchPaillasseList();
};

// --- LOGIQUE MÉTIER ---

const openDossier = async (id) => {
  if (!id) return;

  activeId.value = id;
  labStore.clearMessages();
  
  // Reset complet
  formValues.value = {}; 
  formFlags.value = {};
  formInterpretations.value = {};
  formGlobalNote.value = '';
  
  // Appel API
  const data = await labStore.fetchResultDetail(id);
  
  // Remplissage du formulaire
  if (data) {
    // 🟢 Remplissage de la note globale depuis le champ "note" (si sauvegardé en brouillon)
    formGlobalNote.value = data.note || '';

    if (data.details) {
      data.details.forEach(d => {
        // Pour être sûr de rattraper les anciennes données
        const val = (d.valeur !== null && d.valeur !== undefined) ? d.valeur : '';
        formValues.value[d.detail_id] = val;
        
        // S'il avait déjà été flaggé manuellement ou auto-interprété
        formFlags.value[d.detail_id] = d.flagged ? 'A' : ''; 
        formInterpretations.value[d.detail_id] = d.interpretation || '';
      });
    }
  }
};

const submit = async (isCompleted, shouldPrint) => {
  // Sécurité: On s'assure d'avoir un ID valide
  const targetId = activeId.value || activeDossier.value?.result_id;
  
  if (!targetId) {
      alert("Erreur: Aucun dossier sélectionné");
      return;
  }

  // 🟢 Construction du payload des valeurs au format attendu par le Controller
  const payloadValues = {};
  for (const detailId in formValues.value) {
      payloadValues[detailId] = {
          valeur: formValues.value[detailId],
          flag: formFlags.value[detailId] || '',
          interpretation: formInterpretations.value[detailId] || ''
      };
  }

  // 🟢 Construction du payload global
  const fullPayload = {
      values: payloadValues,
      completed: isCompleted,
      note: formGlobalNote.value
  };

  // ⚠️ ATTENTION : Assure-toi que ta fonction `labStore.saveValues`
  // transmette maintenant l'objet `fullPayload` complet à ton API.
  const success = await labStore.saveValues(targetId, fullPayload);
  
  if (success) {
      if (isCompleted && shouldPrint) {
          // Logique d'impression basique
          await labStore.downloadPDF(targetId, `Resultat_${targetId}.pdf`);
      }

      // Si c'est fini, on ferme
      if (isCompleted) {
          activeId.value = null;
          formValues.value = {};
          formFlags.value = {};
          formInterpretations.value = {};
          formGlobalNote.value = '';
      }
  }
};

// --- HELPERS D'AFFICHAGE ---

// Trouve la bonne plage de référence selon le sexe (M/F)
const getRangeForPatient = (ranges, sexePatient) => {
    if (!ranges || ranges.length === 0) return '-';
    // Cherche la range spécifique au sexe, sinon prend la première (défaut)
    const range = ranges.find(r => r.sexe === sexePatient) || ranges[0];
    return `${range.min} - ${range.max}`;
};
</script>

<style scoped>
.animate-fade-in { animation: fadeIn 0.3s ease-in-out; }
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
input[type=number]::-webkit-inner-spin-button, 
input[type=number]::-webkit-outer-spin-button { 
  -webkit-appearance: none; margin: 0; 
}
</style>