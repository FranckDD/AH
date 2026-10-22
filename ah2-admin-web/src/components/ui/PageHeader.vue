<script setup>
defineProps({
    title: { type: String, required: true },
    subtitle: { type: String, default: '' },
});
</script>

<template>
    <header class="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div class="min-w-0">
            <h1 class="text-2xl font-bold text-ink">{{ title }}</h1>
            <p v-if="subtitle" class="mt-1 text-base text-ink-muted">{{ subtitle }}</p>
        </div>
        <!-- Sous md les actions s'empilent en pleine largeur -->
        <div v-if="$slots.actions" class="flex flex-col gap-2 md:flex-row md:items-center [&>*]:w-full md:[&>*]:w-auto">
            <slot name="actions" />
        </div>
    </header>
</template>
