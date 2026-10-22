<script setup>
import { ref, useId } from 'vue';
import { ChevronDownIcon } from '@heroicons/vue/20/solid';

const props = defineProps({
    title: { type: String, required: true },
    subtitle: { type: String, default: '' },
    collapsible: { type: Boolean, default: false },
    defaultOpen: { type: Boolean, default: true },
});

const open = ref(props.collapsible ? props.defaultOpen : true);
const bodyId = `form-section-${useId()}`;
</script>

<template>
    <fieldset class="rounded-card border border-tone-neutral-border bg-white">
        <legend class="sr-only">{{ title }}</legend>
        <component
            :is="collapsible ? 'button' : 'div'"
            :type="collapsible ? 'button' : undefined"
            :aria-expanded="collapsible ? open : undefined"
            :aria-controls="collapsible ? bodyId : undefined"
            :class="['flex w-full min-h-11 items-center justify-between gap-3 px-4 py-3 text-left md:px-5', collapsible ? 'cursor-pointer rounded-card focus-visible:outline-2 focus-visible:outline-brand-600' : '']"
            @click="collapsible && (open = !open)"
        >
            <span class="min-w-0">
                <span class="block text-lg font-semibold text-ink">{{ title }}</span>
                <span v-if="subtitle" class="block text-sm text-ink-muted">{{ subtitle }}</span>
            </span>
            <ChevronDownIcon v-if="collapsible" :class="['h-5 w-5 shrink-0 text-ink-muted transition-transform', open ? 'rotate-180' : '']" aria-hidden="true" />
        </component>
        <div v-show="open" :id="bodyId" class="grid gap-4 border-t border-tone-neutral-border px-4 py-4 md:grid-cols-2 md:px-5">
            <slot />
        </div>
    </fieldset>
</template>
