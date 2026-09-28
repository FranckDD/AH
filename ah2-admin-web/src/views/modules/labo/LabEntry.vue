<template>
  <div class="max-w-6xl mx-auto space-y-6 pb-20 animate-fade-in-up">
    
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-bold text-gray-800">Saisie Laboratoire</h1>
            <p class="text-sm text-gray-500">Gestion Multi-Examens & Patients Externes</p>
        </div>
        
        <div class="flex gap-3">
            <div v-if="labStore.successMessage" class="bg-green-100 text-green-800 px-4 py-2 rounded-lg flex items-center shadow-sm">
                <CheckCircleIcon class="w-5 h-5 mr-2"/> {{ labStore.successMessage }}
            </div>
            <button v-if="labStore.lastResultId" @click="downloadPdf" class="bg-indigo-100 text-indigo-700 px-4 py-2 rounded-lg font-bold flex items-center hover:bg-indigo-200 transition">
                <PrinterIcon class="w-5 h-5 mr-2"/> Imprimer PDF
            </button>
        </div>
    </div>

    <div v-if="labStore.error" class="bg-red-100 text-red-700 p-4 rounded-xl flex items-center border border-red-200">
        <ExclamationCircleIcon class="w-5 h-5 mr-2"/> {{ labStore.error }}
    </div>

    <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 relative z-20">
      <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
            <UserIcon class="w-5 h-5 text-indigo-600"/> 
            {{ selectedPatient ? 'Patient Sélectionné' : 'Identification Patient' }}
          </h3>
          <button v-if="!selectedPatient" @click="showExternalModal = true" class="text-sm bg-orange-50 text-orange-700 border border-orange-200 px-3 py-2 rounded-lg font-bold hover:bg-orange-100 transition flex items-center gap-2">
            <UserPlusIcon class="w-5 h-5"/> Nouveau Patient Externe
          </button>
      </div>

      <div v-if="!selectedPatient" class="relative">
        <input v-model="searchQuery" @input="handleSearch" type="text" placeholder="Rechercher (Nom, Prénom ou Code)..." class="w-full px-4 py-3 pl-10 border border-gray-300 rounded-xl focus:ring-indigo-500 focus:border-indigo-500 transition shadow-sm" autofocus />
        <ArrowPathIcon v-if="labStore.loading" class="w-5 h-5 text-indigo-500 animate-spin absolute right-3 top-3.5"/>
        <MagnifyingGlassIcon v-else class="w-5 h-5 text-gray-400 absolute left-3 top-3.5"/>
        
        <div v-if="labStore.searchResults.length > 0" class="absolute z-50 w-full bg-white border mt-2 rounded-xl shadow-xl max-h-60 overflow-y-auto">
          <div v-for="p in labStore.searchResults" :key="p.patient_id" @click="selectPatient(p)" class="px-4 py-3 hover:bg-indigo-50 cursor-pointer border-b last:border-0 flex justify-between items-center transition">
            <div>
                <p class="font-bold text-gray-800">{{ p.first_name }} {{ p.last_name }}</p>
                <p class="text-xs text-gray-500">{{ p.gender }} • Né(e) le: {{ formatDate(p.date_of_birth) }}</p>
            </div>
            <span class="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600 font-mono">ID: {{ p.patient_id }}</span>
          </div>
        </div>
      </div>

      <div v-else class="flex items-center justify-between p-4 bg-indigo-50 rounded-xl border border-indigo-100 animate-fade-in">
        <div class="flex items-center gap-4">
            <div class="h-12 w-12 rounded-full flex items-center justify-center font-bold text-xl uppercase text-white shadow" :class="selectedPatient.is_external ? 'bg-orange-500' : 'bg-indigo-600'">
                {{ selectedPatient.first_name?.charAt(0) || '?' }}
            </div>
            <div>
                <h4 class="font-bold text-gray-900 text-lg flex items-center gap-2">
                    {{ selectedPatient.first_name }} {{ selectedPatient.last_name }}
                    <span v-if="selectedPatient.is_external" class="text-[10px] bg-orange-100 text-orange-800 px-2 rounded-full border border-orange-200 uppercase tracking-widest">Externe</span>
                </h4>
                <div class="text-sm text-gray-600 flex gap-3">
                    <span>{{ calculateAge(selectedPatient) }} ans</span>
                    <span>{{ selectedPatient.gender }}</span>
                </div>
            </div>
        </div>
        <button @click="resetPatient" class="text-red-600 hover:bg-red-50 px-3 py-1 rounded-lg text-sm font-medium transition">Changer</button>
      </div>
    </div>

    <div v-if="selectedPatient" class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 animate-fade-in relative z-10">
        <label class="block text-sm font-medium text-gray-700 mb-2">Ajouter un examen à la liste</label>
        <div class="flex gap-4">
            <select v-model="examToAdd" class="flex-1 border-gray-300 rounded-xl focus:ring-indigo-500 focus:border-indigo-500 py-2.5">
                <option :value="null">-- Choisir un examen --</option>
                <option v-for="ex in labStore.exams" :key="ex.id" :value="ex">{{ ex.nom }} ({{ ex.code }})</option>
            </select>
            <button @click="addExamToList" :disabled="!examToAdd" class="bg-indigo-600 text-white px-6 py-2 rounded-xl font-bold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2 shadow-md">
                <PlusCircleIcon class="w-5 h-5"/> Ajouter
            </button>
        </div>
    </div>

    <div v-if="addedExams.length > 0" class="space-y-6">
        <div v-for="(examItem, index) in addedExams" :key="index" class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden animate-slide-up">
            <div class="bg-gray-50 px-6 py-3 border-b border-gray-200 flex justify-between items-center">
                <h3 class="font-bold text-gray-800 text-lg">{{ examItem.nom }}</h3>
                <button @click="removeExam(index)" class="text-red-500 hover:text-red-700 p-1 hover:bg-red-50 rounded">
                    <TrashIcon class="w-5 h-5"/>
                </button>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                    <thead class="bg-white text-gray-500 border-b border-gray-100 uppercase text-xs">
                        <tr>
                            <th class="px-6 py-3 w-1/3">Paramètre</th>
                            <th class="px-6 py-3 w-1/4">Valeur</th>
                            <th class="px-6 py-3">Unité</th>
                            <th class="px-6 py-3">Normes</th>
                            <th class="px-6 py-3 text-center">État</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-50">
                        <tr v-for="row in examItem.rows" :key="row.parametre_id" class="hover:bg-gray-50 transition">
                            <td class="px-6 py-3 font-medium text-gray-900">{{ row.nom_parametre }}</td>
                            <td class="px-6 py-3">
                                <input v-if="row.type_valeur === 'numeric'" type="number" step="0.01" v-model="row.valeur" @input="checkFlag(row)" :class="getInputColor(row)" class="w-full border-gray-300 rounded-lg text-right font-mono p-2 border" placeholder="0.00">
                                <input v-else type="text" v-model="row.valeur" class="w-full border-gray-300 rounded-lg p-2 border" placeholder="Résultat...">
                            </td>
                            <td class="px-6 py-3 text-gray-500">{{ row.unite }}</td>
                            <td class="px-6 py-3 text-xs text-gray-500">{{ row.min !== null ? `${row.min} - ${row.max}` : '--' }}</td>
                            <td class="px-6 py-3 text-center">
                                <span v-if="row.flagged" class="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-bold border border-red-200">ANORMAL</span>
                                <CheckIcon v-else-if="row.valeur" class="w-5 h-5 mx-auto text-green-500"/>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="p-4 bg-gray-50 border-t border-gray-200">
                <input v-model="examItem.note" placeholder="Note pour cet examen (ex: Sérum lipémique)" class="w-full text-sm border-gray-300 rounded-lg p-2 border bg-white" />
            </div>
        </div>

        <div class="flex justify-end pt-4 pb-10">
            <button @click="submitAll" :disabled="labStore.loading" class="bg-indigo-600 text-white px-8 py-3 rounded-xl font-bold shadow-lg hover:bg-indigo-700 transition transform hover:-translate-y-1 flex items-center gap-2 disabled:opacity-50">
                <ArrowPathIcon v-if="labStore.loading" class="animate-spin h-5 w-5"/>
                <CheckIcon v-else class="w-5 h-5"/>
                <span>VALIDER ET ENREGISTRER ({{ addedExams.length }})</span>
            </button>
        </div>
    </div>

    <div v-if="showExternalModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-bounce-in">
            <div class="px-6 py-4 bg-orange-50 border-b border-orange-100 flex justify-between items-center">
                <h3 class="font-bold text-orange-900">Nouveau Patient Externe</h3>
                <button @click="showExternalModal = false" class="text-gray-400 hover:text-red-500"><XMarkIcon class="w-6 h-6"/></button>
            </div>
            <div class="p-6 space-y-4">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Nom Complet</label>
                    <input v-model="extForm.nom" type="text" class="w-full border-gray-300 rounded-lg p-2 border" placeholder="Ex: KOUAM Emmanuel">
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Âge (Ans)</label>
                        <input v-model.number="extForm.age" type="number" class="w-full border-gray-300 rounded-lg p-2 border">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Sexe</label>
                        <select v-model="extForm.sexe" class="w-full border-gray-300 rounded-lg p-2 border">
                            <option value="M">Masculin</option>
                            <option value="F">Féminin</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="p-4 bg-gray-50 flex justify-end gap-3">
                <button @click="showExternalModal = false" class="px-4 py-2 text-gray-600 font-medium hover:bg-gray-200 rounded-lg">Annuler</button>
                <button @click="confirmExternalPatient" class="px-4 py-2 bg-orange-600 text-white font-bold rounded-lg hover:bg-orange-700 shadow">Confirmer</button>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useLabStore } from '@/stores/labStore';
