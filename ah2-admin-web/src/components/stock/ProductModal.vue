<template>
  <!-- Panneau plein ecran sur telephone et tablette, grande fenetre centree sur PC -->
  <FullScreenPanel :title="isEditing ? t('stock.modal.edit_title') : t('stock.modal.add_title')" @close="$emit('close')">

    <form id="product-form" @submit.prevent="handleSubmit" class="space-y-4">

        <FormSection :title="t('stockScreens.section_product')">
            <div class="md:col-span-2">
                <FormField id="product-name" :label="t('stock.modal.name')" required v-slot="{ describedBy }">
                    <input id="product-name" v-model="form.name" type="text" required :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
                </FormField>
            </div>

            <FormField id="product-category" :label="t('stock.modal.category')" v-slot="{ describedBy }">
                <select id="product-category" v-model="form.category" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
                    <option value="PHARMA">{{ t('stock.categories.PHARMA') }}</option>
                    <option value="NATUREL">{{ t('stock.categories.NATUREL') }}</option>
                    <option value="MATERIEL">{{ t('stock.categories.MATERIEL') }}</option>
                </select>
            </FormField>

            <FormField id="product-price" :label="t('stock.modal.price') + ' (FCFA)'" required v-slot="{ describedBy }">
                <input id="product-price" v-model.number="form.price" type="number" required min="0" step="any" inputmode="decimal" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white text-right']" />
            </FormField>

            <template v-if="form.category === 'PHARMA'">
                <FormField id="product-forme" :label="t('stock.modal.form')" v-slot="{ describedBy }">
                    <select id="product-forme" v-model="form.forme" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
                        <option
                            v-for="opt in formOptions"
                            :key="opt.value"
                            :value="opt.value"
                        >
                            {{ t(opt.labelKey) }}
                        </option>
                    </select>
                </FormField>
                <FormField id="product-dosage" label="Dosage (mg/ml)" v-slot="{ describedBy }">
                    <input id="product-dosage" v-model="form.dosage" type="text" placeholder="Ex: 500mg" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
                </FormField>
            </template>
        </FormSection>

        <FormSection :title="t('stockScreens.section_stock')">
            <FormField id="product-quantity" :label="t('stock.modal.qty')" :required="canEditQuantity" v-slot="{ describedBy }">
                <input v-if="canEditQuantity" id="product-quantity" v-model.number="form.quantity" type="number" required min="0" inputmode="numeric" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white font-mono']" />
                <template v-else>
                    <p :id="'product-quantity'" class="px-1 py-2 font-mono text-base text-ink">{{ form.quantity ?? 0 }}</p>
                    <p class="text-sm text-ink-muted">{{ product ? t('stockAdjust.qty_readonly_edit') : t('stockAdjust.qty_readonly_create') }}</p>
                </template>
            </FormField>

            <FormField id="product-threshold" label="Seuil Alerte" required v-slot="{ describedBy }">
                <input id="product-threshold" v-model.number="form.minThreshold" type="number" required min="0" inputmode="numeric" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white font-mono']" />
            </FormField>

            <div class="md:col-span-2">
                <FormField
                    id="product-expiry"
                    :label="t('stock.modal.expiry')"
                    :help="form.category === 'MATERIEL' ? 'Optionnel pour le matériel non périssable.' : ''"
                    v-slot="{ describedBy }"
                >
                    <input id="product-expiry" v-model="form.expiryDate" type="date" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
                </FormField>
            </div>
        </FormSection>

    </form>

    <!-- Barre d'actions fixe : Enregistrer (principal) et Annuler (discret) -->
    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('common.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="product-form">
          <span v-if="isEditing">Mettre à jour</span>
          <span v-else>{{ t('common.save') }}</span>
        </AppButton>
      </ActionBar>
    </template>

  </FullScreenPanel>
</template>

<script setup>
import { reactive, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';

const props = defineProps({ product: Object, canEditQuantity: { type: Boolean, default: true } });
const emit = defineEmits(['close', 'save']);
const { t } = useI18n();

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// 🟢 Définition des options de forme avec clés de traduction
// 'value' est ce qui est stocké en BDD (on garde le français pour compatibilité)
// 'labelKey' est la clé pour l'affichage traduit
const formOptions = [
    { value: 'Comprimé', labelKey: 'stock.forms.tablet' },
    { value: 'Sirop', labelKey: 'stock.forms.syrup' },
    { value: 'Injection', labelKey: 'stock.forms.injection' },
    { value: 'Pommade', labelKey: 'stock.forms.ointment' },
    { value: 'Gélule', labelKey: 'stock.forms.capsule' },
    { value: 'Sachet', labelKey: 'stock.forms.sachet' },
    { value: 'Autre', labelKey: 'stock.forms.other' }
];

const form = reactive({
    id: null,
    name: '',
    category: 'PHARMA',
    quantity: 0,
    minThreshold: 10,
    price: 0,
    expiryDate: '',
    forme: 'Comprimé',
    dosage: ''
});

const isEditing = computed(() => !!form.id);

watch(() => props.product, (newVal) => {
    if (newVal) {
        Object.assign(form, newVal);
        if (!form.forme) form.forme = 'Autre';
    } else {
        Object.assign(form, {
            id: null,
            name: '',
            category: 'PHARMA',
            quantity: 0,
            minThreshold: 10,
            price: 0,
            expiryDate: '',
            forme: 'Comprimé',
            dosage: ''
        });
    }
}, { immediate: true });

const handleSubmit = () => {
    if (form.category !== 'PHARMA') {
        form.forme = 'Autre';
        form.dosage = '';
    }
    emit('save', { ...form });
};
</script>
