<template>
    <p v-if="dossierStore.isLoading" class="flex h-96 items-center justify-center" role="status">
        <span class="h-12 w-12 animate-spin rounded-full border-b-2 border-brand-600"></span>
        <span class="sr-only">{{ t('common.loading') }}</span>
    </p>

    <div v-else-if="dossierStore.patientSummary" class="grid gap-6">

        <PatientHeader :patient="dossierStore.patientSummary" :age-label="exactAgeLabel" @back="goBack" />

        <!-- Grossesse : jamais montee pour la secretaire ni pour un role hors liste (aucun libelle, aucun champ) -->
        <PatientPregnancyBlock v-if="showPregnancyBlock" :patient-id="route.params.id" :patient-file="dossierStore.patientFile" @saved="onPregnancySaved" />

        <div class="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <AppButton variant="secondary" @click="exportDossier('pdf')" :disabled="isExportingDossier">
            {{ t('export.confirm') }} PDF
          </AppButton>
          <AppButton variant="secondary" @click="exportDossier('excel')" :disabled="isExportingDossier">
            {{ t('export.confirm') }} Excel
          </AppButton>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <VitalsCard :label="t('medical.vitals.bp')" :value="dossierStore.vitals.bp" unit="mmHg" :icon="HeartIcon" :date="dossierStore.vitals.lastDate" />
            <VitalsCard :label="t('medical.vitals.weight')" :value="dossierStore.patientSummary?.last_weight" unit="kg" :icon="ScaleIcon" />
            <VitalsCard :label="t('medical.vitals.temperature')" :value="dossierStore.patientSummary?.last_temp" unit="°C" :icon="FireIcon" />

            <!-- Allergies : rouge, avec icone et texte (alerte clinique) -->
            <div class="flex items-start rounded-card border p-4 shadow-card" :class="toneClasses('danger')">
                <ExclamationTriangleIcon class="mr-3 mt-1 h-6 w-6 shrink-0" aria-hidden="true" />
                <div>
                    <h4 class="text-base font-bold">
                        {{ t('medical.alerts.allergies_title') }}
                    </h4>
                    <p class="mt-1 text-base font-medium leading-tight">
                        {{ dossierStore.patientSummary?.allergies || t('medical.none_reported_empty') }}
                    </p>
                </div>
            </div>
        </div>

        <div class="min-h-[500px] overflow-hidden rounded-card border border-tone-neutral-border bg-white shadow-card">

            <div class="overflow-x-auto border-b border-tone-neutral-border px-2 md:px-4">
                <div class="-mb-px flex gap-1" role="tablist" :aria-label="t('screens.dossier.aria')">
                    <button type="button" role="tab" :aria-selected="currentTab === 'MEDICAL'" @click="currentTab = 'MEDICAL'" :class="tabClass('MEDICAL')">
                        <HeartIcon :class="['mr-2 h-5 w-5', tabIconClass('MEDICAL')]" aria-hidden="true" /> {{ t('medical.tabs.medical_record') }}
                    </button>
                    <button type="button" role="tab" :aria-selected="currentTab === 'LABO'" @click="currentTab = 'LABO'" :class="tabClass('LABO')">
                        <BeakerIcon :class="['mr-2 h-5 w-5', tabIconClass('LABO')]" aria-hidden="true" /> {{ t('medical.tabs.lab_exams') }}
                    </button>
                    <button type="button" role="tab" :aria-selected="currentTab === 'PHARMA'" @click="currentTab = 'PHARMA'" :class="tabClass('PHARMA')">
                        <TagIcon :class="['mr-2 h-5 w-5', tabIconClass('PHARMA')]" aria-hidden="true" /> {{ t('medical.tabs.treatments') }}
                    </button>
                    <button v-if="authStore.hasRole(['medecin', 'nurse'])" type="button" role="tab" :aria-selected="currentTab === 'HOSPITALISATION'" @click="currentTab = 'HOSPITALISATION'" :class="tabClass('HOSPITALISATION')">
                        <BuildingOffice2Icon :class="['mr-2 h-5 w-5', tabIconClass('HOSPITALISATION')]" aria-hidden="true" /> {{ t('hospitalization.card_title') }}
                    </button>
                    <button v-if="dossierStore.isToxicology" type="button" role="tab" :aria-selected="currentTab === 'TOXICO'" @click="currentTab = 'TOXICO'" :class="tabClass('TOXICO')">
                        <NoSymbolIcon :class="['mr-2 h-5 w-5', tabIconClass('TOXICO')]" aria-hidden="true" /> {{ t('medical.tabs.toxico_followup') }}
                    </button>
                    <button v-if="dossierStore.isSpiritual" type="button" role="tab" :aria-selected="currentTab === 'SPIRITUEL'" @click="currentTab = 'SPIRITUEL'" :class="tabClass('SPIRITUEL')">
                        <SparklesIcon :class="['mr-2 h-5 w-5', tabIconClass('SPIRITUEL')]" aria-hidden="true" /> {{ t('medical.tabs.spiritual_followup') }}
                    </button>
                </div>
            </div>

            <div class="p-4 md:p-6">

                <div v-if="currentTab === 'MEDICAL'" class="space-y-4">
                    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <h3 class="text-lg font-bold text-ink">{{ t('medical.history.title') }}</h3>
                        <AppButton v-if="canCreateConsultation" @click="openConsultationModal()">
                            {{ t('medical.actions.new_consultation') }}
                        </AppButton>
                    </div>
                    <MedicalRecordTimeline
                        :records="dossierStore.medicalHistory"
                        @edit="openEditConsultationModal"
                        @prescribe="openPrescriptionFor"
                    />
                </div>

                <div v-if="currentTab === 'LABO'">
                    <LabResultTable :results="dossierStore.labHistory" />
                </div>

                <div v-if="currentTab === 'PHARMA'">
                    <EmptyState v-if="dossierStore.prescriptionHistory.length === 0" :title="t('screens.dossier.no_prescription_title')" :message="t('screens.dossier.no_prescription_msg')" />
                    <ul v-else class="space-y-2">
                        <li v-for="p in dossierStore.prescriptionHistory" :key="p.prescription_id" class="flex flex-wrap items-center gap-2 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-3 text-base text-ink">
                            <span class="font-semibold">{{ p.is_lab_order ? t('medical.treatments.lab_order') : p.medication }}</span>
                            <span v-if="p.is_lab_order && p.lab_exams_list?.length">{{ p.lab_exams_list.join(', ') }}</span>
                            <span v-for="(d, i) in prescriptionDetails(p)" :key="i">{{ d }}</span>
                            <StatusBadge :tone="isActivePrescription(p.status) ? 'success' : 'neutral'" :label="t(prescriptionStatusLabelKey(p.status))" />
                        </li>
                    </ul>
                </div>

                <div v-if="currentTab === 'HOSPITALISATION'">
                    <HospitalizationCard :patient-id="dossierStore.patientSummary.patient_id" />
                </div>

                <div v-if="currentTab === 'SPIRITUEL'" class="space-y-4">
                    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <h3 class="text-lg font-bold text-ink">
                            {{ t('medical.tabs.spiritual_followup') }}
                        </h3>
                        <AppButton v-if="!dossierStore.spirituelRestreint">
                            {{ t('medical.spiritual.new_note') }}
                        </AppButton>
                    </div>

                    <p v-if="dossierStore.spirituelRestreint" class="rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4 text-base text-ink-muted">
                        {{ t('screens.dossier.other_service') }}
                    </p>
                    <SpiritualTimeline v-else :records="dossierStore.spiritualHistory" />

                </div>

                <div v-if="currentTab === 'TOXICO'">
                    <div class="mb-4 flex items-center justify-between">
                        <h3 class="text-lg font-bold text-ink">
                            {{ t('medical.tabs.toxico_followup') }}
                        </h3>
                    </div>
                    <p v-if="dossierStore.toxicoRestreint" class="rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4 text-base text-ink-muted">
                        {{ t('screens.dossier.other_service') }}
                    </p>
                    <p v-else-if="dossierStore.isDomaineIndisponible('dossier_toxico')" class="rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4 text-base text-ink-muted">
                        {{ t('screens.dossier.unavailable') }}
                    </p>
                    <dl v-else-if="dossierStore.toxicoDossier" class="grid gap-2 rounded-card border p-4 text-base" :class="toneClasses('warning')">
                        <div><dt class="inline font-medium">{{ t('screens.dossier.substance') }}</dt> <dd class="inline">{{ dossierStore.toxicoDossier.substance }}</dd></div>
                        <div><dt class="inline font-medium">{{ t('screens.dossier.current_phase') }}</dt> <dd class="inline">{{ dossierStore.toxicoDossier.currentPhase }}</dd></div>
                        <div><dt class="inline font-medium">{{ t('screens.dossier.psychologist') }}</dt> <dd class="inline">{{ dossierStore.toxicoDossier.psychologist }}</dd></div>
                        <div><dt class="inline font-medium">{{ t('screens.dossier.admission') }}</dt> <dd class="inline">{{ dossierStore.toxicoDossier.admissionDate }}</dd></div>
                    </dl>
                    <EmptyState v-else :title="t('screens.dossier.no_toxico')" />
                </div>

                <p v-if="dossierStore.domainesIndisponibles.length" class="mt-4 rounded-card border px-3 py-2 text-base" :class="toneClasses('warning')">
                    {{ t('screens.dossier.partial', { domains: dossierStore.domainesIndisponibles.join(', ') }) }}
                </p>
            </div>
        </div>

        <div v-if="prescriptionOffer.visible" class="flex flex-col gap-3 rounded-card border p-4 sm:flex-row sm:items-center sm:justify-between" :class="toneClasses('success')">
            <p class="text-base font-medium">{{ t('medical.consultation_flow.offer_prescription') }}</p>
            <div class="flex flex-col gap-2 sm:flex-row">
                <AppButton variant="secondary" @click="declinePrescriptionOffer">
                    {{ t('medical.consultation_flow.decline') }}
                </AppButton>
                <AppButton variant="pharma" @click="acceptPrescriptionOffer">
                    {{ t('medical.consultation_flow.accept') }}
                </AppButton>
            </div>
        </div>

        <MedicalRecordModal
            v-if="showConsultationModal"
            :record="editingRecord"
            :appointmentId="consultationAppointmentId"
            :prefilledPatient="patientPrefill"
            @close="closeConsultationModal"
            @save="handleConsultationSave"
        />

        <PrescriptionModal
            v-if="showPrescriptionModal"
            :prefilledPatient="patientPrefill"
            :prefilledMedicalRecordId="prescriptionOffer.medicalRecordId"
            @close="showPrescriptionModal = false"
            @save="handlePrescriptionSave"
        />
    </div>

    <div v-else class="flex min-h-[50vh] flex-col items-center justify-center p-6 text-center" role="alert">
        <ExclamationTriangleIcon class="mb-3 h-10 w-10 text-tone-danger-text" aria-hidden="true" />
        <p class="text-lg font-medium text-tone-danger-text">{{ dossierStore.error || t('medical.errors.patient_not_found') }}</p>
    </div>
