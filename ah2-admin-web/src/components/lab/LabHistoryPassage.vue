<script setup>
// Une ligne de l'historique = un passage patient (un dossier). Lecture en un coup d'oeil : heure, patient, examens,
// etat global et anomalies ; les examens se deplient. Les anomalies sont dites par une icone ET un nombre.
import { computed, ref, useId } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { ChevronDownIcon, ExclamationTriangleIcon, EyeIcon, PrinterIcon } from '@heroicons/vue/24/outline';
import { AppButton, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { hasPrintable, examStatusMeta } from '@/utils/labPassages';

const props = defineProps({
    passage: { type: Object, required: true },
});
defineEmits(['view', 'pdf', 'pdf-batch']);

const { t } = useI18n();
const open = ref(false);
const panelId = `lab-passage-${useId()}`;

const isMulti = computed(() => props.passage.exams.length > 1);
const time = computed(() => (props.passage.test_date ? dayjs(props.passage.test_date).format('HH:mm') : '-'));
const preview = computed(() => {
    const names = props.passage.exams.map((e) => e.examen_nom);
    return { shown: names.slice(0, 2).join(', '), more: Math.max(0, names.length - 2) };
});
const canPrintBatch = computed(() => isMulti.value && !!props.passage.batch_id && hasPrintable(props.passage));

// Etat d'un examen : meme mot, meme icone et meme couleur que la paillasse (termine = vert).
const statusMeta = (status) => examStatusMeta(status);
</script>

<template>
    <article class="rounded-card border border-tone-neutral-border bg-white shadow-card" :class="passage.abnormalCount > 0 ? 'border-l-4 border-l-tone-danger-solid' : ''">
        <div class="grid gap-3 p-3 lg:grid-cols-[4rem_minmax(0,1.2fr)_minmax(0,1.5fr)_minmax(0,1fr)_auto] lg:items-center">
            <p class="text-sm font-semibold text-ink-muted">{{ time }}</p>

            <div class="min-w-0">
                <h3 class="break-words text-sm font-semibold text-ink">{{ passage.patient_name }}</h3>
                <p class="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
                    {{ t('labScreens.sex_age', { sex: passage.patient_sexe, age: passage.patient_age, years: t('lab.result_modal.years') }) }}
                    <StatusBadge v-if="passage.is_external" tone="warning" :label="t('lab.result_modal.external')" />
                </p>
            </div>

            <div class="min-w-0 text-sm">
                <template v-if="isMulti">
                    <p class="font-semibold text-ink">{{ t('labScreens.exams_count', { n: passage.exams.length }) }}</p>
                    <p class="break-words text-ink-muted">{{ preview.shown }}<span v-if="preview.more > 0">{{ t('labScreens.exams_preview_more', { n: preview.more }) }}</span></p>
                </template>
                <template v-else>
                    <p class="break-words font-semibold text-ink">{{ passage.exams[0].examen_nom }}</p>
                    <p class="text-ink-muted">#{{ passage.exams[0].result_id }}<span v-if="passage.exams[0].code">, {{ passage.exams[0].code }}</span></p>
                </template>
            </div>

            <div class="flex flex-wrap items-center gap-2">
                <StatusBadge :tone="passage.status.tone" :label="t(passage.status.labelKey, passage.status.params)" />
                <span v-if="passage.abnormalCount > 0" class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-semibold" :class="toneClasses('danger')">
                    <ExclamationTriangleIcon class="h-4 w-4 shrink-0" aria-hidden="true" />
                    {{ t('labScreens.abnormal_count', passage.abnormalCount) }}
                </span>
                <StatusBadge v-if="passage.exams.some((e) => e.corrected)" tone="info" :label="t('lab.technician.corrected_badge')" />
            </div>

            <div class="flex flex-wrap gap-2 lg:justify-end">
                <template v-if="isMulti">
                    <AppButton variant="secondary" size="sm" :aria-expanded="open" :aria-controls="panelId" @click="open = !open">
                        {{ open ? t('labScreens.hide_exams') : t('labScreens.show_exams') }}
                        <ChevronDownIcon class="h-5 w-5 shrink-0 transition-transform" :class="open ? 'rotate-180' : ''" aria-hidden="true" />
                    </AppButton>
                    <AppButton v-if="canPrintBatch" variant="info" size="sm" :icon="PrinterIcon" @click="$emit('pdf-batch', passage)">{{ t('labScreens.pdf_batch') }}</AppButton>
                </template>
                <template v-else>
                    <AppButton variant="secondary" size="sm" :icon="EyeIcon" @click="$emit('view', passage.exams[0])">{{ t('lab.history_view.view_details') }}</AppButton>
                    <AppButton v-if="passage.exams[0].status !== 'pending'" variant="secondary" size="sm" :icon="PrinterIcon" @click="$emit('pdf', passage.exams[0])">{{ t('lab.history_view.download_pdf') }}</AppButton>
                </template>
            </div>
        </div>

        <ul v-if="isMulti && open" :id="panelId" class="divide-y divide-tone-neutral-border border-t border-tone-neutral-border bg-tone-neutral-bg">
            <li v-for="res in passage.exams" :key="res.result_id" class="grid gap-2 p-3 sm:grid-cols-[1fr_auto] sm:items-center">
                <div class="min-w-0">
                    <p class="flex flex-wrap items-center gap-2 text-sm font-semibold text-ink">
                        {{ res.examen_nom }}
                        <StatusBadge :tone="statusMeta(res.status).tone" :label="t(statusMeta(res.status).labelKey)" />
                        <span v-if="res.nb_anormaux > 0" class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-semibold" :class="toneClasses('danger')">
                            <ExclamationTriangleIcon class="h-4 w-4 shrink-0" aria-hidden="true" />
                            {{ t('labScreens.abnormal_count', res.nb_anormaux) }}
                        </span>
                        <StatusBadge v-if="res.corrected" tone="info" :label="t('lab.technician.corrected_badge')" />
                    </p>
                    <p class="text-sm text-ink-muted">#{{ res.result_id }}<span v-if="res.code">, {{ res.code }}</span></p>
                </div>
                <div class="flex flex-wrap gap-2">
                    <AppButton variant="secondary" size="sm" :icon="EyeIcon" @click="$emit('view', res)">{{ t('lab.history_view.view_details') }}</AppButton>
                    <AppButton v-if="res.status !== 'pending'" variant="secondary" size="sm" :icon="PrinterIcon" @click="$emit('pdf', res)">{{ t('lab.history_view.download_pdf') }}</AppButton>
                </div>
            </li>
        </ul>
    </article>
</template>
