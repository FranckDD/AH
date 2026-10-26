<template>
  <div class="fixed top-20 right-4 z-100 flex flex-col items-end gap-2 pointer-events-none" role="status" aria-live="polite">
    <TransitionGroup name="toast-slide">
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        class="pointer-events-auto max-w-sm w-full rounded-xl shadow-lg border px-4 py-3 flex items-start gap-3"
        :class="toneClasses(toast.type === 'success' ? 'success' : toast.type === 'error' ? 'danger' : 'warning')"
      >
        <CheckCircleIcon v-if="toast.type === 'success'" class="h-5 w-5 shrink-0 mt-0.5" aria-hidden="true" />
        <ExclamationTriangleIcon v-else class="h-5 w-5 shrink-0 mt-0.5" aria-hidden="true" />
        <p class="text-sm flex-1">{{ toast.message }}</p>
        <button
          @click="toastStore.dismiss(toast.id)"
          :aria-label="$t('ui.close')"
          class="shrink-0 text-current opacity-60 hover:opacity-100 transition"
        >
          <XMarkIcon class="h-4 w-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToastStore } from '@/stores/toastStore';
import { CheckCircleIcon, ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline';
import { toneClasses } from '@/design/tones';

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
