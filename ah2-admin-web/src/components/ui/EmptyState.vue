<script setup>
import { InboxIcon } from '@heroicons/vue/24/outline';

defineProps({
    title: { type: String, required: true },
    message: { type: String, default: '' },
    icon: { type: [Object, Function], default: null },
});
</script>

<template>
    <div class="flex flex-col items-center gap-2 px-4 py-10 text-center">
        <component :is="icon || InboxIcon" class="h-10 w-10 text-ink-muted" aria-hidden="true" />
        <p class="text-lg font-semibold text-ink">{{ title }}</p>
        <p v-if="message" class="max-w-md text-base text-ink-muted">{{ message }}</p>
        <div v-if="$slots.action" class="mt-2"><slot name="action" /></div>
    </div>
</template>
