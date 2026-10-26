<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('toxico.title')" :subtitle="t('toxicoScreens.followed_count', toxicoStore.listTotal)">
      <template #actions>
        <div v-if="activeTab === 'active'" class="md:w-72">
          <FormField id="toxico-search" :label="t('toxicoScreens.search_label')" v-slot="{ describedBy }">
            <input id="toxico-search" :value="toxicoStore.filters.search" @input="handleSearch" type="text" :placeholder="t('common.search_placeholder')"
                   :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <AppButton v-if="canAdmitPatient" :icon="PlusCircleIcon" @click="openNewAdmission">{{ t('toxico.new_admission') }}</AppButton>
      </template>
    </PageHeader>

    <!-- Memes quatre reperes colores que le tableau de bord : bleu, vert, rouge, orange -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatTile :title="t('toxicoScreens.active_patients_title')" :value="toxicoStore.statsLoadFailed ? '-' : toxicoStore.activeTotal" :note="t('toxicoScreens.week_note', { n: newPatientsThisWeek })" :icon="UserGroupIcon" tone="info" />
      <StatTile :title="t('toxicoScreens.admissions_month')" :value="toxicoStore.statsLoadFailed ? '-' : toxicoStore.currentMonthAdmissions" :note="t('toxicoScreens.admissions_month_note')" :icon="CalendarIcon" tone="success" />
      <StatTile :title="t('toxicoScreens.relapse_title')" :value="toxicoStore.statsLoadFailed ? '-' : `${toxicoStore.relapseRate}%`" :icon="ExclamationCircleIcon" tone="danger">
        <div class="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-tone-neutral-bg" role="progressbar" :aria-valuenow="toxicoStore.relapseRate" aria-valuemin="0" aria-valuemax="100"
             :aria-label="t('toxicoScreens.relapse_title')">
          <div class="h-1.5 rounded-full bg-tone-danger-solid transition-all duration-700" :style="{ width: toxicoStore.relapseRate + '%' }"></div>
        </div>
      </StatTile>
      <StatTile :title="t('toxicoScreens.withdrawal_title')" :value="toxicoStore.statsLoadFailed ? '-' : toxicoStore.statsByPhase[1] || 0" :note="t('toxicoScreens.withdrawal_note')" :icon="FireIcon" tone="warning" />
    </div>

    <div role="tablist" :aria-label="t('toxico.discharged.tabs_label')" class="inline-flex gap-1 justify-self-start rounded-card bg-tone-neutral-bg p-1">
      <button v-for="tab in listTabs" :key="tab.id" type="button" role="tab"
              :aria-selected="activeTab === tab.id" @click="activeTab = tab.id"
              :class="activeTab === tab.id ? 'bg-white font-semibold text-action-700 shadow-card' : 'text-ink-muted hover:text-ink'"
              class="min-h-11 rounded-control px-5 text-base transition focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600">
        {{ t(tab.label) }}
      </button>
    </div>

    <ToxicoDischargedPanel v-if="activeTab === 'discharged'" :canReadmit="canAdmitPatient"
        @view="openDossier" @readmit="openReadmission" />

    <template v-if="activeTab === 'active'">
      <LoadErrorState v-if="toxicoStore.listLoadFailed" @retry="toxicoStore.fetchToxicoPatients()" />
      <ResponsiveTable
        v-else
        :columns="columns"
        :rows="toxicoStore.patients"
        row-key="patient_id"
        :loading="toxicoStore.isLoading"
        :empty-title="t('toxicoScreens.no_patients')"
        :empty-message="' '"
        striped
      >
        <template #cell-patient="{ row: p }">
          <span class="block font-semibold">{{ p.patientName }}</span>
          <span class="block text-sm text-ink-muted">{{ p.code }}</span>
          <span class="mt-1 inline-block"><StatusBadge tone="neutral" :label="String(p.substance)" /></span>
        </template>
        <template #cell-phase="{ row: p }">
          <StatusBadge :tone="phaseMeta(p.currentPhase).tone" :label="t(`toxico.phases.${p.currentPhase}`)" />
          <div class="mt-2 h-1.5 w-24 overflow-hidden rounded-full bg-tone-neutral-bg" role="progressbar" :aria-valuenow="p.currentPhase" aria-valuemin="0" aria-valuemax="4"
               :aria-label="t('toxicoScreens.phase_bar', { phase: t(`toxico.phases.${p.currentPhase}`), n: p.currentPhase })">
            <div class="h-full rounded-full" :class="phaseMeta(p.currentPhase).bar" :style="{ width: (p.currentPhase / 4) * 100 + '%' }"></div>
          </div>
        </template>
        <template #cell-relapses="{ row: p }">
          <span v-if="p.relapseCount > 0" class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-semibold" :class="toneClasses('danger')">
            <ExclamationTriangleIcon class="h-4 w-4 shrink-0" aria-hidden="true" />
            {{ t('toxicoScreens.relapses_count', p.relapseCount) }}
          </span>
          <span v-else class="text-ink-muted">-</span>
        </template>
        <template #cell-psy="{ row: p }">
          <span class="inline-flex items-center gap-1.5">
            <UserIcon class="h-4 w-4 shrink-0 text-ink-muted" aria-hidden="true" />
            {{ p.psychologist }}
          </span>
        </template>
        <template #actions="{ row: p }">
          <AppButton variant="secondary" size="sm" :icon="EyeIcon" :title="t('toxicoScreens.details_title')" @click="openPatientDetails(p)">{{ t('toxicoScreens.details') }}</AppButton>
          <AppButton variant="info" size="sm" :icon="ClipboardDocumentListIcon" @click="openDossier(p)">{{ t('toxicoScreens.dossier') }}</AppButton>
          <AppButton v-if="canEvaluatePatient" size="sm" :icon="PencilSquareIcon" @click="openEvaluation(p)">{{ t('toxico.actions.evaluate') }}</AppButton>
          <AppButton v-if="canDischargePatient" variant="danger" size="sm" :icon="ArrowRightStartOnRectangleIcon" :title="t('toxico.actions.discharge')" @click="confirmDischarge(p)">{{ t('toxico.stays.discharge_action') }}</AppButton>
        </template>
      </ResponsiveTable>

      <nav v-if="toxicoStore.listTotal > 20" :aria-label="t('toxicoScreens.pagination_label')" class="flex justify-end gap-2">
        <AppButton variant="secondary" :disabled="toxicoStore.filters.page === 1" @click="toxicoStore.setPage(toxicoStore.filters.page - 1)">{{ t('toxicoScreens.prev') }}</AppButton>
        <AppButton variant="secondary" @click="toxicoStore.setPage(toxicoStore.filters.page + 1)">{{ t('toxicoScreens.next') }}</AppButton>
      </nav>
    </template>

    <ToxicoDossierModal 
        v-if="showDossierModal"
        :patientId="selectedPatientId" 
        @close="closeDossierModal"
        @discharged="onDischargedFromDossier"
    />

    <ToxicoEvaluationModal 
        v-if="showEvalModal"
        :patient="selectedPatientForEval"
        @close="closeEvalModal"
        @save="handleSaveEvaluation"
    />

    <ToxicoAdmissionModal
        v-if="showAdmissionModal"
        :preselectedPatient="readmitPatient"
        @close="closeAdmission"
        @save="handleAdmission"
    />

    <ToxicoPatientDetailsModal
        v-if="showPatientDetailsModal"
        :patient="selectedPatientForDetails"
        @close="closePatientDetailsModal"
        @open-dossier="openDossierFromDetails"
    />

    <ToxicoDischargeModal
        v-if="showDischargeConfirm && patientToDischarge"
        :dossierId="Number(patientToDischarge.dossier_id || patientToDischarge.id)"
        :patientName="patientToDischarge.patientName || ''"
        :minDate="String(patientToDischarge.admissionDate || '').slice(0, 10)"
        @close="closeDischarge"
        @discharged="onDischarged"
    />

  </div>
