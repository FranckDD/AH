<template>
  <FullScreenPanel :title="t('toxicoScreens.details_modal_title')" :subtitle="t('toxicoScreens.details_modal_subtitle')" accent @close="$emit('close')">
    <div v-if="patient" class="grid gap-4">

      <!-- Identite : bleu -->
      <section aria-labelledby="tox-det-identity" :class="card">
        <h3 id="tox-det-identity" :class="[sectionTitle, SECTION.info]">
          <IdentificationIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
          {{ t('toxicoScreens.section_identity') }}
        </h3>
        <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div><dt :class="DT">{{ t('toxicoScreens.f_firstname') }}</dt><dd :class="DD">{{ patient.firstName || patient.first_name || t('toxicoScreens.not_provided') }}</dd></div>
          <div><dt :class="DT">{{ t('toxicoScreens.f_lastname') }}</dt><dd :class="DD">{{ patient.lastName || patient.last_name || t('toxicoScreens.not_provided') }}</dd></div>
          <div><dt :class="DT">{{ t('toxicoScreens.f_dob') }}</dt><dd :class="DD">{{ formatDate(patient.dob) }}</dd></div>
          <div><dt :class="DT">{{ t('toxicoScreens.f_age') }}</dt><dd :class="DD">{{ t('toxicoScreens.years', { n: calculateAge(patient.dob) }) }}</dd></div>
          <div><dt :class="DT">{{ t('toxicoScreens.f_mother') }}</dt><dd :class="DD">{{ patient.mothersName || patient.mothers_name || t('toxicoScreens.not_provided') }}</dd></div>
          <div><dt :class="DT">{{ t('toxicoScreens.f_code') }}</dt><dd class="font-mono text-base font-bold text-tone-info-text">{{ patient.code || 'N/A' }}</dd></div>
        </dl>
      </section>

      <!-- Contact : vert -->
      <section aria-labelledby="tox-det-contact" :class="card">
        <h3 id="tox-det-contact" :class="[sectionTitle, SECTION.success]">
          <PhoneIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
          {{ t('toxicoScreens.section_contact') }}
        </h3>
        <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div class="sm:col-span-2"><dt :class="DT">{{ t('toxicoScreens.f_address') }}</dt><dd :class="DD">{{ patient.address || t('toxicoScreens.not_provided_f') }}</dd></div>
          <div><dt :class="DT">{{ t('toxicoScreens.f_phone') }}</dt><dd :class="DD">{{ patient.contact || t('toxicoScreens.not_provided') }}</dd></div>
          <div>
            <dt :class="DT">{{ t('toxicoScreens.f_substance') }}</dt>
            <dd class="mt-1"><StatusBadge tone="neutral" :label="patient.substance || t('toxicoScreens.not_specified_f')" /></dd>
          </div>
        </dl>
      </section>

      <!-- Admission : indigo -->
      <section aria-labelledby="tox-det-admission" :class="card">
        <h3 id="tox-det-admission" :class="[sectionTitle, SECTION.accent]">
          <CalendarIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
          {{ t('toxicoScreens.section_admission') }}
        </h3>
        <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div><dt :class="DT">{{ t('toxicoScreens.f_admission_date') }}</dt><dd :class="DD">{{ formatDate(patient.admissionDate || patient.admission_date) }}</dd></div>
          <div><dt :class="DT">{{ t('toxicoScreens.f_psychologist') }}</dt><dd :class="DD">{{ patient.psychologist || t('toxicoScreens.not_assigned') }}</dd></div>
          <div class="sm:col-span-2">
            <dt :class="DT">{{ t('toxicoScreens.f_status') }}</dt>
            <dd class="mt-1 flex flex-wrap items-center gap-2">
              <StatusBadge :tone="phaseMeta(patient.currentPhase || 1).tone" :label="t('toxicoScreens.phase_short', { n: patient.currentPhase || 1 })" />
              <span v-if="patient.relapseCount > 0" class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-semibold" :class="toneClasses('danger')">
                <ExclamationTriangleIcon class="h-4 w-4 shrink-0" aria-hidden="true" />
                {{ t('toxicoScreens.relapses_count', patient.relapseCount) }}
              </span>
            </dd>
          </div>
        </dl>
      </section>

      <!-- Tuteur : orange -->
      <section aria-labelledby="tox-det-guardian" :class="card">
        <h3 id="tox-det-guardian" :class="[sectionTitle, SECTION.warning]">
          <ShieldCheckIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
          {{ t('toxicoScreens.section_guardian') }}
        </h3>
        <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div><dt :class="DT">{{ t('toxicoScreens.f_guardian_name') }}</dt><dd :class="DD">{{ patient.guardianName || patient.guardian_name || t('toxicoScreens.not_provided') }}</dd></div>
          <div><dt :class="DT">{{ t('toxicoScreens.f_guardian_contact') }}</dt><dd :class="DD">{{ patient.guardianContact || patient.guardian_contact || t('toxicoScreens.not_provided') }}</dd></div>
          <div class="sm:col-span-2">
            <dt :class="DT">{{ t('toxicoScreens.f_consent') }}</dt>
            <dd class="mt-1">
              <button v-if="patient.consentFile || patient.consent_file" type="button" :disabled="consentLoading" @click="openConsent"
                 class="inline-flex min-h-11 items-center gap-2 text-base font-medium text-tone-info-text underline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600 disabled:opacity-60">
                <PaperClipIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
                {{ t('toxicoScreens.file_download') }}
                <ArrowDownTrayIcon class="h-4 w-4 shrink-0" aria-hidden="true" />
              </button>
              <span v-if="!(patient.consentFile || patient.consent_file)" class="text-base italic text-ink-muted">{{ t('toxicoScreens.file_none') }}</span>
              <p v-if="consentError" role="alert" class="mt-1 text-sm text-tone-danger-text">{{ consentError }}</p>
            </dd>
          </div>
        </dl>
      </section>

      <!-- Notes : neutre -->
      <section v-if="patient.notes" aria-labelledby="tox-det-notes" :class="card">
        <h3 id="tox-det-notes" :class="[sectionTitle, SECTION.neutral]">
          <DocumentTextIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
          {{ t('toxicoScreens.section_notes') }}
        </h3>
        <p class="whitespace-pre-line text-base text-ink">{{ patient.notes }}</p>
      </section>
    </div>

    <div v-else class="py-10 text-center text-base text-ink-muted">
      <UserCircleIcon class="mx-auto mb-3 h-12 w-12" aria-hidden="true" />
      <p>{{ t('toxicoScreens.no_patient') }}</p>
    </div>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <p class="self-center text-sm text-ink-muted">{{ t('toxicoScreens.created_on', { date: formatDate(patient?.createdAt || new Date().toISOString()) }) }}</p>
        </template>
        <AppButton variant="secondary" @click="$emit('close')">{{ t('toxicoScreens.close') }}</AppButton>
        <AppButton variant="info" :icon="ClipboardDocumentListIcon" @click="openDossier">{{ t('toxicoScreens.open_full_dossier') }}</AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { AppButton, StatusBadge, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { phaseMeta } from '@/utils/toxicoUi';
import {
  UserCircleIcon,
  IdentificationIcon,
  PhoneIcon,
  CalendarIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  PaperClipIcon, 
  ArrowDownTrayIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();

// Titres de section : memes couleurs qu'avant (bleu, vert, indigo, orange), via les jetons ; le titre reste ecrit.
const card = 'rounded-card border border-tone-neutral-border bg-white p-4';
const sectionTitle = 'mb-4 flex items-center gap-2 border-b pb-2 text-lg font-semibold';
const SECTION = {
  info: 'border-tone-info-border text-tone-info-text',
  success: 'border-tone-success-border text-tone-success-text',
  accent: 'border-action-600 text-action-700',
  warning: 'border-tone-warning-border text-tone-warning-text',
  neutral: 'border-tone-neutral-border text-ink',
};
const DT = 'text-sm text-ink-muted';
const DD = 'text-base font-semibold text-ink';

const props = defineProps({
  patient: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['close', 'open-dossier']);

// Formater une date
const formatDate = (dateString) => {
  if (!dateString) return t('toxicoScreens.not_provided_f');
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  } catch (e) {
    return dateString;
  }
};

// Calculer l'âge
const calculateAge = (dob) => {
  if (!dob) return '?';
  try {
    const birthDate = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  } catch (e) {
    return '?';
  }
};
// Le consentement n'est plus public (/static) : on le charge avec le jeton, puis on l'ouvre depuis un blob local.
const consentLoading = ref(false);
const consentError = ref('');
const openConsent = async () => {
  const dossierId = props.patient?.dossier_id || props.patient?.dossierId;
  const stored = props.patient?.consentFile || props.patient?.consent_file;
  if (!dossierId || !stored) return;
  consentLoading.value = true;
  consentError.value = '';
  try {
    const res = await api.get(`/toxico/dossiers/${dossierId}/consent`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data);
    window.open(url, '_blank', 'noopener,noreferrer');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) {
    consentError.value = t('toxicoScreens.file_error');
  } finally {
    consentLoading.value = false;
  }
};

// Ouvrir le dossier complet
const openDossier = () => {
  if (props.patient?.patient_id) {
    emit('open-dossier', props.patient.patient_id);
    emit('close');
  }
};
</script>