<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('appointments.title')" :subtitle="t('appointments.subtitle')">
      <template #actions>
        <div class="flex rounded-control bg-tone-neutral-bg p-1" role="group" :aria-label="t('appointments.title')">
          <button
            type="button"
            @click="viewMode = 'list'"
            :aria-pressed="viewMode === 'list'"
            class="min-h-11 flex-1 rounded-control px-4 text-base font-medium transition focus-visible:outline-2 focus-visible:outline-brand-600 md:min-h-9"
            :class="viewMode === 'list' ? 'bg-white text-ink shadow-card' : 'text-ink-muted hover:text-ink'"
          >
            {{ t('appointments.view_list') }}
          </button>
          <button
            type="button"
            @click="viewMode = 'calendar'"
            :aria-pressed="viewMode === 'calendar'"
            class="min-h-11 flex-1 rounded-control px-4 text-base font-medium transition focus-visible:outline-2 focus-visible:outline-brand-600 md:min-h-9"
            :class="viewMode === 'calendar' ? 'bg-white text-ink shadow-card' : 'text-ink-muted hover:text-ink'"
          >
            {{ t('appointments.view_calendar') }}
          </button>
        </div>

        <AppButton :icon="PlusCircleIcon" @click="openCreateModal">
          {{ t('appointments.new_appointment') }}
        </AppButton>
      </template>
    </PageHeader>

    <section v-if="viewMode === 'list'" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:flex lg:flex-wrap lg:items-end">

      <div class="md:col-span-2 lg:min-w-[220px] lg:flex-1">
        <FormField id="appt-search" :label="t('appointments.search_label')" v-slot="{ describedBy }">
          <div class="relative">
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
            <input
              id="appt-search"
              v-model="searchQuery"
              type="text"
              :aria-describedby="describedBy"
              :placeholder="t('appointments.search_placeholder')"
              :class="[fieldClass, 'bg-white pl-10']"
            >
          </div>
        </FormField>
      </div>

      <div class="lg:w-48">
        <FormField id="appt-status" :label="t('appointments.status_label')" v-slot="{ describedBy }">
          <select id="appt-status" v-model="statusFilter" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option value="ALL">{{ t('appointments.status_all') }}</option>
            <option v-for="s in appointmentStatuses" :key="s" :value="s">{{ t(`appointments.status_${s}`) }}</option>
          </select>
        </FormField>
      </div>

      <div class="lg:w-44">
        <FormField id="appt-date-mode" :label="t('appointments.date_label')" v-slot="{ describedBy }">
          <select id="appt-date-mode" v-model="dateMode" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option value="ALL">{{ t('appointments.date_all') }}</option>
            <option value="TODAY">{{ t('appointments.date_today') }}</option>
            <option value="CUSTOM">{{ t('appointments.date_custom') }}</option>
          </select>
        </FormField>
      </div>

      <div v-if="dateMode === 'CUSTOM'" class="lg:w-44">
        <FormField id="appt-custom-date" :label="t('appointments.date_custom')" v-slot="{ describedBy }">
          <input id="appt-custom-date" v-model="customDate" type="date" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
      </div>
    </section>

    <section v-if="viewMode === 'list'" class="grid gap-3">

      <p class="text-base text-ink-muted" aria-live="polite">
        {{ appointmentStore.appointments.length }} {{ t('appointments.results_count') }}
      </p>

      <ResponsiveTable
        :columns="columns"
        :rows="appointmentStore.appointments"
        row-key="id"
        :loading="appointmentStore.isLoading"
        :empty-title="t('appointments.empty')"
      >
        <template #cell-patient="{ row: appt }">
          <div class="text-base font-medium text-ink">{{ patientName(appt) }}</div>
          <div class="text-sm text-ink-muted">{{ appt.code_patient }}</div>
        </template>
        <template #cell-phone="{ row: appt }">{{ appt.contact_phone || '-' }}</template>
        <template #cell-doctor="{ row: appt }">{{ appt.doctor_full_name || appt.doctor_username || '-' }}</template>
        <template #cell-date="{ row: appt }"><span class="font-mono">{{ appt.appointment_date }}</span></template>
        <template #cell-time="{ row: appt }"><span class="font-mono">{{ (appt.appointment_time || '').substring(0, 5) }}</span></template>
        <template #cell-reason="{ row: appt }">{{ appt.reason || '-' }}</template>
        <template #cell-status="{ row: appt }"><StatusBadge :status="appt.status" /></template>

        <template #actions="{ row: appt }">
          <!--
            Bouton "Accepter" volontairement omis (contrairement au
            client desktop) - voir docs/superpowers/SUIVI-AVANCEMENT.md,
            registre C4. Non touche par ce chantier.
          -->
          <AppButton
            v-if="appt.status === 'pending'"
            @click="demarrerConsultation(appt)"
            :disabled="!appt.patient_id || !appt.server_id"
            :title="!appt.server_id ? t('appointments.pending_sync') : ''"
          >
            {{ t('appointments.actions.start_consultation') }}
          </AppButton>
          <AppButton
            v-if="appt.status === 'pending'"
            variant="secondary"
            @click="appointmentStore.completeAppointment(appt.server_id)"
            :disabled="!appt.server_id"
            :title="!appt.server_id ? t('appointments.pending_sync') : ''"
          >
            {{ t('appointments.actions.complete') }}
          </AppButton>
          <AppButton
            v-if="appt.status === 'pending'"
            variant="secondary"
            @click="voirDossier(appt)"
            :disabled="!appt.patient_id"
          >
            {{ t('appointments.actions.view_dossier') }}
          </AppButton>
          <AppButton variant="ghost" @click="openEditModal(appt)">
            {{ t('appointments.actions.edit') }}
          </AppButton>
          <AppButton
            v-if="appt.status === 'pending'"
            variant="danger"
            @click="appointmentStore.cancelAppointment(appt.server_id)"
            :disabled="!appt.server_id"
            :title="!appt.server_id ? t('appointments.pending_sync') : ''"
          >
            {{ t('appointments.actions.cancel') }}
          </AppButton>
        </template>
      </ResponsiveTable>

    </section>

    <div v-else class="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <AppointmentsCalendar
          :appointments="appointmentStore.rawAppointments"
          @day-click="handleDayClick"
        />
      </div>
      <AppointmentDayPanel
        v-if="selectedDate"
        :date="selectedDate"
        :appointments="selectedDateAppointments"
        @close="selectedDate = null"
        @edit="openEditModal"
        @cancel="(appt) => appointmentStore.cancelAppointment(appt.server_id)"
        @complete="(appt) => appointmentStore.completeAppointment(appt.server_id)"
        @view-dossier="voirDossier"
        @start-consultation="demarrerConsultation"
      />
    </div>

    <AppointmentModal
      v-if="showModal"
      :appointment="editingAppointment"
      :initial-date="createDate"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAppointmentStore, APPOINTMENT_STATUSES } from '@/stores/appointmentStore';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import StatusBadge from '@/components/appointments/StatusBadge.vue';
