<template>
  <div class="fixed top-20 right-4 z-[100] flex flex-col items-end gap-2 pointer-events-none">
    <TransitionGroup name="toast-slide">
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        class="pointer-events-auto max-w-sm w-full rounded-xl shadow-lg border px-4 py-3 flex items-start gap-3"
        :class="toast.type === 'error'
          ? 'bg-red-50 border-red-200 text-red-800'
          : 'bg-amber-50 border-amber-200 text-amber-800'"
      >
        <ExclamationTriangleIcon class="h-5 w-5 flex-shrink-0 mt-0.5" />
        <p class="text-sm flex-1">{{ toast.message }}</p>
        <button
          @click="toastStore.dismiss(toast.id)"
          class="flex-shrink-0 text-current opacity-60 hover:opacity-100 transition"
        >
          <XMarkIcon class="h-4 w-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToastStore } from '@/stores/toastStore';
import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline';

const toastStore = useToastStore();
</script>

<style scoped>
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.toast-slide-enter-from,
.toast-slide-leave-to {
  transform: translateX(120%);
  opacity: 0;
}
.toast-slide-leave-active {
  position: absolute;
}
</style>