</template>

<script setup>
import { notify } from '@/utils/notify';
import { ref, onMounted, computed } from 'vue';
import { useToxicoStore } from '@/stores/toxicoStore';
import { useAuthStore } from '@/stores/auth'; // 🟢 IMPORT DU STORE AUTH
import { useI18n } from 'vue-i18n';
import ToxicoEvaluationModal from '@/components/toxico/ToxicoEvaluationModal.vue';
import ToxicoDossierModal from '@/components/toxico/ToxicoDossierModal.vue';
import ToxicoAdmissionModal from '@/components/toxico/ToxicoAdmissionModal.vue';
import ToxicoPatientDetailsModal from '@/components/toxico/ToxicoPatientDetailsModal.vue';
import ToxicoDischargeModal from '@/components/toxico/ToxicoDischargeModal.vue';
import ToxicoDischargedPanel from '@/components/toxico/ToxicoDischargedPanel.vue';
import { toPreselectedPatient } from '@/utils/toxicoDischarged';
import { AppButton, PageHeader, FormField, StatTile, StatusBadge, ResponsiveTable, LoadErrorState } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { phaseMeta } from '@/utils/toxicoUi';
import { useToastStore } from '@/stores/toastStore';
import { TOXICO_DISCHARGE_ROLES } from '@/utils/toxicoExport';
import {
    PlusCircleIcon,
    UserIcon,
    UserGroupIcon,
    CalendarIcon,
    ExclamationCircleIcon,
    FireIcon,
    ClipboardDocumentListIcon,
    PencilSquareIcon,
    ArrowRightStartOnRectangleIcon,
    ExclamationTriangleIcon,
    EyeIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const toxicoStore = useToxicoStore();
const authStore = useAuthStore(); // 🟢 INITIALISATION
const toast = useToastStore();

// --- ONGLETS Actifs | Sortis ---
const listTabs = [
    { id: 'active', label: 'toxico.discharged.tab_active' },
    { id: 'discharged', label: 'toxico.discharged.tab_discharged' },
];
const activeTab = ref('active');
const readmitPatient = ref(null);
const openNewAdmission = () => { readmitPatient.value = null; showAdmissionModal.value = true; };
const openReadmission = (row) => {
    if (!canAdmitPatient.value) return;
    readmitPatient.value = toPreselectedPatient(row);
    showAdmissionModal.value = true;
};
const closeAdmission = () => { showAdmissionModal.value = false; readmitPatient.value = null; };

// --- ÉTATS LOCAUX ---
const showDossierModal = ref(false);
const showAdmissionModal = ref(false);
const showEvalModal = ref(false);
const showDischargeConfirm = ref(false);
const showPatientDetailsModal = ref(false);

const selectedPatientId = ref(null);
const selectedPatientForEval = ref(null);
const patientToDischarge = ref(null);
const selectedPatientForDetails = ref(null);

// --- 🟢 PERMISSIONS (COMPUTED) ---
const canAdmitPatient = computed(() => {
    // Admin, Manager et Assistant peuvent créer une admission
    return authStore.hasRole(['admin', 'ToxicoManager', 'Assistant']);
});

const canEvaluatePatient = computed(() => {
    // Regle metier : SEUL le psychologue fait l'evaluation psychologique
    return authStore.hasRole(['Psychologist']);
});

const canDischargePatient = computed(() => {
    // Admin, Manager et promoteur (2026-10-22) peuvent faire une sortie
    return authStore.hasRole(TOXICO_DISCHARGE_ROLES);
});


// --- CALCUL DYNAMIQUE : +X cette semaine (meme calcul reel que le tableau de bord) ---
const newPatientsThisWeek = computed(() => toxicoStore.newThisWeekCount);

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
    { key: 'patient', label: t('toxico.table.patient') },
    { key: 'phase', label: t('toxico.table.phase') },
    { key: 'relapses', label: t('toxicoScreens.col_relapses'), align: 'center' },
    { key: 'psy', label: t('toxico.table.psy') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// --- LIFECYCLE ---
onMounted(() => {
    toxicoStore.fetchToxicoPatients();
    toxicoStore.fetchDashboardStats().catch(() => {});
    toxicoStore.fetchPsychologists();
});

// --- ACTIONS UI ---
let searchTimeout;
const handleSearch = (event) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        toxicoStore.setSearch(event.target.value);
    }, 500);
};

