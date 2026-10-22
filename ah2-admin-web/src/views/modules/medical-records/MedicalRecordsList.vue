<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('medicalRecords.title')" :subtitle="t('medicalRecords.subtitle')">
      <template #actions>
        <AppButton :icon="PlusCircleIcon" @click="openCreateModal">
          {{ t('medicalRecords.new_record') }}
        </AppButton>
      </template>
    </PageHeader>

    <section class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:flex lg:flex-wrap lg:items-end">

      <div class="md:col-span-2 lg:min-w-[220px] lg:flex-1">
        <FormField id="mr-search" :label="t('medicalRecords.search_label')" v-slot="{ describedBy }">
          <div class="relative">
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
            <input
              id="mr-search"
              v-model="searchQuery"
              type="text"
              :aria-describedby="describedBy"
              :placeholder="t('medicalRecords.search_placeholder')"
              :class="[fieldClass, 'bg-white pl-10']"
            >
          </div>
        </FormField>
      </div>

      <div class="lg:w-44">
        <FormField id="mr-motif-filter" :label="t('medicalRecords.motif_label')" v-slot="{ describedBy }">
          <select id="mr-motif-filter" v-model="motifFilter" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option value="">{{ t('medicalRecords.motif_all') }}</option>
            <option v-for="m in medicalRecordStore.motifs" :key="m.code" :value="m.code">{{ m.label_fr }}</option>
          </select>
        </FormField>
      </div>

      <div class="lg:w-40">
        <FormField id="mr-severity-filter" :label="t('medicalRecords.severity_label')" v-slot="{ describedBy }">
          <select id="mr-severity-filter" v-model="severityFilter" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']">
            <option value="">{{ t('medicalRecords.severity_all') }}</option>
            <option value="low">{{ t('medicalRecords.severity_low') }}</option>
            <option value="medium">{{ t('medicalRecords.severity_medium') }}</option>
            <option value="high">{{ t('medicalRecords.severity_high') }}</option>
          </select>
        </FormField>
      </div>

      <div class="lg:w-40">
        <FormField id="mr-date-from" :label="t('medicalRecords.date_from')" v-slot="{ describedBy }">
          <input id="mr-date-from" v-model="dateFrom" type="date" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
      </div>

      <div class="lg:w-40">
        <FormField id="mr-date-to" :label="t('medicalRecords.date_to')" v-slot="{ describedBy }">
          <input id="mr-date-to" v-model="dateTo" type="date" :aria-describedby="describedBy" :class="[fieldClass, 'bg-white']" />
        </FormField>
      </div>
    </section>

    <section class="grid gap-3">

      <p class="text-base text-ink-muted" aria-live="polite">
        {{ medicalRecordStore.pagination.total }} {{ t('medicalRecords.results_count') }}
      </p>

      <ResponsiveTable
        :columns="columns"
        :rows="medicalRecordStore.records"
        row-key="record_id"
        :loading="medicalRecordStore.isLoading"
        :empty-title="t('medicalRecords.empty')"
      >
        <template #cell-patient="{ row: rec }">
          <div class="text-base font-medium text-ink">{{ patientName(rec) }}</div>
          <div class="text-sm text-ink-muted">{{ rec.patient?.code_patient }}</div>
        </template>
        <template #cell-date="{ row: rec }"><span class="font-mono">{{ (rec.consultation_date || '').substring(0, 10) }}</span></template>
        <template #cell-motif="{ row: rec }">{{ motifLabel(rec.motif_code) }}</template>
        <template #cell-severity="{ row: rec }">
          <StatusBadge :tone="severityTone(rec.severity)" :label="severityLabel(rec.severity)" />
        </template>
        <template #cell-diagnosis="{ row: rec }">
          <span class="block lg:max-w-xs lg:truncate" :title="rec.diagnosis">{{ rec.diagnosis || '-' }}</span>
        </template>
        <template #cell-treatment="{ row: rec }">
          <span class="block lg:max-w-xs lg:truncate" :title="rec.treatment">{{ rec.treatment || '-' }}</span>
        </template>

        <template #actions="{ row: rec }">
          <!-- Consultation passee : lecture seule, on affiche le badge a la place des boutons -->
          <StatusBadge v-if="!isRecordEditable(rec, medicalRecordStore.records)" tone="neutral" :label="t('medical.readonly.badge')" />
          <template v-else>
            <AppButton
              variant="secondary"
              @click="openEditModal(rec)"
              :disabled="!rec.record_id"
              :title="rec.record_id ? '' : 'En attente de synchronisation'"
            >
              {{ t('medicalRecords.actions.edit') }}
            </AppButton>
            <AppButton
              variant="danger"
              @click="handleDelete(rec)"
              :disabled="!rec.record_id"
              :title="rec.record_id ? '' : 'En attente de synchronisation'"
            >
              {{ t('medicalRecords.actions.delete') }}
            </AppButton>
          </template>
        </template>
      </ResponsiveTable>

      <div v-if="medicalRecordStore.pagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">
          {{ t('common.page') }} {{ medicalRecordStore.pagination.page }} / {{ medicalRecordStore.pagination.total_pages }}
        </p>
        <div class="flex gap-2">
          <AppButton
            variant="secondary"
            :icon="ChevronLeftIcon"
            :aria-label="t('medicalRecords.prev_page')"
            @click="goToPage(medicalRecordStore.pagination.page - 1)"
            :disabled="medicalRecordStore.pagination.page === 1"
          />
          <AppButton
            variant="secondary"
            :icon="ChevronRightIcon"
            :aria-label="t('medicalRecords.next_page')"
            @click="goToPage(medicalRecordStore.pagination.page + 1)"
            :disabled="medicalRecordStore.pagination.page === medicalRecordStore.pagination.total_pages"
          />
        </div>
      </div>

    </section>

    <MedicalRecordModal
      v-if="showModal"
      :record="editingRecord"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { useI18n } from 'vue-i18n';
