<template>
  <FullScreenPanel :title="mode === 'settle' ? t('caisse.installment_modal.settle_title') : t('caisse.installment_modal.title')" @close="$emit('close')">
    <form id="installment-form" @submit.prevent="handleSubmit" class="space-y-4">
      <p class="text-base text-ink">
        {{ t('caisse.installment_modal.remaining_due') }} : <span class="font-bold">{{ formatCurrency(remainingDue) }}</span>
      </p>

      <FormField id="installment-amount" :label="t('finance.modal.amount')" :help="t('caisseScreens.installment_help')" required v-slot="{ describedBy }">
        <input id="installment-amount" v-model.number="paidAmount" type="number" min="0.01" :max="remainingDue" step="0.01" required
               inputmode="decimal" :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" />
      </FormField>

      <FormField id="installment-method" :label="t('finance.modal.method')" v-slot="{ describedBy }">
        <select id="installment-method" v-model="paymentMethod" :aria-describedby="describedBy" :class="fieldClass">
          <option v-for="m in paymentModes" :key="m.code" :value="m.code">{{ m.label }}</option>
        </select>
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
        <AppButton type="submit" form="installment-form" :disabled="isSaving || !(paidAmount > 0)" :loading="isSaving">
          {{ isSaving ? t('caisse.cancel_modal.saving') : (mode === 'settle' ? t('caisse.installment_modal.settle_confirm') : t('finance.modal.save')) }}
        </AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ExclamationCircleIcon } from '@heroicons/vue/20/solid';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { usePaymentModes, normalizeMode, FALLBACK_PAYMENT_MODES } from '@/utils/paymentModes';
import { round2 } from '@/utils/invoiceTotals';

const props = defineProps({
  remainingDue: { type: Number, required: true },
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
  // 'settle' = bouton "Solder" : meme panneau, pre-rempli avec le reste du et
  // le mode de la facture, la secretaire confirme (et peut changer le mode ou
  // le montant). Plus aucun paiement en un seul clic (defaut 3, 2026-10-26).
  mode: { type: String, default: 'installment' },
  defaultMethod: { type: String, default: '' },
});
const emit = defineEmits(['close', 'confirm']);
const { t } = useI18n();

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const paidAmount = ref(props.remainingDue);
// Liste officielle des modes (codes stables, GET /payment-modes, repli hors ligne).
const paymentModes = usePaymentModes();
// Mode de la facture ramene a un code officiel ; sinon especes (le serveur
// refuse un mode hors liste).
const initialMethod = (raw) => {
  const code = normalizeMode(raw);
  return FALLBACK_PAYMENT_MODES.some((m) => m.code === code) ? code : 'especes';
};
const paymentMethod = ref(initialMethod(props.defaultMethod));
// SOLDE seulement si le versement couvre tout le reste du ; un montant reduit
// reste un versement ordinaire.
// Comparaison au centime (round2) : evite qu'un bruit binaire (ex. 1999.9999)
// transforme un solde complet en simple versement.
const paymentType = () => (props.mode === 'settle' && round2(paidAmount.value) >= round2(props.remainingDue) ? 'SOLDE' : 'VERSEMENT_ECHEANCE');

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value || 0).replace('XOF', 'FCFA');

const handleSubmit = () => {
  if (!(paidAmount.value > 0)) return;
  emit('confirm', { paid_amount: Number(paidAmount.value), payment_method: paymentMethod.value, payment_type: paymentType(), note: null });
};
</script>
