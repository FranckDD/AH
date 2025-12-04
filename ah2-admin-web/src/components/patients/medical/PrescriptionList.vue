<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div v-for="presc in prescriptions" :key="presc.id" class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between">
        <div>
            <div class="flex justify-between items-start">
                <h4 class="font-bold text-gray-900">{{ presc.medication }}</h4>
                <span :class="presc.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'" class="px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                    {{ presc.status }}
                </span>
            </div>
            <p class="text-sm text-gray-600 mt-1">
                <span class="font-medium">Posologie:</span> {{ presc.dosage }} - {{ presc.frequency }}
            </p>
            <p class="text-sm text-gray-600">
                <span class="font-medium">Durée:</span> {{ presc.duration }}
            </p>
        </div>
        <div class="mt-4 pt-3 border-t border-gray-50 flex justify-between text-xs text-gray-400">
            <span>Début: {{ presc.start_date }}</span>
            <span>Dr./Nurse {{ presc.prescribed_by_name || 'Inconnu' }}</span>
        </div>
    </div>
    
    <div v-if="prescriptions.length === 0" class="col-span-full text-center py-8 text-gray-500">
        Aucune prescription enregistrée.
    </div>
  </div>
</template>

<script setup>
defineProps({
    prescriptions: { type: Array, default: () => [] }
});
</script>