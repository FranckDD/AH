<template>
  <!-- Panneau plein ecran sur telephone et tablette, grande fenetre centree sur PC -->
  <FullScreenPanel :title="isEdit ? t('consultations.modal.title_edit') : t('consultations.modal.title_new')" @close="$emit('close')">

    <form id="consultation-form" @submit.prevent="handleSubmit" class="space-y-4">

      <FormSection :title="t('consultationsScreens.section_patient')">
        <div class="md:col-span-2">
          <FormField
            id="cs-patient-code"
            :label="t('consultations.modal.patient_code')"
            required
            :error="patientId ? '' : patientLookupMessage"
            :help="patientId ? patientLookupMessage : ''"
            v-slot="{ describedBy, invalid }"
          >
            <input
              id="cs-patient-code"
              v-model="patientCode"
              @blur="lookupPatient"
              type="text"
              required
              :readonly="isEdit"
              :aria-describedby="describedBy"
              :aria-invalid="invalid"
              :class="[fieldClass, isEdit ? 'cursor-not-allowed bg-tone-neutral-bg text-ink-muted' : 'bg-white']"
              placeholder="Ex: AH2-000818AQ"
            />
          </FormField>
        </div>
      </FormSection>

      <FormSection :title="t('consultations.modal.type_label')">
        <FormField id="cs-type" :label="t('consultations.modal.type_label')" required v-slot="{ describedBy }">
          <select id="cs-type" v-model="form.typeConsultation" required :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option value="Spiritual">{{ t('consultations.type_spiritual') }}</option>
            <option value="FamilyRestoration">{{ t('consultations.type_family_restoration') }}</option>
          </select>
        </FormField>
        <FormField id="cs-date" :label="t('consultations.modal.consultation_date')" v-slot="{ describedBy }">
          <input id="cs-date" v-model="form.consultationDate" type="datetime-local" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
      </FormSection>

      <template v-if="form.typeConsultation === 'Spiritual'">
        <FormSection :title="t('consultations.modal.section_spiritual')">
          <FormField id="cs-mp" :label="t('consultations.modal.prayer_book_type')" v-slot="{ describedBy }">
            <select id="cs-mp" v-model="form.mpType" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
              <option value="">{{ t('consultations.modal.prayer_book_none') }}</option>
              <option v-for="pbt in consultationStore.prayerBookTypes" :key="pbt.type_code" :value="pbt.type_code">
                {{ pbt.label || pbt.type_code }}
              </option>
            </select>
          </FormField>

          <FormField id="cs-psaume" :label="t('consultations.modal.psaume')" v-slot="{ describedBy }">
            <input id="cs-psaume" v-model="form.psaume" type="text" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
          </FormField>

          <fieldset class="md:col-span-2">
            <legend class="mb-1 text-base font-medium text-ink">{{ t('consultations.modal.presc_generic') }}</legend>
            <div class="flex flex-wrap gap-x-6">
              <label v-for="opt in ['Hony', 'Massage', 'Prayer']" :key="opt" class="flex min-h-11 cursor-pointer items-center gap-2 text-base text-ink">
                <input type="checkbox" :value="opt" v-model="form.prescGeneric" class="h-5 w-5 rounded-control border-tone-neutral-border accent-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600" />
                {{ opt }}
              </label>
            </div>
          </fieldset>

          <fieldset class="md:col-span-2">
            <legend class="mb-1 text-base font-medium text-ink">{{ t('consultations.modal.presc_med_spirituel') }}</legend>
            <div class="flex flex-wrap gap-x-6">
              <label v-for="opt in ['SE', 'TIS', 'AE']" :key="opt" class="flex min-h-11 cursor-pointer items-center gap-2 text-base text-ink">
                <input type="checkbox" :value="opt" v-model="form.prescMedSpirituel" class="h-5 w-5 rounded-control border-tone-neutral-border accent-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600" />
                {{ opt }}
              </label>
            </div>
          </fieldset>
        </FormSection>
      </template>

      <template v-else-if="form.typeConsultation === 'FamilyRestoration'">
        <FormSection :title="t('consultations.modal.section_family_restoration')">
          <FormField id="cs-fr-registered" :label="t('consultations.modal.fr_registered_at')" required v-slot="{ describedBy }">
            <input id="cs-fr-registered" v-model="form.frRegisteredAt" type="date" required :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
          </FormField>
          <FormField id="cs-fr-appointment" :label="t('consultations.modal.fr_appointment_at')" required v-slot="{ describedBy }">
            <input id="cs-fr-appointment" v-model="form.frAppointmentAt" type="date" required :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
          </FormField>
          <FormField id="cs-fr-amount" :label="t('consultations.modal.fr_amount_paid')" required v-slot="{ describedBy }">
            <input id="cs-fr-amount" v-model="form.frAmountPaid" type="number" min="0" step="0.01" required inputmode="decimal" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
          </FormField>
          <div class="md:col-span-2">
            <FormField id="cs-fr-observation" :label="t('consultations.modal.fr_observation')" v-slot="{ describedBy }">
              <textarea id="cs-fr-observation" v-model="form.frObservation" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white py-2']"></textarea>
            </FormField>
          </div>
        </FormSection>
      </template>

      <FormSection :title="t('consultations.modal.section_common')">
        <div class="md:col-span-2">
          <FormField id="cs-notes" :label="t('consultations.modal.notes')" v-slot="{ describedBy }">
            <textarea id="cs-notes" v-model="form.notes" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white py-2']"></textarea>
          </FormField>
        </div>
      </FormSection>

    </form>

    <!-- Barre d'actions fixe : Enregistrer (principal) et Annuler (discret) -->
    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('consultations.modal.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="consultation-form">{{ t('consultations.modal.save') }}</AppButton>
      </ActionBar>
    </template>

  </FullScreenPanel>
</template>

<script setup>
import { notifyText } from '@/utils/notify';
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { usePatientLookup } from '@/composables/usePatientLookup.js';
import { useConsultationStore } from '@/stores/consultationStore';
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';

const { t } = useI18n();
const consultationStore = useConsultationStore();

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
    notifyText(t('consultations.modal.patient_not_found'));
    return;
  }
  if (!form.typeConsultation) {
    notifyText(t('consultations.modal.type_required'));
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
