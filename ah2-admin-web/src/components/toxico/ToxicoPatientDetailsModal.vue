<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    
    <div class="relative mx-auto w-full max-w-2xl bg-white shadow-2xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
      
      <!-- En-tête -->
      <div class="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-2xl flex justify-between items-center flex-shrink-0">
        <div class="flex items-center">
          <div class="bg-blue-100 p-2 rounded-lg mr-3">
            <UserCircleIcon class="h-6 w-6 text-blue-700" />
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-800">Détails du Patient</h3>
            <p class="text-sm text-gray-600">Informations d'admission et contact</p>
          </div>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 bg-white p-2 rounded-full shadow-sm border border-gray-200 transition">
          <span class="text-xl font-bold">&times;</span>
        </button>
      </div>

      <!-- Contenu -->
      <div class="p-6 overflow-y-auto">
        <div v-if="patient" class="space-y-6">
          
          <!-- Section identité -->
          <div class="bg-white border border-gray-200 rounded-xl p-5">
            <h4 class="text-sm font-bold text-blue-700 uppercase tracking-wider mb-4 pb-2 border-b border-blue-100 flex items-center">
              <IdentificationIcon class="h-4 w-4 mr-2" />
              Identité
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Prénom</label>
                <p class="font-semibold text-gray-800">{{ patient.firstName || patient.first_name || 'Non renseigné' }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Nom</label>
                <p class="font-semibold text-gray-800">{{ patient.lastName || patient.last_name || 'Non renseigné' }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Date de naissance</label>
                <p class="font-semibold text-gray-800">{{ formatDate(patient.dob) }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Âge</label>
                <p class="font-semibold text-gray-800">{{ calculateAge(patient.dob) }} ans</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Nom de jeune fille de la mère</label>
                <p class="font-semibold text-gray-800">{{ patient.mothersName || patient.mothers_name || 'Non renseigné' }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Code patient</label>
                <p class="font-mono font-bold text-blue-600">{{ patient.code || 'N/A' }}</p>
              </div>
            </div>
          </div>

          <!-- Section contact -->
          <div class="bg-white border border-gray-200 rounded-xl p-5">
            <h4 class="text-sm font-bold text-green-700 uppercase tracking-wider mb-4 pb-2 border-b border-green-100 flex items-center">
              <PhoneIcon class="h-4 w-4 mr-2" />
              Contact & Localisation
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <div class="col-span-2">
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Adresse</label>
                <p class="font-semibold text-gray-800">{{ patient.address || 'Non renseignée' }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Téléphone patient</label>
                <p class="font-semibold text-gray-800">{{ patient.contact || 'Non renseigné' }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Substance</label>
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-800">
                  {{ patient.substance || 'Non spécifiée' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Section admission -->
          <div class="bg-white border border-gray-200 rounded-xl p-5">
            <h4 class="text-sm font-bold text-purple-700 uppercase tracking-wider mb-4 pb-2 border-b border-purple-100 flex items-center">
              <CalendarIcon class="h-4 w-4 mr-2" />
              Admission
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Date d'admission</label>
                <p class="font-semibold text-gray-800">{{ formatDate(patient.admissionDate || patient.admission_date) }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Psychologue</label>
                <p class="font-semibold text-gray-800">{{ patient.psychologist || 'Non assigné' }}</p>
              </div>
              <div class="col-span-2">
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Statut actuel</label>
                <div class="flex items-center space-x-3">
                  <span :class="getPhaseColor(patient.currentPhase || 1)" class="px-3 py-1 text-xs font-bold rounded-full border shadow-sm">
                    Phase {{ patient.currentPhase || 1 }}
                  </span>
                  <span v-if="patient.relapseCount > 0" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">
                    ⚠️ {{ patient.relapseCount }} rechute(s)
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Section tuteur -->
          <div class="bg-white border border-gray-200 rounded-xl p-5">
            <h4 class="text-sm font-bold text-orange-700 uppercase tracking-wider mb-4 pb-2 border-b border-orange-100 flex items-center">
              <ShieldCheckIcon class="h-4 w-4 mr-2" />
              Tuteur légal
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Nom du tuteur</label>
                <p class="font-semibold text-gray-800">{{ patient.guardianName || patient.guardian_name || 'Non renseigné' }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Contact du tuteur</label>
                <p class="font-semibold text-gray-800">{{ patient.guardianContact || patient.guardian_contact || 'Non renseigné' }}</p>
              </div>
              <div class="col-span-2">
                <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Consentement signé</label>
                <p class="font-semibold text-gray-800">{{ patient.consentFile || patient.consent_file || 'Aucun fichier téléchargé' }}</p>
              </div>
            </div>
          </div>

          <!-- Section notes -->
          <div v-if="patient.notes" class="bg-white border border-gray-200 rounded-xl p-5">
            <h4 class="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4 pb-2 border-b border-gray-100 flex items-center">
              <DocumentTextIcon class="h-4 w-4 mr-2" />
              Notes additionnelles
            </h4>
            <p class="text-gray-700 whitespace-pre-line">{{ patient.notes }}</p>
          </div>

        </div>
        
        <!-- Message si pas de patient -->
        <div v-else class="text-center py-10 text-gray-500">
          <UserCircleIcon class="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p>Aucune information patient disponible</p>
        </div>
      </div>

      <!-- Pied de page -->
      <div class="px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-2xl flex justify-between items-center flex-shrink-0">
        <div class="text-sm text-gray-500">
          Dossier créé le {{ formatDate(patient?.createdAt || new Date().toISOString()) }}
        </div>
        <div class="flex space-x-2">
          <button 
            @click="$emit('close')"
            class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 font-medium transition"
          >
            Fermer
          </button>
          <button 
            @click="openDossier"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition flex items-center"
          >
            <ClipboardDocumentListIcon class="h-4 w-4 mr-2" />
            Ouvrir le dossier complet
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { 
  UserCircleIcon,
  IdentificationIcon,
  PhoneIcon,
  CalendarIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon
} from '@heroicons/vue/24/outline';

const props = defineProps({
  patient: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['close', 'open-dossier']);

// Formater une date
const formatDate = (dateString) => {
  if (!dateString) return 'Non renseignée';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  } catch (e) {
    return dateString;
  }
};

// Calculer l'âge
const calculateAge = (dob) => {
  if (!dob) return '?';
  try {
    const birthDate = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  } catch (e) {
    return '?';
  }
};

// Couleur de phase (identique à celle dans la liste)
const getPhaseColor = (phase) => {
  switch(phase) {
    case 1: return 'bg-red-100 text-red-800 border-red-200'; 
    case 2: return 'bg-orange-100 text-orange-800 border-orange-200'; 
    case 3: return 'bg-blue-100 text-blue-800 border-blue-200'; 
    case 4: return 'bg-green-100 text-green-800 border-green-200'; 
    default: return 'bg-gray-100';
  }
};

// Ouvrir le dossier complet
const openDossier = () => {
  if (props.patient?.patient_id) {
    emit('open-dossier', props.patient.patient_id);
    emit('close');
  }
};
</script>