const openDossier = (patient) => {
    selectedPatientId.value = patient.patient_id;
    showDossierModal.value = true;
};

const closeDossierModal = () => {
    showDossierModal.value = false;
    selectedPatientId.value = null;
};

const openEvaluation = (patient) => {
    if (!canEvaluatePatient.value) return;
    if (!patient.dossier_id && !patient.id) {
        console.error("❌ Patient n'a pas de dossier_id:", patient);
        notify('alerts.dossier_id_missing');
        return;
    }
    
    if (!patient.dossier_id && patient.id) {
        patient.dossier_id = patient.id;
    }
    
    selectedPatientForEval.value = patient;
    showEvalModal.value = true;
};

const closeEvalModal = () => {
    showEvalModal.value = false;
    selectedPatientForEval.value = null;
};

const handleAdmission = async (result) => {
    // Réadmission depuis "Sortis" : retour sur Actifs (le store a déjà rechargé la liste active)
    if (result?.isReadmission) {
        activeTab.value = 'active';
        toxicoStore.setDischargedPage(1);
    }
    try {
        await toxicoStore.fetchToxicoPatients();
        await toxicoStore.fetchDashboardStats();
        toast.push(result?.isReadmission
            ? t('toxico.stays.readmission_success', { n: result.stayNumber })
            : t('toxico.admission.success'), 'success');
    } catch (error) {
        console.error("Erreur lors du rafraîchissement:", error);
        notify('alerts.admission_refresh_failed');
    }
};

