<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm" @click.self="$emit('close')">
    
    <div class="relative mx-auto w-full max-w-lg bg-white shadow-xl rounded-2xl border border-gray-200 p-6 transform transition-all">
        
        <button @click="$emit('close')" class="absolute top-4 right-4 text-gray-400 hover:text-gray-700 transition bg-white rounded-full p-1 hover:bg-gray-100">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>

        <slot></slot>
    </div>
  </div>
</template>

<script setup>
// Ce composant émet un événement pour dire au parent de se fermer
defineEmits(['close']);
</script>