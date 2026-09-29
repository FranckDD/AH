<template>
  <div class="fixed inset-0 bg-gray-600/50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-md shadow-xl rounded-2xl bg-white">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('appointments.modal.title_edit') : t('appointments.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            :readonly="isEdit"
            placeholder="Ex: AH2-000818AQ"
            :class="[
              'block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm',
              isEdit ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''
            ]"
          />
          <p class="mt-1 text-xs" :class="patientId ? 'text-emerald-600' : 'text-gray-400'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.specialty') }}</label>
          <select v-model="form.specialty" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm">
            <option value="">{{ t('appointments.modal.specialty_none') }}</option>
            <option v-for="spec in appointmentStore.specialties" :key="spec" :value="spec">{{ spec }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.doctor') }}</label>
          <select v-model="form.doctorId" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm">
            <option value="">{{ t('appointments.modal.doctor_unassigned') }}</option>
            <option v-for="d in doctors" :key="d.user_id" :value="d.user_id">{{ d.full_name }}</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.date') }}</label>
            <input
              v-model="form.appointmentDate"
              type="date"
              required
              class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.time') }}</label>
            <select v-model="form.appointmentTime" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm">
              <option value="" disabled>--:--</option>
              <option v-for="slot in timeSlots" :key="slot" :value="slot">{{ slot }}</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.reason') }}</label>
          <textarea
            v-model="form.reason"
            rows="2"
            placeholder="Ex: Consultation de suivi..."
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
          ></textarea>
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-xs">
            {{ t('appointments.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition bg-emerald-600 hover:bg-emerald-700">
            {{ t('appointments.modal.save') }}
          </button>
        </div>
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
