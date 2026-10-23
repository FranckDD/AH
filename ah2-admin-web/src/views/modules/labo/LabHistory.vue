<template>
  <div class="h-full overflow-y-auto p-4 text-sm md:p-6 [&_table]:text-sm [&_dd]:text-sm">
    <div class="mx-auto grid max-w-7xl gap-6">

      <PageHeader :title="t('lab.nav.history')" />

      <section :aria-label="t('labScreens.filters_label')" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:grid-cols-[1fr_16rem_auto_auto] lg:items-end">
        <FormField id="lab-history-search" :label="t('labScreens.history_search')" v-slot="{ describedBy }">
          <input id="lab-history-search" v-model="filters.query" @input="handleSearch" type="text" :placeholder="t('lab.history_view.search_ph')"
                 :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="lab-history-status" :label="t('labScreens.status_filter')" v-slot="{ describedBy }">
          <select id="lab-history-status" v-model="filters.status" @change="handleFilterChange" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ t('lab.history_view.all_statuses') }}</option>
            <option value="pending">{{ t('lab.status.pending') }}</option>
            <option value="completed">{{ t('lab.history_view.completed_tech') }}</option>
          </select>
        </FormField>

        <AppButton v-if="filters.abnormal" variant="secondary" :icon="ExclamationTriangleIcon" :title="t('lab.history_view.clear_abnormal')" @click="clearAbnormal">
          {{ t('lab.history_view.abnormal_only') }}<template v-if="filters.period">, {{ t(`lab.dashboard.period_${filters.period}`) }}</template>
          <XMarkIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
        </AppButton>

        <AppButton variant="secondary" :icon="ArrowPathIcon" :loading="store.loading" @click="refresh">{{ t('lab.history_view.refresh') }}</AppButton>
      </section>

      <p v-if="store.loading && store.paginatedHistory.items.length === 0" role="status" class="p-10 text-center text-sm text-ink-muted">{{ t('ui.loading') }}</p>
      <section v-else-if="store.paginatedHistory.items.length === 0" class="rounded-card border border-tone-neutral-border bg-white shadow-card">
        <EmptyState :title="t('lab.history_view.empty')" :message="t('lab.history_view.empty_hint')" />
      </section>

      <!-- Un passage patient = une carte : le patient une seule fois, tous ses examens dedans -->
      <!-- Un dossier (passage patient) par ligne, separe par jour ; les examens se deplient -->
      <div v-else class="grid gap-6">
        <section v-for="day in days" :key="day.key" :aria-label="dayLabel(day.key)" class="grid gap-3">
          <h2 class="sticky top-0 z-10 bg-page py-1 text-sm font-semibold capitalize text-ink-muted">{{ dayLabel(day.key) }}</h2>
          <LabHistoryPassage v-for="passage in day.passages" :key="passage.key" :passage="passage" @view="openView" @pdf="downloadPdf" @pdf-batch="downloadBatchPdf" />
        </section>
      </div>

      <nav v-if="store.paginatedHistory.total_pages > 0" :aria-label="t('labScreens.pagination_label')"
           class="flex flex-col gap-3 rounded-card border border-tone-neutral-border bg-white p-3 shadow-card sm:flex-row sm:items-center sm:justify-between">
        <p class="text-sm text-ink-muted">
          {{ t('labScreens.history_passages', { n: passages.length, total: store.paginatedHistory.total_items }) }}
        </p>
        <div class="flex items-center justify-between gap-3 sm:justify-end">
          <AppButton variant="secondary" :disabled="filters.page === 1" @click="prevPage">{{ t('lab.history_view.prev') }}</AppButton>
          <span class="text-sm font-medium text-ink">
            {{ t('lab.history_view.page', { current: store.paginatedHistory.current_page, total: store.paginatedHistory.total_pages }) }}
          </span>
          <AppButton variant="secondary" :disabled="filters.page >= store.paginatedHistory.total_pages" @click="nextPage">{{ t('lab.history_view.next') }}</AppButton>
        </div>
      </nav>

      <ResultDetailModal
          v-if="selectedResult"
          :result="selectedResult"
          @close="selectedResult = null"
          @print="downloadPdf"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useLabStore } from '@/stores/labStore';
