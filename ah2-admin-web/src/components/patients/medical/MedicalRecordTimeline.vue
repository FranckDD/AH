<template>
  <div class="relative pl-4 border-l-2 border-gray-200 space-y-8">
    
    <div v-for="record in records" :key="record.record_id" class="relative">
        <div class="absolute -left-[21px] top-1 h-4 w-4 rounded-full bg-emerald-500 border-2 border-white ring-2 ring-emerald-100"></div>
        
        <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition">
            <div class="flex justify-between items-start mb-2">
                <div>
                    <h4 class="font-bold text-gray-900 text-lg">{{ record.diagnosis || 'Consultation Générale' }}</h4>
                    <p class="text-sm text-gray-500">{{ formatDate(record.consultation_date) }} • Dr. {{ record.created_by_name || 'Inconnu' }}</p>
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
            
            <div v-if="record.treatment" class="mt-3 pt-3 border-t border-gray-100">
                <p class="text-xs font-bold text-gray-500 uppercase">Traitement prescrit</p>
                <p class="text-sm text-gray-800">{{ record.treatment }}</p>
            </div>
        </div>
    </div>

    <div v-if="records.length === 0" class="text-gray-500 italic pl-2">
        Aucun historique médical disponible.
    </div>

  </div>
</template>

<script setup>
defineProps({
    records: { type: Array, default: () => [] }
});

const formatDate = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('fr-FR', {
        year: 'numeric', month: 'long', day: 'numeric'
    });
};
</script>