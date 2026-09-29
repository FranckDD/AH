<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
    <div class="bg-white w-full max-w-4xl max-h-[90vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-zoom-in">
      
      <div class="px-8 py-6 border-b border-gray-100 flex justify-between items-start bg-gray-50/50">
        <div>
          <div class="flex items-center gap-3 mb-1">
            <h2 class="text-2xl font-bold text-gray-900">{{ getPatientName }}</h2>
            <span :class="statusStyles" class="px-3 py-1 rounded-full text-xs font-black uppercase tracking-widest">
              {{ translateStatus(result.status) }}
            </span>
          </div>
          <p class="text-gray-500 text-sm flex items-center gap-2">
            <CalendarIcon class="w-4 h-4"/> Examen du {{ formatDate(result.test_date || result.created_at) }}
            <span class="text-gray-300">|</span>
            <span class="font-mono text-xs">ID: {{ result.result_id || result.id }}</span>
            <span v-if="result.code" class="font-mono text-xs text-indigo-400">| Lot: {{ result.code }}</span>
          </p>
        </div>
        <button @click="$emit('close')" class="p-2 hover:bg-gray-200 rounded-full transition">
          <XMarkIcon class="w-6 h-6 text-gray-400" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-8 space-y-8">
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="space-y-3">
            <h3 class="text-xs font-bold text-indigo-600 uppercase tracking-wider">Informations Patient</h3>
            <div class="bg-gray-50 p-4 rounded-2xl border border-gray-100">
                <p class="text-sm font-medium text-gray-700">Type: 
                  <span class="text-gray-900 font-bold">
                    {{ (result.is_external || result.external_patient_info) ? 'Externe' : 'Interne' }}
                  </span>
                </p>
                <p class="text-sm font-medium text-gray-700">Sexe: 
                  <span class="text-gray-900">
                    {{ result.patient_info?.sexe || result.patient_sexe || 'Non renseigné' }}
                  </span>
                </p>
                <p class="text-sm font-medium text-gray-700">Âge: 
                  <span class="text-gray-900">
                    {{ result.patient_info?.age ? `${result.patient_info.age} ans` : (result.patient_age || 'Non renseigné') }} 
                  </span>
                </p>
            </div>
          </div>

          <div class="space-y-3">
            <h3 class="text-xs font-bold text-indigo-600 uppercase tracking-wider">Prescription</h3>
            <div class="bg-gray-50 p-4 rounded-2xl border border-gray-100">
                <p class="text-sm font-medium text-gray-700">Prescripteur: 
                  <span class="text-gray-900">{{ result.medecin_prescripteur || result.prescriber || 'Non spécifié' }}</span>
                </p>
                <p class="text-sm font-medium text-gray-700">Examen: 
                  <span class="text-gray-900 font-bold">{{ result.examen_nom || result.exam_name || 'Non spécifié' }}</span>
                </p>
            </div>
          </div>
        </div>

        <div class="space-y-4">
          <h3 class="text-xs font-bold text-indigo-600 uppercase tracking-wider">Résultats Biologiques</h3>
          <div class="border border-gray-100 rounded-2xl overflow-hidden shadow-xs">
            <table class="w-full text-left border-collapse">
              <thead class="bg-gray-50 border-b border-gray-100 text-[10px] uppercase font-bold text-gray-500">
                <tr>
                  <th class="px-6 py-3">Paramètre</th>
                  <th class="px-6 py-3 text-center">Résultat</th>
                  <th class="px-6 py-3">Unité</th>
                  <th class="px-6 py-3">Valeurs de Référence</th>
                  <th class="px-6 py-3 text-right">Interprétation</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                
                <tr v-for="(detail, index) in result.details" :key="detail.detail_id || index" class="hover:bg-blue-50/30 transition">
                  <td class="px-6 py-4 font-semibold text-gray-700">{{ detail.nom || detail.parameter_name || 'Inconnu' }}</td>
                  
                  <td class="px-6 py-4 text-center">
                    <span :class="getValueStyle(detail)" class="text-lg font-bold">
                      {{ detail.valeur !== null && detail.valeur !== undefined && detail.valeur !== '' ? detail.valeur : '-' }}
                    </span>
                    <span v-if="detail.flag" class="text-xs ml-1 text-red-500 font-bold" title="Anormal">
                      ({{ detail.flag }})
                    </span>
                  </td>
                  
                  <td class="px-6 py-4 text-gray-500 italic text-sm">{{ detail.unite || detail.unit || '-' }}</td>
                  
                  <td class="px-6 py-4 text-gray-400 text-sm font-mono whitespace-nowrap">
                    {{ getRange(detail.ranges, result.patient_info?.sexe) }}
                  </td>
                  
                  <td class="px-6 py-4 text-right">
                    <span v-if="detail.interpretation" class="text-xs px-2 py-1 bg-gray-100 rounded-sm text-gray-600 font-medium">
                        {{ detail.interpretation }}
                    </span>
                    <span v-else class="text-gray-300">-</span>
                  </td>
                </tr>
                
                <tr v-if="!result.details?.length">
                  <td colspan="5" class="px-6 py-8 text-center text-gray-400 text-sm">
                    Aucun paramètre configuré ou enregistré pour cet examen.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="result.note || result.comments" class="bg-amber-50 p-4 rounded-2xl border border-amber-100">
            <h4 class="text-xs font-bold text-amber-800 uppercase mb-1">Conclusion / Notes générales</h4>
            <p class="text-gray-700 text-sm italic whitespace-pre-line">" {{ result.note || result.comments }} "</p>
        </div>
      </div>

      <div class="px-8 py-6 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
        <button @click="$emit('close')" class="px-6 py-2 text-gray-600 font-bold hover:bg-gray-200 rounded-xl transition">
          Fermer
        </button>
        <button 
          v-if="result.status !== 'pending'"
          @click="printPdf" 
          class="px-6 py-2 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 shadow-lg shadow-indigo-200 flex items-center gap-2 transition"
        >
          <PrinterIcon class="w-5 h-5"/> Imprimer
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { XMarkIcon, CalendarIcon, PrinterIcon } from '@heroicons/vue/24/outline';
import dayjs from 'dayjs';

