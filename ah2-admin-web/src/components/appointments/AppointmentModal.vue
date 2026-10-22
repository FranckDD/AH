<template>
  <!-- Panneau plein ecran sur telephone, fenetre centree des sm -->
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="appointment-modal-title">
    <div class="app-refonte flex max-h-dvh w-full max-w-lg flex-col overflow-hidden bg-white shadow-card sm:rounded-card">

      <div class="flex items-center justify-between gap-3 border-b border-tone-neutral-border px-4 py-3 md:px-5">
        <h3 id="appointment-modal-title" class="text-xl font-bold text-ink">
          {{ isEdit ? t('appointments.modal.title_edit') : t('appointments.modal.title_new') }}
        </h3>
        <button
          type="button"
          @click="$emit('close')"
          class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-ink-muted hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
          :aria-label="t('ui.close')"
        >
          <XMarkIcon class="h-6 w-6" aria-hidden="true" />
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="flex min-h-0 flex-1 flex-col">
        <div class="flex-1 space-y-4 overflow-y-auto p-4 md:p-5">

          <FormSection :title="t('appointments.modal.section_patient')">
            <div class="md:col-span-2">
              <FormField
                id="appt-patient-code"
                :label="t('appointments.modal.patient_code')"
                required
                :help="patientId ? patientLookupMessage : t('appointments.modal.patient_code_help')"
                :error="patientId ? '' : patientLookupMessage"
                v-slot="{ describedBy, invalid }"
              >
                <input
                  id="appt-patient-code"
                  v-model="patientCode"
                  @blur="lookupPatient"
                  type="text"
                  required
                  :readonly="isEdit"
                  :aria-describedby="describedBy"
                  :aria-invalid="invalid"
                  placeholder="Ex: AH2-000818AQ"
                  :class="[inputClass, isEdit ? 'cursor-not-allowed bg-tone-neutral-bg text-ink-muted' : 'bg-white']"
                />
              </FormField>
            </div>
          </FormSection>

          <FormSection :title="t('appointments.modal.section_appointment')">
            <FormField id="appt-specialty" :label="t('appointments.modal.specialty')" v-slot="{ describedBy }">
              <select id="appt-specialty" v-model="form.specialty" :aria-describedby="describedBy" :class="[inputClass, 'bg-white']">
                <option value="">{{ t('appointments.modal.specialty_none') }}</option>
                <option v-for="spec in appointmentStore.specialties" :key="spec" :value="spec">{{ spec }}</option>
              </select>
            </FormField>

            <FormField id="appt-doctor" :label="t('appointments.modal.doctor')" v-slot="{ describedBy }">
              <select id="appt-doctor" v-model="form.doctorId" :aria-describedby="describedBy" :class="[inputClass, 'bg-white']">
                <option value="">{{ t('appointments.modal.doctor_unassigned') }}</option>
                <option v-for="d in doctors" :key="d.user_id" :value="d.user_id">{{ d.full_name }}</option>
              </select>
            </FormField>

            <FormField id="appt-date" :label="t('appointments.modal.date')" required v-slot="{ describedBy }">
              <input
                id="appt-date"
                v-model="form.appointmentDate"
                type="date"
                required
                :aria-describedby="describedBy"
                :class="[inputClass, 'bg-white']"
              />
            </FormField>

            <FormField id="appt-time" :label="t('appointments.modal.time')" required v-slot="{ describedBy }">
              <select id="appt-time" v-model="form.appointmentTime" required :aria-describedby="describedBy" :class="[inputClass, 'bg-white']">
                <option value="" disabled>--:--</option>
                <option v-for="slot in timeSlots" :key="slot" :value="slot">{{ slot }}</option>
              </select>
            </FormField>

            <div class="md:col-span-2">
              <FormField id="appt-reason" :label="t('appointments.modal.reason')" v-slot="{ describedBy }">
                <textarea
                  id="appt-reason"
                  v-model="form.reason"
                  rows="2"
                  :aria-describedby="describedBy"
                  placeholder="Ex: Consultation de suivi..."
                  :class="[inputClass, 'bg-white py-2']"
                ></textarea>
              </FormField>
            </div>
          </FormSection>
        </div>

        <ActionBar>
          <template #secondary>
            <AppButton variant="ghost" @click="$emit('close')">{{ t('appointments.modal.cancel') }}</AppButton>
          </template>
          <AppButton type="submit">{{ t('appointments.modal.save') }}</AppButton>
        </ActionBar>
      </form>

    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAppointmentStore } from '@/stores/appointmentStore';
import { db, waitForInitialSync } from '@/powersync-client/client';
import api from '@/services/api';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormField, FormSection, ActionBar } from '@/components/ui';