import debounce from 'lodash/debounce';
import { 
  UserIcon, UserPlusIcon, MagnifyingGlassIcon, PlusCircleIcon, TrashIcon, 
  CheckCircleIcon, ExclamationCircleIcon, CheckIcon, PrinterIcon, ArrowPathIcon, XMarkIcon 
} from '@heroicons/vue/24/outline';

const labStore = useLabStore();

// --- ETATS ---
const searchQuery = ref('');
const selectedPatient = ref(null);
const showExternalModal = ref(false);
const examToAdd = ref(null);
const addedExams = ref([]);
const extForm = ref({ nom: '', age: null, sexe: 'M' });

// --- INIT ---
onMounted(async () => {
    labStore.clearMessages();
    if (labStore.exams.length === 0) await labStore.fetchExams();
});

// --- RECHERCHE ---
const handleSearch = debounce(async () => {
    if (searchQuery.value.length > 1) {
        await labStore.searchFiles(searchQuery.value);
    } else {
        labStore.searchResults = [];
    }
}, 300);

const selectPatient = (p) => {
    selectedPatient.value = { ...p, is_external: false };
    searchQuery.value = '';
    labStore.searchResults = [];
    labStore.clearMessages();
};

// --- LOGIQUE PATIENT EXTERNE ---
const confirmExternalPatient = () => {
    if (!extForm.value.nom || !extForm.value.age) return alert('Nom et âge requis');
    selectedPatient.value = {
        patient_id: null,
        first_name: extForm.value.nom,
        last_name: '',
        age_fixed: extForm.value.age,
        gender: extForm.value.sexe,
        is_external: true
    };
    showExternalModal.value = false;
    extForm.value = { nom: '', age: null, sexe: 'M' };
};

