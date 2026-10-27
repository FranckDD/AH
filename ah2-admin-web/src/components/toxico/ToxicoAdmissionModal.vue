<template>
  <FullScreenPanel :title="t('toxico.admission.title')" accent @close="$emit('close')">
    <form id="toxico-admission-form" @submit.prevent="handleSubmit" class="grid gap-4">

      <FormSection :title="t('toxico.admission.section_patient')">
        <div class="grid gap-3 md:col-span-2">
          <div v-if="!showNewPatientForm && !selectedExistingPatient" class="grid gap-2">
            <FormField id="tox-adm-search" :label="t('toxicoScreens.search_existing')" v-slot="{ describedBy }">
              <input id="tox-adm-search" v-model="searchQuery" @input="onSearchInput" type="text" :placeholder="t('toxicoScreens.search_existing')"
                     :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <p v-if="isSearching" role="status" class="text-sm text-ink-muted">{{ t('toxicoScreens.searching') }}</p>
            <ul v-if="searchResults.length" :aria-label="t('toxicoScreens.search_results')" class="max-h-56 divide-y divide-tone-neutral-border overflow-y-auto rounded-control border border-tone-neutral-border">
              <li v-for="p in searchResults" :key="p.patient_id">
                <button type="button" @click="selectExistingPatient(p)"
                        class="flex min-h-11 w-full flex-wrap items-center gap-x-2 px-3 py-2 text-left text-base hover:bg-action-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600">
                  <span class="font-medium text-ink">{{ p.first_name }} {{ p.last_name }}</span>
                  <span class="text-sm text-ink-muted">{{ t('toxicoScreens.patient_meta', { code: p.code_patient, date: p.birth_date }) }}</span>
                </button>
              </li>
            </ul>
            <AppButton variant="secondary" size="sm" :icon="UserPlusIcon" class="justify-self-start" @click="startNewPatient">{{ t('toxicoScreens.new_patient') }}</AppButton>
          </div>

          <div v-if="selectedExistingPatient" class="flex items-center justify-between gap-3 rounded-control border border-action-600 bg-action-50 px-3 py-2">
            <span class="min-w-0 break-words text-base font-medium text-action-700">{{ selectedPatientLabel }}</span>
            <AppButton variant="ghost" size="sm" @click="clearExistingPatient">{{ t('toxicoScreens.change_patient') }}</AppButton>
          </div>

          <p v-if="dossierCheck === 'loading'" role="status" class="text-sm text-ink-muted">{{ t('toxico.stays.checking') }}</p>
          <div v-else-if="dossierCheck === 'readmission'" role="status" class="grid gap-1 rounded-card border p-3 text-base" :class="toneClasses('warning')">
            <p class="font-semibold">{{ t('toxico.stays.readmission_banner', { n: nextStayNumber }) }}</p>
            <p>{{ t('toxico.stays.readmission_phase_reset') }}</p>
            <p v-if="lastDischargeDate">{{ t('toxico.stays.readmission_min_date', { date: lastDischargeDate }) }}</p>
          </div>
          <div v-else-if="dossierCheck === 'active'" role="alert" class="rounded-card border p-3 text-base" :class="toneClasses('danger')">
            {{ t('toxico.stays.already_active') }}
          </div>
          <div v-else-if="dossierCheck === 'error'" role="alert" class="flex flex-wrap items-center gap-2 rounded-card border p-3 text-base" :class="toneClasses('danger')">
            <span>{{ t('toxico.stays.check_failed') }}</span>
            <AppButton variant="secondary" size="sm" @click="checkToxicoDossier(selectedExistingPatient.patient_id)">{{ t('toxico.stays.retry') }}</AppButton>
          </div>
        </div>

        <template v-if="selectedExistingPatient || showNewPatientForm">
          <FormField id="tox-adm-date" :label="t('toxico.admission.date')" required class="md:col-span-2" v-slot="{ describedBy }">
            <input id="tox-adm-date" v-model="form.admissionDate" type="date" required :max="today" :min="minAdmissionDate || undefined" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>

          <FormField id="tox-adm-substance" :label="t('toxico.admission.substance')" required v-slot="{ describedBy }">
            <select id="tox-adm-substance" v-model="form.substance" required :aria-describedby="describedBy" :class="fieldClass">
              <option value="Alcool">{{ t('toxico.substances.alcohol') }}</option>
              <option value="Cannabis">{{ t('toxico.substances.cannabis') }}</option>
              <option value="Opioïdes">{{ t('toxico.substances.opioids') }}</option>
              <option value="Cocaïne">{{ t('toxico.substances.cocaine') }}</option>
              <option value="Polytoxicomanie">{{ t('toxico.substances.poly') }}</option>
              <option value="Autre">{{ t('toxicoScreens.substance_other') }}</option>
            </select>
          </FormField>
          <FormField id="tox-adm-psy" :label="t('toxico.admission.psychologist')" required v-slot="{ describedBy }">
            <select id="tox-adm-psy" v-model="form.psychologist" required :aria-describedby="describedBy" :class="fieldClass">
              <option :value="null" disabled selected>{{ t('toxicoScreens.select_placeholder') }}</option>
              <option v-for="psy in psychologistsList" :key="psy.id" :value="psy.id">{{ psy.name }}</option>
            </select>
          </FormField>
        </template>

        <template v-if="showNewPatientForm">
          <FormField id="tox-adm-first" :label="t('toxico.admission.firstname')" required v-slot="{ describedBy }">
            <input id="tox-adm-first" v-model="form.firstName" type="text" required :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="tox-adm-last" :label="t('toxico.admission.lastname')" required v-slot="{ describedBy }">
            <input id="tox-adm-last" v-model="form.lastName" type="text" required :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="tox-adm-dob" :label="t('toxico.admission.dob')" required v-slot="{ describedBy }">
            <input id="tox-adm-dob" v-model="form.dob" type="date" required :max="maxDateFormatted" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="tox-adm-sex" :label="t('toxico.admission.sex')" required v-slot="{ describedBy }">
            <select id="tox-adm-sex" v-model="form.gender" required :aria-describedby="describedBy" :class="fieldClass">
              <option value="" disabled>{{ t('toxicoScreens.select_placeholder') }}</option>
              <option value="M">{{ t('toxico.admission.sex_male') }}</option>
              <option value="F">{{ t('toxico.admission.sex_female') }}</option>
            </select>
          </FormField>
          <FormField id="tox-adm-mother" :label="t('toxico.admission.mothers_name')" required v-slot="{ describedBy }">
            <input id="tox-adm-mother" v-model="form.mothersName" type="text" required :placeholder="t('toxicoScreens.mothers_name_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <FormField id="tox-adm-address" :label="t('toxico.admission.address')" v-slot="{ describedBy }">
            <div class="relative">
              <MapPinIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
              <input id="tox-adm-address" v-model="form.address" type="text" :aria-describedby="describedBy" :class="[fieldClass, 'pl-10']" />
            </div>
          </FormField>
          <FormField id="tox-adm-contact" :label="t('toxico.admission.contact')" v-slot="{ describedBy }">
            <input id="tox-adm-contact" v-model="form.contact" type="tel" :placeholder="t('toxicoScreens.phone_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </template>
      </FormSection>

      <FormSection :title="t('toxico.admission.section_guardian')">
        <FormField id="tox-adm-guardian" :label="t('toxico.admission.guardian_name')" required v-slot="{ describedBy }">
          <input id="tox-adm-guardian" v-model="form.guardianName" type="text" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="tox-adm-guardian-contact" :label="t('toxico.admission.guardian_contact')" required v-slot="{ describedBy }">
          <input id="tox-adm-guardian-contact" v-model="form.guardianContact" type="tel" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <div class="md:col-span-2">
          <p class="mb-1.5 text-base font-medium text-ink">{{ t('toxico.admission.consent_file') }}</p>
          <label for="tox-adm-file"
                 class="flex cursor-pointer flex-col items-center gap-1 rounded-card border-2 border-dashed border-tone-neutral-border bg-white px-6 py-5 text-center hover:bg-tone-neutral-bg focus-within:outline-2 focus-within:outline-offset-1 focus-within:outline-brand-600">
            <PaperClipIcon class="h-8 w-8 text-ink-muted" aria-hidden="true" />
            <span class="break-all text-base font-medium text-action-700">{{ fileName || t('toxico.admission.upload_placeholder') }}</span>
            <span class="text-sm text-ink-muted">{{ t('toxicoScreens.file_hint') }}</span>
            <input id="tox-adm-file" name="file-upload" type="file" class="sr-only" @change="handleFileUpload" accept=".pdf,.jpg,.png" />
          </label>
        </div>
      </FormSection>

      <FormField id="tox-adm-notes" :label="t('toxico.admission.notes')" v-slot="{ describedBy }">
        <textarea id="tox-adm-notes" v-model="form.notes" rows="3" :placeholder="t('toxicoScreens.notes_placeholder')" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>

      <p v-if="errorMessage" role="alert" class="flex items-start gap-2 whitespace-pre-line rounded-card border p-3 text-base" :class="toneClasses('danger')">
        <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        {{ errorMessage }}
      </p>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="secondary" :disabled="isLoading" @click="$emit('close')">{{ t('toxico.admission.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="toxico-admission-form" :icon="CheckCircleIcon" :disabled="isLoading || !isFormValid" :loading="isLoading">
          {{ isLoading ? t('toxicoScreens.processing') : t('toxico.admission.submit') }}
        </AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { reactive, ref, onMounted, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { ToxicoGateway } from '@/services/ToxicoGateway';
import { apiErrorMessage, readmissionPrefill } from '@/utils/toxicoStays';
import { formatDateDMY, todayLocalISO } from '@/utils/localDate';
import { displayName } from '@/utils/toxicoDischarged';
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import {
    UserPlusIcon,
    CheckCircleIcon,
    MapPinIcon,
    PaperClipIcon,
    ExclamationCircleIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const emit = defineEmits(['close', 'save']);
// Réadmission depuis l'onglet "Sortis" : { patient_id, first_name, last_name, code_patient }
const props = defineProps({
    preselectedPatient: { type: Object, default: null },
});
const toxicoStore = useToxicoStore();

const today = todayLocalISO();
const maxDate = new Date();
maxDate.setFullYear(maxDate.getFullYear() - 10); // Minimum 10 ans
const maxDateFormatted = todayLocalISO(maxDate);

// Style commun des champs (zone tactile >= 44 px, focus visible).
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const fileName = ref('');
const isLoading = ref(false);
const errorMessage = ref('');

const psychologistsList = computed(() => toxicoStore.psychologists);

onMounted(() => {
    toxicoStore.fetchPsychologists();
});

const form = reactive({
    firstName: '',
    lastName: '',
    dob: '',
    mothersName: '',
    gender: '',
    address: '',
    contact: '',
    admissionDate: today,
    substance: 'Alcool',
    psychologist: null, 
    guardianName: '',
    guardianContact: '',
    consentFile: null,
    notes: ''
});

// Recherche d'un patient existant (chantier 6, tache 4)
const searchQuery = ref('');
const searchResults = ref([]);
const isSearching = ref(false);
const selectedExistingPatient = ref(null);
const showNewPatientForm = ref(false);
const selectedPatientLabel = computed(() => {
    const p = selectedExistingPatient.value;
    if (!p) return '';
    const name = displayName(p.first_name, p.last_name);
    return p.code_patient ? `${name} (${p.code_patient})` : name;
});

let searchTimeout = null;
const onSearchInput = () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        if (searchQuery.value.trim().length < 2) {
            searchResults.value = [];
            return;
        }
        isSearching.value = true;
        searchResults.value = await toxicoStore.searchExistingPatients(searchQuery.value);
        isSearching.value = false;
    }, 300);
};

// Etat du dossier toxico du patient rattache : 'none' (pas de dossier, 404),
// 'readmission' (dossier inactif), 'active' (deja suivi -> le backend refusera 409).
const dossierCheck = ref('');
const existingDossier = ref(null);
const lastClosedStay = computed(() => {
    const stays = existingDossier.value?.stays || [];
    return [...stays].filter((s) => !s.is_open).sort((a, b) => b.stay_number - a.stay_number)[0] || null;
});
const nextStayNumber = computed(() => {
    const stays = existingDossier.value?.stays || [];
    return (stays.length ? Math.max(...stays.map((s) => s.stay_number)) : 0) + 1;
});
// Regle backend : la nouvelle admission ne precede pas la derniere sortie.
const minAdmissionDate = computed(() =>
    dossierCheck.value === 'readmission' && lastClosedStay.value?.discharge_date
        ? String(lastClosedStay.value.discharge_date).slice(0, 10) : '');
const lastDischargeDate = computed(() => {
    if (!minAdmissionDate.value) return '';
    return formatDateDMY(minAdmissionDate.value);
});

const checkToxicoDossier = async (patientId) => {
    dossierCheck.value = 'loading';
    existingDossier.value = null;
    try {
        const res = await ToxicoGateway.getPatientDetails(patientId);
        if (selectedExistingPatient.value?.patient_id !== patientId) return;
        existingDossier.value = res.data;
        dossierCheck.value = res.data?.isActive ? 'active' : 'readmission';
        if (dossierCheck.value === 'readmission') {
            // reprise du sejour precedent : substance et tuteur (modifiables), plutot qu'un formulaire remis a zero
            const prefill = readmissionPrefill(res.data);
            if (prefill.substance) form.substance = prefill.substance;
            if (prefill.guardianName && !form.guardianName) form.guardianName = prefill.guardianName;
            if (prefill.psychologist && !form.psychologist) form.psychologist = prefill.psychologist;
            if (prefill.guardianContact && !form.guardianContact) form.guardianContact = prefill.guardianContact;
        }
        if (minAdmissionDate.value && form.admissionDate < minAdmissionDate.value) {
            form.admissionDate = minAdmissionDate.value > today ? today : minAdmissionDate.value;
        }
    } catch (e) {
        if (selectedExistingPatient.value?.patient_id !== patientId) return;
        dossierCheck.value = e?.response?.status === 404 ? 'none' : 'error';
    }
};

const selectExistingPatient = (patient) => {
    selectedExistingPatient.value = patient;
    showNewPatientForm.value = false;
    searchResults.value = [];
    checkToxicoDossier(patient.patient_id);
};

const clearExistingPatient = () => {
    selectedExistingPatient.value = null;
    dossierCheck.value = '';
    existingDossier.value = null;
};

onMounted(() => {
    if (props.preselectedPatient?.patient_id) selectExistingPatient(props.preselectedPatient);
});

const startNewPatient = () => {
    clearExistingPatient();
    showNewPatientForm.value = true;
};

// Validation du formulaire
const isFormValid = computed(() => {
    const patientOk = selectedExistingPatient.value || (
        form.firstName.trim() && form.lastName.trim() && form.dob && form.mothersName.trim() && form.gender
    );
    const dossierOk = !selectedExistingPatient.value || ['none', 'readmission'].includes(dossierCheck.value);
    return patientOk && dossierOk &&
           form.admissionDate &&
           form.substance &&
           form.psychologist &&
           form.guardianName.trim() &&
           form.guardianContact.trim();
});

// Watcher pour reset les erreurs
watch(form, () => {
    errorMessage.value = '';
});

const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
        // Validation de la taille du fichier (5MB max)
        if (file.size > 5 * 1024 * 1024) {
            errorMessage.value = "Le fichier est trop volumineux (max 5MB)";
            return;
        }
        fileName.value = file.name; // Pour l'affichage
        form.consentFile = file; 
    }
};

