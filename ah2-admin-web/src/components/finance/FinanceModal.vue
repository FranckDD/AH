<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-md shadow-xl rounded-2xl bg-white">
      
      <!-- En-tête -->
      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ t('finance.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">
        
        <!-- Sélecteur TYPE (Recette / Dépense) -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('finance.modal.type') }}</label>
            <div class="flex rounded-md shadow-sm" role="group">
                <button 
                    type="button" 
                    @click="setTransactionType('INCOME')"
                    :class="form.type === 'INCOME' ? 'bg-green-600 text-white ring-2 ring-green-600' : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'"
                    class="flex-1 py-2 px-4 text-sm font-medium rounded-l-lg transition-colors flex justify-center items-center gap-2"
                >
                    <span>💰</span> {{ t('finance.income') }}
                </button>
                <button 
                    type="button" 
                    @click="setTransactionType('EXPENSE')"
                    :class="form.type === 'EXPENSE' ? 'bg-red-600 text-white ring-2 ring-red-600' : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'"
                    class="flex-1 py-2 px-4 text-sm font-medium rounded-r-lg transition-colors flex justify-center items-center gap-2"
                >
                    <span>💸</span> {{ t('finance.expense') }}
                </button>
            </div>
        </div>

        <!-- Montant et Date -->
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.amount') }}</label>
                <div class="relative rounded-md shadow-sm">
                    <input 
                        v-model.number="form.amount" 
                        type="number" 
                        min="1" 
                        required 
                        class="block w-full pl-3 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:outline-none transition sm:text-sm"
                        :class="form.type === 'INCOME' ? 'focus:ring-green-500 focus:border-green-500' : 'focus:ring-red-500 focus:border-red-500'"
                        placeholder="0"
                    />
                    <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <span class="text-gray-500 sm:text-sm">FCFA</span>
                    </div>
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.date') }}</label>
                <input 
                    v-model="form.date" 
                    type="date" 
                    required 
                    class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" 
                />
            </div>
        </div>

        <!-- Catégorie -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.category') }}</label>
            <select 
                v-model="form.category" 
                required
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
                <option value="" disabled>-- Sélectionner --</option>
                <!-- On lie la valeur à 'cat.key' (Code) et on affiche 'cat.label' (Traduction) -->
                <option v-for="cat in availableCategories" :key="cat.key" :value="cat.key">
                    {{ cat.label }}
                </option>
            </select>
        </div>

        <!-- Moyen de Paiement -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.method') }}</label>
            <select v-model="form.paymentMethod" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                <option value="Espèces">{{ t('finance.payment_methods.cash') }}</option>
                <option value="Mobile Money">{{ t('finance.payment_methods.mobile') }}</option>
                <option value="Virement">{{ t('finance.payment_methods.transfer') }}</option>
                <option value="Chèque">{{ t('finance.payment_methods.check') }}</option>
            </select>
        </div>

        <!-- Description -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.desc') }}</label>
            <textarea 
                v-model="form.description" 
                rows="2" 
                required
                placeholder="Ex: Achat de matériel, Consultation M. X..."
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            ></textarea>
        </div>

        <!-- Boutons -->
        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-sm">
            {{ t('finance.modal.cancel') }}
          </button>
          <button 
            type="submit" 
            class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition flex items-center"
            :class="form.type === 'INCOME' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'"
          >
            <!-- Petit loader si besoin, sinon texte normal -->
            {{ t('finance.modal.save') }}
          </button>
        </div>
      </form>

    </div>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const emit = defineEmits(['close', 'save']);

// Date du jour YYYY-MM-DD
const today = new Date().toISOString().substring(0, 10);

const form = reactive({
  type: 'INCOME',
  amount: '', // Vide par défaut pour forcer la saisie
  date: today,
  category: '',
  paymentMethod: 'Espèces',
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
        alert("Le montant doit être supérieur à 0");
        return;
    }
    if (!form.category) {
        alert("Veuillez sélectionner une catégorie");
        return;
    }

    // On envoie une copie des données
    emit('save', { ...form });
};
</script>