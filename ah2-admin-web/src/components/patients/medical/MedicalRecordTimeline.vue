<template>
  <div class="relative pl-4 border-l-2 border-gray-200 space-y-8">
    
    <div v-for="record in records" :key="record.record_id" class="relative">
        <div class="absolute -left-[21px] top-1 h-4 w-4 rounded-full bg-emerald-500 border-2 border-white ring-2 ring-emerald-100"></div>
        
        <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition">
            <div class="flex justify-between items-start mb-2">
                <div>
                    <h4 class="font-bold text-gray-900 text-lg">{{ record.diagnosis || 'Consultation Générale' }}</h4>
                    <p class="text-sm text-gray-500">
                        {{ formatDate(record.consultation_date) }} • {{ authorLabel(record) }}
                    </p>
                    <p v-if="record.needs_doctor_review" class="mt-1">
                        <span
                            class="inline-block px-2 py-0.5 text-[11px] font-semibold rounded-full"
                            :class="record.reviewed_at ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'"
                        >
                            {{ record.reviewed_at ? 'Pris en charge' : (record.assigned_doctor_id ? 'À transmettre — assigné' : 'À transmettre — file d\'attente') }}
                        </span>
                    </p>
                </div>
                <span class="px-2 py-1 text-xs font-bold rounded bg-gray-100 text-gray-600">
                    {{ record.motif_code }}
                </span>
            </div>

            <div class="grid grid-cols-3 gap-2 mb-3 bg-gray-50 p-2 rounded-lg text-xs">
                <div class="text-center">
                    <span class="block text-gray-400">Tension</span>
                    <span class="font-bold text-gray-700">{{ record.bp || '-' }}</span>
                </div>
                <div class="text-center border-l border-gray-200">
                    <span class="block text-gray-400">Poids</span>
                    <span class="font-bold text-gray-700">{{ record.weight ? record.weight + ' kg' : '-' }}</span>
                </div>
                <div class="text-center border-l border-gray-200">
                    <span class="block text-gray-400">Temp</span>
                    <span class="font-bold text-gray-700">{{ record.temperature ? record.temperature + '°' : '-' }}</span>
                </div>
            </div>

            <p class="text-gray-700 text-sm whitespace-pre-line">{{ record.notes || record.symptoms || 'Aucune note' }}</p>

            <div v-if="record.allergies || record.medical_history" class="mt-2 grid grid-cols-2 gap-2 text-xs">
                <div v-if="record.allergies">
                    <p class="font-bold text-gray-500 uppercase">Allergies</p>
                    <p class="text-gray-700">{{ record.allergies }}</p>
                </div>
                <div v-if="record.medical_history">
                    <p class="font-bold text-gray-500 uppercase">Antécédents</p>
                    <p class="text-gray-700">{{ record.medical_history }}</p>
                </div>
            </div>

            <div v-if="record.treatment" class="mt-3 pt-3 border-t border-gray-100">
                <p class="text-xs font-bold text-gray-500 uppercase">Traitement prescrit</p>
                <p class="text-sm text-gray-800">{{ record.treatment }}</p>
            </div>

            <div v-if="canManage" class="mt-3 pt-3 border-t border-gray-100 flex gap-2">
                <button
                    @click="$emit('edit', record)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 transition"
                >
                    Modifier
                </button>
                <button
                    @click="$emit('prescribe', record)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-600 text-white hover:bg-purple-700 transition"
                >
                    Prescrire
                </button>
            </div>
        </div>
    </div>

    <div v-if="records.length === 0" class="text-gray-500 italic pl-2">
        Aucun historique médical disponible.
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '@/stores/auth';

defineProps({
    records: { type: Array, default: () => [] }
});

defineEmits(['edit', 'prescribe']);

const authStore = useAuthStore();
const canManage = computed(() => authStore.hasRole(['medecin', 'nurse']));

// Pas de prefixe "Dr." fige : ce champ est aussi rempli par des
// infirmieres (created_by_name), afficher "Dr." devant leur nom etait
// trompeur. On ne connait pas ici le role exact de l'auteur (pas
// disponible sur ce record), donc on affiche juste le nom, sans titre
// invente.
const authorLabel = (record) => record.created_by_name || 'Inconnu';

const formatDate = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('fr-FR', {
        year: 'numeric', month: 'long', day: 'numeric'
    });
};
</script>