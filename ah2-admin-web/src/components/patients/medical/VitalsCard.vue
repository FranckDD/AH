<template>
  <div class="bg-white p-5 rounded-card shadow-card border border-tone-neutral-border flex items-start justify-between gap-3">

    <div>
      <p class="text-sm font-semibold text-ink-muted mb-1">
        {{ label }}
      </p>

      <div class="flex items-baseline">
        <h3 class="text-2xl font-extrabold text-ink">
          {{ value || '-' }}
        </h3>
        <span v-if="unit && value" class="ml-1 text-base font-medium text-ink-muted">
          {{ unit }}
        </span>
      </div>

      <p v-if="date" class="text-sm text-ink-muted mt-1">
        {{ date }}
      </p>
    </div>

    <div :class="`p-3 rounded-card ${colorClass} flex items-center justify-center`">
      <component
        :is="icon"
        :class="`h-6 w-6 ${iconColor}`"
        aria-hidden="true"
      />
    </div>

  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: null },
  unit: { type: String, default: '' }, // Ex: 'kg', 'mmHg', '°C'
  date: { type: String, default: null }, // Ex: 'Il y a 2 jours'
  icon: { type: [Object, Function], required: true }, // Support Heroicons v1 & v2
  colorClass: { type: String, default: 'bg-brand-100' },
  iconColor: { type: String, default: 'text-brand-700' }
});
</script>
