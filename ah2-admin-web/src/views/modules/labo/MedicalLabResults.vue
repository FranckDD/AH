<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('lab.nav.medical_results')" />

    <div class="flex flex-col gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card sm:flex-row sm:items-center">
      <div class="relative flex-1 sm:max-w-md">
        <label for="lab-results-search" class="sr-only">{{ t('lab.history_view.search_ph') }}</label>
        <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
        <input
            id="lab-results-search"
            v-model="filters.query"
            @input="handleSearch"
            type="text"
            :placeholder="t('lab.history_view.search_ph')"
            class="block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white pl-10 pr-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600"
        >
      </div>

      <AppButton variant="secondary" :icon="ArrowPathIcon" @click="refresh" :title="t('lab.history_view.refresh')">
        {{ t('lab.history_view.refresh') }}
      </AppButton>
    </div>

    <section class="grid gap-3">

      <LoadErrorState v-if="store.historyFailed" @retry="refresh()" />

      <ResponsiveTable
        v-else
        :columns="columns"
        :rows="store.paginatedHistory.items"
        row-key="result_id"
        :loading="store.loading"
        :empty-title="t('lab.history_view.empty_medical')"
        :empty-message="t('lab.history_view.empty_medical_hint')"
      >
        <template #cell-date="{ row: res }">
          <div class="text-base font-medium text-ink">{{ formatDate(res.test_date) }}</div>
          <div class="font-mono text-sm text-ink-muted">#{{ res.result_id }} <span v-if="res.code">| {{ res.code }}</span></div>
        </template>

        <template #cell-patient="{ row: res }">
          <div class="text-base font-bold text-ink">{{ res.patient_name }}</div>
          <div class="mt-1 flex flex-wrap items-center gap-2">
            <span class="text-sm text-ink-muted">{{ res.patient_age }} - {{ res.patient_sexe }}</span>
            <StatusBadge v-if="res.is_external" tone="warning" :label="t('lab.result_modal.external')" />
          </div>
        </template>

        <template #cell-exam="{ row: res }">
          <span class="font-medium text-ink">{{ res.examen_nom }}</span>
        </template>

        <template #actions="{ row: res }">
          <AppButton variant="secondary" :icon="EyeIcon" @click="openView(res)" :title="t('lab.history_view.view_details')">
            {{ t('lab.history_view.view_details') }}
          </AppButton>
          <AppButton variant="secondary" :icon="PrinterIcon" @click="downloadPdf(res)" :title="t('lab.history_view.download_pdf')">
            {{ t('lab.history_view.download_pdf') }}
          </AppButton>
        </template>
      </ResponsiveTable>

      <div v-if="store.paginatedHistory.total_pages > 0" class="flex flex-col gap-3 rounded-card border border-tone-neutral-border bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-base text-ink-muted" aria-live="polite">
              {{ t('lab.history_view.showing', { n: store.paginatedHistory.items.length, total: store.paginatedHistory.total_items }) }}
          </p>
          <div class="flex items-center justify-between gap-2 sm:justify-end">
              <AppButton
                  variant="secondary"
                  @click="prevPage"
                  :disabled="filters.page === 1"
              >
                  {{ t('lab.history_view.prev') }}
              </AppButton>
              <span class="px-2 text-base font-medium text-ink">
                  {{ t('lab.history_view.page', { current: store.paginatedHistory.current_page, total: store.paginatedHistory.total_pages }) }}
              </span>
              <AppButton
                  variant="secondary"
                  @click="nextPage"
                  :disabled="filters.page >= store.paginatedHistory.total_pages"
              >
                  {{ t('lab.history_view.next') }}
              </AppButton>
          </div>
      </div>
    </section>

    <ResultDetailModal
        v-if="selectedResult"
        :result="selectedResult"
        @close="selectedResult = null"
        @print="downloadPdf"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useLabStore } from '@/stores/labStore';
import { useI18n } from 'vue-i18n';
import ResultDetailModal from '@/components/lab/ResultDetailModal.vue';
import { AppButton, PageHeader, StatusBadge, ResponsiveTable, LoadErrorState } from '@/components/ui';
import dayjs from 'dayjs';
import debounce from 'lodash/debounce';
import {
    MagnifyingGlassIcon, ArrowPathIcon, PrinterIcon, EyeIcon
} from '@heroicons/vue/24/outline';

// Vue dediee medecin/nurse (chantier perimetre medical, 2026-09-22) - pas
// de selecteur de statut : le backend (controller/lab_controller.py,
// Tache 3 de ce meme plan) force deja "completed" pour ce role, quel que
// soit le parametre envoye. L'afficher laisserait croire qu'on peut choisir
// "en attente" pour ne jamais rien voir.
const store = useLabStore();
const { t } = useI18n();
const selectedResult = ref(null);

// Colonnes du tableau (cartes empilees sous lg).
const columns = computed(() => [
    { key: 'date', label: t('lab.history_view.col_date') },
    { key: 'patient', label: t('lab.history_view.col_patient') },
    { key: 'exam', label: t('lab.history_view.col_exam') },
]);

const filters = ref({
    query: '',
    page: 1,
    limit: 15
});

const fetchData = async () => {
    const q = filters.value.query;
    if (q.length === 1) return;

    await store.fetchPaginatedHistory({
        page: filters.value.page,
        limit: filters.value.limit,
        search: q.length >= 2 ? q : null,
    });
};

const handleSearch = debounce(() => {
    filters.value.page = 1;
    fetchData();
}, 400);

const nextPage = () => {
    if (filters.value.page < store.paginatedHistory.total_pages) {
        filters.value.page++;
        fetchData();
    }
};

const prevPage = () => {
    if (filters.value.page > 1) {
        filters.value.page--;
        fetchData();
    }
};

const refresh = () => {
    filters.value.query = '';
    filters.value.page = 1;
    fetchData();
};

const openView = async (item) => {
    const detail = await store.fetchResultDetail(item.result_id);
    if (detail) {
        selectedResult.value = detail;
    }
};

const downloadPdf = async (item) => {
    const filename = `Resultat_${item.result_id}.pdf`;
    await store.downloadPDF(item.result_id, filename);
};

const formatDate = (d) => {
    if (!d) return t('lab.history_view.na');
    return dayjs(d).format('DD/MM/YYYY HH:mm');
};

onMounted(() => {
    fetchData();
});
</script>
