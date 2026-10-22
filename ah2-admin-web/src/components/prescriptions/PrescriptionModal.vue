<template>
  <!-- Panneau plein ecran sur telephone et tablette, grande fenetre centree sur PC -->
  <FullScreenPanel :title="isEdit ? t('prescriptions.modal.title_edit') : t('prescriptions.modal.title_new')" @close="$emit('close')">

    <form id="prescription-form" @submit.prevent="handleSubmit" class="space-y-4">

      <FormSection :title="t('prescriptions.modal.section_patient')">
        <div class="md:col-span-2">
          <FormField
            id="presc-patient-code"
            :label="t('prescriptions.modal.patient_code')"
            required
            :help="patientId || patientUuid ? patientLookupMessage : t('prescriptions.modal.help_patient_code')"
            :error="patientId || patientUuid ? '' : patientLookupMessage"
            v-slot="{ describedBy, invalid }"
          >
            <input
              id="presc-patient-code"
              v-model="patientCode"
              @blur="lookupPatient"
              type="text"
              required
              :readonly="isEdit || !!prefilledPatient"
              :aria-describedby="describedBy"
              :aria-invalid="invalid"
              :class="[fieldClass, (isEdit || prefilledPatient) ? 'cursor-not-allowed bg-tone-neutral-bg text-ink-muted' : 'bg-white']"
              placeholder="Ex: AH2-000818AQ"
            />
          </FormField>
        </div>
      </FormSection>

      <FormSection :title="t('prescriptions.modal.section_prescription')">
        <div class="md:col-span-2">
          <label for="is_lab_order" class="inline-flex min-h-11 cursor-pointer items-center gap-3 text-base text-ink">
            <input
              id="is_lab_order"
              v-model="form.isLabOrder"
              type="checkbox"
              class="h-5 w-5 rounded-control border-tone-neutral-border accent-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
            />
            {{ t('prescriptions.modal.is_lab_order') }}
          </label>
        </div>

        <template v-if="!form.isLabOrder">
          <div class="md:col-span-2">
            <FormField id="presc-medication" :label="t('prescriptions.modal.medication')" required v-slot="{ describedBy }">
              <input
                id="presc-medication"
                v-model="form.medication"
                type="text"
                required
                :aria-describedby="describedBy"
                placeholder="Ex: Paracétamol 1000mg"
                :class="[fieldClass, 'bg-white']"
              />
            </FormField>
          </div>

          <FormField id="presc-dosage" :label="t('prescriptions.modal.dosage')" required v-slot="{ describedBy }">
            <input
              id="presc-dosage"
              v-model="form.dosage"
              type="text"
              required
              :aria-describedby="describedBy"
              placeholder="Ex: 1000mg"
              :class="[fieldClass, 'bg-white']"
            />
          </FormField>

          <FormField id="presc-frequency" :label="t('prescriptions.modal.frequency')" required :help="t('prescriptions.modal.help_frequency')" v-slot="{ describedBy }">
            <input
              id="presc-frequency"
              v-model="form.frequency"
              type="text"
              required
              :aria-describedby="describedBy"
              placeholder="Ex: 3x / jour"
              :class="[fieldClass, 'bg-white']"
            />
          </FormField>

          <FormField id="presc-duration" :label="t('prescriptions.modal.duration')" required :help="t('prescriptions.modal.help_duration')" v-slot="{ describedBy }">
            <input
              id="presc-duration"
              v-model="form.duration"
              type="text"
              required
              :aria-describedby="describedBy"
              placeholder="Ex: 7 jours"
              :class="[fieldClass, 'bg-white']"
            />
          </FormField>
        </template>

        <template v-else>
          <div class="md:col-span-2">
            <FormField id="presc-exam-filter" :label="t('prescriptions.modal.exams')" v-slot="{ describedBy }">
              <input
                id="presc-exam-filter"
                v-model="examFilter"
                type="text"
                :aria-describedby="describedBy"
                :placeholder="t('prescriptions.modal.exams_filter')"
                :class="[fieldClass, 'mb-2 bg-white']"
              />
              <div class="max-h-56 space-y-1 overflow-y-auto rounded-control border border-tone-neutral-border bg-white p-2">
                <label v-for="exam in filteredExamTypes" :key="exam.id" class="flex min-h-11 cursor-pointer items-center gap-3 text-base text-ink">
                  <input
                    type="checkbox"
                    :value="exam.nom"
                    v-model="form.labExamsList"
                    class="h-5 w-5 rounded-control border-tone-neutral-border accent-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
                  />
                  {{ exam.nom }}
                </label>
                <p v-if="filteredExamTypes.length === 0" class="py-1 text-base text-ink-muted">
                  {{ t('prescriptions.modal.exams_empty') }}
                </p>
              </div>
            </FormField>
          </div>
        </template>
      </FormSection>

      <FormSection :title="t('prescriptions.modal.section_dates')">
        <FormField id="presc-start" :label="t('prescriptions.modal.start_date')" required v-slot="{ describedBy }">
          <input
            id="presc-start"
            v-model="form.startDate"
            type="date"
            required
            :aria-describedby="describedBy"
            :class="[fieldClass, 'bg-white']"
          />
        </FormField>

        <FormField v-if="!form.isLabOrder" id="presc-end" :label="t('prescriptions.modal.end_date')" :help="t('prescriptions.modal.help_end_date')" v-slot="{ describedBy }">
          <input
            id="presc-end"
            v-model="form.endDate"
            type="date"
            :aria-describedby="describedBy"
            :class="[fieldClass, 'bg-white']"
          />
        </FormField>

        <div class="md:col-span-2">
          <FormField id="presc-notes" :label="t('prescriptions.modal.notes')" v-slot="{ describedBy }">
            <textarea
              id="presc-notes"
              v-model="form.notes"
              rows="3"
              :aria-describedby="describedBy"
              :class="[fieldClass, 'bg-white py-2']"
            ></textarea>
          </FormField>
        </div>
      </FormSection>

    </form>

    <!-- Barre d'actions fixe : Enregistrer (principal) et Annuler (discret) -->
    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('prescriptions.modal.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="prescription-form">{{ t('prescriptions.modal.save') }}</AppButton>
      </ActionBar>
    </template>

  </FullScreenPanel>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { usePrescriptionStore } from '@/stores/prescriptionStore';
import { usePatientLookup } from '@/composables/usePatientLookup';
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';

const { t } = useI18n();
const prescriptionStore = usePrescriptionStore();
const emit = defineEmits(['close', 'save']);

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