const props = defineProps({
  result: { type: Object, required: true }
});

const emit = defineEmits(['close', 'print']);

// --- COMPUTED ---
const getPatientName = computed(() => {
  const r = props.result;
  if (r.patient_info?.nom) return r.patient_info.nom;
  if (r.patient_name) return r.patient_name; 
  if (r.external_patient_info) return r.external_patient_info.nom_complet || 'Patient Externe';
  return 'Anonyme';
});

const statusStyles = computed(() => {
    switch(props.result.status) {
        case 'validated': return 'bg-green-100 text-green-700 border border-green-200';
        case 'completed': return 'bg-blue-100 text-blue-700 border border-blue-200';
        default: return 'bg-amber-100 text-amber-700 border border-amber-200';
    }
});

// --- METHODS ---
const translateStatus = (status) => {
    const map = {
        'pending': 'En attente',
        'completed': 'Terminé',
        'validated': 'Validé'
    };
    return map[status] || status || 'Inconnu';
};

const formatDate = (date) => {
    if (!date) return 'Date inconnue';
    return dayjs(date).format('DD/MM/YYYY à HH:mm');
};

// Fonction récupérée de ta paillasse pour lire la valeur de référence correctement
const getRange = (ranges, sexePatient) => {
    if (!ranges || ranges.length === 0) return '-';
    const range = ranges.find(r => r.sexe === sexePatient) || ranges[0];
    return `${range.min} - ${range.max}`;
};

const getValueStyle = (detail) => {
    // Si la valeur a été flaggée (Haut, Bas, Anormal)
    if (detail.flag === 'H' || detail.flag === 'L' || detail.flag === 'A' || detail.flagged) {
        return 'text-red-600';
    }
    return 'text-gray-900';
};

const printPdf = () => emit('print', props.result);
</script>

<style scoped>
@keyframes zoom-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
.animate-zoom-in {
  animation: zoom-in 0.2s ease-out;
}
</style>