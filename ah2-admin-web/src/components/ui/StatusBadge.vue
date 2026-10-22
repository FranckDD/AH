<script setup>
import { computed } from 'vue';
import { toneClasses } from '@/design/tones';

const props = defineProps({
    tone: { type: String, default: 'neutral' },
    label: { type: String, required: true },
});

const classes = computed(() => toneClasses(props.tone));
</script>

<template>
    <!-- Le point + le texte portent l'état : jamais la couleur seule -->
    <span :class="['inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-sm font-medium', classes]">
        <span class="h-2 w-2 shrink-0 rounded-full bg-current" aria-hidden="true"></span>
        {{ label }}
    </span>
</template>
