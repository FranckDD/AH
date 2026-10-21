<template>
  <div class="bg-white rounded-2xl shadow-xs border border-gray-100 overflow-hidden">
    <!-- Filtres -->
    <div class="p-4 md:p-6 border-b border-gray-100 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
      <label class="block">
        <span class="text-xs font-semibold text-gray-600">{{ t('toxico.discharged.filters.search') }}</span>
        <input :value="store.dischargedFilters.search" @input="onSearch" type="search"
               :placeholder="t('toxico.discharged.filters.search_placeholder')"
               class="mt-1 block w-full min-h-[44px] lg:min-h-0 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm focus:ring-indigo-500 focus:border-indigo-500" />
      </label>
      <label class="block">
        <span class="text-xs font-semibold text-gray-600">{{ t('toxico.discharged.filters.reason') }}</span>
        <select :value="store.dischargedFilters.reason" @change="store.setDischargedFilters({ reason: $event.target.value })"
                class="mt-1 block w-full min-h-[44px] lg:min-h-0 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm">
          <option value="">{{ t('toxico.discharged.filters.all_reasons') }}</option>
          <option v-for="r in DISCHARGE_REASONS" :key="r" :value="r">{{ t(dischargeReasonLabelKey(r)) }}</option>
        </select>
      </label>
      <label class="block">
        <span class="text-xs font-semibold text-gray-600">{{ t('toxico.discharged.filters.from') }}</span>
        <input type="date" :value="dateFrom" @change="onDate('from', $event.target.value)"
               class="mt-1 block w-full min-h-[44px] lg:min-h-0 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm" />
      </label>
      <label class="block">
        <span class="text-xs font-semibold text-gray-600">{{ t('toxico.discharged.filters.to') }}</span>
        <input type="date" :value="dateTo" @change="onDate('to', $event.target.value)"
               class="mt-1 block w-full min-h-[44px] lg:min-h-0 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm" />
      </label>
      <p v-if="dateError" role="alert" class="md:col-span-2 lg:col-span-4 text-sm text-red-600">{{ t(dateError) }}</p>
    </div>

    <!-- Etats (periode invalide : resultats vides, pas d'ancienne periode appliquee en silence) -->
    <div v-if="dateError" class="p-10 text-center text-gray-500">{{ t('toxico.discharged.invalid_range_hint') }}</div>
    <div v-else-if="store.dischargedLoading" class="p-10 text-center text-gray-500 flex flex-col items-center">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-2"></div>
      {{ t('toxico.discharged.loading') }}
    </div>
    <div v-else-if="store.dischargedError" role="alert" class="p-10 text-center">
      <p class="text-red-600 mb-3">{{ t('toxico.discharged.error') }}</p>
      <button type="button" @click="store.fetchDischarged()"
              class="min-h-[44px] lg:min-h-0 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold">
        {{ t('toxico.discharged.retry') }}
      </button>
    </div>
    <div v-else-if="!store.discharged.length" class="p-10 text-center text-gray-500">
      {{ t('toxico.discharged.empty') }}
    </div>

    <template v-else>
      <!-- Tableau (lg+) -->
      <div class="hidden lg:block overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-indigo-50 text-indigo-900 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('toxico.discharged.col.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('toxico.discharged.col.stay') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('toxico.discharged.col.reason') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('toxico.discharged.col.psy') }}</th>
              <th class="px-6 py-4 font-semibold text-center">{{ t('toxico.discharged.col.stays') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('toxico.discharged.col.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="row in store.discharged" :key="row.dossier_id" class="hover:bg-gray-50">
              <td class="px-6 py-4">
                <div class="font-medium text-gray-900">{{ row.patientName }}</div>
                <div class="text-xs text-gray-500 font-mono">{{ row.code }}</div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-700">{{ stayDates(row) }}</td>
              <td class="px-6 py-4">
                <span :class="reasonClass(row.last_stay?.discharge_reason)" class="px-2.5 py-0.5 text-xs font-bold rounded-full border">
                  {{ t(dischargeReasonLabelKey(row.last_stay?.discharge_reason)) }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ row.last_stay?.psychologist_name || t('toxico.discharged.none') }}</td>
              <td class="px-6 py-4 text-center text-sm font-semibold text-gray-800">{{ row.stays_count }}</td>
              <td class="px-6 py-4 text-right whitespace-nowrap space-x-2">
                <button type="button" @click="$emit('view', row)"
                        class="text-blue-600 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg text-xs font-semibold">
                  {{ t('toxico.discharged.view') }}
                </button>
                <button v-if="canReadmit" type="button" @click="$emit('readmit', row)"
                        class="text-green-700 hover:text-green-900 bg-green-50 hover:bg-green-100 px-3 py-1.5 rounded-lg text-xs font-semibold">
                  {{ t('toxico.discharged.readmit') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Cartes (< lg ; 2 colonnes a partir de md) -->
      <ul class="lg:hidden grid grid-cols-1 md:grid-cols-2 gap-3 p-4">
        <li v-for="row in store.discharged" :key="row.dossier_id" class="border border-gray-200 rounded-xl p-4 space-y-2">
          <div class="flex justify-between items-start gap-2">
            <div class="min-w-0">
              <p class="font-semibold text-gray-900 truncate">{{ row.patientName }}</p>
              <p class="text-xs text-gray-500 font-mono">{{ row.code }}</p>
            </div>
            <span :class="reasonClass(row.last_stay?.discharge_reason)" class="shrink-0 px-2.5 py-0.5 text-xs font-bold rounded-full border">
              {{ t(dischargeReasonLabelKey(row.last_stay?.discharge_reason)) }}
            </span>
          </div>
          <p class="text-sm text-gray-700">{{ stayDates(row) }}</p>
          <p class="text-sm text-gray-600">
            {{ t('toxico.discharged.col.psy') }} : {{ row.last_stay?.psychologist_name || t('toxico.discharged.none') }}
            · {{ t('toxico.discharged.stays_count', { n: row.stays_count }) }}
          </p>
          <div class="flex gap-2 pt-1">
            <button type="button" @click="$emit('view', row)"
                    class="flex-1 min-h-[44px] bg-blue-50 text-blue-700 rounded-lg text-sm font-semibold">
              {{ t('toxico.discharged.view') }}
            </button>
            <button v-if="canReadmit" type="button" @click="$emit('readmit', row)"
                    class="flex-1 min-h-[44px] bg-green-50 text-green-700 rounded-lg text-sm font-semibold">
              {{ t('toxico.discharged.readmit') }}
            </button>
          </div>
        </li>
      </ul>

    </template>

      <!-- Pagination : visible des qu'il existe des lignes, meme si la page courante est vide -->
      <nav v-if="!dateError && !store.dischargedLoading && !store.dischargedError && store.dischargedTotal > 0" class="p-4 border-t border-gray-100 flex items-center justify-between gap-2"
           :aria-label="t('toxico.discharged.pagination')">
        <button type="button" :disabled="page <= 1" @click="store.setDischargedPage(page - 1)"
                class="min-h-[44px] lg:min-h-0 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">
          {{ t('toxico.discharged.prev') }}
        </button>
        <span class="text-sm text-gray-700">
          {{ t('toxico.discharged.page_of', { page, pages: Math.max(store.dischargedTotalPages, 1), total: store.dischargedTotal }) }}
        </span>
        <button type="button" :disabled="page >= Math.max(store.dischargedTotalPages, 1)" @click="store.setDischargedPage(page + 1)"
                class="min-h-[44px] lg:min-h-0 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">
          {{ t('toxico.discharged.next') }}
        </button>
      </nav>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { DISCHARGE_REASONS, dischargeReasonLabelKey } from '@/utils/toxicoStays';
import { dischargedDateRangeError } from '@/utils/toxicoDischarged';

defineProps({ canReadmit: { type: Boolean, default: false } });
defineEmits(['view', 'readmit']);

const { t } = useI18n();
const store = useToxicoStore();
const page = computed(() => store.dischargedFilters.page);

// Dates saisies localement : envoyees seulement si la periode est valide.
const dateFrom = ref(store.dischargedFilters.from);
const dateTo = ref(store.dischargedFilters.to);
const dateError = computed(() => dischargedDateRangeError(dateFrom.value, dateTo.value));
const onDate = (which, value) => {
    if (which === 'from') dateFrom.value = value; else dateTo.value = value;
    if (dateError.value) store.clearDischarged();
    else store.setDischargedFilters({ from: dateFrom.value, to: dateTo.value });
};

let searchTimeout;
const onSearch = (e) => {
    clearTimeout(searchTimeout);
    const value = e.target.value;
    searchTimeout = setTimeout(() => {
        if (dateError.value) store.dischargedFilters.search = value;
        else store.setDischargedFilters({ search: value });
    }, 400);
};

const fmt = (d) => {
    if (!d) return '—';
    const x = new Date(String(d).slice(0, 10));
    return isNaN(x.getTime()) ? d : x.toLocaleDateString();
};
const stayDates = (row) => row.last_stay
    ? t('toxico.discharged.stay_dates', { n: row.last_stay.stay_number, from: fmt(row.last_stay.admission_date), to: fmt(row.last_stay.discharge_date) })
    : t('toxico.discharged.no_stay');

const reasonClass = (r) => ({
    guerison: 'bg-green-100 text-green-800 border-green-200',
    abandon: 'bg-orange-100 text-orange-800 border-orange-200',
    exclusion: 'bg-red-100 text-red-800 border-red-200',
    autre: 'bg-gray-100 text-gray-700 border-gray-200',
}[r] || 'bg-gray-100 text-gray-500 border-gray-200');

onMounted(() => { if (!dateError.value) store.fetchDischarged(); });
onBeforeUnmount(() => clearTimeout(searchTimeout));
</script>
