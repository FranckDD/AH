<template>
  <div class="space-y-8 w-full">
    
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div>
            <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
                {{ t('config.title') }}
            </h1>
            <p class="text-sm text-gray-500">{{ t('config.subtitle') }}</p>
        </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        
        <div class="p-6 border-b border-gray-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <h2 class="text-xl font-bold text-gray-800">{{ t('config.exams_title') }}</h2>
            
            <div class="flex flex-1 md:justify-end space-x-3 w-full md:w-auto">
                
                <div class="relative w-full md:w-64">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
                    </div>
                    <input 
                        v-model="searchQuery"
                        type="text"
                        :placeholder="t('common.search_placeholder') || 'Rechercher...'"
                        class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-xl bg-gray-50 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition"
                    />
                </div>

                <button 
                    @click="openExamModal(null)" 
                    class="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 shadow-md transition font-semibold text-sm whitespace-nowrap"
                >
                    <PlusCircleIcon class="h-5 w-5 mr-2" />
                    {{ t('config.add_exam') }}
                </button>
            </div>
        </div>

        <div v-if="configStore.isLoading" class="p-10 text-center text-gray-500">
            <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-2"></span>
            <p>{{ t('common.loading') }}</p>
        </div>
        
        <div v-else class="overflow-x-auto">
            <table class="min-w-full text-left border-collapse">
                <thead>
                    <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                        <th class="px-6 py-3 font-semibold">{{ t('config.table_code') }}</th>
                        <th class="px-6 py-3 font-semibold">{{ t('config.table_name') }}</th>
                        <th class="px-6 py-3 font-semibold">{{ t('config.table_category') }}</th>
                        <th class="px-6 py-3 font-semibold text-right">{{ t('config.table_price') }}</th>
                        <th class="px-6 py-3 font-semibold text-right">{{ t('users.table.actions') }}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="exam in filteredExamens" :key="exam.id" class="hover:bg-gray-50 transition">
                        <td class="px-6 py-4 font-mono text-xs text-gray-600 bg-gray-50 w-24 border-r border-gray-100">
                            {{ exam.code }}
                        </td>
                        <td class="px-6 py-4 font-medium text-gray-900">
                            {{ exam.nom }}
                        </td>
                        <td class="px-6 py-4 text-sm text-gray-600">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-800 border border-blue-100">
                                {{ exam.categorie }}
                            </span>
                        </td>
                        <td class="px-6 py-4 text-right font-bold text-green-700 text-base">
                            {{ formatPrice(exam.prix) }}
                        </td>
                        <td class="px-6 py-4 text-right">
                            <button 
                                @click="openExamModal(exam)"
                                class="text-indigo-600 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center inline-flex ml-auto"
                            >
                                <PencilSquareIcon class="h-4 w-4 mr-1" />
                                {{ t('config.edit') }}
                            </button>
                        </td>
                    </tr>
                    <tr v-if="filteredExamens.length === 0">
                        <td colspan="5" class="px-6 py-8 text-center text-gray-500 italic">
                            {{ t('users.table.no_results') }} "{{ searchQuery }}"
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="p-6 border-b border-gray-100">
            <h2 class="text-xl font-bold text-gray-800">{{ t('config.prayers_title') }}</h2>
            <p class="text-sm text-gray-500 mt-1">{{ t('config.prayers_subtitle') }}</p>
        </div>
        <div class="overflow-x-auto">
            <table class="min-w-full text-left border-collapse">
                <thead>
                    <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                        <th class="px-6 py-3 font-semibold">{{ t('config.table_type_code') }}</th>
                        <th class="px-6 py-3 font-semibold">{{ t('config.table_label') }}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="type in configStore.prayerBookTypes" :key="type.type_code" class="hover:bg-gray-50 transition">
                        <td class="px-6 py-4 font-mono text-xs text-gray-600 w-24">{{ type.type_code }}</td>
                        <td class="px-6 py-4 font-medium text-gray-900">{{ type.label }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100">
        <div class="p-6 border-b border-gray-100">
            <h2 class="text-xl font-bold text-gray-800">{{ t('config.general_title') }}</h2>
            <p class="text-sm text-gray-500 mt-1">{{ t('config.general_subtitle') }}</p>
        </div>
        
        <div class="p-6 space-y-6">
            
            <div class="flex items-center justify-between border border-gray-200 p-4 rounded-xl">
                <div>
                    <h3 class="font-semibold text-gray-900 flex items-center">
                        <ArrowDownTrayIcon class="h-5 w-5 mr-2 text-indigo-500" />
                        {{ t('config.db_backup') }}
                    </h3>
                    <p class="text-sm text-gray-500">{{ t('config.db_backup_subtitle') }}</p>
                </div>
                
                <button 
                    @click="handleBackup"
                    :disabled="isBackupRunning"
                    :class="{'bg-indigo-600 hover:bg-indigo-700': !isBackupRunning, 'bg-gray-400 cursor-not-allowed': isBackupRunning}"
                    class="px-4 py-2 text-white rounded-lg font-medium shadow-md transition flex items-center"
                >
                    <span v-if="isBackupRunning" class="flex items-center">
                        <span class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                        {{ t('common.loading') }}
                    </span>
                    <span v-else>
                        {{ t('config.launch_backup') }}
                    </span>
                </button>
            </div>

            <div class="flex items-center justify-between border border-gray-200 p-4 rounded-xl">
                <div>
                    <h3 class="font-semibold text-gray-900 flex items-center">
                        <WrenchScrewdriverIcon class="h-5 w-5 mr-2" :class="isMaintenanceMode ? 'text-red-500' : 'text-green-500'" />
                        {{ t('config.maintenance_mode') }}
                    </h3>
                    <p class="text-sm" :class="isMaintenanceMode ? 'text-red-600 font-bold' : 'text-gray-500'">
                        {{ isMaintenanceMode ? t('config.maintenance_active') : t('config.maintenance_mode_subtitle') }}
                    </p>
                </div>
                
                <button 
                    @click="toggleMaintenanceMode"
                    :class="isMaintenanceMode 
                        ? 'bg-red-600 hover:bg-red-700' 
                        : 'bg-green-600 hover:bg-green-700'"
                    class="px-4 py-2 text-white rounded-lg font-medium shadow-md transition"
                >
                    {{ isMaintenanceMode ? t('config.deactivate') : t('config.activate') }}
                </button>
            </div>

        </div>
    </div>

    <Modal v-if="showExamModal" @close="showExamModal = false">
        <h3 class="text-xl font-bold text-gray-800 mb-4">{{ modalForm.id ? t('config.edit') : t('config.add_exam') }}</h3>
        
        <form @submit.prevent="handleSaveExamen" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700">{{ t('config.table_name') }}</label>
                <input v-model="modalForm.nom" type="text" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">{{ t('config.table_code') }}</label>
                    <input v-model="modalForm.code" type="text" required :disabled="modalForm.id !== null" :class="{'bg-gray-100': modalForm.id !== null}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700">{{ t('config.table_category') }}</label>
                    <input v-model="modalForm.categorie" type="text" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">{{ t('config.table_price') }}</label>
                <div class="relative">
                    <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500 font-bold text-sm">FCFA</span>
                    <input 
                        v-model.number="modalForm.prix" 
                        type="number" 
                        step="100" 
                        required 
                        min="0"
                        class="w-full pl-14 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 font-mono" 
                    />
                </div>
            </div>

            <div class="pt-4 flex justify-end space-x-3 border-t">
                <button type="button" @click="showExamModal = false" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition">
                    {{ t('config.cancel') }}
                </button>
                <button type="submit" class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium shadow-md transition flex items-center">
                    <CheckCircleIcon class="h-5 w-5 inline mr-2" />
                    {{ t('config.save') }}
                </button>
            </div>
        </form>
    </Modal>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useConfigStore } from '@/stores/configStore';
