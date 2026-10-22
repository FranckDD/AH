<template>
  <FullScreenPanel :title="t('retrait.modal.title')" @close="$emit('close')">
    <form id="retrait-form" @submit.prevent="handleSubmit" class="grid gap-4">
      <FormField id="retrait-amount" :label="t('retrait.modal.amount')" :help="t('retraitScreens.amount_help')" required v-slot="{ describedBy }">
        <input id="retrait-amount" v-model.number="form.amount" type="number" min="1" step="0.01" required inputmode="decimal"
               :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" placeholder="0" />
      </FormField>

      <div class="grid gap-4 md:grid-cols-2">
        <FormField id="retrait-category" :label="t('retrait.modal.category')" v-slot="{ describedBy }">
          <select id="retrait-category" v-model="form.category" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">-- {{ t('retrait.modal.category') }} --</option>
            <option value="SUPPLIES">{{ t('finance.categories.supplies') }}</option>
            <option value="SALARY">{{ t('finance.categories.salary') }}</option>
            <option value="MAINTENANCE">{{ t('finance.categories.maintenance') }}</option>
            <option value="BILLS">{{ t('finance.categories.bills') }}</option>
            <option value="OTHER">{{ t('finance.categories.other') }}</option>
          </select>
        </FormField>

        <FormField id="retrait-method" :label="t('finance.modal.method')" v-slot="{ describedBy }">
          <select id="retrait-method" v-model="form.paymentMethod" :aria-describedby="describedBy" :class="fieldClass">
            <option value="Espèces">{{ t('finance.payment_methods.cash') }}</option>
            <option value="Mobile Money">{{ t('finance.payment_methods.mobile') }}</option>
            <option value="Virement">{{ t('finance.payment_methods.transfer') }}</option>
            <option value="Chèque">{{ t('finance.payment_methods.check') }}</option>
          </select>
        </FormField>
      </div>

      <FormField id="retrait-justification" :label="t('retrait.modal.justification')" :help="t('retraitScreens.justification_help')" required v-slot="{ describedBy }">
        <textarea id="retrait-justification" v-model="form.justification" rows="3" required
                  :placeholder="t('retrait.modal.justification_placeholder')" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>

      <p v-if="errorMessage" role="alert" class="flex items-start gap-2 rounded-control border p-3 text-base" :class="toneClasses('danger')">
        <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <span>{{ errorMessage }}</span>
      </p>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" :disabled="isSaving" @click="$emit('close')">{{ t('finance.modal.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="retrait-form" variant="danger" :disabled="isSaving || !isFormValid" :loading="isSaving">
          {{ isSaving ? t('caisse.cancel_modal.saving') : t('finance.modal.save') }}
        </AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ExclamationCircleIcon } from '@heroicons/vue/20/solid';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const props = defineProps({
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'save']);
const { t } = useI18n();

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
