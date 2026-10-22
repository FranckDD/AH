<template>
  <div class="bg-white p-4 md:p-6 rounded-card shadow-card border border-tone-neutral-border flex flex-col md:flex-row justify-between items-start md:items-center gap-4">

    <div class="flex items-center gap-4 min-w-0">
        <div class="h-16 w-16 shrink-0 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-2xl font-bold border-2 border-white shadow-card" aria-hidden="true">
            {{ getInitials(patient.full_name) }}
        </div>
        <div class="min-w-0">
            <h2 class="text-2xl font-bold text-ink">{{ patient.full_name }}</h2>
            <div class="flex flex-wrap items-center text-ink-muted text-base mt-1 gap-x-3 gap-y-1">
                <span class="font-mono bg-tone-neutral-bg px-2 py-0.5 rounded-control text-tone-neutral-text">{{ patient.code }}</span>
                <span>{{ patient.age }} ans</span>
                <span>{{ patient.gender === 'M' ? 'Homme' : 'Femme' }}</span>
            </div>
        </div>
    </div>

    <div class="flex flex-wrap gap-2">
        <StatusBadge v-if="patient.flags?.is_clinical" tone="info" label="CLINIQUE" />
        <StatusBadge v-if="patient.flags?.is_toxicology" tone="warning" label="TOXICOLOGIE" />
        <StatusBadge v-if="patient.flags?.is_spiritual" tone="neutral" label="SPIRITUEL" />
        <StatusBadge v-if="patient.is_staff" tone="success" :label="t('staffDiscount.badge')" />
    </div>

    <AppButton variant="ghost" :icon="XMarkIcon" @click="$emit('back')">
        Fermer
    </AppButton>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import { AppButton, StatusBadge } from '@/components/ui';

defineProps({
    patient: { type: Object, required: true }
});
defineEmits(['back']);
const { t } = useI18n();

const getInitials = (name) => {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
};
</script>
