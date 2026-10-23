<template>
  <FullScreenPanel :title="patient ? `${patient.firstName || ''} ${patient.lastName || ''}`.trim() : t('toxicoScreens.dossier_title')"
                   :subtitle="patient ? t('toxicoScreens.dossier_code_substance', { code: patient.code, substance: patient.substance }) : ''" wide accent @close="$emit('close')">
    <p v-if="isLoading" role="status" class="p-10 text-center text-base text-ink-muted">{{ t('ui.loading') }}</p>

    <div v-else-if="!patient" role="alert" class="grid justify-items-center gap-3 p-6 text-center">
      <p class="text-base font-medium text-tone-danger-text">{{ t('toxicoScreens.dossier_load_error') }}</p>
      <AppButton variant="secondary" @click="$emit('close')">{{ t('toxicoScreens.close') }}</AppButton>
    </div>

    <div v-else class="grid gap-4">
      <div v-if="patient.isActive === false" class="flex flex-wrap items-center gap-2">
        <StatusBadge tone="neutral" :label="t('toxico.discharged.badge_inactive')" />
      </div>

      <div role="tablist" :aria-label="t('toxicoScreens.dossier_title')" class="flex gap-1 overflow-x-auto border-b border-tone-neutral-border">
        <button v-for="tab in visibleTabs" :key="tab.id" type="button" role="tab" :id="`tox-tab-${tab.id}`" :aria-selected="currentTab === tab.id" :aria-controls="`tox-panel-${tab.id}`"
                @click="currentTab = tab.id"
                :class="[
                  currentTab === tab.id ? 'border-action-600 font-semibold text-action-700' : 'border-transparent text-ink-muted hover:border-tone-neutral-border hover:text-ink',
                  'flex min-h-11 shrink-0 items-center gap-2 border-b-4 px-3 text-base focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600'
                ]">
          <component :is="tab.icon" class="h-5 w-5 shrink-0" aria-hidden="true" />
          {{ t(tab.label) }}
        </button>
      </div>

      <p v-if="dischargeSuccess" role="status" class="rounded-card border p-3 text-base" :class="toneClasses('success')">{{ t('toxico.stays.discharge_success') }}</p>

      <section v-if="currentTab === 'history'" role="tabpanel" id="tox-panel-history" aria-labelledby="tox-tab-history" class="grid gap-4">
        <AppCard :title="t('toxicoScreens.progress_title')">
          <div class="h-4 w-full overflow-hidden rounded-full bg-tone-neutral-bg" role="progressbar" :aria-valuenow="patient.currentPhase || 1" aria-valuemin="1" aria-valuemax="4"
               :aria-label="t('toxicoScreens.phase_progress', { phase: patient.currentPhase || 1 })">
            <div class="h-4 rounded-full transition-all duration-500" :class="phaseMeta(patient.currentPhase || 1).bar"
                 :style="{ width: ((patient.currentPhase || 1) / 4) * 100 + '%' }"></div>
          </div>
          <div class="mt-2 flex justify-between text-sm text-ink-muted">
            <span v-for="n in 4" :key="n">{{ t('toxicoScreens.phase_short', { n }) }}</span>
          </div>
        </AppCard>

        <AppCard :title="t('toxico.dossier.tabs.history')">
          <ToxicoStaysTimeline :stays="patient.stays || []" :phaseHistory="patient.phaseHistory || []" :evaluations="patient.evaluations || []" />
        </AppCard>
      </section>

      <section v-if="currentTab === 'medical'" role="tabpanel" id="tox-panel-medical" aria-labelledby="tox-tab-medical">
        <AppCard :title="t('toxico.dossier.recent.medical_title')">
          <template #actions>
            <AppButton v-if="canOpenFullHistory" variant="secondary" size="sm" @click="openFullHistory('MEDICAL')">{{ t('toxico.dossier.recent.see_all') }}</AppButton>
          </template>
          <p v-if="recentLoading" role="status" class="py-4 text-center text-base italic text-ink-muted">{{ t('toxico.dossier.recent.loading') }}</p>
          <p v-else-if="recentError || recent?.historique_medical === null" role="alert" class="py-4 text-center text-base text-tone-danger-text">{{ t('toxico.dossier.recent.error') }}</p>
          <p v-else-if="!recent?.historique_medical?.length" class="py-4 text-center text-base italic text-ink-muted">{{ t('toxico.dossier.recent.empty_medical') }}</p>
          <ul v-else class="divide-y divide-tone-neutral-border">
            <li v-for="r in recent.historique_medical" :key="r.record_id" class="flex justify-between gap-4 py-3">
              <div class="min-w-0">
                <p class="break-words text-base font-semibold text-ink">{{ r.diagnosis || r.motif_code }}</p>
                <p v-if="r.symptoms" class="break-words text-sm text-ink-muted">{{ r.symptoms }}</p>
              </div>
              <span class="shrink-0 whitespace-nowrap text-sm text-ink-muted">{{ formatDate(r.consultation_date) }}</span>
            </li>
          </ul>
        </AppCard>
      </section>

      <section v-if="currentTab === 'prescriptions'" role="tabpanel" id="tox-panel-prescriptions" aria-labelledby="tox-tab-prescriptions">
        <AppCard :title="t('toxico.dossier.recent.prescriptions_title')">
          <template #actions>
            <AppButton v-if="canOpenFullHistory" variant="secondary" size="sm" @click="openFullHistory('PHARMA')">{{ t('toxico.dossier.recent.see_all') }}</AppButton>
          </template>
          <p v-if="recentLoading" role="status" class="py-4 text-center text-base italic text-ink-muted">{{ t('toxico.dossier.recent.loading') }}</p>
          <p v-else-if="recentError || recent?.prescriptions === null" role="alert" class="py-4 text-center text-base text-tone-danger-text">{{ t('toxico.dossier.recent.error') }}</p>
          <p v-else-if="!recent?.prescriptions?.length" class="py-4 text-center text-base italic text-ink-muted">{{ t('toxico.dossier.recent.empty_prescriptions') }}</p>
          <ul v-else class="divide-y divide-tone-neutral-border">
            <li v-for="p in recent.prescriptions" :key="p.prescription_id" class="flex justify-between gap-4 py-3">
              <div class="min-w-0">
                <p class="break-words text-base font-semibold text-ink">{{ prescriptionLabel(p) }}</p>
                <p v-if="p.dosage || p.frequency" class="break-words text-sm text-ink-muted">{{ [p.dosage, p.frequency].filter(Boolean).join(', ') }}</p>
              </div>
              <span class="shrink-0 whitespace-nowrap text-sm text-ink-muted">{{ formatDate(p.start_date) }}</span>
            </li>
          </ul>
        </AppCard>
      </section>
    </div>

    <template v-if="patient" #footer>
      <ActionBar>
        <template #secondary>
          <p v-if="exportError" role="alert" class="self-center text-sm text-tone-danger-text">{{ t(exportError) }}</p>
          <AppButton v-if="canExportDossier" variant="secondary" :disabled="isExporting" :loading="isExporting" @click="exportPdf">
            {{ isExporting ? t('toxico.export.exporting') : t('toxico.export.dossier_pdf') }}
          </AppButton>
        </template>
        <AppButton v-if="canDischarge" variant="danger" @click="showDischarge = true">{{ t('toxico.stays.discharge_action') }}</AppButton>
        <AppButton @click="$emit('close')">{{ t('toxicoScreens.dossier_close') }}</AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>

  <ToxicoDischargeModal v-if="showDischarge && patient" :dossierId="patient.dossier_id"
      :patientName="`${patient.firstName || ''} ${patient.lastName || ''}`.trim()"
      @close="showDischarge = false" @discharged="onDischarged" />
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useToxicoStore } from '@/stores/toxicoStore';
import { useAuthStore } from '@/stores/auth';
import { ToxicoGateway } from '@/services/ToxicoGateway';
import { ClockIcon, HeartIcon, BeakerIcon } from '@heroicons/vue/24/outline';
import ToxicoStaysTimeline from '@/components/toxico/ToxicoStaysTimeline.vue';
import ToxicoDischargeModal from '@/components/toxico/ToxicoDischargeModal.vue';
import { AppButton, AppCard, StatusBadge, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { phaseMeta } from '@/utils/toxicoUi';
import { TOXICO_DOSSIER_EXPORT_ROLES, TOXICO_DISCHARGE_ROLES, downloadPdfBlob, dossierExportFilename, exportErrorKey } from '@/utils/toxicoExport';

const { t } = useI18n();
const toxicoStore = useToxicoStore();
const authStore = useAuthStore();
const router = useRouter();

const props = defineProps({
  patientId: { type: Number, required: true }
});

const emit = defineEmits(['close', 'discharged']);

// Initialiser avec un objet vide évite parfois des erreurs, 
// mais ici on utilise v-if="!patient" donc null est correct pour l'état initial.
const patient = ref(null);
const isLoading = ref(true);
const currentTab = ref('history');

const tabs = [
    { id: 'history', label: 'toxico.dossier.tabs.history', icon: ClockIcon },
    { id: 'medical', label: 'toxico.dossier.tabs.medical', icon: HeartIcon },
    { id: 'prescriptions', label: 'toxico.dossier.tabs.prescriptions', icon: BeakerIcon },
];

// Dossier medical / prescriptions : admin, responsable toxico et psychologue
// seulement (accompagnateur spirituel et assistant n'y ont pas droit - le
// backend refuse aussi GET /patients/{id}/dossier/recent pour eux).
const canSeeClinical = computed(() => authStore.hasRole(['admin', 'ToxicoManager', 'Psychologist']));
// L'historique complet vit sur /patients/:id, reserve admin + responsable toxico.
const canOpenFullHistory = computed(() => authStore.hasRole(['admin', 'ToxicoManager']));
// Sortie : responsable toxico et admin uniquement, et seulement sur un dossier actif.
const canDischarge = computed(() => !!patient.value?.isActive && authStore.hasRole(TOXICO_DISCHARGE_ROLES));
const showDischarge = ref(false);
// Export PDF du dossier (actif ou sorti) : evaluations sensibles -> memes roles que le backend.
const canExportDossier = computed(() => authStore.hasRole(TOXICO_DOSSIER_EXPORT_ROLES));
const isExporting = ref(false);
const exportError = ref(null);
const exportPdf = async () => {
    isExporting.value = true;
    exportError.value = null;
    try {
        const res = await ToxicoGateway.exportDossierPdf(props.patientId);
        downloadPdfBlob(res.data, dossierExportFilename(props.patientId));
    } catch (e) {
        exportError.value = exportErrorKey(e);
    } finally {
        isExporting.value = false;
    }
};
const dischargeSuccess = ref(false);
const loadDossier = async () => {
    const data = await toxicoStore.getPatientDetails(props.patientId);
    patient.value = data;
};
const onDischarged = async () => {
    showDischarge.value = false;
    dischargeSuccess.value = true;
    emit('discharged');
    try { await loadDossier(); } catch (e) { console.error('Erreur rechargement dossier:', e); }
};
const visibleTabs = computed(() =>
    tabs.filter((tab) => canSeeClinical.value || !['medical', 'prescriptions'].includes(tab.id))
);

// Activite recente (3 derniers de chaque), chargee a la premiere ouverture
// d'un des deux onglets - jamais avant, pour ne rien consommer inutilement.
const recent = ref(null);
const recentLoading = ref(false);
const recentError = ref(false);

const loadRecent = async () => {
    if (recent.value || recentLoading.value) return;
    recentLoading.value = true;
    recentError.value = false;
    try {
        const res = await ToxicoGateway.getRecentActivity(props.patientId);
        recent.value = res.data;
    } catch (e) {
        console.error('Erreur activite recente:', e);
        recentError.value = true;
    } finally {
        recentLoading.value = false;
    }
};

watch(currentTab, (tab) => {
    if (canSeeClinical.value && (tab === 'medical' || tab === 'prescriptions')) loadRecent();
});

const prescriptionLabel = (p) =>
    p.medication || (p.lab_exams_list && p.lab_exams_list.length ? p.lab_exams_list.join(', ') : p.lab_exams) || '-';

const openFullHistory = (tab) => {
    emit('close');
    router.push({ name: 'PatientDetail', params: { id: props.patientId }, query: { tab } });
};

const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
        return new Date(dateStr).toLocaleDateString();
    } catch (e) {
        return dateStr;
    }
};

onMounted(async () => {
    isLoading.value = true;
    try {
        // Le store appelle l'API get_patient_detail qui renvoie { firstName, lastName, phaseHistory... }
        await loadDossier();
    } catch (e) {
        console.error("❌ Erreur chargement dossier:", e);
    } finally {
        isLoading.value = false;
    }
});
</script>