<script setup>
import { computed } from 'vue';
import { buttonClasses } from '@/utils/ui';

const props = defineProps({
    variant: { type: String, default: 'primary' },
    size: { type: String, default: 'md' },
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    type: { type: String, default: 'button' },
    icon: { type: [Object, Function], default: null },
});

const classes = computed(() => buttonClasses(props.variant, props.size));
// Désactivé pendant le chargement : pas de double soumission.
const isDisabled = computed(() => props.disabled || props.loading);
</script>

<template>
    <button :type="type" :class="classes" :disabled="isDisabled" :aria-busy="loading || undefined">
        <svg v-if="loading" class="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
            <path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4" stroke-linecap="round" />
        </svg>
        <component :is="icon" v-else-if="icon" class="h-5 w-5 shrink-0" aria-hidden="true" />
        <slot />
    </button>
</template>
