<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div v-for="presc in prescriptions" :key="presc.id" class="bg-white p-4 rounded-card border border-tone-neutral-border shadow-card flex flex-col justify-between">
        <div>
            <div class="flex justify-between items-start gap-2">
                <h4 class="font-bold text-ink text-lg">{{ presc.medication }}</h4>
                <StatusBadge :tone="presc.status === 'active' ? 'success' : 'neutral'" :label="String(presc.status)" />
            </div>
            <p class="text-base text-ink mt-1">
                <span class="font-medium">Posologie:</span> {{ presc.dosage }} - {{ presc.frequency }}
            </p>
            <p class="text-base text-ink">
                <span class="font-medium">Durée:</span> {{ presc.duration }}
            </p>
        </div>
        <div class="mt-4 pt-3 border-t border-tone-neutral-border flex justify-between gap-2 text-sm text-ink-muted">
            <span>Début: {{ presc.start_date }}</span>
            <span>Dr./Nurse {{ presc.prescribed_by_name || 'Inconnu' }}</span>
        </div>
    </div>

    <div v-if="prescriptions.length === 0" class="col-span-full text-center py-8 text-ink-muted text-base">
        Aucune prescription enregistrée.
    </div>
  </div>
</template>

<script setup>
import { StatusBadge } from '@/components/ui';

defineProps({
    prescriptions: { type: Array, default: () => [] }
});
</script>
