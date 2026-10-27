<script setup>
// Fiche du produit concerne dans la fenetre de nouvelle facture : photo (ou
// image neutre), nom, forme, dosage, prix, stock. Purement informatif.
import { ref, watch, computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhotoIcon } from '@heroicons/vue/24/outline';
import { ProductPhotoGateway } from '@/services/ProductPhotoGateway';

const props = defineProps({
    product: { type: Object, default: null },
    formatCurrency: { type: Function, required: true },
});
const { t } = useI18n();
const photoUrl = ref(null);
let token = 0;

watch(
    () => [props.product?.medication_id, props.product?.has_photo, props.product?.photo_version],
    async ([id, hasPhoto, version]) => {
        const mine = ++token;
        photoUrl.value = null;
        if (!id || !hasPhoto) return;
        const url = await ProductPhotoGateway.getPhotoUrl(id, version);
        if (mine === token) photoUrl.value = url;
    },
    { immediate: true }
);
onBeforeUnmount(() => { token++; });

const stock = computed(() => (props.product?.quantity != null ? Number(props.product.quantity) : null));
const dosage = computed(() => {
    const d = props.product?.dosage_mg;
    return d === null || d === undefined || d === '' ? '' : `${Number(d)} mg`;
});
</script>

<template>
    <aside class="grid content-start gap-2 rounded-card border border-tone-neutral-border bg-white p-3" :aria-label="t('caisseInvoice.product_panel')">
        <p class="text-base font-semibold text-ink">{{ t('caisseInvoice.product_panel') }}</p>
        <template v-if="product">
            <div class="flex h-40 items-center justify-center overflow-hidden rounded-control border border-tone-neutral-border bg-tone-neutral-bg">
                <img v-if="photoUrl" :src="photoUrl" :alt="product.drug_name" class="h-full w-full object-contain" />
                <div v-else class="flex flex-col items-center gap-1 text-ink-muted">
                    <PhotoIcon class="h-12 w-12" aria-hidden="true" />
                    <span class="text-base">{{ t('caisseInvoice.product_no_photo') }}</span>
                </div>
            </div>
            <p class="text-lg font-bold text-ink">{{ product.drug_name }}</p>
            <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-base">
                <template v-if="product.forme">
                    <dt class="text-ink-muted">{{ t('caisseInvoice.product_forme') }}</dt>
                    <dd class="text-right font-medium text-ink">{{ product.forme }}</dd>
                </template>
                <template v-if="dosage">
                    <dt class="text-ink-muted">{{ t('caisseInvoice.product_dosage') }}</dt>
                    <dd class="text-right font-medium text-ink">{{ dosage }}</dd>
                </template>
                <dt class="text-ink-muted">{{ t('caisseInvoice.product_price') }}</dt>
                <dd class="text-right font-semibold text-ink">{{ formatCurrency(product.price) }}</dd>
                <template v-if="stock !== null">
                    <dt class="text-ink-muted">{{ t('caisseInvoice.product_stock') }}</dt>
                    <dd class="text-right font-medium text-ink">{{ stock }}</dd>
                </template>
            </dl>
        </template>
        <p v-else class="text-base text-ink-muted">{{ t('caisseInvoice.product_none') }}</p>
    </aside>
</template>