import { useI18n } from 'vue-i18n';
import ResultDetailModal from '@/components/lab/ResultDetailModal.vue';
import LabHistoryPassage from '@/components/lab/LabHistoryPassage.vue';
import debounce from 'lodash/debounce';
import { ArrowPathIcon, ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline';
import { AppButton, PageHeader, FormField, EmptyState } from '@/components/ui';
import { groupHistory, groupPassagesByDay } from '@/utils/labPassages';

// --- INIT ---
const store = useLabStore();
const { t, locale } = useI18n();
const selectedResult = ref(null);
const route = useRoute();

// Un passage patient (batch_id) = une carte avec tous ses examens ; la pagination serveur porte sur les passages.
const passages = computed(() => groupHistory(store.paginatedHistory.items));
// Separes par jour (le plus recent d'abord), comme une chronologie.
const days = computed(() => groupPassagesByDay(passages.value));

const localKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const dayLabel = (key) => {
    if (key === 'unknown') return t('labScreens.day_unknown');
    const long = new Date(`${key}T00:00:00`).toLocaleDateString(locale.value, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    if (key === localKey(today)) return `${t('labScreens.today')}, ${long}`;
    if (key === localKey(yesterday)) return `${t('labScreens.yesterday')}, ${long}`;
    return long;
};
// Style commun des champs.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Arrivee depuis la carte "Pathologiques" du dashboard : ?abnormal=1&period=month
const PERIODS = ['day', 'month', 'year'];
const filters = ref({
    query: '',
    status: '',
    abnormal: route.query.abnormal === '1',
    period: PERIODS.includes(route.query.period) ? route.query.period : null,
    page: 1,
    limit: 15 // Tu peux ajuster le nombre d'éléments par page ici
});

// --- API LOGIC ---
const fetchData = async () => {
    const q = filters.value.query;
    
    // On n'envoie pas la requête si on a tapé un seul caractère (sauf si c'est vide)
    if (q.length === 1) return;

    // Utilisation de la nouvelle action paginée du store
    await store.fetchPaginatedHistory({
        page: filters.value.page,
        limit: filters.value.limit,
        search: q.length >= 2 ? q : null,
        status: filters.value.status || null,
        abnormal: filters.value.abnormal ? true : null,
        period: filters.value.abnormal ? filters.value.period : null,
        group: true
    });
};

const clearAbnormal = () => {
    filters.value.abnormal = false;
    filters.value.period = null;
    filters.value.page = 1;
    fetchData();
};

// Réinitialise la page à 1 quand on fait une nouvelle recherche
const handleSearch = debounce(() => {
    filters.value.page = 1;
    fetchData();
}, 400);

// Réinitialise la page à 1 quand on change le statut
const handleFilterChange = () => {
    filters.value.page = 1;
    fetchData();
};

// Pagination - Page suivante
const nextPage = () => {
    if (filters.value.page < store.paginatedHistory.total_pages) {
        filters.value.page++;
        fetchData();
    }
};

// Pagination - Page précédente
const prevPage = () => {
    if (filters.value.page > 1) {
        filters.value.page--;
        fetchData();
    }
};

const refresh = () => {
    filters.value.query = '';
    filters.value.status = '';
    filters.value.page = 1;
    fetchData();
};

// --- ACTIONS ---
const openView = async (item) => {
    // Attention: l'ID s'appelle maintenant result_id dans notre nouveau schéma
    const detail = await store.fetchResultDetail(item.result_id);
    if (detail) {
        selectedResult.value = detail;
    }
};

const downloadBatchPdf = async (passage) => {
    await store.downloadBatchPDF(passage.batch_id, `Dossier_${passage.exams[0].code || passage.batch_id}.pdf`);
};

const downloadPdf = async (item) => {
    const filename = `Resultat_${item.result_id}.pdf`;
    await store.downloadPDF(item.result_id, filename);
};

onMounted(() => {
    fetchData();
});
</script>
