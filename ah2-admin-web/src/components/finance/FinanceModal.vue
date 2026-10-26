<template>
  <FullScreenPanel :title="t('finance.modal.title_new')" @close="$emit('close')">
    <form id="finance-form" @submit.prevent="handleSubmit" class="grid gap-4">
      <p role="note" class="rounded-control border p-3 text-base" :class="toneClasses('warning')">{{ t('financeScreens.real_money_warning') }}</p>

      <!-- Type : Recette ou Depense (etat ecrit, pas seulement la couleur) -->
      <div class="grid gap-1.5">
        <span class="text-base font-medium text-ink">{{ t('finance.modal.type') }}</span>
        <div class="grid grid-cols-2 gap-2" role="group" :aria-label="t('finance.modal.type')">
          <AppButton :variant="form.type === 'INCOME' ? 'success' : 'secondary'" :aria-pressed="form.type === 'INCOME'" :icon="BanknotesIcon" @click="setTransactionType('INCOME')">
            {{ t('finance.income') }}
          </AppButton>
          <AppButton :variant="form.type === 'EXPENSE' ? 'danger' : 'secondary'" :aria-pressed="form.type === 'EXPENSE'" :icon="ArrowTrendingDownIcon" @click="setTransactionType('EXPENSE')">
            {{ t('finance.expense') }}
          </AppButton>
        </div>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <FormField id="fin-amount" :label="t('finance.modal.amount')" :help="t('financeScreens.amount_help')" required v-slot="{ describedBy }">
          <input id="fin-amount" v-model.number="form.amount" type="number" min="1" required inputmode="decimal"
                 :aria-describedby="describedBy" :class="[fieldClass, 'text-right']" placeholder="0" />
        </FormField>
        <FormField id="fin-date" :label="t('finance.modal.date')" required v-slot="{ describedBy }">
          <input id="fin-date" v-model="form.date" type="date" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <FormField id="fin-category" :label="t('finance.modal.category')" required v-slot="{ describedBy }">
          <select id="fin-category" v-model="form.category" required :aria-describedby="describedBy" :class="fieldClass">
            <option value="" disabled>{{ t('financeScreens.select_category') }}</option>
            <!-- On lie la valeur a 'cat.key' (code) et on affiche 'cat.label' (traduction) -->
            <option v-for="cat in availableCategories" :key="cat.key" :value="cat.key">
              {{ cat.label }}
            </option>
          </select>
        </FormField>
        <FormField id="fin-method" :label="t('finance.modal.method')" required v-slot="{ describedBy }">
          <select id="fin-method" v-model="form.paymentMethod" required :aria-describedby="describedBy" :class="fieldClass">
            <option value="" disabled>{{ t('paymentModeChoice.placeholder') }}</option>
            <option v-for="m in paymentModes" :key="m.code" :value="m.code">{{ m.label }}</option>
          </select>
        </FormField>
      </div>

      <FormField id="fin-desc" :label="t('finance.modal.desc')" required v-slot="{ describedBy }">
        <textarea id="fin-desc" v-model="form.description" rows="3" required
                  :placeholder="t('financeScreens.description_placeholder')" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('finance.modal.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="finance-form" :variant="form.type === 'INCOME' ? 'success' : 'danger'">{{ t('finance.modal.save') }}</AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { notify, notifyText } from '@/utils/notify';
import { reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { BanknotesIcon, ArrowTrendingDownIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { usePaymentModes } from '@/utils/paymentModes';
import { todayLocalISO } from '@/utils/localDate';

const { t } = useI18n();
// Liste officielle des modes (repli fige hors ligne) ; la valeur envoyee est le CODE.
const paymentModes = usePaymentModes();

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const emit = defineEmits(['close', 'save']);

// Date du jour YYYY-MM-DD
const today = todayLocalISO();

const form = reactive({
  type: 'INCOME',
  amount: '', // Vide par défaut pour forcer la saisie
  date: today,
  category: '',
  paymentMethod: '', // aucun defaut : on choisit un mode de la liste officielle (code stocke)
  description: ''
});

// Gestion du changement de type
const setTransactionType = (type) => {
    form.type = type;
    form.category = ''; // On reset la catégorie car les listes sont différentes
};

// 🟢 LISTES DES CATÉGORIES (CODES + LABELS)
// Les 'key' sont les valeurs envoyées à la BDD (Majuscules pour la standardisation)
const availableCategories = computed(() => {
    if (form.type === 'INCOME') {
        return [
            { key: 'CONSULTATION', label: t('finance.categories.consultation') },
            { key: 'PHARMACY', label: t('finance.categories.pharmacy') },
            { key: 'HOSPITALIZATION', label: t('finance.categories.hospitalization') },
            { key: 'LAB', label: t('finance.categories.lab') },
            { key: 'DETOX', label: t('finance.categories.detox') },
            { key: 'OTHER', label: t('finance.categories.other') }
        ];
    } else {
        return [
            { key: 'SUPPLIES', label: t('finance.categories.supplies') }, // Achat matériel
            { key: 'SALARY', label: t('finance.categories.salary') },
            { key: 'MAINTENANCE', label: t('finance.categories.maintenance') },
            { key: 'BILLS', label: t('finance.categories.bills') }, // Factures eau/élec
            { key: 'OTHER', label: t('finance.categories.other') }
        ];
    }
});

const handleSubmit = () => {
    // Validation basique
    if (form.amount <= 0) {
        notify('alerts.amount_positive');
        return;
    }
    if (!form.category) {
        notify('alerts.category_required');
        return;
    }
    if (!form.paymentMethod) {
        notifyText(t('paymentModeChoice.placeholder'));
        return;
    }

    // On envoie une copie des données
    emit('save', { ...form });
};
</script>