<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
    <div class="relative mx-auto p-6 border w-full max-w-2xl shadow-xl rounded-2xl bg-white my-8">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('medicalRecords.modal.title_edit') : t('medicalRecords.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-6">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            :readonly="isEdit || !!prefilledPatient"
            :class="[
              'block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm',
              (isEdit || !!prefilledPatient) ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''
            ]"
            placeholder="Ex: AH2-000818AQ"
          />
          <p class="mt-1 text-xs" :class="patientId ? 'text-emerald-600' : 'text-gray-400'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div>
          <h4 class="text-sm font-bold text-gray-500 uppercase mb-3">{{ t('medicalRecords.modal.section_consultation') }}</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.consultation_date') }}</label>
              <input v-model="form.consultationDate" type="date" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.motif') }}</label>
              <select v-model="form.motifCode" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
                <option value="">{{ t('medicalRecords.modal.motif_none') }}</option>
                <option v-for="m in medicalRecordStore.motifs" :key="m.code" :value="m.code">{{ m.label_fr }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.severity') }}</label>
              <select v-model="form.severity" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
                <option v-for="opt in severityOptions" :key="opt.value" :value="opt.value">{{ t(opt.labelKey) }}</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-4 mt-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.marital_status') }}</label>
              <select v-model="form.maritalStatus" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
                <option v-for="opt in maritalOptions" :key="opt.value" :value="opt.value">{{ t(opt.labelKey) }}</option>
              </select>
            </div>
          </div>
        </div>

        <div>
          <h4 class="text-sm font-bold text-gray-500 uppercase mb-3">{{ t('medicalRecords.modal.section_vitals') }}</h4>
          <div class="grid grid-cols-4 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.bp') }}</label>
              <input v-model="form.bp" type="text" placeholder="Ex: 120/80" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.temperature') }}</label>
              <input v-model="form.temperature" type="number" step="0.1" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.weight') }}</label>
              <input v-model="form.weight" type="number" step="0.1" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.height') }}</label>
              <input v-model="form.height" type="number" step="0.1" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>
          </div>
        </div>

        <div>
          <h4 class="text-sm font-bold text-gray-500 uppercase mb-3">{{ t('medicalRecords.modal.section_notes') }}</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.medical_history') }}</label>
              <textarea v-model="form.medicalHistory" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.allergies') }}</label>
              <textarea v-model="form.allergies" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.symptoms') }}</label>
              <textarea v-model="form.symptoms" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.diagnosis') }}</label>
              <textarea v-model="form.diagnosis" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.treatment') }}</label>
              <textarea v-model="form.treatment" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.notes') }}</label>
              <textarea v-model="form.notes" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
          </div>
        </div>

        <div v-if="!isEdit">
          <h4 class="text-sm font-bold text-gray-500 uppercase mb-3">{{ t('medicalRecords.modal.section_triage') }}</h4>
          <label class="inline-flex items-center cursor-pointer mb-3">
            <input type="checkbox" v-model="form.needsDoctorReview" class="sr-only peer">
            <div class="relative w-11 h-6 bg-gray-200 peer-focus:outline-hidden peer-focus:ring-4 peer-focus:ring-teal-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:inset-s-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal-600"></div>
            <span class="ms-3 text-sm font-medium text-gray-900">{{ t('medicalRecords.modal.needs_doctor_review') }}</span>
          </label>
          <p v-if="!form.needsDoctorReview" class="text-xs text-gray-400 mb-1">{{ t('medicalRecords.modal.needs_doctor_review_hint') }}</p>
          <div v-if="form.needsDoctorReview">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('medicalRecords.modal.assign_doctor') }}</label>
            <select v-model="form.assignedDoctorId" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
              <option value="">{{ t('medicalRecords.modal.assign_doctor_pool') }}</option>
              <option v-for="d in doctors" :key="d.user_id" :value="d.user_id">{{ d.full_name }}</option>
            </select>
            <p class="text-xs text-gray-400 mt-1">{{ t('medicalRecords.modal.assign_doctor_hint') }}</p>
          </div>
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-xs">
            {{ t('medicalRecords.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition bg-teal-600 hover:bg-teal-700">
            {{ t('medicalRecords.modal.save') }}
          </button>
        </div>
      </form>

    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { usePatientLookup } from '@/composables/usePatientLookup';
import api from '@/services/api';

const { t } = useI18n();
const medicalRecordStore = useMedicalRecordStore();
const emit = defineEmits(['close', 'save']);

const props = defineProps({
  record: {
    type: Object,
    default: null,
  },
  prefilledPatient: {
    type: Object,
    default: null,
  },
  appointmentId: {
    type: Number,
    default: null,
  },
});

const isEdit = computed(() => !!props.record);

const {
  patientCode,
  patientId,
  patientUuid,
  patientName,
  patientLookupMessage,
  lookupPatient,
  ensureLookup,
  setFromExisting,
} = usePatientLookup(() => t('medicalRecords.modal.patient_not_found'));

const today = new Date().toISOString().substring(0, 10);

const form = reactive({
  consultationDate: today,
  motifCode: '',
  maritalStatus: 'Single',
  severity: 'low',
  bp: '',
  temperature: '',
  weight: '',
  height: '',
  medicalHistory: '',
  allergies: '',
  symptoms: '',
  diagnosis: '',
  treatment: '',
  notes: '',
  needsDoctorReview: false,
  assignedDoctorId: '',
});

const doctors = ref([]);

const maritalOptions = [
  { value: 'Single', labelKey: 'medicalRecords.modal.marital_single' },
  { value: 'Married', labelKey: 'medicalRecords.modal.marital_married' },
  { value: 'Divorced', labelKey: 'medicalRecords.modal.marital_divorced' },
  { value: 'Widowed', labelKey: 'medicalRecords.modal.marital_widowed' },
];

const severityOptions = [
  { value: 'low', labelKey: 'medicalRecords.severity_low' },
  { value: 'medium', labelKey: 'medicalRecords.severity_medium' },
  { value: 'high', labelKey: 'medicalRecords.severity_high' },
];

onMounted(async () => {
  if (!medicalRecordStore.motifs.length) {
    medicalRecordStore.fetchMotifs();
  }

  if (props.record) {
    const rec = props.record;
    setFromExisting({
      patientId: rec.patient_id || rec.patient?.patient_id || null,
      patientUuid: rec.patient_uuid || null,
      code: rec.patient?.code_patient || '',
      firstName: rec.patient?.first_name,
      lastName: rec.patient?.last_name,
    });
    form.consultationDate = (rec.consultation_date || '').substring(0, 10);
    form.motifCode = rec.motif_code || '';
    form.maritalStatus = rec.marital_status || 'Single';
    form.severity = rec.severity || 'low';
    form.bp = rec.bp || '';
    form.temperature = rec.temperature ?? '';
    form.weight = rec.weight ?? '';
    form.height = rec.height ?? '';
    form.medicalHistory = rec.medical_history || '';
    form.allergies = rec.allergies || '';
    form.symptoms = rec.symptoms || '';
    form.diagnosis = rec.diagnosis || '';
    form.treatment = rec.treatment || '';
    form.notes = rec.notes || '';
  }

  if (!props.record && props.prefilledPatient) {
    setFromExisting(props.prefilledPatient);
  }

  try {
    const resp = await api.get('/doctor-dashboard/doctors');
    doctors.value = resp.data || [];
  } catch (e) {
    console.error('Erreur chargement liste medecins:', e);
  }
});

function parseVital(value, min, max, errorKey) {
  if (value === '' || value === null || value === undefined) return { ok: true, value: null };
  const num = Number(value);
  if (Number.isNaN(num) || num < min || num >= max) {
    alert(t(errorKey));
    return { ok: false };
  }
  return { ok: true, value: num };
}

async function handleSubmit() {
  await ensureLookup();

  if (!patientId.value && !patientUuid.value) {
    alert(t('medicalRecords.modal.patient_not_found'));
    return;
  }

  if (!form.motifCode) {
    alert(t('medicalRecords.modal.motif_required'));
    return;
  }

  const temp = parseVital(form.temperature, 30, 45, 'medicalRecords.modal.temperature_range');
  if (!temp.ok) return;
  const weight = parseVital(form.weight, 0, 1000, 'medicalRecords.modal.weight_range');
  if (!weight.ok) return;
  const height = parseVital(form.height, 30, 250, 'medicalRecords.modal.height_range');
  if (!height.ok) return;

  emit('save', {
    patientId: patientId.value,
    patientUuid: patientUuid.value,
    appointmentId: props.appointmentId,
    consultationDate: form.consultationDate,
    motifCode: form.motifCode,
    maritalStatus: form.maritalStatus,
    severity: form.severity,
    bp: form.bp,
    temperature: temp.value,
    weight: weight.value,
    height: height.value,
    medicalHistory: form.medicalHistory,
    allergies: form.allergies,
    symptoms: form.symptoms,
    diagnosis: form.diagnosis,
    treatment: form.treatment,
    notes: form.notes,
    needsDoctorReview: form.needsDoctorReview,
    assignedDoctorId: form.needsDoctorReview ? (form.assignedDoctorId || null) : null,
  });
}
</script>