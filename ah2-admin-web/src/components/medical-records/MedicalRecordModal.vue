<template>
  <!-- Panneau plein ecran sur telephone et tablette, grande fenetre centree sur PC -->
  <FullScreenPanel :title="isEdit ? t('medicalRecords.modal.title_edit') : t('medicalRecords.modal.title_new')" @close="$emit('close')">

    <form id="medical-record-form" @submit.prevent="handleSubmit" class="space-y-4">

      <FormSection :title="t('medicalRecords.modal.section_patient')">
        <div class="md:col-span-2">
          <FormField
            id="mr-patient-code"
            :label="t('medicalRecords.modal.patient_code')"
            required
            :help="patientId || patientUuid ? patientLookupMessage : t('medicalRecords.modal.help_patient_code')"
            :error="patientId || patientUuid ? '' : patientLookupMessage"
            v-slot="{ describedBy, invalid }"
          >
            <input
              id="mr-patient-code"
              v-model="patientCode"
              @blur="lookupPatient"
              type="text"
              required
              :readonly="isEdit || !!prefilledPatient"
              :aria-describedby="describedBy"
              :aria-invalid="invalid"
              :class="[fieldClass, (isEdit || !!prefilledPatient) ? 'cursor-not-allowed bg-tone-neutral-bg text-ink-muted' : 'bg-white']"
              placeholder="Ex: AH2-000818AQ"
            />
          </FormField>
        </div>
      </FormSection>

      <FormSection :title="t('medicalRecords.modal.section_consultation')">
        <FormField id="mr-date" :label="t('medicalRecords.modal.consultation_date')" required v-slot="{ describedBy }">
          <input id="mr-date" v-model="form.consultationDate" type="date" required :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="mr-motif" :label="t('medicalRecords.modal.motif')" required v-slot="{ describedBy }">
          <select id="mr-motif" v-model="form.motifCode" required :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option value="">{{ t('medicalRecords.modal.motif_none') }}</option>
            <option v-for="m in medicalRecordStore.motifs" :key="m.code" :value="m.code">{{ m.label_fr }}</option>
          </select>
        </FormField>
        <FormField id="mr-severity" :label="t('medicalRecords.modal.severity')" v-slot="{ describedBy }">
          <select id="mr-severity" v-model="form.severity" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option v-for="opt in severityOptions" :key="opt.value" :value="opt.value">{{ t(opt.labelKey) }}</option>
          </select>
        </FormField>
        <FormField id="mr-marital" :label="t('medicalRecords.modal.marital_status')" v-slot="{ describedBy }">
          <select id="mr-marital" v-model="form.maritalStatus" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option v-for="opt in maritalOptions" :key="opt.value" :value="opt.value">{{ t(opt.labelKey) }}</option>
          </select>
        </FormField>
      </FormSection>

      <FormSection :title="t('medicalRecords.modal.section_vitals')" collapsible>
        <FormField id="mr-bp" :label="t('medicalRecords.modal.bp')" :help="t('medicalRecords.modal.help_bp')" v-slot="{ describedBy }">
          <input id="mr-bp" v-model="form.bp" type="text" :aria-describedby="describedBy" placeholder="Ex: 120/80" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="mr-temperature" :label="t('medicalRecords.modal.temperature')" :help="t('medicalRecords.modal.help_temperature')" v-slot="{ describedBy }">
          <input id="mr-temperature" v-model="form.temperature" type="number" step="0.1" inputmode="decimal" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="mr-weight" :label="t('medicalRecords.modal.weight')" :help="t('medicalRecords.modal.help_weight')" v-slot="{ describedBy }">
          <input id="mr-weight" v-model="form.weight" type="number" step="0.1" inputmode="decimal" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="mr-height" :label="t('medicalRecords.modal.height')" :help="t('medicalRecords.modal.help_height')" v-slot="{ describedBy }">
          <input id="mr-height" v-model="form.height" type="number" step="0.1" inputmode="decimal" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
      </FormSection>

      <FormSection :title="t('medicalRecords.modal.section_history')" collapsible>
        <FormField id="mr-history" :label="t('medicalRecords.modal.medical_history')" v-slot="{ describedBy }">
          <textarea id="mr-history" v-model="form.medicalHistory" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white py-2']"></textarea>
        </FormField>
        <FormField id="mr-allergies" :label="t('medicalRecords.modal.allergies')" v-slot="{ describedBy }">
          <textarea id="mr-allergies" v-model="form.allergies" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white py-2']"></textarea>
        </FormField>
      </FormSection>

      <FormSection :title="t('medicalRecords.modal.section_exam')" collapsible>
        <div class="md:col-span-2">
          <FormField id="mr-symptoms" :label="t('medicalRecords.modal.symptoms')" v-slot="{ describedBy }">
            <textarea id="mr-symptoms" v-model="form.symptoms" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white py-2']"></textarea>
          </FormField>
        </div>
      </FormSection>

      <FormSection :title="t('medicalRecords.modal.section_diagnosis')" collapsible>
        <FormField id="mr-diagnosis" :label="t('medicalRecords.modal.diagnosis')" v-slot="{ describedBy }">
          <textarea id="mr-diagnosis" v-model="form.diagnosis" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white py-2']"></textarea>
        </FormField>
        <FormField id="mr-treatment" :label="t('medicalRecords.modal.treatment')" v-slot="{ describedBy }">
          <textarea id="mr-treatment" v-model="form.treatment" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white py-2']"></textarea>
        </FormField>
      </FormSection>

      <FormSection :title="t('medicalRecords.modal.section_notes')" collapsible>
        <div class="md:col-span-2">
          <FormField id="mr-notes" :label="t('medicalRecords.modal.notes')" v-slot="{ describedBy }">
            <textarea id="mr-notes" v-model="form.notes" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white py-2']"></textarea>
          </FormField>
        </div>
      </FormSection>

      <FormSection v-if="!isEdit" :title="t('medicalRecords.modal.section_triage')">
        <div class="md:col-span-2 grid gap-3">
          <label class="inline-flex min-h-11 cursor-pointer items-center">
            <input type="checkbox" v-model="form.needsDoctorReview" class="peer sr-only">
            <div class="relative h-6 w-11 shrink-0 rounded-full bg-tone-neutral-border transition peer-checked:bg-brand-600 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-600 after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:after:translate-x-5"></div>
            <span class="ms-3 text-base font-medium text-ink">{{ t('medicalRecords.modal.needs_doctor_review') }}</span>
          </label>
          <p v-if="!form.needsDoctorReview" class="text-sm text-ink-muted">{{ t('medicalRecords.modal.needs_doctor_review_hint') }}</p>
          <div v-if="form.needsDoctorReview">
            <FormField id="mr-assign" :label="t('medicalRecords.modal.assign_doctor')" :help="t('medicalRecords.modal.assign_doctor_hint')" v-slot="{ describedBy }">
              <select id="mr-assign" v-model="form.assignedDoctorId" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
                <option value="">{{ t('medicalRecords.modal.assign_doctor_pool') }}</option>
                <option v-for="d in doctors" :key="d.user_id" :value="d.user_id">{{ d.full_name }}</option>
              </select>
            </FormField>
          </div>
        </div>
      </FormSection>

    </form>

    <!-- Barre d'actions fixe : Enregistrer (principal) et Annuler (discret) -->
    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('medicalRecords.modal.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="medical-record-form">{{ t('medicalRecords.modal.save') }}</AppButton>
      </ActionBar>
    </template>

  </FullScreenPanel>
</template>

<script setup>
import { reactive, computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { usePatientLookup } from '@/composables/usePatientLookup';
import api from '@/services/api';
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';

const { t } = useI18n();
const medicalRecordStore = useMedicalRecordStore();
const emit = defineEmits(['close', 'save']);

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
  // Parcours « nouveau patient » de l'infirmiere : la case « a examiner par un medecin » est
  // cochee d'office (modifiable). Defaut false : tous les autres usages sont inchanges.
  defaultNeedsDoctorReview: {
    type: Boolean,
    default: false,
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
  needsDoctorReview: props.defaultNeedsDoctorReview,
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
