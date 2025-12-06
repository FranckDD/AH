<template>
  <div class="space-y-8 w-full max-w-7xl mx-auto pb-12">
    
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('config.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('config.subtitle') }}</p>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden transition-all">
      <div 
        @click="openSections.structure = !openSections.structure"
        class="p-6 border-b border-gray-100 bg-gray-50/80 cursor-pointer hover:bg-gray-100 transition flex justify-between items-center"
      >
        <div>
            <h2 class="text-lg font-bold text-gray-800 flex items-center">
                <BuildingOfficeIcon class="h-5 w-5 mr-2 text-indigo-600" />
                Identité de la Structure & En-tête des Documents
            </h2>
            <p class="text-sm text-gray-500 mt-1">
                Ces informations seront utilisées pour générer les en-têtes de vos factures, ordonnances et rapports.
            </p>
        </div>
        <ChevronDownIcon 
            class="h-6 w-6 text-gray-400 transform transition-transform duration-200"
            :class="{'rotate-180': openSections.structure}"
        />
      </div>
      
      <div v-show="openSections.structure" class="transition-all duration-300 ease-in-out">
        <form @submit.prevent="saveStructureConfig" class="p-6">
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6">

                <div class="md:col-span-4 flex flex-col items-center justify-start p-4 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50 hover:bg-gray-100 transition">
                    <label class="block text-sm font-medium text-gray-700 mb-4">Logo de la Structure</label>
                    
                    <div class="relative group cursor-pointer w-40 h-40 mb-4">
                        <img 
                            :src="previewLogo || configStore.structureInfo.logo_url || '/placeholder-logo.png'" 
                            class="w-full h-full object-contain rounded-lg bg-white shadow-sm border p-2"
                            alt="Aperçu Logo"
                        />
                        <div class="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <PhotoIcon class="h-8 w-8 text-white" />
                        </div>
                        <input type="file" accept="image/*" @change="handleLogoUpload" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                    </div>
                    
                    <p class="text-xs text-gray-500 text-center">Cliquez pour changer.<br>Format recommandé : PNG transparent.</p>
                </div>

                <div class="md:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-5">
                    
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Dénomination Sociale</label>
                        <input v-model="formStructure.name" type="text" placeholder="Ex: Clinique Saint-Luc" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" required />
                    </div>

                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Slogan / Devise (Apparaît sous le nom)</label>
                        <input v-model="formStructure.slogan" type="text" placeholder="Ex: Votre santé, notre priorité" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" />
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Téléphone Principal</label>
                        <input v-model="formStructure.phone" type="tel" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" />
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Téléphone Secondaire</label>
                        <input v-model="formStructure.phone2" type="tel" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" />
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Adresse Email</label>
                        <input v-model="formStructure.email" type="email" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" />
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Site Web</label>
                        <input v-model="formStructure.website" type="text" placeholder="www.exemple.com" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" />
                    </div>

                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Adresse Physique / Localisation</label>
                        <input v-model="formStructure.address" type="text" placeholder="Quartier, Avenue, Ville" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" />
                    </div>
                    
                    <div>
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Ville</label>
                        <input v-model="formStructure.city" type="text" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" />
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Boite Postale (BP)</label>
                        <input v-model="formStructure.po_box" type="text" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border" />
                    </div>

                    <div class="md:col-span-2 border-t pt-4 mt-2">
                        <h3 class="text-sm font-bold text-gray-700 mb-3">Informations Légales / Fiscales</h3>
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Numéro Contribuable (NIU)</label>
                        <input v-model="formStructure.niu" type="text" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border bg-gray-50" />
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Registre Commerce (RCCM)</label>
                        <input v-model="formStructure.rccm" type="text" class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2.5 border bg-gray-50" />
                    </div>
                </div>
            </div>

            <div class="mt-6 flex justify-end border-t pt-4">
                <button 
                    type="submit"
                    :disabled="isSaving"
                    class="flex items-center px-6 py-2.5 bg-gray-900 text-white rounded-xl hover:bg-gray-800 shadow-lg transition font-medium text-sm disabled:opacity-70 disabled:cursor-not-allowed"
                >
                    <span v-if="isSaving" class="flex items-center">
                        <span class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                        Enregistrement...
                    </span>
                    <span v-else class="flex items-center">
                        <CheckCircleIcon class="h-5 w-5 mr-2" />
                        Enregistrer la Configuration Structure
                    </span>
                </button>
            </div>
        </form>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden transition-all">
      <div 
        @click="openSections.exams = !openSections.exams"
        class="p-6 border-b border-gray-100 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-gray-50 transition"
      >
        <div class="flex items-center">
            <h2 class="text-xl font-bold text-gray-800 mr-4">{{ t('config.exams_title') }}</h2>
            <ChevronDownIcon 
                class="h-6 w-6 text-gray-400 transform transition-transform duration-200 md:hidden"
                :class="{'rotate-180': openSections.exams}"
            />
        </div>
        
        <div class="flex flex-1 md:justify-end space-x-3 w-full md:w-auto transition-all" :class="{'hidden md:flex': !openSections.exams}">
          <div class="relative w-full md:w-64" @click.stop> <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
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
            @click.stop="openExamModal(null)" 
            class="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 shadow-md transition font-semibold text-sm whitespace-nowrap"
          >
            <PlusCircleIcon class="h-5 w-5 mr-2" />
            {{ t('config.add_exam') }}
          </button>

           <ChevronDownIcon 
                class="h-6 w-6 text-gray-400 transform transition-transform duration-200 hidden md:block ml-4"
                :class="{'rotate-180': openSections.exams}"
            />
        </div>
      </div>

      <div v-show="openSections.exams" class="transition-all duration-300 ease-in-out">
        <div v-if="configStore.isLoading && configStore.examens.length === 0" class="p-10 text-center text-gray-500">
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
                <td class="px-6 py-4 text-right space-x-2">
                    <button 
                    @click="openExamModal(exam)"
                    class="text-indigo-600 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg text-xs font-semibold transition inline-flex items-center"
                    >
                    <PencilSquareIcon class="h-4 w-4 mr-1" />
                    {{ t('config.edit') }}
                    </button>
                    <button 
                    @click="handleDeleteExam(exam.id)"
                    class="text-red-600 hover:text-red-900 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg text-xs font-semibold transition inline-flex items-center"
                    >
                    <TrashIcon class="h-4 w-4 mr-1" />
                    {{ t('common.delete') }}
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
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden transition-all h-fit">
            <div 
                @click="openSections.prayers = !openSections.prayers"
                class="p-6 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition flex justify-between items-center"
            >
                <div>
                    <h2 class="text-xl font-bold text-gray-800">{{ t('config.prayers_title') }}</h2>
                    <p class="text-sm text-gray-500 mt-1">{{ t('config.prayers_subtitle') }}</p>
                </div>
                 <ChevronDownIcon 
                    class="h-6 w-6 text-gray-400 transform transition-transform duration-200"
                    :class="{'rotate-180': openSections.prayers}"
                />
            </div>
            <div v-show="openSections.prayers" class="transition-all duration-300 ease-in-out">
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
        </div>
        
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 transition-all h-fit">
            <div 
                @click="openSections.general = !openSections.general"
                class="p-6 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition flex justify-between items-center"
            >
                <div>
                    <h2 class="text-xl font-bold text-gray-800">{{ t('config.general_title') }}</h2>
                    <p class="text-sm text-gray-500 mt-1">{{ t('config.general_subtitle') }}</p>
                </div>
                 <ChevronDownIcon 
                    class="h-6 w-6 text-gray-400 transform transition-transform duration-200"
                    :class="{'rotate-180': openSections.general}"
                />
            </div>
            
            <div v-show="openSections.general" class="transition-all duration-300 ease-in-out">
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
                        :class="isMaintenanceMode ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'"
                        class="px-4 py-2 text-white rounded-lg font-medium shadow-md transition"
                    >
                        {{ isMaintenanceMode ? t('config.deactivate') : t('config.activate') }}
                    </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <ExamFormModal 
      v-if="showExamModal" 
      :examen="selectedExam" 
      @close="showExamModal = false" 
      @saved="onExamSaved" 
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue';
import { useConfigStore } from '@/stores/configStore';
import { useI18n } from 'vue-i18n';
import { 
  PlusCircleIcon, 
  PencilSquareIcon, 
  MagnifyingGlassIcon,
  WrenchScrewdriverIcon, 
  ArrowDownTrayIcon,
  TrashIcon,
  BuildingOfficeIcon,
  PhotoIcon,
  CheckCircleIcon,
  ChevronDownIcon // 🟢 Ajout de l'icône Chevron
} from '@heroicons/vue/24/outline';

import ExamFormModal from '@/components/config/ExamFormModal.vue';

const { t } = useI18n();
const configStore = useConfigStore();

// --- 🟢 ÉTAT POUR LES ACCORDÉONS ---
// Par défaut, la structure et les examens sont ouverts, le reste fermé pour alléger.
const openSections = reactive({
    structure: true,
    exams: true,
    prayers: false,
    general: false
});


// --- ETAT CONFIGURATION STRUCTURE ---
const formStructure = ref({
    name: '', slogan: '', phone: '', phone2: '', email: '', website: '',
    address: '', city: '', po_box: '', niu: '', rccm: ''
});
const logoFile = ref(null);
const previewLogo = ref(null);
const isSaving = ref(false);

// --- ETATS CONFIGURATION GENERALE ---
const showExamModal = ref(false);
const selectedExam = ref(null);
const searchQuery = ref('');
const isMaintenanceMode = ref(false);
const isBackupRunning = ref(false);


// --- CYCLE DE VIE ---
onMounted(async () => {
    await configStore.fetchStructureInfo();
    configStore.fetchExamens();
    configStore.fetchPrayerBooks();
});

watch(() => configStore.structureInfo, (info) => {
    if (info) { formStructure.value = { ...formStructure.value, ...info }; }
}, { deep: true });


// --- LOGIQUE STRUCTURE & LOGO ---
const handleLogoUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
        logoFile.value = file;
        previewLogo.value = URL.createObjectURL(file);
    }
};

