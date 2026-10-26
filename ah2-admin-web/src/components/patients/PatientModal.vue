<template>
  <!-- Panneau plein ecran sur telephone et tablette, grande fenetre centree sur PC -->
  <FullScreenPanel :title="isEditing ? $t('screens.patientForm.edit_title') : $t('screens.patientForm.new_title')" @close="$emit('close')">

    <form @submit.prevent="handleSubmit" id="patientForm" class="space-y-4">

      <FormSection :title="$t('patients.modal.section_identity')">
        <FormField id="patient-first-name" :label="$t('screens.patientForm.first_name')" required v-slot="{ describedBy }">
          <input id="patient-first-name" v-model="form.firstName" type="text" required :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="patient-last-name" :label="$t('screens.patientForm.last_name')" required v-slot="{ describedBy }">
          <input id="patient-last-name" v-model="form.lastName" type="text" required :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="patient-birth-date" :label="$t('screens.patientForm.birth_date')" required v-slot="{ describedBy }">
          <input id="patient-birth-date" v-model="form.birthDate" type="date" required :max="today" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="patient-gender" :label="$t('screens.patientForm.gender')" v-slot="{ describedBy }">
          <select id="patient-gender" v-model="form.gender" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option :value="null">{{ $t('screens.patientForm.gender_unspecified') }}</option>
            <option value="M">{{ $t('screens.patientForm.male') }}</option>
            <option value="F">{{ $t('screens.patientForm.female') }}</option>
            <option value="A">{{ $t('screens.patientForm.other') }}</option>
          </select>
        </FormField>
        <div class="md:col-span-2">
          <FormField id="patient-national-id" :label="$t('screens.patientForm.national_id')" v-slot="{ describedBy }">
            <input id="patient-national-id" v-model="form.nationalId" type="text" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
          </FormField>
        </div>
      </FormSection>

      <FormSection :title="$t('patients.modal.section_contact')">
        <FormField id="patient-phone" :label="$t('screens.patientForm.phone')" v-slot="{ describedBy }">
          <input id="patient-phone" v-model="form.contactPhone" type="tel" inputmode="tel" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="patient-residence" :label="$t('screens.patientForm.residence')" v-slot="{ describedBy }">
          <input id="patient-residence" v-model="form.residence" type="text" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <div class="md:col-span-2">
          <FormField id="patient-assurance" :label="$t('screens.patientForm.insurance')" v-slot="{ describedBy }">
            <input id="patient-assurance" v-model="form.assurance" type="text" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
          </FormField>
        </div>
      </FormSection>

      <FormSection :title="$t('patients.modal.section_family')">
        <FormField id="patient-father" :label="$t('screens.patientForm.father')" v-slot="{ describedBy }">
          <input id="patient-father" v-model="form.fatherName" type="text" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
        <FormField id="patient-mother" :label="$t('screens.patientForm.mother')" v-slot="{ describedBy }">
          <input id="patient-mother" v-model="form.motherName" type="text" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
      </FormSection>

      <div v-if="errorMessage" role="alert" class="flex items-start gap-2 rounded-control border p-3 text-base" :class="toneClasses('danger')">
        <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <p>{{ errorMessage }}</p>
      </div>

    </form>

    <!-- Barre d'actions fixe : Creer / Enregistrer (principal) et Annuler (discret) -->
    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" :disabled="isSaving" @click="$emit('close')">{{ $t('screens.patientForm.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="patientForm" :disabled="isSaving || !isFormValid" :loading="isSaving">
          {{ isEditing ? $t('screens.patientForm.save') : $t('screens.patientForm.create') }}
        </AppButton>
      </ActionBar>
    </template>

  </FullScreenPanel>
</template>

<script setup>
import { todayLocalISO } from '@/utils/localDate';
import { reactive, computed, onMounted } from 'vue';
import { ExclamationCircleIcon } from '@heroicons/vue/20/solid';
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const props = defineProps({
  patientToEdit: { type: Object, default: null },
  errorMessage: { type: String, default: '' },
  isSaving: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'save']);
const isEditing = computed(() => !!props.patientToEdit);
const today = todayLocalISO();

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
