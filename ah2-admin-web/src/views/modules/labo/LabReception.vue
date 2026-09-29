<template>
  <div class="h-full overflow-y-auto bg-gray-50 p-6">
    <div class="max-w-5xl mx-auto pb-20 space-y-6">
      
      <div class="flex items-center justify-between" id="top-anchor">
        <div>
          <h1 class="text-2xl font-bold text-gray-800">{{ $t('lab.reception.title') }}</h1>
          <p class="text-sm text-gray-500">{{ $t('lab.reception.subtitle') }}</p>
        </div>
        
        <transition name="fade">
          <div v-if="labStore.successMessage" class="bg-green-100 text-green-800 px-4 py-2 rounded-lg flex items-center shadow-xs border border-green-200">
             <CheckCircleIcon class="w-5 h-5 mr-2"/> 
             <span class="font-medium">{{ labStore.successMessage || $t('lab.reception.success_message') }}</span>
          </div>
        </transition>
      </div>
  
      <div class="bg-white rounded-2xl shadow-xs border border-gray-200 overflow-visible relative z-30">
        <div class="bg-gray-50 border-b border-gray-200 px-6 py-3 flex justify-between items-center">
          <h2 class="font-bold text-gray-700 flex items-center gap-2">
            <UserIcon class="w-5 h-5"/> {{ $t('lab.reception.section1_title') }}
          </h2>
          
          <div class="bg-gray-200 p-1 rounded-lg flex text-sm font-medium">
            <button  
              @click="setMode('internal')"
              :class="mode === 'internal' ? 'bg-white text-indigo-600 shadow-xs' : 'text-gray-500 hover:text-gray-700'"
              class="px-4 py-1.5 rounded-md transition-all"
            >
              {{ $t('lab.reception.mode_internal') }}
            </button>
            <button  
              @click="setMode('external')"
              :class="mode === 'external' ? 'bg-white text-orange-600 shadow-xs' : 'text-gray-500 hover:text-gray-700'"
              class="px-4 py-1.5 rounded-md transition-all"
            >
              {{ $t('lab.reception.mode_external') }}
            </button>
          </div>
        </div>
  
        <div class="p-6">
          <div v-if="mode === 'internal'" class="space-y-4">
            <div v-if="!selectedPatient" class="relative">
              <input 
                v-model="searchQuery" 
                type="text" 
                :placeholder="$t('lab.reception.search_placeholder')" 
                class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition"
                autocomplete="off"
              />
              <MagnifyingGlassIcon class="w-5 h-5 text-gray-400 absolute left-3 top-3.5"/>
              
              <div v-if="labStore.loading" class="absolute right-3 top-3.5">
                  <ArrowPathIcon class="w-5 h-5 text-indigo-300 animate-spin"/>
              </div>

              <div v-if="showResults" class="absolute z-50 w-full mt-2 bg-white rounded-xl shadow-2xl border border-gray-200 max-h-80 overflow-y-auto">
                <div v-if="labStore.loading" class="py-8 flex flex-col items-center justify-center text-indigo-500">
                    <ArrowPathIcon class="w-8 h-8 animate-spin mb-2"/>
                    <span class="text-sm font-medium">Recherche en cours...</span>
                </div>
                <div v-else-if="labStore.searchResults && labStore.searchResults.length > 0">
                    <div 
                      v-for="p in labStore.searchResults" 
                      :key="p.prescription_id" 
                      @click="selectInternalPatient(p)"
                      class="px-4 py-3 hover:bg-indigo-50 cursor-pointer border-b border-gray-50 last:border-0 flex justify-between items-center group transition-colors"
                    >
                      <div>
                        <div class="font-bold text-gray-800 group-hover:text-indigo-700">{{ p.nom }}</div>
                        <div class="text-xs text-indigo-500 mt-1 flex items-center gap-1">
                            <BeakerIcon class="w-3 h-3"/>
                            <span v-if="p.exams_prescribed && p.exams_prescribed.length">
                                 {{ p.exams_prescribed.length }} examens prescrits
                            </span>
                            <span v-else>Prescription vide</span>
                        </div>
                      </div>
                      <span class="bg-gray-100 group-hover:bg-white text-gray-600 text-[10px] font-mono uppercase px-2 py-1 rounded-sm border border-gray-200">
                        {{ p.patient_code }}
                      </span>
                    </div>
                </div>
                <div v-else class="px-6 py-8 text-center">
                   <div class="bg-gray-50 w-10 h-10 rounded-full flex items-center justify-center mx-auto mb-2">
                       <MagnifyingGlassIcon class="w-5 h-5 text-gray-400"/>
                   </div>
                   <p class="text-sm text-gray-500 font-medium">{{ $t('lab.reception.no_results') }}</p>
                </div>
              </div>
            </div>
  
            <div v-else class="flex items-center justify-between bg-indigo-50 border border-indigo-100 p-4 rounded-xl animate-fade-in">
              <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xl font-bold uppercase">
                  {{ selectedPatient.nom.charAt(0) }}
                </div>
                <div>
                  <h3 class="font-bold text-indigo-900">{{ selectedPatient.nom }}</h3>
                  <p class="text-sm text-indigo-700">
                      {{ $t('lab.reception.patient_internal_label') }} #{{ selectedPatient.patient_code }}
                  </p>
                  <p v-if="autoImportedCount > 0" class="text-xs text-green-600 font-medium mt-1">
                      ✓ {{ autoImportedCount }} examens importés de la prescription
                  </p>
                </div>
              </div>
              <button @click="resetPatient" class="text-sm text-red-600 hover:underline font-medium">
                  {{ $t('lab.reception.change_patient') }}
              </button>
            </div>
          </div>
  
          <div v-else class="space-y-4 animate-fade-in">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{ $t('lab.reception.ext_name_label') }}</label>
                <input v-model="extForm.full_name" type="text" class="w-full border-gray-300 rounded-lg focus:ring-orange-500 focus:border-orange-500" placeholder="Ex: KOUAM Jean">
              </div>
              <div class="grid grid-cols-2 gap-4">
                 <div>
                   <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{ $t('lab.reception.ext_age_label') }}</label>
                   <input v-model.number="extForm.age" type="number" class="w-full border-gray-300 rounded-lg focus:ring-orange-500 focus:border-orange-500">
                 </div>
                 <div>
                   <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{ $t('lab.reception.ext_gender_label') }}</label>
                   <select v-model="extForm.gender" class="w-full border-gray-300 rounded-lg focus:ring-orange-500 focus:border-orange-500">
                     <option value="M">{{ $t('lab.gender.m') }}</option>
                     <option value="F">{{ $t('lab.gender.f') }}</option>
                   </select>
                 </div>
              </div>
            </div>
            <div class="bg-orange-50 text-orange-800 text-xs p-3 rounded-sm border border-orange-100 flex items-start gap-2">
              <ExclamationCircleIcon class="w-4 h-4 mt-0.5 shrink-0"/>
              <p>{{ $t('lab.reception.ext_warning') }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-xs border border-gray-200 overflow-visible relative z-20">
        <div class="bg-gray-50 border-b border-gray-200 px-6 py-3">
          <h2 class="font-bold text-gray-700 flex items-center gap-2">
            <IdentificationIcon class="w-5 h-5"/> {{ $t('lab.reception.prescriber_info') || 'Information Prescription' }}
          </h2>
        </div>
        <div class="p-6">
          <div class="max-w-md">
            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Prescrit par (Médecin/Infirmier)</label>
            <div class="relative">
              <select 
                v-model="selectedDoctorId" 
                class="w-full border-gray-300 rounded-xl py-3 pl-10"
              >
                <option :value="null">-- Choisir le prescripteur --</option>
                
                <option v-for="doc in doctors" :key="doc.user_id" :value="doc.user_id">
                  {{ doc.full_name }} — {{ doc.specialty_name || 'Médecin' }}
                </option>
              </select>
              <UserIcon class="w-5 h-5 text-gray-400 absolute left-3 top-3.5"/>
            </div>
            <p class="text-[10px] text-gray-400 mt-1 italic">Si le prescripteur est externe, choisissez un responsable interne référent.</p>
          </div>
        </div>
      </div>
  
      <div class="bg-white rounded-2xl shadow-xs border border-gray-200 overflow-hidden relative z-0">
        <div class="bg-gray-50 border-b border-gray-200 px-6 py-3">
          <h2 class="font-bold text-gray-700 flex items-center gap-2">
            <BeakerIcon class="w-5 h-5"/> {{ $t('lab.reception.section2_title') }}
          </h2>
        </div>
  
        <div class="p-6 space-y-6">
          <div class="flex gap-3">
            <select v-model="selectedExamId" class="flex-1 border-gray-300 rounded-xl focus:ring-indigo-500 focus:border-indigo-500 py-3">
              <option :value="null">{{ $t('lab.reception.select_exam_placeholder') }}</option>
              <option v-for="exam in labStore.exams" :key="exam.id" :value="exam.id">
                {{ exam.nom }} ({{ exam.code }})
              </option>
            </select>
            <button 
              @click="addExamToCart" 
              :disabled="!selectedExamId"
              class="bg-gray-800 text-white px-6 py-2 rounded-xl font-bold hover:bg-gray-900 transition disabled:opacity-50 flex items-center gap-2"
            >
              <PlusCircleIcon class="w-5 h-5"/> {{ $t('lab.reception.add_btn') }}
            </button>
          </div>
  
          <div v-if="cart.length > 0" class="border border-gray-200 rounded-xl overflow-hidden animate-fade-in">
            <table class="w-full text-sm text-left">
              <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
                <tr>
                  <th class="px-4 py-3">{{ $t('lab.reception.cart_exam_col') }}</th>
                  <th class="px-4 py-3 text-right">{{ $t('lab.reception.cart_action_col') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="(item, index) in cart" :key="index" class="hover:bg-gray-50">
                  <td class="px-4 py-3 font-medium text-gray-900">
                      {{ item.nom }}
                      <span v-if="item.is_prescribed" class="ml-2 text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded-full">Prescrit</span>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <button @click="removeFromCart(index)" class="text-red-500 hover:text-red-700 p-1">
                      <TrashIcon class="w-5 h-5"/>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div v-else class="text-center py-8 text-gray-400 border-2 border-dashed border-gray-200 rounded-xl">
             {{ $t('lab.reception.cart_empty') }}
          </div>
        </div>
      </div>
  
      <div class="flex justify-end pt-4">
        <button 
          @click="submitRequest" 
          :disabled="!canSubmit || labStore.loading"
          class="bg-indigo-600 text-white px-8 py-4 rounded-xl font-bold text-lg shadow-lg hover:bg-indigo-700 transition transform hover:-translate-y-1 flex items-center gap-3 disabled:opacity-50 disabled:transform-none"
        >
          <ArrowPathIcon v-if="labStore.loading" class="w-6 h-6 animate-spin"/>
          <PaperAirplaneIcon v-else class="w-6 h-6"/>
          <span>{{ $t('lab.reception.submit_btn') }} ({{ cart.length }})</span>
        </button>
      </div>
    </div>
  </div>
  
</template>
  
<script setup>
  import { ref, computed, onMounted, watch } from 'vue';
  import { useLabStore } from '@/stores/labStore';
  import axios from 'axios'; // Assure-toi que c'est configuré ou utilise ton instance API
  import debounce from 'lodash/debounce';
  import { useI18n } from 'vue-i18n'; 
  import { 
    UserIcon, MagnifyingGlassIcon, BeakerIcon, PlusCircleIcon, IdentificationIcon,
    TrashIcon, PaperAirplaneIcon, CheckCircleIcon, ExclamationCircleIcon, ArrowPathIcon 
  } from '@heroicons/vue/24/outline';
  import api from '@/services/api';
  import { useAuthStore } from '@/stores/auth';

  const { t } = useI18n();
  const labStore = useLabStore();
  const authStore = useAuthStore();
  
  
  // UI State
  const mode = ref('internal'); 
  const searchQuery = ref('');
  const selectedExamId = ref(null);
  const showResults = ref(false); 
  
  // Data State
  const selectedPatient = ref(null); 
  const doctors = ref([]); // Liste des médecins récupérée du backend
  const selectedDoctorId = ref(null);
  const extForm = ref({ full_name: '', age: '', gender: 'M' }); 
  const cart = ref([]); 
  const autoImportedCount = ref(0); 
  
  // --- INITIALISATION ---
  onMounted(async () => {
    labStore.fetchExams();
    labStore.clearMessages();
    fetchDoctors();
    
    // Fermeture si click outside
    window.addEventListener('click', (e) => {
        if (!e.target.closest('.relative')) {
            showResults.value = false;
        }
    });
  });

  const fetchDoctors = async () => {
  try {
    // Ici, on utilise 'api' et non 'axios'. 
    // Pas besoin de mettre 'http://localhost:8000', juste la route :
    const response = await api.get('/users/doctors');
    
    // On récupère la donnée brute (full_name est déjà dedans)
    doctors.value = response.data;
  } catch (e) {
    // Secours hors ligne (laborantin) : doctors_lookup est synchronise pour
    // tous les roles. Meme forme que la reponse serveur ({user_id, full_name,
    // specialty_name}) pour que le <select> et submitRequest restent inchanges.
    if (!e.response && authStore.hasRole(['laborantin'])) {
      try {
        const { db } = await import('@/powersync-client/client');
        const rows = await db.getAll('SELECT user_id, full_name FROM doctors_lookup ORDER BY full_name');
        doctors.value = rows.map((r) => ({
          user_id: r.user_id,
          full_name: r.full_name,
          specialty_name: null,
        }));
        return;
      } catch (localErr) {
        console.error("Erreur lecture locale des médecins", localErr);
      }
    }
    console.error("Erreur lors du chargement des médecins", e);
  }
};
  
  // --- 1. LOGIQUE RECHERCHE ---
  
  const performSearch = debounce(async (val) => {
    labStore.clearMessages();
  
    if (val && val.trim().length > 1) {
      try {
        showResults.value = true; 
        await labStore.searchInternal(val.trim());
      } catch (e) {
        console.error("Erreur de recherche", e);
      }
    } else {
      labStore.searchResults = [];
      showResults.value = false;
    }
  }, 300);
  
  watch(searchQuery, (newVal) => {
    if (!selectedPatient.value) {
      if (!newVal || newVal.trim().length <= 1) {
          showResults.value = false;
      }
      performSearch(newVal);
    }
  });
  
  // --- 2. SÉLECTION & AUTO-REMPLISSAGE ---
  
  const normalize = (str) => {
    return str ? str.toString().toLowerCase().trim() : '';
  };

  const selectInternalPatient = (p) => {
    selectedPatient.value = p;
    searchQuery.value = ''; 
    showResults.value = false; 
    
    cart.value = [];
    autoImportedCount.value = 0;

    // Auto-remplissage du panier via prescription
    if (p.exams_prescribed && Array.isArray(p.exams_prescribed)) {
        p.exams_prescribed.forEach(prescribedName => {
            const fullExam = labStore.exams.find(e => 
                normalize(e.nom) === normalize(prescribedName)
            );
            if (fullExam) {
                const alreadyInCart = cart.value.some(c => c.id === fullExam.id);
                if (!alreadyInCart) {
                    cart.value.push({ ...fullExam, is_prescribed: true });
                    autoImportedCount.value++;
                }
            }
        });
    }
  };
  
  const setMode = (newMode) => {
    mode.value = newMode;
    resetPatient();
    labStore.clearMessages();
  };
  
  const resetPatient = () => {
    selectedPatient.value = null;
    selectedDoctorId.value = null;
    extForm.value = { full_name: '', age: '', gender: 'M' };
    searchQuery.value = '';
    cart.value = []; 
    autoImportedCount.value = 0;
    showResults.value = false;
  };
  
  // --- 3. PANIER ---
  
  const addExamToCart = () => {
    const exam = labStore.exams.find(e => e.id === selectedExamId.value);
    if (exam) {
      if (!cart.value.find(c => c.id === exam.id)) {
        cart.value.push({ ...exam, is_prescribed: false }); 
      }
    }
    selectedExamId.value = null;
  };
  
  const removeFromCart = (index) => {
    cart.value.splice(index, 1);
  };
  
  // --- 4. SOUMISSION ---
  
  const canSubmit = computed(() => {
    const hasExam = cart.value.length > 0;
    const hasPatient = mode.value === 'internal' 
      ? !!selectedPatient.value 
      : (extForm.value.full_name && extForm.value.age);
    
    // On peut rendre le médecin obligatoire si on veut
    const hasDoctor = !!selectedDoctorId.value;
    
    return hasExam && hasPatient && hasDoctor;
  });
  
  const submitRequest = async () => {
    if (cart.value.length === 0) return;

    try {
      const resultsPayload = cart.value.map(item => ({
        examen_id: item.id,
        valeur: null, 
        unite: item.unite || ''
      }));

      const doc = doctors.value.find(d => d.user_id === selectedDoctorId.value);

      const payload = {
        results: resultsPayload,
        patient_id: null,
        origin_prescription_id: null,
        prescribed_by_id: selectedDoctorId.value, // 🟢 Injecté ici
        prescribed_by_name: doc ? doc.full_name : null,
        external_patient_info: null
      };

      if (selectedPatient.value) {
          payload.patient_id = selectedPatient.value.id;
          payload.origin_prescription_id = selectedPatient.value.prescription_id || selectedPatient.value.last_prescription_id || null;
      }
      else if (extForm.value.full_name) {
          payload.external_patient_info = { 
              nom: extForm.value.full_name, 
              prenom: '', 
              age: extForm.value.age,
              sexe: extForm.value.gender, 
              telephone: '' 
          };
      }

      await labStore.createBatchRequest(payload);
      
      alert("Dossier enregistré avec succès !");
      resetPatient();
      
    } catch (error) {
      console.error("Erreur lors de l'envoi :", error);
      alert("Erreur technique lors de l'enregistrement.");
    }
  };
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.5s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>