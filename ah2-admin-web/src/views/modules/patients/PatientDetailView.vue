<template>
    <div v-if="dossierStore.isLoading" class="flex justify-center items-center h-96">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
    </div>

    <div v-else-if="dossierStore.patientSummary" class="min-h-screen bg-gray-50 space-y-6">
        
        <PatientHeader :patient="dossierStore.patientSummary" @back="goBack" />

        <div class="flex justify-end gap-2 px-1">
          <button @click="exportDossier('pdf')" :disabled="isExportingDossier"
                  class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50">
            {{ t('export.confirm') }} PDF
          </button>
          <button @click="exportDossier('excel')" :disabled="isExportingDossier"
                  class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50">
            {{ t('export.confirm') }} Excel
          </button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 px-1">
            <VitalsCard :label="t('medical.vitals.bp')" :value="dossierStore.vitals.bp" unit="mmHg" :icon="HeartIcon" colorClass="bg-rose-500" iconColor="text-rose-600" :date="dossierStore.vitals.lastDate" />
            <VitalsCard :label="t('medical.vitals.weight')" :value="dossierStore.patientSummary?.last_weight" unit="kg" :icon="ScaleIcon" colorClass="bg-blue-500" iconColor="text-blue-600" />
            <VitalsCard :label="t('medical.vitals.temperature')" :value="dossierStore.patientSummary?.last_temp" unit="°C" :icon="FireIcon" colorClass="bg-orange-500" iconColor="text-orange-600" />

            <div class="bg-red-50 p-4 rounded-xl border border-red-100 flex items-start shadow-xs">
                <ExclamationTriangleIcon class="h-6 w-6 text-red-600 mr-3 mt-1 shrink-0" />
                <div>
                    <h4 class="text-xs font-bold text-red-700 uppercase tracking-wider">
                        {{ t('medical.alerts.allergies_title') }}
                    </h4>
                    <p class="text-sm text-red-900 mt-1 font-medium leading-tight">
                        {{ dossierStore.patientSummary?.allergies || t('common.none') }}
                    </p>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden min-h-[500px] mx-1">
            
            <div class="border-b border-gray-200 px-6">
                <nav class="-mb-px flex space-x-8 overflow-x-auto" aria-label="Tabs">
                    <button @click="currentTab = 'MEDICAL'" :class="[currentTab === 'MEDICAL' ? 'border-emerald-500 text-emerald-600' : 'border-transparent text-gray-500 hover:text-gray-700', 'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center transition duration-150']">
                        <HeartIcon class="h-5 w-5 mr-2" /> {{ t('medical.tabs.medical_record') }}
                    </button>
                    <button @click="currentTab = 'LABO'" :class="[currentTab === 'LABO' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700', 'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center transition duration-150']">
                        <BeakerIcon class="h-5 w-5 mr-2" /> {{ t('medical.tabs.lab_exams') }}
                    </button>
                    <button @click="currentTab = 'PHARMA'" :class="[currentTab === 'PHARMA' ? 'border-purple-500 text-purple-600' : 'border-transparent text-gray-500 hover:text-gray-700', 'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center transition duration-150']">
                        <TagIcon class="h-5 w-5 mr-2" /> {{ t('medical.tabs.treatments') }}
                    </button>
                    <button v-if="authStore.hasRole(['medecin', 'nurse'])" @click="currentTab = 'HOSPITALISATION'" :class="[currentTab === 'HOSPITALISATION' ? 'border-red-500 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700', 'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center transition duration-150']">
                        <BuildingOffice2Icon class="h-5 w-5 mr-2" /> {{ t('hospitalization.card_title') }}
                    </button>
                    <button v-if="dossierStore.isToxicology" @click="currentTab = 'TOXICO'" :class="[currentTab === 'TOXICO' ? 'border-orange-500 text-orange-600' : 'border-transparent text-gray-500 hover:text-gray-700', 'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center transition duration-150']">
                        <NoSymbolIcon class="h-5 w-5 mr-2" /> {{ t('medical.tabs.toxico_followup') }}
                    </button>
                    <button v-if="dossierStore.isSpiritual" @click="currentTab = 'SPIRITUEL'" :class="[currentTab === 'SPIRITUEL' ? 'border-amber-500 text-amber-700' : 'border-transparent text-gray-500 hover:text-gray-700', 'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center transition duration-150']">
                        <SparklesIcon class="h-5 w-5 mr-2" /> {{ t('medical.tabs.spiritual_followup') }}
                    </button>
                </nav>
            </div>

            <div class="p-6">
                
                <div v-if="currentTab === 'MEDICAL'" class="space-y-4">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-gray-800">{{ t('medical.history.title') }}</h3>
                        <button v-if="canCreateConsultation" @click="openConsultationModal()" class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition">
                            {{ t('medical.actions.new_consultation') }}
                        </button>
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
                    <ul class="mt-4 space-y-2">
                        <li v-for="p in dossierStore.prescriptionHistory" :key="p.prescription_id" class="p-3 bg-gray-50 rounded-sm border border-purple-100 hover:shadow-md transition">
                            <span class="font-semibold text-purple-800">{{ p.medication }}</span> - {{ p.dosage }} 
                            <span :class="['ml-2 text-xs font-medium px-2 py-0.5 rounded-full', p.status === 'Active' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800']">
                                ({{ p.status }})
                            </span>
                        </li>
                    </ul>
                </div>

                <div v-if="currentTab === 'HOSPITALISATION'">
                    <HospitalizationCard :patient-id="dossierStore.patientSummary.patient_id" />
                </div>

                <div v-if="currentTab === 'SPIRITUEL'" class="space-y-4">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-gray-800 text-amber-700">
                            {{ t('medical.tabs.spiritual_followup') }}
                        </h3>
                        <button v-if="!dossierStore.spirituelRestreint" class="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition">
                            {{ t('medical.spiritual.new_note') }}
                        </button>
                    </div>

                    <div v-if="dossierStore.spirituelRestreint" class="bg-gray-50 p-4 rounded-lg border border-gray-200 text-gray-500 text-sm">
                        Ce domaine relève d'un autre service — non affiché ici.
                    </div>
                    <SpiritualTimeline v-else :records="dossierStore.spiritualHistory" />

                </div>

                <div v-if="currentTab === 'TOXICO'">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-gray-800 text-orange-600">
                            {{ t('medical.tabs.toxico_followup') }}
                        </h3>
                    </div>
                    <div v-if="dossierStore.toxicoRestreint" class="bg-gray-50 p-4 rounded-lg border border-gray-200 text-gray-500 text-sm">
                        Ce domaine relève d'un autre service — non affiché ici.
                    </div>
                    <div v-else-if="dossierStore.isDomaineIndisponible('dossier_toxico')" class="bg-gray-50 p-4 rounded-lg border border-gray-200 text-gray-500 text-sm">
                        Indisponible pour le moment — réessayez plus tard.
                    </div>
                    <div v-else-if="dossierStore.toxicoDossier" class="bg-orange-50 p-4 rounded-lg border border-orange-200 space-y-2">
                        <p><span class="font-medium text-orange-800">Substance :</span> {{ dossierStore.toxicoDossier.substance }}</p>
                        <p><span class="font-medium text-orange-800">Phase actuelle :</span> {{ dossierStore.toxicoDossier.currentPhase }}</p>
                        <p><span class="font-medium text-orange-800">Psychologue :</span> {{ dossierStore.toxicoDossier.psychologist }}</p>
                        <p><span class="font-medium text-orange-800">Admission :</span> {{ dossierStore.toxicoDossier.admissionDate }}</p>
                    </div>
                    <div v-else class="text-sm text-gray-400">Aucun dossier toxicologie pour ce patient.</div>
                </div>

                <div v-if="dossierStore.domainesIndisponibles.length" class="mt-4 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                    Certaines informations sont temporairement indisponibles : {{ dossierStore.domainesIndisponibles.join(', ') }}.
                </div>
            </div>
        </div>

        <div v-if="prescriptionOffer.visible" class="mx-1 bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center justify-between">
            <p class="text-sm text-emerald-800">{{ t('medical.consultation_flow.offer_prescription') }}</p>
            <div class="flex gap-2">
                <button @click="declinePrescriptionOffer" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-emerald-300 text-emerald-700 hover:bg-emerald-100 transition">
                    {{ t('medical.consultation_flow.decline') }}
                </button>
                <button @click="acceptPrescriptionOffer" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition">
                    {{ t('medical.consultation_flow.accept') }}
                </button>
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

    <div v-else class="min-h-screen flex flex-col items-center justify-center text-red-500 p-6 bg-gray-50">
        <ExclamationTriangleIcon class="h-10 w-10 mb-3" />
        <p class="text-lg font-medium">{{ dossierStore.error || t('medical.errors.patient_not_found') }}</p>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { usePatientDossierStore } from '@/stores/patientDossierStore';

import PatientHeader from '@/components/patients/PatientHeader.vue';
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

const currentTab = ref('MEDICAL');

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
        } else {
            await dossierStore.refreshMedicalHistory(route.params.id);
        }

        if (data.appointmentId) {
            try {
                await appointmentStore.completeAppointment(data.appointmentId);
            } catch (err) {
                console.error('Erreur complétion RDV:', err);
                alert(t('medical.consultation_flow.appointment_complete_failed'));
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
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
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
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
    }
}

onMounted(async () => {
    const id = route.params.id;
    if (id) await dossierStore.fetchDossierComplete(id);

    const appointmentId = route.query.appointmentId ? Number(route.query.appointmentId) : null;
    if (appointmentId && canCreateConsultation.value) {
        openConsultationModal(appointmentId);
        router.replace({ query: {} });
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
        if (target) {
            openEditConsultationModal(target);
        }
        router.replace({ query: {} });
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