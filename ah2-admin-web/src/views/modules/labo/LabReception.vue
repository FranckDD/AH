<template>
  <div class="h-full overflow-y-auto p-4 text-sm md:p-6 [&_table]:text-sm [&_dd]:text-sm">
    <div class="mx-auto grid max-w-5xl gap-6 pb-6" id="top-anchor">

      <PageHeader :title="$t('lab.reception.title')" :subtitle="$t('lab.reception.subtitle')" />

      <p v-if="labStore.successMessage" role="status" class="flex items-center gap-2 rounded-card border p-4 text-sm" :class="toneClasses('success')">
        <CheckCircleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
        <span class="font-medium">{{ labStore.successMessage || $t('lab.reception.success_message') }}</span>
      </p>
      <p v-if="labStore.successMessage && (labStore.lastDossier || labStore.lastDossierPending)" class="-mt-3 text-sm font-medium text-ink" data-testid="lab-dossier-state">
        {{ labStore.lastDossier ? $t('labScreens.dossier_assigned_receipt', { n: labStore.lastDossier }) : $t('labScreens.dossier_pending_receipt') }}
      </p>

      <!-- Patient -->
      <AppCard :title="$t('lab.reception.section1_title')" class="relative z-30">
        <template #actions>
          <div role="group" :aria-label="$t('labScreens.mode_label')" class="flex gap-2">
            <AppButton :variant="mode === 'internal' ? 'primary' : 'secondary'" :aria-pressed="mode === 'internal'" @click="setMode('internal')">
              {{ $t('lab.reception.mode_internal') }}
            </AppButton>
            <AppButton :variant="mode === 'external' ? 'primary' : 'secondary'" :aria-pressed="mode === 'external'" @click="setMode('external')">
              {{ $t('lab.reception.mode_external') }}
            </AppButton>
          </div>
        </template>

        <div v-if="mode === 'internal'" class="grid gap-4">
          <div v-if="!selectedPatient" class="relative">
            <FormField id="lab-reception-search" :label="$t('labScreens.search_label')" v-slot="{ describedBy }">
              <input id="lab-reception-search" v-model="searchQuery" type="text" autocomplete="off" :placeholder="$t('lab.reception.search_placeholder')"
                     :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>

            <div v-if="showResults" class="absolute z-50 mt-2 max-h-80 w-full overflow-y-auto rounded-card border border-tone-neutral-border bg-white shadow-card">
              <p v-if="labStore.loading" role="status" class="flex items-center justify-center gap-2 px-4 py-6 text-sm text-ink-muted">
                <ArrowPathIcon class="h-5 w-5 animate-spin" aria-hidden="true" />
                {{ $t('labScreens.searching') }}
              </p>
              <ul v-else-if="labStore.searchResults && labStore.searchResults.length > 0" class="divide-y divide-tone-neutral-border">
                <li v-for="p in labStore.searchResults" :key="p.prescription_id ?? `inv-${p.id}`">
                  <button type="button" @click="selectInternalPatient(p)"
                          class="flex min-h-11 w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600">
                    <span class="min-w-0">
                      <span class="block break-words text-sm font-semibold text-ink">{{ p.nom }}</span>
                      <span class="flex items-center gap-1 text-sm text-ink-muted">
                        <BeakerIcon class="h-4 w-4 shrink-0" aria-hidden="true" />
                        <template v-if="p.exams_prescribed && p.exams_prescribed.length">{{ $t('labScreens.exams_prescribed_count', { n: p.exams_prescribed.length }) }}</template>
                        <template v-if="p.invoiced_exams && p.invoiced_exams.length">{{ (p.exams_prescribed && p.exams_prescribed.length) ? ', ' : '' }}{{ $t('labScreens.invoiced_count', { n: p.invoiced_exams.length }) }}</template>
                        <template v-if="!(p.exams_prescribed && p.exams_prescribed.length) && !(p.invoiced_exams && p.invoiced_exams.length)">{{ $t('labScreens.prescription_empty') }}</template>
                      </span>
                    </span>
                    <StatusBadge tone="neutral" :label="String(p.patient_code)" />
                  </button>
                </li>
              </ul>
              <p v-else role="status" class="px-4 py-6 text-center text-sm text-ink-muted">{{ $t('lab.reception.no_results') }}</p>
            </div>
          </div>

          <div v-else class="flex flex-col gap-3 rounded-card border border-brand-600 bg-brand-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div class="flex items-center gap-4">
              <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xl font-bold uppercase text-white" aria-hidden="true">
                {{ selectedPatient.nom.charAt(0) }}
              </span>
              <div>
                <h3 class="text-lg font-bold text-ink">{{ selectedPatient.nom }}</h3>
                <p class="text-sm text-ink-muted">{{ $t('lab.reception.patient_internal_label') }} #{{ selectedPatient.patient_code }}</p>
                <p v-if="autoImportedCount > 0" class="mt-1 flex items-center gap-1 text-sm font-medium text-tone-success-text">
                  <CheckCircleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
                  {{ $t('labScreens.imported_count', { n: autoImportedCount }) }}
                </p>
                <p v-if="invoicedImportedCount > 0" class="mt-1 flex items-center gap-1 text-sm font-medium text-tone-success-text">
                  <CheckCircleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
                  {{ $t('labScreens.invoiced_imported', { n: invoicedImportedCount }) }}
                </p>
              </div>
            </div>
            <AppButton variant="secondary" @click="resetPatient">{{ $t('lab.reception.change_patient') }}</AppButton>
          </div>

          <p v-if="selectedPatient && internalAgeLabel" class="text-sm font-medium text-ink" data-testid="internal-age">
            {{ $t('pregnancy.internal_age', { label: internalAgeLabel }) }}
          </p>

          <!-- Grossesse du dossier patient (lecture seule ici), SA de la demande modifiable -->
          <fieldset v-if="showInternalPregnancy" class="grid gap-4 rounded-card border border-tone-neutral-border p-4 md:grid-cols-2" data-testid="pregnancy-block-internal">
            <legend class="px-2 text-sm font-semibold text-ink">{{ $t('pregnancy.block_title') }}</legend>
            <p class="text-sm text-ink-muted md:col-span-2">{{ $t('pregnancy.read_only_note') }}</p>
            <dl class="grid gap-1 text-sm md:col-span-2">
              <div><dt class="inline font-medium">{{ $t('pregnancy.status_label') }} :</dt> <dd class="inline">{{ $t('pregnancy.status_' + (selectedPatient.pregnancy_status || 'inconnu')) }}</dd></div>
              <div v-if="selectedPatient.expected_delivery_date"><dt class="inline font-medium">{{ $t('pregnancy.dpa_short') }} :</dt> <dd class="inline">{{ frDate(selectedPatient.expected_delivery_date) }}</dd></div>
              <div v-if="selectedPatient.pregnancy_program_number"><dt class="inline font-medium">{{ $t('pregnancy.program_label_short') }} :</dt> <dd class="inline">{{ selectedPatient.pregnancy_program_number }}</dd></div>
            </dl>
            <FormField id="lab-int-status" :label="$t('pregnancy.request_status_label')" :help="$t('pregnancy.request_status_help')" v-slot="{ describedBy }">
              <select id="lab-int-status" v-model="internalStatus" :aria-describedby="describedBy" :class="fieldClass" data-testid="internal-request-status">
                <option v-for="st in PREGNANCY_STATUSES" :key="st" :value="st">{{ $t('pregnancy.status_' + st) }}</option>
              </select>
            </FormField>
            <template v-if="internalStatus === 'enceinte'">
              <FormField id="lab-int-ga" :label="$t('pregnancy.ga_label')" :help="gaInvalid ? $t('pregnancy.ga_invalid') : $t('pregnancy.ga_help')" v-slot="{ describedBy }">
                <input id="lab-int-ga" v-model="gaWeeks" type="number" min="0" max="45" step="1" inputmode="numeric" :aria-describedby="describedBy" :aria-invalid="gaInvalid" :class="fieldClass" />
              </FormField>
              <div v-if="gaSuggestion !== null" class="flex flex-col justify-end gap-2 text-sm">
                <p class="text-ink-muted" data-testid="ga-suggestion">{{ $t('pregnancy.ga_suggested', { n: gaSuggestion }) }}</p>
                <AppButton v-if="String(gaWeeks) !== String(gaSuggestion)" variant="secondary" @click="gaWeeks = String(gaSuggestion)">{{ $t('pregnancy.ga_use_suggested', { n: gaSuggestion }) }}</AppButton>
              </div>
            </template>
          </fieldset>
        </div>

        <div v-else class="grid gap-4">
          <div class="grid gap-4 md:grid-cols-2">
            <FormField id="lab-ext-name" :label="$t('lab.reception.ext_name_label')" v-slot="{ describedBy }">
              <input id="lab-ext-name" v-model="extForm.full_name" type="text" :placeholder="$t('labScreens.ext_name_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField id="lab-ext-gender" :label="$t('lab.reception.ext_gender_label')" v-slot="{ describedBy }">
              <select id="lab-ext-gender" v-model="extForm.gender" :aria-describedby="describedBy" :class="fieldClass">
                <option value="M">{{ $t('lab.gender.m') }}</option>
                <option value="F">{{ $t('lab.gender.f') }}</option>
                <option value="X">{{ $t('pregnancy.sex_unknown') }}</option>
              </select>
            </FormField>
          </div>

          <!-- Age : nombre + unite, OU date de naissance -->
          <div class="grid gap-4 md:grid-cols-4" data-testid="external-age">
            <FormField id="lab-ext-age" :label="$t('pregnancy.ext_age_value')" :help="$t('pregnancy.ext_age_help')" v-slot="{ describedBy }">
              <input id="lab-ext-age" v-model="extForm.age_value" type="number" min="0" step="1" inputmode="numeric" :disabled="!!extForm.birth_date"
                     :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField id="lab-ext-age-unit" :label="$t('pregnancy.ext_age_unit')" v-slot="{ describedBy }">
              <select id="lab-ext-age-unit" v-model="extForm.age_unit" :disabled="!!extForm.birth_date" :aria-describedby="describedBy" :class="fieldClass">
                <option v-for="u in AGE_UNITS" :key="u" :value="u">{{ $t('pregnancy.unit_' + u) }}</option>
              </select>
            </FormField>
            <FormField id="lab-ext-birth" :label="$t('pregnancy.ext_birth_or')" v-slot="{ describedBy }">
              <input id="lab-ext-birth" v-model="extForm.birth_date" type="date" :max="todayIso()" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <p class="flex items-end pb-2 text-sm font-medium" :class="extAgeEntered && extAgeDays === null ? 'text-tone-danger-text' : 'text-ink'" role="status" data-testid="external-age-label">
              <template v-if="extAgeDays !== null">{{ $t('pregnancy.ext_age_kept', { label: extAgeLabel }) }}</template>
              <template v-else-if="extAgeEntered">{{ $t('pregnancy.ext_age_invalid') }}</template>
            </p>
          </div>

          <!-- Grossesse (laboratoire, medecin, infirmier, admin) : femme ou sexe inconnu -->
          <fieldset v-if="showExternalPregnancy" class="grid gap-4 rounded-card border border-tone-neutral-border p-4 md:grid-cols-2" data-testid="pregnancy-block-external">
            <legend class="px-2 text-sm font-semibold text-ink">{{ $t('pregnancy.block_title') }}</legend>
            <FormField id="lab-ext-preg-status" :label="$t('pregnancy.status_label')" v-slot="{ describedBy }">
              <select id="lab-ext-preg-status" v-model="extForm.pregnancy_status" :aria-describedby="describedBy" :class="fieldClass">
                <option v-for="st in PREGNANCY_STATUSES" :key="st" :value="st">{{ $t('pregnancy.status_' + st) }}</option>
              </select>
            </FormField>
            <template v-if="extForm.pregnancy_status === 'enceinte'">
              <FormField id="lab-ext-ga" :label="$t('pregnancy.ga_label')" :help="gaInvalid ? $t('pregnancy.ga_invalid') : $t('pregnancy.ga_help')" v-slot="{ describedBy }">
                <input id="lab-ext-ga" v-model="gaWeeks" type="number" min="0" max="45" step="1" inputmode="numeric" :aria-describedby="describedBy" :aria-invalid="gaInvalid" :class="fieldClass" />
              </FormField>
              <FormField id="lab-ext-dpa" :label="$t('pregnancy.dpa_label')" v-slot="{ describedBy }">
                <input id="lab-ext-dpa" v-model="extForm.expected_delivery_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
              </FormField>
              <FormField id="lab-ext-program" :label="$t('pregnancy.program_label')" v-slot="{ describedBy }">
                <input id="lab-ext-program" v-model="extForm.pregnancy_program_number" type="text" maxlength="50" autocomplete="off" :aria-describedby="describedBy" :class="fieldClass" />
              </FormField>
              <div v-if="gaSuggestion !== null" class="flex flex-col justify-end gap-2 text-sm md:col-span-2">
                <p class="text-ink-muted" data-testid="ga-suggestion">{{ $t('pregnancy.ga_suggested', { n: gaSuggestion }) }}</p>
                <AppButton v-if="String(gaWeeks) !== String(gaSuggestion)" variant="secondary" @click="gaWeeks = String(gaSuggestion)">{{ $t('pregnancy.ga_use_suggested', { n: gaSuggestion }) }}</AppButton>
              </div>
            </template>
          </fieldset>
          <p class="flex items-start gap-2 rounded-control border p-3 text-sm" :class="toneClasses('warning')">
            <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            {{ $t('lab.reception.ext_warning') }}
          </p>
        </div>
      </AppCard>

      <!-- Prescripteur -->
      <AppCard :title="$t('labScreens.prescriber_section')" class="relative z-20">
        <div v-if="mode === 'external'" class="grid max-w-2xl gap-4 md:grid-cols-2" data-testid="external-prescriber">
          <FormField id="lab-ext-prescriber-title" :label="$t('labScreens.ext_prescriber_title')" required v-slot="{ describedBy }">
            <select id="lab-ext-prescriber-title" v-model="extPrescriber.title" :aria-describedby="describedBy" :class="fieldClass">
              <option value="">{{ $t('labScreens.ext_prescriber_choose_title') }}</option>
              <option v-for="title in PRESCRIBER_TITLES" :key="title" :value="title">{{ title }}</option>
            </select>
          </FormField>
          <FormField id="lab-ext-prescriber-name" :label="$t('labScreens.ext_prescriber_name')" :help="extPrescriber.title === 'Volontaire' ? $t('labScreens.ext_prescriber_name_optional') : $t('labScreens.ext_prescriber_name_help')" v-slot="{ describedBy }">
            <input id="lab-ext-prescriber-name" v-model="extPrescriber.name" type="text" maxlength="80" autocomplete="off" list="lab-ext-prescriber-list"
                   :aria-describedby="describedBy" :class="fieldClass" @input="onPrescriberNameInput" />
            <datalist id="lab-ext-prescriber-list">
              <option v-for="s in prescriberSuggestions" :key="s.label" :value="s.name">{{ s.label }}</option>
            </datalist>
          </FormField>
        </div>
        <div v-else class="max-w-md">
          <FormField id="lab-reception-doctor" :label="$t('labScreens.prescribed_by')" :help="$t('labScreens.prescriber_help')" v-slot="{ describedBy }">
            <select id="lab-reception-doctor" v-model="selectedDoctorId" :aria-describedby="describedBy" :class="fieldClass">
              <option :value="null">{{ $t('labScreens.choose_prescriber') }}</option>
              <option v-for="doc in doctors" :key="doc.user_id" :value="doc.user_id">
                {{ doc.full_name }}, {{ doc.specialty_name || $t('labScreens.doctor_default') }}
              </option>
            </select>
          </FormField>
        </div>
      </AppCard>

      <!-- Examens -->
      <AppCard :title="$t('lab.reception.section2_title')" class="relative z-0">
        <div class="grid gap-6">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div class="flex-1">
              <FormField id="lab-reception-exam" :label="$t('lab.reception.select_exam_placeholder')" v-slot="{ describedBy }">
                <select id="lab-reception-exam" v-model="selectedExamId" :aria-describedby="describedBy" :class="fieldClass">
                  <option :value="null">{{ $t('lab.reception.select_exam_placeholder') }}</option>
                  <option v-for="exam in labStore.exams" :key="exam.id" :value="exam.id">{{ exam.nom }} ({{ exam.code }})</option>
                </select>
              </FormField>
            </div>
            <AppButton variant="secondary" :icon="PlusCircleIcon" :disabled="!selectedExamId" @click="addExamToCart">{{ $t('lab.reception.add_btn') }}</AppButton>
          </div>

          <ResponsiveTable v-if="cart.length > 0" :columns="cartColumns" :rows="cartRows" row-key="id" :aria-label="$t('labScreens.cart_table')" role="region" striped>
            <template #cell-exam="{ row: item }">
              <span class="font-medium">{{ item.nom }}</span>
              <span v-if="item.is_prescribed" class="ml-2 inline-block"><StatusBadge tone="info" :label="$t('labScreens.prescribed_badge')" /></span>
              <span v-if="item.is_invoiced" class="ml-2 inline-block"><StatusBadge tone="success" :label="$t('lab.reception.invoiced_badge')" /></span>
            </template>
            <template #cell-action="{ row: item }">
              <AppButton variant="danger" :icon="TrashIcon" @click="removeFromCart(item.index)">{{ $t('labScreens.remove') }}</AppButton>
            </template>
          </ResponsiveTable>
          <p v-else class="rounded-card border-2 border-dashed border-tone-neutral-border py-8 text-center text-sm text-ink-muted">
            {{ $t('lab.reception.cart_empty') }}
          </p>
        </div>
      </AppCard>

      <ActionBar class="rounded-card border">
        <AppButton :icon="PaperAirplaneIcon" :disabled="!canSubmit || labStore.loading" :loading="labStore.loading" @click="submitRequest">
          {{ $t('lab.reception.submit_btn') }} ({{ cart.length }})
        </AppButton>
      </ActionBar>
    </div>
  </div>
