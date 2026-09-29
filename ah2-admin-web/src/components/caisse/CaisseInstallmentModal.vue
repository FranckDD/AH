<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-sm shadow-xl rounded-2xl bg-white">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold text-gray-900">{{ t('caisse.installment_modal.title') }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <p class="text-sm text-gray-600 mb-4">
        {{ t('caisse.installment_modal.remaining_due') }}: <span class="font-bold">{{ formatCurrency(remainingDue) }}</span>
      </p>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('caisse.invoice_modal.unit_price') === '' ? '' : t('finance.modal.amount') }}</label>
          <input v-model.number="paidAmount" type="number" min="0.01" :max="remainingDue" step="0.01" required
                 class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.method') }}</label>
          <select v-model="paymentMethod" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm">
            <option value="Espèces">{{ t('finance.payment_methods.cash') }}</option>
            <option value="Mobile Money">{{ t('finance.payment_methods.mobile') }}</option>
            <option value="Virement">{{ t('finance.payment_methods.transfer') }}</option>
            <option value="Chèque">{{ t('finance.payment_methods.check') }}</option>
          </select>
        </div>

        <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">
          {{ errorMessage }}
        </div>

        <div class="flex justify-end space-x-3 pt-2">
          <button type="button" @click="$emit('close')" :disabled="isSaving"
                  class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition disabled:opacity-50">
            {{ t('finance.modal.cancel') }}
          </button>
          <button type="submit" :disabled="isSaving || !(paidAmount > 0)"
                  class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium shadow-xs transition disabled:opacity-50">
            {{ isSaving ? t('caisse.cancel_modal.saving') : t('finance.modal.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  remainingDue: { type: Number, required: true },
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'confirm']);
const { t } = useI18n();

const paidAmount = ref(props.remainingDue);
const paymentMethod = ref('Espèces');

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value || 0).replace('XOF', 'FCFA');

const handleSubmit = () => {
  if (!(paidAmount.value > 0)) return;
  emit('confirm', { paid_amount: Number(paidAmount.value), payment_method: paymentMethod.value, note: null });
};
</script>
