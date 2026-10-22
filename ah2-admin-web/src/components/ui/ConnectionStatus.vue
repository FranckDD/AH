<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
    CheckCircleIcon,
    ArrowPathIcon,
    ArrowUpTrayIcon,
    SignalSlashIcon,
    ExclamationTriangleIcon,
} from '@heroicons/vue/20/solid';
import { toneClasses } from '@/design/tones';
import { useConnectionStatus } from '@/composables/useConnectionStatus';
import { connectionTone, connectionLabelKey } from '@/utils/connectionStatus';

const { t } = useI18n();
const { state, pending } = useConnectionStatus();

const ICONS = {
    online: CheckCircleIcon,
    syncing: ArrowPathIcon,
    pending: ArrowUpTrayIcon,
    offline: SignalSlashIcon,
    error: ExclamationTriangleIcon,
};

const icon = computed(() => ICONS[state.value] ?? SignalSlashIcon);
const classes = computed(() => toneClasses(connectionTone(state.value)));
const label = computed(() =>
    state.value === 'pending'
        ? t(connectionLabelKey('pending'), { n: pending.value }, pending.value)
        : t(connectionLabelKey(state.value))
);
// Hors ligne : on rassure sur les saisies (détail visible à partir de lg).
const detail = computed(() =>
    state.value === 'offline' ? t('medicalShell.connection.offlineDetail') : ''
);
</script>

<template>
    <!-- Icône + texte + couleur : l'état n'est jamais porté par la couleur seule -->
    <div
        role="status"
        :aria-label="t('medicalShell.connection.label')"
        :title="detail ? `${label} ${detail}` : label"
        :class="['inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium', classes]"
    >
        <component :is="icon" :class="['h-4 w-4 shrink-0', state === 'syncing' ? 'animate-spin' : '']" aria-hidden="true" />
        <span class="whitespace-nowrap">{{ label }}</span>
        <span v-if="detail" class="hidden whitespace-nowrap lg:inline">{{ detail }}</span>
    </div>
</template>
