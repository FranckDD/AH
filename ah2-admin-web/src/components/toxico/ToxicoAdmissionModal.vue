<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-xs">
    
    <div class="relative mx-auto w-full max-w-2xl bg-white shadow-xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
      
      <div class="px-6 py-4 border-b border-gray-100 bg-indigo-600 rounded-t-2xl flex justify-between items-center shrink-0">
        <h3 class="text-lg font-bold text-white flex items-center">
            <UserPlusIcon class="h-6 w-6 mr-2" />
            {{ t('toxico.admission.title') }}
        </h3>
        <button @click="$emit('close')" class="text-indigo-100 hover:text-white transition">
          <span class="text-2xl font-bold">&times;</span>
        </button>
      </div>

      <div class="p-6 overflow-y-auto">
        <form @submit.prevent="handleSubmit" class="space-y-6">
            
            <div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
                <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 border-b border-gray-200 pb-2">
                    {{ t('toxico.admission.section_patient') }}
                </h4>

                <div v-if="!showNewPatientForm && !selectedExistingPatient" class="space-y-2">
                    <input v-model="searchQuery" @input="onSearchInput" type="text"
                           placeholder="Rechercher un patient existant (nom, code)..."
                           class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                    <ul v-if="searchResults.length" class="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-48 overflow-y-auto">
                        <li v-for="p in searchResults" :key="p.patient_id" @click="selectExistingPatient(p)"
                            class="px-3 py-2 hover:bg-indigo-50 cursor-pointer text-sm">
                            <span class="font-medium">{{ p.first_name }} {{ p.last_name }}</span>
                            <span class="text-gray-500 ml-2">{{ p.code_patient }} — {{ p.birth_date }}</span>
                        </li>
                    </ul>
                    <p v-if="isSearching" class="text-xs text-gray-400">Recherche...</p>
                    <button type="button" @click="startNewPatient" class="text-sm text-indigo-600 font-medium hover:underline">
                        + Nouveau patient
                    </button>
                </div>

                <div v-if="selectedExistingPatient" class="flex items-center justify-between bg-indigo-50 border border-indigo-200 rounded-lg px-3 py-2">
                    <span class="text-sm font-medium text-indigo-900">
                        {{ selectedExistingPatient.first_name }} {{ selectedExistingPatient.last_name }} ({{ selectedExistingPatient.code_patient }})
                    </span>
                    <button type="button" @click="selectedExistingPatient = null" class="text-xs text-indigo-600 hover:underline">Changer</button>
                </div>

                <div v-if="selectedExistingPatient || showNewPatientForm" class="space-y-4 mt-3">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.date') }} <span class="text-red-500">*</span></label>
                        <input v-model="form.admissionDate" type="date" required
                               :max="today"
                               class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.substance') }} <span class="text-red-500">*</span></label>
                            <select v-model="form.substance" required
                                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                                <option value="Alcool">{{ t('toxico.substances.alcohol') }}</option>
                                <option value="Cannabis">{{ t('toxico.substances.cannabis') }}</option>
                                <option value="Opioïdes">{{ t('toxico.substances.opioids') }}</option>
                                <option value="Cocaïne">{{ t('toxico.substances.cocaine') }}</option>
                                <option value="Polytoxicomanie">{{ t('toxico.substances.poly') }}</option>
                                <option value="Autre">Autre</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.psychologist') }} <span class="text-red-500">*</span></label>
                            <select v-model="form.psychologist" required
                                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                                <option :value="null" disabled selected>-- Sélectionner --</option>
                                <option v-for="psy in psychologistsList" :key="psy.id" :value="psy.id">
                                    {{ psy.name }}
                                </option>
                            </select>
                        </div>
                    </div>
                </div>

                <div v-if="showNewPatientForm" class="space-y-4 mt-3">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.firstname') }} <span class="text-red-500">*</span></label>
                            <input v-model="form.firstName" type="text" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.lastname') }} <span class="text-red-500">*</span></label>
                            <input v-model="form.lastName" type="text" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.dob') }} <span class="text-red-500">*</span></label>
                            <input v-model="form.dob" type="date" required
                                   :max="maxDate"
                                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.mothers_name') }} <span class="text-red-500">*</span></label>
                            <input v-model="form.mothersName" type="text" required
                                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
                                   placeholder="Nom de jeune fille..." />
                        </div>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.address') }}</label>
                        <div class="relative">
                            <MapPinIcon class="h-5 w-5 text-gray-400 absolute top-2.5 left-3" />
                            <input v-model="form.address" type="text"
                                   class="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                        </div>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.contact') }}</label>
                        <input v-model="form.contact" type="tel"
                               class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
                               placeholder="Numéro de téléphone..." />
                    </div>
                </div>
            </div>

            <div class="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                <h4 class="text-xs font-bold text-indigo-800 uppercase tracking-wider mb-3 border-b border-indigo-200 pb-2">
                    {{ t('toxico.admission.section_guardian') }}
                </h4>
                <div class="space-y-4">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.guardian_name') }} <span class="text-red-500">*</span></label>
                            <input v-model="form.guardianName" type="text" required 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.guardian_contact') }} <span class="text-red-500">*</span></label>
                            <input v-model="form.guardianContact" type="tel" required 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.consent_file') }}</label>
                        <div class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg bg-white hover:bg-gray-50 transition cursor-pointer relative">
                            <div class="space-y-1 text-center">
                                <PaperClipIcon class="mx-auto h-8 w-8 text-gray-400" />
                                <div class="flex text-sm text-gray-600 justify-center">
                                    <label for="file-upload" class="relative cursor-pointer bg-white rounded-md font-medium text-indigo-600 hover:text-indigo-500 focus-within:outline-hidden">
                                        <span>{{ fileName || t('toxico.admission.upload_placeholder') }}</span>
                                        <input id="file-upload" name="file-upload" type="file" 
                                               class="sr-only" @change="handleFileUpload" accept=".pdf,.jpg,.png" />
                                    </label>
                                </div>
                                <p class="text-xs text-gray-500">PDF, PNG, JPG jusqu'à 5MB</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('toxico.admission.notes') }}</label>
                <textarea v-model="form.notes" rows="3" 
                          class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
                          placeholder="Notes supplémentaires..."></textarea>
            </div>

            <!-- Messages d'erreur -->
            <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-sm">
                <div class="flex">
                    <div class="shrink-0">
                        <ExclamationCircleIcon class="h-5 w-5 text-red-400" />
                    </div>
                    <div class="ml-3">
                        <p class="text-sm text-red-700">{{ errorMessage }}</p>
                    </div>
                </div>
            </div>

            <div class="pt-4 flex justify-end space-x-3 border-t border-gray-100 shrink-0">
                <button type="button" @click="$emit('close')" :disabled="isLoading" 
                        class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition disabled:opacity-50">
                    {{ t('toxico.admission.cancel') }}
                </button>
                <button 
                    type="submit" 
                    :disabled="isLoading || !isFormValid"
                    class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium shadow-md transition flex items-center disabled:opacity-75 disabled:cursor-not-allowed"
                >
                    <template v-if="isLoading">
                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Traitement...
                    </template>
                    <template v-else>
                        <CheckCircleIcon class="h-5 w-5 mr-2" />
                        {{ t('toxico.admission.submit') }}
                    </template>
                </button>
            </div>

        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { 
    UserPlusIcon, 
    CheckCircleIcon, 
    MapPinIcon, 
    PaperClipIcon,
    ExclamationCircleIcon 
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const emit = defineEmits(['close', 'save']); 
const toxicoStore = useToxicoStore();

const today = new Date().toISOString().split('T')[0];
const maxDate = new Date();
maxDate.setFullYear(maxDate.getFullYear() - 10); // Minimum 10 ans
const maxDateFormatted = maxDate.toISOString().split('T')[0];

const fileName = ref('');
const isLoading = ref(false);
const errorMessage = ref('');

const psychologistsList = computed(() => toxicoStore.psychologists);

onMounted(() => {
    toxicoStore.fetchPsychologists();
});

const form = reactive({
    firstName: '',
    lastName: '',
    dob: '',
    mothersName: '',
    address: '',
    contact: '',
    admissionDate: today,
    substance: 'Alcool',
    psychologist: null, 
    guardianName: '',
    guardianContact: '',
    consentFile: null,
    notes: ''
});

// Recherche d'un patient existant (chantier 6, tache 4)
const searchQuery = ref('');
const searchResults = ref([]);
const isSearching = ref(false);
const selectedExistingPatient = ref(null);
const showNewPatientForm = ref(false);

let searchTimeout = null;
const onSearchInput = () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        if (searchQuery.value.trim().length < 2) {
            searchResults.value = [];
            return;
        }
        isSearching.value = true;
        searchResults.value = await toxicoStore.searchExistingPatients(searchQuery.value);
        isSearching.value = false;
    }, 300);
};

