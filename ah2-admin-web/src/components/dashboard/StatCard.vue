<template>
  <div class="relative bg-white overflow-hidden rounded-2xl shadow-sm border border-gray-100 group hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1">
    
    <div class="p-6">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-medium text-gray-500 mb-1 uppercase tracking-wider">
            {{ title }}
          </p>
          <div class="flex items-baseline">
            <h3 class="text-2xl font-extrabold text-gray-900">
              {{ value }}
            </h3>
          </div>
        </div>

        <div :class="`p-3 rounded-xl ${colorClass} bg-opacity-10 text-white shadow-inner`">
          <component :is="icon" :class="`h-8 w-8 ${iconColor}`" aria-hidden="true" />
        </div>
      </div>
    </div>

    <div v-if="trend" class="bg-gray-50 px-6 py-2 border-t border-gray-100 flex items-center">
      <span :class="trendIsPositive ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100'" class="px-2 py-0.5 rounded text-xs font-bold mr-2">
        {{ trend }}
      </span>
      <span class="text-xs text-gray-400 font-medium">vs mois dernier</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  value: { type: String, required: true },
  icon: { type: [Object, Function], required: true },
  colorClass: { type: String, default: 'bg-blue-500' }, // Fond de l'icône
  iconColor: { type: String, default: 'text-blue-600' }, // Couleur de l'icône elle-même
  trend: { type: String, default: null },
  trendIsPositive: { type: Boolean, default: true }
});

</script>