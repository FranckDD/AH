<script setup>
import { computed } from 'vue';
import { ExclamationCircleIcon } from '@heroicons/vue/20/solid';
import { describedBy } from '@/utils/ui';

const props = defineProps({
    id: { type: String, required: true },
    label: { type: String, required: true },
    required: { type: Boolean, default: false },
    help: { type: String, default: '' },
    error: { type: String, default: '' },
});

const described = computed(() => describedBy(props.id, { help: props.help, error: props.error }));
</script>

<template>
    <div class="flex flex-col gap-1.5">
        <label :for="id" class="text-base font-medium text-ink">
            {{ label }}
            <template v-if="required">
                <span class="text-tone-danger-text" aria-hidden="true"> *</span>
                <span class="sr-only"> ({{ $t('ui.required') }})</span>
            </template>
        </label>
        <!-- Le contrôle reçoit describedBy et invalid pour les poser sur l'input -->
        <slot :describedBy="described" :invalid="!!error" :id="id" />
        <p v-if="help" :id="`${id}-help`" class="text-sm text-ink-muted">{{ help }}</p>
        <p v-if="error" :id="`${id}-error`" role="alert" class="flex items-start gap-1.5 text-sm font-medium text-tone-danger-text">
            <ExclamationCircleIcon class="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            {{ error }}
        </p>
    </div>
</template>
