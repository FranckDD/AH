<template>
    <div v-if="dossierStore.isLoading" class="flex justify-center items-center h-96">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
    </div>

    <div v-else-if="dossierStore.patientSummary" class="min-h-screen bg-gray-50 space-y-6">
        
        <PatientHeader :patient="dossierStore.patientSummary" @back="goBack" />

        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 px-1">
            <VitalsCard :label="t('medical.vitals.bp')" :value="dossierStore.vitals.bp" unit="mmHg" :icon="HeartIcon" colorClass="bg-rose-500" iconColor="text-rose-600" :date="dossierStore.vitals.lastDate" />
            <VitalsCard :label="t('medical.vitals.weight')" :value="dossierStore.patientSummary?.last_weight" unit="kg" :icon="ScaleIcon" colorClass="bg-blue-500" iconColor="text-blue-600" />
            <VitalsCard :label="t('medical.vitals.temperature')" :value="dossierStore.patientSummary?.last_temp" unit="°C" :icon="FireIcon" colorClass="bg-orange-500" iconColor="text-orange-600" />

            <div class="bg-red-50 p-4 rounded-xl border border-red-100 flex items-start shadow-sm">
                <ExclamationTriangleIcon class="h-6 w-6 text-red-600 mr-3 mt-1 flex-shrink-0" />
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
                        <button class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition">
                            {{ t('medical.actions.new_consultation') }}
                        </button>
                    </div>
                    <MedicalRecordTimeline :records="dossierStore.medicalHistory" />
                </div>

                <div v-if="currentTab === 'LABO'">
                    <LabResultTable :results="dossierStore.labHistory" />
                </div>

                <div v-if="currentTab === 'PHARMA'">
                    <ul class="mt-4 space-y-2">
                        <li v-for="p in dossierStore.prescriptionHistory" :key="p.prescription_id" class="p-3 bg-gray-50 rounded border border-purple-100 hover:shadow-md transition">
                            <span class="font-semibold text-purple-800">{{ p.medication }}</span> - {{ p.dosage }} 
                            <span :class="['ml-2 text-xs font-medium px-2 py-0.5 rounded-full', p.status === 'Active' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800']">
                                ({{ p.status }})
                            </span>
                        </li>
                    </ul>
                </div>

                <div v-if="currentTab === 'SPIRITUEL'" class="space-y-4">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-gray-800 text-amber-700">
                            {{ t('medical.tabs.spiritual_followup') }}
                        </h3>
                        <button class="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition">
                            {{ t('medical.spiritual.new_note') }}
                        </button>
                    </div>

                    <SpiritualTimeline :records="dossierStore.spiritualHistory" />
                    
                </div>

                <div v-if="currentTab === 'TOXICO'">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-gray-800 text-orange-600">
                            {{ t('medical.tabs.toxico_followup') }}
                        </h3>
                    </div>
                    <div class="bg-orange-50 p-4 rounded-lg border border-orange-200 text-orange-800">
                        <p class="font-medium">{{ t('medical.toxico.summary') }}</p>
                        <p class="text-sm mt-1">{{ t('medical.toxico.details') }}</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div v-else class="min-h-screen flex flex-col items-center justify-center text-red-500 p-6 bg-gray-50">
        <ExclamationTriangleIcon class="h-10 w-10 mb-3" />
        <p class="text-lg font-medium">{{ dossierStore.error || t('medical.errors.patient_not_found') }}</p>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { usePatientDossierStore } from '@/stores/patientDossierStore';

import PatientHeader from '@/components/patients/PatientHeader.vue';
import VitalsCard from '@/components/patients/medical/VitalsCard.vue';
import MedicalRecordTimeline from '@/components/patients/medical/MedicalRecordTimeline.vue';
import LabResultTable from '@/components/patients/labs/LabResultTable.vue';
// 🟢 Le composant est bien importé ici
import SpiritualTimeline from '@/components/patients/medical/SpiritualTimeline.vue'; 

import { 
    HeartIcon, ScaleIcon, FireIcon, ExclamationTriangleIcon,
    BeakerIcon, TagIcon, NoSymbolIcon, SparklesIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const dossierStore = usePatientDossierStore();
const currentTab = ref('MEDICAL');

onMounted(() => {
    const id = route.params.id;
    if (id) dossierStore.fetchDossierComplete(id);
});

const goBack = () => router.back();
</script>