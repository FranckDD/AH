<template>
  <Modal @close="$emit('close')">
    <h3 class="text-xl font-bold text-gray-800 mb-6 border-b pb-3">
        {{ isEditing ? t('stock.modal.edit_title') : t('stock.modal.add_title') }}
    </h3>

    <form @submit.prevent="handleSubmit" class="space-y-4">
        
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('stock.modal.name') }}</label>
            <input v-model="form.name" type="text" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" />
        </div>

        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('stock.modal.category') }}</label>
                <select v-model="form.category" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 bg-white">
                    <option value="PHARMA">{{ t('stock.categories.PHARMA') }}</option>
                    <option value="NATUREL">{{ t('stock.categories.NATUREL') }}</option>
                    <option value="MATERIEL">{{ t('stock.categories.MATERIEL') }}</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('stock.modal.price') }}</label>
                <div class="relative">
                    <input v-model.number="form.price" type="number" required min="0" class="w-full pl-3 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 text-right" />
                    <span class="absolute right-3 top-2 text-gray-400 text-sm">FCFA</span>
                </div>
            </div>
        </div>

        <div v-if="form.category === 'PHARMA'" class="grid grid-cols-2 gap-4 bg-blue-50 p-3 rounded-lg border border-blue-100 animate-fade-in">
            <div>
                <label class="block text-xs font-bold text-blue-700 mb-1 uppercase">
                    {{ t('stock.modal.form') || 'Forme' }} </label>
                <select 
                    v-model="form.forme" 
                    class="w-full px-2 py-1.5 border border-blue-200 rounded text-sm focus:ring-blue-500 bg-white"
                >
                    <option 
                        v-for="opt in formOptions" 
                        :key="opt.value" 
                        :value="opt.value"
                    >
                        {{ t(opt.labelKey) }}
                    </option>
                </select>
            </div>
            <div>
                <label class="block text-xs font-bold text-blue-700 mb-1 uppercase">Dosage (mg/ml)</label>
                <input v-model="form.dosage" type="text" placeholder="Ex: 500mg" class="w-full px-2 py-1.5 border border-blue-200 rounded text-sm focus:ring-blue-500" />
            </div>
        </div>

        <div class="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
            <div>
                <label class="block text-sm font-bold text-gray-700 mb-1">{{ t('stock.modal.qty') }}</label>
                <input v-model.number="form.quantity" type="number" required min="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 font-mono" />
            </div>
            <div>
                <label class="block text-sm font-bold text-gray-700 mb-1">Seuil Alerte</label>
                <input v-model.number="form.minThreshold" type="number" required min="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 font-mono text-red-600" />
            </div>
        </div>

        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('stock.modal.expiry') }}</label>
            <input v-model="form.expiryDate" type="date" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" />
            <p v-if="form.category === 'MATERIEL'" class="text-xs text-gray-500 mt-1 italic">
                Optionnel pour le matériel non périssable.
            </p>
        </div>

        <div class="pt-4 flex justify-end space-x-3 border-t mt-6">
            <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition">
                {{ t('common.cancel') }}
            </button>
            <button type="submit" class="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 shadow-md transition flex items-center">
                <span v-if="isEditing">Mettre à jour</span>
                <span v-else>{{ t('common.save') }}</span>
            </button>
        </div>

    </form>
  </Modal>
</template>

<script setup>
import { reactive, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import Modal from '@/components/common/Modal.vue';

const props = defineProps({ product: Object });
const emit = defineEmits(['close', 'save']);
const { t } = useI18n();

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

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>