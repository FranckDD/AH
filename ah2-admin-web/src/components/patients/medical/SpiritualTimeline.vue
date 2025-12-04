<template>
  <div class="relative pl-4 border-l-2 border-amber-200 space-y-6">
    
    <div v-for="rec in records" :key="rec.consultation_id || rec.id" class="relative">
        <div class="absolute -left-[21px] top-1 h-4 w-4 rounded-full bg-amber-500 border-2 border-white ring-2 ring-amber-100"></div>
        
        <div class="bg-white p-4 rounded-xl border border-amber-100 shadow-sm hover:shadow-md transition">
            
            <div class="flex justify-between items-start mb-2">
                <div>
                    <h4 class="font-bold text-gray-900 text-lg">
                        {{ rec.type || rec.type_consultation }}
                    </h4>
                    <p class="text-sm text-gray-500">
                        {{ formatDate(rec.date || rec.consultation_date) }} • 
                        {{ rec.intervenant || rec.created_by_name || 'Conseiller' }}
                    </p>
                </div>
                
                <span v-if="rec.type_consultation === 'FamilyRestoration'" class="px-2 py-1 text-xs font-bold rounded bg-purple-100 text-purple-700 border border-purple-200">
                    Famille
                </span>
            </div>

            <div v-if="rec.psaume" class="mb-3 inline-flex items-center px-3 py-1 rounded-full bg-amber-50 text-amber-800 text-sm font-medium border border-amber-200">
                📖 Psaume : {{ rec.psaume }}
            </div>

            <p v-if="rec.notes" class="text-gray-700 text-sm whitespace-pre-line mb-3 bg-gray-50 p-2 rounded">
                {{ rec.notes }}
            </p>

            <div v-if="rec.type_consultation === 'FamilyRestoration'" class="grid grid-cols-2 gap-2 mb-3 text-xs bg-purple-50 p-2 rounded border border-purple-100">
                <div>
                    <span class="text-gray-500 block">Montant payé:</span>
                    <span class="font-bold text-gray-800">{{ rec.fr_amount_paid }} FCFA</span>
                </div>
                <div>
                    <span class="text-gray-500 block">RDV Prévu:</span>
                    <span class="font-bold text-gray-800">{{ formatDate(rec.fr_appointment_at) }}</span>
                </div>
            </div>

            <div v-if="(rec.presc_generic && rec.presc_generic.length) || (rec.presc_med_spirituel && rec.presc_med_spirituel.length)" class="mt-3 pt-3 border-t border-gray-100">
                <p class="text-xs font-bold text-gray-500 uppercase mb-2">Prescriptions Spirituelles</p>
                <div class="flex flex-wrap gap-2">
                    <span v-for="p in rec.presc_generic" :key="p" class="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs border border-blue-100">
                        {{ p }}
                    </span>
                    <span v-for="p in rec.presc_med_spirituel" :key="p" class="px-2 py-1 bg-emerald-50 text-emerald-700 rounded text-xs border border-emerald-100">
                        {{ p }}
                    </span>
                </div>
            </div>

        </div>
    </div>

    <div v-if="records.length === 0" class="text-gray-500 italic pl-2">
        Aucun historique spirituel.
    </div>

  </div>
</template>

<script setup>
defineProps({
    records: { type: Array, default: () => [] }
});

const formatDate = (dateString) => {
    if (!dateString) return '-';
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString; // Retourne la string brute si parsing échoue
    return d.toLocaleDateString('fr-FR', {
        day: 'numeric', month: 'long', year: 'numeric'
    });
};
</script>