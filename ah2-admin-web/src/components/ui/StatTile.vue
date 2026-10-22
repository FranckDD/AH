<script setup>
// Tuile de statistique : titre, valeur bien lisible, note facultative. La tonalite ne colore que l'icone
// (jamais la valeur) ; le sens doit rester ecrit dans le titre ou la note.
import { computed } from 'vue';
import { toneClasses } from '@/design/tones';

const props = defineProps({
    title: { type: String, required: true },
    value: { type: [String, Number], required: true },
    note: { type: String, default: '' },
    icon: { type: [Object, Function], default: null },
    tone: { type: String, default: 'neutral' },
});

const iconClasses = computed(() => toneClasses(props.tone));
</script>

<template>
    <div class="flex items-start justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
        <div class="min-w-0">
            <p class="text-sm font-medium text-ink-muted">{{ title }}</p>
            <p class="mt-1 break-words text-2xl font-bold text-ink">{{ value }}</p>
            <p v-if="note" class="mt-1 text-sm text-ink-muted">{{ note }}</p>
            <slot />
        </div>
        <span v-if="icon" :class="['flex h-11 w-11 shrink-0 items-center justify-center rounded-control border', iconClasses]">
            <component :is="icon" class="h-6 w-6" aria-hidden="true" />
        </span>
    </div>
</template>
