<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('prescriptions.title')" :subtitle="t('prescriptions.subtitle')">
      <template #actions>
        <AppButton variant="pharma" :icon="PlusCircleIcon" @click="openCreateModal">
          {{ t('prescriptions.new_prescription') }}
        </AppButton>
      </template>
    </PageHeader>

    <section class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:flex lg:flex-wrap lg:items-end">

      <div class="md:col-span-2 lg:min-w-[220px] lg:flex-1">
        <FormField id="presc-search" :label="t('prescriptions.search_label')" v-slot="{ describedBy }">
          <div class="relative">
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
            <input
              id="presc-search"
              v-model="searchQuery"
              type="text"
              :aria-describedby="describedBy"
              :placeholder="t('prescriptions.search_placeholder')"
              :class="[fieldClass, 'bg-white pl-10']"
            >
          </div>
        </FormField>
      </div>

      <div class="lg:w-40">
        <FormField id="presc-date-from" :label="t('prescriptions.date_from')" v-slot="{ describedBy }">
          <input id="presc-date-from" v-model="dateFrom" type="date" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
      </div>

      <div class="lg:w-40">
        <FormField id="presc-date-to" :label="t('prescriptions.date_to')" v-slot="{ describedBy }">
          <input id="presc-date-to" v-model="dateTo" type="date" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
      </div>
    </section>

    <section class="grid gap-3">

      <p class="text-base text-ink-muted" aria-live="polite">
        {{ prescriptionStore.pagination.total }} {{ t('prescriptions.results_count') }}
      </p>

      <ResponsiveTable
        :columns="columns"
        :rows="prescriptionStore.prescriptions"
        row-key="prescription_id"
        :loading="prescriptionStore.isLoading"
        :empty-title="t('prescriptions.empty')"
      >
        <template #cell-patient="{ row: presc }">
          <div class="text-base font-medium text-ink">{{ patientName(presc) }}</div>
          <div class="text-sm text-ink-muted">{{ presc.patient?.code_patient }}</div>
        </template>

        <template #cell-content="{ row: presc }">
          <template v-if="presc.is_lab_order">
            <StatusBadge tone="info" :label="t('prescriptions.table.lab_order_badge')" />
            <div class="mt-1 text-sm text-ink-muted">{{ (presc.lab_exams_list || []).join(', ') || '-' }}</div>
          </template>
          <template v-else>
            <span class="font-semibold text-ink">{{ presc.medication }}</span>
            <div class="text-sm text-ink-muted">{{ presc.dosage }}, {{ presc.frequency }}</div>
          </template>
        </template>

        <template #cell-duration="{ row: presc }">{{ presc.is_lab_order ? '-' : (presc.duration || '-') }}</template>
        <template #cell-start_date="{ row: presc }"><span class="font-mono">{{ presc.start_date }}</span></template>

        <!-- Date de fin : badge selon l'urgence de renouvellement, avec le delai ecrit en toutes lettres -->
        <template #cell-end_date="{ row: presc }">
          <template v-if="!presc.is_lab_order && presc.end_date">
            <StatusBadge :tone="endTone(presc)" :label="presc.end_date" />
            <div v-if="endLabel(presc)" class="mt-1 text-sm text-ink-muted">{{ endLabel(presc) }}</div>
          </template>
          <span v-else class="text-ink-muted">-</span>
        </template>

        <template #cell-prescriber="{ row: presc }">{{ presc.prescribed_by_name || '-' }}</template>

        <template #actions="{ row: presc }">
          <!-- Prescription d'une consultation passee : lecture seule, badge a la place des boutons -->
          <StatusBadge
            v-if="!isPrescriptionEditable(presc)"
            tone="neutral"
            :label="t('medical.readonly.badge')"
            :title="t('medical.readonly.prescription_locked')"
          />
          <template v-else>
            <AppButton
              variant="secondary"
              @click="openEditModal(presc)"
              :disabled="!presc.prescription_id"
              :title="presc.prescription_id ? '' : 'En attente de synchronisation'"
            >
              {{ t('prescriptions.actions.edit') }}
            </AppButton>
            <AppButton
              variant="danger"
              @click="handleDelete(presc)"
              :disabled="!presc.prescription_id"
              :title="presc.prescription_id ? '' : 'En attente de synchronisation'"
            >
              {{ t('prescriptions.actions.delete') }}
            </AppButton>
          </template>
        </template>
      </ResponsiveTable>

      <div v-if="prescriptionStore.pagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">
          {{ t('common.page') }} {{ prescriptionStore.pagination.page }} / {{ prescriptionStore.pagination.total_pages }}
        </p>
        <div class="flex gap-2">
          <AppButton
            variant="secondary"
            :icon="ChevronLeftIcon"
            :aria-label="t('prescriptions.prev_page')"
            @click="goToPage(prescriptionStore.pagination.page - 1)"
            :disabled="prescriptionStore.pagination.page === 1"
          />
          <AppButton
            variant="secondary"
            :icon="ChevronRightIcon"
            :aria-label="t('prescriptions.next_page')"
            @click="goToPage(prescriptionStore.pagination.page + 1)"
            :disabled="prescriptionStore.pagination.page === prescriptionStore.pagination.total_pages"
          />
        </div>
      </div>

    </section>

    <PrescriptionModal
      v-if="showModal"
      :prescription="editingPrescription"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { notify } from '@/utils/notify';
