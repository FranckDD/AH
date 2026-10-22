<!-- src/components/stock/AdjustmentRequestModal.vue -->
<!-- Demande de reapprovisionnement / correction de stock (secretaire). -->
<template>
  <!-- Panneau plein ecran sur telephone et tablette, grande fenetre centree sur PC -->
  <FullScreenPanel :title="$t('stockAdjust.modal_title')" @close="$emit('close')">

    <form id="adjustment-form" @submit.prevent="submit" class="space-y-4">
      <p class="text-base text-ink">
        <span class="font-semibold">{{ product.name }}</span>,
        {{ $t('stockAdjust.current_stock') }} : {{ product.quantity }}
      </p>
      <p v-if="error" role="alert" class="flex items-start gap-2 rounded-control border p-3 text-base" :class="toneClasses('danger')">
        <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <span>{{ error }}</span>
      </p>

      <FormField id="adjust-kind" :label="$t('stockAdjust.col_kind')" :help="$t(`stockAdjust.kind_help.${form.kind}`)" v-slot="{ describedBy }">
        <select id="adjust-kind" v-model="form.kind" :aria-describedby="describedBy" :class="fieldClass">
          <option v-for="k in ADJUSTMENT_KINDS" :key="k" :value="k">{{ $t(`stockAdjust.kind.${k}`) }}</option>
        </select>
      </FormField>

      <FormField id="adjust-quantity" :label="$t('stockOps.col_quantity')" required v-slot="{ describedBy }">
        <input id="adjust-quantity" v-model.number="form.quantity" type="number" :min="form.kind === 'correction' ? 0 : 1" step="1"
               inputmode="numeric" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>

      <FormField id="adjust-reason" :label="$t('stockOps.col_reason')" required v-slot="{ describedBy }">
        <textarea id="adjust-reason" v-model="form.reason" rows="3" maxlength="2000" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ $t('stockOps.close') }}</AppButton>
        </template>
        <AppButton type="submit" form="adjustment-form" :disabled="saving" :loading="saving">
          {{ saving ? $t('stockOps.saving') : $t('stockAdjust.send') }}
        </AppButton>
      </ActionBar>
    </template>

  </FullScreenPanel>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ExclamationCircleIcon } from '@heroicons/vue/20/solid';
import { StockOpsGateway, describeStockError } from '@/services/StockOpsGateway';
import { ADJUSTMENT_KINDS, validateAdjustmentRequest } from '@/utils/adjustmentRequest';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';

// product : { id, name, quantity }
const props = defineProps({ product: { type: Object, required: true } });
const emit = defineEmits(['close', 'created']);
const { t } = useI18n();

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
