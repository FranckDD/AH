<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
    <div class="relative mx-auto p-6 border w-full max-w-2xl shadow-xl rounded-2xl bg-white max-h-[90vh] overflow-y-auto">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('consultations.modal.title_edit') : t('consultations.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            :readonly="isEdit"
            :class="[
              'block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm',
              isEdit ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''
            ]"
            placeholder="Ex: AH2-000818AQ"
          />
          <p v-if="patientLookupMessage" class="text-sm mt-1" :class="patientId ? 'text-green-600' : 'text-red-500'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.type_label') }}</label>
          <select v-model="form.typeConsultation" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
            <option value="Spiritual">{{ t('consultations.type_spiritual') }}</option>
            <option value="FamilyRestoration">{{ t('consultations.type_family_restoration') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.consultation_date') }}</label>
          <input v-model="form.consultationDate" type="datetime-local" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
        </div>

        <template v-if="form.typeConsultation === 'Spiritual'">
          <fieldset class="border border-gray-200 rounded-lg p-4 space-y-4">
            <legend class="text-sm font-semibold text-gray-600 px-1">{{ t('consultations.modal.section_spiritual') }}</legend>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.prayer_book_type') }}</label>
              <select v-model="form.mpType" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm">
                <option value="">{{ t('consultations.modal.prayer_book_none') }}</option>
                <option v-for="pbt in consultationStore.prayerBookTypes" :key="pbt.type_code" :value="pbt.type_code">
                  {{ pbt.label || pbt.type_code }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.psaume') }}</label>
              <input v-model="form.psaume" type="text" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.presc_generic') }}</label>
              <div class="flex gap-4">
                <label v-for="opt in ['Hony', 'Massage', 'Prayer']" :key="opt" class="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" :value="opt" v-model="form.prescGeneric" class="rounded border-gray-300" />
                  {{ opt }}
                </label>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.presc_med_spirituel') }}</label>
              <div class="flex gap-4">
                <label v-for="opt in ['SE', 'TIS', 'AE']" :key="opt" class="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" :value="opt" v-model="form.prescMedSpirituel" class="rounded border-gray-300" />
                  {{ opt }}
                </label>
              </div>
            </div>
          </fieldset>
        </template>

        <template v-else-if="form.typeConsultation === 'FamilyRestoration'">
          <fieldset class="border border-gray-200 rounded-lg p-4 space-y-4">
            <legend class="text-sm font-semibold text-gray-600 px-1">{{ t('consultations.modal.section_family_restoration') }}</legend>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.fr_registered_at') }}</label>
                <input v-model="form.frRegisteredAt" type="date" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.fr_appointment_at') }}</label>
                <input v-model="form.frAppointmentAt" type="date" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.fr_amount_paid') }}</label>
              <input v-model="form.frAmountPaid" type="number" min="0" step="0.01" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.fr_observation') }}</label>
              <textarea v-model="form.frObservation" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
            </div>
          </fieldset>
        </template>

        <fieldset class="border border-gray-200 rounded-lg p-4 space-y-4">
          <legend class="text-sm font-semibold text-gray-600 px-1">{{ t('consultations.modal.section_common') }}</legend>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('consultations.modal.notes') }}</label>
            <textarea v-model="form.notes" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm"></textarea>
          </div>
        </fieldset>

        <div class="flex justify-end gap-3 pt-2">
          <button type="button" @click="$emit('close')" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 text-sm font-medium">
            {{ t('consultations.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 text-sm font-medium">
            {{ t('consultations.modal.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { usePatientLookup } from '@/composables/usePatientLookup.js';
import { useConsultationStore } from '@/stores/consultationStore';

const { t } = useI18n();
const consultationStore = useConsultationStore();

const props = defineProps({ consultation: { type: Object, default: null } });
const emit = defineEmits(['close', 'save']);

const isEdit = computed(() => !!props.consultation);

const {
  patientCode, patientId, patientName, patientLookupMessage,
  lookupPatient, ensureLookup, setFromExisting,
} = usePatientLookup(() => t('consultations.modal.patient_not_found'));

const form = reactive({
  typeConsultation: 'Spiritual',
  consultationDate: '',
  mpType: '',
  psaume: '',
  prescGeneric: [],
  prescMedSpirituel: [],
  frRegisteredAt: '',
  frAppointmentAt: '',
  frAmountPaid: '',
  frObservation: '',
  notes: '',
});

let isInitializing = true;

watch(() => form.typeConsultation, (newType) => {
  if (isInitializing) return;
  if (newType === 'Spiritual') {
    form.frRegisteredAt = '';
    form.frAppointmentAt = '';
    form.frAmountPaid = '';
    form.frObservation = '';
  } else if (newType === 'FamilyRestoration') {
    form.mpType = '';
    form.psaume = '';
    form.prescGeneric = [];
    form.prescMedSpirituel = [];
  }
});

onMounted(() => {
  consultationStore.fetchPrayerBookTypes();

  if (props.consultation) {
    const rec = props.consultation;
    setFromExisting({
      patientId: rec.patient_id,
      code: rec.patient?.code_patient,
      firstName: rec.patient?.first_name,
      lastName: rec.patient?.last_name,
    });
    form.typeConsultation = rec.type_consultation || 'Spiritual';
    form.consultationDate = rec.consultation_date ? rec.consultation_date.slice(0, 16) : '';
    form.mpType = rec.mp_type || '';
    form.psaume = rec.psaume || '';
    form.frRegisteredAt = rec.fr_registered_at ? rec.fr_registered_at.slice(0, 10) : '';
    form.frAppointmentAt = rec.fr_appointment_at ? rec.fr_appointment_at.slice(0, 10) : '';
    form.frAmountPaid = rec.fr_amount_paid || '';
    form.frObservation = rec.fr_observation || '';
    form.notes = rec.notes || '';
    form.prescGeneric = rec.presc_generic || [];
    form.prescMedSpirituel = rec.presc_med_spirituel || [];
  }
  isInitializing = false;
});

async function handleSubmit() {
  await ensureLookup();

  if (!patientId.value) {
    alert(t('consultations.modal.patient_not_found'));
    return;
  }
  if (!form.typeConsultation) {
    alert(t('consultations.modal.type_required'));
    return;
  }

  emit('save', {
    patientId: patientId.value,
    typeConsultation: form.typeConsultation,
    prescGeneric: form.prescGeneric,
    prescMedSpirituel: form.prescMedSpirituel,
    mpType: form.mpType || null,
    psaume: form.psaume || null,
    notes: form.notes || null,
    frRegisteredAt: form.frRegisteredAt || null,
    frAppointmentAt: form.frAppointmentAt || null,
    frAmountPaid: form.frAmountPaid !== '' && form.frAmountPaid !== null ? form.frAmountPaid : null,
    frObservation: form.frObservation || null,
    consultationDate: form.consultationDate || null,
  });
}
</script>