// Style commun des champs : zone tactile >= 44 px, focus visible.
const inputClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const { t } = useI18n();
const appointmentStore = useAppointmentStore();
const emit = defineEmits(['close', 'save']);

const props = defineProps({
  appointment: {
    type: Object,
    default: null,
  },
  // Pre-remplit la date a la creation (vue calendrier - clic sur un jour
  // vide, voir AppointmentsCalendar.vue). Ignore en mode edition
  // (props.appointment garde toujours la priorite).
  initialDate: {
    type: String,
    default: '',
  },
});

const isEdit = computed(() => !!props.appointment);

const patientCode = ref('');
const patientId = ref(null);
const patientName = ref('');
const patientLookupMessage = ref('');

const form = reactive({
  specialty: '',
  appointmentDate: '',
  appointmentTime: '',
  reason: '',
  doctorId: '',
});

const doctors = ref([]);

// Creneaux de 30 min, 08:00-18:30 - port exact de book_appoint_view.py
// (f"{h:02d}:{m:02d}" for h in range(8, 19) for m in (0, 30))
const timeSlots = computed(() => {
  const slots = [];
  for (let h = 8; h <= 18; h++) {
    for (const m of [0, 30]) {
      slots.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
    }
  }
  return slots;
});

// Recherche patient sur la base locale PowerSync (patients_lookup) au lieu
// d'un appel REST direct - fonctionne desormais aussi hors ligne, ce qui
// est le but meme de ce pilote (creer un RDV sans reseau implique de
// pouvoir retrouver le patient sans reseau non plus).
async function lookupPatient() {
  const raw = patientCode.value.trim();
  if (!raw) {
    patientId.value = null;
    patientName.value = '';
    patientLookupMessage.value = '';
    return;
  }

  let code = raw.toUpperCase();
  if (!code.startsWith('AH2-')) {
    code = `AH2-${code}`;
  }
  patientCode.value = code;

  try {
    // La connexion PowerSync n'est plus attendue au login (elle bloquait
    // l'ouverture de la fenetre pendant plusieurs secondes) - c'est donc ici,
    // au seul endroit qui lit vraiment les tables synchronisees, qu'on
    // s'assure que le premier sync est termine. Sans cela un code patient
    // parfaitement valide repondrait "patient introuvable" tant que
    // patients_lookup n'est pas encore peuplee (bug du chantier 4).
    await waitForInitialSync();

    // getOptional() (pas .get()) : .get() leve une exception si aucune
    // ligne ne correspond, ce qui ferait tomber un code patient
    // simplement inconnu dans le catch generique ci-dessous - avec le
    // meme message que "patient introuvable" que la vraie panne locale
    // (base PowerSync pas encore prete, etc.), rendant les deux cas
    // indistinguables en diagnostic. getOptional() renvoie null sur
    // absence de ligne, laissant le catch reserve aux vraies erreurs.
    const match = await db.getOptional(
      'SELECT patient_id, first_name, last_name FROM patients_lookup WHERE code_patient = ?',
      [code]
    );
    if (!match) {
      patientId.value = null;
      patientName.value = '';
      patientLookupMessage.value = t('appointments.modal.patient_not_found');
      return;
    }
    patientId.value = match.patient_id;
    patientName.value = [match.first_name, match.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  } catch (err) {
    console.error('Erreur recherche patient (locale):', err);
    patientId.value = null;
    patientName.value = '';
    patientLookupMessage.value = t('appointments.modal.patient_lookup_error');
  }
}

onMounted(async () => {
  if (props.appointment) {
    const appt = props.appointment;
    patientId.value = appt.patient_id || null;
    patientCode.value = appt.code_patient || '';
    patientName.value = [appt.first_name, appt.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
    form.specialty = appt.specialty || '';
    form.appointmentDate = (appt.appointment_date || '').substring(0, 10);
    form.appointmentTime = (appt.appointment_time || '').substring(0, 5);
    form.reason = appt.reason || '';
    form.doctorId = appt.doctor_id || '';
  } else if (props.initialDate) {
    form.appointmentDate = props.initialDate;
  }

  try {
    const resp = await api.get('/doctor-dashboard/doctors');
    doctors.value = resp.data || [];
  } catch (e) {
    console.error('Erreur chargement liste medecins:', e);
  }
});

async function handleSubmit() {
  if (!patientId.value && patientCode.value.trim()) {
    await lookupPatient();
  }

  if (!patientId.value) {
    alert(t('appointments.modal.patient_not_found'));
    return;
  }

  emit('save', {
    patientId: patientId.value,
    specialty: form.specialty,
    appointmentDate: form.appointmentDate,
    appointmentTime: form.appointmentTime,
    reason: form.reason,
    doctorId: form.doctorId || null,
  });
}
</script>
