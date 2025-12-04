<template>
  <div class="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex items-start justify-between hover:shadow-md transition-shadow duration-200">
    
    <div>
      <p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">
        {{ label }}
      </p>
      
      <div class="flex items-baseline">
        <h3 class="text-2xl font-extrabold text-gray-900">
          {{ value || '-' }}
        </h3>
        <span v-if="unit && value" class="ml-1 text-sm font-medium text-gray-500">
          {{ unit }}
        </span>
      </div>

      <p v-if="date" class="text-[10px] text-gray-400 mt-1 font-medium">
        {{ date }}
      </p>
    </div>

    <div :class="`p-3 rounded-xl ${colorClass} bg-opacity-10 flex items-center justify-center`">
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
  colorClass: { type: String, default: 'bg-emerald-500' },
  iconColor: { type: String, default: 'text-emerald-600' }
});
</script>