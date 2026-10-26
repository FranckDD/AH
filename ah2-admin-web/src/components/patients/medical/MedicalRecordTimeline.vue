<template>
  <div class="relative pl-4 border-l-2 border-tone-neutral-border space-y-8">

    <div v-for="record in records" :key="record.record_id" class="relative">
        <div class="absolute left-[-21px] top-1 h-4 w-4 rounded-full bg-brand-600 border-2 border-white ring-2 ring-brand-100"></div>

        <div class="bg-white p-4 rounded-card border border-tone-neutral-border shadow-card">
            <div class="flex justify-between items-start gap-3 mb-2">
                <div class="min-w-0">
                    <h4 class="font-bold text-ink text-lg">{{ record.diagnosis || t('screens.record.default_diagnosis') }}</h4>
                    <p class="text-base text-ink-muted">
                        {{ formatDate(record.consultation_date) }} - {{ authorLabel(record) }}
                    </p>
                    <p v-if="record.needs_doctor_review" class="mt-1">
                        <StatusBadge
                            :tone="record.reviewed_at ? 'success' : 'warning'"
                            :label="record.reviewed_at ? t('screens.record.taken_over') : (record.assigned_doctor_id ? t('screens.record.to_forward_assigned') : t('screens.record.to_forward_queue'))"
                        />
                    </p>
                    <p v-if="!editable(record)" class="mt-1">
                        <StatusBadge tone="neutral" :label="t('medical.readonly.badge')" />
                    </p>
                </div>
                <span class="shrink-0 px-2 py-1 text-sm font-bold rounded-control bg-tone-neutral-bg text-tone-neutral-text">
                    {{ record.motif_code }}
                </span>
            </div>

            <div class="grid grid-cols-3 gap-2 mb-3 bg-tone-neutral-bg p-2 rounded-control text-sm">
                <div class="text-center">
                    <span class="block text-ink-muted">{{ t('screens.record.bp') }}</span>
                    <span class="font-bold text-ink">{{ record.bp || '-' }}</span>
                </div>
                <div class="text-center border-l border-tone-neutral-border">
                    <span class="block text-ink-muted">{{ t('screens.record.weight') }}</span>
                    <span class="font-bold text-ink">{{ record.weight ? record.weight + ' kg' : '-' }}</span>
                </div>
                <div class="text-center border-l border-tone-neutral-border">
                    <span class="block text-ink-muted">{{ t('screens.record.temp') }}</span>
                    <span class="font-bold text-ink">{{ record.temperature ? record.temperature + '°' : '-' }}</span>
                </div>
            </div>

            <p class="text-ink text-base whitespace-pre-line">{{ record.notes || record.symptoms || t('screens.record.no_note') }}</p>

            <div v-if="record.allergies || record.medical_history" class="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-base">
                <div v-if="record.allergies">
                    <p class="text-sm font-bold text-ink-muted uppercase">{{ t('screens.record.allergies') }}</p>
                    <p class="text-ink">{{ record.allergies }}</p>
                </div>
                <div v-if="record.medical_history">
                    <p class="text-sm font-bold text-ink-muted uppercase">{{ t('screens.record.history') }}</p>
                    <p class="text-ink">{{ record.medical_history }}</p>
                </div>
            </div>

            <div v-if="record.treatment" class="mt-3 pt-3 border-t border-tone-neutral-border">
                <p class="text-sm font-bold text-ink-muted uppercase">{{ t('screens.record.treatment') }}</p>
                <p class="text-base text-ink">{{ record.treatment }}</p>
            </div>

            <div v-if="canManage && editable(record)" class="mt-3 pt-3 border-t border-tone-neutral-border flex flex-col gap-2 sm:flex-row">
                <AppButton variant="secondary" @click="$emit('edit', record)">
                    {{ t('screens.record.edit') }}
                </AppButton>
                <AppButton variant="pharma" @click="$emit('prescribe', record)">
                    {{ t('screens.record.prescribe') }}
                </AppButton>
            </div>
        </div>
    </div>

    <div v-if="records.length === 0" class="text-ink-muted text-base pl-2">
        {{ t('screens.record.none') }}
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { formatDateDMY } from '@/utils/localDate';
import { useAuthStore } from '@/stores/auth';
import { isRecordEditable } from '@/utils/consultationLock';
import { AppButton, StatusBadge } from '@/components/ui';

const props = defineProps({
    records: { type: Array, default: () => [] }
});

defineEmits(['edit', 'prescribe']);

const authStore = useAuthStore();
const canManage = computed(() => authStore.hasRole(['medecin', 'nurse']));
const { t } = useI18n();

// Consultation passee = lecture seule : flag serveur is_editable, ou calcul
// local (lignes PowerSync hors ligne) sur l'historique complet du patient.
const editable = (record) => isRecordEditable(record, props.records, { samePatient: true });

// Pas de prefixe "Dr." fige : ce champ est aussi rempli par des
// infirmieres (created_by_name), afficher "Dr." devant leur nom etait
// trompeur. On ne connait pas ici le role exact de l'auteur (pas
// disponible sur ce record), donc on affiche juste le nom, sans titre
// invente.
const authorLabel = (record) => record.created_by_name || t('screens.record.unknown_author');

const formatDate = formatDateDMY;
</script>