const saveStructureConfig = async () => {
    isSaving.value = true;
    try {
        const formData = new FormData();
        Object.keys(formStructure.value).forEach(key => {
            formData.append(key, formStructure.value[key] || '');
        });
        if (logoFile.value) {
            formData.append('logo', logoFile.value);
        }
        await configStore.saveStructureInfo(formData);
        alert("Configuration de la structure enregistrée avec succès !");
    } catch (error) {
        console.error("Erreur save:", error);
        alert("Erreur lors de l'enregistrement: " + error.message);
    } finally {
        isSaving.value = false;
    }
};


// --- LOGIQUE EXAMENS ---
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
  selectedExam.value = exam;
  showExamModal.value = true;
};

const onExamSaved = () => {
  showExamModal.value = false;
  configStore.fetchExamens();
};

const handleDeleteExam = async (id) => {
    if(confirm(t('config.delete_confirmation') || "Supprimer cet élément ?")) {
        await configStore.deleteExamen(id);
    }
};

// --- LOGIQUE SYSTEME ---
const handleBackup = async () => {
  if (isBackupRunning.value) return;
  isBackupRunning.value = true;
  await new Promise(resolve => setTimeout(resolve, 3000)); 
  isBackupRunning.value = false;
  alert(t('config.db_backup') + " terminée.");
};

const toggleMaintenanceMode = async () => {
  isMaintenanceMode.value = !isMaintenanceMode.value;
};

const formatPrice = (price) => {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency', currency: 'XOF', minimumFractionDigits: 0
  }).format(price).replace('XOF', 'FCFA'); 
};
</script>