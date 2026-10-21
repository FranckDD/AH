<!-- src/components/stock/AdjustmentRequestModal.vue -->
<!-- Demande de reapprovisionnement / correction de stock (secretaire). -->
<template>
  <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
    <form @submit.prevent="submit" class="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-3 max-h-[90vh] overflow-y-auto">
      <h3 class="text-lg font-semibold text-gray-800">{{ $t('stockAdjust.modal_title') }}</h3>
      <p class="text-sm text-gray-600">
        <span class="font-medium">{{ product.name }}</span>
        — {{ $t('stockAdjust.current_stock') }} : {{ product.quantity }}
      </p>
      <div v-if="error" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ error }}</div>

      <label class="block text-sm">{{ $t('stockAdjust.col_kind') }}
        <select v-model="form.kind" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg">
          <option v-for="k in ADJUSTMENT_KINDS" :key="k" :value="k">{{ $t(`stockAdjust.kind.${k}`) }}</option>
        </select>
      </label>
      <p class="text-xs text-gray-500">{{ $t(`stockAdjust.kind_help.${form.kind}`) }}</p>

      <label class="block text-sm">{{ $t('stockOps.col_quantity') }}
        <input v-model.number="form.quantity" type="number" :min="form.kind === 'correction' ? 0 : 1" step="1"
               class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg" />
      </label>
      <label class="block text-sm">{{ $t('stockOps.col_reason') }}
        <textarea v-model="form.reason" rows="3" maxlength="2000" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"></textarea>
      </label>

      <div class="flex justify-end gap-2 pt-2">
        <button type="button" @click="$emit('close')" class="px-4 py-2 bg-gray-200 rounded-lg text-sm">{{ $t('stockOps.close') }}</button>
        <button type="submit" :disabled="saving" class="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
          {{ saving ? $t('stockOps.saving') : $t('stockAdjust.send') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { ADJUSTMENT_KINDS, validateAdjustmentRequest } from '@/utils/adjustmentRequest';

// product : { id, name, quantity }
const props = defineProps({ product: { type: Object, required: true } });
const emit = defineEmits(['close', 'created']);
const { t } = useI18n();

const form = reactive({ kind: 'reapprovisionnement', quantity: null, reason: '' });
const error = ref('');
const saving = ref(false);

const submit = async () => {
  error.value = '';
  const check = validateAdjustmentRequest(form);
  if (!check.ok) { error.value = t(`stockAdjust.err_${check.error}`); return; }
  saving.value = true;
  try {
    const created = await StockOpsGateway.createAdjustmentRequest({
      product_id: props.product.id, kind: form.kind, quantity: form.quantity, reason: form.reason.trim(),
    });
    emit('created', created);
  } catch (err) {
    error.value = describeStockError(err, t('stockOps.error_save'));
    console.error('Creation de la demande d\'ajustement echouee :', err);
  } finally {
    saving.value = false;
  }
};
</script>
