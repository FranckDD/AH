<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-75 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    <div class="relative mx-auto w-full max-w-lg bg-white shadow-2xl rounded-xl border border-gray-100 p-6">
      
      <div class="flex justify-between items-center mb-6 border-b pb-3">
        <h3 class="text-xl font-bold text-gray-800">
          {{ isEditing ? t('config.edit') : t('config.add_exam') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>
      
      <form @submit.prevent="handleSave" class="space-y-4">
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('config.table_name') }}</label>
          <input 
            v-model="form.nom" 
            type="text" 
            required 
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition" 
          />
        </div>
        
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('config.table_code') }}</label>
            <input 
              v-model="form.code" 
              type="text" 
              required 
              :disabled="isEditing" 
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 transition" 
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('config.table_category') }}</label>
            <input 
              v-model="form.categorie" 
              type="text" 
              required 
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition" 
            />
          </div>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('config.table_price') }}</label>
          <div class="relative">
            <input 
              v-model.number="form.prix" 
              type="number" 
              min="0" 
              step="100" 
              required 
              class="w-full pl-4 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 font-bold text-gray-800 font-mono transition" 
            />
            <span class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 font-bold text-xs">FCFA</span>
          </div>
        </div>

        <div class="pt-6 flex justify-end space-x-3 border-t mt-4">
          <button 
            type="button" 
            @click="$emit('close')" 
            class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition"
          >
            {{ t('config.cancel') }}
          </button>
          <button 
            type="submit" 
            :disabled="configStore.isLoading"
            class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium shadow-md transition flex items-center disabled:opacity-70 disabled:cursor-not-allowed"
          >
            <span v-if="configStore.isLoading" class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2"></span>
            <CheckCircleIcon v-else class="h-5 w-5 mr-2" />
            {{ t('config.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue';
import { useConfigStore } from '@/stores/configStore';
import { useI18n } from 'vue-i18n';
import { CheckCircleIcon } from '@heroicons/vue/24/outline';

const props = defineProps({
  examen: { type: Object, default: null }
});

const emit = defineEmits(['close', 'saved']);
const { t } = useI18n();
const configStore = useConfigStore();

// Initialisation du formulaire
const form = reactive({
  id: null,
  code: '',
  nom: '',
  categorie: '',
  prix: 0
});

const isEditing = computed(() => form.id !== null);

// Remplir le formulaire à l'ouverture ou au changement de la prop
watch(() => props.examen, (newVal) => {
  if (newVal) {
    // Copie pour éviter de modifier la prop directement
    Object.assign(form, newVal);
  } else {
    // Reset pour mode Ajout
    form.id = null;
    form.code = '';
    form.nom = '';
    form.categorie = '';
    form.prix = 0;
  }
}, { immediate: true });

const handleSave = async () => {
  try {
    await configStore.saveExamen({ ...form });
    emit('saved'); // Notifier le parent pour rafraîchir la liste si besoin
    emit('close');
  } catch (error) {
    // L'erreur est déjà loguée dans le store, mais on peut ajouter une alerte locale ici si nécessaire
    alert(error.message);
  }
};
</script>