const selectExistingPatient = (patient) => {
    selectedExistingPatient.value = patient;
    showNewPatientForm.value = false;
    searchResults.value = [];
};

const startNewPatient = () => {
    selectedExistingPatient.value = null;
    showNewPatientForm.value = true;
};

// Validation du formulaire
const isFormValid = computed(() => {
    const patientOk = selectedExistingPatient.value || (
        form.firstName.trim() && form.lastName.trim() && form.dob && form.mothersName.trim()
    );
    return patientOk &&
           form.admissionDate &&
           form.substance &&
           form.psychologist &&
           form.guardianName.trim() &&
           form.guardianContact.trim();
});

// Watcher pour reset les erreurs
watch(form, () => {
    errorMessage.value = '';
});

const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
        // Validation de la taille du fichier (5MB max)
        if (file.size > 5 * 1024 * 1024) {
            errorMessage.value = "Le fichier est trop volumineux (max 5MB)";
            return;
        }
        fileName.value = file.name; // Pour l'affichage
        form.consentFile = file; 
    }
};

const handleSubmit = async () => {
    //console.log("=".repeat(60));
    //console.log("📤 TOXICO ADMISSION - Début de l'envoi");
    //console.log("=".repeat(60));
    
    // Validation
    if (!isFormValid.value) {
        errorMessage.value = "Veuillez remplir tous les champs obligatoires (*)";
        return;
    }

    // Validation des dates (uniquement pertinent pour un nouveau patient)
    const admissionDate = new Date(form.admissionDate);
    const todayDate = new Date();

    if (admissionDate > todayDate) {
        errorMessage.value = "La date d'admission ne peut pas être dans le futur";
        return;
    }

    if (!selectedExistingPatient.value) {
        const dobDate = new Date(form.dob);

        if (dobDate > todayDate) {
            errorMessage.value = "La date de naissance ne peut pas être dans le futur";
            return;
        }

        if (dobDate > admissionDate) {
            errorMessage.value = "La date de naissance ne peut pas être après la date d'admission";
            return;
        }
    }

    if (isLoading.value) return;

    isLoading.value = true;
    errorMessage.value = '';

    // 🟢 Préparation du payload avec validation
    const payload = {
        admissionDate: form.admissionDate,
        substance: form.substance,
        psychologist: parseInt(form.psychologist, 10),
        guardianName: form.guardianName.trim(),
        guardianContact: form.guardianContact.trim(),
        consentFile: form.consentFile || "",
        notes: form.notes?.trim() || ""
    };

    if (selectedExistingPatient.value) {
        payload.patientId = selectedExistingPatient.value.patient_id;
    } else {
        payload.firstName = form.firstName.trim();
        payload.lastName = form.lastName.trim();
        payload.dob = form.dob;
        payload.mothersName = form.mothersName.trim();
        payload.address = form.address?.trim() || "";
        payload.contact = form.contact?.trim() || "";
    }

    // Log détaillé
    //console.log("📋 Payload préparé:", JSON.stringify(payload, null, 2));
    

    try {
        //console.log("🔄 Appel à toxicoStore.addPatient...");
        await toxicoStore.addPatient(payload);
        
        console.log("✅ Admission réussie!");
        emit('save'); 
        emit('close'); 
        
    } catch (error) {
        console.error("❌ Erreur lors de l'admission:", error);
        
        // Gestion détaillée des erreurs
        if (error.response) {
            console.error("📊 Détails de l'erreur:", {
                status: error.response.status,
                data: error.response.data,
                headers: error.response.headers
            });
            
            if (error.response.status === 422) {
                // Erreur de validation Pydantic
                const details = error.response.data.detail;
                if (Array.isArray(details)) {
                    const errors = details.map(err => {
                        const field = err.loc.join('.');
                        return `${field}: ${err.msg}`;
                    });
                    errorMessage.value = `Erreurs de validation:\n${errors.join('\n')}`;
                } else {
                    errorMessage.value = `Erreur: ${details}`;
                }
            } else if (error.response.status === 400) {
                errorMessage.value = error.response.data.detail || "Données invalides";
            } else if (error.response.status === 401) {
                errorMessage.value = "Session expirée. Veuillez vous reconnecter.";
                // Redirection pourrait être ajoutée ici
            } else {
                errorMessage.value = `Erreur serveur (${error.response.status}): ${error.response.data.detail || 'Veuillez réessayer'}`;
            }
        } else if (error.request) {
            errorMessage.value = "Erreur réseau. Veuillez vérifier votre connexion.";
            console.error("🌐 Erreur réseau:", error.request);
        } else {
            errorMessage.value = error.message || "Une erreur inattendue est survenue";
            console.error("⚠️ Erreur inattendue:", error.message);
        }
        
        // Garder la modale ouverte pour permettre la correction
    } finally {
        isLoading.value = false;
        //console.log("=".repeat(60));
        //console.log("📤 TOXICO ADMISSION - Fin du traitement");
        //console.log("=".repeat(60));
    }
};
</script>