<!-- Encadre "Controle du jour" : les points a voir de la periode, en mots, avec la date de premiere apparition,
     les mentions "deja signale", "recalcule", "etat actuel" et un lien vers l'ecran concerne. -->
<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { AppButton, StatusBadge } from '@/components/ui';
import { useAuthStore } from '@/stores/auth';
import { controlState, formatLocalDate, linkAllowed } from '@/utils/reports';

const props = defineProps({
    control: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    error: { type: String, default: '' },
});
const emit = defineEmits(['retry']);
const { t, te, locale } = useI18n();
const router = useRouter();
const authStore = useAuthStore();
// Bouton Ouvrir seulement si la garde du routeur laisse passer cet utilisateur (ex. prix -> finance : admin seul).
function canOpen(item) {
    if (!item.link) return false;
    try { return linkAllowed(router.resolve(item.link), authStore.userRole); } catch { return false; }
}
const uncontrolled = computed(() => Number(props.control?.uncontrolled_days || 0));
const uncontrolledRange = computed(() => props.control?.uncontrolled_range || null);
const state = computed(() => controlState(props.control));
const items = computed(() => props.control?.items || []);
const kindLabel = (k) => (te(`reports.kinds.${k}`) ? t(`reports.kinds.${k}`) : k);
function open(item) {
    if (canOpen(item)) router.push(item.link);
}
</script>

<template>
    <section class="rounded-card border-2 border-brand-600 bg-white p-4 shadow-card md:p-5" aria-labelledby="control-title">
        <header class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 id="control-title" class="text-lg font-semibold text-ink">{{ t('reports.control.title') }}</h2>
            <StatusBadge v-if="!loading && !error" :tone="state === 'watch' ? 'warning' : 'success'"
                         :label="state === 'watch' ? t('reports.control.state_watch') : t('reports.control.state_nothing')" />
        </header>

        <p v-if="loading" role="status" class="text-base text-ink-muted">{{ t('reports.states.loading') }}</p>
        <div v-else-if="error" role="alert" class="flex flex-wrap items-center gap-3 text-base text-tone-danger-text">
            <span>{{ t('reports.states.error') }}</span>
            <AppButton variant="secondary" size="sm" @click="emit('retry')">{{ t('reports.states.retry') }}</AppButton>
        </div>
        <p v-else-if="!items.length" class="text-base text-ink">{{ t('reports.control.empty') }}</p>
        <ul v-else class="grid gap-2">
            <li v-for="item in items" :key="item.key"
                class="flex flex-col gap-2 rounded-control border border-tone-neutral-border p-3 sm:flex-row sm:items-center sm:justify-between">
                <div class="grid min-w-0 gap-1">
                    <p class="text-base font-medium text-ink">{{ item.label }}</p>
                    <div class="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
                        <StatusBadge tone="warning" :label="kindLabel(item.kind)" />
                        <span>{{ t('reports.control.first_seen', { date: formatLocalDate(item.first_seen, locale) }) }}</span>
                        <span v-if="item.already_notified_on">{{ t('reports.control.already_notified', { date: formatLocalDate(item.already_notified_on, locale) }) }}</span>
                        <StatusBadge v-if="item.recomputed" tone="neutral" :label="t('reports.control.recomputed')" />
                        <StatusBadge v-if="item.current_state" tone="info" :label="t('reports.control.current_state')" />
                    </div>
                </div>
                <AppButton v-if="canOpen(item)" variant="secondary" size="sm" @click="open(item)">{{ t('reports.control.open') }}</AppButton>
            </li>
        </ul>
        <p v-if="uncontrolled > 0" role="note" class="mt-3 rounded-control border border-tone-warning-border bg-tone-warning-bg p-3 text-base text-tone-warning-text">
            {{ uncontrolledRange?.from && uncontrolledRange?.to
                ? t('reports.control.uncontrolled_range', { n: uncontrolled, from: formatLocalDate(uncontrolledRange.from, locale), to: formatLocalDate(uncontrolledRange.to, locale) })
                : t('reports.control.uncontrolled_days', { n: uncontrolled }) }}
        </p>
        <p v-if="control?.recomputed?.length" class="mt-3 text-sm text-ink-muted">{{ t('reports.control.recomputed_days', { n: control.recomputed.length }) }}</p>
    </section>
</template>
