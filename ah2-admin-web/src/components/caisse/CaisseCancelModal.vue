<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-xs">
    <div class="relative mx-auto w-full max-w-md bg-white shadow-xl rounded-2xl border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-100 bg-red-600 rounded-t-2xl flex justify-between items-center">
        <h3 class="text-lg font-bold text-white flex items-center">
          <ExclamationTriangleIcon class="h-6 w-6 mr-2" />
          {{ t('caisse.cancel_modal.title') }}
        </h3>
        <button @click="$emit('close')" class="text-red-100 hover:text-white transition">
          <span class="text-2xl font-bold">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <p class="text-sm text-gray-600">{{ label }}</p>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            {{ t('caisse.cancel_modal.justification') }} <span class="text-red-500">*</span>
          </label>
          <textarea
            v-model="justification"
            rows="3"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500"
            :placeholder="t('caisse.cancel_modal.justification_placeholder')"
          ></textarea>
        </div>

        <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">
          {{ errorMessage }}
        </div>

        <div class="flex justify-end space-x-3 pt-2">
          <button type="button" @click="$emit('close')" :disabled="isSaving"
                  class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition disabled:opacity-50">
            {{ t('caisse.cancel_modal.cancel') }}
          </button>
          <button type="submit" :disabled="isSaving || !justification.trim()"
                  class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium shadow-xs transition disabled:opacity-50">
            {{ isSaving ? t('caisse.cancel_modal.saving') : t('caisse.cancel_modal.confirm') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline';

const props = defineProps({
  label: { type: String, default: '' },
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'confirm']);

const { t } = useI18n();
const justification = ref('');

const handleSubmit = () => {
  if (!justification.value.trim()) return;
  emit('confirm', justification.value.trim());
};
</script>