</template>

<script setup>
import { notify, notifyText } from '@/utils/notify';
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { usePatientDossierStore } from '@/stores/patientDossierStore';

import PatientHeader from '@/components/patients/PatientHeader.vue';
import PatientPregnancyBlock from '@/components/patients/PatientPregnancyBlock.vue';
import { ageLabelFromBirth, localTodayIso } from '@/utils/labAge';
import { canSeePregnancy, pregnancyApplies } from '@/utils/pregnancy';
import VitalsCard from '@/components/patients/medical/VitalsCard.vue';
import MedicalRecordTimeline from '@/components/patients/medical/MedicalRecordTimeline.vue';
import LabResultTable from '@/components/patients/labs/LabResultTable.vue';
// 🟢 Le composant est bien importé ici
import SpiritualTimeline from '@/components/patients/medical/SpiritualTimeline.vue';
import HospitalizationCard from '@/components/hospitalization/HospitalizationCard.vue';

import MedicalRecordModal from '@/components/medical-records/MedicalRecordModal.vue';
import PrescriptionModal from '@/components/prescriptions/PrescriptionModal.vue';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { usePrescriptionStore } from '@/stores/prescriptionStore';
import { useAppointmentStore } from '@/stores/appointmentStore';
import { useAuthStore } from '@/stores/auth';
import { isRecordEditable } from '@/utils/consultationLock';
import { prescriptionStatusLabelKey, prescriptionDetails, isActivePrescription } from '@/utils/prescriptionDisplay';
import { AppButton, StatusBadge, EmptyState } from '@/components/ui';
import { toneClasses } from '@/design/tones';