import { ref, computed, onMounted } from 'vue';
import { usePrescriptionStore } from '@/stores/prescriptionStore';
import { useI18n } from 'vue-i18n';
import PrescriptionModal from '@/components/prescriptions/PrescriptionModal.vue';
import { isPrescriptionEditable } from '@/utils/consultationLock';
import { endUrgency } from '@/utils/prescriptionEnd';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const prescriptionStore = usePrescriptionStore();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs de filtre.
const columns = computed(() => [
  { key: 'patient', label: t('prescriptions.table.patient') },
  { key: 'content', label: t('prescriptions.table.content') },
  { key: 'duration', label: t('prescriptions.table.duration') },
  { key: 'start_date', label: t('prescriptions.table.start_date') },
  { key: 'end_date', label: t('prescriptions.table.end_date') },
  { key: 'prescriber', label: t('prescriptions.table.prescriber') },
]);
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

onMounted(() => {
  prescriptionStore.fetchPrescriptions();
  prescriptionStore.fetchExamTypes();
});

const searchQuery = computed({
  get: () => prescriptionStore.filters.searchQuery,
  set: (val) => prescriptionStore.setFilters({ searchQuery: val }),
});

const dateFrom = computed({
  get: () => prescriptionStore.filters.dateFrom,
  set: (val) => prescriptionStore.setFilters({ dateFrom: val }),
});

const dateTo = computed({
  get: () => prescriptionStore.filters.dateTo,
  set: (val) => prescriptionStore.setFilters({ dateTo: val }),
});

function goToPage(page) {
  if (page >= 1 && page <= prescriptionStore.pagination.total_pages) {
    prescriptionStore.setPage(page);
  }
}

function patientName(presc) {
  const p = presc.patient;
  if (!p) return '-';
  return [p.first_name, p.last_name].filter(Boolean).join(' ');
}

// "Urgence de renouvellement" sur la date de fin (voir utils/prescriptionEnd.js) : echue = gris,
// aujourd'hui ou 3 jours = rouge, 7 jours = orange, 14 jours = bleu, au-dela = vert. Uniquement pour les
// prescriptions medicamenteuses (les bons d'examen n'ont pas de date de fin, voir le v-if du gabarit).
function endTone(presc) {
  return endUrgency(presc.end_date)?.tone || 'neutral';
}

function endLabel(presc) {
  const u = endUrgency(presc.end_date);
  if (!u) return '';
  if (u.kind === 'expired') return t('prescriptions.end_expired');
  if (u.kind === 'today') return t('prescriptions.end_today');
  return t('prescriptions.end_in_days', { n: u.days }, u.days);
}

const showModal = ref(false);
const editingPrescription = ref(null);

function openCreateModal() {
  editingPrescription.value = null;
  showModal.value = true;
}

function openEditModal(presc) {
  editingPrescription.value = presc;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingPrescription.value = null;
}

async function handleSave(data) {
  try {
    if (editingPrescription.value) {
      await prescriptionStore.updatePrescription(editingPrescription.value.prescription_id, data);
    } else {
      await prescriptionStore.createPrescription(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement prescription:', err);
    notify('alerts.save_failed', { detail: err.response?.data?.detail || err.message });
  }
}

async function handleDelete(presc) {
  if (!confirm(t('prescriptions.confirm_delete'))) return;
  try {
    await prescriptionStore.deletePrescription(presc.prescription_id);
  } catch (err) {
    console.error('Erreur suppression prescription:', err);
    notify('alerts.delete_failed', { detail: err.response?.data?.detail || err.message });
  }
}
</script>