import { useI18n } from 'vue-i18n';
import { 
    PlusCircleIcon, 
    PencilSquareIcon, 
    MagnifyingGlassIcon,
    CheckCircleIcon,
    WrenchScrewdriverIcon, // Nouvelle icône
    ArrowDownTrayIcon       // Nouvelle icône
} from '@heroicons/vue/24/outline';

import Modal from '@/components/common/Modal.vue'; 

const { t } = useI18n();
const configStore = useConfigStore();

// --- Logique Modale Examens ---
const showExamModal = ref(false);
const searchQuery = ref(''); 

const modalForm = reactive({
    id: null,
    code: '',
    nom: '',
    categorie: '',
    prix: 0.00
});

// --- Logique Générale et Maintenance ---
const isMaintenanceMode = ref(false);
const isBackupRunning = ref(false);

const fetchGeneralConfig = () => {
    // Simuler le chargement d'un état (par exemple, de l'API)
    isMaintenanceMode.value = false; // Par défaut, désactivé
};

onMounted(() => {
    configStore.fetchExamens();
    configStore.fetchPrayerBooks();
    // Fetch des configurations générales (mock)
    fetchGeneralConfig();
});

// 🔍 Filtrage des Examens
const filteredExamens = computed(() => {
    if (!searchQuery.value) return configStore.examens;
    
    const query = searchQuery.value.toLowerCase();
    return configStore.examens.filter(exam => 
        exam.nom.toLowerCase().includes(query) ||
        exam.code.toLowerCase().includes(query) ||
        exam.categorie.toLowerCase().includes(query)
    );
});

const openExamModal = (exam) => {
    if (exam) {
        // Mode Édition
        modalForm.id = exam.id;
        modalForm.code = exam.code;
        modalForm.nom = exam.nom;
        modalForm.categorie = exam.categorie;
        modalForm.prix = exam.prix;
    } else {
        // Mode Ajout : Reset
        modalForm.id = null;
        modalForm.code = '';
        modalForm.nom = '';
        modalForm.categorie = '';
        modalForm.prix = 0;
    }
    showExamModal.value = true;
};

const handleSaveExamen = async () => {
    await configStore.saveExamen({ ...modalForm });
    showExamModal.value = false;
    console.log(`Examen ${modalForm.nom} sauvegardé.`);
};

const handleBackup = async () => {
    if (isBackupRunning.value) return;

    isBackupRunning.value = true;
    console.log("Lancement de la procédure de sauvegarde BDD...");
    
    // Simulation d'appel API au backend (3 secondes)
    await new Promise(resolve => setTimeout(resolve, 3000)); 
    
    console.log("Sauvegarde BDD terminée !");
    isBackupRunning.value = false;
    alert(t('config.db_backup') + " terminée avec succès.");
};

const toggleMaintenanceMode = async () => {
    // Simulation d'appel API pour changer l'état global du système
    isMaintenanceMode.value = !isMaintenanceMode.value;
    console.log(`Mode Maintenance basculé sur: ${isMaintenanceMode.value}`);
};

const formatPrice = (price) => {
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'XOF',
        minimumFractionDigits: 0
    }).format(price).replace('XOF', 'FCFA'); 
};
</script>