import MedicalRecordModal from '@/components/medical-records/MedicalRecordModal.vue';
import { isRecordEditable } from '@/utils/consultationLock';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const medicalRecordStore = useMedicalRecordStore();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs de filtre.
const columns = computed(() => [
  { key: 'patient', label: t('medicalRecords.table.patient') },
  { key: 'date', label: t('medicalRecords.table.date') },
  { key: 'motif', label: t('medicalRecords.table.motif') },
  { key: 'severity', label: t('medicalRecords.table.severity') },
  { key: 'diagnosis', label: t('medicalRecords.table.diagnosis') },
  { key: 'treatment', label: t('medicalRecords.table.treatment') },
]);
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

onMounted(() => {
  medicalRecordStore.fetchMedicalRecords();
  medicalRecordStore.fetchMotifs();
});

const searchQuery = computed({
  get: () => medicalRecordStore.filters.searchQuery,
  set: (val) => medicalRecordStore.setFilters({ searchQuery: val }),
});

const motifFilter = computed({
  get: () => medicalRecordStore.filters.motifCode,
  set: (val) => medicalRecordStore.setFilters({ motifCode: val }),
});

const severityFilter = computed({
  get: () => medicalRecordStore.filters.severity,
  set: (val) => medicalRecordStore.setFilters({ severity: val }),
});

const dateFrom = computed({
  get: () => medicalRecordStore.filters.dateFrom,
  set: (val) => medicalRecordStore.setFilters({ dateFrom: val }),
});

const dateTo = computed({
  get: () => medicalRecordStore.filters.dateTo,
  set: (val) => medicalRecordStore.setFilters({ dateTo: val }),
});

function goToPage(page) {
  if (page >= 1 && page <= medicalRecordStore.pagination.total_pages) {
    medicalRecordStore.setPage(page);
  }
}

function patientName(rec) {
  const p = rec.patient;
  if (!p) return '-';
  return [p.first_name, p.last_name].filter(Boolean).join(' ');
}

function motifLabel(code) {
  const m = medicalRecordStore.motifs.find((x) => x.code === code);
  return m ? m.label_fr : (code || '-');
}

// Coloration par gravite (rouge / orange / vert), toujours accompagnee du texte.
function severityTone(severity) {
  if (severity === 'high') return 'danger';
  if (severity === 'medium') return 'warning';
  if (severity === 'low') return 'success';
  return 'neutral';
}

function severityLabel(severity) {
  if (severity === 'high') return t('medicalRecords.severity_high');
  if (severity === 'medium') return t('medicalRecords.severity_medium');
  if (severity === 'low') return t('medicalRecords.severity_low');
  return '-';
}

const showModal = ref(false);
const editingRecord = ref(null);

function openCreateModal() {
  editingRecord.value = null;
  showModal.value = true;
}

function openEditModal(rec) {
  editingRecord.value = rec;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingRecord.value = null;
}

async function handleSave(data) {
  try {
    if (editingRecord.value) {
      await medicalRecordStore.updateMedicalRecord(editingRecord.value.record_id ?? editingRecord.value.local_id, data);
    } else {
      await medicalRecordStore.createMedicalRecord(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement dossier medical:', err);
    alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
  }
}

async function handleDelete(rec) {
  if (!confirm(t('medicalRecords.confirm_delete'))) return;
  try {
    await medicalRecordStore.deleteMedicalRecord(rec.record_id);
  } catch (err) {
    console.error('Erreur suppression dossier medical:', err);
    alert('Erreur lors de la suppression : ' + (err.response?.data?.detail || err.message));
  }
}
</script>