import AppointmentModal from '@/components/appointments/AppointmentModal.vue';
import AppointmentsCalendar from '@/components/appointments/AppointmentsCalendar.vue';
import AppointmentDayPanel from '@/components/appointments/AppointmentDayPanel.vue';
import { AppButton, PageHeader, FormField, ResponsiveTable } from '@/components/ui';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const appointmentStore = useAppointmentStore();
const appointmentStatuses = APPOINTMENT_STATUSES;
const router = useRouter();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs de filtre.
const columns = computed(() => [
  { key: 'patient', label: t('appointments.table.patient') },
  { key: 'phone', label: t('appointments.table.phone') },
  { key: 'doctor', label: t('appointments.table.doctor') },
  { key: 'date', label: t('appointments.table.date') },
  { key: 'time', label: t('appointments.table.time') },
  { key: 'reason', label: t('appointments.table.reason') },
  { key: 'status', label: t('appointments.table.status') },
]);
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

function voirDossier(appt) {
  router.push(`/medical/patients/${appt.patient_id}`);
}

function demarrerConsultation(appt) {
  router.push(`/medical/patients/${appt.patient_id}?appointmentId=${appt.server_id}`);
}

onMounted(() => {
  appointmentStore.startWatchingAppointments();
  appointmentStore.fetchSpecialties();
});

const searchQuery = computed({
  get: () => appointmentStore.filters.searchQuery,
  set: (val) => appointmentStore.setFilters({ searchQuery: val }),
});

const statusFilter = computed({
  get: () => appointmentStore.filters.status,
  set: (val) => appointmentStore.setFilters({ status: val }),
});

const dateMode = computed({
  get: () => appointmentStore.filters.dateMode,
  set: (val) => appointmentStore.setFilters({ dateMode: val }),
});

const customDate = computed({
  get: () => appointmentStore.filters.customDate,
  set: (val) => appointmentStore.setFilters({ customDate: val }),
});

function patientName(appt) {
  return [appt.first_name, appt.last_name].filter(Boolean).join(' ') || '-';
}

const showModal = ref(false);
const editingAppointment = ref(null);
const createDate = ref('');

function openCreateModal() {
  editingAppointment.value = null;
  createDate.value = '';
  showModal.value = true;
}

function openEditModal(appt) {
  editingAppointment.value = appt;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingAppointment.value = null;
  createDate.value = '';
}

// --- Vue calendrier ---
const viewMode = ref('list'); // 'list' | 'calendar'
const selectedDate = ref(null);

const selectedDateAppointments = computed(() => {
  if (!selectedDate.value) return [];
  return appointmentStore.rawAppointments
    .filter((a) => (a.appointment_date || '').substring(0, 10) === selectedDate.value)
    .sort((a, b) => (a.appointment_time || '').localeCompare(b.appointment_time || ''));
});

// Clic sur un jour du calendrier (AppointmentsCalendar.vue) : un jour avec
// des RDV ouvre le panneau de detail, un jour vide ouvre directement la
// creation avec la date pre-remplie - decision prise avec l'utilisateur
// au brainstorming (2026-09-28).
function handleDayClick(dateStr) {
  const hasAppointments = appointmentStore.rawAppointments.some(
    (a) => (a.appointment_date || '').substring(0, 10) === dateStr
  );
  if (hasAppointments) {
    selectedDate.value = dateStr;
  } else {
    editingAppointment.value = null;
    createDate.value = dateStr;
    showModal.value = true;
  }
}

async function handleSave(data) {
  try {
    if (editingAppointment.value) {
      await appointmentStore.updateAppointment(editingAppointment.value.id, data);
    } else {
      await appointmentStore.createAppointment(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement rendez-vous:', err);
    alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
  }
}
</script>