const handleSubmit = async () => {
    //console.log("=".repeat(60));
    //console.log("📤 TOXICO ADMISSION - Début de l'envoi");
    //console.log("=".repeat(60));
    
    // Validation
    if (!isFormValid.value) {
        errorMessage.value = "Veuillez remplir tous les champs obligatoires (*)";
        return;
    }

    // Validation des dates (uniquement pertinent pour un nouveau patient)
    const admissionDate = new Date(form.admissionDate);
    const todayDate = new Date();

    if (admissionDate > todayDate) {
        errorMessage.value = "La date d'admission ne peut pas être dans le futur";
        return;
    }

    if (minAdmissionDate.value && form.admissionDate < minAdmissionDate.value) {
        errorMessage.value = t('toxico.stays.errors.admission_before_discharge', { date: lastDischargeDate.value });
        return;
    }

    if (!selectedExistingPatient.value) {
        const dobDate = new Date(form.dob);

        if (dobDate > todayDate) {
            errorMessage.value = "La date de naissance ne peut pas être dans le futur";
            return;
        }

        if (dobDate > admissionDate) {
            errorMessage.value = "La date de naissance ne peut pas être après la date d'admission";
            return;
        }
    }

    if (isLoading.value) return;

    isLoading.value = true;
    errorMessage.value = '';

    // 🟢 Préparation du payload avec validation
    const payload = {
        admissionDate: form.admissionDate,
        substance: form.substance,
        psychologist: parseInt(form.psychologist, 10),
        guardianName: form.guardianName.trim(),
        guardianContact: form.guardianContact.trim(),
        consentFile: form.consentFile || "",
        notes: form.notes?.trim() || ""
    };

    if (selectedExistingPatient.value) {
        payload.patientId = selectedExistingPatient.value.patient_id;
    } else {
        payload.firstName = form.firstName.trim();
        payload.lastName = form.lastName.trim();
        payload.dob = form.dob;
        payload.mothersName = form.mothersName.trim();
        payload.gender = form.gender;
        payload.address = form.address?.trim() || "";
        payload.contact = form.contact?.trim() || "";
    }

    // Log détaillé
    //console.log("📋 Payload préparé:", JSON.stringify(payload, null, 2));
    

    try {
        //console.log("🔄 Appel à toxicoStore.addPatient...");
        const result = await toxicoStore.addPatient(payload);
        
        console.log("✅ Admission réussie!");
        emit('save', { isReadmission: !!result?.is_readmission, stayNumber: result?.stay_number ?? null }); 
        emit('close'); 
        
    } catch (error) {
        console.error("❌ Erreur lors de l'admission:", error);
        
        // Gestion détaillée des erreurs
        if (error.response) {
            console.error("📊 Détails de l'erreur:", {
                status: error.response.status,
                data: error.response.data,
                headers: error.response.headers
            });
            
            if (error.response.status === 422) {
                // Erreur de validation Pydantic
                const details = error.response.data.detail;
                if (Array.isArray(details)) {
                    const errors = details.map(err => {
                        const field = err.loc.join('.');
                        return `${field}: ${err.msg}`;
                    });
                    errorMessage.value = `Erreurs de validation:\n${errors.join('\n')}`;
                } else {
                    errorMessage.value = `Erreur: ${details}`;
                }
            } else if (error.response.status === 409) {
                errorMessage.value = apiErrorMessage(error, t('toxico.stays.already_active'));
            } else if (error.response.status === 400) {
                errorMessage.value = error.response.data.detail || "Données invalides";
            } else if (error.response.status === 401) {
                errorMessage.value = "Session expirée. Veuillez vous reconnecter.";
                // Redirection pourrait être ajoutée ici
            } else {
                errorMessage.value = `Erreur serveur (${error.response.status}): ${error.response.data.detail || 'Veuillez réessayer'}`;
            }
        } else if (error.request) {
            errorMessage.value = "Erreur réseau. Veuillez vérifier votre connexion.";
            console.error("🌐 Erreur réseau:", error.request);
        } else {
            errorMessage.value = error.message || "Une erreur inattendue est survenue";
            console.error("⚠️ Erreur inattendue:", error.message);
        }
        
        // Garder la modale ouverte pour permettre la correction
    } finally {
        isLoading.value = false;
        //console.log("=".repeat(60));
        //console.log("📤 TOXICO ADMISSION - Fin du traitement");
        //console.log("=".repeat(60));
    }
};
</script>