const resetPatient = () => {
    if (addedExams.value.length > 0 && !confirm("Changer de patient annulera la saisie en cours ?")) return;
    selectedPatient.value = null;
    addedExams.value = [];
    labStore.clearMessages();
};

// --- AJOUT EXAMENS & PARAMETRES ---
const getReferenceRange = (param, patient) => {
    if (!param.reference_ranges) return null;
    const age = calculateAge(patient);
    const sexe = patient.gender?.toUpperCase().startsWith('F') ? 'F' : 'M';
    return param.reference_ranges.find(r => 
        (r.sexe === 'A' || r.sexe === sexe) && (age >= r.age_min && age <= r.age_max)
    );
};

const addExamToList = async () => {
    if (!examToAdd.value) return;
    const params = await labStore.fetchExamParams(examToAdd.value.id);
    if (!params.length) return alert("Cet examen n'a pas de paramètres configurés.");

    const rows = params.map(p => {
        const range = getReferenceRange(p, selectedPatient.value);
        return {
            parametre_id: p.id,
            nom_parametre: p.nom_parametre,
            unite: p.unite,
            type_valeur: p.type_resultat || 'numeric', // Aligné sur le backend
            valeur: null,
            min: range ? parseFloat(range.valeur_min) : null,
            max: range ? parseFloat(range.valeur_max) : null,
            flagged: false
        };
    });

    addedExams.value.push({ id: examToAdd.value.id, nom: examToAdd.value.nom, note: '', rows: rows });
    examToAdd.value = null;
};

const removeExam = (index) => addedExams.value.splice(index, 1);

// --- VALIDATION & FLAGS ---
const checkFlag = (row) => {
    if (row.type_valeur !== 'numeric' || !row.valeur || row.min === null) {
        row.flagged = false;
        return;
    }
    const val = parseFloat(row.valeur);
    row.flagged = (val < row.min || val > row.max);
};

const getInputColor = (row) => row.flagged ? 'bg-red-50 text-red-900 border-red-300' : 'bg-white';

// --- ENREGISTREMENT ---
const submitAll = async () => {
    if (addedExams.value.length === 0) return;
    labStore.clearMessages();

    for (const exam of addedExams.value) {
        const details = exam.rows
            .filter(r => r.valeur !== null && r.valeur !== '')
            .map(r => ({
                parametre_id: r.parametre_id,
                valeur: r.valeur.toString(),
                is_abnormal: r.flagged
            }));

        if (details.length === 0) continue;

        const payload = {
            patient_id: selectedPatient.value.is_external ? null : selectedPatient.value.patient_id,
            examen_id: exam.id,
            external_patient_info: selectedPatient.value.is_external ? {
                nom: selectedPatient.value.first_name,
                age: selectedPatient.value.age_fixed,
                sexe: selectedPatient.value.gender
            } : null,
            status: "completed",
            note: exam.note,
            details: details
        };
        await labStore.saveResults(payload);
    }
    addedExams.value = [];
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

const downloadPdf = () => {
    if(labStore.lastResultId) window.open(`${import.meta.env.VITE_API_URL}/labo/results/${labStore.lastResultId}/pdf`, '_blank');
};

const calculateAge = (p) => p.is_external ? p.age_fixed : (p.date_of_birth ? new Date().getFullYear() - new Date(p.date_of_birth).getFullYear() : 0);
const formatDate = (d) => d ? new Date(d).toLocaleDateString('fr-FR') : '';
</script>