</template>

<script setup>
import { notify } from '@/utils/notify';
  import { ref, computed, onMounted, watch } from 'vue';
  import { useLabStore } from '@/stores/labStore';
  import axios from 'axios'; // Assure-toi que c'est configuré ou utilise ton instance API
  import debounce from 'lodash/debounce';
  import { useI18n } from 'vue-i18n'; 
  import { 
    BeakerIcon, PlusCircleIcon,
    TrashIcon, PaperAirplaneIcon, CheckCircleIcon, ExclamationCircleIcon, ArrowPathIcon 
  } from '@heroicons/vue/24/outline';
  import { AppButton, AppCard, PageHeader, FormField, StatusBadge, ResponsiveTable, ActionBar } from '@/components/ui';
  import { toneClasses } from '@/design/tones';
  import api from '@/services/api';
  import { useAuthStore } from '@/stores/auth';
  import {
    AGE_UNITS, ageLabelFromBirth, formatAge, gestationalFromDpa, localTodayIso, tryAgeFromExternal, tryAgeInDays,
  } from '@/utils/labAge';
  import {
    PREGNANCY_STATUSES, batchGestationalWeeks, canWritePregnancy, pregnancyStatusAtResult, externalPregnancyPayload, parseGestationalWeeks, pregnancyApplies,
  } from '@/utils/pregnancy';

  const { t } = useI18n();
  const labStore = useLabStore();
  const authStore = useAuthStore();
  
  
  // Colonnes du panier et style commun des champs.
  const cartColumns = computed(() => [
    { key: 'exam', label: t('lab.reception.cart_exam_col') },
    { key: 'action', label: t('lab.reception.cart_action_col'), align: 'right' },
  ]);
  // Chaque ligne garde sa position dans le panier pour pouvoir la retirer.
  const cartRows = computed(() => cart.value.map((item, index) => ({ ...item, index })));
  const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

  // UI State
  const mode = ref('internal'); 
  const searchQuery = ref('');
  const selectedExamId = ref(null);
  const showResults = ref(false); 
  
  // Data State
  const selectedPatient = ref(null); 
  const doctors = ref([]); // Liste des médecins récupérée du backend
  const selectedDoctorId = ref(null);
  const newExtForm = () => ({
    full_name: '', gender: 'M',
    age_value: '', age_unit: 'ans', birth_date: '',
    pregnancy_status: 'inconnu', expected_delivery_date: '', pregnancy_program_number: '',
  });
  const extForm = ref(newExtForm());
  // SA de la demande (patient interne enceinte ou patient externe enceinte)
  const gaWeeks = ref('');
  // Statut de grossesse choisi pour CETTE demande d'un patient interne (depart : statut du dossier, qui reste inchange)
  const internalStatus = ref('inconnu');
  // --- Age et grossesse ---
  const todayIso = () => localTodayIso();
  const frDate = (iso) => (iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '');

  // Patient interne : age exact depuis la date de naissance (vide hors ligne : la recherche locale n'a pas la naissance).
  const internalAgeLabel = computed(() => (selectedPatient.value ? ageLabelFromBirth(selectedPatient.value.birth_date, todayIso()) : ''));

  // Patient externe : age en jours depuis (nombre + unite) ou la date de naissance.
  const extAgeEntered = computed(() => !!extForm.value.birth_date || (extForm.value.age_value !== '' && extForm.value.age_value !== null));
  const extAgeDays = computed(() => {
    const f = extForm.value;
    if (f.birth_date) return tryAgeInDays(f.birth_date, todayIso());
    if (f.age_value === '' || f.age_value === null || f.age_value === undefined) return null;
    return tryAgeFromExternal(Number(f.age_value), f.age_unit);
  });
  const extAgeLabel = computed(() => (extAgeDays.value === null ? '' : formatAge(extAgeDays.value)));
  // Ancien champ "age" (annees entieres) conserve pour les ecrans qui le lisent encore.
  const extLegacyYears = computed(() => (extAgeDays.value === null ? null : Math.floor(extAgeDays.value / 365.25)));

  const showExternalPregnancy = computed(() => mode.value === 'external' && canWritePregnancy(authStore) && pregnancyApplies(extForm.value.gender));
  const showInternalPregnancy = computed(() => mode.value === 'internal' && !!selectedPatient.value && canWritePregnancy(authStore)
    && selectedPatient.value.pregnancy_status !== undefined && pregnancyApplies(selectedPatient.value.gender));
  const pregnancyStatusNow = computed(() => (mode.value === 'external'
    ? (showExternalPregnancy.value ? extForm.value.pregnancy_status : 'inconnu')
    : (showInternalPregnancy.value ? internalStatus.value : 'inconnu')));
  const dpaNow = computed(() => (mode.value === 'external' ? extForm.value.expected_delivery_date : selectedPatient.value?.expected_delivery_date) || '');
  watch(internalStatus, (st) => {
    if (st !== 'enceinte') gaWeeks.value = '';
  });
  // SA proposee : 40 - floor((DPA - date de reception) / 7), bornee a 0..45 ; la saisie reste libre.
  const gaSuggestion = computed(() => (pregnancyStatusNow.value === 'enceinte' && dpaNow.value ? gestationalFromDpa(dpaNow.value, todayIso()) : null));
  const gaInvalid = computed(() => pregnancyStatusNow.value === 'enceinte' && !parseGestationalWeeks(gaWeeks.value).ok);
  watch(gaSuggestion, (n) => {
    if (n !== null && (gaWeeks.value === '' || gaWeeks.value === null)) gaWeeks.value = String(n);
  });

  // Prescripteur libre du patient externe (le patient interne garde la liste des medecins).
  const PRESCRIBER_TITLES = ['Dr', 'I.D.E.', 'Fr', 'Br', 'M.', 'Mme', 'Volontaire', 'Autre'];
  const extPrescriber = ref({ title: '', name: '' });
  const prescriberSuggestions = ref([]);
  const cart = ref([]); 
  const autoImportedCount = ref(0);
  const invoicedImportedCount = ref(0);
  
  // --- INITIALISATION ---
  onMounted(async () => {
    labStore.fetchExams();
    labStore.clearMessages();
    fetchDoctors();
    
    // Fermeture si click outside
    window.addEventListener('click', (e) => {
        if (!e.target.closest('.relative')) {
            showResults.value = false;
        }
    });
  });

  const fetchDoctors = async () => {
  try {
    // Ici, on utilise 'api' et non 'axios'. 
    // Pas besoin de mettre 'http://localhost:8000', juste la route :
    const response = await api.get('/users/doctors');
    
    // On récupère la donnée brute (full_name est déjà dedans)
    doctors.value = response.data;
  } catch (e) {
    // Secours hors ligne (laborantin) : doctors_lookup est synchronise pour
    // tous les roles. Meme forme que la reponse serveur ({user_id, full_name,
    // specialty_name}) pour que le <select> et submitRequest restent inchanges.
    if (!e.response && authStore.hasRole(['laborantin'])) {
      try {
        const { db } = await import('@/powersync-client/client');
        const rows = await db.getAll('SELECT user_id, full_name FROM doctors_lookup ORDER BY full_name');
        doctors.value = rows.map((r) => ({
          user_id: r.user_id,
          full_name: r.full_name,
          specialty_name: null,
        }));
        return;
      } catch (localErr) {
        console.error("Erreur lecture locale des médecins", localErr);
      }
    }
    console.error("Erreur lors du chargement des médecins", e);
  }
};
  
  // Suggestions de prescripteurs deja saisis (en ligne seulement ; hors ligne, la saisie libre reste possible).
  const fetchPrescriberSuggestions = debounce(async (q) => {
    try {
      const response = await api.get('/labo/external-prescribers', { params: { q: (q || '').trim() } });
      prescriberSuggestions.value = Array.isArray(response.data) ? response.data : [];
    } catch (e) {
      prescriberSuggestions.value = [];
    }
  }, 250);

  const onPrescriberNameInput = () => {
    fetchPrescriberSuggestions(extPrescriber.value.name);
    const match = prescriberSuggestions.value.find((s) => s.name === extPrescriber.value.name);
    if (match && !extPrescriber.value.title) extPrescriber.value.title = match.title;
  };

  watch(mode, (m) => {
    if (m === 'external') fetchPrescriberSuggestions('');
  });

  // --- 1. LOGIQUE RECHERCHE ---
  
  const performSearch = debounce(async (val) => {
    labStore.clearMessages();
  
    if (val && val.trim().length > 1) {
      try {
        showResults.value = true; 
        await labStore.searchInternal(val.trim());
      } catch (e) {
        console.error("Erreur de recherche", e);
      }
    } else {
      labStore.searchResults = [];
      showResults.value = false;
    }
  }, 300);
  
  watch(searchQuery, (newVal) => {
    if (!selectedPatient.value) {
      if (!newVal || newVal.trim().length <= 1) {
          showResults.value = false;
      }
      performSearch(newVal);
    }
  });
  
  // --- 2. SÉLECTION & AUTO-REMPLISSAGE ---
  
  const normalize = (str) => {
    return str ? str.toString().toLowerCase().trim() : '';
  };

  const selectInternalPatient = (p) => {
    selectedPatient.value = p;
    gaWeeks.value = '';
    internalStatus.value = PREGNANCY_STATUSES.includes(p && p.pregnancy_status) ? p.pregnancy_status : 'inconnu';
    if (p && p.expected_delivery_date && p.pregnancy_status === 'enceinte') {
      const n = gestationalFromDpa(p.expected_delivery_date, todayIso());
      if (n !== null) gaWeeks.value = String(n);
    }
    searchQuery.value = ''; 
    showResults.value = false; 
    
    cart.value = [];
    autoImportedCount.value = 0;
    invoicedImportedCount.value = 0;

    // Auto-remplissage du panier via prescription
    if (p.exams_prescribed && Array.isArray(p.exams_prescribed)) {
        p.exams_prescribed.forEach(prescribedName => {
            const fullExam = labStore.exams.find(e => 
                normalize(e.nom) === normalize(prescribedName)
            );
            if (fullExam) {
                const alreadyInCart = cart.value.some(c => c.id === fullExam.id);
                if (!alreadyInCart) {
                    cart.value.push({ ...fullExam, is_prescribed: true });
                    autoImportedCount.value++;
                }
            }
        });
    }

    // Examens factures a la caisse et pas encore recus : la ligne de facture identifie l'examen.
    // Un examen deja dans le panier (prescrit) prend simplement le lien vers sa ligne de facture.
    if (Array.isArray(p.invoiced_exams)) {
        p.invoiced_exams.forEach(line => {
            const inCart = cart.value.find(c => c.id === line.examen_id);
            if (inCart) {
                if (!inCart.caisse_item_id) { inCart.caisse_item_id = line.item_id; inCart.is_invoiced = true; invoicedImportedCount.value++; }
                return;
            }
            const fullExam = labStore.exams.find(e => e.id === line.examen_id);
            if (fullExam) {
                cart.value.push({ ...fullExam, is_prescribed: false, is_invoiced: true, caisse_item_id: line.item_id });
                invoicedImportedCount.value++;
            }
        });
    }
  };
  
  const setMode = (newMode) => {
    mode.value = newMode;
    resetPatient();
    labStore.clearMessages();
  };
  
  const resetPatient = () => {
    selectedPatient.value = null;
    selectedDoctorId.value = null;
    extForm.value = newExtForm();
    gaWeeks.value = '';
    internalStatus.value = 'inconnu';
    extPrescriber.value = { title: '', name: '' };
    searchQuery.value = '';
    cart.value = []; 
    autoImportedCount.value = 0;
    invoicedImportedCount.value = 0;
    showResults.value = false;
  };
  
  // --- 3. PANIER ---
  
  const addExamToCart = () => {
    const exam = labStore.exams.find(e => e.id === selectedExamId.value);
    if (exam) {
      if (!cart.value.find(c => c.id === exam.id)) {
        cart.value.push({ ...exam, is_prescribed: false }); 
      }
    }
    selectedExamId.value = null;
  };
  
  const removeFromCart = (index) => {
    cart.value.splice(index, 1);
  };
  
  // --- 4. SOUMISSION ---
  
  const canSubmit = computed(() => {
    const hasExam = cart.value.length > 0;
    const hasPatient = mode.value === 'internal' 
      ? !!selectedPatient.value 
      : (extForm.value.full_name && extAgeDays.value !== null);
    
    // Interne : medecin obligatoire. Externe : titre obligatoire, nom obligatoire sauf pour Volontaire.
    const hasDoctor = !!selectedDoctorId.value;
    if (gaInvalid.value) return false;
    const hasExtPrescriber = !!extPrescriber.value.title && (extPrescriber.value.title === 'Volontaire' || !!extPrescriber.value.name.trim());
    
    if (mode.value === 'external') return hasExam && hasPatient && hasExtPrescriber;
    return hasExam && hasPatient && hasDoctor;
  });
  
  const submitRequest = async () => {
    if (cart.value.length === 0) return;

    try {
      const resultsPayload = cart.value.map(item => ({
        examen_id: item.id,
        valeur: null, 
        unite: item.unite || '',
        origin_caisse_item_id: item.caisse_item_id || null
      }));

      const doc = doctors.value.find(d => d.user_id === selectedDoctorId.value);

      const payload = {
        results: resultsPayload,
        patient_id: null,
        origin_prescription_id: null,
        prescribed_by_id: selectedDoctorId.value, // 🟢 Injecté ici
        prescribed_by_name: doc ? doc.full_name : null,
        external_patient_info: null
      };

      if (selectedPatient.value) {
          payload.patient_id = selectedPatient.value.id;
          payload.origin_prescription_id = selectedPatient.value.prescription_id || selectedPatient.value.last_prescription_id || null;
      }
      else if (extForm.value.full_name) {
          payload.external_patient_info = { 
              nom: extForm.value.full_name, 
              prenom: '', 
              age: extLegacyYears.value,
              age_days: extAgeDays.value,
              sexe: extForm.value.gender, 
              telephone: '',
              // Le serveur compose "<titre> <nom>" dans prescribed_by_name, le valide et le retire d'ici.
              prescriber_title: extPrescriber.value.title,
              prescriber_name: extPrescriber.value.name
          };
      }

      // SA de la demande (colonne du lot) : seulement si la patiente est enceinte et le role ecrit la grossesse
      const ga = batchGestationalWeeks(pregnancyStatusNow.value, gaWeeks.value, authStore);
      if (ga !== null) payload.gestational_age_weeks = ga;
      // Grossesse de l'externe : bloc SEPARE d'external_patient_info (que les flux de synchronisation livrent).
      // Seul un role qui ecrit la grossesse envoie ces cles (aucune cle pour les autres).
      if (!selectedPatient.value) {
        const extPreg = externalPregnancyPayload(extForm.value, authStore);
        if (Object.keys(extPreg).length) payload.external_pregnancy_info = extPreg;
      }
      const atResult = pregnancyStatusAtResult(pregnancyStatusNow.value, showInternalPregnancy.value || showExternalPregnancy.value, authStore);
      if (atResult) payload.pregnancy_status_at_result = atResult;

      await labStore.createBatchRequest(payload);
      
      notify('alerts.lab_saved', {}, 'success');
      resetPatient();
      
    } catch (error) {
      console.error("Erreur lors de l'envoi :", error);
      notify('alerts.lab_save_failed');
    }
  };
</script>
