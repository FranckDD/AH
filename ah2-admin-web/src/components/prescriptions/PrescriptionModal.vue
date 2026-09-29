<template>
  <div class="fixed inset-0 bg-gray-600/50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-lg shadow-xl rounded-2xl bg-white">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('prescriptions.modal.title_edit') : t('prescriptions.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            :readonly="!!prefilledPatient"
            :class="[
              'block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm',
              prefilledPatient ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''
            ]"
            placeholder="Ex: AH2-000818AQ"
          />
          <p class="mt-1 text-xs" :class="patientId ? 'text-emerald-600' : 'text-gray-400'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div class="flex items-center">
          <input
            id="is_lab_order"
            v-model="form.isLabOrder"
            type="checkbox"
            class="h-4 w-4 text-purple-600 border-gray-300 rounded-sm focus:ring-purple-500"
          />
          <label for="is_lab_order" class="ml-2 block text-sm text-gray-700">
            {{ t('prescriptions.modal.is_lab_order') }}
          </label>
        </div>

        <template v-if="!form.isLabOrder">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.medication') }}</label>
            <input
              v-model="form.medication"
              type="text"
              required
              placeholder="Ex: Paracétamol 1000mg"
              class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.dosage') }}</label>
              <input
                v-model="form.dosage"
                type="text"
                required
                placeholder="Ex: 1000mg"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.frequency') }}</label>
              <input
                v-model="form.frequency"
                type="text"
                required
                placeholder="Ex: 3x / jour"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.duration') }}</label>
              <input
                v-model="form.duration"
                type="text"
                required
                placeholder="Ex: 7 jours"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.end_date') }}</label>
              <input
                v-model="form.endDate"
                type="date"
                class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
          </div>
        </template>

        <template v-else>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.exams') }}</label>
            <input
              v-model="examFilter"
              type="text"
              :placeholder="t('prescriptions.modal.exams_filter')"
              class="block w-full px-3 py-2 border border-gray-300 rounded-lg mb-2 focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
            />
            <div class="max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-2 space-y-1">
              <label v-for="exam in filteredExamTypes" :key="exam.id" class="flex items-center text-sm py-0.5">
                <input
                  type="checkbox"
                  :value="exam.nom"
                  v-model="form.labExamsList"
                  class="h-4 w-4 text-purple-600 border-gray-300 rounded-sm focus:ring-purple-500 mr-2"
                />
                {{ exam.nom }}
              </label>
              <p v-if="filteredExamTypes.length === 0" class="text-xs text-gray-400 italic py-1">
                {{ t('prescriptions.modal.exams_empty') }}
              </p>
            </div>
          </div>
        </template>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.start_date') }}</label>
          <input
            v-model="form.startDate"
            type="date"
            required
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('prescriptions.modal.notes') }}</label>
          <textarea
            v-model="form.notes"
            rows="2"
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
          ></textarea>
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-xs">
            {{ t('prescriptions.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition bg-purple-600 hover:bg-purple-700">
            {{ t('prescriptions.modal.save') }}
          </button>
        </div>
      </form>

    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { usePrescriptionStore } from '@/stores/prescriptionStore';
import { usePatientLookup } from '@/composables/usePatientLookup';

const { t } = useI18n();
const prescriptionStore = usePrescriptionStore();
const emit = defineEmits(['close', 'save']);

const props = defineProps({
  prescription: {
    type: Object,
    default: null,
  },
  prefilledPatient: {
    type: Object,
    default: null,
  },
  // [Number, String] : un id local (uuid, cree hors ligne par
  // medicalRecordStore.createMedicalRecord - voir Tache 2) est une chaine,
  // pas un entier. Number seul produirait un avertissement Vue console a
  // chaque enchainement consultation->prescription pour medecin/nurse.
  prefilledMedicalRecordId: {
    type: [Number, String],
    default: null,
  },
});

const isEdit = computed(() => !!props.prescription);

const {
  patientCode,
  patientId,
  patientUuid,
  patientName,
  patientLookupMessage,
  lookupPatient,
  ensureLookup,
  setFromExisting,
} = usePatientLookup(() => t('prescriptions.modal.patient_not_found'));
const examFilter = ref('');
const medicalRecordId = ref(null);

const today = new Date().toISOString().substring(0, 10);

const form = reactive({
  isLabOrder: false,
  medication: '',
  dosage: '',
  frequency: '',
  duration: '',
  startDate: today,
  endDate: '',
  notes: '',
  labExamsList: [],
});

const filteredExamTypes = computed(() => {
  const q = examFilter.value.trim().toLowerCase();
  if (!q) return prescriptionStore.examTypes;
  return prescriptionStore.examTypes.filter((e) => e.nom.toLowerCase().includes(q));
});

onMounted(() => {
  if (!prescriptionStore.examTypes.length) {
    prescriptionStore.fetchExamTypes();
  }

  if (props.prescription) {
    const presc = props.prescription;
    setFromExisting({
      patientId: presc.patient_id || presc.patient?.patient_id || null,
      patientUuid: presc.patient_uuid || null,
      code: presc.patient?.code_patient || '',
      firstName: presc.patient?.first_name,
      lastName: presc.patient?.last_name,
    });
    medicalRecordId.value = presc.medical_record_id || null;
    form.isLabOrder = !!presc.is_lab_order;
    form.medication = presc.medication || '';
    form.dosage = presc.dosage || '';
    form.frequency = presc.frequency || '';
    form.duration = presc.duration || '';
    form.startDate = (presc.start_date || '').substring(0, 10);
    form.endDate = (presc.end_date || '').substring(0, 10);
    form.notes = presc.notes || '';
    form.labExamsList = Array.isArray(presc.lab_exams_list) ? [...presc.lab_exams_list] : [];
  }

  if (!props.prescription && props.prefilledPatient) {
    setFromExisting(props.prefilledPatient);
  }

  if (!props.prescription && props.prefilledMedicalRecordId) {
    medicalRecordId.value = props.prefilledMedicalRecordId;
  }
});

async function handleSubmit() {
  await ensureLookup();

  if (!patientId.value && !patientUuid.value) {
    alert(t('prescriptions.modal.patient_not_found'));
    return;
  }

  if (!form.isLabOrder && !form.medication.trim()) {
    alert(t('prescriptions.modal.medication_required'));
    return;
  }

  if (form.isLabOrder && form.labExamsList.length === 0) {
    alert(t('prescriptions.modal.exams_required'));
    return;
  }

  if (!form.isLabOrder && form.endDate && form.startDate > form.endDate) {
    alert(t('prescriptions.modal.date_order_error'));
    return;
  }

  emit('save', {
    patientId: patientId.value,
    patientUuid: patientUuid.value,
    medicalRecordId: medicalRecordId.value,
    isLabOrder: form.isLabOrder,
    medication: form.isLabOrder ? '' : form.medication,
    dosage: form.isLabOrder ? '' : form.dosage,
    frequency: form.isLabOrder ? '' : form.frequency,
    duration: form.isLabOrder ? '' : form.duration,
    startDate: form.startDate,
    endDate: form.isLabOrder ? '' : form.endDate,
    notes: form.notes,
    labExamsList: form.isLabOrder ? form.labExamsList : [],
  });
}
</script>
