<template>
  <div class="relative pl-4 border-l-2 border-tone-neutral-border space-y-6">

    <div v-for="rec in records" :key="rec.consultation_id || rec.id" class="relative">
        <div class="absolute left-[-21px] top-1 h-4 w-4 rounded-full bg-brand-600 border-2 border-white ring-2 ring-brand-100"></div>

        <div class="bg-white p-4 rounded-card border border-tone-neutral-border shadow-card">

            <div class="flex justify-between items-start gap-3 mb-2">
                <div class="min-w-0">
                    <h4 class="font-bold text-ink text-lg">
                        {{ rec.type || rec.type_consultation }}
                    </h4>
                    <p class="text-base text-ink-muted">
                        {{ formatDate(rec.date || rec.consultation_date) }} •
                        {{ rec.intervenant || rec.created_by_name || 'Conseiller' }}
                    </p>
                </div>

                <StatusBadge v-if="rec.type_consultation === 'FamilyRestoration'" tone="neutral" label="Famille" />
            </div>

            <div v-if="rec.psaume" class="mb-3 inline-flex items-center px-3 py-1 rounded-full bg-tone-neutral-bg text-ink text-base font-medium border border-tone-neutral-border">
                Psaume : {{ rec.psaume }}
            </div>

            <p v-if="rec.notes" class="text-ink text-base whitespace-pre-line mb-3 bg-tone-neutral-bg p-2 rounded-control">
                {{ rec.notes }}
            </p>

            <div v-if="rec.type_consultation === 'FamilyRestoration'" class="grid grid-cols-2 gap-2 mb-3 text-base bg-tone-neutral-bg p-2 rounded-control border border-tone-neutral-border">
                <div>
                    <span class="text-ink-muted block">Montant payé:</span>
                    <span class="font-bold text-ink">{{ rec.fr_amount_paid }} FCFA</span>
                </div>
                <div>
                    <span class="text-ink-muted block">RDV Prévu:</span>
                    <span class="font-bold text-ink">{{ formatDate(rec.fr_appointment_at) }}</span>
                </div>
            </div>

            <div v-if="(rec.presc_generic && rec.presc_generic.length) || (rec.presc_med_spirituel && rec.presc_med_spirituel.length)" class="mt-3 pt-3 border-t border-tone-neutral-border">
                <p class="text-sm font-bold text-ink-muted uppercase mb-2">Prescriptions Spirituelles</p>
                <div class="flex flex-wrap gap-2">
                    <StatusBadge v-for="p in rec.presc_generic" :key="p" tone="info" :label="String(p)" />
                    <StatusBadge v-for="p in rec.presc_med_spirituel" :key="p" tone="success" :label="String(p)" />
                </div>
            </div>

        </div>
    </div>

    <div v-if="records.length === 0" class="text-ink-muted text-base pl-2">
        Aucun historique spirituel.
    </div>

  </div>
</template>

<script setup>
import { StatusBadge } from '@/components/ui';

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
