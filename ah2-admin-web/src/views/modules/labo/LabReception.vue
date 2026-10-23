<template>
  <div class="h-full overflow-y-auto p-4 text-sm md:p-6 [&_table]:text-sm [&_dd]:text-sm">
    <div class="mx-auto grid max-w-5xl gap-6 pb-6" id="top-anchor">

      <PageHeader :title="$t('lab.reception.title')" :subtitle="$t('lab.reception.subtitle')" />

      <p v-if="labStore.successMessage" role="status" class="flex items-center gap-2 rounded-card border p-4 text-sm" :class="toneClasses('success')">
        <CheckCircleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
        <span class="font-medium">{{ labStore.successMessage || $t('lab.reception.success_message') }}</span>
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
                <li v-for="p in labStore.searchResults" :key="p.prescription_id">
                  <button type="button" @click="selectInternalPatient(p)"
                          class="flex min-h-11 w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600">
                    <span class="min-w-0">
                      <span class="block break-words text-sm font-semibold text-ink">{{ p.nom }}</span>
                      <span class="flex items-center gap-1 text-sm text-ink-muted">
                        <BeakerIcon class="h-4 w-4 shrink-0" aria-hidden="true" />
                        <template v-if="p.exams_prescribed && p.exams_prescribed.length">{{ $t('labScreens.exams_prescribed_count', { n: p.exams_prescribed.length }) }}</template>
                        <template v-else>{{ $t('labScreens.prescription_empty') }}</template>
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
              </div>
            </div>
            <AppButton variant="secondary" @click="resetPatient">{{ $t('lab.reception.change_patient') }}</AppButton>
          </div>
        </div>

        <div v-else class="grid gap-4">
          <div class="grid gap-4 md:grid-cols-2">
            <FormField id="lab-ext-name" :label="$t('lab.reception.ext_name_label')" v-slot="{ describedBy }">
              <input id="lab-ext-name" v-model="extForm.full_name" type="text" :placeholder="$t('labScreens.ext_name_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <div class="grid grid-cols-2 gap-4">
              <FormField id="lab-ext-age" :label="$t('lab.reception.ext_age_label')" v-slot="{ describedBy }">
                <input id="lab-ext-age" v-model.number="extForm.age" type="number" :aria-describedby="describedBy" :class="fieldClass" />
              </FormField>
              <FormField id="lab-ext-gender" :label="$t('lab.reception.ext_gender_label')" v-slot="{ describedBy }">
                <select id="lab-ext-gender" v-model="extForm.gender" :aria-describedby="describedBy" :class="fieldClass">
                  <option value="M">{{ $t('lab.gender.m') }}</option>
                  <option value="F">{{ $t('lab.gender.f') }}</option>
                </select>
              </FormField>
            </div>
          </div>
          <p class="flex items-start gap-2 rounded-control border p-3 text-sm" :class="toneClasses('warning')">
            <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            {{ $t('lab.reception.ext_warning') }}
          </p>
        </div>
      </AppCard>

      <!-- Prescripteur -->
      <AppCard :title="$t('labScreens.prescriber_section')" class="relative z-20">
        <div class="max-w-md">
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
  const extForm = ref({ full_name: '', age: '', gender: 'M' }); 
  const cart = ref([]); 
  const autoImportedCount = ref(0); 
  
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
    searchQuery.value = ''; 
    showResults.value = false; 
    
    cart.value = [];
    autoImportedCount.value = 0;

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
  };
  
  const setMode = (newMode) => {
    mode.value = newMode;
    resetPatient();
    labStore.clearMessages();
  };
  
  const resetPatient = () => {
    selectedPatient.value = null;
    selectedDoctorId.value = null;
    extForm.value = { full_name: '', age: '', gender: 'M' };
    searchQuery.value = '';
    cart.value = []; 
    autoImportedCount.value = 0;
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
      : (extForm.value.full_name && extForm.value.age);
    
    // On peut rendre le médecin obligatoire si on veut
    const hasDoctor = !!selectedDoctorId.value;
    
    return hasExam && hasPatient && hasDoctor;
  });
  
  const submitRequest = async () => {
    if (cart.value.length === 0) return;

    try {
      const resultsPayload = cart.value.map(item => ({
        examen_id: item.id,
        valeur: null, 
        unite: item.unite || ''
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
              age: extForm.value.age,
              sexe: extForm.value.gender, 
              telephone: '' 
          };
      }

      await labStore.createBatchRequest(payload);
      
      alert("Dossier enregistré avec succès !");
      resetPatient();
      
    } catch (error) {
      console.error("Erreur lors de l'envoi :", error);
      alert("Erreur technique lors de l'enregistrement.");
    }
  };
</script>
