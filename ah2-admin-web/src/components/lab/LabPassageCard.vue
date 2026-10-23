<script setup>
// Carte d'un passage patient a la paillasse : le patient UNE seule fois, puis tous ses examens en pastilles.
// Chaque pastille dit son etat par une icone ET un mot ; cliquer une pastille ouvre cet examen.
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ClockIcon, BeakerIcon, CheckCircleIcon } from '@heroicons/vue/24/outline';
import { StatusBadge } from '@/components/ui';
import { examStatusMeta } from '@/utils/labPassages';

const props = defineProps({
    passage: { type: Object, required: true },
    activeId: { type: Number, default: null },
});
defineEmits(['open']);

const { t } = useI18n();
const ICONS = { clock: ClockIcon, beaker: BeakerIcon, check: CheckCircleIcon };
const meta = (status) => examStatusMeta(status);
const isActivePassage = computed(() => props.passage.exams.some((e) => e.result_id === props.activeId));
const initial = computed(() => (props.passage.patient_name || '?').trim().charAt(0).toUpperCase());

// Couleur de la pastille choisie ; l'etat reste dit par l'icone et le mot.
const PILL_TONE = {
    warning: 'border-tone-warning-border bg-tone-warning-bg text-tone-warning-text',
    info: 'border-tone-info-border bg-tone-info-bg text-tone-info-text',
    success: 'border-tone-success-border bg-tone-success-bg text-tone-success-text',
};
</script>

<template>
    <article :class="isActivePassage ? 'border-brand-600 bg-brand-50' : 'border-tone-neutral-border bg-white'" class="grid gap-3 rounded-card border-2 p-3">
        <header class="flex items-start gap-3">
            <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-100 text-lg font-bold text-brand-800" aria-hidden="true">{{ initial }}</span>
            <div class="min-w-0 flex-1">
                <h3 class="break-words text-sm font-semibold text-ink">{{ passage.patient_name }}</h3>
                <p class="text-sm text-ink-muted">{{ t('labScreens.sex_age', { sex: passage.patient_sexe, age: passage.patient_age, years: t('lab.result_modal.years') }) }}</p>
            </div>
            <StatusBadge v-if="passage.is_external" tone="warning" :label="t('labScreens.external_badge')" />
        </header>

        <div v-if="passage.exams.length > 1">
            <p class="mb-1 text-sm text-ink-muted">{{ t('labScreens.passage_progress', { done: passage.progress.done, total: passage.progress.total }) }}</p>
            <div class="h-2 overflow-hidden rounded-full bg-tone-neutral-bg" role="progressbar" :aria-valuenow="passage.progress.done" aria-valuemin="0" :aria-valuemax="passage.progress.total"
                 :aria-label="t('labScreens.passage_progress', { done: passage.progress.done, total: passage.progress.total })">
                <div class="h-2 rounded-full bg-brand-600 transition-all duration-500" :style="{ width: passage.progress.pct + '%' }"></div>
            </div>
        </div>

        <ul class="flex flex-wrap gap-2" :aria-label="t('labScreens.passage_exams')">
            <li v-for="e in passage.exams" :key="e.result_id">
                <button type="button" :aria-pressed="activeId === e.result_id" @click="$emit('open', e.result_id)"
                        :class="[PILL_TONE[meta(e.status).tone], activeId === e.result_id ? 'ring-2 ring-brand-600 ring-offset-1' : '']"
                        class="inline-flex min-h-11 items-center gap-2 rounded-full border-2 px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600">
                    <component :is="ICONS[meta(e.status).icon]" class="h-5 w-5 shrink-0" aria-hidden="true" />
                    <span class="font-semibold">{{ e.examen_nom || t('lab.technician.exam') }}</span>
                    <span>{{ t(meta(e.status).labelKey) }}</span>
                </button>
            </li>
        </ul>
    </article>
</template>
