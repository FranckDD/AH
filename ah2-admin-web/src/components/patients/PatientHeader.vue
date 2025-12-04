<template>
  <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
    
    <div class="flex items-center gap-4">
        <div class="h-16 w-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-2xl font-bold border-2 border-white shadow-sm">
            {{ getInitials(patient.full_name) }}
        </div>
        <div>
            <h2 class="text-2xl font-bold text-gray-900">{{ patient.full_name }}</h2>
            <div class="flex items-center text-gray-500 text-sm mt-1 space-x-3">
                <span class="font-mono bg-gray-100 px-2 py-0.5 rounded text-gray-700">{{ patient.code }}</span>
                <span>{{ patient.age }} ans</span>
                <span>{{ patient.gender === 'M' ? 'Homme' : 'Femme' }}</span>
            </div>
        </div>
    </div>

    <div class="flex flex-wrap gap-2">
        <span v-if="patient.flags?.is_clinical" class="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">
            CLINIQUE
        </span>
        <span v-if="patient.flags?.is_toxicology" class="px-3 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-200">
            TOXICOLOGIE
        </span>
        <span v-if="patient.flags?.is_spiritual" class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
            SPIRITUEL
        </span>
    </div>

    <button @click="$emit('back')" class="text-gray-400 hover:text-gray-600">
        Fermer ✕
    </button>
  </div>
</template>

<script setup>
defineProps({
    patient: { type: Object, required: true }
});
defineEmits(['back']);

const getInitials = (name) => {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
};
</script>