<script setup>
defineProps({
    title: { type: String, default: '' },
    subtitle: { type: String, default: '' },
});
</script>

<template>
    <section class="rounded-card border border-tone-neutral-border bg-white shadow-card">
        <header v-if="title || subtitle || $slots.actions" class="flex flex-wrap items-start justify-between gap-3 border-b border-tone-neutral-border px-4 py-3 md:px-5">
            <div class="min-w-0">
                <h2 v-if="title" class="text-lg font-semibold text-ink">{{ title }}</h2>
                <p v-if="subtitle" class="text-sm text-ink-muted">{{ subtitle }}</p>
            </div>
            <div v-if="$slots.actions" class="flex flex-wrap gap-2"><slot name="actions" /></div>
        </header>
        <div class="px-4 py-4 md:px-5"><slot /></div>
        <footer v-if="$slots.footer" class="border-t border-tone-neutral-border px-4 py-3 md:px-5"><slot name="footer" /></footer>
    </section>
</template>