import {
    HeartIcon, ScaleIcon, FireIcon, ExclamationTriangleIcon,
    BeakerIcon, TagIcon, NoSymbolIcon, SparklesIcon, BuildingOffice2Icon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const dossierStore = usePatientDossierStore();
const medicalRecordStore = useMedicalRecordStore();
const prescriptionStore = usePrescriptionStore();
const appointmentStore = useAppointmentStore();
const authStore = useAuthStore();

const canCreateConsultation = computed(() => authStore.hasRole(['medecin', 'nurse']));

// Age exact depuis la naissance du dossier serveur (vide hors ligne : ancien affichage en annees).
const exactAgeLabel = computed(() => ageLabelFromBirth(dossierStore.patientFile?.birth_date, localTodayIso()));

// Bloc grossesse : roles qui peuvent la voir (hasRole), patiente de sexe feminin ou inconnu.
const showPregnancyBlock = computed(() => canSeePregnancy(authStore)
    && pregnancyApplies(dossierStore.patientSummary?.gender ?? dossierStore.patientFile?.gender));
function onPregnancySaved(values) {
    if (dossierStore.patientFile) Object.assign(dossierStore.patientFile, values);
}

const currentTab = ref('MEDICAL');

// Une couleur par rubrique pour se reperer d'un coup d'oeil : l'icone la garde toujours, l'onglet actif la prend
// en plus pour son texte et son trait. Classes ecrites en toutes lettres (Tailwind ne detecte pas les noms construits).
const TAB_STYLES = {
    MEDICAL: { active: 'border-tab-record text-tab-record', hover: 'hover:border-tab-record', icon: 'text-tab-record' },
    LABO: { active: 'border-tab-lab text-tab-lab', hover: 'hover:border-tab-lab', icon: 'text-tab-lab' },
    PHARMA: { active: 'border-tab-pharma text-tab-pharma', hover: 'hover:border-tab-pharma', icon: 'text-tab-pharma' },
    HOSPITALISATION: { active: 'border-tab-hospital text-tab-hospital', hover: 'hover:border-tab-hospital', icon: 'text-tab-hospital' },
    TOXICO: { active: 'border-tab-toxico text-tab-toxico', hover: 'hover:border-tab-toxico', icon: 'text-tab-toxico' },
    SPIRITUEL: { active: 'border-tab-spirit text-tab-spirit', hover: 'hover:border-tab-spirit', icon: 'text-tab-spirit' },
};

const tabClass = (name) => [
    currentTab.value === name
        ? `${TAB_STYLES[name].active} font-semibold`
        : `border-transparent text-ink-muted hover:text-ink ${TAB_STYLES[name].hover} font-medium`,
    'flex min-h-11 items-center whitespace-nowrap border-b-2 px-3 text-base transition duration-150 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600'
];

const tabIconClass = (name) => TAB_STYLES[name].icon;

const showConsultationModal = ref(false);
const consultationAppointmentId = ref(null);
const editingRecord = ref(null);
const showPrescriptionModal = ref(false);
const prescriptionOffer = ref({ visible: false, medicalRecordId: null });

// Une consultation peut venir de 2 sources differentes selon le contexte
// (Tache 6, chantier triage) : la reponse HTTP normale (record_id, entier
// reel) ou la table locale PowerSync (offline/juste apres creation), qui
// n'a que id (uuid local) et server_id (entier une fois synchronise, sinon
// null). medicalRecordStore.updateMedicalRecord() sait deja resoudre les
// deux (WHERE id = ? OR server_id = ?) - on reutilise le meme ordre de
// priorite ici plutot que d'en inventer un nouveau.
function resolveRecordId(record) {
    return record?.record_id ?? record?.server_id ?? record?.id ?? null;
}

const patientPrefill = computed(() => {
    const p = dossierStore.patientSummary;
    if (!p) return null;
    return {
        patientId: p.patient_id,
        patientUuid: p.patient_uuid || null,
        code: p.code,
        firstName: (p.full_name || '').split(' ')[0] || '',
        lastName: (p.full_name || '').split(' ').slice(1).join(' ') || '',
    };
});

function openConsultationModal(appointmentId = null) {
    editingRecord.value = null;
    consultationAppointmentId.value = appointmentId;
    showConsultationModal.value = true;
}

// Reutilise exactement le motif deja etabli par
// MedicalRecordsList.vue::openEditModal - meme modale, meme store, juste
// un point d'entree de plus (depuis la timeline du dossier patient au
// lieu du module Dossiers medicaux separe).
function openEditConsultationModal(record) {
    editingRecord.value = record;
    consultationAppointmentId.value = null;
    showConsultationModal.value = true;
}

function closeConsultationModal() {
    showConsultationModal.value = false;
    consultationAppointmentId.value = null;
    editingRecord.value = null;
}

async function handleConsultationSave(data) {
    try {
        if (editingRecord.value) {
            const recordId = resolveRecordId(editingRecord.value);
            await medicalRecordStore.updateMedicalRecord(recordId, data);
            if (authStore.hasRole(['medecin', 'nurse'])) {
                await dossierStore.refreshMedicalHistoryLocal(route.params.id);
            } else {
                await dossierStore.refreshMedicalHistory(route.params.id);
            }
            closeConsultationModal();
            return;
        }

        const record = await medicalRecordStore.createMedicalRecord(data);

        // medecin/nurse : l'ecriture ci-dessus est locale (Tache 2), un
        // refresh HTTP juste apres lirait avant que DossierConnector.js
        // n'ait eu le temps d'uploader vers le serveur (course) - on relit
        // directement la meme table locale qui vient d'etre ecrite.
        // Autres roles : comportement HTTP inchange.
        if (authStore.hasRole(['medecin', 'nurse'])) {
            await dossierStore.refreshMedicalHistoryLocal(route.params.id);
            // Non attendu (pas de await) : rafraichissement des constantes
            // vitales seules, best-effort, ne doit jamais retarder la suite
            // du flux (proposition de prescription) ni le bloquer si hors
            // ligne - voir refreshVitalsSummaryLocal ci-dessus.
            dossierStore.refreshVitalsSummaryLocal(route.params.id);
            // Relecture serveur des que la synchro a abouti : auteur et signes vitaux
            // (resume clinique calcule cote serveur) n'existent pas dans la ligne locale.
            dossierStore.syncDossierFromServer(route.params.id);
        } else {
            await dossierStore.refreshMedicalHistory(route.params.id);
        }

        if (data.appointmentId) {
            try {
                await appointmentStore.completeAppointment(data.appointmentId);
            } catch (err) {
                console.error('Erreur complétion RDV:', err);
                notifyText(t('medical.consultation_flow.appointment_complete_failed'));
            }
        }

        closeConsultationModal();
        if (record && record.record_id) {
            prescriptionOffer.value = { visible: true, medicalRecordId: record.record_id };
        } else {
            console.warn('Dossier medical cree mais record_id indisponible (reponse de secours du backend) - proposition de prescription liee non affichee.');
        }
    } catch (err) {
        console.error('Erreur enregistrement dossier medical:', err);
        notify('alerts.save_failed', { detail: err.response?.data?.detail || err.message });
    }
}

// Prescription depuis la timeline, independante de "qui a cree la
// consultation" - contrairement a prescriptionOffer (proposee seulement
// juste apres une nouvelle creation), utilisable sur n'importe quelle
// consultation existante par n'importe qui ayant le droit d'agir ici.
function openPrescriptionFor(record) {
    prescriptionOffer.value = { visible: false, medicalRecordId: resolveRecordId(record) };
    showPrescriptionModal.value = true;
}

function declinePrescriptionOffer() {
    prescriptionOffer.value = { visible: false, medicalRecordId: null };
}

function acceptPrescriptionOffer() {
    prescriptionOffer.value.visible = false;
    showPrescriptionModal.value = true;
}

async function handlePrescriptionSave(data) {
    try {
        await prescriptionStore.createPrescription(data);

        if (authStore.hasRole(['medecin', 'nurse'])) {
            await dossierStore.refreshPrescriptionHistoryLocal(route.params.id);
        }

        showPrescriptionModal.value = false;
        prescriptionOffer.value = { visible: false, medicalRecordId: null };
    } catch (err) {
        console.error('Erreur enregistrement prescription:', err);
        notify('alerts.save_failed', { detail: err.response?.data?.detail || err.message });
    }
}

// Retire ?appointmentId= / ?record= de l'adresse SANS naviguer : la vue est cle sur
// route.fullPath (AppShell), donc un router.replace sans query la recreait et fermait le
// formulaire qu'on venait d'ouvrir (defaut des guides, 2026-10-26).
function clearDeepLinkQuery() {
    try {
        const url = new URL(window.location.href);
        url.search = '';
        window.history.replaceState(window.history.state, '', url.toString());
    } catch {
        /* sans effet : l'adresse garde simplement son parametre */
    }
}

onMounted(async () => {
    const id = route.params.id;
    if (id) await dossierStore.fetchDossierComplete(id);

    // Venu du modal dossier toxico ("Voir tout l'historique") : ouvrir
    // directement l'onglet cible.
    if (['MEDICAL', 'PHARMA'].includes(route.query.tab)) {
        currentTab.value = route.query.tab;
    }

    const appointmentId = route.query.appointmentId ? Number(route.query.appointmentId) : null;
    if (appointmentId && canCreateConsultation.value) {
        openConsultationModal(appointmentId);
        clearDeepLinkQuery();
        return;
    }

    // Venu de "Prendre en charge" (dashboard medecin, chantier triage) :
    // on atterrit directement sur la consultation prise en charge plutot
    // que de laisser le medecin la rechercher dans la timeline.
    const recordQuery = route.query.record;
    if (recordQuery && canCreateConsultation.value) {
        const target = dossierStore.medicalHistory.find(
            (r) => String(resolveRecordId(r)) === String(recordQuery)
        );
        // Consultation passee = lecture seule : pas d'ouverture en edition.
        if (target && isRecordEditable(target, dossierStore.medicalHistory, { samePatient: true })) {
            openEditConsultationModal(target);
        }
        clearDeepLinkQuery();
    }
});

const goBack = () => router.back();

const isExportingDossier = ref(false);

const exportDossier = async (format) => {
    isExportingDossier.value = true;
    try {
        const response = await api.get(`/patients/${route.params.id}/dossier/export`, {
            params: { format },
            responseType: 'blob',
        });
        const mimeType = format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
        const blob = new Blob([response.data], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `dossier_${route.params.id}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
        link.click();
        window.URL.revokeObjectURL(url);
    } finally {
        isExportingDossier.value = false;
    }
};
</script>