<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-md shadow-xl rounded-2xl bg-white">
      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">{{ t('retrait.modal.title') }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('retrait.modal.amount') }}</label>
          <div class="relative rounded-md shadow-xs">
            <input v-model.number="form.amount" type="number" min="1" step="0.01" required
                   class="block w-full pl-3 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 sm:text-sm"
                   placeholder="0" />
            <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <span class="text-gray-500 sm:text-sm">FCFA</span>
            </div>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('retrait.modal.category') }}</label>
          <select v-model="form.category" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm">
            <option value="">-- {{ t('retrait.modal.category') }} --</option>
            <option value="SUPPLIES">{{ t('finance.categories.supplies') }}</option>
            <option value="SALARY">{{ t('finance.categories.salary') }}</option>
            <option value="MAINTENANCE">{{ t('finance.categories.maintenance') }}</option>
            <option value="BILLS">{{ t('finance.categories.bills') }}</option>
            <option value="OTHER">{{ t('finance.categories.other') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.method') }}</label>
          <select v-model="form.paymentMethod" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm">
            <option value="Espèces">{{ t('finance.payment_methods.cash') }}</option>
            <option value="Mobile Money">{{ t('finance.payment_methods.mobile') }}</option>
            <option value="Virement">{{ t('finance.payment_methods.transfer') }}</option>
            <option value="Chèque">{{ t('finance.payment_methods.check') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('retrait.modal.justification') }}</label>
          <textarea v-model="form.justification" rows="2" required
                    :placeholder="t('retrait.modal.justification_placeholder')"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm"></textarea>
        </div>

        <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">
          {{ errorMessage }}
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" :disabled="isSaving"
                  class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-xs disabled:opacity-50">
            {{ t('finance.modal.cancel') }}
          </button>
          <button type="submit" :disabled="isSaving || !isFormValid"
                  class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition flex items-center bg-red-600 hover:bg-red-700 disabled:opacity-50">
            {{ isSaving ? t('caisse.cancel_modal.saving') : t('finance.modal.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'save']);
const { t } = useI18n();

const form = reactive({
  amount: '',
  category: '',
  paymentMethod: 'Espèces',
  justification: '',
});

const isFormValid = computed(() => Number(form.amount) > 0 && form.justification.trim().length > 0);

const handleSubmit = () => {
  if (!isFormValid.value) return;
  emit('save', {
    amount: Number(form.amount),
    justification: form.justification.trim(),
    category: form.category || null,
    payment_method: form.paymentMethod,
  });
};
</script>