// L'envoi est fait UNE seule fois, par ToxicoEvaluationModal (qui affiche ses
// propres erreurs). Ici on ne fait que fermer la modale : renvoyer l'evaluation
// creait un doublon dans l'historique (defaut releve 2026-10-26).
const handleSaveEvaluation = () => {
    closeEvalModal();
};

const confirmDischarge = (patient) => {
    if (!patient.dossier_id && !patient.id) {
        notify('alerts.dossier_id_missing');
        return;
    }
    patientToDischarge.value = patient;
    showDischargeConfirm.value = true;
};

// La modale envoie { reason, note } ; le store rafraichit deja liste + stats.
const closeDischarge = () => {
    showDischargeConfirm.value = false;
    patientToDischarge.value = null;
};
const onDischarged = () => {
    closeDischarge();
    toast.push(t('toxico.stays.discharge_success'), 'success');
};
// Le store a deja rafraichi liste + stats lors de la sortie : rien a refaire ici.
const onDischargedFromDossier = () => {};

const openPatientDetails = async (patient) => {
    try {
        selectedPatientForDetails.value = null;
        showPatientDetailsModal.value = true;
        const patientId = patient.patient_id || patient.id;
        if (!patientId) {
            notify('alerts.patient_id_missing');
            showPatientDetailsModal.value = false;
            return;
        }
        const detailedPatient = await toxicoStore.getPatientDetails(patientId);
        selectedPatientForDetails.value = detailedPatient;
    } catch (error) {
        console.error("❌ Erreur chargement détails:", error);
        notify('alerts.details_load_failed');
        showPatientDetailsModal.value = false;
    }
};

const closePatientDetailsModal = () => {
    showPatientDetailsModal.value = false;
    selectedPatientForDetails.value = null;
};

const openDossierFromDetails = (patientId) => {
    closePatientDetailsModal();
    selectedPatientId.value = patientId;
    showDossierModal.value = true;
};
</script>