<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-xs">
    <div class="relative mx-auto w-full max-w-2xl bg-white shadow-2xl rounded-2xl flex flex-col max-h-[90vh]">

      <div class="flex justify-between items-center p-6 border-b border-gray-100">
        <h3 class="text-xl font-bold text-gray-800">
          {{ isEditing ? 'Modifier le patient' : 'Nouveau patient' }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition p-2 rounded-full hover:bg-gray-100">
          <span class="text-2xl leading-none">&times;</span>
        </button>
      </div>

      <div class="p-6 overflow-y-auto custom-scrollbar">
        <form @submit.prevent="handleSubmit" id="patientForm" class="space-y-6">

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Prénom <span class="text-red-500">*</span></label>
              <input v-model="form.firstName" type="text" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Nom <span class="text-red-500">*</span></label>
              <input v-model="form.lastName" type="text" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Date de naissance <span class="text-red-500">*</span></label>
              <input v-model="form.birthDate" type="date" required :max="today" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Genre</label>
              <select v-model="form.gender" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 bg-white">
                <option :value="null">— Non précisé —</option>
                <option value="M">Masculin</option>
                <option value="F">Féminin</option>
                <option value="A">Autre</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Numéro national d'identité</label>
              <input v-model="form.nationalId" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Téléphone</label>
              <input v-model="form.contactPhone" type="tel" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Assurance</label>
              <input v-model="form.assurance" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Résidence</label>
              <input v-model="form.residence" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Nom du père</label>
              <input v-model="form.fatherName" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Nom de la mère</label>
              <input v-model="form.motherName" type="text" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-sm">
            <p class="text-sm text-red-700">{{ errorMessage }}</p>
          </div>

        </form>
      </div>

      <div class="p-6 border-t border-gray-100 flex justify-end gap-3 bg-gray-50 rounded-b-2xl">
        <button type="button" @click="$emit('close')" :disabled="isSaving" class="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition shadow-xs disabled:opacity-50">
          Annuler
        </button>
        <button type="submit" form="patientForm" :disabled="isSaving || !isFormValid" class="px-5 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 font-medium shadow-lg shadow-green-200 transition transform active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed flex items-center">
          <svg v-if="isSaving" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ isEditing ? 'Enregistrer' : 'Créer' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted } from 'vue';

const props = defineProps({
  patientToEdit: { type: Object, default: null },
  errorMessage: { type: String, default: '' },
  isSaving: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'save']);
const isEditing = computed(() => !!props.patientToEdit);
const today = new Date().toISOString().split('T')[0];

const form = reactive({
  firstName: '',
  lastName: '',
  birthDate: '',
  gender: null,
  nationalId: '',
  contactPhone: '',
  assurance: '',
  residence: '',
  fatherName: '',
  motherName: '',
});

onMounted(() => {
  if (props.patientToEdit) {
    const p = props.patientToEdit;
    Object.assign(form, {
      firstName: p.first_name,
      lastName: p.last_name,
      birthDate: p.birth_date,
      gender: p.gender,
      nationalId: p.national_id || '',
      contactPhone: p.contact_phone || '',
      assurance: p.assurance || '',
      residence: p.residence || '',
      fatherName: p.father_name || '',
      motherName: p.mother_name || '',
    });
  }
});

const isFormValid = computed(() => {
  return form.firstName.trim() && form.lastName.trim() && form.birthDate;
});

const handleSubmit = () => {
  if (!isFormValid.value) return;
  emit('save', { ...form });
};
</script>
