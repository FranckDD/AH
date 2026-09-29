import { defineStore } from 'pinia';

let nextId = 1;
const AUTO_DISMISS_MS = 6000;

export const useToastStore = defineStore('toast', {
  state: () => ({
    toasts: [],
  }),
  actions: {
    push(message, type = 'error') {
      const id = nextId++;
      this.toasts.push({ id, message, type });
      setTimeout(() => this.dismiss(id), AUTO_DISMISS_MS);
    },
    dismiss(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
  },
});
