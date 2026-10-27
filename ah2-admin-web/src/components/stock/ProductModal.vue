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
                    <option value="AUTRE">{{ t('stock.categories.AUTRE') }}</option>
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
                <FormField id="product-dosage" :label="t('stock.modal.dosage')" v-slot="{ describedBy }">
                    <input id="product-dosage" v-model="form.dosage" type="text" :placeholder="t('stock.modal.dosage_ph')" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
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

            <FormField id="product-threshold" :label="t('stock.modal.threshold')" required v-slot="{ describedBy }">
                <input id="product-threshold" v-model.number="form.minThreshold" type="number" required min="0" inputmode="numeric" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white font-mono']" />
            </FormField>

            <div class="md:col-span-2">
                <FormField
                    id="product-expiry"
                    :label="t('stock.modal.expiry')"
                    :help="form.category === 'MATERIEL' ? t('stock.modal.expiry_optional') : ''"
                    v-slot="{ describedBy }"
                >
                    <input id="product-expiry" v-model="form.expiryDate" type="date" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
                </FormField>
            </div>
        </FormSection>

    </form>

    <!-- Photo et code-barres : fiche d'un produit existant, roles de gestion seulement (le code n'est jamais modifiable) -->
    <FormSection v-if="isEditing && canManage" :title="t('stockLabels.section_title')" class="mt-4">
        <div class="grid gap-4 md:col-span-2 md:grid-cols-2">
            <div class="grid content-start gap-3">
                <p class="text-base font-medium text-ink">{{ t('stockLabels.code_label') }}</p>
                <p data-testid="product-code" class="select-all font-mono text-3xl font-bold tracking-widest text-ink">{{ form.barcode || '-' }}</p>
                <p class="text-sm text-ink-muted">{{ t('stockLabels.code_help') }}</p>
                <div v-if="barcodeMarkup" class="w-full max-w-xs rounded-control border border-tone-neutral-border bg-white p-2" v-html="barcodeMarkup"></div>
            </div>

            <div class="grid content-start gap-3">
                <p class="text-base font-medium text-ink">{{ t('stockLabels.photo_label') }}</p>
                <div class="flex h-48 w-48 items-center justify-center overflow-hidden rounded-control border border-dashed border-tone-neutral-border bg-tone-neutral-bg">
                    <img v-if="photoUrl" :src="photoUrl" :alt="form.name" class="h-full w-full object-contain" />
                    <span v-else class="px-2 text-center text-base text-ink-muted">{{ t('stockLabels.no_photo') }}</span>
                </div>
                <p class="text-sm text-ink-muted">{{ t('stockLabels.photo_help') }}</p>
                <input ref="photoInput" type="file" accept="image/jpeg,image/png,image/webp" class="hidden" tabindex="-1" aria-hidden="true" @change="onPhotoPicked" />
                <div class="flex flex-wrap gap-2">
                    <AppButton type="button" variant="secondary" :disabled="photoBusy" :loading="photoBusy" @click="photoInput && photoInput.click()">
                        {{ form.hasPhoto ? t('stockLabels.replace_photo') : t('stockLabels.add_photo') }}
                    </AppButton>
                    <AppButton v-if="form.hasPhoto" type="button" variant="ghost" :disabled="photoBusy" @click="removePhoto">
                        {{ t('stockLabels.remove_photo') }}
                    </AppButton>
                </div>
                <p v-if="photoError" role="alert" class="rounded-control border p-3 text-base font-medium" :class="toneClasses('danger')">{{ photoError }}</p>
            </div>
        </div>
    </FormSection>

    <!-- Barre d'actions fixe : Enregistrer (principal) et Annuler (discret) -->
    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('common.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="product-form">
          <span v-if="isEditing">{{ t('stock.modal.update') }}</span>
          <span v-else>{{ t('common.save') }}</span>
        </AppButton>
      </ActionBar>
    </template>

  </FullScreenPanel>
</template>

<script setup>
import { reactive, ref, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import { useStockStore } from '@/stores/stockStore';
import { ProductPhotoGateway } from '@/services/ProductPhotoGateway';
import { barcodeSvgMarkup } from '@/utils/barcodeSvg';
import { describeServerError } from '@/utils/serverError';

const props = defineProps({ product: Object, canEditQuantity: { type: Boolean, default: true } });
const emit = defineEmits(['close', 'save']);
const { t } = useI18n();
const authStore = useAuthStore();
const stockStore = useStockStore();

// Photo et etiquettes : roles de gestion seulement (la secretaire ne fait que lire le stock).
const canManage = computed(() => authStore.hasRole(['admin', 'Assistant', 'ToxicoManager']));
const MAX_PHOTO_BYTES = 5 * 1024 * 1024;
const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const photoInput = ref(null);
const photoUrl = ref(null);
const photoBusy = ref(false);
const photoError = ref('');

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
    dosage: '',
    barcode: '',
    hasPhoto: false,
    photoVersion: 0
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
            dosage: '',
            barcode: '',
            hasPhoto: false,
            photoVersion: 0
        });
    }
}, { immediate: true });

const barcodeMarkup = computed(() => barcodeSvgMarkup(form.barcode));

// Apercu : recharge quand la photo change (version incrementee par le serveur).
watch(() => [form.id, form.hasPhoto, form.photoVersion, canManage.value], async ([id, has, version, manage]) => {
    photoUrl.value = null;
    if (!id || !has || !manage) return;
    const url = await ProductPhotoGateway.getPhotoUrl(id, version);
    if (form.id === id && form.photoVersion === version) photoUrl.value = url;
}, { immediate: true });

const applyServerProduct = (data) => {
    form.hasPhoto = !!data?.has_photo;
    form.photoVersion = Number(data?.photo_version) || 0;
    // La liste du stock est rechargee pour que la ligne (et l'etat de la photo) soit a jour.
    stockStore.fetchStock();
};

const onPhotoPicked = async (event) => {
    const input = event.target;
    const file = input.files && input.files[0];
    input.value = '';
    if (!file) return;
    photoError.value = '';
    if (!PHOTO_TYPES.includes(file.type)) { photoError.value = t('stockLabels.bad_type'); return; }
    if (file.size > MAX_PHOTO_BYTES) { photoError.value = t('stockLabels.too_big'); return; }
    photoBusy.value = true;
    try {
        applyServerProduct(await ProductPhotoGateway.uploadPhoto(form.id, file));
    } catch (err) {
        photoError.value = describeServerError(err, t('stockLabels.upload_failed'));
    } finally {
        photoBusy.value = false;
    }
};

const removePhoto = async () => {
    if (!window.confirm(t('stockLabels.confirm_remove'))) return;
    photoError.value = '';
    photoBusy.value = true;
    try {
        applyServerProduct(await ProductPhotoGateway.deletePhoto(form.id));
    } catch (err) {
        photoError.value = describeServerError(err, t('stockLabels.remove_failed'));
    } finally {
        photoBusy.value = false;
    }
};

const handleSubmit = () => {
    if (form.category !== 'PHARMA') {
        form.forme = 'Autre';
        form.dosage = '';
    }
    emit('save', { ...form });
};
</script>
